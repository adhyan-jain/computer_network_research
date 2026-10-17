# Multi-Frame Ordering, Transitivity, and Cycle Resolution Audit

**Date:** October 13, 2026  
**Topic:** Wi-Fi 7 MLO Sequence-Aware Stochastic Partitioning (SASP)  
**Deliverable:** Independent Audit of Multi-Frame Transitivity and Cycle Resolution (Phase 2)  
**Auditor:** Independent Mathematical Reviewer & Networking Systems Specialist  

---

## 1. Executive Summary

This audit resolves the fundamental mathematical question governing Theorem 3:
> *Does the pairwise preference relation derived from Theorem 3 define a globally consistent (transitive) multi-frame ordering for $N \ge 3$ candidate packets, and how does the implementation handle multi-frame scheduling?*

### Key Findings
1. **Universal Transitivity Fails:** The pairwise preference relation $\prec$ derived from Theorem 3 is **strictly non-transitive**. A concrete, reproducible three-frame cycle (Condorcet tournament cycle) is confirmed:
   $$\text{Frame } A \prec B, \quad B \prec C, \quad C \prec A$$
   with substantial cost differences ($> 0.11$ in each direction).
2. **Implementation Ground Truth:** In `src/mlo_sim/schedulers.py:412-421`, `SASPScheduler` applies Theorem 3's variance-aware pairwise swap **strictly when $N = 2$**. When $N > 2$ candidates exist, it does **not** invoke a cyclic comparator; instead, it falls back to scalar arrival-mean sorting (`predictions.sort(key=lambda x: x[0])`), avoiding Python Timsort failure but operating as Mean-Only Sequencing for $N \ge 3$.
3. **Batch Global Optimality vs. Pairwise Heuristics:** Under the true aggregate receiver reordering cost $J(\pi) = \sum_{i=1}^N w_i \mathbb{E}[\max_{j: \pi(j) \le \pi(i)} A_j - A_i]$, pairwise costs cannot simply be summed. For the cyclic candidate triplet, exhaustive enumeration of all $3! = 6$ permutations identifies an unambiguous, unique global minimizer ($ABC$ with aggregate cost $1.1283$, whereas $ACB$ has cost $1.5257$).
4. **Preserved Mathematical Scope:** Theorem 3 is mathematically exact and strictly optimal for **pairs** of frames ($N=2$). For $N \ge 3$, pairwise sorting is an index heuristic, not a globally optimal policy.

---

## 2. Independent Derivation of the Pairwise Rule

### 2.1 The Pairwise Model
Let candidate frames $a$ and $b$ belong to flows with priority weights $w_a > 0$ and $w_b > 0$.
Their physical completion epochs are modeled as independent Gaussian random variables:
$$A_a \sim \mathcal{N}(\mu_a, \sigma_a^2), \quad A_b \sim \mathcal{N}(\mu_b, \sigma_b^2)$$
Define the difference variable:
$$Z \triangleq A_a - A_b \sim \mathcal{N}(d, \sigma_Z^2), \quad d = \mu_a - \mu_b, \quad \sigma_Z = \sqrt{\sigma_a^2 + \sigma_b^2} > 0$$

Under 802.11be in-order delivery:
- If sequence number $s_a < s_b$ (order $a < b$): Frame $b$ is blocked if $A_a > A_b$. The expected weighted penalty on frame $b$ is:
  $$C(a < b) = w_b \mathbb{E}[(A_a - A_b)^+] = w_b \mathbb{E}[Z^+]$$
- If sequence number $s_b < s_a$ (order $b < a$): Frame $a$ is blocked if $A_b > A_a$. The expected weighted penalty on frame $a$ is:
  $$C(b < a) = w_a \mathbb{E}[(A_b - A_a)^+] = w_a \mathbb{E}[(-Z)^+]$$

### 2.2 Truncated Gaussian Expectations
Let $u = d / \sigma_Z = (\mu_a - \mu_b) / \sigma_Z$. By direct integration:
$$\mathbb{E}[Z^+] = \int_{-d/\sigma_Z}^{\infty} (d + \sigma_Z t) \phi(t) dt = \sigma_Z [\phi(u) + u \Phi(u)]$$
Using the identity $Z^+ - (-Z)^+ = Z$, taking expectations yields $\mathbb{E}[(-Z)^+] = \mathbb{E}[Z^+] - d$. Hence:
$$\mathbb{E}[(-Z)^+] = \sigma_Z [\phi(u) + u \Phi(u)] - \sigma_Z u = \sigma_Z [\phi(u) - u(1 - \Phi(u))]$$

### 2.3 Pairwise Cost Difference & The Function $h(u)$
The difference between the two sequence choices is:
$$\Delta C(a, b) \triangleq C(a < b) - C(b < a) = w_b \mathbb{E}[Z^+] - w_a \mathbb{E}[(-Z)^+]$$
Substituting the truncated expectations and factoring $\sigma_Z$:
$$\Delta C(a, b) = \sigma_Z \cdot h(u)$$
where
$$h(u) \triangleq (w_b - w_a) \phi(u) + \left[ w_a(1 - \Phi(u)) + w_b \Phi(u) \right] u$$

### 2.4 Monotonicity and Existence of Unique Root
Differentiating $h(u)$ with respect to $u$:
$$h'(u) = (w_b - w_a)\phi'(u) + (w_b - w_a)\phi(u)u + [w_a(1 - \Phi(u)) + w_b \Phi(u)] + u [-w_a \phi(u) + w_b \phi(u)]$$
Since $\phi'(u) = -u \phi(u)$, the first two terms cancel identically:
$$(w_b - w_a)(-u\phi(u)) + (w_b - w_a)(u\phi(u)) = 0$$
Thus:
$$h'(u) = w_a(1 - \Phi(u)) + w_b \Phi(u)$$
Because $w_a > 0$, $w_b > 0$, and $\Phi(u) \in (0, 1)$ for all $u \in \mathbb{R}$, $h'(u) > 0$ strictly everywhere.
Therefore:
1. $h(u)$ is strictly monotonically increasing.
2. $\lim_{u \to -\infty} h(u) = -\infty$ and $\lim_{u \to +\infty} h(u) = +\infty$.
3. By the Intermediate Value Theorem, there exists a **unique** real root $u^*(w_a, w_b)$ such that $h(u^*) = 0$.

Because $h(u)$ is strictly increasing:
$$C(a < b) \le C(b < a) \iff h(u) \le 0 \iff \frac{\mu_a - \mu_b}{\sqrt{\sigma_a^2 + \sigma_b^2}} \le u^*(w_a, w_b)$$

### 2.5 Boundary Behaviors
- **Equal Weights ($w_a = w_b$):** $(w_b - w_a) = 0 \implies h(u) = w_a u = 0 \implies u^* = 0$. Decision reduces to $\mu_a \le \mu_b$.
- **Equal Means ($d = 0 \implies u = 0$):** $h(0) = (w_b - w_a)\phi(0)$. If $w_b > w_a$, $h(0) > 0 \implies u^* < 0$. $a < b$ is favored only if $\mu_a$ is substantially smaller than $\mu_b$ ($d / \sigma_Z \le u^* < 0$).
- **Anti-symmetry:** $h_{b, a}(-u) = -h_{a, b}(u) \implies u^*(w_b, w_a) = -u^*(w_a, w_b)$.
- **Vanishing Variance ($\sigma_Z \to 0$):** $\Delta C \to \max(0, d)w_b - \max(0, -d)w_a$. For $d < 0$, $C(a < b) = 0 < -d w_a = C(b < a)$. Decision collapses to deterministic ordering $\mu_a \le \mu_b$.

---

## 3. Direct Transitivity Test and Cycle Proof

### 3.1 Candidate Triplet Evaluation
We independently evaluate the candidate triplet using numerical integration and analytical formulas:

| Frame | Mean Completion ($\mu$) | Standard Deviation ($\sigma$) | Priority Weight ($w$) |
| :--- | :---: | :---: | :---: |
| **A** | -0.0060 | 0.1069 | 4.10 |
| **B** | 0.1068 | 0.1101 | 20.80 |
| **C** | -0.0845 | 0.2477 | 2.85 |

#### Pairwise Comparisons:
1. **Frame A vs. Frame B:**
   - $d_{AB} = -0.0060 - 0.1068 = -0.1128$
   - $\sigma_{AB} = \sqrt{0.1069^2 + 0.1101^2} = 0.15346$
   - $u_{AB} = -0.1128 / 0.15346 = -0.73504$
   - $C(A < B) = 20.80 \times \mathbb{E}[(A_A - A_B)^+] = \mathbf{0.429600}$
   - $C(B < A) = 4.10 \times \mathbb{E}[(A_B - A_A)^+] = \mathbf{0.547161}$
   - Difference: $\Delta C = -0.117561 < 0 \implies \mathbf{A \prec B}$ (A placed before B is preferred).

2. **Frame B vs. Frame C:**
   - $d_{BC} = 0.1068 - (-0.0845) = +0.1913$
   - $\sigma_{BC} = \sqrt{0.1101^2 + 0.2477^2} = 0.27107$
   - $u_{BC} = 0.1913 / 0.27107 = +0.70572$
   - $C(B < C) = 2.85 \times \mathbb{E}[(A_B - A_C)^+] = \mathbf{0.654518}$
   - $C(C < B) = 20.80 \times \mathbb{E}[(A_C - A_B)^+] = \mathbf{0.797794}$
   - Difference: $\Delta C = -0.143276 < 0 \implies \mathbf{B \prec C}$ (B placed before C is preferred).

3. **Frame C vs. Frame A:**
   - $d_{CA} = -0.0845 - (-0.0060) = -0.0785$
   - $\sigma_{CA} = \sqrt{0.2477^2 + 0.1069^2} = 0.26978$
   - $u_{CA} = -0.0785 / 0.26978 = -0.2910$
   - $C(C < A) = 4.10 \times \mathbb{E}[(A_C - A_A)^+] = \mathbf{0.298899}$
   - $C(A < C) = 2.85 \times \mathbb{E}[(A_A - A_C)^+] = \mathbf{0.431496}$
   - Difference: $\Delta C = -0.132597 < 0 \implies \mathbf{C \prec A}$ (C placed before A is preferred).

#### Result:
$$\mathbf{A \prec B, \quad B \prec C, \quad C \prec A}$$
This constitutes a **strict Condorcet cycle**. Every preference has a substantial numerical margin ($> 0.11$). Transitivity fails conclusively.

### 3.2 Broader Parameter Search & Domain Characterization
To characterize where transitivity holds versus where cycles emerge, we executed three large-scale Monte Carlo grid searches:

1. **Unconstrained Heterogeneous Parameters (100,000 random triplets):**
   - $\mu \in [-0.5, 0.5]$, $\sigma \in [0.05, 0.5]$, $w \in [1.0, 50.0]$
   - **Result:** **164 cycles observed (0.164%)**.
2. **Equal Weights Domain ($w_a = w_b = w_c = w$):**
   - 100,000 random triplets with $\mu \in [-0.5, 0.5]$, $\sigma \in [0.05, 0.5]$, identical $w$.
   - **Result:** **0 cycles (0.0%)**.
   - *Mathematical Proof:* When weights are equal, $u^* = 0$, so $a \prec b \iff \mu_a \le \mu_b$. Since standard inequality on real numbers is a total linear order, transitivity is unconditionally preserved.
3. **Equal Variance Domain ($\sigma_a = \sigma_b = \sigma_c = 0.1$):**
   - 1,000,000 random triplets with $\mu \in [-0.5, 0.5]$, heterogeneous weights $w \in [1.0, 50.0]$.
   - **Result:** **1 cycle observed (0.0001%)**. Cycles are extremely rare under equal variance, but still mathematically possible when weight ratios create non-linear threshold shifts that interact with near-boundary mean differences.
4. **Separated Means Domain ($|\Delta\mu| \gg \sigma$):**
   - When mean differences exceed $3\sigma$, the pairwise threshold root $u^*$ is dominated by the mean difference: $a \prec b \iff \mu_a < \mu_b$. The relation is transitive.

---

## 4. Implementation Code Audit (`src/mlo_sim/schedulers.py`)

We inspected `SASPScheduler.schedule()` (lines 366–483) and verified:

1. **Batch Joint Sequencing (Lines 390–434):**
   - Lines 391–403: Constructs greedy bipartite matching between sorted idle links (by $\hat{\mu}$) and sorted flows (by weight).
   - Lines 411–420:
     ```python
     # Pairwise threshold ordering via Theorem 3 if use_variance
     if self.use_variance and len(predictions) == 2:
         w1, w2 = predictions[0][1], predictions[1][1]
         u_star = compute_threshold_root(w1, w2)
         sigma_pair = math.sqrt(predictions[0][3].estimated_std_ms**2 + predictions[1][3].estimated_std_ms**2)
         delta_mu = predictions[0][0] - predictions[1][0]
         if delta_mu / max(1e-6, sigma_pair) > u_star:
             predictions.reverse()
     else:
         predictions.sort(key=lambda x: x[0])
     ```
   - **Exact Finding:** Theorem 3's threshold root $u^*$ is evaluated **strictly when $len(predictions) == 2$**!
   - For $N > 2$ candidates, the scheduler executes `predictions.sort(key=lambda x: x[0])`—which sorts solely by scalar projected arrival $\hat{A} = t_{\text{curr}} + \hat{\mu}$. This is **Mean-Only Sequencing**!
   - This architectural choice was protective: passing an intransitive pairwise comparator to Python's `list.sort(key=functools.cmp_to_key(...))` would violate Timsort's strict weak ordering requirement and cause non-deterministic behavior.
2. **Single-Link Scheduling (Lines 451–472):**
   - Single-link candidates are evaluated against in-flight frames using an ad-hoc scalar cost:
     ```python
     cost = (link.estimated_mean_ms / w_f) + 2.0 * inflight_penalty
     ```
   - Sequence number is assigned strictly upon dispatch: `sn = self.next_seq_num; self.next_seq_num += 1`. In-flight frames retain their previously committed sequence numbers.

---

## 5. Specification of Multi-Frame Policy and Cycle Resolution

### 5.1 True Aggregate Receiver Delay Objective
Let candidate frames $\{1, \dots, N\}$ be assigned sequence numbers according to permutation $\pi = (\pi(1), \dots, \pi(N))$, where $\pi(k) \in \{1, \dots, N\}$ is the sequence rank of frame $k$.
Under IEEE 802.11be in-order release:
$$R_k = \max\left(A_k, \max_{j: \pi(j) < \pi(k)} A_j\right) = \max_{j: \pi(j) \le \pi(k)} A_j$$
The reordering delay of frame $k$ is $\Delta_k = R_k - A_k$.
The true aggregate weighted cost of permutation $\pi$ across the batch is:
$$J(\pi) \triangleq \mathbb{E}\left[ \sum_{k=1}^N w_k \left( \max_{j: \pi(j) \le \pi(k)} A_j - A_k \right) \right]$$

### 5.2 Exhaustive Permutation Evaluation for Candidate Triplet (A, B, C)
For the intransitive triplet ($A \prec B, B \prec C, C \prec A$), we evaluate all $3! = 6$ possible permutations under the exact aggregate objective $J(\pi)$ using 200,000 Monte Carlo draws:

| Permutation $\pi$ | Sequence Rank ($s=0, 1, 2$) | Aggregate Weighted Delay $J(\pi)$ | Relative to Optimal | Description |
| :---: | :---: | :---: | :---: | :--- |
| **ABC** | $s_A = 0, s_B = 1, s_C = 2$ | **1.128306** | **0.0% (GLOBAL OPTIMUM)** | Assigns $s=0$ to fast frame A, $s=1$ to high-priority B, $s=2$ to high-variance C |
| **BAC** | $s_B = 0, s_A = 1, s_C = 2$ | **1.245819** | +10.4% | Places high-priority B first |
| **BCA** | $s_B = 0, s_C = 1, s_A = 2$ | **1.335585** | +18.4% | Places A last |
| **CAB** | $s_C = 0, s_A = 1, s_B = 2$ | **1.390335** | +23.2% | Follows $C \prec A$ |
| **CBA** | $s_C = 0, s_B = 1, s_A = 2$ | **1.473747** | +30.6% | Places C first |
| **ACB** | $s_A = 0, s_C = 1, s_B = 2$ | **1.525722** | **+35.2% (WORST)** | Traps high-priority B behind high-variance C |

#### Crucial Insights:
1. **Unambiguous Global Optimum Exists:** While pairwise preferences form a cycle ($A \prec B \prec C \prec A$), the true aggregate batch objective $J(\pi)$ has an unambiguous global minimizer: **permutation $ABC$**.
2. **Failure of Naive Pairwise Following:** Following the preference $C \prec A$ by placing C before A produces $CAB$ (cost 1.390) or $ACB$ (cost 1.526)—the worst possible permutation! Why? Because placing C before B heavily penalizes high-priority frame B ($w_B = 20.80$) due to C's large variance ($\sigma_C = 0.2477$).
3. **Double-Counting Flaw of Pairwise Summation:** Summing pairwise costs $\sum_{i < j} C(\pi_i < \pi_j)$ overcounts delay because $\Delta_k = \max(0, A_1 - A_k, A_2 - A_k)$ is strictly sub-additive: $\max(X, Y) \le X^+ + Y^+$.

---

## 6. Formal Policy Recommendations for the Paper & Scheduler

1. **Clarify Scope in Theorem 3:**
   - Retain Theorem 3 as an **exact, provably optimal pairwise rule for $N=2$**.
   - Explicitly state in the theorem remarks that for $N \ge 3$, the pairwise relation is non-transitive, and pairwise index sorting is an efficient $\mathcal{O}(M \log M)$ heuristic.
2. **Small-Batch Permutation Policy for Wi-Fi 7 ($N \le 3$):**
   - In 802.11be hardware, an AP MLD operates 2 or 3 links (2.4 GHz, 5 GHz, 6 GHz). Therefore, concurrent batch dispatches are restricted to $N \in \{2, 3\}$.
   - For $N = 2$: Theorem 3 threshold root gives the exact global optimum ($2! = 2$ choices).
   - For $N = 3$: Evaluate the $3! = 6$ permutations under expected aggregate delay or Clark's approximation to choose the global minimum, requiring $< 1.5\,\mu\text{s}$.
3. **Unit Tests Added:**
   - `tests/test_pairwise_transitivity.py` (5 tests, all passing):
     - Validates closed-form pairwise cost against independent adaptive numerical quadrature.
     - Confirms the algebraic difference identity $\Delta C \equiv \sigma_Z h(u)$.
     - Demonstrates the strict three-frame cycle $A \prec B, B \prec C, C \prec A$.
     - Proves transitivity preservation under equal weights ($w_a = w_b = w_c$).
     - Evaluates the 6 batch permutations under Monte Carlo integration.

---
*End of Multi-Frame Ordering Audit.*
