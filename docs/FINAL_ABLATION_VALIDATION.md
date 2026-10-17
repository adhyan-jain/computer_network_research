# Final Ablation Statistical Validation Report (Phase 3 Audit)

**Campaign:** Targeted Algorithmic Ablation (Full SASP vs. Mean-Only Sequencing vs. FIFO)  
**Date:** October 13, 2026  
**Raw Data Source:** `experiments/ablation_phase6/raw_runs.csv` (2,160 rows, 383,221 bytes)  
**Historical Summary:** `experiments/ablation_phase6/summary_ablation.csv` (73 rows)  
**Independent Audit Script:** `experiments/ablation_phase6/independent_statistical_audit.py`  
**Audit Output CSV:** `experiments/ablation_phase6/audit_statistical_summary.csv`  
**Auditor:** Independent Research Auditor & Statistical Reviewer  

---

## 1. Executive Summary & Verdict

The latest project report asserted:
> *"The variance-aware threshold root $u^*$ provides a measurable, statistically significant advantage (3.5% to 4.9% gain, $p < 0.05$) over Mean-Only Sequencing in the specific operating regime of moderate-to-high priority asymmetry ($w \in [5, 50]$) and near-equal link means ($\Delta\mu \le 0.2$ ms)."*

### Independent Statistical Verdict: **CLAIM REFUTED AS CONFIRMATORY EVIDENCE.**
1. **Multiplicity Collapse:** 18 distinct parameter configurations were evaluated across Regimes A, B, and C. The reported $p$-values ($p=0.0382$ at $w=10$, $p=0.0320$ at $w=50$) are raw, unadjusted two-tailed Student-t test values. Under standard family-wise error rate control (**Bonferroni threshold $\alpha = 0.05 / 18 = 0.00278$**) or **Benjamini-Hochberg False Discovery Rate (FDR at $q = 0.05$)**, **ZERO out of 18 configurations achieve statistical significance**.
2. **Selective Post-Hoc Reporting:** The 3.5%--4.9% range was isolated after inspecting the full 18-configuration output table. In adjacent configurations, Full SASP exhibits either 0% difference ($w=1, 2$), non-significant gains ($w=20, p=0.152$), negative performance ($w=100$, where Mean-Only is 3.96% better), or substantial degradation (at $\Delta\mu = 0.5$ ms and $1.0$ ms, where Mean-Only is 11.4% and 12.0% better than Full SASP).
3. **High Decision Concordance:** In the claimed "significant" configurations, Full SASP and Mean-Only make **identical scheduling decisions in 60% to 83% of simulation seeds** (25/30 ties at $w=10$, 18/30 ties at $w=50$). The slight advantage stems from a small subset of seeds (4 to 9 seeds), offset by seeds where Full SASP loses.
4. **Implementation Artifact in Regime C:** In `experiments/ablation_phase6/run_ablation_campaign.py:85`, `links[1].contention_sigma_ms` was modified after object initialization, but `WirelessChannel` was instantiated with default parameters. Consequently, all runs across $\sigma_2 / \sigma_1 \in \{1, 2, 5, 10\}$ executed on identical physical channel noise, producing 100% duplicate numbers.
5. **RNG Stream Desynchronization:** `simulator.py` draws packet inter-arrival times, contention backoff slots, and channel error outcomes from a single shared `self.rng` generator. Once a scheduler deviates in transmission timing, the sequence of future packet arrivals desynchronizes across arms, weakening the validity of strict seed-level pairing.

---

## 2. Reconstructed Experiment Grid and Data Integrity

| Attribute | Documented Design | Verified Physical Data | Audit Status |
| :--- | :---: | :---: | :---: |
| Regimes Evaluated | 3 (Regime A, B, C) | 3 distinct regime tags | VERIFIED |
| Total Configurations | 18 | 18 unique $(w, \Delta\mu, \sigma_{\text{mult}})$ tuples | VERIFIED |
| Schedulers Evaluated | 4 arms | `DefaultFIFO`, `CongestionAware`, `MeanOnly`, `FullSASP` | VERIFIED |
| Seeds Evaluated | 30 paired seeds | Range `3000` to `3029` (30 consecutive integers) | VERIFIED |
| Total Simulation Runs | 2,160 | Exactly 2,160 rows in `raw_runs.csv` | VERIFIED |
| Missing / Omitted Runs | 0 | 0 dropped, 0 duplicate, 0 failed | CLEAN |
| Experimental Unit | Seed realization | 30 independent runs per scheduler-configuration | VERIFIED |
| Primary Metric | Weighted Cross-Blocking Cost | $\sum_f w_f \cdot \bar{\mathcal{X}}_f$ | VERIFIED |
| Secondary Metrics | Goodput, p95/p99 delay, wall time | Recorded per run in CSV columns | VERIFIED |

---

## 3. Independent Recomputation & Statistical Testing Table

The table below reports independent recomputations from `experiments/ablation_phase6/audit_statistical_summary.csv`:

| Regime | Parameter | FIFO Cost | Mean-Only Cost | Full SASP Cost | Rel. Imp. (%) | Raw $p_t$ | Wilcoxon $p_w$ | Cohen's $d_z$ | Wins / Ties / Losses | Bonferroni ($\alpha=0.0028$) | FDR ($q=0.05$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Regime A** | $w = 1.0$ | 0.0057 | 0.0043 | 0.0043 | $0.00\%$ | 1.0000 | 1.0000 | 0.000 | 0 / 30 / 0 | Not Sig | Not Sig |
| **Regime A** | $w = 2.0$ | 0.0088 | 0.0060 | 0.0060 | $0.00\%$ | 1.0000 | 1.0000 | 0.000 | 0 / 30 / 0 | Not Sig | Not Sig |
| **Regime A** | $w = 5.0$ | 0.0181 | 0.0130 | 0.0126 | $+3.55\%$ | 0.0533 | 0.0457 | 0.368 | 4 / 26 / 0 | Not Sig | Not Sig |
| **Regime A** | $w = 10.0$ | 0.0337 | 0.0240 | 0.0231 | $+3.83\%$ | 0.0382 | 0.0255 | 0.396 | 5 / 25 / 0 | **Not Sig** | **Not Sig** |
| **Regime A** | $w = 20.0$ | 0.0650 | 0.0428 | 0.0416 | $+2.80\%$ | 0.1519 | 0.2616 | 0.269 | 6 / 21 / 3 | Not Sig | Not Sig |
| **Regime A** | $w = 50.0$ | 0.1586 | 0.1036 | 0.0986 | $+4.87\%$ | 0.0320 | 0.0528 | 0.411 | 9 / 18 / 3 | **Not Sig** | **Not Sig** |
| **Regime A** | $w = 100.0$ | 0.3146 | 0.2047 | 0.2129 | $-3.96\%$ | 0.6808 | 0.0580 | -0.076 | 10 / 17 / 3 | Not Sig | Not Sig |
| **Regime B** | $\Delta\mu = 0.00$ ms | 0.1043 | 0.1125 | 0.1025 | $+8.85\%$ | 0.3650 | 0.9882 | 0.168 | 3 / 24 / 3 | Not Sig | Not Sig |
| **Regime B** | $\Delta\mu = 0.05$ ms | 0.1801 | 0.0980 | 0.0957 | $+2.37\%$ | 0.0791 | 0.0941 | 0.332 | 5 / 24 / 1 | Not Sig | Not Sig |
| **Regime B** | $\Delta\mu = 0.10$ ms | 0.1586 | 0.1036 | 0.0986 | $+4.87\%$ | 0.0320 | 0.0528 | 0.411 | 9 / 18 / 3 | **Not Sig** | **Not Sig** |
| **Regime B** | $\Delta\mu = 0.20$ ms | 0.1389 | 0.1343 | 0.1227 | $+8.64\%$ | 0.5022 | 0.3715 | 0.124 | 9 / 15 / 6 | Not Sig | Not Sig |
| **Regime B** | $\Delta\mu = 0.50$ ms | 0.3722 | 0.1903 | 0.2119 | $-11.39\%$ | 0.2815 | 0.1564 | -0.200 | 13 / 12 / 5 | Not Sig | Not Sig |
| **Regime B** | $\Delta\mu = 1.00$ ms | 1.3233 | 0.4668 | 0.5230 | $-12.04\%$ | 0.1772 | 0.7882 | -0.253 | 15 / 6 / 9 | Not Sig | Not Sig |
| **Regime B** | $\Delta\mu = 2.00$ ms | 4.8482 | 1.0670 | 1.0640 | $+0.28\%$ | 0.9642 | 0.2000 | 0.008 | 17 / 6 / 7 | Not Sig | Not Sig |
| **Regime C** | $\sigma_{\text{mult}} = 1.0$ | 0.1043 | 0.1125 | 0.1025 | $+8.85\%$ | 0.3650 | 0.9882 | 0.168 | 3 / 24 / 3 | Not Sig | Not Sig |
| **Regime C** | $\sigma_{\text{mult}} = 2.0$ | 0.1043 | 0.1125 | 0.1025 | $+8.85\%$ | 0.3650 | 0.9882 | 0.168 | 3 / 24 / 3 | Not Sig | Not Sig |
| **Regime C** | $\sigma_{\text{mult}} = 5.0$ | 0.1043 | 0.1125 | 0.1025 | $+8.85\%$ | 0.3650 | 0.9882 | 0.168 | 3 / 24 / 3 | Not Sig | Not Sig |
| **Regime C** | $\sigma_{\text{mult}} = 10.0$ | 0.1043 | 0.1125 | 0.1025 | $+8.85\%$ | 0.3650 | 0.9882 | 0.168 | 3 / 24 / 3 | Not Sig | Not Sig |

---

## 4. Evaluation of Existing Claims A through E

### Claim A: Full SASP provides a 3.5–4.9% improvement over Mean-Only Sequencing
- **Independent Finding:** **UNSUPPORTED AS CONFIRMATORY EVIDENCE.**
- While the sample means in two isolated configurations ($w=10$ and $w=50$ at $\Delta\mu = 0.1$ ms) exhibit 3.83% and 4.87% lower cost with nominal uncorrected $p$-values of $0.038$ and $0.032$, these values represent exploratory subgroup findings across 18 tests.
- When correcting for the 18 simultaneous comparisons via Bonferroni ($\alpha = 0.00278$) or Benjamini-Hochberg FDR ($q = 0.05$), neither configuration survives.
- Furthermore, in 18 to 25 out of the 30 seeds, Full SASP and Mean-Only make identical decisions. Across the wider parameter space, Full SASP degrades performance by up to 12% relative to Mean-Only.

### Claim B: Both methods outperform FIFO by 20–78%
- **Independent Finding:** **PARTIALLY SUPPORTED WITH QUALIFICATIONS.**
- At wide link delay asymmetries ($\Delta\mu \ge 0.5$ ms), both predictive sequencing algorithms achieve massive gains over FIFO, peaking at **78.1% cost reduction** at $\Delta\mu = 2.0$ ms (FIFO cost 4.85 vs SASP 1.06).
- However, the "20–78%" range does not hold universally:
  - At equal link means ($\Delta\mu = 0.0$ ms), Mean-Only is actually **7.8% worse than FIFO** (0.1125 vs 0.1043), and Full SASP is only 1.7% better ($p = 0.365$).
  - At $\Delta\mu = 0.20$ ms, Mean-Only is only 3.3% better than FIFO.
- Headline claims must state that predictive sequencing provides 20%--78% reductions **under asymmetric link delays ($\Delta\mu \ge 0.5$ ms)**, but negligible or negative gains under equal link means.

### Claim C: At large mean differences or equal weights, both methods converge
- **Independent Finding:** **CONFIRMED FOR EQUAL WEIGHTS; QUALIFIED FOR LARGE DELTAS.**
- At equal weights ($w=1, 2$), Theorem 3 root $u^* = 0$, guaranteeing mathematically identical decisions ($p = 1.00$, 30/30 ties).
- At large mean differences ($\Delta\mu = 2.0$ ms), the mean cost difference is indeed negligible (+0.28%, $p = 0.964$). However, the two schedulers differ in 24 out of 30 seeds (17 wins for SASP, 7 wins for Mean-Only). A high $p$-value ($0.964$) reflects high variance across dissimilar decisions, not decision equivalence.

### Claim D: Variance awareness is the source of the improvement
- **Independent Finding:** **REFUTED AS PROVEN CAUSAL SOURCE.**
- In Regime C, variance scaling was never physically executed in the channel model due to the `WirelessChannel` bug.
- In Regime B, variance-aware scoring in Full SASP causes it to assign sequence numbers conservatively, leading to worse performance than Mean-Only at $\Delta\mu \in [0.5, 1.0]$ ms.
- The fundamental performance leap of SASP over FIFO is driven by **predictive arrival ordering based on means**, not variance tuning.

### Claim E: Complexity and overhead are acceptable
- **Independent Finding:** **CONFIRMED FOR TYPICAL TOPOLOGIES; QUALIFIED FOR WORST-CASE.**
- On the host Linux platform, measured decision times are:
  - 2 links, 2 flows: Mean $0.76\,\mu\text{s}$, Median $0.70\,\mu\text{s}$, p95 $0.82\,\mu\text{s}$, Max $61.5\,\mu\text{s}$
  - 3 links, 3 flows: Mean $0.87\,\mu\text{s}$, Median $0.82\,\mu\text{s}$, p95 $1.19\,\mu\text{s}$, Max $6.95\,\mu\text{s}$
  - 4 links, 8 flows: Mean $0.38\,\mu\text{s}$, Median $0.36\,\mu\text{s}$, p95 $0.51\,\mu\text{s}$, Max $6.07\,\mu\text{s}$
- The previously cited $16.3\,\mu\text{s}$ tail figure was an observed host-scheduling artifact and must not be described as strictly within the $16\,\mu\text{s}$ SIFS boundary without qualification.

---

## 5. Exact Commands to Reproduce Statistical Validation

To reproduce the complete independent statistical validation:
```bash
cd /home/adhyan/Desktop/wifi7_mlo_hol
.venv/bin/python3 experiments/ablation_phase6/independent_statistical_audit.py
```
Output artifact generated: `experiments/ablation_phase6/audit_statistical_summary.csv`.

---
*End of Final Ablation Statistical Validation Report.*
