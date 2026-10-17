# Independent Novelty Verdict (Phase 5 Audit)

**Date:** October 13, 2026  
**Auditor Role:** Independent Reviewer & Reproducibility Specialist  
**Topic:** Wi-Fi 7 MLO Sequence-Aware Stochastic Partitioning (SASP)  

*Disclaimer: This evaluation represents an academic novelty assessment for scientific peer-review positioning. It does NOT constitute a legal freedom-to-operate opinion or patent non-infringement clearance.*

---

## 1. Executive Summary & Verdict

**OVERALL NOVELTY VERDICT: CONFIRMED FOR NARROWED CLAIMS (CONDITIONAL GO).**

The project possesses authentic academic novelty when framed accurately:
1. **Mathematical Novelty:** The post-facto trace accounting decomposition ($\Delta_i = \mathcal{S}_i + \mathcal{X}_i$), the exact Poisson tail stall probability ($\Pr(N \ge W)$), the strictly optimal pairwise Gaussian threshold rule $u^*(w_a, w_b)$ for $N=2$, and the symmetric-link causal uncertainty floor ($\min(w)\frac{\sigma_Z}{\sqrt{2\pi}}$) are original theoretical results.
2. **Algorithmic Novelty:** Transmitter-side Upper MAC predictive sequence assignment—aligning sequence numbers with predicted physical arrival epochs to protect standard 802.11be Block Ack receiver buffers—is technically differentiated from published literature and patent disclosures.
3. **Crucial Claim Boundary (Phase 3 & Phase 5 Audit):**
   - Transitivity fails for pairwise comparisons ($N \ge 3$), meaning Theorem 3 does not generate a globally optimal multi-frame order. Multi-frame scheduling is an index heuristic.
   - The reported 3.5%--4.9% gain of Full SASP over Mean-Only Sequencing does not survive multiple-comparison corrections across the 18 tested configurations. The dominant source of the 20%--78% gain over FIFO is **predictive arrival ordering by means**, not the variance threshold.

---

## 2. Six Detailed Novelty Questions Answered

### Question 1: Is the CF-HOL problem itself novel?
**NO for the general reordering effect; YES for the formal cross-flow formulation.**
- The fact that multi-link latency asymmetry causes Block Ack window stalls was demonstrated empirically by Carreño et al. (2021) and Oliveira et al. (2026).
- However, prior works treated reordering as an aggregate, single-stream delay spike. This paper is the first to formalize **cross-flow interference between distinct application flows multiplexed onto a shared TID** and provide an exact, orthogonal trace decomposition separating intra-flow self-blocking from inter-flow cross-blocking.

### Question 2: Is the specific pairwise decision rule novel?
**YES.**
- The derivation of the transcendental equation $h(u) = (w_b - w_a)\phi(u) + [w_a(1-\Phi(u)) + w_b\Phi(u)]u = 0$, the proof of strictly positive derivative $h'(u) > 0$, and the threshold decision rule $s_a < s_b \iff (\mu_a - \mu_b)/\sigma_Z \le u^*(w_a, w_b)$ are mathematically novel.
- No prior wireless MAC algorithm utilizes this threshold root for frame sequence allocation.

### Question 3: Is the multi-frame scheduling policy novel?
**CONDITIONALLY (as an engineering heuristic).**
- Universal transitivity fails for pairwise comparisons (proven by our discovered Condorcet cycle $A \prec B \prec C \prec A$).
- SASP's multi-frame policy—using Theorem 3 for $N=2$ pairs and scalar mean sorting for $N \ge 3$ batches—is an effective heuristic, but it is not globally optimal. Global batch optimality requires complete permutation enumeration over $N!$ sequence assignments under the non-additive receiver delay model.

### Question 4: Is the resulting combined mechanism meaningfully different from the closest published work?
**YES.**
- **Versus Oliveira, Raposo, and Luís (IEEE OJCOMS 2026):** Oliveira et al. conducted an empirical ns-3 measurement study of aggregate BA stalls. They proposed no mathematical models, no closed-form stall conditions, and no sequence scheduling algorithms. SASP provides the theoretical framework and the sender-side predictive sequencing policy.
- **Versus MediaTek (US12470496B2 / US20240163947A1, Nov 2025):** MediaTek requires a proprietary receiving station that executes Deep Packet Inspection (DPI) to split incoming packets into separate per-flow reorder queues. SASP is **purely transmitter U-MAC**, interoperating with standard commercial client stations without modifying 802.11be receiver semantics.
- **Versus Carreño et al. (2021), Choi et al. (2025), and ATLAS (2026):** These schedulers allocate packets to links, but assign sequence numbers strictly in FIFO arrival order. SASP actively decouples link assignment from sequence numbering.

### Question 5: Does the evidence establish a meaningful advantage?
**YES over FIFO (20%--78%); UNPROVEN over Mean-Only Sequencing.**
- SASP provides a major, reproducible advantage over standard FIFO MLO, reducing cross-flow blocking by 20% to 78% under asymmetric link conditions ($\Delta\mu \ge 0.5$ ms).
- However, the statistical audit proves that Full SASP's variance-aware root $u^*$ does not provide a statistically significant improvement over simple Mean-Only Sequencing once multiple comparisons are controlled. The paper must frame predictive sequencing as the primary contribution, with the Theorem 3 threshold root serving as a theoretical guarantee and priority tie-breaker rather than an empirical breakthrough.

### Question 6: Which claims remain uncertain because of incomplete prior-art access?
1. Proprietary, unreleased microcode heuristics in commercial AP chipsets (Broadcom, Qualcomm, Intel).
2. Recently published or pending patent applications (post-mid-2025) concerning transmitter sequence management.
3. Hardware-level SIFS turnaround feasibility under high PHY data rates.

---

## 3. Disallowed Claims Matrix

| Disallowed Claim | Reason for Strike | Mandatory Replacement Claim |
| :--- | :--- | :--- |
| "Zero patent risk / absolute freedom to operate" | Literature audit is an engineering study, not legal advice | "Engineering prior-art analysis distinguishes SASP from published receiver-side patents" |
| "Universal causal lower bound $\ge \min(w)\sigma_Z\phi(u)$" | Mathematically false for all $u > 0$ | "Symmetric-link stochastic uncertainty floor $\min(w)\frac{\sigma_Z}{\sqrt{2\pi}}$ at $u=0$" |
| "Almost surely window collapse at $\lambda = \lambda^*$" | Mathematically invalid for Poisson arrivals ($\Pr(N < W) = 46.7\%$) | "Mean-drift crossover boundary with exact Poisson stall probability $\Pr(N \ge W)$" |
| "Statistically significant 3.5%--4.9% gain over Mean-Only" | Fails multiple-comparison correction across 18 tested configurations | "Predictive sequencing provides up to 78% reduction over FIFO; threshold root acts as an index tie-breaker in near-equal mean regimes" |
| "Globally optimal multi-frame scheduler" | Transitivity fails; pairwise preferences can form cycles | "Pairwise optimal decision rule providing an efficient index heuristic for multi-frame scheduling" |
| "100% compliant and deployable in commercial Wi-Fi 7" | Evaluated only in custom Python simulator; no physical silicon testbed | "Sender-side mechanism compatible with standard IEEE 802.11be receiver semantics under simulation" |

---
*End of Independent Novelty Verdict.*
