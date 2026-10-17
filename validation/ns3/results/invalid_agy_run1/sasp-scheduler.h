#ifndef SASP_SCHEDULER_H
#define SASP_SCHEDULER_H

#include "ns3/core-module.h"
#include "ns3/wifi-module.h"
#include "ns3/network-module.h"
#include "ns3/tag.h"

#include <cmath>
#include <map>
#include <vector>
#include <deque>
#include <algorithm>

namespace ns3 {

/**
 * FlowIdTag identifies application flows (Flow 1: Latency-Sensitive, Flow 2: Bulk Background)
 * sharing the same TID 0 and Block Ack ordering context.
 */
class MloFlowIdTag : public Tag
{
public:
    static TypeId GetTypeId()
    {
        static TypeId tid = TypeId("ns3::MloFlowIdTag")
            .SetParent<Tag>()
            .AddConstructor<MloFlowIdTag>()
            .AddAttribute("FlowId", "Application Flow Identifier",
                          UintegerValue(0),
                          MakeUintegerAccessor(&MloFlowIdTag::GetFlowId, &MloFlowIdTag::SetFlowId),
                          MakeUintegerChecker<uint8_t>())
            .AddAttribute("PacketSeq", "Per-Flow Application Sequence Number",
                          UintegerValue(0),
                          MakeUintegerAccessor(&MloFlowIdTag::GetPacketSeq, &MloFlowIdTag::SetPacketSeq),
                          MakeUintegerChecker<uint32_t>())
            .AddAttribute("GenTime", "Packet Generation Timestamp in Microseconds",
                          UintegerValue(0),
                          MakeUintegerAccessor(&MloFlowIdTag::GetGenTimeUs, &MloFlowIdTag::SetGenTimeUs),
                          MakeUintegerChecker<uint64_t>());
        return tid;
    }

    TypeId GetInstanceTypeId() const override { return GetTypeId(); }
    uint32_t GetSerializedSize() const override { return sizeof(uint8_t) + sizeof(uint32_t) + sizeof(uint64_t); }
    void Serialize(TagBuffer i) const override
    {
        i.WriteU8(m_flowId);
        i.WriteU32(m_packetSeq);
        i.WriteU64(m_genTimeUs);
    }
    void Deserialize(TagBuffer i) override
    {
        m_flowId = i.ReadU8();
        m_packetSeq = i.ReadU32();
        m_genTimeUs = i.ReadU64();
    }
    void Print(std::ostream &os) const override
    {
        os << "FlowId=" << (uint32_t)m_flowId << " Seq=" << m_packetSeq << " Gen=" << m_genTimeUs << "us";
    }

    void SetFlowId(uint8_t flowId) { m_flowId = flowId; }
    uint8_t GetFlowId() const { return m_flowId; }
    void SetPacketSeq(uint32_t seq) { m_packetSeq = seq; }
    uint32_t GetPacketSeq() const { return m_packetSeq; }
    void SetGenTimeUs(uint64_t t) { m_genTimeUs = t; }
    uint64_t GetGenTimeUs() const { return m_genTimeUs; }

private:
    uint8_t m_flowId{0};
    uint32_t m_packetSeq{0};
    uint64_t m_genTimeUs{0};
};

/**
 * Operating Modes for the ns-3 MLO Scheduler
 */
enum SaspSchedulerMode
{
    SASP_MODE_DEFAULT_FIFO = 0, //!< Native FIFO reference (non-predictive)
    SASP_MODE_MEAN_ONLY = 1,    //!< Mean-Only Sequencing (predictive mean, omits variance threshold)
    SASP_MODE_FULL_SASP = 2     //!< Full SASP (pairwise Gaussian threshold for N=2, scalar-mean sort for N>=3)
};

/**
 * Causal Link Service-Time Estimator
 */
struct LinkEstimatorState
{
    double meanCompletionMs{1.0};      //!< EWMA mean completion time [ms]
    double varianceCompletionMs2{0.01}; //!< EWMA completion variance [ms^2]
    uint64_t sampleCount{0};           //!< Realized ACK observations
    double alpha{0.125};               //!< EWMA smoothing factor
    double minVarianceFloor{1e-6};     //!< Strictly positive variance floor
};

/**
 * Record of an in-flight transmission
 */
struct InflightRecord
{
    uint8_t linkId;
    uint8_t flowId;
    uint16_t seqNum;
    Time txStartTime;
    double projectedCompletionTimeMs;
};

/**
 * Sequence-Aware Scheduling Policy (SASP) Engine for ns-3
 */
class SaspScheduler : public Object
{
public:
    static TypeId GetTypeId();

    SaspScheduler();
    virtual ~SaspScheduler() = default;

    void SetMode(SaspSchedulerMode mode);
    SaspSchedulerMode GetMode() const;

    void SetFlowWeight(uint8_t flowId, double weight);
    double GetFlowWeight(uint8_t flowId) const;

    void SetLinkInitialEstimates(uint8_t linkId, double initialMeanMs, double initialStdMs);

    // Decision Hook connected to QosTxop::SetSaspMpduSelectCallback
    Ptr<WifiMpdu> SelectMpdu(uint8_t linkId, const QosTxop* qosTxop, Ptr<WifiMpdu> defaultItem);

    // Causal Feedback Observers
    void NotifyMpduTransmitted(uint8_t linkId, Ptr<const WifiMpdu> mpdu);
    void NotifyMpduAcked(uint8_t linkId, Ptr<const WifiMpdu> mpdu);
    void NotifyMpduFailed(uint8_t linkId, Ptr<const WifiMpdu> mpdu);

    // Metrics & Audit Inspection
    uint64_t GetTotalDecisions() const { return m_totalDecisions; }
    uint64_t GetInvertedDecisions() const { return m_invertedDecisions; }
    double GetLinkMean(uint8_t linkId) const;
    double GetLinkStd(uint8_t linkId) const;

    // Mathematical Solver: Theorem 3 unique root
    static double ComputeThresholdRoot(double w_a, double w_b);
    static double StandardPhi(double u);
    static double StandardNormalCdf(double u);
    static double PartialExpectation(double mu, double sigma);

private:
    SaspSchedulerMode m_mode{SASP_MODE_DEFAULT_FIFO};
    std::map<uint8_t, double> m_flowWeights;
    std::map<uint8_t, LinkEstimatorState> m_linkEstimators;
    std::map<uint16_t, InflightRecord> m_inflightMpdus; // key: sequence number

    uint64_t m_totalDecisions{0};
    uint64_t m_invertedDecisions{0};

    uint8_t ExtractFlowId(Ptr<const WifiMpdu> mpdu) const;
};

} // namespace ns3

#endif // SASP_SCHEDULER_H
