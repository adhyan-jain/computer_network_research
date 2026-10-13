# Comprehensive Related Work and Literature Audit

**Subject:** Cross-Flow Head-of-Line Blocking and Multi-Link Scheduling in IEEE 802.11be (Wi-Fi 7)  
**Date:** 2026-10-12  
**Target Venue Criteria:** Q1 Computer Networks / IEEE Transactions on Networking (ToN) / IEEE Transactions on Mobile Computing (TMC)  

---

## 1. Multi-Link Operation (MLO) Architecture in IEEE 802.11be

The IEEE 802.11be amendment introduces Multi-Link Operation (MLO) to enable Multi-Link Devices (MLDs) to aggregate or steer traffic across multiple frequency bands (2.4 GHz, 5 GHz, 6 GHz). The standard introduces a split-MAC architecture:
- **Upper MAC (U-MAC):** Link-agnostic sublayer responsible for interfacing with upper layers (Logical Link Control/IP), maintaining unified transmission queues per Traffic Identifier (TID), assigning 802.11 Sequence Numbers (SNs), coordinating Block Acknowledgment (BA) agreements, and managing receiver-side reordering buffers.
- **Lower MAC (L-MAC):** Link-specific sublayer executing channel access mechanisms (Enhanced Distributed Channel Access / EDCA), PHY-layer framing, carrier sensing, and per-link acknowledgments.

Under standard 802.11be specifications (IEEE Std 802.11be-2024):
1. **Per-TID Block Ack Agreement:** A single BA agreement spans all affiliated links between a non-AP MLD and an AP MLD for a given TID ($\text{TID} \in \{0, \dots, 7\}$).
2. **Unified Sequence Number Space:** All MPDUs generated under a given TID share a single contiguous 12-bit sequence number space ($s \in [0, 4095]$).
3. **In-Order Delivery Requirement:** The receiver MLD reordering buffer must deliver MSDUs to upper layers in monotonically increasing sequence number order (up to window sliding triggered by WinStart advancement or reordering timeout).

---

## 2. Deep Literature Audit

### 2.1 Characterizing Block Ack Window Reordering in Multi-Link Wi-Fi
- **Authors:** Rafael Oliveira, Duarte M. G. Raposo, and Miguel Luís
- **Publication:** *IEEE Open Journal of the Communications Society*, Vol. 7, 2026. DOI: `10.1109/OJCOMS.2026.3686295`
- **Scope & Methodology:** ns-3 simulation campaign evaluating Simultaneous Transmit and Receive (STR) MLO under burst loss, varied BA window sizes (64, 256, 1024), frame aggregation (A-MPDU), OFDMA, and TCP/UDP traffic flows.
- **Core Findings:**
  1. Asynchronous multi-link transmission causes severe out-of-order frame arrivals at the receiver reordering buffer.
  2. UDP traffic experiences severe latency spikes and jitter due to receiver buffer waiting times, while TCP experiences throughput degradation due to spurious RTOs or dupACKs.
  3. Steering retransmissions to cleaner links accelerates BA window repair compared to Single-Link Operation (SLO).
- **Critical Limitations & Unanswered Questions:**
  - **No Mathematical Model:** Provides no analytical, stochastic, or closed-form model for BA window stall duration or reordering latency.
  - **No Cross-Flow Distinction:** Blends all traffic in a TID into aggregate packet streams without distinguishing self-blocking (intra-flow) from cross-flow blocking (inter-flow).
  - **No Scheduling Algorithm:** Merely lists reordering-aware scheduling and retransmission steering as speculative future work; does not formulate or implement any sequence-aware or cross-flow-mitigating scheduling policy.

---

### 2.2 Analytical Delay Models of IEEE 802.11be MLO
- **Carreño et al. (2021), arXiv:2105.10199:** *IEEE 802.11be Multi-Link Operation: When the Best Could Be to Use Only a Single Interface*. Demonstrated that uncoordinated traffic splitting across multiple links exposes flows to cross-link interference and contention jitter, causing multi-link to underperform a single clean link under asymmetric loads. Focuses purely on link-selection heuristics (congestion-aware vs. static); does not model BA reordering buffers or sequence numbers.
- **Levy et al. (2022), arXiv:2201.07499:** *Multi-link Operation in IEEE 802.11be WLANs*. Architectural overview of STR and Non-STR (NSTR) MLO. No formal stochastic reordering model.
- **Al-Hraishawi et al. (2022), arXiv:2212.12420:** *Delay Analysis of IEEE 802.11be Multi-link Operation under Finite Load*. Formulates a queueing-theoretic model for MLO delay distributions under unsaturated finite loads. Analyzes MAC service time across links, but assumes ideal in-order receiver handoff, omitting the Block Ack reorder buffer and out-of-order completion penalties.
- **Sangeetha et al. (2026), Computer Networks, DOI: `10.1016/j.comnet.2026.112187`:** *IEEE 802.11be WLANs: Performance assessment of multi-link operation with unsaturated queues*. Investigates queue occupancy, channel access delays, and throughput under unsaturated conditions. Does not address sequence-number constraints or receiver reorder stalls.
- **Choi et al. (2025), Computer Networks, DOI: `10.1016/j.comnet.2025.111895`:** *Joint design of L-MAC transmission mechanism and U-MAC packet scheduling for NSTR MLO operations in Wi-Fi 7*. Focuses on in-device coexistence (IDC) interference in NSTR devices, designing alternating (ATX) and synchronous (SATX) transmission. Addresses transmission synchronization to prevent blind spots, not receiver sequence-space cross-flow HOL blocking.

---

### 2.3 Multipath Transport and Cross-Layer Reordering Prior Art
- **MPTCP / Multipath QUIC Packet Schedulers (BLEST, D-STREAM, Peekaboo, ECF):**
  - MPTCP schedulers (e.g., BaFi, LowRTT, BLEST) operate at Layer 4 across distinct IP connections with separate TCP sequence numbers and separate socket receive buffers.
  - In contrast, Wi-Fi 7 MLO operates at Layer 2 within a single MAC address pair and a rigid hardware/firmware sliding window ($W \le 256$ or $1024$), where frame reordering stalls the entire MAC client entity for that TID.
  - Schedulers designed for Layer 4 cannot control 802.11 Sequence Number assignment or Lower MAC contention timing, nor do they account for the tight hardware constraints of 802.11be BA bitmap updates.

---

## 3. The Unresolved Research Gap

Prior art has identified that Wi-Fi 7 MLO suffers from reordering latency (Oliveira et al., 2026) and that multi-link allocation requires congestion awareness (Carreño et al., 2021). However, the literature reveals a major foundational gap:

1. **Absence of a Formal Analytical Model:** No existing work models the stochastic coupling between heterogeneous link completion times and receiver Block Ack reordering delay under a shared sequence space.
2. **Absence of Cross-Flow Blocking Formalization:** In IEEE 802.11, multiple distinct application flows (e.g., interactive gaming and video streaming) frequently share TID 0 (Best Effort) or TID 5 (Video). When frames from different flows are dispatched across asymmetric links, a fast frame from Flow $B$ is stalled at the receiver waiting for an earlier-sequenced frame from Flow $A$ that was sent over a slower or lossy link. The literature has neither mathematically formulated nor empirically isolated this **Cross-Flow Head-of-Line (CF-HOL) blocking** from intra-flow self-blocking.
3. **Absence of Sequence-Aware Sender Policies:** Conventional U-MAC schedulers assign sequence numbers sequentially at packet arrival or enqueue time. Because standard receivers cannot be modified without violating standard 802.11 compliance, the transmitter must proactively coordinate packet selection, link mapping, and sequence number assignment to prevent reorder stalls. No existing work provides a provably optimal, sequence-aware scheduling policy for Wi-Fi 7 MLO.
