# Comprehensive Experiment Plan

**Subject:** Empirical Validation of Cross-Flow Head-of-Line Blocking and Sequence-Aware Scheduling in Wi-Fi 7 MLO  
**Statistical Discipline:** Independent replications with recorded pseudo-random seeds, $95\%$ confidence intervals, explicit hypothesis testing.

---

## 1. Experimental Campaign Matrix

| Experiment ID | Focus / Objective | Independent Variables | Fixed Parameters | Dependent Metrics | Hypotheses Tested |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **EXP-01** | **Link Asymmetry Sweep** | Delay asymmetry $\delta \in [0.1, 5.0]$ ms (varying Link 1 vs. Link 2 data rates and contention) | 2 links, $W=64$, $\Lambda = 500$ pkt/s, 2 flows ($w_1=w_2=1$), 30 seeds | Mean $(\mathcal{S}, \mathcal{X}, \Delta)$, p95/p99 latency, ratio $\mathcal{X}/\Delta$ | **H1, H3** |
| **EXP-02** | **BA Window Collapse Boundary** | Normalized load $\lambda / \lambda^* \in [0.2, 2.5]$, where $\lambda^* = W / \delta$ | $W \in \{64, 256\}$, $\delta = 1.0$ ms, 30 seeds | Goodput, window stall frequency, p99 latency | **H2** |
| **EXP-03** | **Flow Priority Heterogeneity** | Priority weight ratio $w_2 / w_1 \in [1, 50]$ (bulk vs. interactive) | 2 links, $\delta = 2.0$ ms, $\Lambda = 400$ pkt/s, 30 seeds | Per-flow latency (p50, p95, p99), flow completion times, weighted cost | **H4** |
| **EXP-04** | **Channel Contention and Burst Loss** | Frame error rate $p \in [0.0, 0.3]$, Gilbert-Elliott burstiness | 2 links, $W=64$, retry limit $L_{\max}=7$, 30 seeds | Retransmission count, recovery latency, cross-flow blocking | **H3** |
| **EXP-05** | **Multi-Link Scalability** | Link count $K \in \{2, 3, 4\}$, Flow count $M \in \{2, 4, 8\}$ | Symmetric and asymmetric links, $W=256$, 30 seeds | Scheduling compute overhead ($\mu\text{s}$), aggregate goodput, blocking reduction | **H3** |
| **EXP-06** | **Sensitivity to Estimation Errors** | Variance estimation bias $\epsilon_\sigma \in [-50\%, +50\%]$, mean delay bias $\epsilon_\mu \in [-50\%, +50\%]$ | Asymmetric links, $W=64$, 30 seeds | Relative degradation in cross-flow blocking vs. Oracle and default FIFO | **H5** |
| **EXP-07** | **Ablation Study** | Modular components: (1) Baseline FIFO, (2) Link Dispatch only, (3) Mean-only Sequencing, (4) Full SASP | Asymmetric links, $W=64$, asymmetric weights, 30 seeds | Decomposition of gain attributable to each algorithmic component | **H3, H4** |

---

## 2. Metrics Definition and Collection Protocol

1. **Reordering Delay Attribution:**
   - Physical Arrival Time: $A_i$
   - Intra-Flow Release Bound: $R_i^{\text{intra}} = \max(A_i, \max_{j: f_j = f_i, s_j < s_i} A_j)$
   - Global Release Time: $R_i = \max(A_i, \max_{k: s_k < s_i} A_k)$
   - Self-Blocking: $\mathcal{S}_i = R_i^{\text{intra}} - A_i$
   - Cross-Flow Blocking: $\mathcal{X}_i = R_i - R_i^{\text{intra}}$
   - Total Reorder Stall: $\Delta_i = R_i - A_i = \mathcal{S}_i + \mathcal{X}_i$
2. **Network Performance Metrics:**
   - Throughput (Mbps): Total bytes delivered to LLC / Total simulation time.
   - Goodput (Mbps): Useful application payload delivered in-order without duplicates.
   - Tail Latency: Empirical 50th, 95th, and 99th percentiles of packet end-to-end delay ($R_i - t_i^{\text{arr}}$).
   - Window Stall Ratio: Fraction of time that in-flight frames span $\ge W$ unacknowledged sequence numbers.
3. **Computational Complexity Metrics:**
   - Wall-clock CPU time per scheduling decision ($\mu\text{s}$ on Intel Core i7-13620H).

---

## 3. Statistical Execution Guidelines

- Each scenario is executed across $N_{\text{runs}} = 30$ independent Monte Carlo replications with explicit random seeds (e.g., seeds `1001` through `1030`).
- Results are reported as mean $\pm 95\%$ Student-t confidence intervals.
- Two-sample Welch's t-test and Kolmogorov-Smirnov tests are executed to establish statistical significance ($p < 0.001$).
- Raw per-packet traces and summary CSV files are stored in `experiments/raw/` and `experiments/results/`.
- Figures are automatically generated from raw summary CSVs using Python matplotlib and saved to `experiments/plots/`.
