# Reconstructed Theoretical Counterexamples and Boundary Cases

**Purpose:** Rigorous documentation of edge cases, failure modes, and counterexamples that delineate the exact boundary conditions of Theorems 1–4.

---

## 1. Counterexample 1: Medium Contention Breaks End-to-End Attribution Invariance

### Scenario
- Consider Flow 1 operating alone in the network.
- Packets $p_1$ and $p_2$ arrive at $t=0.0$ ms.
- Because there is no cross-traffic, Link 1 has zero contention. EDCA contention window remains at $CW_{\min} = 15$.
- Packet $p_1$ completes transmission at $A_1 = 1.0$ ms. Packet $p_2$ completes at $A_2 = 1.2$ ms.
- With sequence numbers $s_1 = 1, s_2 = 2$:
  $$R_2^{\text{intra}} = \max(A_2, A_1) = \max(1.2, 1.0) = 1.2\text{ ms}$$
  $$\mathcal{S}_2 = R_2^{\text{intra}} - A_2 = 1.2 - 1.2 = 0.0\text{ ms}$$

### Contention Distortion
- Now introduce Flow 2 (bulk background traffic).
- Packets from Flow 2 contend on Link 1 concurrently with packet $p_1$ of Flow 1.
- A wireless collision occurs; Link 1 doubles its contention window to $CW = 31$, incurring random backoff slots.
- Consequently, packet $p_1$ completes late at $A_1 = 3.0$ ms.
- Meanwhile, packet $p_2$ of Flow 1 was dispatched on clear Link 2 and completed at $A_2 = 1.2$ ms.
- Evaluating the decomposition on this new trace:
  $$R_2^{\text{intra}} = \max(A_2, A_1) = \max(1.2, 3.0) = 3.0\text{ ms}$$
  $$\mathcal{S}_2 = R_2^{\text{intra}} - A_2 = 3.0 - 1.2 = 1.8\text{ ms}$$

### Implication
Flow 1's "self-blocking delay" $\mathcal{S}_2$ increased from $0.0$ ms to $1.8$ ms simply because Flow 2 was added to the channel.  
**Conclusion:** Attribution invariance holds **strictly post-facto on an observed trace with fixed physical arrival times**. It does not hold end-to-end across counterfactual network states with physical medium contention.

---

## 2. Counterexample 2: Single-Link Operation Falsifies Universal Causal Floor

### Scenario
- An MLD transmitter has two active links: Link 1 (2.4 GHz, $\mu_1 = 3.0$ ms, $\sigma_1 = 0.5$ ms) and Link 2 (5 GHz, $\mu_2 = 1.0$ ms, $\sigma_2 = 0.2$ ms).
- Two flows (Flow $A$ and Flow $B$) share TID 0.
- The project's historical Theorem 4 claimed that for *any* online causal scheduler, expected cross-flow delay is strictly lower-bounded by:
  $$\mathbb{E}[\mathcal{X}] \ge \min(w_a, w_b) \frac{\sigma_Z}{\sqrt{2\pi}} e^{-u^2/2} > 0$$

### Causal Policy Execution
- Consider a causal scheduler that selects **Single-Link Operation (SLO)**, routing all frames from both Flow $A$ and Flow $B$ exclusively over Link 2 in FIFO order.
- On Link 2, physical transmissions occur sequentially over a single radio interface.
- Frames complete physical transmission in strict FIFO order: $A_1 < A_2 < A_3 < \dots$
- Sequence numbers are assigned in FIFO order: $s_1 < s_2 < s_3 < \dots$
- At the receiver reorder buffer:
  $$R_i = \max(A_i, \max_{k: s_k < s_i} A_k) = \max(A_i, A_{i-1}) = A_i$$
  $$\Delta_i = R_i - A_i = 0.0\text{ ms}$$
  $$\mathcal{X}_i = R_i - R_i^{\text{intra}} = 0.0\text{ ms}$$

### Implication
The causal single-link scheduler achieves **exact zero cross-flow blocking delay** ($\mathcal{X} = 0$).  
**Conclusion:** Theorem 4 is not universal. It holds *strictly conditional on concurrent frame dispatch across stochastic parallel links*.

---

## 3. Counterexample 3: Why Simple Pairwise Comparison is Sub-Optimal for $N \ge 3$ Frames

### Scenario
- Consider three candidate frames ready for dispatch across three links:
  - Frame $a$ (Flow 1, weight $w_a = 1$): $A_a \sim \mathcal{N}(5.0, 1.0^2)$.
  - Frame $b$ (Flow 2, weight $w_b = 5$): $A_b \sim \mathcal{N}(3.0, 0.5^2)$.
  - Frame $c$ (Flow 3, weight $w_c = 10$): $A_c \sim \mathcal{N}(2.0, 0.2^2)$.
- In a Block Ack reorder buffer, when sequence numbers are assigned as a permutation $\pi = (s_1, s_2, s_3)$, the release time of packet $i$ depends on the **joint supremum of all preceding arrivals**:
  $$R_i = \max(A_i, \max_{k \in \mathcal{P}_i} A_k)$$

### Order Statistics Non-Linearity
- For three variables, $\mathbb{E}[\max(A_a, A_b, A_c)]$ cannot be decomposed into the sum of pairwise expectations $\mathbb{E}[(A_a - A_b)^+] + \mathbb{E}[(A_b - A_c)^+]$.
- By Clark's formula (1961), the distribution of $\max(X, Y)$ is skewed (non-Gaussian) even when $X$ and $Y$ are jointly normal.
- A sequential greedy pairwise application of Theorem 3 may choose $s_c < s_b < s_a$, but if Link 1 exhibits high variance tail risk, joint multi-packet scheduling requires evaluating the joint cumulative distribution function (CDF):
  $$F_{\max}(t) = \prod_{k \in \mathcal{P}_i} \Phi\left(\frac{t - \mu_k}{\sigma_k}\right)$$

### Implication
Pairwise index sorting via Theorem 3 is an efficient $\mathcal{O}(M \log M)$ heuristic, but **not a globally optimal policy for general $N$ in-flight packets**.

---

*End of Counterexamples.*
