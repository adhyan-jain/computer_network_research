# Reconstructed Theoretical Counterexamples and Boundary Cases

**Purpose:** Rigorous documentation of edge cases, mathematical falsifications, and counterexamples that delineate the exact boundary conditions of Theorems 1–4.

---

## 1. Counterexample 1: Medium Contention Breaks End-to-End Causal Attribution Invariance

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

## 2. Counterexample 2: Single-Link Operation Falsifies Unconditioned Lower Bounds

### Scenario
- An MLD transmitter has two active links: Link 1 (2.4 GHz, $\mu_1 = 3.0$ ms, $\sigma_1 = 0.5$ ms) and Link 2 (5 GHz, $\mu_2 = 1.0$ ms, $\sigma_2 = 0.2$ ms).
- Two flows (Flow $A$ and Flow $B$) share TID 0.
- A causal scheduler selects **Single-Link Operation (SLO)**, routing all frames from both Flow $A$ and Flow $B$ exclusively over Link 2 in FIFO order.
- On Link 2, physical transmissions occur sequentially over a single radio interface.
- Frames complete physical transmission in strict FIFO order: $A_1 < A_2 < A_3 < \dots$
- Sequence numbers are assigned in FIFO order: $s_1 < s_2 < s_3 < \dots$
- At the receiver reorder buffer:
  $$R_i = \max(A_i, \max_{k: s_k < s_i} A_k) = \max(A_i, A_{i-1}) = A_i$$
  $$\Delta_i = R_i - A_i = 0.0\text{ ms}$$
  $$\mathcal{X}_i = R_i - R_i^{\text{intra}} = 0.0\text{ ms}$$

### Implication
The causal single-link scheduler achieves **exact zero cross-flow blocking delay** ($\mathcal{X} = 0$).  
**Conclusion:** Theorem 4 is not universal across all online policies. It holds *strictly conditional on concurrent frame dispatch across stochastic parallel links*.

---

## 3. Counterexample 3: Order Statistics Non-Linearity Breaks Global Optimality for $N \ge 3$ Frames

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
- A sequential greedy pairwise application of Theorem 3 sorts candidate frames by their pairwise indices, but joint multi-packet scheduling requires evaluating the joint cumulative distribution function:
  $$F_{\max}(t) = \prod_{k \in \mathcal{P}_i} \Phi\left(\frac{t - \mu_k}{\sigma_k}\right)$$

### Implication
Pairwise index sorting via Theorem 3 is an efficient $\mathcal{O}(M \log M)$ heuristic, but **not a globally optimal policy for general $N \ge 3$ in-flight packets**.

---

## 4. Counterexample 4: Numerical Falsification of the Claimed $\sigma_Z \phi(u)$ Lower Bound

### Scenario
- Consider frames $a$ and $b$ with equal weights $w_a = w_b = 1.0$.
- Let $Z = A_a - A_b \sim \mathcal{N}(d, \sigma_Z^2)$ with $\sigma_Z = 1.0$ and mean asymmetry $d = 2.0$, so $u = d / \sigma_Z = 2.0$.
- The historical claim asserted:
  $$\min(C(s_a < s_b), C(s_b < s_a)) \ge \min(w_a, w_b) \sigma_Z \phi(u)$$
- Evaluating the claimed lower bound at $u = 2.0$:
  $$\min(w_a, w_b) \sigma_Z \phi(2.0) = 1.0 \times 1.0 \times \frac{1}{\sqrt{2\pi}} e^{-2^2 / 2} \approx 0.05399$$

### Actual Cost Evaluation
- Now compute the actual cost of assigning $s_b < s_a$:
  $$C(s_b < s_a) = w_a \mathbb{E}[(-Z)^+] = \sigma_Z \left[ \phi(u) - u (1 - \Phi(u)) \right]$$
- For $u = 2.0$:
  $$\phi(2.0) \approx 0.05399$$
  $$\Phi(2.0) \approx 0.97725 \implies 1 - \Phi(2.0) \approx 0.02275$$
  $$u (1 - \Phi(u)) = 2.0 \times 0.02275 = 0.04550$$
  $$C(s_b < s_a) = 0.05399 - 0.04550 = 0.00849$$
- Therefore:
  $$\min(C(s_a < s_b), C(s_b < s_a)) \le C(s_b < s_a) = 0.00849 < 0.05399$$

### Implication
The actual optimal cost ($0.00849$) is **more than 6 times smaller** than the claimed lower bound ($0.05399$).  
**Conclusion:** The claimed lower bound is mathematically false for all $u > 0$ because $\mathbb{E}[(-Z)^+] < \sigma_Z \phi(u)$ when $u > 0$. As $u \to \infty$, the optimal cost decays to $0$.

---

## 5. Counterexample 5: Falsification of "Almost Surely" Window Stall at Critical Rate $\lambda^*$

### Scenario
- Consider a Block Ack window of size $W = 16$.
- Link 1 has service duration $\delta = 8.0$ ms.
- Link 2 receives Poisson arrivals at rate $\lambda_2 = \lambda^* = W / \delta = 16 / 8.0\text{ ms} = 2.0\text{ pkts/ms}$.
- Mean arrivals during $\delta$: $\mathbb{E}[N] = \lambda_2 \delta = 16.0$.
- The historical claim asserted that for $\lambda_2 \ge \lambda^*$, the receiver buffer stalls **almost surely** ($\Pr(\text{stall}) = 1.0$).

### Stochastic Reality
- Because arrivals are Poisson, the probability that fewer than $W$ packets arrive is strictly positive:
  $$\Pr(N < W) = \sum_{k=0}^{W-1} \frac{(\lambda_2 \delta)^k e^{-\lambda_2 \delta}}{k!} = \sum_{k=0}^{15} \frac{16^k e^{-16}}{k!} \approx 0.4667$$
- Therefore, at the critical rate $\lambda_2 = \lambda^*$:
  $$\Pr(\text{stall}) = \Pr(N \ge W) = 1 - 0.4667 = 0.5333$$
  The probability of stalling is only $\approx 53.3\%$, while the probability of NOT stalling is $\approx 46.7\%$.
- Even at $20\%$ overload ($\lambda_2 = 1.2 \lambda^*$, mean arrivals $= 19.2$):
  $$\Pr(N < 16) \approx 0.2021$$
  The buffer does NOT stall in more than $20\%$ of instances!

### Implication
$\lambda^*$ is a **mean-drift / load crossover condition**, not an almost-sure guarantee. For finite traffic, stall probability is governed by the Poisson tail distribution:
$$P_{\text{stall}} = 1 - \sum_{k=0}^{W-1} \frac{(\lambda \delta)^k e^{-\lambda \delta}}{k!} = \frac{\gamma(W, \lambda \delta)}{(W-1)!}$$

---

*End of Counterexamples.*
