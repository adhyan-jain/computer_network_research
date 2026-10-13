# Independent Novelty Verdict (Phase 3 Audit)

**Date:** October 13, 2026  
**Auditor Role:** Independent Reviewer & Reproducibility Auditor  
**Topic:** Cross-Flow Head-of-Line Blocking in Wi-Fi 7 Multi-Link Operation: Analytical Modeling and Sequence-Aware Scheduling  

---

## 1. Executive Summary

This independent novelty audit re-evaluates the research claims against recent IEEE 802.11be literature (including Oliveira et al., IEEE OJCOMS 2026) and the wireless patent landscape (including MediaTek US12470496B2).

**OVERALL NOVELTY VERDICT: CONFIRMED WITH NARROWED CLAIMS (CONDITIONAL GO).**

The core contribution occupies an authentic, unoccupied architectural niche: a **transmitter-only Upper MAC predictive sequencing policy** operating under unmodified IEEE 802.11be receiver semantics. However, several previously inflated claims must be permanently removed or qualified.

---

## 2. Three Mandatory Questions Answered

### Question 1: Is the underlying problem known?
**YES.**
- The phenomenon that Multi-Link Operation induces packet reordering and Block Ack window stalls is recognized in empirical literature:
  - Carreño et al. (2021) demonstrated throughput degradation under asymmetric links.
  - Oliveira, Raposo, and Luís (IEEE OJCOMS 2026) conducted an in-depth ns-3 simulation showing substantial BA window reordering stalls for UDP traffic.
  - MediaTek patent US12470496B2 (granted Nov 2025) explicitly addresses HOL blocking across multiple traffic types within a shared BA window.
- **What is NOT known / genuinely novel about our problem formulation:**
  Prior works treated reordering as an aggregate, monolithic delay phenomenon. This project is the first to isolate **cross-flow interference between distinct flows multiplexed onto a single Best-Effort TID** and provide a formal trace accounting framework ($\Delta_i = \mathcal{S}_i + \mathcal{X}_i$) separating intra-flow self-blocking from inter-flow cross-blocking.

### Question 2: Is the proposed mechanism novel over existing academic and technical work?
**YES.**
- **Versus Oliveira et al. (2026):** Oliveira et al. provided no mathematical model, no closed-form stall conditions, and no sequence scheduling algorithm (only speculating on reactive retransmission steering in future work). SASP is a proactive predictive sequencing scheduler.
- **Versus MediaTek (US12470496B2 / US20240244007A1):** MediaTek claims a **receiving apparatus** that performs Deep Packet Inspection (DPI) to identify traffic types and split receive queues. MediaTek requires custom receiver firmware/hardware. SASP operates **strictly at the transmitter U-MAC**, leaving commercial client stations 100% standard-compliant and unmodified.
- **Versus Carreño et al. (2021) and Choi et al. (2025):** Existing MLO schedulers make macro-level link choices (e.g. congestion-aware link selection) but assign sequence numbers strictly in FIFO enqueue order. SASP decouples link dispatch from sequence numbering, allocating sequence numbers based on predicted physical arrival order.
- **Versus MPTCP Schedulers (BLEST, LowRTT):** MPTCP operates at Layer 4 across independent IP socket buffers on multi-RTT timescales ($10–100$ ms). Wi-Fi 7 U-MAC operates at Layer 2 across hardware-constrained Block Ack bitmaps ($W \le 256$) on sub-millisecond timescales with EDCA contention backoff.

### Question 3: Has the mechanism been validated well enough to establish a meaningful contribution?
**CONDITIONALLY.**
- **Theoretical Validation:** Theorems 1–3 are fully proved, verified algebraically, and backed by passing unit tests (39/39 passing).
- **Empirical Validation:** 7 experiment campaigns across 30 seeds show consistent cross-blocking reductions (16.1% to 36.2%) and window stall mitigation (96.8% cross-blocking reduction at stall).
- **Validation Limitations:** All simulations are executed in a custom Python discrete-event simulator. There is no physical Wi-Fi 7 hardware testbed or ns-3 cross-validation. This limitation must be explicitly disclosed in the manuscript.

---

## 3. Disallowed and Inflated Claims (Permanently Stricken)

1. **NO "Zero Patent Risk" Claims:** A prior-art literature review is an engineering analysis, not a legal opinion. Never claim guaranteed non-infringement or absolute freedom-to-operate.
2. **NO "Universal Causal Floor" for General Asymmetric Links:** The old Theorem 4 inequality $\ge \min(w) \sigma_Z \phi(u)$ is mathematically false for $u > 0$. The repaired theorem holds strictly for symmetric links ($u = 0$).
3. **NO "Almost Surely" Window Collapse:** Crossing $\lambda^* = W/\delta$ represents a mean-drift boundary, not an almost-sure event for finite Poisson arrivals.
4. **NO Fabricated Numbers:** All metrics must match the raw CSVs exactly (e.g. 16.1% asymmetry reduction, 20.5% ablation reduction, not legacy 64.2% or 68.4%).
5. **NO Claim of Global Multi-Frame Optimality:** Theorem 3 proves pairwise optimality. Multi-frame scheduling is an index-based heuristic.

---

## 4. Final Verdict

The research artifact possesses **solid, publishable novelty** when framed honestly:
> *"An analytical modeling framework and transmitter-side predictive sequence allocation algorithm that mitigates cross-flow head-of-line blocking in IEEE 802.11be Multi-Link Operation without requiring receiver modifications."*

Suitable for submission to *Computer Networks* (Elsevier) or *IEEE OJCOMS*.
