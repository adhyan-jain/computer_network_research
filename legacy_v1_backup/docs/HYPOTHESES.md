# Frozen Experimental Hypotheses

**Status:** Frozen prior to experiment execution  
**Date:** 2026-10-12  
**Standard:** IEEE 802.11be Wi-Fi 7 Multi-Link Operation  

---

## Hypothesis 1 (Cross-Flow Inversion Penalty Under FIFO)
- **Prediction:** Under standard FIFO sequence allocation across heterogeneous links with delay asymmetry $\delta = \mu_1 - \mu_2 > 0$, the receiver reordering delay $\Delta$ is dominated by cross-flow blocking $\mathcal{X}$, which increases monotonically with link asymmetry $\delta$ and traffic load $\lambda$.
- **Causal Mechanism:** Packets of the faster flow dispatched on the faster link arrive out of sequence number order relative to earlier-sequenced packets of the slower flow on the slower link, forcing the faster frames to sit unreleased in the receive buffer.
- **Primary Metric:** Mean cross-flow blocking delay $\mathbb{E}[\mathcal{X}]$ and ratio $\mathbb{E}[\mathcal{X}] / \mathbb{E}[\Delta]$.
- **Baseline for Comparison:** Single-Link Operation (SLO) and default ns-3 MLO (FIFO).
- **Falsification / Kill Condition:** If $\mathbb{E}[\mathcal{X}]$ remains constant or diminishes as link asymmetry $\delta$ increases, Hypothesis 1 is refuted.

---

## Hypothesis 2 (Multi-Link BA Window Collapse Boundary)
- **Prediction:** When the arrival rate of packets on the fast link exceeds the critical boundary $\lambda^* = W / \delta$, the reordering buffer reaches permanent saturation under FIFO dispatching, causing a sharp drop in fast-link throughput (goodput collapse) and a surge in tail latency (p99).
- **Causal Mechanism:** Outstanding unreleased frames reach the negotiated Block Ack window limit $W$, blocking the transmitter from allocating new sequence numbers without violating the receiver's window $[W_{\text{start}}, W_{\text{start}} + W - 1]$.
- **Primary Metric:** Fast-link throughput, stall probability, and p99 latency as a function of normalized load $\lambda / \lambda^*$.
- **Baseline:** Static flow pinning vs. SASP.
- **Falsification / Kill Condition:** If the fast link sustains its full unconstrained throughput beyond $\lambda^* = W / \delta$ under FIFO sequencing without window advance drops, Hypothesis 2 is refuted.

---

## Hypothesis 3 (SASP Cross-Flow Blocking Reduction)
- **Prediction:** SASP achieves a statistically significant reduction in weighted cross-flow blocking (at least $60\%$ reduction relative to default FIFO MLO) across diverse channel conditions, approaching within $15\%$ of the offline non-causal Oracle lower bound.
- **Causal Mechanism:** Theorem 3's optimal predictive sequencing dynamically assigns earlier sequence numbers to frames with earlier expected completion times, preventing physical arrivals from inverting sequence order at the receiver.
- **Primary Metric:** Expected weighted cross-flow blocking $\sum_f w_f \mathbb{E}[\mathcal{X}_f]$ and p95/p99 reordering delay.
- **Baseline:** Default ns-3 MLO (FIFO), Congestion-Aware (CALA), Lowest-Latency (LLF), and Retransmission-Steering (WARS).
- **Falsification / Kill Condition:** If SASP fails to achieve at least a $30\%$ reduction in cross-flow blocking over default FIFO MLO, or is matched by a non-sequencing heuristic (e.g., CALA), Hypothesis 3 is refuted.

---

## Hypothesis 4 (Priority Protection for Latency-Sensitive Traffic)
- **Prediction:** Under asymmetric flow weights ($w_{\text{interactive}} \gg w_{\text{bulk}}$), SASP reduces the cross-flow blocking experienced by the interactive flow by over $80\%$ without degrading aggregate system throughput.
- **Causal Mechanism:** The negative threshold $u^*(w_A, w_B) < 0$ systematically prioritizes the sequence assignment of latency-sensitive packets, isolating them from bulk flow retransmission bursts.
- **Primary Metric:** Interactive flow latency distribution (p50, p95, p99) and aggregate goodput.
- **Baseline:** Equal-weight SASP and CALA.
- **Falsification / Kill Condition:** If the interactive flow experiences equal or greater cross-flow delay under asymmetric weights compared to equal weights, Hypothesis 4 is refuted.

---

## Hypothesis 5 (Resilience to Estimation Error and Channel Variance)
- **Prediction:** Even when runtime link delay variance $\hat{\sigma}^2$ has up to $50\%$ estimation error (mismatch between estimated and true channel parameters), SASP maintains at least a $40\%$ reduction in cross-flow blocking over FIFO baselines.
- **Causal Mechanism:** The Gaussian integral formulation in Theorem 3 is smooth and continuous in $\sigma_Z$, ensuring graceful degradation under noisy parameter tracking.
- **Primary Metric:** Sensitivity degradation curve: $\Delta \mathcal{X}$ vs. parameter error $\epsilon \in [-0.5, +0.5]$.
- **Falsification / Kill Condition:** If an estimation error of $20\%$ causes SASP to perform worse than default FIFO MLO, Hypothesis 5 is refuted.
