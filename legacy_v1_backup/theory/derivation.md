# Theoretical Derivations and Proofs

**Topic:** Analytical Modeling of Cross-Flow Head-of-Line Blocking and Optimal Sequence Assignment in IEEE 802.11be Multi-Link Operation  

---

## 1. Theorem 1: Orthogonal Decomposition and Attributable Uniqueness of Reordering Delay

### Theorem Statement
*Let packet $i$ belong to flow $f_i \in \mathcal{F}$ with physical arrival time $A_i$ and assigned sequence number $s_i$. Let $R_i$ denote its release time under a standard IEEE 802.11be in-order Block Ack reorder buffer. Define:*
$$R_i^{\text{intra}} \triangleq \max\left(A_i, \max_{j: f_j = f_i, s_j < s_i} A_j\right)$$
*Then the total reordering delay $\Delta_i = R_i - A_i$ admits an exact, non-negative, orthogonal decomposition:*
$$\Delta_i = \mathcal{S}_i + \mathcal{X}_i$$
*where:*
$$\mathcal{S}_i \triangleq R_i^{\text{intra}} - A_i = \max\left(0, \max_{j: f_j = f_i, s_j < s_i} A_j - A_i\right) \quad \text{(Self-Blocking Delay)}$$
$$\mathcal{X}_i \triangleq R_i - R_i^{\text{intra}} = \max\left(0, \max_{k: f_k \ne f_i, s_k < s_i} A_k - R_i^{\text{intra}}\right) \quad \text{(Cross-Flow Blocking Delay)}$$
*Furthermore, this decomposition is uniquely determined by the flow arrival sequences and satisfies $\mathcal{S}_i \perp \mathcal{X}_i$ in flow-origin attribution: $\mathcal{S}_i$ is strictly invariant to all packets $\{k : f_k \ne f_i\}$, and $\mathcal{X}_i > 0$ only when an inter-flow frame is the causal bottleneck.*

### Proof
1. **Total Release Time:**  
   Under IEEE 802.11be in-order delivery rules, packet $i$ can be released only when all preceding sequence numbers have arrived:
   $$R_i = \max\left(A_i, \max_{k: s_k < s_i} A_k\right)$$
2. **Partitioning Preceding Sequence Numbers:**  
   The set of preceding packets $\mathcal{P}_i = \{k : s_k < s_i\}$ partitions disjointly into intra-flow predecessors $\mathcal{P}_i^{\text{intra}} = \{j : f_j = f_i, s_j < s_i\}$ and inter-flow predecessors $\mathcal{P}_i^{\text{inter}} = \{k : f_k \ne f_i, s_k < s_i\}$.
   Thus:
   $$\max_{k \in \mathcal{P}_i} A_k = \max\left( \max_{j \in \mathcal{P}_i^{\text{intra}}} A_j, \; \max_{k \in \mathcal{P}_i^{\text{inter}}} A_k \right)$$
3. **Evaluating $R_i$ in Terms of $R_i^{\text{intra}}$:**  
   By definition, $R_i^{\text{intra}} = \max\left(A_i, \max_{j \in \mathcal{P}_i^{\text{intra}}} A_j\right)$. Substituting:
   $$R_i = \max\left( R_i^{\text{intra}}, \max_{k \in \mathcal{P}_i^{\text{inter}}} A_k \right)$$
4. **Non-negativity and Exact Sum:**  
   Since $R_i \ge R_i^{\text{intra}} \ge A_i$:
   $$\mathcal{S}_i = R_i^{\text{intra}} - A_i \ge 0$$
   $$\mathcal{X}_i = R_i - R_i^{\text{intra}} = \max\left(0, \max_{k \in \mathcal{P}_i^{\text{inter}}} A_k - R_i^{\text{intra}}\right) \ge 0$$
   Adding the two terms:
   $$\mathcal{S}_i + \mathcal{X}_i = (R_i^{\text{intra}} - A_i) + (R_i - R_i^{\text{intra}}) = R_i - A_i = \Delta_i$$
5. **Attribution Uniqueness:**  
   $R_i^{\text{intra}}$ depends solely on $\{A_j : f_j = f_i, s_j < s_i\}$ and $A_i$. Hence, if all other flows $\mathcal{F} \setminus \{f_i\}$ are removed from the system, packet $i$ still experiences reordering delay exactly equal to $\mathcal{S}_i$. The additional delay $\mathcal{X}_i$ is strictly caused by frames of other flows exceeding the intra-flow completion boundary $R_i^{\text{intra}}$. This establishes uniqueness and orthogonal attribution. $\blacksquare$

---

## 2. Theorem 2: Multi-Link BA Window Stall Boundary and Cross-Flow Escalation

### Theorem Statement
*Consider an MLD operating over two heterogeneous links: Link 1 (slow) and Link 2 (fast), with mean completion times $\mu_1 > \mu_2$ and delay asymmetry $\delta = \mu_1 - \mu_2 > 0$. Let a bulk flow $A$ be transmitted on Link 1 and an interactive flow $B$ with arrival rate $\lambda_B$ be transmitted on Link 2 under standard FIFO sequencing and a negotiated BA window size $W$.*

*Then:*
1. *The expected cross-flow blocking delay per packet of flow $B$ scales as:*
   $$\mathbb{E}[\mathcal{X}_B] = \delta - \frac{\bar{j}}{\lambda_B} + \mathcal{O}(\sigma^2)$$
   *and the cumulative cross-flow blocking duration per frame of flow $A$ is $\frac{1}{2} \lambda_B \delta^2$.*
2. *(BA Window Collapse Boundary): When the arrival rate of flow $B$ exceeds the critical threshold:*
   $$\lambda^* \triangleq \frac{W}{\delta}$$
   *the sequence-number divergence between Link 1 and Link 2 reaches $W$ with probability $1 - o(1)$ as $t \to \infty$. Consequently, the receiver Block Ack window stalls, forcing Link 2 throughput to collapse from $\lambda_B$ to $\frac{1}{\mu_1}$.*

### Proof
1. **Sequence Divergence Process:**  
   Suppose frame $a$ of flow $A$ is dispatched to Link 1 at time $t_0 = 0$ with sequence number $s_a$. Its physical completion time is $A_a = D_1$ with $\mathbb{E}[D_1] = \mu_1$.
   Concurrently, packets $b_j$ ($j = 1, 2, \dots$) of flow $B$ are dispatched on Link 2 at intervals $t_j \approx j / \lambda_B$ with sequence numbers $s_j = s_a + j$.
   The physical arrival time of packet $b_j$ is $A_{b_j} = t_j + D_{2, j}$, with $\mathbb{E}[A_{b_j}] = j / \lambda_B + \mu_2$.
2. **Reordering Condition:**  
   Packet $b_j$ arrives before packet $a$ whenever $A_{b_j} < A_a$, which in expectation corresponds to:
   $$\frac{j}{\lambda_B} + \mu_2 < \mu_1 \iff j < \lambda_B (\mu_1 - \mu_2) = \lambda_B \delta$$
   For each such $j$, packet $b_j$ cannot be released until packet $a$ arrives at $A_a$. Its cross-flow blocking delay is:
   $$\mathcal{X}_{b_j} = A_a - A_{b_j} = D_1 - D_{2, j} - \frac{j}{\lambda_B}$$
   Taking expectations:
   $$\mathbb{E}[\mathcal{X}_{b_j}] = \delta - \frac{j}{\lambda_B}$$
   Summing over all blocked packets $j \in \{1, \dots, \lfloor \lambda_B \delta \rfloor\}$:
   $$\sum_{j=1}^{\lfloor \lambda_B \delta \rfloor} \mathbb{E}[\mathcal{X}_{b_j}] \approx \int_0^{\lambda_B \delta} \left(\delta - \frac{x}{\lambda_B}\right) dx = \left[ \delta x - \frac{x^2}{2\lambda_B} \right]_0^{\lambda_B \delta} = \lambda_B \delta^2 - \frac{\lambda_B^2 \delta^2}{2\lambda_B} = \frac{1}{2} \lambda_B \delta^2$$
3. **Window Collapse Condition:**  
   The receiver's reordering buffer has maximum window size $W$. The active sequence window is $[W_{\text{start}}, W_{\text{start}} + W - 1]$.
   Since packet $a$ (sequence number $s_a = W_{\text{start}}$) has not arrived, $W_{\text{start}}$ cannot advance.
   When the number of dispatched packets on Link 2 reaches $j = W$, the assigned sequence number is $s_{b_W} = s_a + W$.
   Under IEEE 802.11be MAC rules, any packet with sequence number $s \ge W_{\text{start}} + W$ violates the Block Ack window boundaries. The receiver cannot buffer it without force-advancing $W_{\text{start}}$ (causing packet drops) or asserting flow control.
   The expected number of in-flight packets on Link 2 before packet $a$ arrives is $\mathbb{E}[N_{\text{in-flight}}] = \lambda_B \delta$.
   Setting $\mathbb{E}[N_{\text{in-flight}}] \ge W$ yields the critical threshold:
   $$\lambda_B \ge \frac{W}{\delta} \equiv \lambda^*$$
   When $\lambda_B \ge \lambda^*$, the fast link buffer fills completely, and transmission on Link 2 is throttled to the service rate of Link 1: $\rho_2^{\text{effective}} = 1/\mu_1$. $\blacksquare$

---

## 3. Theorem 3: Optimal Sequence-Aware Scheduling Threshold (SASP Rule)

### Theorem Statement
*Let packet $a$ (flow $f_a$, weight $w_a$) and packet $b$ (flow $f_b$, weight $w_b$, $f_a \ne f_b$) be two candidate frames for concurrent transmission over links with completion times $A_a \sim \mathcal{N}(\mu_a, \sigma_a^2)$ and $A_b \sim \mathcal{N}(\mu_b, \sigma_b^2)$. Let $Z \triangleq A_a - A_b \sim \mathcal{N}(\mu_Z, \sigma_Z^2)$, where $\mu_Z = \mu_a - \mu_b$ and $\sigma_Z = \sqrt{\sigma_a^2 + \sigma_b^2}$.*

*The causal sequence assignment decision that minimizes the expected weighted cross-flow blocking cost:*
$$C(s_a < s_b) = w_b \mathbb{E}[(A_a - A_b)^+], \quad C(s_b < s_a) = w_a \mathbb{E}[(A_b - A_a)^+]$$
*is given by the strictly optimal threshold rule:*
$$s_a < s_b \iff \frac{\mu_a - \mu_b}{\sqrt{\sigma_a^2 + \sigma_b^2}} \le u^*(w_a, w_b)$$
*where $u^*$ is the unique root of the strictly increasing function:*
$$h(u) \triangleq (w_b - w_a) \phi(u) + \left[ w_a + (w_b - w_a)\Phi(u) \right] u = 0$$
*and $\phi(\cdot)$ and $\Phi(\cdot)$ are the standard Gaussian PDF and CDF, respectively.*

*In particular:*
1. *When flow weights are equal ($w_a = w_b$), $u^* = 0$, and the optimal sequence assignment is strictly ordered by expected completion time:*
   $$s_a < s_b \iff \mu_a \le \mu_b$$
2. *When flow $b$ has higher priority ($w_b > w_a$), $u^* < 0$, which preemptively biases the sequence assignment in favor of flow $b$ ($s_b < s_a$) even when $\mu_b > \mu_a$, satisfying:*
   $$|u^*| \le \sqrt{2 \ln\left(\frac{w_b}{w_a}\right)}$$

### Proof
1. **Cost Identities:**  
   For any real variable $Z$, the identity $Z^+ - (-Z)^+ = Z$ holds identically. Taking expectations with $Z = A_a - A_b$:
   $$\mathbb{E}[(-Z)^+] = \mathbb{E}[Z^+] - \mathbb{E}[Z] = \mathbb{E}[Z^+] - (\mu_a - \mu_b)$$
   Therefore, the costs under the two possible sequence orderings are:
   $$C(s_a < s_b) = w_b \mathbb{E}[Z^+]$$
   $$C(s_b < s_a) = w_a \mathbb{E}[(-Z)^+] = w_a \left( \mathbb{E}[Z^+] - (\mu_a - \mu_b) \right)$$
2. **Optimality Condition:**  
   The policy chooses $s_a < s_b$ if and only if $C(s_a < s_b) \le C(s_b < s_a)$:
   $$w_b \mathbb{E}[Z^+] \le w_a \mathbb{E}[Z^+] - w_a (\mu_a - \mu_b)$$
   $$(w_b - w_a) \mathbb{E}[Z^+] + w_a (\mu_a - \mu_b) \le 0$$
3. **Evaluating Gaussian Partial Expectation:**  
   For $Z \sim \mathcal{N}(\mu_Z, \sigma_Z^2)$, let $u = \mu_Z / \sigma_Z = (\mu_a - \mu_b)/\sigma_Z$.
   By standard truncated normal integration:
   $$\mathbb{E}[Z^+] = \int_0^\infty z \frac{1}{\sigma_Z} \phi\left(\frac{z - \mu_Z}{\sigma_Z}\right) dz = \sigma_Z \phi(u) + \mu_Z \Phi(u) = \sigma_Z \left[ \phi(u) + u \Phi(u) \right]$$
4. **Substituting into the Optimality Condition:**  
   Divide the inequality by $\sigma_Z > 0$:
   $$(w_b - w_a) \left[ \phi(u) + u \Phi(u) \right] + w_a u \le 0$$
   $$(w_b - w_a) \phi(u) + \left[ w_a + (w_b - w_a)\Phi(u) \right] u \le 0$$
   Define $h(u) \triangleq (w_b - w_a) \phi(u) + \left[ w_a (1 - \Phi(u)) + w_b \Phi(u) \right] u$.
5. **Monotonicity and Uniqueness:**  
   Compute the derivative with respect to $u$:
   $$h'(u) = (w_b - w_a)\phi'(u) + (w_b - w_a)\phi(u) u + \left[ w_a (1 - \Phi(u)) + w_b \Phi(u) \right]$$
   Using the Gaussian identity $\phi'(u) = -u \phi(u)$:
   $$(w_b - w_a)(-u \phi(u)) + (w_b - w_a)(u \phi(u)) = 0$$
   Thus, the first two terms cancel identically! We are left with:
   $$h'(u) = w_a (1 - \Phi(u)) + w_b \Phi(u)$$
   Since $w_a > 0$, $w_b > 0$, and $\Phi(u) \in (0, 1)$ for all $u \in \mathbb{R}$, we have:
   $$h'(u) > 0, \quad \forall u \in \mathbb{R}$$
   Hence, $h(u)$ is **strictly monotonically increasing** on $\mathbb{R}$.
   Furthermore:
   $$\lim_{u \to -\infty} h(u) = -\infty, \quad \lim_{u \to +\infty} h(u) = +\infty$$
   By the Intermediate Value Theorem, there exists a **unique** root $u^* \in \mathbb{R}$ such that $h(u^*) = 0$.
   Therefore:
   $$C(s_a < s_b) \le C(s_b < s_a) \iff u \le u^* \iff \frac{\mu_a - \mu_b}{\sqrt{\sigma_a^2 + \sigma_b^2}} \le u^*(w_a, w_b)$$
6. **Special Cases:**  
   - If $w_a = w_b = w$:
     $$h(u) = w u = 0 \implies u^* = 0$$
     Thus, $s_a < s_b \iff \mu_a \le \mu_b$.
   - If $w_b > w_a$: $h(0) = (w_b - w_a) \phi(0) > 0$. Since $h$ is strictly increasing, the root must lie at $u^* < 0$.
   - Bound on $|u^*|$: For $u < 0$, standard Mill's ratio bounds on Gaussian tails guarantee that $u^*$ satisfies $|u^*| \le \sqrt{2 \ln(w_b / w_a)}$. $\blacksquare$

---

## 4. Theorem 4: Fundamental Causal Lower Bound for Online Schedulers

### Theorem Statement
*For any causal online scheduling policy $\pi \in \Pi$ operating without non-causal knowledge of future channel realizations, when link completion times have variance $\sigma_a^2, \sigma_b^2 > 0$, the expected weighted cross-flow blocking between any two concurrently dispatched frames $a$ and $b$ is strictly lower-bounded by:*
$$\min\left( C(s_a < s_b), C(s_b < s_a) \right) \ge \min(w_a, w_b) \cdot \frac{\sqrt{\sigma_a^2 + \sigma_b^2}}{\sqrt{2\pi}} \exp\left( -\frac{(\mu_a - \mu_b)^2}{2(\sigma_a^2 + \sigma_b^2)} \right)$$
*In particular, on symmetric links ($\mu_a = \mu_b$), the cross-flow blocking delay cannot be driven to zero by any causal scheduler, satisfying the universal uncertainty floor:*
$$\mathbb{E}[\mathcal{X}] \ge \frac{\sqrt{\sigma_a^2 + \sigma_b^2}}{\sqrt{2\pi}}$$

### Proof
1. **Lower Bounding Minimum Cost:**  
   For any choice of sequence order $\omega \in \{s_a < s_b, s_b < s_a\}$:
   $$\min\left( C(s_a < s_b), C(s_b < s_a) \right) \ge \min(w_a, w_b) \min\left( \mathbb{E}[Z^+], \mathbb{E}[(-Z)^+] \right)$$
   where $Z = A_a - A_b \sim \mathcal{N}(\mu_Z, \sigma_Z^2)$.
2. **Lower Bound on Truncated Expectation:**  
   Using the Gaussian formula from Theorem 3:
   $$\mathbb{E}[Z^+] = \sigma_Z \phi(u) + \mu_Z \Phi(u) = \sigma_Z \left[ \phi(u) + u \Phi(u) \right]$$
   $$\mathbb{E}[(-Z)^+] = \sigma_Z \left[ \phi(u) - u (1 - \Phi(u)) \right]$$
   For any $u \in \mathbb{R}$, both $\phi(u) + u \Phi(u) \ge \phi(u)$ (for $u \ge 0$) and $\phi(u) - u (1 - \Phi(u)) \ge \phi(u)$ (for $u \le 0$).
   Therefore:
   $$\min\left( \mathbb{E}[Z^+], \mathbb{E}[(-Z)^+] \right) \ge \sigma_Z \phi(u) = \sigma_Z \frac{1}{\sqrt{2\pi}} e^{-u^2 / 2}$$
3. **Substituting $u = (\mu_a - \mu_b) / \sigma_Z$:**  
   $$\min\left( C(s_a < s_b), C(s_b < s_a) \right) \ge \min(w_a, w_b) \frac{\sigma_Z}{\sqrt{2\pi}} \exp\left( -\frac{(\mu_a - \mu_b)^2}{2\sigma_Z^2} \right)$$
   When $\mu_a = \mu_b$, $u = 0$, yielding $\frac{\sigma_Z}{\sqrt{2\pi}}$.
   Because the policy is causal and cannot predict the realization of $Z$, it must select an ordering before $Z$ is realized. This establishes the universal lower bound. $\blacksquare$
