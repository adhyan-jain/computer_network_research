# Implementation and Protocol Feasibility Audit (Phase 2)

**Topic:** IEEE 802.11be Multi-Link Operation Sequence-Aware Stochastic Partitioning (SASP)  
**Date:** October 13, 2026  
**Auditor Role:** Independent Networking-Systems & Protocol Specialist  

---

## 1. End-to-End Packet Lifecycle & Control Flow

The simulation engine implements the standard Upper MAC (U-MAC) / Lower MAC (L-MAC) functional split specified in IEEE 802.11be (§ 9.2.4 and § 10.24). The complete packet trace is mapped below with exact file and line references:

```text
1. Packet Generation (src/mlo_sim/simulator.py:90-109)
   │  Flow generates Packet(packet_id, flow_id, size_bytes, arr_time, weight).
   │  packet.seq_num is None (UNASSIGNED).
   ▼
2. Queue Ingestion (src/mlo_sim/simulator.py:101)
   │  Packet appended to per-flow FIFO queue: self.queues[flow_id].append(pkt).
   │  No sequence numbers allocated during enqueue.
   ▼
3. Scheduling Trigger (src/mlo_sim/simulator.py:160-199)
   │  Invoked when packet arrives or link transmission completes.
   │  Gathers idle links: [l for l in links if l.current_packet is None and current_time >= l.busy_until].
   │  Calls scheduler.schedule(current_time, available_links, queues, flows, inflight, win_size, win_start).
   ▼
4. Sequence Allocation & Link Binding (src/mlo_sim/schedulers.py:423-430, 477-482)
   │  SASP performs joint candidate evaluation.
   │  Allocates sequence number: sn = self.next_seq_num; self.next_seq_num += 1.
   │  Binds packet to chosen Link: (pkt, selected_link, assigned_sn).
   ▼
5. L-MAC Transmission Initiation (src/mlo_sim/simulator.py:183-198)
   │  pkt.seq_num = assigned_sn; pkt.link_id = link.link_id; pkt.disp_time = current_time.
   │  Computes channel attempt delay via EDCA backoff: channel.simulate_transmission_attempt().
   │  Schedules EVENT_LINK_TX_COMPLETE at current_time + attempt_delay.
   ▼
6. Transmission Completion & Block Ack (src/mlo_sim/simulator.py:111-157)
   │  If frame lost: increment retries. If attempts < max_retries, reschedule with EDCA backoff.
   │  (Sequence number remains UNCHANGED on retransmission).
   │  If success: link.current_packet = None; notify scheduler via on_packet_completed().
   ▼
7. Receiver Reorder Buffer Ingestion (src/mlo_sim/core.py:107-147)
   │  BlockAckReceiver receives packet with arr_rx_time = current_time.
   │  If sn < win_start: dropped as duplicate/late.
   │  If sn >= win_start + win_size: forced window advance (win_start = sn - win_size + 1).
   │  Buffer insertion: self.buffer[sn] = packet.
   │  In-order release: releases contiguous sequence numbers starting from win_start.
   ▼
8. Delay Attribution & Higher-Layer Delivery (src/mlo_sim/core.py:149-184)
   │  Calculates exact decomposition: S_i = max(0, R_intra - A_i), X_i = max(0, rel_time - R_intra).
   │  Delivers packet to LLC.
```

---

## 2. Sequence Number Allocation Line Audit

Every scheduler allocates sequence numbers strictly at the **dispatch epoch immediately before transmission**, not during queue ingestion:

| Scheduler | File & Function | Source Lines | Allocation Logic |
| :--- | :--- | :--- | :--- |
| `SingleLink` | `schedulers.py:SingleLinkScheduler.schedule` | Lines 137–138 | `self._allocate_fifo_sn(best_flow)` (FIFO dispatch order) |
| `DefaultFIFO` | `schedulers.py:DefaultFifoScheduler.schedule` | Lines 174–175 | `self._allocate_fifo_sn(best_flow)` (Earliest available link, FIFO order) |
| `RoundRobin` | `schedulers.py:RoundRobinScheduler.schedule` | Lines 209–210 | `self._allocate_fifo_sn(best_flow)` (Round-robin link, FIFO order) |
| `LowestLatency` | `schedulers.py:LowestLatencyScheduler.schedule` | Lines 244–245 | `self._allocate_fifo_sn(best_flow)` (Lowest mean link, FIFO order) |
| `CongestionAware` | `schedulers.py:CongestionAwareScheduler.schedule` | Lines 274–275 | `self._allocate_fifo_sn(best_flow)` (Backlog-weighted, FIFO order) |
| `StaticPinning` | `schedulers.py:StaticPinningScheduler.schedule` | Lines 302–303 | `self._allocate_fifo_sn(f_id)` (Pinned flow queue, FIFO order) |
| `RetransmitSteering` | `schedulers.py:RetransmissionSteeringScheduler.schedule` | Lines 338–339 | `self._allocate_fifo_sn(best_flow)` (Fast-link priority, FIFO order) |
| **SASP (Batch)** | `schedulers.py:SASPScheduler.schedule` | **Lines 423–430** | Joint sorting by predicted completion: `sn = self.next_seq_num; self.next_seq_num += 1; pkt.proj_arrival = proj_arr; planned_dispatches.append(...)` |
| **SASP (Single)** | `schedulers.py:SASPScheduler.schedule` | **Lines 477–482** | Cost minimization with in-flight cross-blocking penalty: `sn = self.next_seq_num; self.next_seq_num += 1` |
| `Oracle` | `schedulers.py:OracleScheduler.schedule` | Lines 511–512 | `self._allocate_fifo_sn(best_flow)` (Non-causal lower bound) |

---

## 3. Deterministic Scenario Verification Results

The 7 deterministic scenarios implemented in `tests/test_deterministic_scenarios.py` confirm correct algorithm behavior:

1. **Identical Links (`test_scenario_1_two_identical_links`):**  
   *Result:* PASSED. Frames dispatched across parallel identical links receive sequential sequence numbers ($s_1 = 0, s_2 = 1$).
2. **Predictive Inversion (`test_scenario_2_slow_and_fast_link_predictive_inversion`):**  
   *Result:* PASSED. When a slow link ($\mu_1 = 10$ ms) and fast link ($\mu_2 = 1$ ms) are dispatched simultaneously, SASP assigns sequence number $0$ to the fast link and sequence number $1$ to the slow link. At the receiver, the fast link arrives at $t=1$ ms with $s=0$ and is released immediately to LLC with zero cross-blocking delay ($\mathcal{X} = 0$). Under FIFO, the fast link would receive $s=1$ and stall for $9$ ms waiting for $s=0$.
3. **Unequal Variances with Equal Means (`test_scenario_3_equal_mean_unequal_variance`):**  
   *Result:* PASSED. Theorem 3 threshold root $u^*$ shifts negatively ($u^* < 0$) for high-weight interactive traffic, prioritizing interactive frames under variance uncertainty.
4. **Unequal Priorities with Equal Means (`test_scenario_4_unequal_priorities_equal_means`):**  
   *Result:* PASSED. Interactive frame ($w=10$) is scheduled ahead of bulk frame ($w=1$) and allocated earlier sequence number $s=0$.
5. **In-Flight Frame Cross-Blocking Penalty (`test_scenario_5_inflight_frame_cross_blocking_penalty`):**  
   *Result:* PASSED. When single link is available and a slow frame is in-flight on another link, SASP evaluates candidate penalty via `fast_partial_expectation`.
6. **Exhausted Reorder Window (`test_scenario_6_exhausted_reorder_window`):**  
   *Result:* PASSED. When `next_seq_num >= win_start + win_size`, scheduler returns `None`, halting further dispatches until receiver window slides forward.
7. **Environment Mutation Isolation (`test_scenario_7_fresh_environment_isolation`):**  
   *Result:* PASSED. Sequential simulation runs do not leak mutable link or queue states.

---

## 4. IEEE 802.11be Protocol Feasibility Analysis

A critical question for research credibility is whether SASP's predictive sequencing can be implemented in commercial Wi-Fi 7 hardware without protocol violations.

### 4.1 Transmitter Centralization vs. Distributed L-MAC
- **802.11be Architecture:** The standard defines a centralized U-MAC entity located above independent link-specific Lower MACs (L-MACs). The U-MAC maintains per-TID sequence counters (IEEE Std 802.11be-2024 § 9.2.4.4).
- **Feasibility:** Because sequence numbering is explicitly a U-MAC responsibility, assigning sequence numbers immediately before handing MPDUs to L-MAC transmit queues is standard-compliant.
- **Hardware Requirement:** Requires an AP architecture where the U-MAC scheduler has microsecond-level visibility into L-MAC transmit queue readiness. This is supported in unified AP SoCs (e.g., Broadcom BCM4377, Qualcomm Networking Pro 1620, MediaTek Filogic 880) where all radio interfaces share a common host processor.

### 4.2 Sequence Commitment & PHY Serialization
- **Commitment Rule:** Once an MPDU header is constructed, encoded, and committed to PHY baseband transmission, its sequence number $s_i$ cannot be retroactively altered.
- **Consequence of Estimation Errors:** If Link 2 completes later than predicted (e.g., due to unexpected contention backoff), the sequence assignment cannot be dynamically rolled back. Instead, the receiver reorder buffer handles it naturally through standard Block Ack in-order release.
- **Retransmissions:** When an MPDU experiences a frame error, 802.11be mandates that retransmitted frames **retain their original sequence number**. SASP complies strictly: `simulator.py:144` reschedules lost frames with their original `packet.seq_num`.

### 4.3 Sequence Number Wraparound & Buffer Sizing
- IEEE 802.11 uses a 12-bit sequence space ($[0, 4095]$).
- The maximum negotiated Block Ack window size is $W \le 1024$ frames (standard default is $W = 64$ or $256$).
- Because $W < 2048$, modulo-4096 circular comparisons ($s_a < s_b \iff (s_b - s_a) \pmod{4096} < 2048$) prevent ambiguity. SASP enforces `next_seq_num < win_start + win_size` at all times, preventing buffer overflow.

### 4.4 Receiver Compatibility Summary
| Protocol Layer | Standard Requirement | SASP Behavior | Conformance |
| :--- | :--- | :--- | :---: |
| Receiver PHY | Standard 802.11be PPDU reception | Standard PPDU formats | **100% Compliant** |
| Receiver L-MAC | Standard Block Ack generation | Standard BA bitmap feedback | **100% Compliant** |
| Receiver U-MAC | Sliding window reordering ($W_{\text{start}}$) | Unmodified single-TID buffer | **100% Compliant** |
| Operating System | Standard IP / LLC packet delivery | Monotonic in-order delivery | **100% Compliant** |
| Transmitter U-MAC | Per-TID sequence number assignment | Predictive arrival order assignment | **Standard Allowed** |

**Conclusion:** SASP is strictly transmitter-deployable and fully interoperable with unmodified off-the-shelf IEEE 802.11be receivers.
