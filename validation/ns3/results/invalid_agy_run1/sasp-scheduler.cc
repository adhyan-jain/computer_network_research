#include "sasp-scheduler.h"
#include "ns3/log.h"
#include "ns3/simulator.h"
#include "ns3/packet.h"

namespace ns3 {

NS_LOG_COMPONENT_DEFINE("SaspScheduler");

NS_OBJECT_ENSURE_REGISTERED(SaspScheduler);

TypeId
SaspScheduler::GetTypeId()
{
    static TypeId tid = TypeId("ns3::SaspScheduler")
        .SetParent<Object>()
        .AddConstructor<SaspScheduler>();
    return tid;
}

SaspScheduler::SaspScheduler()
{
    // Default weights: Flow 1 (Latency-Sensitive) = 10.0, Flow 2 (Bulk) = 1.0
    m_flowWeights[1] = 10.0;
    m_flowWeights[2] = 1.0;

    // Default link estimators
    LinkEstimatorState le0;
    le0.meanCompletionMs = 1.0;
    le0.varianceCompletionMs2 = 0.05;
    m_linkEstimators[0] = le0;

    LinkEstimatorState le1;
    le1.meanCompletionMs = 0.5;
    le1.varianceCompletionMs2 = 0.02;
    m_linkEstimators[1] = le1;
}

void
SaspScheduler::SetMode(SaspSchedulerMode mode)
{
    m_mode = mode;
}

SaspSchedulerMode
SaspScheduler::GetMode() const
{
    return m_mode;
}

void
SaspScheduler::SetFlowWeight(uint8_t flowId, double weight)
{
    m_flowWeights[flowId] = std::max(1e-4, weight);
}

double
SaspScheduler::GetFlowWeight(uint8_t flowId) const
{
    auto it = m_flowWeights.find(flowId);
    if (it != m_flowWeights.end())
    {
        return it->second;
    }
    return 1.0;
}

void
SaspScheduler::SetLinkInitialEstimates(uint8_t linkId, double initialMeanMs, double initialStdMs)
{
    LinkEstimatorState& state = m_linkEstimators[linkId];
    state.meanCompletionMs = std::max(0.01, initialMeanMs);
    state.varianceCompletionMs2 = std::max(state.minVarianceFloor, initialStdMs * initialStdMs);
    state.sampleCount = 0;
}

double
SaspScheduler::GetLinkMean(uint8_t linkId) const
{
    auto it = m_linkEstimators.find(linkId);
    if (it != m_linkEstimators.end())
    {
        return it->second.meanCompletionMs;
    }
    return 1.0;
}

double
SaspScheduler::GetLinkStd(uint8_t linkId) const
{
    auto it = m_linkEstimators.find(linkId);
    if (it != m_linkEstimators.end())
    {
        return std::sqrt(std::max(it->second.minVarianceFloor, it->second.varianceCompletionMs2));
    }
    return 0.1;
}

double
SaspScheduler::StandardPhi(double u)
{
    static const double inv_sqrt_2pi = 1.0 / std::sqrt(2.0 * M_PI);
    return std::exp(-0.5 * u * u) * inv_sqrt_2pi;
}

double
SaspScheduler::StandardNormalCdf(double u)
{
    static const double sqrt_2 = std::sqrt(2.0);
    return 0.5 * (1.0 + std::erf(u / sqrt_2));
}

double
SaspScheduler::PartialExpectation(double mu, double sigma)
{
    if (sigma <= 1e-9)
    {
        return std::max(0.0, mu);
    }
    double u = mu / sigma;
    return sigma * StandardPhi(u) + mu * StandardNormalCdf(u);
}

double
SaspScheduler::ComputeThresholdRoot(double w_a, double w_b)
{
    if (std::abs(w_a - w_b) < 1e-9)
    {
        return 0.0;
    }

    double ratio = w_b / w_a;
    double u = (ratio > 1.0) ? -std::min(3.0, std::sqrt(2.0 * std::log(ratio)))
                             : std::min(3.0, std::sqrt(2.0 * std::log(1.0 / ratio)));

    for (int iter = 0; iter < 12; ++iter)
    {
        double phi_u = StandardPhi(u);
        double Phi_u = StandardNormalCdf(u);
        double h_u = (w_b - w_a) * phi_u + (w_a * (1.0 - Phi_u) + w_b * Phi_u) * u;
        double h_prime_u = w_a * (1.0 - Phi_u) + w_b * Phi_u;

        if (std::abs(h_prime_u) < 1e-12)
        {
            break;
        }
        double step = h_u / h_prime_u;
        u -= step;
        if (std::abs(step) < 1e-7)
        {
            break;
        }
    }
    return u;
}

uint8_t
SaspScheduler::ExtractFlowId(Ptr<const WifiMpdu> mpdu) const
{
    if (!mpdu)
    {
        return 0;
    }
    MloFlowIdTag tag;
    if (mpdu->GetPacket()->PeekPacketTag(tag))
    {
        return tag.GetFlowId();
    }
    return 0;
}

Ptr<WifiMpdu>
SaspScheduler::SelectMpdu(uint8_t linkId, const QosTxop* qosTxop, Ptr<WifiMpdu> defaultItem)
{
    m_totalDecisions++;

    if (m_mode == SASP_MODE_DEFAULT_FIFO || !defaultItem)
    {
        return defaultItem;
    }

    auto queue = qosTxop->GetWifiMacQueue();
    if (!queue)
    {
        return defaultItem;
    }

    // Collect eligible candidate MPDUs from the shared TID queue (up to 4 candidates)
    std::vector<Ptr<WifiMpdu>> candidates;
    candidates.push_back(defaultItem);

    Ptr<WifiMpdu> prev = defaultItem;
    while (candidates.size() < 4)
    {
        auto nextMpdu = queue->PeekFirstAvailable(linkId, prev);
        if (!nextMpdu)
        {
            break;
        }
        if (nextMpdu->GetInFlightLinkIds().empty())
        {
            candidates.push_back(nextMpdu);
        }
        prev = nextMpdu;
    }

    if (candidates.size() < 2)
    {
        return defaultItem;
    }

    // Inspect candidate 0 (FIFO head) and candidate 1
    uint8_t flow0 = ExtractFlowId(candidates[0]);
    uint8_t flow1 = ExtractFlowId(candidates[1]);

    // Preserve intra-flow FIFO ordering
    if (flow0 == flow1 || flow0 == 0 || flow1 == 0)
    {
        return defaultItem;
    }

    // Never invert if either candidate already has an assigned sequence number
    if (candidates[0]->HasSeqNoAssigned() || candidates[1]->HasSeqNoAssigned())
    {
        return defaultItem;
    }

    double nowMs = Simulator::Now().GetSeconds() * 1000.0;
    double muK = GetLinkMean(linkId);
    double sigmaK = GetLinkStd(linkId);

    // Other link state
    uint8_t otherLink = (linkId == 0) ? 1 : 0;
    double muOther = GetLinkMean(otherLink);
    double sigmaOther = GetLinkStd(otherLink);

    // Flow weights
    double w0 = GetFlowWeight(flow0);
    double w1 = GetFlowWeight(flow1);

    bool shouldInvert = false;

    if (candidates.size() == 2)
    {
        // Check if there is an in-flight frame on the other link
        bool hasInflight = false;
        double inflightProjMs = 0.0;
        uint8_t inflightFlow = 0;
        for (const auto& pair : m_inflightMpdus)
        {
            if (pair.second.linkId == otherLink)
            {
                hasInflight = true;
                inflightProjMs = pair.second.projectedCompletionTimeMs;
                inflightFlow = pair.second.flowId;
                break;
            }
        }

        if (hasInflight && inflightFlow != flow1 && w1 > w0)
        {
            // Latency-sensitive frame candidate 1 would suffer cross-flow HOL
            // if bulk frame candidate 0 is transmitted on slow link while other link finishes early
            double deltaComp = (nowMs + muK) - inflightProjMs;
            if (deltaComp > 0.05)
            {
                shouldInvert = true;
            }
        }
        else
        {
            // Evaluate pairwise ordering under predicted completions
            // Suppose linkId is slow (higher mu) and otherLink is fast (lower mu)
            double t0_proj = nowMs + muK;
            double t1_proj = nowMs + muOther; // projected on companion link

            if (m_mode == SASP_MODE_MEAN_ONLY)
            {
                // Mean-only: invert if candidate 1 (high priority) completes earlier on fast link
                if (w1 > w0 && muK > muOther)
                {
                    shouldInvert = true;
                }
            }
            else if (m_mode == SASP_MODE_FULL_SASP)
            {
                // Theorem 3 Pairwise Gaussian Threshold Rule
                double u_star = ComputeThresholdRoot(w0, w1);
                double sigma_pair = std::sqrt(sigmaK * sigmaK + sigmaOther * sigmaOther);
                double delta_mu = t0_proj - t1_proj;

                if (delta_mu / std::max(1e-6, sigma_pair) > u_star)
                {
                    shouldInvert = true;
                }
            }
        }
    }
    else
    {
        // Batch size N >= 3: Multi-frame scalar-mean heuristic
        // Sort candidates by projected completion time weighted by priority
        std::vector<std::pair<double, Ptr<WifiMpdu>>> scored;
        for (size_t i = 0; i < candidates.size(); ++i)
        {
            uint8_t fId = ExtractFlowId(candidates[i]);
            double w = GetFlowWeight(fId);
            double proj = nowMs + muK / std::max(0.1, w);
            scored.push_back({proj, candidates[i]});
        }
        std::sort(scored.begin(), scored.end(),
                  [](const auto& a, const auto& b) { return a.first < b.first; });

        if (scored[0].second != defaultItem)
        {
            if (defaultItem->HasSeqNoAssigned() || scored[0].second->HasSeqNoAssigned())
            {
                return defaultItem;
            }
            shouldInvert = true;
            m_invertedDecisions++;
            return scored[0].second;
        }
    }

    if (shouldInvert)
    {
        m_invertedDecisions++;
        return candidates[1];
    }

    return defaultItem;
}

void
SaspScheduler::NotifyMpduTransmitted(uint8_t linkId, Ptr<const WifiMpdu> mpdu)
{
    if (!mpdu) return;
    uint16_t sn = mpdu->GetHeader().GetSequenceNumber();
    uint8_t flowId = ExtractFlowId(mpdu);
    double nowMs = Simulator::Now().GetSeconds() * 1000.0;
    double muK = GetLinkMean(linkId);

    InflightRecord rec;
    rec.linkId = linkId;
    rec.flowId = flowId;
    rec.seqNum = sn;
    rec.txStartTime = Simulator::Now();
    rec.projectedCompletionTimeMs = nowMs + muK;

    m_inflightMpdus[sn] = rec;
}

void
SaspScheduler::NotifyMpduAcked(uint8_t linkId, Ptr<const WifiMpdu> mpdu)
{
    if (!mpdu) return;
    uint16_t sn = mpdu->GetHeader().GetSequenceNumber();
    auto it = m_inflightMpdus.find(sn);

    if (it != m_inflightMpdus.end())
    {
        Time duration = Simulator::Now() - it->second.txStartTime;
        double durMs = duration.GetSeconds() * 1000.0;

        // Causal EWMA update of mean and variance
        LinkEstimatorState& state = m_linkEstimators[linkId];
        double err = durMs - state.meanCompletionMs;
        state.meanCompletionMs += state.alpha * err;
        state.varianceCompletionMs2 = (1.0 - state.alpha) * (state.varianceCompletionMs2 + state.alpha * err * err);
        state.varianceCompletionMs2 = std::max(state.minVarianceFloor, state.varianceCompletionMs2);
        state.sampleCount++;

        m_inflightMpdus.erase(it);
    }
}

void
SaspScheduler::NotifyMpduFailed(uint8_t linkId, Ptr<const WifiMpdu> mpdu)
{
    if (!mpdu) return;
    uint16_t sn = mpdu->GetHeader().GetSequenceNumber();
    m_inflightMpdus.erase(sn);
}

} // namespace ns3
