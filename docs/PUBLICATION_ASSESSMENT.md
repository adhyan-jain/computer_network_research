# Publication Assessment & Target Venue Analysis

**Target Objective:** Q1 Journal Publication in Computer Networks / Mobile Systems  
**Date:** 2026-10-13  
**Status:** Evaluation and Manuscript Preparation Complete  

---

## 1. Candidate Journal Rankings & Strategic Fit

| Journal Venue | Publisher / Quartile | Impact Factor / CiteScore | Scope Alignment | Key Strengths of Our Paper for Venue | Potential Reviewer Objections | Overall Fit Score |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: |
| **Computer Networks** | Elsevier (Q1) | 5.6 / 10.2 | Dedicated focus on wireless MAC protocols, 802.11 standards, cross-layer scheduling, and queueing models. | Perfect match. Follows recent landmark MLO papers (Choi et al. 2025, Sangeetha et al. 2026). Direct protocol relevance to Wi-Fi 7 standardization. | Will scrutinize discrete-event vs. real hardware validation. | **9.5 / 10 (Primary Target)** |
| **IEEE/ACM Transactions on Networking (ToN)** | IEEE / ACM (Q1) | 3.7 / 8.1 | High theoretical rigor, stochastic modeling, network optimization, queueing theory. | Strong match for Theorems 1–4, orthogonal decomposition, and sub-Gaussian threshold derivation. | May demand broader general topology or network-wide multi-AP multi-user cross-interference models. | **9.0 / 10 (High Alternative)** |
| **IEEE Transactions on Mobile Computing (TMC)** | IEEE (Q1) | 7.9 / 14.5 | High impact wireless communication, mobile systems, MAC/PHY cross-layer performance. | Fits Wi-Fi 7 MLO operational focus, priority traffic QoS, and tail latency suppression. | High empirical bar; reviewers often request testbed traces or hardware evaluations. | **8.5 / 10** |
| **IEEE Open Journal of the Communications Society (OJCOMS)** | IEEE (Q1) | 7.3 / 11.2 | Direct venue where Oliveira, Raposo, and Luís (2026) published their BA-window characterization study. | Direct follow-up solving the open scheduling and modeling questions raised in Oliveira et al. | Fast turnaround, but slightly lower theoretical prestige than ToN or Computer Networks. | **8.8 / 10** |

---

## 2. Assessment of Publication Readiness

### Strong Selling Points (Review Drivers):
1. **Clear and Defensible Gap:** Directly builds on the recent 2026 Oliveira et al. OJCOMS characterization paper, answering the exact mathematical and algorithmic questions that study left open.
2. **Defensible Prior-Art Boundary:** Explicitly distinguishes itself from MediaTek's patented receiver DPI method (US12470496B2) by strictly adhering to standard-compliant transmitter-side U-MAC scheduling.
3. **Four Proven Theorems:**
   - Theorem 1: Exact, unique orthogonal decomposition ($\Delta_i = \mathcal{S}_i + \mathcal{X}_i$).
   - Theorem 2: Closed-form Multi-Link BA Collapse Boundary condition ($\lambda^* = W / \delta$).
   - Theorem 3: Unique sub-Gaussian threshold root $u^*(w_a, w_b)$ with monotonicity proof.
   - Theorem 4: Fundamental causal uncertainty lower bound $\ge \frac{\sigma_Z}{\sqrt{2\pi}} e^{-u^2/2}$.
4. **Comprehensive Empirical Validation:** Evaluated against 8 distinct baselines across 30 random seeds with $95\%$ confidence intervals, 4-way ablation, and parameter sensitivity analysis.

### Remaining Scientific Objections & Mitigations:
1. **Lack of Hardware Testbed Validation:**
   - *Objection:* Commercial off-the-shelf Wi-Fi 7 chipsets do not run this scheduler in silicon.
   - *Mitigation:* Explicitly discussed under threats to validity. The standard simulation methodology is verified by property-based adversarial testing and complete reproducibility.
2. **Poisson Arrival Assumption:**
   - *Objection:* Real application traffic (e.g. video frames) arrives in bursts rather than strictly memoryless renewals.
   - *Mitigation:* The discrete-event engine supports batch packet generation, and Theorem 3's pairwise threshold rule is conditioned on instantaneous in-flight state rather than requiring arrival Poissonianity.

---

## 3. Recommended Submission Strategy

- **First Choice:** *Computer Networks (Elsevier)*. Fast, thorough peer review process with strong precedent for Wi-Fi 7 MLO protocol designs.
- **Secondary Target:** *IEEE/ACM Transactions on Networking (ToN)* if expanding the multi-user AP downlink scheduling aspects.
