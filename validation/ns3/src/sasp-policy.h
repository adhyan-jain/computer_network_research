// sasp-policy.h - ns-3-independent sequence-assignment policy core (SASP / Mean-Only / FIFO).
//
// Pure functions + a causal per-link completion-time estimator. No simulator state, no clocks,
// no access to future information: every input is a number supplied by the caller. This file is
// unit-tested standalone (tests/policy_unit_test.cc) and cross-checked against the audited
// Python implementation (src/mlo_sim/schedulers.py: compute_threshold_root and the pairwise rule).
//
// Scope of the claims (see preregistration.md section 1):
//  * N == 2 candidates : pairwise Gaussian threshold rule (Full SASP) or mean-only comparison.
//  * N >= 3 candidates : BOTH predictive arms use the scalar expected-completion-time sort
//                        (no pairwise comparator is ever used inside a sort).
//  * Nothing here is claimed to be globally optimal for N >= 3.
#ifndef SASP_POLICY_H
#define SASP_POLICY_H

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

namespace sasp
{

enum class Mode : int
{
    FIFO = 0,
    MEAN_ONLY = 1,
    FULL = 2
};

inline double
StdPdf(double u)
{
    return std::exp(-0.5 * u * u) / std::sqrt(2.0 * M_PI);
}

inline double
StdCdf(double u)
{
    return 0.5 * (1.0 + std::erf(u / std::sqrt(2.0)));
}

// Unique root u* of h(u) = (wb-wa) phi(u) + [wa(1-Phi(u)) + wb Phi(u)] u  (identical to the
// audited Python compute_threshold_root, including the iteration count and start value).
inline double
ThresholdRoot(double wa, double wb)
{
    if (std::fabs(wa - wb) < 1e-9)
    {
        return 0.0;
    }
    const double ratio = wb / wa;
    double u = (ratio > 1.0) ? -std::min(3.0, std::sqrt(2.0 * std::log(ratio)))
                             : std::min(3.0, std::sqrt(2.0 * std::log(1.0 / ratio)));
    for (int i = 0; i < 12; ++i)
    {
        const double ph = StdPdf(u);
        const double Ph = StdCdf(u);
        const double h = (wb - wa) * ph + (wa * (1.0 - Ph) + wb * Ph) * u;
        const double hp = wa * (1.0 - Ph) + wb * Ph;
        if (std::fabs(hp) < 1e-12)
        {
            break;
        }
        const double step = h / hp;
        u -= step;
        if (std::fabs(step) < 1e-7)
        {
            break;
        }
    }
    return u;
}

// Causal, size- and rate-aware completion-time model for one link (ms):
//     T(bits) = o + bits / R
// R is the KNOWN configured PHY data rate (configuration knowledge). o is the per-exchange overhead
// (preamble, SIFS, Block Ack, retry inflation, ...) learned ONLY from completed transmissions as
// the EWMA of  (observed completion time) - (PSDU bits / R)  at each ACK/BA. The variance is the
// EWMA variance of that residual. Initial values and floors are fixed constants (prereg. 3.2).
struct LinkEstimator
{
    double rateBps{86e6};   // configured PHY rate
    double mean{0.15};      // learned overhead o (ms)
    double var{0.0025};     // ms^2
    double varFloor{4e-4};  // (0.02 ms)^2
    double alpha{0.1};
    uint32_t n{0};

    void Init(double rate, double initOverheadMs, double initStdMs, double floorStdMs)
    {
        rateBps = rate;
        mean = initOverheadMs;
        varFloor = floorStdMs * floorStdMs;
        var = std::max(varFloor, initStdMs * initStdMs);
        n = 0;
    }

    double AirtimeMs(double bits) const { return bits / rateBps * 1e3; }

    // predicted completion duration (ms) of an exchange carrying `bits`
    double Predict(double bits) const { return mean + AirtimeMs(bits); }

    // completionMs: ACK time - first tx start; psduBits: size of the PSDU that carried the MPDU
    void Update(double completionMs, double psduBits)
    {
        ++n;
        const double sample = completionMs - AirtimeMs(psduBits);
        const double a = std::max(alpha, 1.0 / (n + 2.0)); // fast warm-up, prior carries weight
        const double err = sample - mean;
        mean += a * err;
        var = std::max(varFloor, (1.0 - a) * (var + a * err * err));
    }

    double Std() const { return std::sqrt(var); }
};

struct Candidate
{
    int flow{0};        // application flow id (0 = unknown)
    double weight{1.0}; // priority weight
    double predT{0.0};  // predicted completion epoch (ms)
};

struct Decision
{
    std::vector<int> reserve; // indices (>=1) of candidates to sequence BEFORE the head, in order
    bool pairwise{false};
    double deltaMu{0.0};
    double sigmaPair{0.0};
    double uStar{0.0};
    int nCandidates{0};
    const char* reason{"none"};
};

// c[0] is the queue head (the MPDU that would be sequenced next under FIFO); c[1..] are the
// other eligible not-yet-sequenced MPDUs in FIFO order. sigmaPair is sqrt(sigma_headLink^2 +
// sigma_otherLink^2) (used only by the pairwise rule).
inline Decision
Decide(Mode mode, const std::vector<Candidate>& c, double sigmaPair)
{
    Decision d;
    d.nCandidates = static_cast<int>(c.size());
    if (mode == Mode::FIFO || c.size() < 2)
    {
        d.reason = (mode == Mode::FIFO) ? "fifo" : "single_candidate";
        return d;
    }
    bool distinct = false;
    for (std::size_t i = 1; i < c.size(); ++i)
    {
        distinct = distinct || (c[i].flow != c[0].flow);
    }
    if (!distinct)
    {
        d.reason = "same_flow_keep_fifo";
        return d;
    }

    if (c.size() == 2)
    {
        d.pairwise = true;
        d.deltaMu = c[0].predT - c[1].predT;
        d.sigmaPair = sigmaPair;
        if (mode == Mode::FULL)
        {
            d.uStar = ThresholdRoot(c[0].weight, c[1].weight);
            if (d.deltaMu / std::max(1e-6, sigmaPair) > d.uStar)
            {
                d.reserve.push_back(1);
                d.reason = "pairwise_threshold_invert";
            }
            else
            {
                d.reason = "pairwise_threshold_keep";
            }
        }
        else
        {
            d.uStar = 0.0;
            if (d.deltaMu > 0.0)
            {
                d.reserve.push_back(1);
                d.reason = "pairwise_mean_invert";
            }
            else
            {
                d.reason = "pairwise_mean_keep";
            }
        }
        return d;
    }

    // N >= 3: scalar expected-completion-time sort (same for MEAN_ONLY and FULL). Intra-flow FIFO
    // is preserved: a later MPDU of a flow can never be placed before an earlier one.
    std::vector<double> key(c.size());
    for (std::size_t i = 0; i < c.size(); ++i)
    {
        key[i] = c[i].predT;
        for (int j = static_cast<int>(i) - 1; j >= 0; --j)
        {
            if (c[j].flow == c[i].flow)
            {
                key[i] = std::max(key[i], key[j] + 1e-9);
                break;
            }
        }
    }
    std::vector<int> order(c.size());
    for (std::size_t i = 0; i < c.size(); ++i)
    {
        order[i] = static_cast<int>(i);
    }
    std::stable_sort(order.begin(), order.end(), [&](int a, int b) { return key[a] < key[b]; });
    for (int idx : order)
    {
        if (idx == 0)
        {
            break;
        }
        d.reserve.push_back(idx);
    }
    d.reason = d.reserve.empty() ? "scalar_sort_keep" : "scalar_sort_reorder";
    return d;
}

} // namespace sasp

#endif
