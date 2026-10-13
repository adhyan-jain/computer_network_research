# Quantitative Claim-to-Evidence Reconciliation Audit (Phase 4)

**Audit Objective:** Independent verification of every quantitative claim against raw simulation evidence.  
**Date:** October 13, 2026  
**Auditor Role:** Scientific Reproducibility Auditor  

---

## 1. Executive Summary & Audit Rules

This audit maps every numerical claim reported in `README.md`, `FINAL_REPORT.md`, and `paper/main.tex` directly to the raw simulation CSV files in `experiments/results/`.

**Audit Mandate:**
- All reported percentage reductions are independently recomputed using explicitly stated formulas and denominators.
- No historical CSV files have been modified or overwritten.
- Statistical units are confirmed as independent random simulation runs (N=30 seeds per point).
- The root cause of EXP-06's constant 18.2% advantage is fully explained.
- Discrepancies between host Python execution profiling and embedded firmware timing are resolved.
- Simulated reviewer acceptance scores are permanently removed from publication readiness claims.

---

## 2. Headline Claim Reconciliation Matrix

| Claim ID | Claimed Statement | Source CSV & Rows | Generating Code / Config | Formula & Denominator | Recomputed Value | Reconciliation Status |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **CLM-01** | EXP-01: SASP reduces cross-blocking from 0.891 ms to 0.747 ms at $\delta = 5.0$ ms (16.1% reduction) | `exp1_link_asymmetry.csv` (Rows for $\delta=5.0$, `DefaultFIFO` vs `SASP`) | `run_campaign.py:76-156`<br>30 seeds (1000–1029), 400 pkts/s | $\frac{\text{FIFO} - \text{SASP}}{\text{FIFO}} \times 100$<br>Denominator: 0.8906 ms | $\frac{0.8906 - 0.7469}{0.8906} = 16.14\%$ | **VERIFIED** |
| **CLM-02** | EXP-01: Orthogonal decomposition identity $\Delta \equiv \mathcal{S} + \mathcal{X}$ holds on all rows | `exp1_link_asymmetry.csv` (All 72 rows) | `core.py:150-185`, `run_campaign.py:147-154` | $|\mathcal{S} + \mathcal{X} - \Delta| < 10^{-4}$ (4 decimal places) | Holds on all 72 rows (max deviation $10^{-4}$ due to round-to-4) | **VERIFIED** |
| **CLM-03** | EXP-02: Under stall boundary ($\lambda / \lambda^* = 1.5$), SASP reduces p99 latency from 133.1 ms to 100.5 ms (24.5% reduction) | `exp2_window_collapse.csv` (Rows for `norm_load=1.5`, `DefaultFIFO` vs `SASP`) | `run_campaign.py:158-223`<br>$W=16, \mu_{\text{slow}}=8$ ms | $\frac{133.0713 - 100.5062}{133.0713} \times 100$ | $24.47\%$ | **VERIFIED** |
| **CLM-04** | EXP-02: Under stall boundary ($\lambda / \lambda^* = 1.5$), SASP suppresses cross-blocking from 0.737 ms to 0.024 ms (96.8% reduction) | `exp2_window_collapse.csv` (Rows for `norm_load=1.5`) | `run_campaign.py:158-223` | $\frac{0.7374 - 0.0235}{0.7374} \times 100$ | $96.81\%$ | **VERIFIED** |
| **CLM-05** | EXP-03: Under priority ratio 50:1, SASP reduces weighted cross-blocking cost from 6.643 to 5.549 (16.5% reduction) | `exp3_priority_heterogeneity.csv` (Rows for `weight_ratio=50.0`) | `run_campaign.py:226-290`<br>$w_1=1.0, w_2=50.0$ | $\frac{6.6431 - 5.5491}{6.6431} \times 100$ | $16.47\%$ | **VERIFIED** |
| **CLM-06** | EXP-03: Interactive flow cross-blocking reduced from 0.263 ms to 0.220 ms (16.3% reduction) | `exp3_priority_heterogeneity.csv` (Rows for `weight_ratio=50.0`) | `run_campaign.py:226-290` | $\frac{0.2632 - 0.2204}{0.2632} \times 100$ | $16.26\%$ | **VERIFIED** |
| **CLM-07** | EXP-04: At 25% FER, SASP reduces cross-blocking from 0.960 ms to 0.613 ms (36.2% reduction) | `exp4_contention_loss.csv` (Rows for `fer=0.25`) | `run_campaign.py:293-354` | $\frac{0.9600 - 0.6129}{0.9600} \times 100$ | $36.16\%$ | **VERIFIED** |
| **CLM-08** | EXP-05: Pure decision overhead ranges from 1.27 $\mu$s to 16.26 $\mu$s in Python | `exp5_scalability.csv` (All 9 SASP rows) | `run_campaign.py:357-420`<br>`TimedSchedulerWrapper` | Min and Max of `decision_overhead_us` column | Min: $1.27\,\mu\text{s}$ (4 links/2 flows)<br>Max: $16.26\,\mu\text{s}$ (2 links/8 flows) | **VERIFIED (With Qualifier)** |
| **CLM-09** | EXP-06: Constant 18.2% relative advantage across estimation bias | `exp6_estimation_robustness.csv` (All 7 rows) | `run_campaign.py:423-494` | $\frac{0.2499 - 0.2044}{0.2499} \times 100$ | Exactly $18.18\%$ on all rows | **VERIFIED (Artifact Identified)** |
| **CLM-10** | EXP-07: Ablation shows Full SASP weighted cost of 1.4988 vs FIFO 1.8845 (20.5% reduction) | `exp7_ablation_study.csv` (All 4 rows) | `run_campaign.py:497-558`<br>30 seeds each | $\frac{1.8845 - 1.4988}{1.8845} \times 100$ | $20.47\%$ | **VERIFIED** |
| **CLM-11** | EXP-07: Mean-only sequencing achieves 1.5000 (20.4% reduction), leaving 0.1 pp marginal gain for $u^*$ | `exp7_ablation_study.csv` (`3_MeanOnlySequencing` vs `4_FullSASP`) | `run_campaign.py:510-512` | $\frac{1.8845 - 1.5000}{1.8845} = 20.40\%$<br>Marginal: $20.47 - 20.40 = 0.07\%$ | $0.08\%$ marginal difference | **VERIFIED (Key Scientific Finding)** |

---

## 3. Deep-Dive Audits of Flagged Discrepancies

### 3.1 EXP-06: Why is Relative Advantage Constant at 18.18%?
An auditor might suspect that a constant 18.18% across bias values from $-50\%$ to $+50\%$ indicates a faulty script or hardcoded value.  
**Auditor Finding: It is NOT hardcoded; it is a physical regime effect.**
- In EXP-06, Link 0 has mean delay $2.5$ ms and Link 1 has mean delay $0.5$ ms.
- The mean delay difference is $\Delta\mu = 2.5 - 0.5 = 2.0$ ms.
- The link delay standard deviation is $\sigma \approx 0.1$ ms.
- The test weights are $w_1 = 1.0, w_2 = 5.0$, for which the optimal threshold root is $u^* = -0.636$.
- When SASP checks whether to invert sequence numbers:
  $$\frac{\Delta\mu}{\sigma_{\text{pair}}} \approx \frac{2.0\text{ ms}}{0.14\text{ ms}} \approx 14.3 \gg -0.636 = u^*$$
- Even when the variance estimator is biased by $+50\%$ ($\sigma_{\text{pair}} \to 0.21$ ms) or $-50\%$ ($\sigma_{\text{pair}} \to 0.07$ ms), the ratio $\Delta\mu / \sigma_{\text{pair}}$ remains between $9.5$ and $28.5$—always vastly greater than $-0.636$.
- Consequently, the scheduler makes the **exact same sequencing decisions** on every packet dispatch across all bias levels!
- **Scientific Implication:** In moderate-to-high delay asymmetry regimes ($\Delta\mu \gg \sigma$), the scheduling decision is dominated by the mean difference; estimation errors in the variance parameter have zero impact on the resulting schedule.

### 3.2 EXP-05: SIFS Timing and Overhead Qualification
- The report previously claimed that $16.3\,\mu\text{s}$ execution time is "within the $16\,\mu\text{s}$ SIFS budget".
- **Auditor Correction:** In IEEE 802.11a/g/n/ac/ax/be (5 GHz/6 GHz), SIFS is strictly $16\,\mu\text{s}$. A Python execution time of $16.26\,\mu\text{s}$ is **greater than $16\,\mu\text{s}$** and does not fit within SIFS without margin.
- **Accurate Presentation:**
  - For standard configurations ($M \le 4$ flows, $K \le 3$ links), SASP executes in $1.27$ to $3.98\,\mu\text{s}$ in interpreted Python—well within the $16\,\mu\text{s}$ window.
  - The $16.26\,\mu\text{s}$ maximum occurs only under an extreme stress topology (8 active flows on 2 links) run in interpreted CPython.
  - In a production Access Point, the scheduling algorithm would be compiled in C/C++ or microcode running on an embedded ARM Cortex-A53/A73 network processor, where execution overhead will be substantially lower. However, this must be stated as an **engineering expectation**, not an empirical measurement.

### 3.3 Artificial Reviewer Scores Retraction
- Sections in previous reports citing "Reviewer Score: 8.5/10" and "Verdict: Accept with Minor Revision" were generated during internal LLM adversarial simulations.
- **Auditor Action:** All references attributing these scores to external journal review have been formally retracted and struck from the publication assessment.

---

## 4. Reconciled Headline Summary Table

Every headline number in the manuscript now corresponds directly to the verified values:

| Dimension | Baseline FIFO | SASP | Verified Delta | Verification Source |
| :--- | :---: | :---: | :---: | :--- |
| **Link Asymmetry ($\delta=5.0$ ms)** | 0.891 ms | 0.747 ms | **16.1% reduction** | `exp1_link_asymmetry.csv` |
| **BA Stall Collapse ($\lambda/\lambda^*=1.5$)** | 0.737 ms | 0.024 ms | **96.8% cross reduction** | `exp2_window_collapse.csv` |
| **BA Stall Tail Latency (p99)** | 133.1 ms | 100.5 ms | **24.5% p99 reduction** | `exp2_window_collapse.csv` |
| **Priority Heterogeneity ($w=50$)** | 6.643 | 5.549 | **16.5% cost reduction** | `exp3_priority_heterogeneity.csv` |
| **Frame Loss & Retries (FER=25%)** | 0.960 ms | 0.613 ms | **36.2% reduction** | `exp4_contention_loss.csv` |
| **Ablation Weighted Cost** | 1.8845 | 1.4988 | **20.5% cost reduction** | `exp7_ablation_study.csv` |
| **Scheduling Overhead (Typical)** | — | 1.3–4.0 $\mu$s | Within SIFS budget | `exp5_scalability.csv` |

---
*End of Claim-to-Evidence Audit.*
