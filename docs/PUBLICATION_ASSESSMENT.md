# Publication Assessment & Target Venue Analysis (Phase 3 Audit)

**Target Objective:** Q1 Journal Publication in Computer Networks / Mobile Systems  
**Date:** October 13, 2026  
**Status:** Post-Audit Independent Assessment  

---

## 1. Candidate Journal Rankings & Strategic Fit

| Journal Venue | Publisher / Quartile | Impact Factor / CiteScore | Scope Alignment | Key Strengths of Our Paper for Venue | Potential Reviewer Objections | Overall Fit Score |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: |
| **Computer Networks** | Elsevier (Q1) | 5.6 / 10.2 | Dedicated focus on wireless MAC protocols, 802.11 standards, cross-layer scheduling, and queueing models. | Strong match. Follows recent landmark MLO papers (Choi et al. 2025, Sangeetha et al. 2026). Direct protocol relevance to Wi-Fi 7 standardization. | Will scrutinize custom discrete-event simulation vs. ns-3 or real hardware validation. | **9.2 / 10 (Primary Target)** |
| **IEEE Open Journal of the Communications Society (OJCOMS)** | IEEE (Q1) | 7.3 / 11.2 | Direct venue where Oliveira, Raposo, and Luís (2026) published their BA-window characterization study. | Direct follow-up providing the analytical model and transmitter scheduling policy that Oliveira et al. left open. | Reviewers will compare directly with Oliveira et al.'s ns-3 model. | **9.0 / 10 (Strong Alternative)** |
| **IEEE/ACM Transactions on Networking (ToN)** | IEEE / ACM (Q1) | 3.7 / 8.1 | High theoretical rigor, stochastic modeling, network optimization, queueing theory. | Strong match for Theorems 1–3, orthogonal trace decomposition, and threshold root derivation. | Demands multi-cell/multi-AP generalization and more extensive mathematical scope beyond pairwise analysis. | **8.0 / 10** |
| **IEEE Transactions on Mobile Computing (TMC)** | IEEE (Q1) | 7.9 / 14.5 | High-impact wireless systems, MAC/PHY cross-layer performance. | Fits Wi-Fi 7 MLO operational focus, priority traffic QoS, and tail latency suppression. | High empirical bar; reviewers frequently mandate testbed traces or hardware evaluations. | **7.8 / 10** |

---

## 2. Assessment of Publication Readiness (Audited)

### Genuine Selling Points:
1. **Clear and Defensible Gap:** Directly builds on the recent 2026 Oliveira et al. OJCOMS characterization paper, providing an analytical framework and transmitter scheduling policy where previous work was purely descriptive.
2. **Standard-Compliant Transmitter Seam:** Operates exclusively at the transmitter U-MAC without requiring receiver modification or deep packet inspection, distinguishing the approach from MediaTek patent US12470496B2.
3. **Four Repaired Mathematical Results:**
   - Theorem 1: Buffer reorder trace accounting decomposition ($\Delta_i = \mathcal{S}_i + \mathcal{X}_i$).
   - Theorem 2: Multi-link BA sequence gap drift condition ($\lambda^* = W / \delta$) and exact Poisson stall probability.
   - Theorem 3: Unique pairwise threshold root $u^*(w_a, w_b)$ with strict monotonicity proof.
   - Theorem 4: Symmetric-link stochastic uncertainty floor ($\min(w) \frac{\sigma_Z}{\sqrt{2\pi}}$).
4. **Reproducible Experimental Campaign:** 8 baselines evaluated across 30 random seeds with $95\%$ Student-t confidence intervals, deterministic unit testing, and parameter sensitivity analysis.

### Substantive Reviewer Objections & Necessary Caveats:
1. **Simulation Platform Limitation:** Custom Python discrete-event simulator rather than ns-3 or physical hardware testbed. Reviewers from IEEE/ACM networking venues will demand explicit disclosure of this scope limitation.
2. **Ablation Nuance:** In moderate asymmetry regimes, mean-only sequencing achieves ~99% of SASP's gain over FIFO, meaning the variance-aware threshold root $u^*$ acts primarily as a theoretical guarantee and priority tie-breaker rather than an empirical game-changer under mild conditions.
3. **Pairwise vs. Global Optimality:** Theorem 3 proves optimality strictly for pairs of frames; multi-frame scheduling is an index-based heuristic.

---

## 3. Recommended Submission Strategy

- **First Choice:** *Computer Networks (Elsevier)*. Appropriate balance of protocol engineering and analytical modeling.
- **Alternative:** *IEEE Open Journal of the Communications Society (OJCOMS)* as a direct companion paper to Oliveira et al. (2026).
