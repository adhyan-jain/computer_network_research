# Candidate Decision Report

**Date:** 2026-10-12  
**Decision Framework:** Multi-Criteria Scoring and Veto Gate Evaluation  

---

## 1. Candidate Comparison

| Evaluation Metric | Candidate A: Sequence-Aware MLO Scheduling (SASP) | Candidate B: L4S Bottleneck Distinguishability Limits | Candidate C: Adversarial INT Telemetry Verification |
| :--- | :---: | :---: | :---: |
| **Mathematical Novelty Potential** | **8 / 10** (Coupled discrete-continuous stochastic optimization, exact decomposition theorem, threshold rule) | 7 / 10 (Information-theoretic hypothesis testing bounds on marked queues) | 5 / 10 (Sensitivity analysis, near-tie discontinuity problems) |
| **Algorithmic Novelty Potential** | **8 / 10** (Predictive sequencing and link dispatching in Wi-Fi 7 U-MAC) | 6 / 10 (Likely reduces to CUSUM/SPRT variants on ECN marking rates) | 5 / 10 (Clamping / winsorization with known bounds) |
| **Practical Importance / Demand** | **9 / 10** (Wi-Fi 7 MLO is actively deploying worldwide; cross-flow HOL threatens multi-link latency gains) | 7 / 10 (L4S / Prague deployment in wireless networks) | 6 / 10 (Telemetry manipulation in enterprise switches) |
| **Strength of Prior-Art Evidence** | **9 / 10** (Comprehensive audit of IEEE OJCOMS 2026, MediaTek patent US12470496B2, and 802.11be specs) | 6 / 10 (RFC 9331, IETF TSVWG drafts, ongoing discussions) | 7 / 10 (Extensive literature on Byzantine routing and tomography) |
| **Prior-Art Risk** | **Low** (Clear boundary established: sender-side U-MAC vs. patented receiver DPI) | Medium (High volume of recent L4S/Prague RFCs and papers) | High (Preempted by shortest-path stability and SecureINT) |
| **Theoretical Feasibility** | **High** (Rigorous proofs derived for decomposition, stall boundary, and sub-Gaussian thresholds) | Medium (Complex non-stationary fluid limits under wireless delay spikes) | Low (Discontinuous step-function gain for hard shortest path) |
| **Implementation Feasibility** | **High** (Discrete-event simulation engine with full 802.11be MAC semantics, EDCA, BA window) | Medium (Requires ns-3 L4S dual-queue models or kernel eBPF) | Medium (Mininet / P4 setup) |
| **Reproducibility** | **Very High** (Deterministic random seeds, statistical confidence intervals, standalone Python engine) | Medium | Medium |
| **Journal Target Fit (Q1)** | **IEEE/ACM ToN, IEEE TMC, Computer Networks (Elsevier)** | Computer Communications / Performance Evaluation | IEEE TNSM |
| **Overall Weighted Score** | **8.6 / 10** | 6.7 / 10 | 5.2 / 10 |

---

## 2. Decision Verdict

**SELECTED TOPIC:**  
**Candidate A: Cross-Flow Head-of-Line Blocking in Wi-Fi 7 Multi-Link Operation: Analytical Modeling and Sequence-Aware Scheduling**

### Key Justification:
1. **Survives All Veto Gates:** Prior art (Oliveira et al., MediaTek patent) provides empirical characterizations and receiver-side proprietary claims, but leaves sender-side stochastic modeling and sequence-aware optimization completely unsolved.
2. **Defensible Mathematical Grounding:** Allows derivation of:
   - An exact orthogonal decomposition theorem separating intra-flow self-blocking from inter-flow cross-blocking.
   - A closed-form Multi-Link BA Window Collapse condition ($\lambda^* = W / \delta$).
   - An optimal sequence-inversion threshold rule under stochastic link delay distributions.
   - A fundamental lower bound on cross-flow delay for any causal online scheduler.
3. **Execution Readiness:** Environment has full Python 3.14 + scientific stack (NumPy, SciPy, Matplotlib, Pytest) and LaTeX compilation engine (pdfTeX, BibTeX, Latexmk).
