# PREREGISTRATION PLAN: Wi-Fi 7 MLO Cross-Flow HOL ns-3 Independent Validation & Ablation

**Protocol Identifier:** PREREG-WIFI7-MLO-HOL-NS3-20261013  
**Date:** October 13, 2026  
**Simulator Target:** ns-3.47 (Pinned Release)  
**Study Scope:** Transmitter-Side Sequence-Aware Scheduling Policy (SASP), Mean-Only Sequencing, and Native FIFO Reference under IEEE 802.11be Multi-Link Operation (STR Mode) with Shared TID/BA Reordering Context.

---

## 1. Research Question & Algorithmic Definitions

### 1.1 Core Research Question
Under IEEE 802.11be Wi-Fi 7 Multi-Link Operation (MLO) Simultaneous Transmit and Receive (STR) mode, where heterogeneous application flows share a single Traffic Identifier (TID) and receiver Block Ack (BA) reordering context, can a transmitter-side sequence-assignment policy using estimated completion times reduce receiver-side cross-flow Block Ack reordering delay without modifying the receiver?

### 1.2 Evaluated Scheduling Arms
1. **Arm A: Native FIFO Reference (`DefaultFIFO`)**
   - Packets enqueued into the shared TID MAC queue are allocated sequence numbers in monotonic arrival (FIFO) order at lower-MAC handoff.
   - Dispatched across available links based on standard link eligibility.
2. **Arm B: Mean-Only Sequencing (`MeanOnly`)**
   - Evaluates eligible candidate packets across links using causal estimates of physical link completion time $\hat{\mu}_k$.
   - Inverts sequence assignment based strictly on predicted scalar mean completion times $\hat{T}_{i,k} = t + \hat{\mu}_k$, omitting variance-aware thresholds.
3. **Arm C: Full SASP (`FullSASP`)**
   - Applies the pairwise Gaussian threshold rule $u^*(w_a, w_b)$ (Theorem 3) when exactly $N=2$ candidate packets are jointly eligible.
   - For candidate sets of $N \ge 3$, orders candidates by scalar expected completion time $\hat{T}_{i,k}$ (multi-frame heuristic).
   - Operates strictly causally: predictions use only completed transmissions, ACK feedback, and link state available at decision epoch.

---

## 2. Experimental Design & Configuration Grids

### 2.1 Topology & Workload
- **MLD Endpoints:** 1 AP MLD and 1 non-AP STA MLD.
- **Links:** 2 simultaneous active links operating in STR mode (Link 0: 5 GHz, Link 1: 6 GHz).
- **Traffic Model:** Shared TID 0, UDP transport.
  - Flow 1 (Latency-Sensitive): Periodic voice/interactive packets (160-byte payload, fixed generation interval). Weight $w_1 = 10.0$ (or configured ratio).
  - Flow 2 (Bulk Background): Poisson/CBR stream (1200-byte payload) generating link queue occupancy. Weight $w_2 = 1.0$.

### 2.2 Calibration Targets
- **Reference Capacity ($C_{ref}$):** Measured scheduler-neutral saturation throughput under symmetric links.
- **Link Asymmetry Targets:**
  - $A_0$ (Approximately Symmetric): Median completion-time ratio $\mu_2 / \mu_1 \approx 1.0$.
  - $A_1$ (Moderate Asymmetry): Median completion-time ratio $\mu_2 / \mu_1 \approx 1.5$.
  - $A_2$ (Strong Asymmetry): Median completion-time ratio $\mu_2 / \mu_1 \approx 3.0$.
- **Offered Load Targets:**
  - $L_0$: $0.30 \times C_{ref}$ (Light load).
  - $L_1$: $0.60 \times C_{ref}$ (Medium load).
  - $L_2$: $0.85 \times C_{ref}$ (Heavy load, near saturation).

### 2.3 Main Experiment Grid (3 x 3 x 30 x 3 = 810 Runs)
- Asymmetry Levels: $\{A_0, A_1, A_2\}$ (3)
- Load Levels: $\{L_0, L_1, L_2\}$ (3)
- Random Seeds: $\{1, 2, \dots, 30\}$ (30 paired seeds)
- Scheduler Arms: $\{NativeFIFO, MeanOnly, FullSASP\}$ (3)
- **Total Main Simulation Runs:** 810

### 2.4 Variance-Aware Threshold Ablation Grid (3 x 3 x 30 x 3 = 810 Runs)
- Fixed Mean Delta: $|\mu_1 - \mu_2| \le 0.2$ ms.
- Contention/Service Variance Ratios: $\sigma_2^2 / \sigma_1^2 \in \{1.0, 2.0, 4.0\}$ (3)
- Flow Priority Ratios: $w_1 / w_2 \in \{1, 10, 50\}$ (3)
- Random Seeds: $\{1, 2, \dots, 30\}$ (30 paired seeds)
- Scheduler Arms: $\{NativeFIFO, MeanOnly, FullSASP\}$ (3)
- **Total Ablation Simulation Runs:** 810

---

## 3. Endpoints & Metrics

### 3.1 Primary Endpoint
- **Mean Cross-Flow Receiver Reordering Wait of Latency-Sensitive Packets ($\bar{\mathcal{X}}_{ls}$):**
  $$\bar{\mathcal{X}}_{ls} = \frac{1}{|\mathcal{P}_{ls}|} \sum_{p \in \mathcal{P}_{ls}} \mathcal{X}_p \quad \text{[ms]}$$
  Where $\mathcal{X}_p = \max(0, \text{deliver\_time}(p) - \text{rx\_time}(p))$ attributable to missing lower-sequence frames belonging to other flows within the same TID.

### 3.2 Secondary Endpoints
1. Latency-sensitive end-to-end delay (Median, p95, p99) [ms].
2. Overall Mean Cross-Flow Reordering Wait ($\bar{\mathcal{X}}$) [ms].
3. Mean Within-Flow Reordering Wait ($\bar{\mathcal{S}}$) [ms].
4. Total Block Ack Waiting Time [ms].
5. Application Packet Delivery Ratio (PDR) [%].
6. Goodput per flow [Mbps].
7. MAC Retry and Loss Count.
8. Receiver Reorder Buffer Occupancy distribution.
9. Frequency of Inverted Decisions between FullSASP and MeanOnly [%].

---

## 4. Statistical Analysis Plan & Hypothesis Testing

### 4.1 Primary Confirmatory Hypothesis
- **Hypothesis $H_0$:** Under strong link asymmetry ($A_2$) and heavy offered load ($L_2$), there is no difference in mean cross-flow reordering wait between Full SASP and Native FIFO:
  $$\mu_{\bar{\mathcal{X}}, SASP} = \mu_{\bar{\mathcal{X}}, FIFO}$$
- **Alternative $H_1$:** Full SASP achieves a strictly lower mean cross-flow reordering wait than Native FIFO:
  $$\mu_{\bar{\mathcal{X}}, SASP} < \mu_{\bar{\mathcal{X}}, FIFO}$$
- **Statistical Test:** Two-sided paired Student's t-test (and non-parametric Wilcoxon signed-rank test as sensitivity check) on the 30 paired random seeds.
- **Significance Level:** $\alpha = 0.05$.
- **Effect Reporting:** Absolute paired difference $\Delta = \bar{\mathcal{X}}_{SASP} - \bar{\mathcal{X}}_{FIFO}$, 95% Confidence Interval, and relative percentage reduction.

### 4.2 Secondary Confirmatory Analysis (Mean-Only vs Full SASP)
- **Comparison:** Full SASP vs Mean-Only across all 9 main configurations and 9 ablation configurations.
- **Family-Wise Error Rate (FWER) Control:** Holm-Bonferroni step-down procedure applied within each comparison family. Both raw $p$-values and Holm-adjusted $p$-values will be reported.
- **Equivalence Bound:** Practical equivalence threshold pre-declared at $\pm 5\%$ relative change. If $| \Delta_{SASP - MeanOnly} | < 0.05 \times \bar{\mathcal{X}}_{MeanOnly}$, policies are practically indistinguishable.

### 4.3 Outlier & Invalidation Rules
- Any simulation terminating with an unhandled exception or nonzero exit code will be preserved in `logs/` and excluded from the statistical sample, with root cause documented.
- No post-hoc exclusion based on favorable or unfavorable metric values.
