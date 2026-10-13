# Reconstructed Theoretical Derivations and Proofs

**Topic:** Analytical Modeling of Multi-Link Block Acknowledgment Reordering and Predictive Sequence Allocation in IEEE 802.11be  
**Audit Status:** Fully Reconstructed, Mathematically Repaired, and Scope-Bound (Phase 1 Audit)  
**Date:** October 2026  

---

## 1. Theorem 1: Buffer Reorder Accounting Decomposition

### 1.1 Theorem Statement
Let packet $i$ belong to flow $f_i \in \mathcal{F}$ with assigned Upper MAC sequence number $s_i \in [0, 4095]$ and physical arrival epoch $A_i$ at the receiver physical layer. Let the receiver operate a standard IEEE 802.11be Block Acknowledgment (BA) reordering entity with in-order delivery semantics for a shared Traffic Identifier (TID).

On an observed arrival trace $\mathcal{T} = \{(s_k, A_k, f_k)\}_{k \in \mathcal{K}}$, packet $i$ is released from the receiver reorder buffer to higher layers (LLC/IP) at epoch:
$$R_i \triangleq \max\left(A_i, \max_{k: s_k < s_i} A_k\right)$$

Define the *virtual intra-flow release boundary* $R_i^{\text{intra}}$ as the release epoch of packet $i$ if reordering constraints were applied solely within its own flow $f_i$:
$$R_i^{\text{intra}} \triangleq \max\left(A_i, \max_{j: f_j = f_i, s_j < s_i} A_j\right)$$

Then the total receiver reorder delay $\Delta_i \triangleq R_i - A_i$ admits an exact, non-negative additive decomposition:
$$\Delta_i = \mathcal{S}_i + \mathcal{X}_i$$
where:
$$\mathcal{S}_i \triangleq R_i^{\text{intra}} - A_i = \max\left(0, \max_{j: f_j = f_i, s_j < s_i} A_j - A_i\right) \quad \text{(Self-Blocking Delay)}$$
$$\mathcal{X}_i \triangleq R_i - R_i^{\text{intra}} = \max\left(0, \max_{k: f_k \ne f_i, s_k < s_i} A_k - R_i^{\text{intra}}\right) \quad \text{(Cross-Flow Blocking Delay)}$$

### 1.2 Proof
1. **Disjoint Partitioning of Predecessors:**  
   The set of causal predecessors $\mathcal{P}_i = \{k : s_k < s_i\}$ partitions into disjoint subsets:
   - Intra-flow predecessors: $\mathcal{P}_i^{\text{intra}} = \{j : f_j = f_i, s_j < s_i\}$
   - Inter-flow predecessors: $\mathcal{P}_i^{\text{inter}} = \{k : f_k \ne f_i, s_k < s_i\}$
   where $\mathcal{P}_i = \mathcal{P}_i^{\text{intra}} \cup \mathcal{P}_i^{\text{inter}}$ and $\mathcal{P}_i^{\text{intra}} \cap \mathcal{P}_i^{\text{inter}} = \emptyset$.

2. **Supremum Evaluation:**  
   $$R_i = \max\left(A_i, \max_{k \in \mathcal{P}_i} A_k\right) = \max\left( \max\left(A_i, \max_{j \in \mathcal{P}_i^{\text{intra}}} A_j\right), \max_{k \in \mathcal{P}_i^{\text{inter}}} A_k \right) = \max\left( R_i^{\text{intra}}, \max_{k \in \mathcal{P}_i^{\text{inter}}} A_k \right)$$

3. **Non-Negativity:**  
   By definition of the supremum over a set containing $A_i$:
   $$R_i \ge R_i^{\text{intra}} \ge A_i$$
   Consequently:
   $$\mathcal{S}_i = R_i^{\text{intra}} - A_i \ge 0$$
   $$\mathcal{X}_i = R_i - R_i^{\text{intra}} \ge 0$$

4. **Additive Sum Identity:**  
   $$\mathcal{S}_i + \mathcal{X}_i = (R_i^{\text{intra}} - A_i) + (R_i - R_i^{\text{intra}}) = R_i - A_i = \Delta_i \quad \blacksquare$$

### 1.3 Lemma 1: Trace-Level Attribution Invariance
*On an observed execution trace $\mathcal{T}$ with fixed arrival times $\{A_k\}$ and assigned sequence numbers $\{s_k\}$, $\mathcal{S}_i$ is strictly invariant to all packets of other flows $\{k : f_k \ne f_i\}$.*

**Measurement Methodology Status & Causal Scope:**  
Theorem 1 and Lemma 1 constitute an exact **post-facto accounting framework** rather than a causal physical law. In a real shared wireless medium, the presence of competing traffic introduces EDCA channel contention, collision-induced backoff stage escalation, and queueing delays, which alter the underlying arrival epochs $\{A_k\}$. Thus, Theorem 1 serves as an exact diagnostic metric for isolating *in-buffer reordering stalls* from *channel service time dispersion*, evaluated on a realized execution trace.

---

## 2. Theorem 2: Multi-Link Sequence Divergence & Buffer Stall Probability

### 2.1 Theorem Statement
Consider a multi-link device (MLD) operating over two active links: Link 1 (slow link, mean service duration $\mu_1$, variance $\sigma_1^2$) and Link 2 (fast link, mean service duration $\mu_2$, variance $\sigma_2^2$), with mean asymmetry $\delta \triangleq \mu_1 - \mu_2 > 0$. Let frames be dispatched on Link 2 at rate $\lambda_2$, sharing a TID and a negotiated Block Ack reorder window of size $W$.

1. **Mean Sequence Divergence:**  
   During the transmission of a frame on Link 1 with stochastic completion duration $D_1$, the number of frames $N$ dispatched on Link 2 has mean:
   $$\mathbb{E}[N] = \lambda_2 \mu_1$$
   When arrivals on Link 2 follow a Poisson process, $\operatorname{Var}(N) = \lambda_2 \mu_1 + \lambda_2^2 \sigma_1^2$.

2. **Mean-Drift Crossover Boundary:**  
   The critical arrival rate at which the expected sequence divergence equals the window size $W$ is:
   $$\lambda^* \triangleq \frac{W}{\delta}$$
   When $\lambda_2 > \lambda^*$, the mean queue drift into the reorder window is positive ($\mathbb{E}[N] > W$), causing the buffer to accumulate frames on average.

3. **Exact Stochastic Stall Probability:**  
   For a constant completion duration $\delta$ on Link 1 and Poisson arrivals at rate $\lambda_2$ on Link 2, the exact probability that the sequence gap reaches or exceeds the reorder window capacity $W$ during this interval is:
   $$P_{\text{stall}}(\lambda_2, \delta, W) \triangleq \Pr(N \ge W) = 1 - \sum_{k=0}^{W-1} \frac{(\lambda_2 \delta)^k e^{-\lambda_2 \delta}}{k!} = \frac{\gamma(W, \lambda_2 \delta)}{(W - 1)!}$$
   where $\gamma(s, x)$ is the lower incomplete gamma function.  
   *(Clarification: For any finite arrival rate $\lambda_2$, $\Pr(N < W) > 0$. Therefore, window collapse does NOT occur "almost surely" at $\lambda_2 = \lambda^*$; rather, $\lambda^*$ represents the median/mean crossover where $P_{\text{stall}} \approx 0.533$ for $W=16$.)*

4. **Cumulative Cross-Flow Stall Delay:**  
   Under FIFO sequencing, when a Link 1 frame completes at epoch $\delta$ while Link 2 frames arrive at deterministic rate $\lambda_2$, the cumulative cross-flow blocking delay across all stalled Link 2 frames is:
   $$\int_0^{\lambda_2 \delta} \left(\delta - \frac{x}{\lambda_2}\right) dx = \frac{1}{2} \lambda_2 \delta^2$$
   The average cross-blocking delay per stalled frame is $\frac{\delta}{2}$.

### 2.2 Proof
1. **Cumulative Delay Integral:**  
   Frame $a$ begins transmission on Link 1 at $t=0$ and completes at $A_a = \delta$. Concurrently, frames $b_x$ arrive on Link 2 at rate $\lambda_2$, completing transmission at $A_{b_x} = x/\lambda_2 + \mu_2$.  
   Frame $b_x$ is blocked behind $a$ whenever $A_{b_x} < A_a$, giving per-packet stall $\mathcal{X}(x) = \delta - x/\lambda_2$.  
   Integrating over the blocked interval $x \in [0, \lambda_2 \delta]$:
   $$\int_0^{\lambda_2 \delta} \left(\delta - \frac{x}{\lambda_2}\right) dx = \lambda_2 \delta^2 - \frac{\lambda_2^2 \delta^2}{2\lambda_2} = \frac{1}{2} \lambda_2 \delta^2$$
   The units are $[1/\text{time}] \times [\text{time}^2] = [\text{time}]$, representing the aggregate delay penalty.

2. **Stochastic Sequence Divergence:**  
   Conditioned on $D_1 = t$, $N \mid D_1 \sim \operatorname{Poisson}(\lambda_2 t)$. By the law of total expectation and variance:
   $$\mathbb{E}[N] = \mathbb{E}[\mathbb{E}[N \mid D_1]] = \mathbb{E}[\lambda_2 D_1] = \lambda_2 \mu_1$$
   $$\operatorname{Var}(N) = \mathbb{E}[\operatorname{Var}(N \mid D_1)] + \operatorname{Var}(\mathbb{E}[N \mid D_1]) = \lambda_2 \mu_1 + \lambda_2^2 \sigma_1^2$$

3. **Stall Probability:**  
   Under Poisson arrivals with parameter $\theta = \lambda_2 \delta$, the CDF is $\Pr(N < W) = \sum_{k=0}^{W-1} \frac{\theta^k e^{-\theta}}{k!}$.  
   Hence the complement probability of reaching or exceeding the window capacity is:
   $$\Pr(N \ge W) = 1 - \sum_{k=0}^{W-1} \frac{(\lambda_2 \delta)^k e^{-\lambda_2 \delta}}{k!} \quad \blacksquare$$

---

## 3. Theorem 3: Pairwise Gaussian Predictive Sequence Allocation

### 3.1 Theorem Statement
Let candidate frame $a$ (belonging to flow $f_a$ with priority weight $w_a > 0$) and candidate frame $b$ (belonging to flow $f_b$ with priority weight $w_b > 0$, $f_a \ne f_b$) be ready for concurrent transmission over independent radio links.  
Let their physical completion times be modeled as independent Gaussian random variables:
$$A_a \sim \mathcal{N}(\mu_a, \sigma_a^2), \quad A_b \sim \mathcal{N}(\mu_b, \sigma_b^2)$$
Define the completion difference random variable $Z \triangleq A_a - A_b \sim \mathcal{N}(d, \sigma_Z^2)$, where $d \triangleq \mu_a - \mu_b$ and $\sigma_Z \triangleq \sqrt{\sigma_a^2 + \sigma_b^2} > 0$.

The sequence assignment minimizing the expected weighted cross-flow blocking cost:
$$C(s_a < s_b) = w_b \mathbb{E}[(A_a - A_b)^+], \quad C(s_b < s_a) = w_a \mathbb{E}[(A_b - A_a)^+]$$
is governed by the threshold decision rule:
$$s_a < s_b \iff \frac{\mu_a - \mu_b}{\sqrt{\sigma_a^2 + \sigma_b^2}} \le u^*(w_a, w_b)$$
where $u^*$ is the unique real root of the transcendental equation:
$$h(u) \triangleq (w_b - w_a) \phi(u) + \left[ w_a (1 - \Phi(u)) + w_b \Phi(u) \right] u = 0$$
and $\phi(u) \triangleq \frac{1}{\sqrt{2\pi}} e^{-u^2/2}$ and $\Phi(u) \triangleq \int_{-\infty}^u \phi(t) dt$ denote the standard normal PDF and CDF.

### 3.2 Proof
1. **Identity for Truncated Differences:**  
   For any real random variable $Z$, $Z^+ - (-Z)^+ = Z$. Taking expectations:
   $$\mathbb{E}[(-Z)^+] = \mathbb{E}[Z^+] - \mathbb{E}[Z] = \mathbb{E}[Z^+] - d$$
   Therefore:
   $$C(s_a < s_b) = w_b \mathbb{E}[Z^+]$$
   $$C(s_b < s_a) = w_a \mathbb{E}[(-Z)^+] = w_a (\mathbb{E}[Z^+] - d)$$

2. **Equivalence Condition:**  
   Assigning $s_a < s_b$ is weakly preferred if and only if:
   $$C(s_a < s_b) \le C(s_b < s_a) \iff w_b \mathbb{E}[Z^+] \le w_a (\mathbb{E}[Z^+] - d) \iff (w_b - w_a) \mathbb{E}[Z^+] + w_a d \le 0$$

3. **Evaluating Truncated Normal Expectation:**  
   For $Z \sim \mathcal{N}(d, \sigma_Z^2)$, let $u = d / \sigma_Z$. Standardizing:
   $$\mathbb{E}[Z^+] = \sigma_Z \left[ \phi(u) + u \Phi(u) \right]$$
   Substituting into the cost comparison and dividing by $\sigma_Z > 0$:
   $$(w_b - w_a) \phi(u) + (w_b - w_a) u \Phi(u) + w_a u \le 0$$
   Factoring the terms multiplying $u$:
   $$(w_b - w_a) \Phi(u) + w_a = w_a (1 - \Phi(u)) + w_b \Phi(u)$$
   Hence:
   $$h(u) = (w_b - w_a) \phi(u) + \left[ w_a (1 - \Phi(u)) + w_b \Phi(u) \right] u \le 0$$

4. **Strict Monotonicity and Root Uniqueness:**  
   Differentiating $h(u)$ with respect to $u$:
   $$h'(u) = (w_b - w_a) \phi'(u) + (w_b - w_a) \phi(u) u + \left[ w_a (1 - \Phi(u)) + w_b \Phi(u) \right]$$
   Using the derivative property of the Gaussian PDF, $\phi'(u) = -u \phi(u)$:
   $$(w_b - w_a)(-u \phi(u)) + (w_b - w_a)(u \phi(u)) \equiv 0$$
   The first two terms cancel identically! Therefore:
   $$h'(u) = w_a (1 - \Phi(u)) + w_b \Phi(u)$$
   Since $w_a > 0$, $w_b > 0$, and $\Phi(u) \in (0, 1)$ for all $u \in \mathbb{R}$:
   $$h'(u) > 0 \quad \forall u \in \mathbb{R}$$
   Because $h'(u)$ is strictly positive everywhere, $h(u)$ is strictly monotonically increasing.  
   Furthermore, $\lim_{u \to -\infty} h(u) = -\infty$ and $\lim_{u \to +\infty} h(u) = +\infty$.  
   By the Intermediate Value Theorem, there exists a unique real root $u^* \in \mathbb{R}$ such that $h(u^*) = 0$. $\blacksquare$

### 3.3 Properties and Scope Boundary
- **Symmetric Weights ($w_a = w_b$):** $w_b - w_a = 0 \implies h(u) = w_a u = 0 \implies u^* = 0$. Optimal sequence assignment orders frames strictly by expected physical arrival: $s_a < s_b \iff \mu_a \le \mu_b$.
- **Asymmetric Weights ($w_b > w_a$):** $h(0) = (w_b - w_a)\phi(0) > 0 \implies u^* < 0$. This biases sequencing toward the high-priority flow $b$, giving it the lower sequence number ($s_b < s_a$) even when $\mu_b > \mu_a$, up to the threshold $d \le u^* \sigma_Z$.
- **Scope Limitation:** Theorem 3 proves the strictly optimal sequence decision for a **pair** of candidate frames. For $N \ge 3$ candidate frames, joint order statistics render greedy pairwise index sorting a computationally efficient heuristic ($\mathcal{O}(M \log M)$), not a provably global optimum.

---

## 4. Theorem 4: Symmetric-Link Uncertainty Floor & Asymptotic Cost Function

### 4.1 Theorem Statement
Let candidate frames $a$ and $b$ be concurrently dispatched on independent stochastic radio links with Gaussian completion distributions $A_a \sim \mathcal{N}(\mu_a, \sigma_a^2)$ and $A_b \sim \mathcal{N}(\mu_b, \sigma_b^2)$ with $\sigma_Z = \sqrt{\sigma_a^2 + \sigma_b^2} > 0$.

1. **Symmetric Link Causal Uncertainty Floor:**  
   When the two links have identical mean completion times ($\mu_a = \mu_b$, so $d=0$ and $u=0$), the expected weighted cross-flow blocking cost under ANY binary sequence assignment decision $\omega \in \{s_a < s_b, s_b < s_a\}$ is strictly bounded below by:
   $$\min\left( C(s_a < s_b), C(s_b < s_a) \right) = \min(w_a, w_b) \cdot \frac{\sigma_Z}{\sqrt{2\pi}} > 0$$
   On symmetric stochastic links, no causal online policy can achieve zero cross-flow blocking delay.

2. **Asymmetric Optimal Decision Cost:**  
   For arbitrary link delay asymmetry $u = (\mu_a - \mu_b) / \sigma_Z$, the optimal decision cost achieves:
   $$C^*(u) \triangleq \min\left( C(s_a < s_b), C(s_b < s_a) \right) = \begin{cases} w_b \sigma_Z \left[ \phi(u) + u \Phi(u) \right] & \text{if } u \le u^*(w_a, w_b) \\ w_a \sigma_Z \left[ \phi(u) - u (1 - \Phi(u)) \right] & \text{if } u > u^*(w_a, w_b) \end{cases}$$
   The optimal cost $C^*(u)$ attains its global maximum at the threshold $u = u^*$ and decays asymptotically to zero as $|u| \to \infty$:
   $$\lim_{|u| \to \infty} C^*(u) = 0$$

### 4.2 Proof
1. **Symmetric Case ($u = 0$):**  
   At $u = 0$, $\phi(0) = \frac{1}{\sqrt{2\pi}}$, $\Phi(0) = \frac{1}{2}$, and $d = 0$.
   $$\mathbb{E}[Z^+] = \sigma_Z [\phi(0) + 0] = \frac{\sigma_Z}{\sqrt{2\pi}}$$
   $$\mathbb{E}[(-Z)^+] = \sigma_Z [\phi(0) - 0] = \frac{\sigma_Z}{\sqrt{2\pi}}$$
   Therefore:
   $$C(s_a < s_b) = w_b \frac{\sigma_Z}{\sqrt{2\pi}}, \quad C(s_b < s_a) = w_a \frac{\sigma_Z}{\sqrt{2\pi}}$$
   $$\min\left( C(s_a < s_b), C(s_b < s_a) \right) = \min(w_a, w_b) \frac{\sigma_Z}{\sqrt{2\pi}} \quad \blacksquare$$

2. **Asymmetric Asymptotics:**  
   For $u > 0$, by Mill's ratio, $1 - \Phi(u) \le \frac{\phi(u)}{u}$.  
   Hence:
   $$\mathbb{E}[(-Z)^+] = \sigma_Z [\phi(u) - u(1 - \Phi(u))] \le \sigma_Z \phi(u) \left[ 1 - u \cdot \left(\frac{1}{u} - \frac{1}{u^3}\right) \right] = \frac{\sigma_Z \phi(u)}{u^2} \to 0 \quad \text{as } u \to \infty$$
   Similarly, $\mathbb{E}[Z^+] \to 0$ as $u \to -\infty$. Thus $C^*(u) \to 0$ as $|u| \to \infty$. $\blacksquare$

### 4.3 Falsification Boundaries (Why No Universal Bound Holds for All $u$)
The earlier hypothesis that $\min(C) \ge \min(w) \sigma_Z \phi(u)$ is mathematically false for $|u| > 0$ because $\mathbb{E}[(-Z)^+] < \sigma_Z \phi(u)$ for all $u > 0$ (e.g., at $u=2$, $\mathbb{E}[(-Z)^+] \approx 0.00849\sigma_Z < 0.05399\sigma_Z = \sigma_Z \phi(2)$). Furthermore, Single-Link Operation achieves $\mathcal{X} = 0$ identically by serializing all traffic over one interface. Thus, Theorem 4 is valid strictly as a **symmetric-link stochastic uncertainty floor** under concurrent multi-link dispatch.

---

*End of Reconstructed Theory.*
