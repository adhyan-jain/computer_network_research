// sasp-mlo-experiment.cc - ns-3.47 Wi-Fi 7 STR-MLO shared-TID cross-flow reordering experiment.
//
// One AP MLD -> one non-AP STA MLD, two STR links (5 GHz / 6 GHz), two UDP flows (latency-sensitive
// and bulk) mapped to the SAME TID (0, AC_BE) and hence the same Block Ack reordering context.
//
// Arms (same binary, same ns-3 PHY/MAC, same receiver):  --scheduler=0 native FIFO,
// 1 Mean-Only Sequencing, 2 Full SASP. The predictive arms act ONLY through the sequence
// reservation hook that patch 0001 adds at QosTxop::GetNextMpdu (the point where the sequence
// number is committed). The receiver is the unmodified ns-3 RecipientBlockAckAgreement; patch
// 0002 only adds observation callbacks.
//
// Causality: policy inputs are (a) link estimators updated from ACK/BA completions that have
// already happened, (b) current simulation time, (c) queue contents, (d) known per-link
// configuration (initial estimate only). No future value is ever passed to the policy.
#include "sasp-policy.h"

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/propagation-module.h"
#include "ns3/spectrum-module.h"
#include "ns3/wifi-module.h"
#include "ns3/recipient-block-ack-agreement.h"
#include "ns3/qos-txop.h"
#include "ns3/wifi-mac-queue.h"

#include <chrono>
#include <cstdio>
#include <fstream>
#include <iomanip>
#include <map>
#include <numeric>
#include <sstream>
#include <unordered_map>
#include <unordered_set>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("SaspMloExperiment");

namespace
{

// ------------------------------------------------------------------ flow tag
class FlowTag : public Tag
{
  public:
    static TypeId GetTypeId()
    {
        static TypeId tid = TypeId("ns3::SaspFlowTag").SetParent<Tag>().AddConstructor<FlowTag>();
        return tid;
    }

    TypeId GetInstanceTypeId() const override { return GetTypeId(); }

    uint32_t GetSerializedSize() const override { return 1 + 4 + 8; }

    void Serialize(TagBuffer i) const override
    {
        i.WriteU8(flow);
        i.WriteU32(seq);
        i.WriteU64(genNs);
    }

    void Deserialize(TagBuffer i) override
    {
        flow = i.ReadU8();
        seq = i.ReadU32();
        genNs = i.ReadU64();
    }

    void Print(std::ostream& os) const override { os << "flow=" << +flow << " seq=" << seq; }

    uint8_t flow{0};
    uint32_t seq{0};
    uint64_t genNs{0};
};

uint64_t
Key(uint8_t flow, uint32_t seq)
{
    return (static_cast<uint64_t>(flow) << 32) | seq;
}

bool
GetTag(Ptr<const Packet> p, FlowTag& t)
{
    return p && p->PeekPacketTag(t);
}

constexpr int kSnSpace = 4096;

// signed distance of sn relative to ref (mod 4096), in (-2048, 2048]
int
SignedDiff(int sn, int ref)
{
    int d = ((sn - ref) % kSnSpace + kSnSpace) % kSnSpace;
    if (d > kSnSpace / 2)
    {
        d -= kSnSpace;
    }
    return d;
}

// ------------------------------------------------------------------ global run state
struct AppPkt
{
    double genMs{0};
    double sinkMs{-1};
    uint32_t size{0};
    bool delivered{false};
};

struct TxRec
{
    double firstTxMs{-1};
    double lastTxMs{-1};
    int link{-1};
    int attempts{0};
    int sn{-1};
    bool acked{false};
    bool dropped{false};
    int64_t snExt{INT64_MIN};
    bool reserved{false};
    double reserveMs{0};
    double holdMs{-1};
    double psduBits{0};
};

struct RxRec
{
    double insMs{-1};
    double relMs{-1};
    int64_t ext{0};
    uint64_t insIdx{0};
    uint64_t relIdx{0};
    bool forced{false};
    bool released{false};
};

struct Globals
{
    std::map<uint64_t, AppPkt> app[4];      // [flow][key]
    std::unordered_map<uint64_t, TxRec> tx; // key = (flow, seq)
    std::unordered_map<uint64_t, RxRec> rx;
    std::vector<uint64_t> insertOrder; // keys in insertion order (global event index)
    uint64_t evIdx{0};
    int64_t rxExtRef{0};
    int64_t txExtRef{0};
    // receiver counters
    uint64_t forcedAdvanceEvents{0};
    uint64_t forcedAdvanceSlots{0};
    uint64_t forcedReleased{0};
    double occT{0}, occArea{0}, occMax{0};
    uint64_t occNow{0};
    // tx counters
    std::array<uint64_t, 2> psdus{{0, 0}};
    std::array<uint64_t, 2> mpdusTx{{0, 0}};
    uint64_t nacked{0}, dropped{0}, untaggedTx{0};
    // per-link completion samples (ms)
    std::array<std::vector<double>, 2> comp;
    std::array<std::vector<double>, 2> psduSize;
    uint64_t snChangedAfterCommit{0};
    // policy
    std::array<sasp::LinkEstimator, 2> est;
    std::array<double, 2> lastPsduStartMs{{-1e9, -1e9}};
    std::array<double, 2> lastPsduBits{{0, 0}};
    std::map<int, double> weight;
    sasp::Mode mode{sasp::Mode::FIFO};
    // decision stats
    uint64_t decisions{0}, decMultiFlow{0}, decPairwise{0}, decGe3{0}, decReserveApplied{0},
        decFullNeMean{0}, reservedMpdus{0}, decNoOtherCand{0};
    double decWallUs{0};
    std::vector<std::string> decLog;
    bool logDecisions{false};
};

Globals G;

// ------------------------------------------------------------------ traffic
class TrafficApp : public Application
{
  public:
    enum Kind
    {
        CBR,
        POISSON,
        SCRIPT
    };

    void Setup(Ptr<Socket> s,
               Address peer,
               uint8_t flow,
               uint32_t size,
               Kind kind,
               double param, // CBR: rate bps; POISSON: mean interval s
               uint32_t stream,
               double startS,
               double stopS)
    {
        m_sock = s;
        m_peer = peer;
        m_flow = flow;
        m_size = size;
        m_kind = kind;
        m_param = param;
        m_start = startS;
        m_stop = stopS;
        m_rng = CreateObject<ExponentialRandomVariable>();
        m_rng->SetStream(stream);
    }

    void AddScripted(double t, uint32_t size) { m_script.push_back({t, size}); }

  private:
    void StartApplication() override
    {
        m_sock->Bind();
        m_sock->Connect(m_peer);
        if (m_kind == SCRIPT)
        {
            for (auto& e : m_script)
            {
                Simulator::Schedule(Seconds(e.first), &TrafficApp::Send, this, e.second);
            }
            return;
        }
        Simulator::Schedule(Seconds(m_start), &TrafficApp::Next, this);
    }

    void StopApplication() override {}

    void Next()
    {
        if (Simulator::Now().GetSeconds() >= m_stop)
        {
            return;
        }
        Send(m_size);
        double gap = (m_kind == CBR) ? (m_size * 8.0 / m_param)
                                     : m_rng->GetValue(m_param, 0.0); // exponential, mean param
        Simulator::Schedule(Seconds(gap), &TrafficApp::Next, this);
    }

    void Send(uint32_t size)
    {
        FlowTag t;
        t.flow = m_flow;
        t.seq = m_seq++;
        t.genNs = Simulator::Now().GetNanoSeconds();
        Ptr<Packet> p = Create<Packet>(size);
        p->AddPacketTag(t);
        AppPkt a;
        a.genMs = Simulator::Now().GetSeconds() * 1e3;
        a.size = size;
        G.app[m_flow][Key(m_flow, t.seq)] = a;
        m_sock->Send(p);
    }

    Ptr<Socket> m_sock;
    Address m_peer;
    uint8_t m_flow{1};
    uint32_t m_size{200};
    Kind m_kind{CBR};
    double m_param{1e6};
    double m_start{0}, m_stop{1};
    uint32_t m_seq{0};
    Ptr<ExponentialRandomVariable> m_rng;
    std::vector<std::pair<double, uint32_t>> m_script;
};

// ------------------------------------------------------------------ trace handlers
double
NowMs()
{
    return Simulator::Now().GetSeconds() * 1e3;
}

void
OnPsduTx(uint8_t link, WifiConstPsduMap map, WifiTxVector, double)
{
    for (const auto& [sta, psdu] : map)
    {
        uint32_t nQos = 0;
        const double psduBits = psdu->GetSize() * 8.0;
        for (auto it = psdu->begin(); it != psdu->end(); ++it)
        {
            const auto& mpdu = *it;
            if (!mpdu->GetHeader().IsQosData())
            {
                continue;
            }
            FlowTag t;
            if (!GetTag(mpdu->GetPacket(), t))
            {
                G.untaggedTx++;
                continue;
            }
            ++nQos;
            auto& r = G.tx[Key(t.flow, t.seq)];
            const int sn = mpdu->GetHeader().GetSequenceNumber();
            if (r.sn >= 0 && r.sn != sn)
            {
                G.snChangedAfterCommit++; // a committed MPDU must never be re-sequenced
            }
            if (r.attempts == 0)
            {
                r.firstTxMs = NowMs();
                const int d = SignedDiff(
                    sn,
                    static_cast<int>(((G.txExtRef % kSnSpace) + kSnSpace) % kSnSpace));
                r.snExt = G.txExtRef + d;
                G.txExtRef = std::max(G.txExtRef, r.snExt);
                if (r.reserved)
                {
                    r.holdMs = NowMs() - r.reserveMs;
                }
            }
            r.sn = sn;
            r.psduBits = psduBits;
            r.lastTxMs = NowMs();
            r.link = link;
            r.attempts++;
            G.mpdusTx[link]++;
        }
        if (nQos > 0)
        {
            G.psdus[link]++;
            G.psduSize[link].push_back(nQos);
            G.lastPsduStartMs[link] = NowMs();
            G.lastPsduBits[link] = psduBits;
        }
    }
}

void
OnAcked(Ptr<const WifiMpdu> mpdu)
{
    if (!mpdu->GetHeader().IsQosData())
    {
        return;
    }
    FlowTag t;
    if (!GetTag(mpdu->GetPacket(), t))
    {
        return;
    }
    auto it = G.tx.find(Key(t.flow, t.seq));
    if (it == G.tx.end() || it->second.acked)
    {
        return;
    }
    auto& r = it->second;
    r.acked = true;
    const double sample = NowMs() - r.firstTxMs; // completion time incl. retries
    if (r.link >= 0)
    {
        G.est[r.link].Update(sample, r.psduBits); // causal: only completed transmissions
        G.comp[r.link].push_back(sample);
    }
}

void
OnNacked(Ptr<const WifiMpdu>)
{
    G.nacked++;
}

void
OnDropped(WifiMacDropReason, Ptr<const WifiMpdu> mpdu)
{
    FlowTag t;
    if (mpdu->GetHeader().IsQosData() && GetTag(mpdu->GetPacket(), t))
    {
        G.dropped++;
        G.tx[Key(t.flow, t.seq)].dropped = true;
    }
}

void
OnSinkRx(Ptr<const Packet> p, const Address&)
{
    FlowTag t;
    if (GetTag(p, t))
    {
        auto& a = G.app[t.flow][Key(t.flow, t.seq)];
        if (!a.delivered)
        {
            a.delivered = true;
            a.sinkMs = NowMs();
        }
    }
}

void
RxInsert(Ptr<const WifiMpdu> mpdu, std::size_t buffered)
{
    FlowTag t;
    if (!GetTag(mpdu->GetPacket(), t))
    {
        return;
    }
    auto& r = G.rx[Key(t.flow, t.seq)];
    if (r.insMs >= 0)
    {
        return;
    }
    const int sn = mpdu->GetHeader().GetSequenceNumber();
    const int d = SignedDiff(sn, static_cast<int>(((G.rxExtRef % kSnSpace) + kSnSpace) % kSnSpace));
    r.ext = G.rxExtRef + d;
    G.rxExtRef = std::max(G.rxExtRef, r.ext);
    r.insMs = NowMs();
    r.insIdx = ++G.evIdx;
    G.insertOrder.push_back(Key(t.flow, t.seq));
    // occupancy accounting
    G.occArea += G.occNow * (r.insMs - G.occT);
    G.occT = r.insMs;
    G.occNow = buffered;
    G.occMax = std::max<double>(G.occMax, buffered);
}

void
RxRelease(Ptr<const WifiMpdu> mpdu, bool forced)
{
    FlowTag t;
    if (!GetTag(mpdu->GetPacket(), t))
    {
        return;
    }
    auto it = G.rx.find(Key(t.flow, t.seq));
    if (it == G.rx.end() || it->second.released)
    {
        return;
    }
    auto& r = it->second;
    r.relMs = NowMs();
    r.relIdx = ++G.evIdx;
    r.forced = forced;
    r.released = true;
    if (forced)
    {
        G.forcedReleased++;
    }
    G.occArea += G.occNow * (r.relMs - G.occT);
    G.occT = r.relMs;
    if (G.occNow > 0)
    {
        G.occNow--;
    }
}

void
RxForced(uint16_t slots, uint16_t)
{
    G.forcedAdvanceEvents++;
    G.forcedAdvanceSlots += slots;
}

// ------------------------------------------------------------------ policy glue
struct Glue
{
    std::vector<Ptr<WifiMpdu>> Reserve(uint8_t k, Ptr<QosTxop> txop, Ptr<WifiMpdu> head)
    {
        using clk = std::chrono::steady_clock;
        const auto w0 = clk::now();
        std::vector<Ptr<WifiMpdu>> out;
        FlowTag ht;
        if (k > 1 || !GetTag(head->GetPacket(), ht))
        {
            return out;
        }
        const uint8_t j = 1 - k;
        std::vector<Ptr<WifiMpdu>> cands{head};
        std::vector<FlowTag> tags{ht};
        auto queue = txop->GetWifiMacQueue();
        // Eligible candidate set (fixed definition, preregistration 3.1): the head plus the first
        // not-yet-sequenced MPDU of each OTHER application flow found within the next
        // kWindow queue entries (at most kMaxCand candidates). Intra-flow FIFO is therefore
        // automatic: a flow only ever contributes its earliest queued MPDU.
        constexpr std::size_t kWindow = 8;
        constexpr std::size_t kMaxCand = 4;
        Ptr<const WifiMpdu> prev = head->GetOriginal();
        std::unordered_set<uint8_t> seenFlows{ht.flow};
        for (std::size_t scanned = 0; scanned < kWindow && cands.size() < kMaxCand; ++scanned)
        {
            auto nx = queue->PeekFirstAvailable(j, prev);
            if (!nx)
            {
                break;
            }
            prev = nx;
            FlowTag t;
            if (nx->HasSeqNoAssigned() || !nx->GetInFlightLinkIds().empty() || nx->IsFragment() ||
                !nx->GetHeader().IsQosData() || !GetTag(nx->GetPacket(), t) ||
                !seenFlows.insert(t.flow).second)
            {
                continue;
            }
            cands.push_back(nx);
            tags.push_back(t);
        }
        G.decisions++;
        if (cands.size() < 2)
        {
            G.decNoOtherCand++;
            return out;
        }

        const double now = NowMs();
        // link j is busy until its in-flight PSDU is predicted to complete (size known at its start)
        const double busyJ = std::max(now,
                                      G.lastPsduStartMs[j] + G.est[j].Predict(G.lastPsduBits[j]));
        std::vector<sasp::Candidate> c;
        double tJ = busyJ;
        for (std::size_t i = 0; i < cands.size(); ++i)
        {
            sasp::Candidate cc;
            cc.flow = tags[i].flow;
            cc.weight = G.weight.count(cc.flow) ? G.weight[cc.flow] : 1.0;
            const double bits = cands[i]->GetSize() * 8.0;
            if (i == 0)
            {
                cc.predT = now + G.est[k].Predict(bits); // head is sent now on link k
            }
            else
            {
                tJ += G.est[j].Predict(bits); // others are served sequentially by link j
                cc.predT = tJ;
            }
            c.push_back(cc);
        }
        const double sigmaPair = std::sqrt(G.est[k].var + G.est[j].var);
        const auto dMean = sasp::Decide(sasp::Mode::MEAN_ONLY, c, sigmaPair);
        const auto dFull = sasp::Decide(sasp::Mode::FULL, c, sigmaPair);
        sasp::Decision dApplied;
        if (G.mode == sasp::Mode::MEAN_ONLY)
        {
            dApplied = dMean;
        }
        else if (G.mode == sasp::Mode::FULL)
        {
            dApplied = dFull;
        }

        bool multi = false;
        for (std::size_t i = 1; i < c.size(); ++i)
        {
            multi = multi || c[i].flow != c[0].flow;
        }
        if (multi)
        {
            G.decMultiFlow++;
            (c.size() == 2 ? G.decPairwise : G.decGe3)++;
            if (dMean.reserve != dFull.reserve)
            {
                G.decFullNeMean++;
            }
        }
        for (int idx : dApplied.reserve)
        {
            out.push_back(cands[idx]);
        }
        if (!out.empty())
        {
            G.decReserveApplied++;
            for (int idx : dApplied.reserve)
            {
                auto& r = G.tx[Key(tags[idx].flow, tags[idx].seq)];
                r.reserved = true;
                r.reserveMs = now;
                G.reservedMpdus++;
            }
        }
        G.decWallUs += std::chrono::duration<double, std::micro>(clk::now() - w0).count();
        if (G.logDecisions && multi)
        {
            std::ostringstream o;
            o << std::setprecision(9) << now << "," << +k << "," << c.size() << ",";
            for (std::size_t i = 0; i < c.size(); ++i)
            {
                o << (i ? "|" : "") << c[i].flow;
            }
            o << ",";
            for (std::size_t i = 0; i < c.size(); ++i)
            {
                o << (i ? "|" : "") << c[i].predT;
            }
            o << "," << G.est[k].mean << "," << G.est[k].var << "," << G.est[j].mean << ","
              << G.est[j].var << "," << dFull.uStar << "," << dFull.deltaMu << ","
              << (dMean.reserve.empty() ? 0 : 1) << "," << (dFull.reserve.empty() ? 0 : 1) << ","
              << dApplied.reserve.size() << "," << dApplied.reason << "," << G.est[k].n << ","
              << G.est[j].n << ",";
            for (std::size_t i = 0; i < tags.size(); ++i)
            {
                o << (i ? "|" : "") << +tags[i].flow << ":" << tags[i].seq;
            }
            o << "," << dMean.reserve.size() << "," << dFull.reserve.size();
            G.decLog.push_back(o.str());
        }
        return out;
    }
};

double
Quantile(std::vector<double> v, double q)
{
    if (v.empty())
    {
        return 0;
    }
    std::sort(v.begin(), v.end());
    std::size_t idx = static_cast<std::size_t>(std::ceil(q * v.size()));
    idx = idx == 0 ? 0 : idx - 1;
    return v[std::min(idx, v.size() - 1)];
}

double
Mean(const std::vector<double>& v)
{
    return v.empty() ? 0 : std::accumulate(v.begin(), v.end(), 0.0) / v.size();
}

double
Stdv(const std::vector<double>& v)
{
    if (v.size() < 2)
    {
        return 0.0;
    }
    const double m = Mean(v);
    double s = 0;
    for (double x : v)
    {
        s += (x - m) * (x - m);
    }
    return std::sqrt(s / (v.size() - 1));
}

std::string
F(double v)
{
    std::ostringstream o;
    o << std::setprecision(9) << v;
    return o.str();
}

} // namespace

int
main(int argc, char* argv[])
{
    uint32_t seed = 1;
    uint32_t runId = 0;
    int schedulerMode = 0;
    std::string cond = "custom", load = "NA";
    double mcs0 = 7, mcs1 = 7, width0 = 20, width1 = 20, rss0 = -55, rss1 = -55;
    double bulkMbps = 5.0;
    double lsMeanIntervalMs = 8.0;
    uint32_t lsSize = 200, bulkSize = 1200;
    double weightRatio = 10.0;
    double simTime = 10.0, warmup = 0.5, drain = 0.3;
    uint32_t maxAmpdu = 6000;
    std::string csvOutput, decisionLog, scriptFile, traceOut, tag = "";
    uint32_t disableHook = 0;

    CommandLine cmd(__FILE__);
    cmd.AddValue("seed", "RngSeed", seed);
    cmd.AddValue("runId", "metadata run id", runId);
    cmd.AddValue("scheduler", "0 FIFO, 1 MeanOnly, 2 FullSASP", schedulerMode);
    cmd.AddValue("cond", "asymmetry condition label (metadata)", cond);
    cmd.AddValue("load", "load label (metadata)", load);
    cmd.AddValue("mcs0", "EHT MCS on link 0", mcs0);
    cmd.AddValue("mcs1", "EHT MCS on link 1", mcs1);
    cmd.AddValue("width0", "channel width link 0 (MHz)", width0);
    cmd.AddValue("width1", "channel width link 1 (MHz)", width1);
    cmd.AddValue("rss0", "fixed RSS link 0 (dBm)", rss0);
    cmd.AddValue("rss1", "fixed RSS link 1 (dBm)", rss1);
    cmd.AddValue("bulkMbps", "bulk offered load (Mbps)", bulkMbps);
    cmd.AddValue("lsMeanIntervalMs", "mean Poisson interval of LS flow (ms)", lsMeanIntervalMs);
    cmd.AddValue("lsSize", "LS payload bytes", lsSize);
    cmd.AddValue("bulkSize", "bulk payload bytes", bulkSize);
    cmd.AddValue("weightRatio", "w_LS / w_bulk", weightRatio);
    cmd.AddValue("simTime", "simulation time (s)", simTime);
    cmd.AddValue("warmup", "metrics warm-up (s)", warmup);
    cmd.AddValue("drain", "traffic-off drain before end (s)", drain);
    cmd.AddValue("maxAmpdu", "BE max A-MPDU size (bytes)", maxAmpdu);
    cmd.AddValue("csvOutput", "append one result row here", csvOutput);
    cmd.AddValue("decisionLog", "write per-decision log here", decisionLog);
    cmd.AddValue("script", "scripted traffic csv: t_s,flow,size (replaces random traffic)", scriptFile);
    cmd.AddValue("disableHook", "1 = do not install the reservation hook (test control)", disableHook);
    cmd.AddValue("traceOut", "per-packet trace csv (written for any run if set)", traceOut);
    cmd.AddValue("buildId", "build/patch identifier (metadata)", tag);
    cmd.Parse(argc, argv);

    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(1); // fixed: pairing across arms is by seed, streams are explicit

    G = Globals();
    G.mode = static_cast<sasp::Mode>(schedulerMode);
    G.weight[1] = weightRatio;
    G.weight[2] = 1.0;
    G.weight[3] = 1.0;
    G.logDecisions = !decisionLog.empty();

    Config::SetDefault("ns3::WifiMac::BE_MaxAmpduSize", UintegerValue(maxAmpdu));

    NodeContainer apNode, staNode;
    apNode.Create(1);
    staNode.Create(1);

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211be);
    const double mcsv[2] = {mcs0, mcs1};
    const double wv[2] = {width0, width1};
    const double rssv[2] = {rss0, rss1};
    const char* band[2] = {"BAND_5GHZ", "BAND_6GHZ"};
    for (uint8_t l = 0; l < 2; ++l)
    {
        wifi.SetRemoteStationManager(
            l,
            "ns3::ConstantRateWifiManager",
            "DataMode",
            StringValue("EhtMcs" + std::to_string(static_cast<int>(mcsv[l]))),
            "ControlMode",
            StringValue("OfdmRate6Mbps"));
    }
    SpectrumWifiPhyHelper phy(2);
    for (uint8_t l = 0; l < 2; ++l)
    {
        std::ostringstream cs;
        cs << "{0, " << static_cast<int>(wv[l]) << ", " << band[l] << ", 0}";
        phy.Set(l, "ChannelSettings", StringValue(cs.str()));
        auto ch = CreateObject<MultiModelSpectrumChannel>();
        auto loss = CreateObject<FixedRssLossModel>();
        loss->SetRss(rssv[l]);
        ch->AddPropagationLossModel(loss);
        phy.AddChannel(ch, l == 0 ? WIFI_SPECTRUM_5_GHZ : WIFI_SPECTRUM_6_GHZ);
    }

    Ssid ssid("sasp-mlo");
    WifiMacHelper mac;
    mac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(ssid));
    NetDeviceContainer staDevs = wifi.Install(phy, mac, staNode);
    mac.SetType("ns3::ApWifiMac",
                "EnableBeaconJitter",
                BooleanValue(false),
                "BeaconGeneration",
                BooleanValue(false),
                "Ssid",
                SsidValue(ssid));
    NetDeviceContainer apDevs = wifi.Install(phy, mac, apNode);
    auto apDev = DynamicCast<WifiNetDevice>(apDevs.Get(0));
    auto staDev = DynamicCast<WifiNetDevice>(staDevs.Get(0));

    // explicit random streams: device/PHY/MAC streams use the same ids in every arm; the
    // application streams (101,102) are separate from the device streams.
    WifiHelper::AssignStreams(apDevs, 1000);
    WifiHelper::AssignStreams(staDevs, 2000);

    MobilityHelper mob;
    auto pos = CreateObject<ListPositionAllocator>();
    pos->Add(Vector(0, 0, 0));
    pos->Add(Vector(1, 0, 0));
    mob.SetPositionAllocator(pos);
    mob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mob.Install(apNode);
    mob.Install(staNode);

    WifiStaticSetupHelper::SetStaticAssociation(apDev, staDevs);
    WifiStaticSetupHelper::SetStaticBlockAck(apDev, staDevs, {0});

    InternetStackHelper inet;
    inet.Install(apNode);
    inet.Install(staNode);
    Ipv4AddressHelper ip;
    ip.SetBase("192.168.7.0", "255.255.255.0");
    ip.Assign(apDevs);
    auto staIf = ip.Assign(staDevs);
    const Ipv4Address staIp = staIf.GetAddress(0);

    // ---- estimator initialisation from KNOWN CONFIGURATION only (identical for all arms)
    for (int l = 0; l < 2; ++l)
    {
        WifiMode m("EhtMcs" + std::to_string(static_cast<int>(mcsv[l])));
        const double rate = m.GetDataRate(MHz_u{wv[l]}, NanoSeconds(800), 1); // bps
        G.est[l].Init(rate, /*overhead ms*/ 0.15, /*std ms*/ 0.05, /*floor std ms*/ 0.02);
    }

    // ---- SASP hook on the AP BE queue (TID 0 shares AC_BE)
    Glue glue;
    auto apMac = DynamicCast<ApWifiMac>(apDev->GetMac());
    Ptr<QosTxop> be = apMac->GetQosTxop(AC_BE);
    if (!disableHook)
    {
        be->SetSequenceReservationCallback(MakeCallback(&Glue::Reserve, &glue));
    }

    // ---- observation
    apMac->TraceConnectWithoutContext("AckedMpdu", MakeCallback(&OnAcked));
    apMac->TraceConnectWithoutContext("NAckedMpdu", MakeCallback(&OnNacked));
    apMac->TraceConnectWithoutContext("DroppedMpdu", MakeCallback(&OnDropped));
    for (uint8_t l = 0; l < 2; ++l)
    {
        apDev->GetPhy(l)->TraceConnectWithoutContext("PhyTxPsduBegin",
                                                     MakeBoundCallback(&OnPsduTx, l));
    }
    auto& obs = RecipientBlockAckAgreement::GetObserver();
    obs.onInsert = RxInsert;
    obs.onRelease = RxRelease;
    obs.onForcedAdvance = RxForced;

    // ---- traffic
    PacketSinkHelper s1("ns3::UdpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), 5001));
    PacketSinkHelper s2("ns3::UdpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), 5002));
    auto sa1 = s1.Install(staNode.Get(0));
    auto sa2 = s2.Install(staNode.Get(0));
    PacketSinkHelper s3("ns3::UdpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), 5003));
    auto sa3 = s3.Install(staNode.Get(0));
    sa3.Get(0)->TraceConnectWithoutContext("Rx", MakeCallback(&OnSinkRx));
    sa3.Start(Seconds(0));
    sa1.Get(0)->TraceConnectWithoutContext("Rx", MakeCallback(&OnSinkRx));
    sa2.Get(0)->TraceConnectWithoutContext("Rx", MakeCallback(&OnSinkRx));
    sa1.Start(Seconds(0));
    sa2.Start(Seconds(0));

    const double trafficStop = simTime - drain;
    auto mkSock = [&]() { return Socket::CreateSocket(apNode.Get(0), UdpSocketFactory::GetTypeId()); };
    if (scriptFile.empty())
    {
        auto ls = CreateObject<TrafficApp>();
        auto bk = CreateObject<TrafficApp>();
        ls->Setup(mkSock(),
                  InetSocketAddress(staIp, 5001),
                  1,
                  lsSize,
                  TrafficApp::POISSON,
                  lsMeanIntervalMs * 1e-3,
                  /*stream*/ 101,
                  0.1,
                  trafficStop);
        bk->Setup(mkSock(),
                  InetSocketAddress(staIp, 5002),
                  2,
                  bulkSize,
                  TrafficApp::CBR,
                  bulkMbps * 1e6,
                  /*stream*/ 102,
                  0.1,
                  trafficStop);
        apNode.Get(0)->AddApplication(ls);
        apNode.Get(0)->AddApplication(bk);
        ls->SetStartTime(Seconds(0.0));
        bk->SetStartTime(Seconds(0.0));
    }
    else
    {
        auto lsS = CreateObject<TrafficApp>();
        auto bkS = CreateObject<TrafficApp>();
        lsS->Setup(mkSock(), InetSocketAddress(staIp, 5001), 1, lsSize, TrafficApp::SCRIPT, 0, 103, 0, simTime);
        bkS->Setup(mkSock(), InetSocketAddress(staIp, 5002), 2, bulkSize, TrafficApp::SCRIPT, 0, 104, 0, simTime);
        auto f3S = CreateObject<TrafficApp>();
        f3S->Setup(mkSock(), InetSocketAddress(staIp, 5003), 3, lsSize, TrafficApp::SCRIPT, 0, 105, 0, simTime);
        std::ifstream f(scriptFile);
        std::string line;
        while (std::getline(f, line))
        {
            if (line.empty() || line[0] == '#')
            {
                continue;
            }
            double t;
            int fl;
            uint32_t sz;
            char c;
            std::istringstream ss(line);
            ss >> t >> c >> fl >> c >> sz;
            (fl == 1 ? lsS : (fl == 2 ? bkS : f3S))->AddScripted(t, sz);
        }
        // Scripted scenarios need ARP resolved before t=0.5 s: ns-3 drops all but the first 3
        // packets queued behind an unresolved ARP entry. Send ONE untagged priming packet
        // (not an application packet: carries no FlowTag, so it is excluded from all metrics).
        auto primeSock = mkSock();
        primeSock->Connect(InetSocketAddress(staIp, 5001));
        Simulator::Schedule(Seconds(0.05), [primeSock]() { primeSock->Send(Create<Packet>(20)); });
        apNode.Get(0)->AddApplication(lsS);
        apNode.Get(0)->AddApplication(bkS);
        apNode.Get(0)->AddApplication(f3S);
        lsS->SetStartTime(Seconds(0));
        bkS->SetStartTime(Seconds(0));
        f3S->SetStartTime(Seconds(0));
    }

    Simulator::Stop(Seconds(simTime));
    Simulator::Run();
    Simulator::Destroy();
    RecipientBlockAckAgreement::GetObserver() = {};

    // ======================================================== metrics
    const bool scripted = !scriptFile.empty();
    const double winLo = scripted ? 0.0 : warmup * 1e3;
    const double winHi = scripted ? simTime * 1e3 : trafficStop * 1e3;
    std::vector<double> lsDelay, lsCross, lsWithin, lsForced, lsTotal, bulkTotal, lsCrossAnyBulk,
        lsQueueWait;
    uint64_t lsSent = 0, lsRcvd = 0, bkSent = 0, bkRcvd = 0;
    double lsBytes = 0, bkBytes = 0;
    uint64_t lsWaiting = 0, lsCrossN = 0;

    std::vector<uint64_t> insIdxOf(G.insertOrder.size());
    for (std::size_t i = 0; i < G.insertOrder.size(); ++i)
    {
        insIdxOf[i] = G.rx[G.insertOrder[i]].insIdx;
    }

    for (int fl = 1; fl <= 2; ++fl)
    {
        for (const auto& [k, a] : G.app[fl])
        {
            if (a.genMs < winLo || a.genMs > winHi)
            {
                continue;
            }
            (fl == 1 ? lsSent : bkSent)++;
            if (!a.delivered)
            {
                continue;
            }
            if (fl == 1)
            {
                lsRcvd++;
                lsBytes += a.size;
                lsDelay.push_back(a.sinkMs - a.genMs);
            }
            else
            {
                bkRcvd++;
                bkBytes += a.size;
            }
            // reorder wait + attribution
            auto rit = G.rx.find(k);
            double wait = 0, cross = 0, within = 0, forcedW = 0, crossAny = 0;
            if (rit != G.rx.end() && rit->second.released)
            {
                const auto& r = rit->second;
                wait = std::max(0.0, r.relMs - r.insMs);
                if (wait > 1e-9)
                {
                    if (r.forced)
                    {
                        forcedW = wait;
                    }
                    else
                    {
                        // binding blocker: last-inserted lower-SN MPDU between insert and release
                        uint64_t blocker = 0;
                        bool found = false;
                        bool anyBulk = false;
                        std::size_t lo = std::upper_bound(insIdxOf.begin(), insIdxOf.end(), r.insIdx) -
                                         insIdxOf.begin();
                        for (std::size_t q = lo; q < insIdxOf.size() && insIdxOf[q] < r.relIdx; ++q)
                        {
                            const auto& o = G.rx[G.insertOrder[q]];
                            if (o.ext < r.ext)
                            {
                                blocker = G.insertOrder[q];
                                found = true;
                                anyBulk = anyBulk || ((blocker >> 32) != static_cast<uint64_t>(fl));
                            }
                        }
                        if (found)
                        {
                            if ((blocker >> 32) == static_cast<uint64_t>(fl))
                            {
                                within = wait;
                            }
                            else
                            {
                                cross = wait;
                            }
                            if (anyBulk)
                            {
                                crossAny = wait;
                            }
                        }
                    }
                }
            }
            if (fl == 1)
            {
                lsTotal.push_back(wait);
                lsCross.push_back(cross);
                lsWithin.push_back(within);
                lsForced.push_back(forcedW);
                lsCrossAnyBulk.push_back(crossAny);
                lsWaiting += (wait > 1e-9);
                lsCrossN += (cross > 1e-9);
                auto t = G.tx.find(k);
                if (t != G.tx.end() && t->second.firstTxMs >= 0)
                {
                    lsQueueWait.push_back(t->second.firstTxMs - a.genMs);
                }
            }
            else
            {
                bulkTotal.push_back(wait);
            }
        }
    }

    // tx audits
    uint64_t retries = 0, uniqueTx = 0, intraFlowInv = 0, snDup = 0;
    {
        std::map<int64_t, int> extCount;
        for (int fl = 1; fl <= 2; ++fl)
        {
            int64_t prevExt = INT64_MIN;
            for (const auto& [k, a] : G.app[fl])
            {
                auto t = G.tx.find(k);
                if (t == G.tx.end() || t->second.snExt == INT64_MIN)
                {
                    continue;
                }
                if (t->second.snExt <= prevExt)
                {
                    intraFlowInv++;
                }
                prevExt = std::max(prevExt, t->second.snExt);
            }
        }
        for (const auto& [k, t] : G.tx)
        {
            if (t.attempts > 0)
            {
                uniqueTx++;
                retries += t.attempts - 1;
                if (extCount[t.snExt]++ > 0)
                {
                    snDup++;
                }
            }
        }
    }
    std::vector<double> holds;
    for (const auto& [k, t] : G.tx)
    {
        if (t.reserved && t.holdMs >= 0)
        {
            holds.push_back(t.holdMs);
        }
    }

    const double win = scripted ? simTime : trafficStop - warmup;
    const double lsOfferedBps = lsSent ? lsSent * lsSize * 8.0 / win : 1;
    const double bkOfferedBps = bkSent ? bkSent * bulkSize * 8.0 / win : 1;
    const double x1 = (lsBytes * 8.0 / win) / lsOfferedBps;
    const double x2 = (bkBytes * 8.0 / win) / bkOfferedBps;
    const double jain = (x1 + x2) * (x1 + x2) / (2.0 * (x1 * x1 + x2 * x2) + 1e-18);

    const std::string header =
        "run_id,seed,scheduler,cond,load,mcs0,mcs1,width0,width1,rss0,rss1,bulk_mbps,"
        "ls_interval_ms,weight_ratio,sim_time_s,max_ampdu,build_id,"
        "ls_sent,ls_rcvd,bulk_sent,bulk_rcvd,ls_pdr,bulk_pdr,"
        "cross_wait_ms,within_wait_ms,forced_wait_ms,total_wait_ms,cross_wait_anybulk_ms,"
        "ls_frac_waiting,ls_frac_cross,bulk_total_wait_ms,"
        "ls_delay_median_ms,ls_delay_p95_ms,ls_delay_p99_ms,ls_delay_mean_ms,ls_queue_wait_ms,"
        "ls_goodput_kbps,bulk_goodput_mbps,total_goodput_mbps,jain,min_norm_tput,"
        "retries,nacked,dropped,unique_tx,"
        "buf_occ_mean,buf_occ_max,forced_adv_events,forced_adv_slots,forced_released,"
        "link0_comp_median_ms,link1_comp_median_ms,link0_comp_mean_ms,link1_comp_mean_ms,"
        "link0_comp_std_ms,link1_comp_std_ms,link0_n,link1_n,link0_psdu_mpdus,link1_psdu_mpdus,"
        "decisions,dec_multiflow,dec_pairwise,dec_ge3,dec_reserve_applied,dec_full_ne_mean,"
        "reserved_mpdus,reserve_hold_mean_ms,reserve_hold_max_ms,dec_wall_us_mean,"
        "audit_sn_changed,audit_intra_flow_inv,audit_sn_dup,audit_untagged_tx,"
        "est0_final_mean,est1_final_mean,est0_final_std,est1_final_std\n";

    std::ostringstream row;
    row << runId << "," << seed << "," << schedulerMode << "," << cond << "," << load << "," << mcs0
        << "," << mcs1 << "," << width0 << "," << width1 << "," << rss0 << "," << rss1 << ","
        << bulkMbps << "," << lsMeanIntervalMs << "," << weightRatio << "," << simTime << ","
        << maxAmpdu << "," << tag << "," << lsSent << "," << lsRcvd << "," << bkSent << ","
        << bkRcvd << "," << F(lsSent ? 100.0 * lsRcvd / lsSent : 0) << ","
        << F(bkSent ? 100.0 * bkRcvd / bkSent : 0) << "," << F(Mean(lsCross)) << ","
        << F(Mean(lsWithin)) << "," << F(Mean(lsForced)) << "," << F(Mean(lsTotal)) << ","
        << F(Mean(lsCrossAnyBulk)) << "," << F(lsRcvd ? double(lsWaiting) / lsRcvd : 0) << ","
        << F(lsRcvd ? double(lsCrossN) / lsRcvd : 0) << "," << F(Mean(bulkTotal)) << ","
        << F(Quantile(lsDelay, 0.5)) << "," << F(Quantile(lsDelay, 0.95)) << ","
        << F(Quantile(lsDelay, 0.99)) << "," << F(Mean(lsDelay)) << "," << F(Mean(lsQueueWait))
        << "," << F(lsBytes * 8.0 / win / 1e3) << "," << F(bkBytes * 8.0 / win / 1e6) << ","
        << F((lsBytes + bkBytes) * 8.0 / win / 1e6) << "," << F(jain) << ","
        << F(std::min(x1, x2)) << "," << retries << "," << G.nacked << "," << G.dropped << ","
        << uniqueTx << "," << F(G.occT > 0 ? G.occArea / G.occT : 0) << "," << F(G.occMax) << ","
        << G.forcedAdvanceEvents << "," << G.forcedAdvanceSlots << "," << G.forcedReleased << ","
        << F(Quantile(G.comp[0], 0.5)) << "," << F(Quantile(G.comp[1], 0.5)) << ","
        << F(Mean(G.comp[0])) << "," << F(Mean(G.comp[1])) << "," << F(Stdv(G.comp[0])) << ","
        << F(Stdv(G.comp[1])) << "," << G.comp[0].size() << "," << G.comp[1].size() << ","
        << F(Mean(G.psduSize[0])) << "," << F(Mean(G.psduSize[1])) << "," << G.decisions << ","
        << G.decMultiFlow << "," << G.decPairwise << "," << G.decGe3 << "," << G.decReserveApplied
        << "," << G.decFullNeMean << "," << G.reservedMpdus << "," << F(Mean(holds)) << ","
        << F(holds.empty() ? 0 : *std::max_element(holds.begin(), holds.end())) << ","
        << F(G.decisions ? G.decWallUs / G.decisions : 0) << "," << G.snChangedAfterCommit << ","
        << intraFlowInv << "," << snDup << "," << G.untaggedTx << "," << F(G.est[0].mean) << ","
        << F(G.est[1].mean) << "," << F(G.est[0].Std()) << "," << F(G.est[1].Std()) << "\n";

    if (!csvOutput.empty())
    {
        bool exists = std::ifstream(csvOutput).good();
        std::ofstream o(csvOutput, std::ios::app);
        if (!exists)
        {
            o << header;
        }
        o << row.str();
    }
    else
    {
        std::cout << header << row.str();
    }
    if (!decisionLog.empty())
    {
        std::ofstream o(decisionLog);
        o << "t_ms,link,n_cand,flows,pred_T_ms,mu_k,var_k,mu_j,var_j,u_star,delta_mu,"
             "would_mean_reserve,would_full_reserve,applied_n,reason,n_est_k,n_est_j,ids,"
             "n_mean_reserve,n_full_reserve\n";
        for (auto& l : G.decLog)
        {
            o << l << "\n";
        }
    }
    if (!traceOut.empty())
    {
        // per-packet trace for deterministic regression tests / audits
        std::ofstream o(traceOut);
        o << std::setprecision(12);
        o << "flow,app_seq,sn,link,first_tx_ms,rx_insert_ms,rx_release_ms,sink_ms,attempts,reserved\n";
        for (int fl = 1; fl <= 3; ++fl)
        {
            for (const auto& [k, a] : G.app[fl])
            {
                auto t = G.tx.find(k);
                auto r = G.rx.find(k);
                o << fl << "," << (k & 0xffffffff) << "," << (t != G.tx.end() ? t->second.sn : -1)
                  << "," << (t != G.tx.end() ? t->second.link : -1) << ","
                  << (t != G.tx.end() ? t->second.firstTxMs : -1) << ","
                  << (r != G.rx.end() ? r->second.insMs : -1) << ","
                  << (r != G.rx.end() ? r->second.relMs : -1) << "," << a.sinkMs << ","
                  << (t != G.tx.end() ? t->second.attempts : 0) << ","
                  << (t != G.tx.end() ? (t->second.reserved ? 1 : 0) : 0) << "\n";
            }
        }
    }
    return 0;
}
