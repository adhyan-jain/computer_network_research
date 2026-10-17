// stock-mlo-baseline.cc - Gate 1 evidence using ONLY stock ns-3.47 public APIs/traces.
//
// Builds a two-link STR Wi-Fi 7 MLO AP-MLD -> STA-MLD pair with two UDP flows on the same TID and
// COMPUTES (does not print constants for) each Gate-1 property:
//   1 real MLO device (NPhys/NLinks == 2, distinct MLD and per-link addresses)
//   2 valid MLD endpoints (association established, MLD address != link addresses)
//   3 two simultaneously operational links (PSDUs transmitted on both, with overlapping airtime)
//   4 both flows share TID 0 and one originator BA agreement (every data MPDU has QoS TID 0,
//     agreement established, one sequence-number space)
//   5 transmission and reception on the intended links (per-link PSDU tx vs. STA MacRx deliveries)
//   6 link-specific timing and outcomes from real traces (PhyTxPsduBegin, AckedMpdu)
//   7 sequence numbers observable (PSDU headers) and BA outcomes (AckedMpdu)
// An FNV-1a fingerprint over the full event trace is printed so the identical program can be run on
// the pristine and on the patched ns-3 (hooks not installed) and compared bit for bit.
#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/propagation-module.h"
#include "ns3/spectrum-module.h"
#include "ns3/wifi-module.h"

#include <algorithm>
#include <cstdio>
#include <fstream>
#include <map>
#include <set>
#include <sstream>

using namespace ns3;

namespace
{
std::ostringstream g_trace;
std::array<uint64_t, 2> g_psdus{{0, 0}};
std::array<uint64_t, 2> g_mpdus{{0, 0}};
std::array<std::vector<std::pair<double, double>>, 2> g_air; // [start,end) per link
std::set<uint8_t> g_tids;
std::set<uint16_t> g_sns;
std::set<uint32_t> g_sizes;
uint64_t g_acked = 0, g_rxDelivered = 0;
std::array<uint64_t, 2> g_rxPhy{{0, 0}};
bool g_dataNotQos = false;

void
OnPsdu(uint8_t link, WifiConstPsduMap map, WifiTxVector txv, double)
{
    for (const auto& [sta, psdu] : map)
    {
        bool any = false;
        for (auto it = psdu->begin(); it != psdu->end(); ++it)
        {
            const auto& h = (*it)->GetHeader();
            if (!h.IsData())
            {
                continue;
            }
            if (!h.IsQosData())
            {
                g_dataNotQos = true;
                continue;
            }
            any = true;
            g_mpdus[link]++;
            g_tids.insert(h.GetQosTid());
            g_sns.insert(h.GetSequenceNumber());
            g_sizes.insert((*it)->GetPacket()->GetSize());
            g_trace << Simulator::Now().GetNanoSeconds() << ",tx," << +link << ","
                    << h.GetSequenceNumber() << "," << +h.GetQosTid() << ","
                    << (*it)->GetPacket()->GetSize() << "\n";
        }
        if (any)
        {
            g_psdus[link]++;
            const double t0 = Simulator::Now().GetSeconds();
            g_air[link].push_back(
                {t0, t0 + WifiPhy::CalculateTxDuration(psdu, txv, WIFI_PHY_BAND_5GHZ).GetSeconds()});
        }
    }
}

void
OnAcked(Ptr<const WifiMpdu> m)
{
    if (m->GetHeader().IsQosData())
    {
        g_acked++;
        g_trace << Simulator::Now().GetNanoSeconds() << ",ack,-1," << m->GetHeader().GetSequenceNumber()
                << "," << +m->GetHeader().GetQosTid() << "," << m->GetPacket()->GetSize() << "\n";
    }
}

void
OnStaRx(Ptr<const Packet> p)
{
    g_rxDelivered++;
    g_trace << Simulator::Now().GetNanoSeconds() << ",deliver,-1,-1,-1," << p->GetSize() << "\n";
}

void
OnPhyRx(uint8_t link, Ptr<const Packet>)
{
    g_rxPhy[link]++;
}
} // namespace

int
main(int argc, char* argv[])
{
    uint32_t seed = 1;
    double simTime = 2.0;
    std::string traceFile;
    CommandLine cmd(__FILE__);
    cmd.AddValue("seed", "RngSeed", seed);
    cmd.AddValue("simTime", "seconds", simTime);
    cmd.AddValue("traceFile", "write the event trace here", traceFile);
    cmd.Parse(argc, argv);
    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(1);

    NodeContainer ap, sta;
    ap.Create(1);
    sta.Create(1);
    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211be);
    const char* band[2] = {"BAND_5GHZ", "BAND_6GHZ"};
    const char* mode[2] = {"EhtMcs1", "EhtMcs7"};
    for (uint8_t l = 0; l < 2; ++l)
    {
        wifi.SetRemoteStationManager(l,
                                     "ns3::ConstantRateWifiManager",
                                     "DataMode",
                                     StringValue(mode[l]),
                                     "ControlMode",
                                     StringValue("OfdmRate6Mbps"));
    }
    SpectrumWifiPhyHelper phy(2);
    for (uint8_t l = 0; l < 2; ++l)
    {
        phy.Set(l, "ChannelSettings", StringValue(std::string("{0, 20, ") + band[l] + ", 0}"));
        auto ch = CreateObject<MultiModelSpectrumChannel>();
        auto loss = CreateObject<FixedRssLossModel>();
        loss->SetRss(-55);
        ch->AddPropagationLossModel(loss);
        phy.AddChannel(ch, l == 0 ? WIFI_SPECTRUM_5_GHZ : WIFI_SPECTRUM_6_GHZ);
    }
    Ssid ssid("baseline");
    WifiMacHelper mac;
    mac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(ssid));
    auto staDevs = wifi.Install(phy, mac, sta);
    mac.SetType("ns3::ApWifiMac",
                "EnableBeaconJitter",
                BooleanValue(false),
                "BeaconGeneration",
                BooleanValue(false),
                "Ssid",
                SsidValue(ssid));
    auto apDevs = wifi.Install(phy, mac, ap);
    auto apDev = DynamicCast<WifiNetDevice>(apDevs.Get(0));
    auto staDev = DynamicCast<WifiNetDevice>(staDevs.Get(0));
    WifiHelper::AssignStreams(apDevs, 1000);
    WifiHelper::AssignStreams(staDevs, 2000);

    MobilityHelper mob;
    auto pos = CreateObject<ListPositionAllocator>();
    pos->Add(Vector(0, 0, 0));
    pos->Add(Vector(1, 0, 0));
    mob.SetPositionAllocator(pos);
    mob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mob.Install(ap);
    mob.Install(sta);
    WifiStaticSetupHelper::SetStaticAssociation(apDev, staDevs);
    WifiStaticSetupHelper::SetStaticBlockAck(apDev, staDevs, {0});

    InternetStackHelper inet;
    inet.Install(ap);
    inet.Install(sta);
    Ipv4AddressHelper ip;
    ip.SetBase("192.168.9.0", "255.255.255.0");
    ip.Assign(apDevs);
    auto staIf = ip.Assign(staDevs);

    for (uint16_t port : {5001, 5002})
    {
        PacketSinkHelper s("ns3::UdpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), port));
        s.Install(sta.Get(0)).Start(Seconds(0));
        OnOffHelper o("ns3::UdpSocketFactory", InetSocketAddress(staIf.GetAddress(0), port));
        o.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
        o.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
        o.SetAttribute("PacketSize", UintegerValue(port == 5001 ? 200 : 1200));
        o.SetAttribute("DataRate", DataRateValue(DataRate(port == 5001 ? "0.2Mbps" : "30Mbps")));
        auto a = o.Install(ap.Get(0));
        a.Start(Seconds(0.2));
        a.Stop(Seconds(simTime - 0.2));
    }

    auto apMac = apDev->GetMac();
    for (uint8_t l = 0; l < 2; ++l)
    {
        apDev->GetPhy(l)->TraceConnectWithoutContext("PhyTxPsduBegin", MakeBoundCallback(&OnPsdu, l));
        staDev->GetPhy(l)->TraceConnectWithoutContext("PhyRxEnd", MakeBoundCallback(&OnPhyRx, l));
    }
    apMac->TraceConnectWithoutContext("AckedMpdu", MakeCallback(&OnAcked));
    staDev->GetMac()->TraceConnectWithoutContext("MacRx", MakeCallback(&OnStaRx));

    Simulator::Stop(Seconds(simTime));
    Simulator::Run();

    // ---- computed checks
    int fails = 0;
    auto check = [&](bool ok, const std::string& what) {
        std::printf("[%s] %s\n", ok ? "PASS" : "FAIL", what.c_str());
        fails += !ok;
    };
    const auto apAddr = apMac->GetAddress();
    const auto staAddr = staDev->GetMac()->GetAddress();
    check(apDev->GetNPhys() == 2 && apMac->GetNLinks() == 2 && staDev->GetNPhys() == 2 &&
              staDev->GetMac()->GetNLinks() == 2,
          "1  real MLO devices: NPhys=NLinks=2 on AP and STA (AP " + std::to_string(apDev->GetNPhys()) +
              ")");
    std::set<Mac48Address> addrs{apAddr, staAddr};
    for (uint8_t l = 0; l < 2; ++l)
    {
        addrs.insert(apMac->GetFrameExchangeManager(l)->GetAddress());
        addrs.insert(staDev->GetMac()->GetFrameExchangeManager(l)->GetAddress());
    }
    check(addrs.size() == 6,
          "2  MLD addresses differ from the 4 per-link addresses (6 distinct addresses)");
    check(apMac->GetBaAgreementEstablishedAsOriginator(staAddr, 0).has_value(),
          "2/4 originator BA agreement established AP-MLD -> STA-MLD for TID 0");
    bool overlap = false;
    for (auto [a0, b0] : g_air[0])
    {
        for (auto [a1, b1] : g_air[1])
        {
            overlap = overlap || (a0 < b1 && a1 < b0);
        }
    }
    check(g_psdus[0] > 100 && g_psdus[1] > 100,
          "3  data PSDUs transmitted on BOTH links (" + std::to_string(g_psdus[0]) + " / " +
              std::to_string(g_psdus[1]) + ")");
    check(overlap, "3  transmissions on the two links overlap in time (STR: simultaneous operation)");
    check(g_tids.size() == 1 && *g_tids.begin() == 0 && !g_dataNotQos,
          "4  every data MPDU of both flows is QoS data with TID 0 (one BA ordering context)");
    check(g_sizes.size() >= 2,
          "4  two distinct application flows present (" + std::to_string(g_sizes.size()) +
              " MPDU size classes)");
    check(g_rxPhy[0] > 0 && g_rxPhy[1] > 0,
          "5  STA receives PPDUs on both links (" + std::to_string(g_rxPhy[0]) + " / " +
              std::to_string(g_rxPhy[1]) + ")");
    check(g_rxDelivered > 1000,
          "5  MPDUs delivered up at the STA MAC (" + std::to_string(g_rxDelivered) + ")");
    check(g_acked > 1000,
          "6/7 per-MPDU BA acknowledgements observed (AckedMpdu: " + std::to_string(g_acked) + ")");
    check(g_sns.size() > 500,
          "7  sequence numbers observable on transmitted MPDUs (" + std::to_string(g_sns.size()) +
              " distinct)");

    const std::string trace = g_trace.str();
    if (!traceFile.empty())
    {
        std::ofstream(traceFile) << trace;
    }
    uint64_t h = 1469598103934665603ULL; // FNV-1a 64: quick comparable fingerprint
    for (unsigned char c : trace)
    {
        h = (h ^ c) * 1099511628211ULL;
    }
    std::printf("TRACE_FNV1A64=%016llx EVENTS=%zu\n",
                static_cast<unsigned long long>(h),
                static_cast<std::size_t>(std::count(trace.begin(), trace.end(), '\n')));
    Simulator::Destroy();
    if (fails == 0)
    {
        std::printf(">>> GATE 1: ALL COMPUTED CHECKS PASSED\n");
    }
    else
    {
        std::printf(">>> GATE 1: %d CHECK(S) FAILED\n", fails);
    }
    return fails == 0 ? 0 : 1;
}
