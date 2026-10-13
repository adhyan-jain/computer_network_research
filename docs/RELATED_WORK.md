# Related Work and Comprehensive Literature Audit

**Topic:** Head-of-Line Reordering, Block Acknowledgment Dynamics, and Multi-Link Scheduling in IEEE 802.11be  
**Date:** October 2026  

---

## 1. Multi-Link Operation (MLO) in IEEE 802.11be

The IEEE 802.11be amendment (Wi-Fi 7) introduces Multi-Link Operation (MLO) to allow affiliated Multi-Link Devices (MLDs) to coordinate communication across 2.4 GHz, 5 GHz, and 6 GHz frequency bands simultaneously.

- **Carreño et al. (2021) [arXiv:2105.10199]:**  
  Conducted early throughput investigations of MLO under delay asymmetry. They demonstrated that when one link is significantly slower or more congested than another, naive multi-link frame distribution can yield worse throughput than constraining all traffic to a single fast link (Single-Link Operation, SLO). However, their study was purely empirical and did not investigate multi-flow multiplexing or the mechanics of Block Acknowledgment reordering.
- **Levy, Rhee, and Kwon (2022) [arXiv:2201.07499]:**  
  Analyzed MLO MAC architectures, focusing on the split between the Upper MAC (U-MAC) and Lower MAC (L-MAC). They established the standard division of responsibilities: U-MAC handles queueing and sequence assignment; L-MAC handles link-specific EDCA channel access and physical transmission.
- **Al-Hraishawi et al. (2022) [arXiv:2212.12420]:**  
  Presented an analytical queueing model of MLO under finite traffic loads, modeling packet delay via an M/G/1 queueing system. However, their model treated arrivals as a single aggregate stream and assumed that packets arrive at the receiver in sequence, omitting the receiver reordering buffer dynamics entirely.
- **Sangeetha et al. (Computer Networks, 2026):**  
  Developed a multi-dimensional discrete-time Markov chain model to assess MLO performance with unsaturated queues. However, their formulation assumed that each traffic flow is mapped to an independent Traffic Identifier (TID), each with its own separate Block Ack agreement and sequence space. Consequently, they did not model cross-flow Head-of-Line blocking within a shared TID.
- **Choi, Jung, and Kim (Computer Networks, 2025):**  
  Proposed a joint design of L-MAC transmission mechanisms and U-MAC packet scheduling for Non-Simultaneous Transmit and Receive (NSTR) MLO. Their work focused on link-switching overhead, blind-zone interference, and power consumption rather than sequence-number reordering across asymmetric links.

---

## 2. Block Acknowledgment Reorder Buffering in MLO

- **Oliveira, Raposo, and Luís (IEEE Open Journal of the Communications Society, 2026):**  
  Provided the first in-depth empirical simulation of Block Acknowledgment (BA) window reordering in multi-link Wi-Fi using ns-3. They demonstrated that out-of-order frame arrivals create substantial buffer occupancy and delay spikes for UDP traffic.  
  *Differences from our work:*
  1. Oliveira et al. measured only aggregate end-to-end delay; they did not isolate intra-flow dispersion from inter-flow cross-blocking.
  2. They provided no formal mathematical model or closed-form boundary conditions for window stalls.
  3. They evaluated a heuristic retransmission steering policy (steering retransmissions to fast links, similar to WARS) but did not investigate predictive sequence number assignment at the transmitter.

---

## 3. Multipath Transport Schedulers vs. Wireless MAC Schedulers

- **Ferlin, Dreibholz, and Alay (IEEE TNSM, 2018) — BLEST:**  
  Proposed the Blocking Estimation-based MPTCP Scheduler (BLEST) to prevent receiver buffer blocking in Multipath TCP over heterogeneous paths. BLEST estimates whether sending a packet over a slow subflow will block the receive buffer by comparing estimated path Round-Trip Times (RTTs).
- **Fundamental Operational Differences between L4 (MPTCP) and L2 (Wi-Fi 7 U-MAC):**
  1. *Timescales:* MPTCP operates over tens to hundreds of milliseconds (RTT scale); Wi-Fi 7 U-MAC scheduling operates over sub-millisecond timescales ($100\,\mu\text{s} - 5\,\text{ms}$) under non-stationary EDCA contention backoff.
  2. *Feedback Granularity:* MPTCP receives cumulative TCP ACKs; Wi-Fi 7 receives per-frame Block Ack bitmaps indicating exact MPDU sequence success/loss within microseconds.
  3. *Window Limits:* MPTCP operates over large host socket buffers (megabytes); 802.11be reorder buffers are constrained by hardware bitmaps ($W \in \{64, 256, 1024\}$ frames), where exceeding the window forces buffer sliding and packet loss.

---

## 4. Patent Landscape and Freedom-to-Operate Analysis

| Assignee / Patent | Core Claimed Mechanism | Layer / Apparatus | Differentiation from Our Contribution |
| :--- | :--- | :--- | :--- |
| **MediaTek Inc.**<br>US12470496B2 (2025) | Deep Packet Inspection (DPI) at receiver to identify IP/UDP flows and maintain separate per-flow receive queues. | **Receiver-side apparatus** | MediaTek alters receiver behavior, violating standard IEEE 802.11be semantics. Our method is **purely transmitter U-MAC**, leaving the receiver completely unmodified. |
| **Qualcomm Inc.**<br>US11800588B2 (2023) | Dynamic TID-to-link mapping based on channel occupancy and Access Category. | **Transmitter MAC** | Maps distinct TIDs to distinct links (macro-scale). Does not solve the single-TID multi-flow problem where diverse applications share TID 0. |
| **Broadcom Corp.**<br>US11678385B2 (2023) | Credit-based multi-link scheduling to pace frame transmission across links based on buffer occupancy. | **Transmitter MAC** | Focuses on credit replenishment and queue backpressure. Does not perform arrival-time prediction or predictive sequence interleaving. |
| **Huawei Technologies**<br>US20240187905A1 (2024) | Primary-link fallback and retransmission steering under sudden link degradation. | **Transmitter MAC** | Reactive retransmission steering after frame loss. Does not address proactive sequence number alignment during initial transmission. |

**Freedom-to-Operate Conclusion:**  
Our proposed solution occupies an unoccupied architectural niche: a **transmitter-only Upper MAC scheduling policy** that optimizes queue selection, link mapping, and sequence-number allocation based on estimated completion delay distributions to ensure standard in-order physical arrivals at unmodified 802.11be receivers.

---

*End of Related Work Audit.*
