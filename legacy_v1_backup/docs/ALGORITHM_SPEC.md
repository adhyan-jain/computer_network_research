# Algorithm Specification: Sequence-Aware Stochastic Partitioning (SASP)

**Sublayer:** Transmitter Upper MAC (U-MAC) Scheduling and Sequence Management  
**Standard Conformance:** IEEE Std 802.11be-2024 (Wi-Fi 7)  
**Target:** Elimination of Cross-Flow Head-of-Line Blocking under Shared Per-TID Sequence Number Spaces  

---

## 1. Architectural Overview

The **Sequence-Aware Stochastic Partitioning (SASP)** algorithm operates inside the transmitter's U-MAC sublayer. It coordinates three joint decisions at each scheduling opportunity:
1. **Flow Selection:** Selecting which flow $f \in \mathcal{F}$ to serve next from per-flow admission queues.
2. **Link Dispatching:** Steering the selected frame to the optimal available Lower MAC (L-MAC) link $\ell \in \mathcal{K}$.
3. **Predictive Sequence Number Assignment:** Allocating sequence numbers $s \in [0, 4095]$ dynamically according to the stochastic completion ordering dictated by Theorem 3, rather than static FIFO arrival order.

```
       +-----------------------------------------------------+
       |         Upper Layers (LLC / IP Flows f in F)        |
       +-----------------------------------------------------+
                                  |
                                  v
       +-----------------------------------------------------+
       |              U-MAC SASP Controller                  |
       |  - Flow Admission Queues Q_1 ... Q_M                |
       |  - Runtime Link Delay Estimators (mu_k, sigma_k^2)  |
       |  - In-flight Window Tracker [WinStart, WinStart+W)  |
       |  - Theorem 3 Threshold Decision Engine              |
       +-----------------------------------------------------+
                 |                     |               |
                 v                     v               v
           [Link 1 L-MAC]        [Link 2 L-MAC]  [Link K L-MAC]
            (e.g., 2.4 GHz)       (e.g., 5 GHz)   (e.g., 6 GHz)
                 |                     |               |
       =================== Wireless Medium ===================
                 |                     |               |
                 v                     v               v
           [Link 1 PHY]          [Link 2 PHY]    [Link K PHY]
                 \                     |              /
                  v                    v             v
       +-----------------------------------------------------+
       |        Standard IEEE 802.11be Receiver MLD          |
       |        - Single Per-TID Reorder Buffer (WinSize W)  |
       |        - Strict In-Order Sequence Release           |
       +-----------------------------------------------------+
                                  |
                                  v
       +-----------------------------------------------------+
       |              Upper Layers (LLC / IP)                |
       +-----------------------------------------------------+
```

---

## 2. Formal Inputs, Outputs, and State

### Inputs (at scheduling epoch $t$):
- $\mathcal{K}$: Set of active operational links, with link states (idle or available queue slot).
- $\mathcal{F}$: Set of flows sharing the TID, with priority weights $\{w_f\}_{f \in \mathcal{F}}$.
- $\{Q_f(t)\}_{f \in \mathcal{F}}$: Per-flow transmission queues at U-MAC.
- $W$: Negotiated Block Ack window size (e.g., $W = 64$ or $256$).
- BA feedback events from L-MAC (acknowledged sequence numbers and bitmaps).

### Outputs:
- Triple $(p^*, \ell^*, s^*)$:
  - $p^*$: Chosen packet from head-of-line of flow $f^*$.
  - $\ell^* \in \mathcal{K}$: Selected link for transmission.
  - $s^* \in [0, 4095]$: Assigned IEEE 802.11 sequence number.

### Internal State Maintained:
1. **Link Statistics Vector:** For each link $k \in \mathcal{K}$:
   - $\hat{\mu}_k$: Estimated mean completion time (exponentially weighted moving average).
   - $\hat{\sigma}_k^2$: Estimated completion time variance.
   - $\hat{p}_k$: Estimated frame error rate (FER).
2. **In-Flight Registry ($\mathcal{O}$):**
   - Set of packets currently dispatched but not yet acknowledged: $\mathcal{O} = \{(s_j, f_j, \ell_j, t_j^{\text{disp}}, \hat{A}_j)\}$.
3. **Sequence Window Boundaries:**
   - $s_{\text{min}}$: Earliest unacknowledged sequence number in flight: $s_{\text{min}} = \min_{(j \in \mathcal{O})} s_j$ (or next available if $\mathcal{O} = \emptyset$).
   - $s_{\text{next}}$: High-water mark of allocated sequence numbers.
   - Flow-specific last sequence number: $\text{last\_sn}[f]$ to enforce intra-flow monotonicity (Assumption A4).

---

## 3. Algorithm Logic and Pseudocode

### 3.1 Runtime Link Delay Estimation
Whenever a packet transmission on link $k$ completes (confirmed via BA bitmap at duration $D_{\text{obs}}$):
$$\hat{\mu}_k \leftarrow (1 - \alpha) \hat{\mu}_k + \alpha D_{\text{obs}}$$
$$\hat{\sigma}_k^2 \leftarrow (1 - \beta) \hat{\sigma}_k^2 + \beta (D_{\text{obs}} - \hat{\mu}_k)^2$$
where $\alpha, \beta \in (0, 1)$ are smoothing constants (default: $\alpha = 0.1, \beta = 0.05$).

### 3.2 SASP Scheduling Epoch Procedure

```python
def sasp_schedule_epoch(current_time, available_links, queues, inflight_set, link_stats, W):
    """
    SASP: Joint Flow Selection, Link Dispatching, and Predictive Sequencing
    """
    # Step 1: Filter candidate flows with non-empty queues
    eligible_flows = [f for f in flows if len(queues[f]) > 0]
    if not eligible_flows or not available_links:
        return None  # Nothing to schedule

    best_decision = None
    min_projected_cost = float('inf')

    # Step 2: Evaluate candidate pairs of (flow, link)
    for ell in available_links:
        mu_ell = link_stats[ell].mean
        sigma_ell = link_stats[ell].std

        for f in eligible_flows:
            pkt = queues[f].peek()
            w_f = pkt.weight
            
            # Projected arrival time of candidate packet
            proj_arrival = current_time + mu_ell

            # Calculate potential cross-flow blocking penalty against currently in-flight frames
            projected_cross_penalty = 0.0
            for inflight in inflight_set:
                if inflight.flow != f:
                    # If inflight has earlier SN, candidate waits if proj_arrival < inflight.arrival
                    # If candidate has earlier SN, inflight waits if inflight.arrival < proj_arrival
                    w_other = inflight.weight
                    sigma_pair = math.sqrt(sigma_ell**2 + inflight.sigma**2)
                    delta_mu = inflight.proj_arrival - proj_arrival
                    
                    # Compute Theorem 3 threshold root u*
                    u_star = compute_threshold_root(w_other, w_f)
                    u_pair = delta_mu / sigma_pair
                    
                    # Cost under optimal sequence assignment between this pair
                    if u_pair >= u_star:
                        # inflight should precede candidate (s_inflight < s_candidate)
                        projected_cross_penalty += w_f * gaussian_partial_expectation(delta_mu, sigma_pair)
                    else:
                        # candidate should precede inflight (s_candidate < s_inflight)
                        projected_cross_penalty += w_other * gaussian_partial_expectation(-delta_mu, sigma_pair)

            # Combined objective: weighted delay + cross-flow blocking penalty
            total_candidate_cost = w_f * mu_ell + projected_cross_penalty

            if total_candidate_cost < min_projected_cost:
                min_projected_cost = total_candidate_cost
                best_decision = (f, ell, proj_arrival)

    if best_decision is None:
        return None

    selected_flow, selected_link, proj_arrival = best_decision
    packet = queues[selected_flow].pop()

    # Step 3: Predictive Sequence Number Assignment (Theorem 3)
    # Ensure:
    # 1. Intra-flow monotonicity: s > last_sn[selected_flow]
    # 2. BA Window Constraint: s - s_min_inflight < W
    # 3. Inter-flow completion ordering: sort relative to concurrent frames
    assigned_sn = allocate_predictive_sn(
        flow=selected_flow,
        proj_arrival=proj_arrival,
        inflight_set=inflight_set,
        last_sn_per_flow=last_sn_per_flow,
        W=W
    )

    # Step 4: Dispatch to L-MAC
    dispatch_to_link(packet, selected_link, assigned_sn)
    inflight_set.add(packet, assigned_sn, selected_flow, selected_link, proj_arrival)
    return (packet, selected_link, assigned_sn)
```

---

## 4. Complexity Analysis

- **Time Complexity per Scheduling Decision:**  
  Let $M = |\mathcal{F}|$ denote the number of active flows, $K = |\mathcal{K}|$ denote the number of links, and $N_{\text{inf}} = |\mathcal{O}|$ denote the number of currently in-flight frames ($N_{\text{inf}} \le W$).
  - Evaluating all flow-link combinations: $M \times K$ candidate evaluations.
  - For each candidate, comparing against in-flight frames requires evaluating $N_{\text{inf}}$ pairwise terms.
  - Computing $u^*$ takes $\mathcal{O}(1)$ via pre-computed lookup table or Newton-Raphson iteration (converging in $\le 4$ steps).
  - Worst-case time complexity per decision: $\mathcal{O}(M \cdot K \cdot W)$.
  - For typical Wi-Fi 7 configurations ($M \le 8$, $K \le 3$, $W \le 64$), the total number of operations is $\le 1536$ basic floating point operations, executing in $< 5\,\mu\text{s}$ on modern wireless SoC embedded processors.
- **Space Complexity:**  
  - In-flight registry stores at most $W$ frame descriptors: $\mathcal{O}(W)$ space.
  - Link statistics: $\mathcal{O}(K)$ space.
  - Total space complexity: $\mathcal{O}(W + K)$, strictly bounded and negligible ($< 4$ KB RAM).

---

## 5. Baselines for Rigorous Empirical Benchmarking

To prove that the performance gains stem directly from our theoretical sequencing and cross-flow awareness, SASP is evaluated against eight distinct baselines:

1. **Single-Link Operation (SLO):** The standard legacy benchmark where the transmitter uses only the fastest individual link (e.g., 5 GHz or 6 GHz).
2. **Default ns-3 MLO (FIFO-Earliest):** Default 802.11be architecture where sequence numbers are allocated in strict arrival order (FIFO), and frames are dispatched to the earliest available link queue.
3. **Round-Robin Multi-Link (RR):** Distributes consecutive packets in round-robin sequence across available links with FIFO sequence numbers.
4. **Lowest-Latency-First Link Selection (LLF):** Dispatches packets to the link with the lowest estimated transmission delay $\hat{\mu}_k$, but with standard FIFO sequence numbers.
5. **Congestion-Aware Link Allocation (CALA):** Dispatches packets to the link minimizing instantaneous queue backlog $Q_k / C_k$ (similar to Carreño et al., 2021).
6. **Static Flow-to-Link Pinning (TID-Link Mapping):** Latency-sensitive flow is pinned to the high-speed link; bulk flow is pinned to the lower-speed link, sharing the TID sequence space (illustrating Counterexample 1).
7. **BA-Window-Aware Retransmission Steering (WARS):** Retransmissions of failed frames are steered to cleaner links (Oliveira et al., 2026), but new transmissions follow standard FIFO sequencing.
8. **Offline Oracle (Lower Bound):** Non-causal scheduler with perfect future knowledge of exact channel realizations $A_i$, allocating sequence numbers to achieve the theoretical minimum reordering delay.
