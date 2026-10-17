# Publication Assessment & Strategy Report (Phase 5 Audit)

**Date:** October 13, 2026  
**Auditor:** Independent Publishing & Networking Systems Reviewer  
**Scope:** Final Venue Positioning, Reviewer Objections, and Submission Feasibility  

---

## 1. Candidate Journal Rankings & Strategic Fit

| Journal Venue | Publisher / Quartile | Impact Factor / CiteScore | Scope Alignment | Key Strengths of Our Paper for Venue | Strongest Expected Reviewer Objections | Overall Fit Score |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: |
| **Computer Networks** | Elsevier (Q1) | 5.6 / 10.2 | Wireless MAC protocols, 802.11 standards, cross-layer scheduling, queueing models. | Strong match. Follows recent landmark MLO papers (Choi et al. 2025, Sangeetha et al. 2026). Direct protocol relevance to Wi-Fi 7 standardization. | Will scrutinize custom discrete-event simulation vs. ns-3 or real hardware validation. | **9.2 / 10 (Primary Target)** |
| **IEEE Open Journal of the Communications Society (OJCOMS)** | IEEE (Q1) | 7.3 / 11.2 | Direct venue where Oliveira, Raposo, and Luís (2026) published their BA-window characterization study. | Direct follow-up providing the analytical model and transmitter scheduling policy that Oliveira et al. left open. | Reviewers will compare directly with Oliveira et al.'s ns-3 model and ask why ns-3 was not used. | **9.0 / 10 (Strong Alternative)** |
| **IEEE/ACM Transactions on Networking (ToN)** | IEEE / ACM (Q1) | 3.7 / 8.1 | High theoretical rigor, stochastic modeling, network optimization, queueing theory. | Strong match for Theorems 1–3, orthogonal trace decomposition, and threshold root derivation. | Will demand global multi-frame optimality proofs rather than pairwise heuristic; will question Gaussian approximation under retry backoff. | **7.5 / 10** |
| **IEEE Transactions on Mobile Computing (TMC)** | IEEE (Q1) | 7.9 / 14.5 | High-impact wireless systems, MAC/PHY cross-layer performance. | Fits Wi-Fi 7 MLO operational focus, priority traffic QoS, and tail latency suppression. | Extremely high empirical bar; reviewers frequently reject papers lacking physical SDR/FPGA or commercial silicon testbed traces. | **7.0 / 10** |

---

## 2. Realistic Assessment of Publication Readiness

### Genuine Scientific Strengths:
1. **First Formal Analytical Formulation of CF-HOL:** Directly addresses the cross-flow reorder penalty within shared TID 0, establishing the orthogonal trace accounting decomposition ($\Delta_i = \mathcal{S}_i + \mathcal{X}_i$) and the mean-drift boundary ($\lambda^* = W/\delta$) with exact Poisson tail stall probabilities.
2. **Standard-Compliant Sender-Side Architecture:** Solves the reordering problem purely at the transmitter U-MAC without requiring proprietary receiver modifications or deep packet inspection (differentiating from MediaTek patent US12470496B2).
3. **Rigorous Experimental Baseline:** 8 baselines evaluated across 30 random seeds with full unit test coverage (44 passing tests), deterministic scenario validation, and parameter sensitivity analysis.
4. **Reproducible 20%--78% Gain Over FIFO:** Under asymmetric link conditions ($\Delta\mu \ge 0.5$ ms), predictive arrival ordering suppresses the vast majority of Block Ack reordering stalls without sacrificing link goodput.

### Primary Reviewer Vulnerabilities (Must Be Explicitly Addressed in Paper):
1. **Custom Python Simulator vs. ns-3:** Reviewers will note that Oliveira et al. evaluated MLO in ns-3. The paper must explicitly frame the implementation as an analytical validation prototype and outline ns-3 porting as immediate future work.
2. **Mean-Only vs. Variance Awareness:** In wide asymmetry regimes, simple Mean-Only Sequencing achieves virtually all of SASP's gain over FIFO, while Full SASP's advantage in near-equal regimes fails multiple-testing significance. The paper must honestly frame predictive sequencing (by means) as the primary empirical engine, and the Theorem 3 threshold root as an analytical bounding tool and priority tie-breaker.
3. **Pairwise vs. Global Multi-Frame Optimality:** Reviewers will question whether pairwise optimality extends to $N \ge 3$ frames. The paper must openly state that transitivity fails (referencing the Condorcet cycle) and that multi-frame scheduling is an index heuristic.
4. **Absence of Silicon Measurements:** All latency measurements reflect Python execution on a host CPU. Hardware timing compliance must be qualified.

---

## 3. Recommended Submission Recommendation

**Target Venue:** *Computer Networks (Elsevier)*  
**Secondary Venue:** *IEEE Open Journal of the Communications Society (OJCOMS)*  

**Submission Framing:**
The paper should be submitted as an **analytical modeling and discrete-event simulation study**. By presenting the theoretical models, the 20%--78% gain over FIFO, and an honest 13-point Threats to Validity section, the paper is scientifically defensible and well-positioned for peer review.

---
*End of Publication Assessment.*
