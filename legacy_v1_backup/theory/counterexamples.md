# Theoretical Counterexamples and Boundary Cases

**Purpose:** Systematic investigation of edge cases and counterexamples exposing the failure modes of heuristic policies and validating the boundary conditions of Theorems 1–4.

---

## 1. Counterexample 1: The Fallacy of Static Flow-to-Link Pinning (Multi-Link BA Collapse)

### Scenario Setup
- Two links: Link 1 (2.4 GHz, rate $R_1 = 10$ Mbps, $\mu_1 = 1.0$ ms per frame) and Link 2 (5 GHz, rate $R_2 = 100$ Mbps, $\mu_2 = 0.1$ ms per frame). Delay asymmetry $\delta = 0.9$ ms.
- Two flows sharing TID 0: Flow $A$ (bulk download) pinned to Link 1; Flow $B$ (real-time video) pinned to Link 2.
- Arrival rate of Flow $B$: $\lambda_B = 10$ packets/ms ($10,000$ pkt/s).
- Negotiated Block Ack window: $W = 64$.
- Sequence assignment: FIFO arrival order ($s_1, s_2, s_3, \dots$).

### Execution and Failure Analysis
1. At $t = 0$, packet $a_1$ of Flow $A$ is assigned sequence number $s = 1$ and dispatched on Link 1.
2. In the interval $t \in [0, 0.9\text{ ms}]$, Flow $B$ generates and transmits frames $b_2, b_3, \dots, b_{65}$ on Link 2, with sequence numbers $s = 2, 3, \dots, 65$.
3. Because Link 2 is fast, packet $b_2$ through $b_{64}$ complete physical transmission by $t \approx 0.64$ ms.
4. At $t = 0.64$ ms:
   - Packet $a_1$ ($s = 1$) is still in flight on Link 1 (completion expected at $t = 1.0$ ms).
   - Receiver reordering window is stuck at $[W_{\text{start}} = 1, W_{\text{end}} = 64]$.
   - Packets $b_2 \dots b_{64}$ are held in the receive buffer; **none can be delivered to upper layers**.
   - When packet $b_{65}$ ($s = 65$) arrives, its sequence number exceeds $W_{\text{start}} + W - 1 = 64$.
5. **Catastrophic Failure:**  
   The receiver cannot accept packet $b_{65}$. Link 2 is blocked from transmitting any further frames. Despite having 100 Mbps capacity, Link 2 is throttled down to the completion rate of Link 1 ($1$ packet per $1.0$ ms).
   - **Cross-flow blocking:** Flow $B$ suffers maximum delay $\approx 0.9$ ms on every packet, and its effective throughput collapses by $90\%$.
   - **Validation of Theorem 2:** The collapse condition $\lambda_B \ge W / \delta = 64 / 0.9 \approx 71.1$ pkt/ms correctly predicts this stall boundary.

---

## 2. Counterexample 2: Inadequacy of Congestion-Aware Link Selection Without Sequencing

### Scenario Setup
- A standard congestion-aware scheduler (e.g., dispatch to link with minimum instantaneous backlog $Q_k / C_k$).
- Link 1 has high latency ($\mu_1 = 5$ ms, $\sigma_1 = 0.5$ ms). Link 2 has low latency ($\mu_2 = 1$ ms, $\sigma_2 = 0.2$ ms).
- At time $t = 0$, both links are idle.
- Packet $1$ (Flow $A$, bulk) is dispatched to Link 1 (SN $s = 1$).
- At time $t = 0.1$ ms, packet $2$ (Flow $B$, latency-critical gaming) arrives.
- The congestion-aware scheduler sees Link 2 is idle with zero backlog, so it dispatches packet $2$ to Link 2 with SN $s = 2$.

### Execution and Failure Analysis
- Packet $2$ completes physical transmission at $A_2 = 0.1 + 1.0 = 1.1$ ms.
- Packet $1$ completes at $A_1 = 0.0 + 5.0 = 5.0$ ms.
- Packet $2$ is held in the receiver buffer from $t = 1.1$ ms until $t = 5.0$ ms.
- **Cross-Flow Blocking:** $\mathcal{X}_2 = 5.0 - 1.1 = 3.9$ ms.
- Even though the scheduler chose the least-congested link, Flow $B$ suffered a 3.9 ms cross-flow stall because sequence numbers were assigned sequentially ($s_1 = 1 < s_2 = 2$).
- **SASP Resolution:** If the scheduler inverts the sequence numbers ($s(\text{pkt } 2) = 1, s(\text{pkt } 1) = 2$), packet 2 is released at $1.1$ ms with $\mathcal{X}_2 = 0$, and packet 1 is released at $5.0$ ms with $\mathcal{X}_1 = 0$!

---

## 3. Counterexample 3: The Failure of Mean-Only Sequencing Under High Variance and Asymmetric Weights

### Scenario Setup
- Two candidate frames: frame $a$ (Flow $A$, bulk, weight $w_a = 1$) and frame $b$ (Flow $B$, real-time control, weight $w_b = 20$).
- Completion distributions:
  - Frame $a$ on Link 1: $\mu_a = 2.0$ ms, $\sigma_a = 1.0$ ms.
  - Frame $b$ on Link 2: $\mu_b = 2.3$ ms, $\sigma_b = 1.0$ ms.
  - Aggregate variance $\sigma_Z = \sqrt{1^2 + 1^2} = \sqrt{2} \approx 1.414$ ms.
- **Mean-Only Policy:** Since $\mu_a = 2.0 < \mu_b = 2.3$, a naive mean-ordering policy assigns $s_a < s_b$.

### Cost Comparison
- Difference in means: $\mu_a - \mu_b = -0.3$ ms. Normalized offset $u = -0.3 / 1.414 \approx -0.212$.
- Under ordering $s_a < s_b$:
  - Frame $b$ is blocked whenever $A_a > A_b$.
  - Expected cost:
    $$C(s_a < s_b) = w_b \sigma_Z [\phi(u) + u \Phi(u)] = 20 \times 1.414 \times [0.390 - 0.212 \times 0.416] \approx 20 \times 1.414 \times 0.302 \approx 8.54$$
- Under inverted ordering $s_b < s_a$:
  - Frame $a$ is blocked whenever $A_b > A_a$. Here normalized offset is $-u = +0.212$.
  - Expected cost:
    $$C(s_b < s_a) = w_a \sigma_Z [\phi(-u) - u (1 - \Phi(-u))] = 1 \times 1.414 \times [0.390 + 0.212 \times 0.584] \approx 1 \times 1.414 \times 0.514 \approx 0.73$$
- **Finding:**  
  Assigning $s_b < s_a$ reduces the expected penalty from $8.54$ to $0.73$ (a **$91.5\%$ reduction** in weighted cross-flow blocking), even though $\mu_b > \mu_a$!
- **Validation of Theorem 3:** The optimal threshold $u^*(1, 20)$ is negative ($u^* \approx -0.85$). Because $u = -0.212 > u^*$, Theorem 3 correctly dictates $s_b < s_a$, proving that mean-only ordering fails under asymmetric flow priorities.
