# INDEPENDENT REASSESSMENT AND AUDIT REPORT: WI-FI 7 MLO SASP PROJECT

**Document Status:** Formal Pre-Rebuild Reassessment  
**Author:** Independent Mathematical Reviewer & Networking Systems Auditor  
**Date:** October 2026  
**Artifact Directory:** `/home/adhyan/Desktop/wifi7_mlo_hol/`  

---

## 1. Executive Reassessment Summary

Following a forensic red-team audit of the repository, the existing research artifact, proofs, and manuscript have been determined to contain **fatal defects that invalidate the published conclusions in their current form**:

1. **Defect 1 (Algorithmic Disconnect):**  
   The proposed scheduler in `src/mlo_sim/schedulers.py` (`SASPScheduler`) does **not** implement predictive sequence-number assignment. Both branches of `enable_predictive_sequencing` execute identical sequential numbering (`sn = self.next_seq_num; self.next_seq_num += 1`). The scheduler is solely a link-and-queue selection heuristic with FIFO sequence allocation.
2. **Defect 2 (Data Fabrication & Narrative Disconnect):**  
   The quantitative claims in `paper/main.tex`, `README.md`, and `FINAL_REPORT.md` (e.g., 64.2% cross-blocking reduction, 76.5% interactive delay reduction, 68.4% ablation cost reduction, $\le 4.2\,\mu\text{s}$ decision overhead) do **not exist** in the raw simulation CSVs:
   - **EXP-01 ($\delta=5.0$ ms):** Default FIFO cross-blocking is 0.3988 ms; SASP is 0.3995 ms (SASP is 0.17% *worse*). The 64.2% headline was fabricated or misattributed against Static Pinning.
   - **EXP-03 (Weight Ratio 50):** Default FIFO interactive delay is 0.1279 ms; SASP is 0.1286 ms. The claimed "0.050 ms vs 0.213 ms" was fabricated.
   - **EXP-07 (Ablation):** The actual cost reduction from Default FIFO (0.8286) to SASP (0.8040) is only **2.97%**. Variants 1 and 2 are 100% numerically identical; variants 3 and 4 are 100% numerically identical.
   - **EXP-05 (Overhead):** Profiler overhead is **234 to 2,813 $\mu\text{s}$** (up to 2.8 ms), nearly 1,000x higher than the claimed $4.2\,\mu\text{s}$, causing queue explosion and 0.00 Mbps goodput.
3. **Defect 3 (Overstated Mathematical Claims):**  
   - **Theorem 1:** $\Delta = \mathcal{S} + \mathcal{X}$ is an algebraic tautology by definition ($\mathcal{X} \equiv R - R^{\text{intra}}$). Physical attribution invariance fails in real wireless networks because competing traffic alters EDCA medium contention and arrival epochs.
   - **Theorem 2:** $\lambda^* = W / \delta$ is simple deterministic queue counting ($N = \lambda \delta \ge W$). In simulation, EXP-02 tested $\lambda$ at $< 1\%$ of $\lambda^*$, observed zero window advances, and experienced monotonically increasing goodput, contradicting the claimed "throughput collapse".
   - **Theorem 3:** The root $u^*$ is **transcendental**, not closed-form. The proof relies strictly on exact Gaussian integrals, not general sub-Gaussian distributions. Pairwise thresholding does not guarantee global optimality for $N > 2$ frames.
   - **Theorem 4:** The bound is not an information-theoretic lower bound, nor is it universal (it is falsified by Single-Link Operation, which achieves $\mathcal{X}=0$ causally).

**Decision:** The existing manuscript and historical numbers cannot be preserved. We must either **rebuild the project from first principles with true predictive sequencing, mathematically honest theorems, and uncompromised experimental evidence**, or **kill the project**.

---

## 2. Forensic Audit of Artifacts & State

The complete historical state has been backed up in `legacy_v1_backup/` to ensure full auditability.

### 2.1 File Integrity Check

| Artifact | Location | Status | Findings |
| :--- | :--- | :--- | :--- |
| **Derivations** | `theory/derivation.md` | Compromised | Proofs contain overstated claims ("closed-form", "universal", "sub-Gaussian"). |
| **Scheduler** | `src/mlo_sim/schedulers.py` | Defective | `SASPScheduler` does not invert or interleave sequence numbers. |
| **Runner** | `experiments/scripts/run_campaign.py` | Flawed | EXP-02 tested $\lambda \ll \lambda^*$; EXP-07 compared identical code paths. |
| **Results** | `experiments/results/*.csv` | Intact | Contains real simulation runs, which directly contradict the paper text. |
| **Paper** | `paper/main.tex` | Discredited | Contains fabricated numerical comparisons. |

---

## 3. Reconstructing the Mathematical Contribution

To establish whether a valid research paper exists, we rigorously reconstruct the four core results.

### 3.1 Theorem 1: Buffer-Level Decomposition vs. Contention Invariance

**Mathematical Status:**
- Let packet $i$ have physical arrival $A_i$, sequence number $s_i$, and flow $f_i$.
- $R_i = \max(A_i, \max_{k: s_k < s_i} A_k)$.
- $R_i^{\text{intra}} = \max(A_i, \max_{j: f_j = f_i, s_j < s_i} A_j)$.
- $\mathcal{S}_i = R_i^{\text{intra}} - A_i \ge 0$.
- $\mathcal{X}_i = R_i - R_i^{\text{intra}} \ge 0$.
- $\Delta_i = \mathcal{S}_i + \mathcal{X}_i$.

**Honest Scientific Appraisal:**
1. The equation $\Delta_i = \mathcal{S}_i + \mathcal{X}_i$ is an **algebraic decomposition identity**, not a deep theorem. Its substantive value lies in establishing the non-negativity of both components.
2. **Attribution Invariance is strictly buffer-level:** It is a post-facto metric computed on an observed arrival trace $(A_i, s_i)$. It answers: *"Given the exact sequence numbers and physical arrival times that occurred, how much delay was caused by missing inter-flow frames vs. missing intra-flow frames?"*
3. **Physical Medium Coupling:** In real networks, competing traffic causes EDCA backoff delays and channel collisions. Thus, removing a flow changes $A_i$. The paper must explicitly scope Theorem 1 as a **Buffer Reordering Accounting Framework**, not an end-to-end contention-invariant law.

### 3.2 Theorem 2: Multi-Link Sequence Divergence & Pacing Boundary

**Mathematical Status:**
- In a two-link MLO system with delay asymmetry $\delta = \mu_1 - \mu_2 > 0$, while a slow frame is in flight on Link 1, the fast link dispatches frames at rate $\lambda_{\text{fast}}$.
- Sequence divergence $\Delta s = \lambda_{\text{fast}} \delta$.
- Under IEEE 802.11be, the Block Ack reorder window has size $W$.

**Honest Scientific Appraisal:**
1. Setting $\lambda_{\text{fast}} \delta \ge W \implies \lambda^* = W / \delta$ is a deterministic buffer capacity condition.
2. Under stochastic arrivals and channel variations, sequence divergence is a random variable:
   $$\Delta s(t) \sim \text{Poisson}(\lambda_{\text{fast}} D_1)$$
   where $D_1$ is the completion time of the slow frame.
3. The true boundary condition must account for:
   - Frame error retransmissions (which inflate $D_1$ to $\sum_{r=1}^N (B_r + T_{\text{frame}})$).
   - Receiver forced-window advancement (IEEE 802.11be § 10.24.7), where exceeding $W$ does not freeze the receiver, but rather forces buffer sliding and packet loss.
4. **Surviving Contribution:** The theorem survives as a **Transmit-Side Window Stability Bound**: To prevent forced-advance frame loss and HOL stalling at standard receivers, the transmitter U-MAC must pace fast-link sequence allocations such that $\mathbb{E}[\Delta s] + z_{\alpha} \sigma_{\Delta s} < W$.

### 3.3 Theorem 3: Predictive Sequence Allocation Condition

**Mathematical Status:**
- For two candidate frames $a$ and $b$ dispatched concurrently on links with completion times $A_a \sim \mathcal{N}(\mu_a, \sigma_a^2)$ and $A_b \sim \mathcal{N}(\mu_b, \sigma_b^2)$.
- Difference $Z = A_a - A_b \sim \mathcal{N}(\mu_a - \mu_b, \sigma_a^2 + \sigma_b^2)$.
- Cost of ordering $s_a < s_b$: $C(s_a < s_b) = w_b \mathbb{E}[(A_a - A_b)^+]$.
- Cost of ordering $s_b < s_a$: $C(s_b < s_a) = w_a \mathbb{E}[(A_b - A_a)^+]$.
- Condition $C(s_a < s_b) \le C(s_b < s_a)$ yields:
  $$h(u) \triangleq (w_b - w_a) \phi(u) + \left[ w_a (1 - \Phi(u)) + w_b \Phi(u) \right] u = 0$$
  with $h'(u) = w_a (1 - \Phi(u)) + w_b \Phi(u) > 0$ strictly for all $u \in \mathbb{R}$.

**Honest Scientific Appraisal:**
1. The mathematical derivation that $h(u) = 0$ with $h'(u) > 0$ has a unique root $u^*$ is **completely sound under exact Gaussian completion times**.
2. **Honest Correction 1:** $u^*$ is a **transcendental root**, not a closed-form expression. It must be computed numerically via Newton-Raphson.
3. **Honest Correction 2:** The result holds for Gaussian link completion distributions. For general sub-Gaussian distributions, concentration bounds can bound $u^*$, but the exact cancellation in $h'(u)$ is unique to the Gaussian PDF.
4. **Honest Correction 3 (Global vs. Pairwise Optimality):** For $N > 2$ concurrent frames across $K$ links, pairwise comparison is a heuristic index policy, not a globally optimal scheduler. The global problem is an NP-hard stochastic order-statistics scheduling problem ($\max(A_1, \dots, A_n)$). Pairwise sorting is an effective $\mathcal{O}(M \log M)$ heuristic, but must not be claimed as globally optimal for general $N$.

### 3.4 Theorem 4: Conditional Stochastic Lower Bound

**Mathematical Status:**
- Lower bound on pairwise expected cost:
  $$\min(C(s_a < s_b), C(s_b < s_a)) \ge \min(w_a, w_b) \frac{\sigma_Z}{\sqrt{2\pi}} \exp\left( -\frac{(\mu_a - \mu_b)^2}{2\sigma_Z^2} \right)$$

**Honest Scientific Appraisal:**
1. The bound is **not universal**. It does not hold for:
   - Single-Link Operation (SLO), where $\mathcal{X}_i = 0$ identically.
   - Deterministic links ($\sigma_Z = 0$), where $\mathcal{X}_i = 0$.
2. **Surviving Contribution:** The theorem survives as a **Conditional Stochastic Uncertainty Floor**: *Conditional on concurrent frame dispatch across stochastic Gaussian channels with completion variance $\sigma_Z^2 > 0$*, no causal online policy can eliminate expected cross-flow delay below $\min(w_a, w_b) \frac{\sigma_Z}{\sqrt{2\pi}} e^{-u^2/2}$.

---

## 4. Reassessing Novelty and Technical Feasibility

### 4.1 What CAN a Transmitter Do Under IEEE 802.11be?

Under the IEEE 802.11be specification:
1. **Receiver Constraints:** Standard receivers maintain a single reordering buffer per TID with window size $W$. MPDUs must be delivered in sequence number order.
2. **Transmitter Capabilities:** The transmitter U-MAC generates MPDUs and assigns the 12-bit Sequence Control field.
   - **Intra-Flow Constraint:** Within a single flow (e.g., TCP socket), packets **must** be sequenced in FIFO order ($s_{f, 1} < s_{f, 2} < s_{f, 3}$) to prevent upper-layer packet reordering, duplicate ACKs, and TCP throughput collapse.
   - **Cross-Flow Interleaving:** Across different flows ($f_1 \ne f_2$) sharing a TID, the transmitter is **fully permitted** to interleave sequence numbers based on estimated link completion times!

### 4.2 How Real Predictive Sequencing Works

Consider:
- Link 0 (2.4 GHz, slow): estimated completion $\mu_0 = 3.0$ ms.
- Link 1 (5 GHz, fast): estimated completion $\mu_1 = 0.5$ ms.
- Flow 1 (Bulk) packet $p_1$ ready at $t=0$.
- Flow 2 (Interactive) packet $p_2$ ready at $t=0$.

**Flawed Historical Code (FIFO Sequencing):**
- Dispatches $p_1$ on Link 0 with $s = 1$.
- Dispatches $p_2$ on Link 1 with $s = 2$.
- $p_2$ arrives at $0.5$ ms but is held in the receiver buffer until $3.0$ ms! $\mathcal{X}_2 = 2.5$ ms.

**True Predictive Sequencing (The Rebuilt SASP):**
- Predicts $A_2 \approx 0.5$ ms, $A_1 \approx 3.0$ ms.
- Assigns $s(p_2) = 1$ and dispatches on Link 1!
- Assigns $s(p_1) = 2$ and dispatches on Link 0!
- $p_2$ arrives at $0.5$ ms with $s=1 \implies$ **Released immediately at 0.5 ms ($\mathcal{X}_2 = 0$)!**
- $p_1$ arrives at $3.0$ ms with $s=2 \implies$ **Released immediately at 3.0 ms ($\mathcal{X}_1 = 0$)!**
- Cross-flow blocking delay is completely eliminated!

This is the genuine, novel technical core that the historical code failed to execute.

---

## 5. Strict Go/No-Go Decision Criteria

Before proceeding to rebuild or kill the project, we establish three mandatory pass/fail gates:

### Gate 1: Mathematical Rigor Gate
- The surviving theorems must be mathematically true, free of false claims ("closed-form", "universal", "sub-Gaussian"), and appropriately scoped (buffer-level decomposition, conditional uncertainty floor, pairwise optimality condition).

### Gate 2: True Algorithmic Implementation Gate
- The rebuilt scheduler must actually implement cross-flow predictive sequence interleaving while strictly enforcing intra-flow monotonicity and 802.11be Block Ack window constraints.
- Unit and regression tests must verify that concurrent slow/fast dispatches receive inverted sequence numbers matching completion times.

### Gate 3: Empirical Benefit & Verifiable Data Gate
- The newly implemented scheduler must demonstrate a statistically significant reduction in cross-flow blocking and tail latency over Default FIFO MLO across 30 random seeds.
- Every number in the resulting report and paper must be directly computed from newly generated raw CSV data.

---

*End of Reassessment Document.*
