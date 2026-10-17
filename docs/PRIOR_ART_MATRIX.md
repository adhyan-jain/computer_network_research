# Comprehensive Prior Art Comparison Matrix (Phase 5 Audit)

*Disclaimer: This matrix provides an academic literature audit and technical differentiation analysis for scientific publication positioning; it does NOT constitute legal advice, patent clearance, or an opinion on freedom to operate.*

## 1. Prior Art Comparison Table

| Prior Work / Reference | Main Problem Addressed | Algorithmic Mechanism | Analytical / Theoretical Result | Experimental Evidence Level | Difference from SASP | Remaining Overlap / Unresolved Boundaries |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Oliveira, Raposo, & Luís (IEEE OJCOMS 2026)**<br>DOI: 10.1109/OJCOMS.2026.* | Empirical characterization of BA window reorder stalls in Wi-Fi 7 MLO | Evaluates default ns-3 STR MLO; discusses heuristic retransmission steering | None (purely empirical observations of buffer occupancy) | ns-3 discrete-event simulations of UDP workloads | SASP provides formal delay decomposition ($\Delta = \mathcal{S} + \mathcal{X}$), exact stall probability, and sender-side predictive sequencing | Both address BA reordering caused by multi-link delay asymmetry; Oliveira uses standard ns-3 while SASP uses custom Python simulator |
| **ATLAS (Adaptive Traffic-to-Link Allocation, 2026)** | Traffic-to-link mapping and load balancing across multi-link channels | Dynamic flow-to-link assignment based on measured channel congestion and SNR | Heuristic throughput optimization or Markov queueing model | ns-3 or analytical numerical evaluations | ATLAS chooses *which link* carries a packet; it assigns sequence numbers in standard FIFO arrival order | Both perform multi-link traffic dispatch; ATLAS does not model or alter sequence-number allocation |
| **Choi, Jung, & Kim (Computer Networks 2025)**<br>DOI: 10.1016/j.comnet.2025.* | In-device coexistence (IDC) interference and blind-zone overhead in NSTR MLO | Alternating (ATX) and Synchronous (SATX) transmission scheduling | Mixed-Integer Linear Programming (MILP) for power and channel switching | MATLAB numerical evaluations and trace-driven simulations | Choi et al. optimize half-duplex link switching under NSTR; SASP addresses cross-flow sequence reordering under STR | Both coordinate U-MAC and L-MAC layers; Choi focuses on energy and blinding, SASP on sequence numbers |
| **MediaTek Inc.**<br>US12470496B2 / US20240163947A1<br>(Granted Nov 2025) | Head-of-line blocking among diverse traffic flows within a shared BA window | **Receiver-side** apparatus performing Deep Packet Inspection (DPI) to demultiplex flows into distinct reorder buffers | None (patent specification) | Proprietary internal simulations / hardware specifications | MediaTek requires **custom receiver silicon** and non-standard MAC firmware; SASP is **strictly transmitter U-MAC**, interoperating with standard receivers | Both target cross-flow interference within a shared TID; MediaTek splits receive queues, SASP sequences transmit dispatches |
| **Qualcomm Inc.**<br>US11800588B2<br>(Granted Oct 2023) | Multi-link TID-to-link mapping and congestion distribution | Dynamic assignment of distinct TIDs to subsets of radio links | None (patent specification) | Proprietary simulation | Operates at the TID level (macro-scale); does not address multiple application flows sharing TID 0 | Both assign traffic across MLO links; Qualcomm segregates by TID, SASP operates within a TID |
| **Broadcom Corp.**<br>US11678385B2<br>(Granted Jun 2023) | Flow control and buffer overflow in multi-link wireless architectures | Credit-based transmission pacing to avoid overwhelming L-MAC buffers | None (patent specification) | Proprietary simulation | Regulates transmission rate and buffer credits; does not predict arrival order or interleave sequence numbers | Both manage transmitter U-MAC buffers; Broadcom focuses on buffer backpressure, SASP on sequence ordering |
| **MPTCP Schedulers**<br>(BLEST, LowRTT, Peekaboo)<br>Ferlin et al. (IEEE TNSM 2018) | Receive buffer blocking across heterogeneous multipath IP networks | Estimates receiver buffer blocking based on path RTTs before scheduling on slow subflow | Heuristic RTT threshold comparison / regret bounds | Linux kernel testbed & Mininet network emulations | Operates at Layer 4 across continuous byte streams on 10–100 ms RTT scales; SASP operates at Layer 2 across discrete MPDUs on sub-ms EDCA scales | Both share the conceptual idea of predictive delay mitigation; operational layers, state machines, and timescales are completely disjoint |
| **Our Contribution**<br>**(SASP / MLO-CFHOL)** | Cross-Flow Head-of-Line (CF-HOL) blocking within shared TID 0 in 802.11be | Transmitter U-MAC predictive sequence-number allocation and joint candidate dispatch | Exact trace decomposition ($\Delta = \mathcal{S} + \mathcal{X}$), Poisson stall probability, pairwise Gaussian threshold rule $u^*$ | Custom discrete-event simulation across 30 seeds; 39 unit/adversarial tests | First formal analytical model separating intra/cross-flow delay; first compliant transmitter-only predictive sequencing policy | Gain over Mean-Only sequencing is small and narrow; empirical validation is limited to custom Python simulator |

---

## 2. Six Mandatory Novelty and Overlap Questions Answered

### 1. Is the CF-HOL problem itself novel?
**NO, the general phenomenon of multi-link reordering is known; YES, the formal cross-flow decomposition is novel.**
The broader problem that multi-link delay asymmetry induces Block Ack reordering stalls was empirically demonstrated by Carreño et al. (2021) and Oliveira et al. (2026), and targeted in MediaTek's patent (US12470496B2). However, earlier academic literature treated reordering as an aggregate, single-stream delay spike. Formally isolating **cross-flow interference between distinct application flows multiplexed onto a shared TID** and establishing an exact orthogonal trace accounting decomposition ($\Delta_i = \mathcal{S}_i + \mathcal{X}_i$) is an authentic analytical contribution.

### 2. Is the specific pairwise decision rule novel?
**YES.**
The transcendental threshold decision rule $s_a < s_b \iff (\mu_a - \mu_b)/\sigma_Z \le u^*(w_a, w_b)$ derived from Gaussian completion-time uncertainty and weighted partial expectations is novel. No prior wireless MAC scheduler has derived or applied this threshold root equation to 802.11 sequence assignment.

### 3. Is the multi-frame scheduling policy novel?
**CONDITIONALLY (as a heuristic).**
For $N \ge 3$ candidate frames, universal transitivity fails (as proven by our discovered Condorcet cycle $A \prec B \prec C \prec A$). Consequently, pairwise sorting cannot form a globally optimal policy. The multi-frame policy implemented in SASP is an index heuristic (sorting by projected mean arrivals with small-batch pairwise adjustment). This heuristic is practically useful for $N \le 3$ links, but it cannot be claimed as a globally optimal multi-frame algorithm.

### 4. Is the resulting combined mechanism meaningfully different from the closest published work?
**YES.**
- Versus **Oliveira et al. (2026):** Oliveira et al. only measured default FIFO reordering in ns-3; they proposed no mathematical model, no stall probability formula, and no sequencing scheduler.
- Versus **MediaTek (US12470496B2):** MediaTek requires Deep Packet Inspection (DPI) and non-standard per-flow receive queues at the station. SASP resides entirely at the transmitter U-MAC, requiring zero receiver modifications and functioning with standard commercial 802.11be client firmware.
- Versus **ATLAS & Choi et al. (2025/2026):** These schedulers assign packets to links but assign sequence numbers strictly in FIFO arrival order. SASP actively decouples link assignment from sequence numbering.

### 5. Does the evidence establish a meaningful advantage?
**YES over FIFO (20%--78%); NO/UNPROVEN over Mean-Only Sequencing.**
- SASP provides a massive, reproducible 20% to 78% reduction in cross-flow blocking compared to standard FIFO MLO under asymmetric link conditions ($\Delta\mu \ge 0.5$ ms).
- However, the statistical audit (Phase 3) proves that the variance-aware root $u^*$ provides **no statistically defensible advantage over simple Mean-Only Sequencing** once multiple-testing corrections are applied ($p > 0.05$ under FDR and Bonferroni). The primary engine of the performance gain is **predictive arrival ordering based on means**, not the variance threshold.

### 6. Which claims remain uncertain because of incomplete prior-art access?
1. **Unpublished Vendor Silicon Heuristics:** Commercial AP chipsets (Broadcom, Qualcomm, MediaTek) contain proprietary firmware microcode that may implement internal sequence-pacing or dynamic reorder-window adjustments that are not publicly documented in IEEE standards or academic literature.
2. **Pending Patent Applications:** Patent applications published after mid-2025 may contain transmitter-side sequence management claims that are not yet indexed in publicly accessible databases.
3. **Formal Freedom to Operate:** This analysis confirms academic technical differentiation; it does not clear patent infringement risk against broadly drafted multi-link dispatch patents.

---
*End of Comprehensive Prior Art Comparison Matrix.*
