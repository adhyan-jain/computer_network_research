# Claim-Evidence Matrix: Wi-Fi 7 MLO SASP Research Project

**Document Status:** Verified Post-Rebuild Audit Matrix  
**Date:** October 2026  
**Artifact Directory:** `/home/adhyan/Desktop/wifi7_mlo_hol/`  

---

## 1. Executive Summary

This matrix provides a comprehensive, bidirectional traceability audit linking every mathematical claim, algorithmic mechanism, and empirical result in the rebuilt research paper to its primary source code, formal test, and raw experimental data generated across 30 independent random seeds.

Every quantitative value reported below is derived directly from the unmanipulated simulation results in `experiments/results/*.csv`.

---

## 2. Theoretical Claim-to-Evidence Traceability

| Claim ID | Mathematical Claim | Scope & Boundary Conditions | Code Implementation | Verification Test | Empirical Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **THM-01** | **Buffer Reorder Accounting Decomposition:** $\Delta_i = \mathcal{S}_i + \mathcal{X}_i$ | Strictly in-buffer accounting identity under IEEE 802.11be in-order release semantics; attribution invariance is trace-level and does not model physical medium contention. | `core.py`: `BlockAckReceiver.receive_packet()` | `test_decomposition.py`: `test_theorem_1_orthogonal_decomposition_identity` | `exp1_link_asymmetry.csv`: Verified exactly across all 8 delay asymmetries and 9 schedulers ($\mathcal{S} + \mathcal{X} = \Delta$ to 4 decimal places). |
| **THM-02** | **Multi-Link Sequence Divergence & Buffer Stability Bound:** $\lambda_2 < (W - z_\alpha \sigma_{\Delta s}) / \mu_1$ | Dynamic sliding window overflow boundary under IEEE 802.11be forced-advance semantics; cumulative cross-blocking scales quadratically as $\frac{1}{2} \lambda_2 \delta^2$. | `core.py`: `BlockAckReceiver` sliding window check; `simulator.py` | `test_ba_window.py`: `test_ba_window_forced_advance` | `exp2_window_collapse.csv`: Demonstrates tail latency surge from 11.40 ms (load 0.2) to 190.02 ms (load 2.0) and goodput saturation at $\sim 13.72$ Mbps when crossing $\lambda^*$. |
| **THM-03** | **Optimal Pairwise Predictive Sequencing Rule:** $s_a < s_b \iff \frac{\mu_a - \mu_b}{\sqrt{\sigma_a^2 + \sigma_b^2}} \le u^*(w_a, w_b)$ | Pairwise optimal for 2 candidate frames under stochastic Gaussian completion; $u^*$ is transcendental, solved via Newton-Raphson in $\le 4$ iterations; for $N > 2$, Clark's approximation applies. | `schedulers.py`: `compute_threshold_root()`, `SASPScheduler` | `test_threshold.py`: `test_theorem_3_root_accuracy`, `test_theorem_3_asymmetric_direction` | `exp3_priority_heterogeneity.csv`, `exp7_ablation_study.csv`: Demonstrates consistent suppression of weighted cost from 1.8845 to 1.4988 (20.5% reduction). |
| **THM-04** | **Conditional Uncertainty Floor:** $\ge \min(w_a, w_b) \frac{\sigma_Z}{\sqrt{2\pi}} e^{-u^2/2}$ | Strictly conditional on concurrent multi-link dispatch over stochastic Gaussian channels; falsified under SLO or deterministic TDMA. | `theory/derivation.md`, `theory/counterexamples.md` | `test_adversarial.py`: `test_adversarial_identical_links_zero_variance` | `exp1_link_asymmetry.csv`: SLO achieves identically $\mathcal{X}=0.0000$, empirically validating that the bound is non-universal and restricted to stochastic MLO. |

---

## 3. Empirical Results Evidence Matrix

All baseline comparisons evaluate 30 independent random seeds (`BASE_SEEDS = [1000..1029]`) with 95% Student-$t$ confidence intervals.

| Experiment ID | Parameter Sweep | Default FIFO Baseline | Proposed SASP | Quantitative Benefit | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **EXP-01** (Link Asymmetry) | Delay Asymmetry $\delta \in [0.2, 5.0]$ ms | $\delta=1.5$: $\mathbb{E}[\mathcal{X}]=0.1718\pm 0.0115$ ms<br>$\delta=5.0$: $\mathbb{E}[\mathcal{X}]=0.8906\pm 0.0415$ ms | $\delta=1.5$: $\mathbb{E}[\mathcal{X}]=0.1414\pm 0.0100$ ms<br>$\delta=5.0$: $\mathbb{E}[\mathcal{X}]=0.7469\pm 0.0395$ ms | **17.7% reduction** at $\delta=1.5$ ms; **16.1% reduction** at $\delta=5.0$ ms; full goodput preserved (9.55 Mbps). | **VERIFIED** (`exp1_link_asymmetry.csv`) |
| **EXP-02** (Window Collapse) | Normalized Load $\lambda / \lambda^* \in [0.2, 2.0]$ | Load 1.0: $\mathbb{E}[\mathcal{X}]=0.9811\pm 0.0654$ ms<br>Load 1.2: $\mathbb{E}[\mathcal{X}]=0.8866\pm 0.0662$ ms | Load 1.0: $\mathbb{E}[\mathcal{X}]=0.2826\pm 0.0531$ ms<br>Load 1.2: $\mathbb{E}[\mathcal{X}]=0.0869\pm 0.0262$ ms | **71.2% reduction** at load 1.0; **90.2% reduction** at load 1.2; prevents BA stall collapse. | **VERIFIED** (`exp2_window_collapse.csv`) |
| **EXP-03** (Priority Heterogeneity) | Priority Ratio $w_{\text{inter}} / w_{\text{bulk}} \in [1, 50]$ | Ratio 10: Weighted cost $= 1.4241\pm 0.0968$<br>Ratio 50: Weighted cost $= 6.6431\pm 0.4774$ | Ratio 10: Weighted cost $= 1.1885\pm 0.1001$<br>Ratio 50: Weighted cost $= 5.5491\pm 0.5015$ | **16.5% reduction** in weighted cost at ratio 10; **16.5% reduction** at ratio 50. | **VERIFIED** (`exp3_priority_heterogeneity.csv`) |
| **EXP-04** (Loss & Contention) | Frame Error Rate $\text{FER} \in [0.0, 0.25]$ | $\text{FER}=0.10$: $\mathbb{E}[\mathcal{X}]=0.3880\pm 0.0385$ ms<br>$\text{FER}=0.25$: $\mathbb{E}[\mathcal{X}]=0.9600\pm 0.0982$ ms | $\text{FER}=0.10$: $\mathbb{E}[\mathcal{X}]=0.3111\pm 0.0341$ ms<br>$\text{FER}=0.25$: $\mathbb{E}[\mathcal{X}]=0.6129\pm 0.0717$ ms | **19.8% reduction** at 10% FER; **36.2% reduction** at 25% FER; retries identical (125.6). | **VERIFIED** (`exp4_contention_loss.csv`) |
| **EXP-05** (Scalability & Complexity) | Links $K \in [2, 4]$, Flows $M \in [2, 8]$ | Overhead: $0.60 - 1.36\,\mu\text{s}$ per decision | Overhead: $1.23 - 15.30\,\mu\text{s}$ per decision (typical $2-4\,\mu\text{s}$) | $\le 15.3\,\mu\text{s}$ worst-case in Python; $< 4.0\,\mu\text{s}$ for typical 2-4 links/flows. | **VERIFIED** (`exp5_scalability.csv`) |
| **EXP-06** (Estimation Robustness) | Variance Bias $\epsilon_\sigma \in [-50\%, +50\%]$ | Baseline cross-blocking: $0.2499$ ms | Biased SASP cross-blocking: $0.2044\pm 0.0128$ ms | **18.2% relative gain** persisted unconditionally across all bias levels. | **VERIFIED** (`exp6_estimation_robustness.csv`) |
| **EXP-07** (Algorithmic Ablation) | 4 Isolated Variants | FIFO: cost $= 1.8845\pm 0.1350$, cross $= 0.3411$<br>Dispatch-Only: cost $= 1.9124$, cross $= 0.3456$ | Mean-Only: cost $= 1.5000$, cross $= 0.2816$<br>Full SASP: cost $= 1.4988$, cross $= 0.2811$ | **20.5% reduction** in weighted cost from baseline; isolating sequence prediction from link dispatch. | **VERIFIED** (`exp7_ablation_study.csv`) |

---

## 4. Disproven Legacy Claims (Retracted & Corrected)

| Legacy Claim | Audit Finding | Correction in Rebuilt Paper |
| :--- | :--- | :--- |
| "64.2% less cross-flow blocking in EXP-01" | Falsified. Legacy CSV showed -0.17% (0.3988 vs 0.3995 ms). The 64.2% was fabricated or computed against Static Pinning. | Rebuilt experiments demonstrate honest **16.1% to 17.7% reduction** against Default FIFO in active queuing regime. |
| "76.5% lower interactive latency in EXP-03" | Falsified. Legacy CSV showed 0.1279 vs 0.1286 ms (-0.5%). | Rebuilt experiments demonstrate honest **16.5% reduction** in weighted cross-flow blocking cost. |
| "68.4% lower cost in EXP-07 ablation" | Falsified. Legacy CSV showed 0.8286 vs 0.8040 (2.97% gain). | Rebuilt ablation proves true **20.5% reduction** from Default FIFO (1.8845) to Full SASP (1.4988). |
| "Decision overhead $\le 4.2\,\mu\text{s}$" | Contradicted. Legacy CSV recorded 234 to $2,813\,\mu\text{s}$ due to whole-simulation profiling artifact. | Instrumented pure scheduler execution time demonstrates **$1.23$ to $15.30\,\mu\text{s}$** per decision in Python. |
| "Closed-form sub-Gaussian threshold root" | Mathematically invalid. The root $u^*$ is transcendental and the derivation requires exact Gaussian densities. | Formulated as **transcendental root $u^*$** computed via Newton-Raphson in $\le 4$ iterations with pure C builtins. |
| "Universal uncertainty lower bound" | Falsified by Single-Link Operation ($\mathcal{X}=0$). | Scoped strictly as **conditional stochastic lower bound** over concurrent multi-link transmissions. |
