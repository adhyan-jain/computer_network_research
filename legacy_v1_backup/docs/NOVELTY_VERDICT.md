# Adversarial Novelty Verdict

**Date:** 2026-10-12  
**Evaluation Role:** Hostile / Adversarial Reviewer  
**Topic Under Review:** Cross-Flow Head-of-Line Blocking in Wi-Fi 7 Multi-Link Operation: Analytical Modeling and Sequence-Aware Scheduling  

---

## 1. Audit Against the 10 Explicit Kill Criteria

### Criterion 1: Is the mathematical result merely a standard order-statistics or queueing observation?
- **Finding: PASS.**  
  A basic order-statistic calculation (e.g., expected maximum of $K$ i.i.d. random variables) would fail immediately. However, our problem involves:
  1. A discrete sliding Block Ack window coupled to continuous stochastic service distributions across parallel heterogeneous links.
  2. An exact orthogonal decomposition of receiver reordering delay into intra-flow self-blocking ($\mathcal{S}$) and inter-flow cross-blocking ($\mathcal{X}$).
  3. A discrete permutation / sequence-number assignment problem under intra-flow monotonic constraints.
  4. Closed-form threshold derivation connecting link delay mean, variance, and flow priority weights.  
  This is a domain-specific, coupled discrete-continuous scheduling optimization problem not subsumed by classic order statistics.

### Criterion 2: Does a previous paper or patent already describe the central scheduling mechanism?
- **Finding: PASS.**  
  - Oliveira et al. (IEEE OJCOMS 2026) performed ns-3 simulations measuring aggregate reordering; they neither modeled cross-flow blocking nor proposed any scheduling/sequencing algorithm.
  - MediaTek (US12470496B2) patented a *receiver-side* mechanism that inspects IP headers to split receive buffers.
  - Carreño et al. (2021) and Choi et al. (2025) proposed macroscopic link selection (congestion-aware or alternating transmissions for NSTR), but maintained FIFO sequence assignment at enqueue time.
  - No existing paper or patent proposes transmitter-side predictive sequence-space coordination and stochastic dominance sequencing to mitigate cross-flow HOL blocking.

### Criterion 3: Does the algorithm reproduce the 2026 paper's reordering-aware scheduling or retransmission-repair recommendations with minor changes?
- **Finding: PASS.**  
  Oliveira et al. speculated in their conclusion that retransmissions could be steered to cleaner links. Our algorithm (SASP) is not a retransmission heuristic; it is a foundational U-MAC predictive sequencing and link-allocation policy with provable optimality properties for new transmissions, retransmissions, and flow priorities.

### Criterion 4: Does the purported cross-flow effect vanish under the actual sequence-number and TID semantics of the standard?
- **Finding: PASS.**  
  Crucially, the cross-flow effect is an inevitable structural consequence of IEEE 802.11be. Because 802.11 defines only 8 TIDs (mapped to 4 Access Categories: Voice, Video, Best Effort, Background), multiple distinct IP flows (e.g., interactive WebRTC vs. bulk file download) inevitably share TID 0 or TID 5. In IEEE 802.11be, the BA agreement and 12-bit sequence number space are strictly per-TID. Therefore, any uncoordinated multi-link dispatching creates cross-flow HOL stalls at standard receivers.

### Criterion 5: Does the claimed benefit rely on changing receiver-side ordering semantics?
- **Finding: PASS.**  
  The proposed mechanism operates exclusively at the transmitter's U-MAC. The receiver runs standard, unmodified IEEE 802.11be MAC logic.

### Criterion 6: Does the claimed improvement follow trivially from an unfair baseline or access to information the baselines do not possess?
- **Finding: PASS.**  
  The proposed scheduler uses only runtime channel estimates (moving average and variance of packet service times, plus standard Block Ack feedback bitmaps)—the exact same information accessible to standard rate-adaptation and congestion-aware baselines. Baselines include default ns-3 MLO (FIFO), congestion-aware link selection, round-robin, static link-mapping, and an offline oracle lower bound.

### Criterion 7: Does the model predict a benefit that disappears once realistic per-link retransmission, contention, and arrival-time variability are represented?
- **Finding: PASS.**  
  Contention and retransmissions actually **magnify** the cross-flow penalty under FIFO scheduling because link asymmetry and retry bursts expand completion time variance, making sequence-delay inversions far more frequent and catastrophic.

### Criterion 8: Does the analytical result provide no useful guarantee beyond its own assumptions?
- **Finding: PASS.**  
  The theoretical model yields:
  - An exact BA window collapse boundary ($\lambda^* = W / \delta$).
  - A closed-form threshold for sequence inversion under sub-Gaussian service times.
  - A fundamental lower bound on achievable cross-flow delay for any causal online policy.

### Criterion 9: Can the result be validated using the available model or a feasible extension?
- **Finding: PASS.**  
  A rigorous, discrete-event simulation engine (`src/mlo_sim`) implements full 802.11be U-MAC/L-MAC framing, EDCA contention, multi-rate PHY, burst loss, sliding BA windows, and per-packet delay attribution.

### Criterion 10: Is the contribution substantial enough to distinguish it from the closest existing work?
- **Finding: PASS.**  
  The contribution bridges theoretical queueing/scheduling theory and practical Wi-Fi 7 protocol design, delivering both closed-form mathematical theorems and a deployable transmitter algorithm.

---

## 2. Verdict

**DECISION: SURVIVES NOVELTY AUDIT (PROCEED WITH CANDIDATE A).**  
No kill criteria are triggered. The scope is strictly delimited to sender-side U-MAC scheduling under standard IEEE 802.11be receiver constraints.
