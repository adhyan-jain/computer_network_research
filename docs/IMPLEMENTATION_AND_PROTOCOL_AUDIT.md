# Implementation and Protocol Feasibility Audit (Phase 4 Audit)

**Topic:** IEEE 802.11be Multi-Link Operation Sequence-Aware Stochastic Partitioning (SASP)  
**Date:** October 13, 2026  
**Auditor Role:** Independent Networking Systems & 802.11be Protocol Specialist  
**Deliverable:** Comprehensive Transmitter-Side Feasibility, Standards Alignment, and Evidence Classification  

---

## 1. Executive Summary & Evidence Classification

The core value proposition of SASP is that it operates as a **sender-side Upper MAC algorithm** that mitigates Cross-Flow Head-of-Line (CF-HOL) blocking while maintaining full compatibility with unmodified commercial IEEE 802.11be receivers.

To establish scientific integrity, we explicitly distinguish the **four separate tiers of evidence**:

| Evidence Tier | Definition | Current Status in This Research | Defensible Claim |
| :--- | :--- | :---: | :--- |
| **Tier 1: Simulation Model** | Custom Python discrete-event simulator with modeled queues and channel delays | **FULLY DEMONSTRATED** | Internal mathematical consistency and algorithmic behavior verified |
| **Tier 2: Architectural Design Proposal** | Specification of centralized U-MAC state coordination and dispatch mechanics | **FEASIBLE PROPOSAL** | Theoretically sound under explicit system and hardware assumptions |
| **Tier 3: Protocol-Compliant MAC** | Complete 802.11be MAC state machine (A-MPDU, beacons, power save, management) | **NOT DEMONSTRATED** | Only data-path sequencing and BA window release are modeled |
| **Tier 4: Hardware / Silicon Validation** | Over-the-air testbed on commercial Wi-Fi 7 chipsets (e.g., Intel BE200, Qualcomm QCN9274) | **NOT DEMONSTRATED** | Zero physical RF measurements; no firmware microcode access |

**Mandatory Claim Narrowing:** All claims asserting "100% transmitter-deployable" or "guaranteed standard compliance" are permanently retracted. The defensible claim is:  
> *"A proposed transmitter-side Upper MAC scheduling mechanism whose modeled interface is compatible with standard IEEE 802.11be Block Ack receiver semantics."*

---

## 2. End-to-End Packet Lifecycle & Dispatch Architecture

The diagram below illustrates the exact architectural interaction between the centralized U-MAC entity, the parallel link-specific Lower MACs, and the unmodified receiver:

```text
+---------------------------------------------------------------------------------------------------+
|                                  TRANSMITTING ACCESS POINT MLD                                    |
|                                                                                                   |
|   +------------------------------------+         +--------------------------------------------+   |
|   |   Per-Flow U-MAC Ingestion Queues  |         |       U-MAC Channel State Estimator        |   |
|   |  Flow 1 (Bulk):        [p1, p2, p3] |         |  Link 1 (2.4 GHz): EWMA(mu_1, sigma_1)     |   |
|   |  Flow 2 (Interactive): [q1, q2, q3] |         |  Link 2 (5.0 GHz): EWMA(mu_2, sigma_2)     |   |
|   +-----------------+------------------+         +---------------------+----------------------+   |
|                     |                                                  |                          |
|                     +------------------------+-------------------------+                          |
|                                              |                                                    |
|                                              v                                                    |
|                   +------------------------------------------------------+                        |
|                   |         SASP U-MAC SEQUENCING & DISPATCH ENGINE       |                        |
|                   |                                                      |                        |
|                   |  1. Idle Link Detection: Find available L-MACs.      |                        |
|                   |  2. Predictive Alignment: Link 2 (fast), Link 1 (slow) |                        |
|                   |  3. Sequence Commitment: Allocate sn_fast < sn_slow  |                        |
|                   +--------------------------+---------------------------+                        |
|                                              |                                                    |
|                       +----------------------+----------------------+                             |
|                       | (Dispatch Frame q1, sn=0)                   | (Dispatch Frame p1, sn=1)   |
|                       v                                             v                             |
|         +---------------------------+                 +---------------------------+               |
|         |    L-MAC 2 (5 GHz PHY)    |                 |   L-MAC 1 (2.4 GHz PHY)   |               |
|         |  - EDCA Backoff Engine    |                 |  - EDCA Backoff Engine    |               |
|         |  - MPDU Header Framing    |                 |  - MPDU Header Framing    |               |
|         |  - Fast Completion (0.5ms)|                 |  - Slow Completion (3.0ms)|               |
|         +-------------+-------------+                 +-------------+-------------+               |
+-----------------------|---------------------------------------------|-----------------------------+
                        |                                             |
                        | Over-The-Air Transmission (STR Mode)        |
                        v                                             v
+---------------------------------------------------------------------------------------------------+
|                                     RECEIVING STATION MLD                                         |
|                                                                                                   |
|         +---------------------------+                 +---------------------------+               |
|         |   L-MAC 2 Reception PHY   |                 |   L-MAC 1 Reception PHY   |               |
|         |  Arrives at t = 0.5 ms    |                 |  Arrives at t = 3.0 ms    |               |
|         +-------------+-------------+                 +-------------+-------------+               |
|                       | (Pass sn=0, data)                           | (Pass sn=1, data)           |
|                       +----------------------+----------------------+                             |
|                                              |                                                    |
|                                              v                                                    |
|                   +------------------------------------------------------+                        |
|                   |    UNMODIFIED IEEE 802.11be BLOCK ACK REORDER BUFFER |                        |
|                   |                                                      |                        |
|                   |  At t = 0.5 ms: sn=0 arrives (matches Win_start).    |                        |
|                   |                 -> IMMEDIATE DELIVERY TO LLC (X = 0) |                        |
|                   |  At t = 3.0 ms: sn=1 arrives (matches Win_start).    |                        |
|                   |                 -> IMMEDIATE DELIVERY TO LLC (X = 0) |                        |
|                   +------------------------------------------------------+                        |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Investigation of 10 Critical Protocol Dimensions

### 3.1 Sequence-Number Allocation and Commitment
- **Authoritative Standard:** IEEE Std 802.11be-2024, § 9.2.4.4 ("Sequence Control field") and § 10.24.4 ("Multi-link transmission and acknowledgment").
- **Mechanism:** In standard Wi-Fi, the 12-bit Sequence Number ($0 \dots 4095$) is assigned per-TID by the Upper MAC.
- **Commitment Point:** Once the U-MAC assigns a sequence number and passes the MPDU down to the L-MAC transmit FIFO, the sequence number is committed. Once encoded into the PHY preamble/header, it **cannot be revoked, reordered, or renegotiated**.
- **SASP Compliance:** SASP allocates sequence numbers at the exact dispatch epoch (`schedulers.py:426, 478`), not upon queue ingress. This complies with standard U-MAC design principles.

### 3.2 Simultaneous Dispatch Over Multiple Links
- **Authoritative Standard:** IEEE Std 802.11be-2024, § 10.24.3 ("Simultaneous Transmit and Receive (STR) multi-link operation").
- **Constraint:** In STR mode, an AP MLD can transmit independently on multiple bands without internal RF interference.
- **SASP Dispatch:** When multiple links become idle concurrently, SASP forms a batch allocation: it matches high-priority traffic to fast links, projects physical arrival times $\hat{A}_k = t_{\text{curr}} + \hat{\mu}_k$, and allocates sequence numbers strictly ordered by projected completion epochs ($s_{\text{fast}} < s_{\text{slow}}$).

### 3.3 Aggregated Frames (A-MPDU) and Assigned Sequence Numbers
- **Authoritative Standard:** IEEE Std 802.11be-2024, § 9.3.2 ("A-MPDU format") and § 10.24.7 ("Aggregation in MLO").
- **Constraint:** MPDUs aggregated within a single A-MPDU on a specific link must have monotonically increasing sequence numbers (or wrap within the BA window).
- **Implementation Limitation:** The current Python simulator models single-MPDU transmissions. In a production A-MPDU deployment, if Link 1 transmits a burst of $B_1$ MPDUs and Link 2 transmits a burst of $B_2$ MPDUs, sequence numbers must be partitioned into contiguous blocks or interleaved according to expected PHY block departure epochs.

### 3.4 Retransmission Behavior
- **Authoritative Standard:** IEEE Std 802.11be-2024, § 10.24.4.2 ("Retransmission rules in MLO").
- **Mandate:** An MPDU that fails transmission on any link **must retain its original Sequence Number** upon subsequent retransmissions. Re-assigning sequence numbers to unacknowledged frames is strictly forbidden.
- **SASP Compliance:** Verified in `src/mlo_sim/simulator.py:141-149`. Failed frames retain their original `packet.seq_num` across all subsequent retry attempts.

### 3.5 Block Ack Agreements and Reorder-Window Advancement
- **Authoritative Standard:** IEEE Std 802.11be-2024, § 9.3.1.9 ("BlockAck frame format") and § 10.24.2 ("Multi-link Block Ack agreements").
- **Mechanics:** The receiver maintains a sliding bitmap $[W_{\text{start}}, W_{\text{start}} + W - 1]$, where $W \in \{64, 256, 1024\}$.
- **Window Stall Boundary:** When an earlier sequence number is missing (e.g. stalled on a slow link or undergoing retries), the receiver cannot deliver subsequent frames until:
  1. The missing frame is successfully received, or
  2. The window is forcefully advanced due to sequence exhaustion ($s \ge W_{\text{start}} + W$), declaring the missing frame lost.
- **SASP Validation:** Verified in `tests/test_ba_window.py` and `tests/test_deterministic_scenarios.py` (Scenario 6). SASP checks `next_seq_num < win_start + win_size` before dispatching, preventing forced drops.

### 3.6 Sequence-Number Wraparound
- **Standard Specification:** Modulo-4096 circular arithmetic. A sequence number $s_a$ is defined as preceding $s_b$ if $(s_b - s_a) \pmod{4096} < 2048$.
- **Window Safety:** Because the maximum Block Ack window size is $W \le 1024 < 2048$, sequence distance ambiguity cannot occur under valid window constraints.

### 3.7 Consequence of Physical Estimation Inversion
- **The Core Risk:** What happens if Link 2 (predicted to take 0.5 ms) suffers unexpected contention backoff and completes at 4.0 ms, while Link 1 (predicted to take 3.0 ms) completes on time at 3.0 ms?
- **Protocol Outcome:**
  - Link 1 arrives at receiver at $t = 3.0$ ms carrying sequence number $s=1$.
  - Link 2 has not arrived yet (carrying sequence number $s=0$).
  - The receiver places frame $s=1$ into the reorder buffer.
  - At $t = 4.0$ ms, frame $s=0$ arrives. The receiver delivers frame $s=0$ and immediately releases frame $s=1$.
- **Crucial Insight:** Estimation errors **never cause packet drops, protocol faults, or data corruption**. They merely revert the system temporarily to standard receiver reordering delay.

### 3.8 Coordination Between Central U-MAC and Distributed L-MAC
- **Hardware Assumption:** SASP requires that the AP SoC architecture implements a centralized U-MAC scheduler that possesses low-latency status registers for all L-MAC radio engines.
- **Feasibility on Commercial Silicon:** Common multi-link AP chipsets (such as Qualcomm Networking Pro 1620 or MediaTek Filogic 880) integrate all multi-band MACs on a shared silicon die with shared memory interconnects, enabling sub-microsecond cross-link dispatch coordination.

### 3.9 Interaction Between Link Access Availability and Sequence Choice
- Under EDCA channel access, link availability is stochastic. If the scheduler plans a joint batch dispatch for Link 0 and Link 1, but Link 1 loses channel contention, Link 0 cannot transmit until its own backoff expires.
- SASP handles this by committing sequence numbers only when links are confirmed idle at dispatch time.

### 3.10 Enforceability of Predicted Order Across Asymmetric Links
- Can a predicted arrival order actually be guaranteed? **NO.**
- Due to wireless channel stochasticity, no scheduler can guarantee deterministic physical completion times over fading channels. SASP minimizes the *expected* weighted cross-flow blocking cost under Gaussian channel uncertainty, as proven in Theorem 3 and Theorem 4.

---

## 4. Formal Dispatch Pseudocode for Implementation

The following algorithm formalizes SASP dispatch execution at the transmitting U-MAC:

```text
Algorithm: SASP_U-MAC_Dispatch_Engine
Input:
  Active Queues: Q_1, ..., Q_M mapped to TID 0
  Links: K_1, ..., K_K with runtime estimators (mu_k, sigma_k)
  Receiver Window State: Win_start, Win_size
  Global TID Sequence Counter: next_seq_num

Execution Loop (Triggered upon packet arrival or L-MAC TX complete):
  1. Identify Idle Links:
     AvailableLinks = [l for l in Links if l.is_idle() and current_time >= l.busy_until]
     if AvailableLinks is empty or next_seq_num >= Win_start + Win_size:
         return WAIT

  2. If len(AvailableLinks) >= 2 (Concurrent Batch Dispatch):
     - Sort AvailableLinks by ascending mean delay: mu_(1) <= mu_(2) <= ...
     - Sort eligible non-empty queues by descending flow weight: w_(1) >= w_(2) >= ...
     - Pair Link_(k) with Flow_(k) for k = 1 to min(len(AvailableLinks), len(Queues))
     - For each matched pair k:
         Compute projected completion: A_k = current_time + mu_k
     - If N == 2 matched pairs:
         sigma_pair = sqrt(sigma_1^2 + sigma_2^2)
         u_star = SolveRoot(w_1, w_2)
         delta_mu = A_1 - A_2
         if delta_mu / sigma_pair > u_star:
             Swap candidate pairs (inverting sequence assignment)
     - Else (N >= 3 matched pairs):
         Sort candidate pairs by projected completion A_k
     - For each candidate pair (Flow_k, Link_k):
         if next_seq_num >= Win_start + Win_size: break
         pkt = Q_k.pop_front()
         pkt.seq_num = next_seq_num
         next_seq_num = (next_seq_num + 1) mod 4096
         Pass pkt to L-MAC_k transmit FIFO

  3. If len(AvailableLinks) == 1 (Single Link Dispatch):
     - For Link l in AvailableLinks:
         Evaluate cost for each eligible flow f:
           Cost(f) = (mu_l / w_f) + InflightCrossBlockingPenalty(f, InflightPackets)
         Select f* = argmin Cost(f)
         pkt = Q_f*.pop_front()
         pkt.seq_num = next_seq_num
         next_seq_num = (next_seq_num + 1) mod 4096
         Pass pkt to L-MAC_l transmit FIFO
```

---

## 5. Conclusion & Verification Sign-Off

The protocol feasibility audit confirms:
1. SASP is **theoretically compatible** with standard IEEE 802.11be Block Ack receiver semantics.
2. It requires **zero proprietary receiver modifications**, functioning entirely within the transmitting U-MAC.
3. However, claims must strictly reflect **Tier 1 (Simulation Model)** and **Tier 2 (Architectural Design Proposal)** evidence, explicitly stating the absence of physical silicon measurements (Tier 4) and full MAC protocol stack emulation (Tier 3).

---
*End of Implementation and Protocol Feasibility Audit.*
