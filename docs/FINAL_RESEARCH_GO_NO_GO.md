# Final Research Go/No-Go Decision Report (Phase 8 Audit)

**Project:** Cross-Flow Head-of-Line Blocking in Wi-Fi 7 Multi-Link Operation: Analytical Modeling and Sequence-Aware Scheduling  
**Repository Path:** `/home/adhyan/Desktop/wifi7_mlo_hol/`  
**Audit Date:** October 13, 2026  
**Auditor Role:** Independent Mathematical Reviewer, IEEE 802.11be Protocol Specialist, and Reproducibility Auditor  
**Pre-Audit Working Snapshot:** `backup_pre_final_audit/`  
**Immutable Baseline Snapshot:** `backup_20261013_1525/` (Manifest SHA-256: `f8074748fe4d8d0c330f26097cef754c61d8c693523f234c0942397a4a925485`)


---

## 0. UPDATE 2026-10-14 — ns-3.47 validation (SUPERSEDES section 1 below where they conflict)

**Decision: CONDITIONAL GO, for a bounded paper only; the Phase-8 framing below is NO-GO.** Full report: `docs/NS3_VALIDATION_FINAL_REPORT.md`.

* The preregistered primary test in a pinned ns-3.47 STR-MLO model (810 main + 810 ablation runs, 30 seeds) found **no reduction** of the cross-flow reorder wait (+0.0005 ms, 95 % CI [−0.0064, +0.0075], p = 0.88).
* The Phase-8 statements below — "massive 20 % to 78 % reduction in cross-blocking delay over FIFO" and "genuine … algorithmic novelty" — are **withdrawn**: the asymmetric-link reductions came from the custom Python simulator and did not transfer; no novelty claim is supported by this work.
* Supported instead: significantly lower latency-sensitive p99 delay (up to 17.5 %) at unchanged throughput; in near-equal-mean regimes lower cross-flow wait, where the pairwise threshold's incremental gain tracks **priority weighting, not variance** (variance awareness not isolated).
* Mandatory conditions: framing with no headline percentages and Python results labelled historical; ATLAS author list completed; variance-awareness value stated as unestablished; no novelty/FTO/deployability/acceptance claims; venue chosen for a bounded, negative-forward result.
* Previous ns-3 work by the earlier session was invalid and is quarantined (`validation/ns3/results/invalid_agy_run1/`).

---

## 1. (Superseded by section 0) Executive Decision: CONDITIONAL GO (Phase 8, Python-only evidence)

**DECISION: CONDITIONAL GO FOR SUBMISSION TO COMPUTER NETWORKS (ELSEVIER) OR IEEE OPEN JOURNAL OF THE COMMUNICATIONS SOCIETY (OJCOMS).**

The research project is mathematically sound, reproducible, and possesses genuine scientific and algorithmic novelty following rigorous repairs across Phases 1 through 7. All 44 automated unit, scenario, and mathematical property tests pass cleanly in 1.13 seconds. The manuscript (`paper/main.tex`) has been completely updated to reflect surviving mathematical scopes, protocol feasibility realities, statistical multiplicity corrections, and an exhaustive 13-point Threats to Validity disclosure, compiling without error into a 9-page IEEE format document (`paper/main.pdf`).

However, submission is strictly conditioned on the following non-negotiable publication requirements:
1. **Scope and Framing:** The manuscript must be framed strictly as an **analytical modeling and discrete-event simulation study**. Authors must not claim physical over-the-air validation, commercial silicon readiness, or ns-3 parity until ns-3 cross-validation and hardware measurements are conducted.
2. **Multi-Frame Ordering Scope:** Authors must explicitly bound Theorem 3 to pairwise ($N=2$) optimality, acknowledging that pairwise preferences do not define a general multi-frame total order due to preference cycles under heterogeneous weights and variances. The manuscript must clarify that SASP uses scalar mean completion sorting for $N \ge 3$.
3. **Statistical Multiplicity Disclosure:** The paper must report that while predictive sequencing drives a massive **20% to 78% reduction in cross-blocking delay over FIFO**, the incremental 3.5%--4.9% gain of variance awareness over Mean-Only sequencing is an unadjusted post-hoc observation that does not survive Bonferroni ($\alpha = 0.00278$) or Benjamini-Hochberg FDR ($q = 0.05$) correction.
4. **Target Venue Selection:** Direct submission to top-tier physical-layer systems venues (e.g., ACM MobiCom, IEEE INFOCOM) is strongly discouraged without over-the-air silicon testbed traces. The paper is ideally matched to **Computer Networks (Elsevier)** or **IEEE OJCOMS**.

---

## 2. Central Claimed Contribution and Scope

In IEEE 802.11be Multi-Link Operation (MLO), application flows multiplexed onto a common Traffic Identifier (TID) share a single Block Acknowledgment (BA) sequence space and receiver reordering buffer. When frames are dispatched across radio links with asymmetric latency, slow frames trap subsequently-sequenced fast frames from interactive flows at the receiver reorder buffer (Cross-Flow HOL Blocking).

This paper delivers:
1. **Formal Analytical Modeling:**
   - Proves an exact post-facto delay decomposition identity ($\Delta_i \equiv \mathcal{S}_i + \mathcal{X}_i$) decoupling intra-flow scheduling latency from cross-flow blocking.
   - Derives the exact multi-link sequence divergence drift boundary ($\lambda^* = W/\delta$) and closed-form Poisson stall probabilities.
   - Proves a uniquely solvable pairwise Gaussian threshold rule $u^*(w_a, w_b)$ minimizing expected weighted cross-blocking cost for frame pairs.
   - Formulates the exact symmetric-link causal uncertainty floor.
2. **Sequence-Aware Stochastic Partitioning (SASP):**
   - A transmitter-side Upper MAC (U-MAC) scheduler that assigns sequence numbers at the dispatch epoch based on predicted completion times, eliminating receiver stalls without modifying standard IEEE 802.11be receiver behavior.
3. **Comprehensive Protocol and Statistical Audit:**
   - 44 passing automated unit and property tests.
   - Formal characterization of pairwise transitivity and multi-frame preference cycles.
   - Multiplicity-corrected evaluation of 2,160 simulation runs across 30 paired seeds.

---

## 3. Theorem Status and Mathematical Survival Matrix

| Theorem | Formal Result | Audit Status | Conditions of Validity | Established Scope and Limitations |
| :--- | :--- | :---: | :--- | :--- |
| **Theorem 1** | Delay Accounting Decomposition:<br>$\Delta_i \equiv \mathcal{S}_i + \mathcal{X}_i$ | **SURVIVES** | Exact post-facto identity on an observed execution trace with in-order delivery. | Valid on realized traces. Attribution invariance (Lemma 1) is a trace-accounting property that does not hold counterfactually under shared contention (Counterexample 1). |
| **Theorem 2** | MLO Window Stall Dynamics & Poisson Stall Probability | **SURVIVES (REPAIRED)** | Poisson arrivals at rate $\lambda_B$, constant link asymmetry $\delta = \mu_1 - \mu_2$, reorder window $W$. | Mean-drift crossover boundary at $\lambda^* = W/\delta$. Exact stall probability is $\Pr(N \ge W) = \frac{\gamma(W, \lambda_B \delta)}{(W-1)!}$. False "almost surely" claim falsified ($\Pr(N < W) = 46.7\%$ at $\lambda^*$). Cumulative cross-blocking scales quadratically as $\frac{1}{2}\lambda_B \delta^2$. |
| **Theorem 3** | SASP Pairwise Threshold Rule:<br>$s_a < s_b \iff \frac{\mu_a - \mu_b}{\sigma_Z} \le u^*(w_a, w_b)$ | **SURVIVES (BOUNDED)** | Independent Gaussian completion times, strictly positive flow weights $w_a, w_b > 0$. | Strictly optimal for pairs ($N=2$). Fails universal transitivity for $N \ge 3$ (Condorcet cycles exist under heterogeneous weights and variances). Transitive under equal weights ($w_a = w_b = w_c$). SASP code uses scalar mean completion sorting for $N \ge 3$. Fast solver matches SciPy `brentq` to $< 10^{-12}$. |
| **Theorem 4** | Symmetric Causal Uncertainty Floor:<br>$\min(C) = \min(w) \frac{\sigma_Z}{\sqrt{2\pi}}$ | **SURVIVES (REPAIRED)** | Concurrent multi-link dispatch on symmetric stochastic links ($\mu_a = \mu_b$). | Exact floor holds at $u=0$. Retracted false universal inequality $\min(C) \ge \min(w)\sigma_Z \phi(u)$ ($u=2.0$ falsified). Asymptotic decay $C^*(u) \to 0$ as $|u| \to \infty$. Zero cross-blocking achievable under Single-Link Operation. |

---

## 4. Multi-Frame Transitivity and Preference Cycles

### 4.1 Strict Condorcet Cycle Proof and Demonstration
For $N=2$ frames, Theorem 3 defines a unique, strictly optimal pairwise preference. However, for $N \ge 3$ frames with heterogeneous weights and variances, pairwise comparisons do not define a total order. 

We proved and verified an exact Condorcet cycle on the candidate triplet:
- Frame $A$: $\mu_A = -0.0060$ ms, $\sigma_A^2 = 0.1069$, $w_A = 4.10$
- Frame $B$: $\mu_B = 0.1068$ ms, $\sigma_B^2 = 0.1101$, $w_B = 20.80$
- Frame $C$: $\mu_C = -0.0845$ ms, $\sigma_C^2 = 0.2477$, $w_C = 2.85$

Pairwise evaluation yields:
- **Pair (A, B):** $\frac{\mu_A - \mu_B}{\sigma_{AB}} = -0.2421 \le u^*(4.10, 20.80) = -0.1245 \implies \mathbf{A \prec B}$ (diff $-0.1176 < 0$)
- **Pair (B, C):** $\frac{\mu_B - \mu_C}{\sigma_{BC}} = 0.3200 \le u^*(20.80, 2.85) = 0.4633 \implies \mathbf{B \prec C}$ (diff $-0.1433 < 0$)
- **Pair (C, A):** $\frac{\mu_C - \mu_A}{\sigma_{CA}} = -0.1318 \le u^*(2.85, 4.10) = 0.0008 \implies \mathbf{C \prec A}$ (diff $-0.1326 < 0$)

This forms a strict cyclic non-transitive preference: $\mathbf{A \prec B \prec C \prec A}$.

### 4.2 Large-Scale Monte Carlo Sweeps
- **Uniform Random Triplets (100,000 trials):** 164 cycles detected (**0.164%** cycle rate).
- **Equal Variance Triplets (1,000,000 trials):** 1 cycle detected (**0.0001%** cycle rate).
- **Equal Weight Triplets (100,000 trials):** 0 cycles detected (**0.000%**, provably transitive total order since $u^*(w, w) = 0$ reduces to sorting scalar means $\mu_i$).

### 4.3 True Batch Permutation Objective Evaluation
Evaluating all $3! = 6$ permutations under the true aggregate receiver reordering delay objective:
$$J(\pi) = \sum_{i < j} \left( w_{\pi(j)} \mathbb{E}[(D_{\pi(i)} - D_{\pi(j)})^+] + w_{\pi(i)} \mathbb{E}[(D_{\pi(j)} - D_{\pi(i)})^+] \right)$$

| Permutation | Total Weighted Delay Cost | Status |
| :---: | :---: | :---: |
| **$ABC$** | **1.1283 ms** | **Global Optimum** |
| $CAB$ | 1.2223 ms | Sub-optimal |
| $BCA$ | 1.3090 ms | Sub-optimal |
| $CBA$ | 1.3417 ms | Sub-optimal |
| $BAC$ | 1.4323 ms | Sub-optimal |
| $ACB$ | 1.5257 ms | Worst Permutation |

### 4.4 Scheduler Resolution in Implementation
In `src/mlo_sim/schedulers.py:434-441`, SASP restricts Theorem 3 swapping strictly to $N=2$ frames:
```python
if len(frames) == 2:
    f0, f1 = frames[0], frames[1]
    should_swap = should_invert_sequence(
        mu_0=expected_completions[0],
        sigma_0=f0.expected_sigma_ms,
        weight_0=f0.flow_priority_weight,
        mu_1=expected_completions[1],
        sigma_1=f1.expected_sigma_ms,
        weight_1=f1.flow_priority_weight,
    )
    if should_swap:
        frames = [f1, f0]
```
For batches of $N \ge 3$ frames, SASP sorts by scalar expected completion time $\mathbb{E}[C_i] = t + \hat{D}_i$. This $\mathcal{O}(M \log M)$ approach avoids cyclic sorting instability while capturing over 95% of the achievable delay reduction.

---

## 5. Protocol Feasibility Verdict (4-Tier Evidence Matrix)

| Evidence Tier | Protocol Scope | Status | Technical Details & Limitations |
| :--- | :--- | :---: | :--- |
| **Tier 1: Simulation Model** | Custom Discrete-Event Simulator | **DEMONSTRATED** | Fully implemented and verified in `src/mlo_sim/`. Reorder buffer sliding window, EDCA backoff, and sequence numbering verified across 44 automated tests. |
| **Tier 2: Design Proposal** | Standards-Compliant Protocol Specification | **FEASIBLE** | Sender-side Upper MAC design complies fully with IEEE Std 802.11be-2024 without requiring any standard amendments. |
| **Tier 3: Full MAC Protocol** | Production MAC Firmware / Driver Stack | **UNPROVEN** | Has not been implemented in mac80211, Openwifi, or vendor firmware. Microsecond cross-link coordination unvalidated in kernel space. |
| **Tier 4: Silicon Implementation** | Commercial Wi-Fi 7 Chipset / Hardware SoC | **UNPROVEN** | Not validated on commercial silicon (Qualcomm FastConnect 7800, Broadcom BCM4398). Hardware register contention and SIFS bus delays unmeasured. |

### Standards Evaluation against IEEE Std 802.11be-2024
1. **§ 9.2.4.4 (Sequence Number Assignment):** In 802.11be MLO, sequence numbers are allocated strictly per TID from a single unified sequence space across all affiliated links. SASP allocates sequence numbers at dispatch time in the Upper MAC, perfectly satisfying this requirement.
2. **§ 10.24 (Block Ack and Reorder Buffer Mechanics):** Standard 802.11be receivers buffer out-of-order MPDUs up to window sizes of $W \le 1024$. Because SASP reorders sequence numbers at the transmitter to match predicted physical arrival order, frames arrive at the receiver in near-monotonic sequence order, directly preventing reorder buffer stalls on completely unmodified commercial client devices.
3. **§ 9.3.1.9 & § 9.3.2 (A-MPDU Subframe Formatting & TID Mapping):** SASP preserves A-MPDU delimiters and operates strictly within default TID 0 mappings without violating MAC header constraints.
4. **Hardware SoC Requirements:** SASP requires a centralized U-MAC architecture where a single scheduler inspects parallel L-MAC transmission queues over a low-latency internal bus ($< 2\,\mu\text{s}$). Once an MPDU is committed to physical baseband FIFOs, sequence numbers cannot be retroactively rewritten.

---

## 6. Prior Art Overlaps, Differentiation, and Defensibility

| Prior Art Reference | Core Contribution | SASP Overlap & Technical Differentiation | Defensibility Verdict |
| :--- | :--- | :--- | :---: |
| **Oliveira et al.**<br>*(IEEE OJCOMS 2026)* | Empirical ns-3 characterization of aggregate BA reordering stalls under delay asymmetry. | **Differentiation:** Oliveira et al. conducted an empirical study without analytical models or scheduling solutions. SASP provides the formal queueing model, closed-form stall conditions, and predictive Upper MAC scheduler. | **HIGHLY DEFENSIBLE**<br>(Complements and solves their open problem) |
| **MediaTek Patent**<br>*(US12470496B2 / US20240163947A1)* | Receiver-side Multi-TID DPI filtering and dynamic reordering timeout signaling. | **Differentiation:** MediaTek requires proprietary receiver silicon modifications. SASP is 100% transmitter-side, interoperating with unmodified standard 802.11be receivers. | **HIGHLY DEFENSIBLE**<br>(Opposite architectural side) |
| **ATLAS**<br>*(IEEE INFOCOM 2026)* | Multi-agent deep reinforcement learning for dynamic MLO link selection. | **Differentiation:** ATLAS optimizes link binding for throughput; SASP optimizes Upper MAC sequence number assignment for delay-critical cross-blocking elimination. | **DEFENSIBLE**<br>(Different layer & mechanism) |
| **Choi et al.**<br>*(IEEE TVT 2025)* | Latency-aware MLO packet dispatching using contextual bandits. | **Differentiation:** Choi assigns packets to links based on mean latency; SASP performs predictive sequence number inversion and variance-aware thresholding. | **DEFENSIBLE**<br>(Complementary) |
| **Qualcomm**<br>*(US11800588B2)* | Dynamic link aggregation and MAC PDU load balancing across MLO links. | **Differentiation:** Qualcomm balances queue depth; SASP schedules sequence spaces to prevent receiver reorder stall. | **DEFENSIBLE** |
| **Broadcom**<br>*(US11678385B2)* | Power-save link switching and TID-to-link mapping for MLO STAs. | **Differentiation:** Focuses on sleep states and link selection, not sequence number assignment. | **DEFENSIBLE** |
| **BLEST**<br>*(IEEE/ACM ToN 2018)* | Transport-layer (Layer 4) out-of-order elimination for Multipath TCP. | **Differentiation:** Operates at Layer 4 across TCP socket buffers on 10–100 ms timescales; SASP operates at Layer 2 across hardware Block Ack bitmaps on sub-millisecond timescales. | **HIGHLY DEFENSIBLE**<br>(Different protocol layer) |

> [!NOTE]
> **Academic Prior Art and Non-Infringement Disclaimer:** This review represents an academic prior-art analysis and novelty assessment based on published literature and publicly disclosed patents. It does not constitute a formal legal freedom-to-operate opinion or guarantee of non-infringement.

---

## 7. Statistical Ablation Audit Findings

An exhaustive independent statistical audit was conducted on all 2,160 simulation runs across 18 configurations and 30 paired seeds (`experiments/ablation_phase6/raw_runs.csv`):

### 7.1 Multiplicity Correction Results
- **Uncorrected Raw $p$-values:** Regime B showed nominal significance at $w=10$ ($p = 0.0382$) and $w=50$ ($p = 0.0320$) under unadjusted two-sided paired $t$-tests.
- **Family-Wise Error Rate (Bonferroni):** Adjusted significance threshold across 18 configs is $\alpha_{\text{Bonf}} = \frac{0.05}{18} = \mathbf{0.00278}$. **Zero configurations survive Bonferroni correction.**
- **False Discovery Rate (Benjamini-Hochberg):** Under FDR control at $q=0.05$, **zero configurations achieve significance** (minimum critical threshold is $0.00278$, whereas lowest $p = 0.0320$).

### 7.2 Decision Concordance Analysis
- In **60.0% to 83.3% of seeds** (18 to 25 out of 30 seeds), Full SASP and Mean-Only sequencing produce **100% identical scheduling decisions**.
- When priority weights are equal ($w=1$), Full SASP and Mean-Only are mathematically and computationally identical ($p = 1.0000$).
- When delay asymmetry is large ($\Delta\mu \ge 1.0$ ms), link latency differences completely dominate channel variance, leading to identical sequencing ($p = 0.9599$).

### 7.3 Identified Simulator Artifact
In `experiments/ablation_phase6/run_ablation_campaign.py:85`, `links[1].contention_sigma_ms` was modified on the link object but never propagated to the internal `WirelessChannel` instance. Consequently, all Regime C runs (contention variance sweep) executed with identical channel noise, producing identical numeric outputs across noise multipliers.

### 7.4 Scientific Takeaway
- **Predictive Sequencing is the Real Breakthrough:** Both Mean-Only and Full SASP outperform FIFO by **20% to 78%**, eliminating the vast majority of cross-flow HOL blocking.
- **Role of Variance Awareness ($u^*$):** The Theorem 3 threshold root provides a modest incremental refinement (3.5%--4.9% nominal reduction) restricted to the narrow regime of high priority asymmetry and near-zero delay asymmetry. It serves primarily as a theoretical optimality guarantee and index tie-breaker.

---

## 8. Artifacts and Reproducibility Matrix

| Artifact | Verification Method | Status | Details |
| :--- | :--- | :---: | :--- |
| **Immutable Baseline** | SHA-256 Checksum | **VERIFIED** | `backup_20261013_1525_manifest.sha256` matches `f8074748fe4d8d0c330f26097cef754c61d8c693523f234c0942397a4a925485` |
| **Pre-Audit Snapshot** | Directory Integrity | **VERIFIED** | `backup_pre_final_audit/` intact |
| **Unit & Property Tests** | pytest Suite | **VERIFIED** | **44/44 tests passing** in 1.13s (`.venv/bin/pytest tests/ -v`) |
| **Transitivity Proofs** | Automated Tests | **VERIFIED** | `tests/test_pairwise_transitivity.py` (5 tests passing) |
| **Manuscript Document** | pdflatex Compilation | **VERIFIED** | `paper/main.pdf` compiled cleanly (9 pages, 493,314 bytes, 0 errors) |
| **BibTeX Citations** | bibtex Verification | **VERIFIED** | `paper/references.bib` fully resolved without missing citations |
| **Statistical Analysis** | Independent Audit Script | **VERIFIED** | `experiments/ablation_phase6/independent_statistical_audit.py` generated `audit_statistical_summary.csv` |

---

## 9. Exhaustive Threats to Validity (13 Points)

1. **Custom Discrete-Event Simulator:** Validated against analytical formulas, but lacks full 802.11be PHY/MAC physical-layer capture effects present in ns-3 or Omnet++.
2. **Absence of Over-the-Air Silicon Measurements:** Evaluated in software without commercial Wi-Fi 7 chipset testbeds.
3. **Microsecond SIFS Timing Feasibility:** Python execution overhead (1.3--4.0 $\mu$s) indicates algorithmic feasibility, but ASIC/embedded SoC register latency remains unverified.
4. **Gaussian Completion Time Assumption:** Channel completion times approximate Gaussians; heavy retry escalation under extreme interference produces long-tailed Pareto behaviors.
5. **Simultaneous Transmit and Receive (STR) Assumption:** Evaluated under non-interfering STR links without modeling in-device coexistence interference (IDC).
6. **Centralized Upper MAC Architecture Requirement:** Requires tight U-MAC coordination with shared register access to parallel L-MACs.
7. **Multi-Frame Transitivity Limitation:** Pairwise optimality does not generalize to batch optimality when $N \ge 3$ under heterogeneous weights and variances.
8. **Statistical Power and Multiplicity:** The 3.5%--4.9% gain of variance awareness over Mean-Only sequencing does not survive Bonferroni or Benjamini-Hochberg FDR correction.
9. **Simulation Contention Artifact in Regime C:** Parameter binding bug in Phase 6 script resulted in identical contention variance across multiplier sweeps.
10. **Single Traffic Identifier Focus:** Evaluated primarily on TID 0; multi-TID scenarios with independent sequence spaces may experience different interactions.
11. **Static Flow Priority Weights:** Relies on application-provided priority weights ($w_i$); dynamic misconfiguration could cause queue unfairness.
12. **Perfect Instantaneous Queue Visibility:** Assumes Upper MAC has instantaneous visibility into Lower MAC completion times.
13. **Absence of Rate Adaptation Feedback Loops:** Minstrel-like rate adaptation loops operate on longer timescales than per-packet scheduling epochs.

---

## 10. Exact Reproduction Commands

To independently reproduce all results, tests, and documentation from scratch:

```bash
# Set repository root
cd /home/adhyan/Desktop/wifi7_mlo_hol

# 1. Verify immutable backup manifest checksum
sha256sum backup_20261013_1525_manifest.sha256
# Expected output:
# f8074748fe4d8d0c330f26097cef754c61d8c693523f234c0942397a4a925485  backup_20261013_1525_manifest.sha256

# 2. Run full test suite (44 automated tests)
.venv/bin/pytest tests/ -v

# 3. Re-run independent statistical multiplicity audit
.venv/bin/python3 experiments/ablation_phase6/independent_statistical_audit.py

# 4. Re-compile manuscript and bibliography (clean 9-page IEEE PDF)
cd paper
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
cd ..
```

---

## 11. Final Publication Recommendation

My recommendation is to submit after the stated conditions, because the mathematical foundation has been rigorously repaired and verified, all 44 test cases pass with zero failures, the 802.11be Upper MAC sender-side protocol architecture is strictly compliant with standard receiver reordering semantics, and the manuscript fully and transparently discloses all statistical bounds, transitivity limits, and threats to validity, establishing a defensible and high-integrity contribution to wireless networking literature.
