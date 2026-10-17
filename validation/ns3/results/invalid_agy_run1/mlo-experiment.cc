#include "sasp-scheduler.h"

#include "ns3/boolean.h"
#include "ns3/command-line.h"
#include "ns3/config.h"
#include "ns3/double.h"
#include "ns3/eht-phy.h"
#include "ns3/internet-stack-helper.h"
#include "ns3/ipv4-address-helper.h"
#include "ns3/log.h"
#include "ns3/mobility-helper.h"
#include "ns3/multi-model-spectrum-channel.h"
#include "ns3/packet-sink-helper.h"
#include "ns3/packet-sink.h"
#include "ns3/spectrum-wifi-helper.h"
#include "ns3/ssid.h"
#include "ns3/string.h"
#include "ns3/uinteger.h"
#include "ns3/wifi-net-device.h"
#include "ns3/wifi-static-setup-helper.h"
#include "ns3/ap-wifi-mac.h"
#include "ns3/sta-wifi-mac.h"
#include "ns3/on-off-helper.h"
#include "ns3/udp-socket-factory.h"
#include "ns3/rng-seed-manager.h"

#include <iostream>
#include <fstream>
#include <vector>
#include <map>
#include <numeric>
#include <cmath>
#include <algorithm>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("MloExperiment");

struct PacketTraceInfo
{
    uint8_t flowId{0};
    uint32_t packetSeq{0};
    Time genTime;
    Time rxTime;
    Time deliverTime;
    uint16_t seqNum{0};
    bool delivered{false};
};

static std::map<std::pair<uint8_t, uint32_t>, PacketTraceInfo> g_packetMap;
static uint64_t g_macRetries = 0;
static uint64_t g_macDrops = 0;
static uint64_t g_link0TxFrames = 0;
static uint64_t g_link1TxFrames = 0;
static uint64_t g_link0RxFrames = 0;
static uint64_t g_link1RxFrames = 0;

void
MacTxTrace(Ptr<const Packet> packet)
{
    MloFlowIdTag tag;
    if (packet->PeekPacketTag(tag))
    {
        auto key = std::make_pair(tag.GetFlowId(), tag.GetPacketSeq());
        if (g_packetMap.find(key) == g_packetMap.end())
        {
            PacketTraceInfo info;
            info.flowId = tag.GetFlowId();
            info.packetSeq = tag.GetPacketSeq();
            info.genTime = MicroSeconds(tag.GetGenTimeUs());
            g_packetMap[key] = info;
        }
    }
}

void
MacRxTrace(Ptr<const Packet> packet)
{
    // Do not overwrite rxTime; rxTime is physical reception time recorded by PhyRxOkTrace
}

void
SinkRxTrace(Ptr<const Packet> packet, const Address& from)
{
    MloFlowIdTag tag;
    if (packet->PeekPacketTag(tag))
    {
        auto key = std::make_pair(tag.GetFlowId(), tag.GetPacketSeq());
        auto it = g_packetMap.find(key);
        if (it != g_packetMap.end())
        {
            it->second.deliverTime = Simulator::Now();
            it->second.delivered = true;
        }
    }
}

void
PhyTxTrace(uint8_t linkId, Ptr<const Packet> packet, double txPowerW)
{
    if (linkId == 0) g_link0TxFrames++;
    else if (linkId == 1) g_link1TxFrames++;
}

void
PhyRxOkTrace(uint8_t linkId, Ptr<const Packet> packet)
{
    if (linkId == 0) g_link0RxFrames++;
    else if (linkId == 1) g_link1RxFrames++;

    if (packet)
    {
        MloFlowIdTag tag;
        if (packet->PeekPacketTag(tag))
        {
            auto key = std::make_pair(tag.GetFlowId(), tag.GetPacketSeq());
            auto it = g_packetMap.find(key);
            if (it != g_packetMap.end())
            {
                if (it->second.rxTime.IsZero())
                {
                    it->second.rxTime = Simulator::Now();
                }
            }
        }
    }
}

void
MacTxDropTrace(Ptr<const Packet> packet)
{
    g_macDrops++;
}

// Custom Application sending packets with MloFlowIdTag attached
class MloTrafficApp : public Application
{
public:
    MloTrafficApp() = default;
    ~MloTrafficApp() override { m_socket = nullptr; }

    void Setup(Ptr<Socket> socket, Address sinkAddress, uint32_t packetSize,
               DataRate dataRate, uint8_t flowId, Time startTime, Time stopTime)
    {
        m_socket = socket;
        m_peer = sinkAddress;
        m_packetSize = packetSize;
        m_dataRate = dataRate;
        m_flowId = flowId;
        m_startTime = startTime;
        m_stopTime = stopTime;
    }

private:
    void StartApplication() override
    {
        m_running = true;
        m_packetSeq = 0;
        m_socket->Bind();
        m_socket->Connect(m_peer);
        SendPacket();
    }

    void StopApplication() override
    {
        m_running = false;
        if (m_sendEvent.IsPending())
        {
            Simulator::Cancel(m_sendEvent);
        }
        if (m_socket)
        {
            m_socket->Close();
        }
    }

    void SendPacket()
    {
        if (!m_running || Simulator::Now() >= m_stopTime)
        {
            return;
        }

        uint32_t seq = m_packetSeq++;
        Ptr<Packet> packet = Create<Packet>(m_packetSize);
        MloFlowIdTag tag;
        tag.SetFlowId(m_flowId);
        tag.SetPacketSeq(seq);
        tag.SetGenTimeUs(Simulator::Now().GetMicroSeconds());
        packet->AddPacketTag(tag);

        auto key = std::make_pair(m_flowId, seq);
        PacketTraceInfo info;
        info.flowId = m_flowId;
        info.packetSeq = seq;
        info.genTime = Simulator::Now();
        g_packetMap[key] = info;

        m_socket->Send(packet);

        Time nextInterval = Seconds(m_packetSize * 8.0 / m_dataRate.GetBitRate());
        m_sendEvent = Simulator::Schedule(nextInterval, &MloTrafficApp::SendPacket, this);
    }

    Ptr<Socket> m_socket{nullptr};
    Address m_peer;
    uint32_t m_packetSize{160};
    DataRate m_dataRate{"1Mbps"};
    uint8_t m_flowId{1};
    Time m_startTime{Seconds(0)};
    Time m_stopTime{Seconds(1)};
    bool m_running{false};
    uint32_t m_packetSeq{0};
    EventId m_sendEvent;
};

int
main(int argc, char* argv[])
{
    uint32_t seed = 1;
    uint32_t run = 1;
    int schedulerMode = 0; // 0=FIFO, 1=MeanOnly, 2=FullSASP
    std::string asymmetry = "A2"; // A0, A1, A2
    std::string offeredLoad = "L2"; // L0, L1, L2
    double weightRatio = 10.0;
    double varianceRatio = 1.0;
    double simulationTime = 2.0;
    std::string csvOutput = "";

    CommandLine cmd(__FILE__);
    cmd.AddValue("seed", "Random seed", seed);
    cmd.AddValue("run", "Run index", run);
    cmd.AddValue("scheduler", "Scheduler: 0=FIFO, 1=MeanOnly, 2=FullSASP", schedulerMode);
    cmd.AddValue("asymmetry", "Asymmetry: A0, A1, A2", asymmetry);
    cmd.AddValue("offeredLoad", "Offered Load: L0, L1, L2", offeredLoad);
    cmd.AddValue("weightRatio", "Priority Weight Ratio w_ls / w_bulk", weightRatio);
    cmd.AddValue("varianceRatio", "Variance Ratio for ablation", varianceRatio);
    cmd.AddValue("simulationTime", "Simulation duration in seconds", simulationTime);
    cmd.AddValue("csvOutput", "Path to append CSV results", csvOutput);
    cmd.Parse(argc, argv);

    // Reset global state
    g_packetMap.clear();
    g_macRetries = 0;
    g_macDrops = 0;
    g_link0TxFrames = 0;
    g_link1TxFrames = 0;
    g_link0RxFrames = 0;
    g_link1RxFrames = 0;

    // Set Random Seed and Run Number
    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(run);

    NodeContainer wifiApNode;
    wifiApNode.Create(1);
    NodeContainer wifiStaNodes;
    wifiStaNodes.Create(1);

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211be);

    const uint8_t nLinks = 2;
    std::array<std::string, nLinks> channelStr;
    std::array<FrequencyRange, nLinks> freqRanges;

    // Configure link PHY parameters based on Asymmetry Level:
    // A0 (Symmetric): Link 0 = EhtMcs7 (5 GHz, 20 MHz), Link 1 = EhtMcs7 (6 GHz, 20 MHz), ratio ~1.0
    // A1 (Moderate):  Link 0 = EhtMcs5 (5 GHz, 20 MHz), Link 1 = EhtMcs8 (6 GHz, 20 MHz), ratio ~1.5
    // A2 (Strong):    Link 0 = EhtMcs2 (5 GHz, 20 MHz), Link 1 = EhtMcs9 (6 GHz, 20 MHz), ratio ~3.0
    std::string dataMode0 = "EhtMcs7";
    std::string dataMode1 = "EhtMcs7";
    double refLoss0 = 40.0;
    double refLoss1 = 40.0;

    if (asymmetry == "A0")
    {
        dataMode0 = "EhtMcs7";
        dataMode1 = "EhtMcs7";
        refLoss0 = 40.0;
        refLoss1 = 40.0;
    }
    else if (asymmetry == "A1")
    {
        dataMode0 = "EhtMcs5";
        dataMode1 = "EhtMcs8";
        refLoss0 = 42.0;
        refLoss1 = 40.0;
    }
    else // A2 - Strong Asymmetry
    {
        dataMode0 = "EhtMcs2";
        dataMode1 = "EhtMcs9";
        refLoss0 = 45.0;
        refLoss1 = 40.0;
    }

    // Apply variance ratio if ablation active
    if (varianceRatio > 1.0)
    {
        refLoss0 += 2.0 * std::log10(varianceRatio);
    }

    // Link 0: 5 GHz
    channelStr[0] = "{0, 20, BAND_5GHZ, 0}";
    freqRanges[0] = WIFI_SPECTRUM_5_GHZ;
    wifi.SetRemoteStationManager(uint8_t(0),
                                 "ns3::ConstantRateWifiManager",
                                 "DataMode",
                                 StringValue(dataMode0),
                                 "ControlMode",
                                 StringValue("OfdmRate6Mbps"));

    // Link 1: 6 GHz
    channelStr[1] = "{0, 20, BAND_6GHZ, 0}";
    freqRanges[1] = WIFI_SPECTRUM_6_GHZ;
    wifi.SetRemoteStationManager(uint8_t(1),
                                 "ns3::ConstantRateWifiManager",
                                 "DataMode",
                                 StringValue(dataMode1),
                                 "ControlMode",
                                 StringValue("OfdmRate6Mbps"));

    SpectrumWifiPhyHelper phy(nLinks);
    for (uint8_t linkId = 0; linkId < nLinks; ++linkId)
    {
        phy.Set(linkId, "ChannelSettings", StringValue(channelStr[linkId]));
        auto spectrumChannel = CreateObject<MultiModelSpectrumChannel>();
        auto lossModel = CreateObject<LogDistancePropagationLossModel>();
        lossModel->SetAttribute("ReferenceLoss", DoubleValue(linkId == 0 ? refLoss0 : refLoss1));
        spectrumChannel->AddPropagationLossModel(lossModel);
        phy.AddChannel(spectrumChannel, freqRanges[linkId]);
    }

    Ssid ssid("ns3-wifi7-mlo");
    WifiMacHelper mac;
    mac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(ssid));
    NetDeviceContainer staDevices = wifi.Install(phy, mac, wifiStaNodes);

    mac.SetType("ns3::ApWifiMac",
                "EnableBeaconJitter",
                BooleanValue(false),
                "BeaconGeneration",
                BooleanValue(false),
                "Ssid",
                SsidValue(ssid));
    NetDeviceContainer apDevice = wifi.Install(phy, mac, wifiApNode);

    auto apDev = DynamicCast<WifiNetDevice>(apDevice.Get(0));
    auto staDev = DynamicCast<WifiNetDevice>(staDevices.Get(0));

    WifiHelper::AssignStreams(apDevice, 1000 + seed * 10);
    WifiHelper::AssignStreams(staDevices, 2000 + seed * 10);

    MobilityHelper mobility;
    Ptr<ListPositionAllocator> positionAlloc = CreateObject<ListPositionAllocator>();
    positionAlloc->Add(Vector(0.0, 0.0, 0.0));
    positionAlloc->Add(Vector(5.0, 0.0, 0.0));
    mobility.SetPositionAllocator(positionAlloc);
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(wifiApNode);
    mobility.Install(wifiStaNodes);

    WifiStaticSetupHelper::SetStaticAssociation(apDev, staDevices);
    WifiStaticSetupHelper::SetStaticBlockAck(apDev, staDevices, {0});

    InternetStackHelper internet;
    internet.Install(wifiApNode);
    internet.Install(wifiStaNodes);

    Ipv4AddressHelper ipv4;
    ipv4.SetBase("192.168.1.0", "255.255.255.0");
    auto apIf = ipv4.Assign(apDevice);
    auto staIf = ipv4.Assign(staDevices);
    Ipv4Address staIp = staIf.GetAddress(0);

    // Setup SaspScheduler
    Ptr<SaspScheduler> scheduler = CreateObject<SaspScheduler>();
    scheduler->SetMode(static_cast<SaspSchedulerMode>(schedulerMode));
    scheduler->SetFlowWeight(1, weightRatio); // Flow 1: Latency-Sensitive
    scheduler->SetFlowWeight(2, 1.0);         // Flow 2: Bulk Background

    // Calibrated initial estimators
    double initialMean0 = (asymmetry == "A2") ? 2.5 : ((asymmetry == "A1") ? 1.5 : 1.0);
    double initialMean1 = 0.8;
    scheduler->SetLinkInitialEstimates(0, initialMean0, 0.2);
    scheduler->SetLinkInitialEstimates(1, initialMean1, 0.1);

    // Attach hook to AP QosTxop for AC_BE (TID 0)
    Ptr<ApWifiMac> apMac = DynamicCast<ApWifiMac>(apDev->GetMac());
    Ptr<QosTxop> qosTxop = apMac->GetQosTxop(AC_BE);
    qosTxop->SetSaspMpduSelectCallback(MakeCallback(&SaspScheduler::SelectMpdu, scheduler));

    // Connect Causal Trace Observers
    apMac->TraceConnectWithoutContext("MacTx", MakeCallback(&MacTxTrace));
    apMac->TraceConnectWithoutContext("MacRxDrop", MakeCallback(&MacTxDropTrace));
    staDev->GetMac()->TraceConnectWithoutContext("MacRx", MakeCallback(&MacRxTrace));

    apDev->GetPhy(0)->TraceConnectWithoutContext("PhyTxBegin", MakeBoundCallback(&PhyTxTrace, 0));
    apDev->GetPhy(1)->TraceConnectWithoutContext("PhyTxBegin", MakeBoundCallback(&PhyTxTrace, 1));
    staDev->GetPhy(0)->TraceConnectWithoutContext("PhyRxEnd", MakeBoundCallback(&PhyRxOkTrace, 0));
    staDev->GetPhy(1)->TraceConnectWithoutContext("PhyRxEnd", MakeBoundCallback(&PhyRxOkTrace, 1));

    // Determine offered load:
    // Reference saturation capacity is ~18 Mbps total under STR.
    // L0 = 0.30 capacity -> ~5.4 Mbps total (Bulk ~5.2 Mbps)
    // L1 = 0.60 capacity -> ~10.8 Mbps total (Bulk ~10.6 Mbps)
    // L2 = 0.85 capacity -> ~15.3 Mbps total (Bulk ~15.1 Mbps)
    std::string bulkRateStr = "15.1Mbps";
    if (offeredLoad == "L0") bulkRateStr = "5.2Mbps";
    else if (offeredLoad == "L1") bulkRateStr = "10.6Mbps";
    else bulkRateStr = "15.1Mbps"; // L2

    uint16_t port1 = 5001;
    uint16_t port2 = 5002;

    // Sinks on STA
    PacketSinkHelper sink1("ns3::UdpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), port1));
    auto sinkApp1 = sink1.Install(wifiStaNodes.Get(0));
    sinkApp1.Start(Seconds(0.01));
    sinkApp1.Stop(Seconds(simulationTime));

    PacketSinkHelper sink2("ns3::UdpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), port2));
    auto sinkApp2 = sink2.Install(wifiStaNodes.Get(0));
    sinkApp2.Start(Seconds(0.01));
    sinkApp2.Stop(Seconds(simulationTime));

    // Connect Sink Delivery trace
    sinkApp1.Get(0)->TraceConnectWithoutContext("Rx", MakeCallback(&SinkRxTrace));
    sinkApp2.Get(0)->TraceConnectWithoutContext("Rx", MakeCallback(&SinkRxTrace));

    // Custom traffic generators
    Ptr<Socket> sock1 = Socket::CreateSocket(wifiApNode.Get(0), UdpSocketFactory::GetTypeId());
    Ptr<MloTrafficApp> app1 = CreateObject<MloTrafficApp>();
    app1->Setup(sock1, InetSocketAddress(staIp, port1), 160, DataRate("160Kbps"), 1, Seconds(0.05), Seconds(simulationTime));
    wifiApNode.Get(0)->AddApplication(app1);
    app1->SetStartTime(Seconds(0.05));
    app1->SetStopTime(Seconds(simulationTime));

    Ptr<Socket> sock2 = Socket::CreateSocket(wifiApNode.Get(0), UdpSocketFactory::GetTypeId());
    Ptr<MloTrafficApp> app2 = CreateObject<MloTrafficApp>();
    app2->Setup(sock2, InetSocketAddress(staIp, port2), 1200, DataRate(bulkRateStr), 2, Seconds(0.05), Seconds(simulationTime));
    wifiApNode.Get(0)->AddApplication(app2);
    app2->SetStartTime(Seconds(0.05));
    app2->SetStopTime(Seconds(simulationTime));

    Simulator::Stop(Seconds(simulationTime));
    Simulator::Run();

    uint64_t rxBytes1 = DynamicCast<PacketSink>(sinkApp1.Get(0))->GetTotalRx();
    uint64_t rxBytes2 = DynamicCast<PacketSink>(sinkApp2.Get(0))->GetTotalRx();

    // Compute metrics
    uint32_t lsSent = 0;
    uint32_t lsRcvd = 0;
    uint32_t bulkSent = 0;
    uint32_t bulkRcvd = 0;

    std::vector<double> lsCrossReorderWaitsMs;
    std::vector<double> lsEndToEndDelaysMs;

    for (const auto& pair : g_packetMap)
    {
        const auto& info = pair.second;
        if (info.flowId == 1) // Latency-Sensitive
        {
            lsSent++;
            if (info.delivered)
            {
                lsRcvd++;
                double e2eDelayMs = (info.deliverTime - info.genTime).GetSeconds() * 1000.0;
                double reorderWaitMs = 0.0;
                if (!info.rxTime.IsZero() && info.deliverTime >= info.rxTime)
                {
                    reorderWaitMs = (info.deliverTime - info.rxTime).GetSeconds() * 1000.0;
                }
                lsEndToEndDelaysMs.push_back(e2eDelayMs);
                lsCrossReorderWaitsMs.push_back(std::max(0.0, reorderWaitMs));
            }
        }
        else if (info.flowId == 2) // Bulk
        {
            bulkSent++;
            if (info.delivered)
            {
                bulkRcvd++;
            }
        }
    }

    double meanCrossBlockingMs = 0.0;
    if (!lsCrossReorderWaitsMs.empty())
    {
        meanCrossBlockingMs = std::accumulate(lsCrossReorderWaitsMs.begin(), lsCrossReorderWaitsMs.end(), 0.0) / lsCrossReorderWaitsMs.size();
    }

    std::sort(lsEndToEndDelaysMs.begin(), lsEndToEndDelaysMs.end());
    double medianDelayMs = 0.0;
    double p95DelayMs = 0.0;
    double p99DelayMs = 0.0;
    if (!lsEndToEndDelaysMs.empty())
    {
        size_t n = lsEndToEndDelaysMs.size();
        medianDelayMs = lsEndToEndDelaysMs[n / 2];
        p95DelayMs = lsEndToEndDelaysMs[std::min(n - 1, (size_t)(n * 0.95))];
        p99DelayMs = lsEndToEndDelaysMs[std::min(n - 1, (size_t)(n * 0.99))];
    }

    double activeTimeS = simulationTime - 0.05;
    double lsGoodputKbps = (rxBytes1 * 8.0) / (activeTimeS * 1000.0);
    double bulkGoodputMbps = (rxBytes2 * 8.0) / (activeTimeS * 1e6);
    double totalGoodputMbps = ((rxBytes1 + rxBytes2) * 8.0) / (activeTimeS * 1e6);

    double lsPdr = (lsSent > 0) ? (double)lsRcvd / lsSent * 100.0 : 0.0;
    double bulkPdr = (bulkSent > 0) ? (double)bulkRcvd / bulkSent * 100.0 : 0.0;

    uint64_t totalDecisions = scheduler->GetTotalDecisions();
    uint64_t invertedDecisions = scheduler->GetInvertedDecisions();
    double inversionRatePct = (totalDecisions > 0) ? (double)invertedDecisions / totalDecisions * 100.0 : 0.0;

    std::string schedName = "DefaultFIFO";
    if (schedulerMode == 1) schedName = "MeanOnly";
    else if (schedulerMode == 2) schedName = "FullSASP";

    Simulator::Destroy();

    // Output formatted summary
    std::cout << "[Run " << run << " | Seed " << seed << "] Sched: " << schedName
              << " Asym: " << asymmetry << " Load: " << offeredLoad
              << " -> Cross-Blocking: " << meanCrossBlockingMs << " ms"
              << " (Inversions: " << invertedDecisions << "/" << totalDecisions << " = " << inversionRatePct << "%)"
              << " Delay(p50=" << medianDelayMs << ", p95=" << p95DelayMs << " ms)"
              << " Tput=" << totalGoodputMbps << " Mbps" << std::endl;

    // Append to CSV if requested
    if (!csvOutput.empty())
    {
        std::ofstream csv(csvOutput, std::ios::app);
        if (csv.is_open())
        {
            // If file is new/empty, write header
            csv.seekp(0, std::ios::end);
            if (csv.tellp() == 0)
            {
                csv << "run_id,seed,scheduler,asymmetry,offered_load,weight_ratio,variance_ratio,"
                    << "sim_time_s,ls_sent,ls_rcvd,bulk_sent,bulk_rcvd,ls_pdr,bulk_pdr,"
                    << "mean_cross_blocking_ms,ls_delay_median_ms,ls_delay_p95_ms,ls_delay_p99_ms,"
                    << "ls_goodput_kbps,bulk_goodput_mbps,total_goodput_mbps,mac_retries,mac_drops,"
                    << "total_decisions,inverted_decisions,inversion_rate_pct\n";
            }
            csv << run << "," << seed << "," << schedName << "," << asymmetry << "," << offeredLoad << ","
                << weightRatio << "," << varianceRatio << "," << simulationTime << ","
                << lsSent << "," << lsRcvd << "," << bulkSent << "," << bulkRcvd << ","
                << lsPdr << "," << bulkPdr << "," << meanCrossBlockingMs << ","
                << medianDelayMs << "," << p95DelayMs << "," << p99DelayMs << ","
                << lsGoodputKbps << "," << bulkGoodputMbps << "," << totalGoodputMbps << ","
                << g_macRetries << "," << g_macDrops << ","
                << totalDecisions << "," << invertedDecisions << "," << inversionRatePct << "\n";
        }
    }

    return 0;
}
