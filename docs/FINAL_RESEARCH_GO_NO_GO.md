# Final Research Go/No-Go Decision Report (Phase 8 Audit)

**Project:** Cross-Flow Head-of-Line Blocking in Wi-Fi 7 Multi-Link Operation: Analytical Modeling and Sequence-Aware Scheduling  
**Repository Path:** `/home/adhyan/Desktop/wifi7_mlo_hol/`  
**Git Remote:** `git@github.com:adhyan-jain/computer_network_research.git`  
**Audit Date:** October 13, 2026  
**Auditor Role:** Independent Mathematical Reviewer, 802.11be Protocol Specialist, and Reproducibility Auditor  

---

## 1. Final Decision: CONDITIONAL GO

**DECISION: CONDITIONAL GO FOR SUBMISSION TO COMPUTER NETWORKS (ELSEVIER) OR IEEE OJCOMS.**

The project is scientifically sound, reproducible, and possesses genuine academic novelty following the mathematical repairs and protocol feasibility audit. However, submission is strictly conditioned on framing the paper as an **analytical modeling and discrete-event simulation study**, explicitly disclosing the absence of physical hardware testbed measurements and ns-3 cross-validation in the newly added 10-point Threats to Validity section.

---

## 2. Central Claimed Contribution

In IEEE 802.11be Multi-Link Operation, application flows multiplexed onto a common Traffic Identifier (TID 0) share a single Block Acknowledgment (BA) sequence space and reordering buffer, causing slow frames on congested links to trap subsequently-sequenced fast frames from interactive flows (Cross-Flow HOL Blocking). This paper provides the first formal analytical characterization of this phenomenon: proving an exact post-facto trace decomposition ($\Delta_i = \mathcal{S}_i + \mathcal{X}_i$), deriving the multi-link buffer divergence drift boundary ($\lambda^* = W/\delta$) with exact Poisson stall probabilities, proving a uniquely solvable pairwise Gaussian threshold rule $u^*(w_a, w_b)$, and bounding the symmetric-link stochastic uncertainty floor. We translate these mathematical findings into *Sequence-Aware Stochastic Partitioning (SASP)*, a transmitter-only Upper MAC scheduler that assigns sequence numbers according to predicted physical arrival epochs without requiring any receiver-side modifications.

---

## 3. Theorem Status and Survival Matrix

| Theorem | Formal Result | Status | Conditions of Validity | Scope Limitations |
| :--- | :--- | :---: | :--- | :--- |
| **Theorem 1** | Delay Accounting Decomposition:<br>$\Delta_i \equiv \mathcal{S}_i + \mathcal{X}_i$ | **SURVIVES** | Exact post-facto identity on an observed execution trace with in-order delivery. | Valid on realized traces. Lemma 1 attribution invariance does not hold counterfactually under medium contention. |
| **Theorem 2** | Multi-Link Sequence Divergence & Buffer Stall Probability | **SURVIVES (REPAIRED)** | Poisson arrivals, constant delay asymmetry $\delta = \mu_1 - \mu_2$, sliding window $W$. | Mean-drift crossover boundary at $\lambda^* = W/\delta$. Exact stall probability $\Pr(N \ge W) = \frac{\gamma(W, \lambda_2 \delta)}{(W-1)!}$. Retracted false "almost surely" claim. |
| **Theorem 3** | SASP Pairwise Threshold Rule:<br>$s_a < s_b \iff \frac{\mu_a - \mu_b}{\sigma_Z} \le u^*(w_a, w_b)$ | **SURVIVES** | Independent Gaussian completion times, strictly positive flow weights $w_a, w_b > 0$. | Strictly optimal for pairs ($N=2$). For $N \ge 3$, index sorting is an efficient $\mathcal{O}(M \log M)$ heuristic. Solver matches SciPy `brentq` to $< 10^{-12}$. |
| **Theorem 4** | Symmetric-Link Causal Uncertainty Floor:<br>$\min(C) = \min(w) \frac{\sigma_Z}{\sqrt{2\pi}}$ | **SURVIVES (REPAIRED)** | Concurrent multi-link dispatch on symmetric stochastic links ($\mu_a = \mu_b$). | Retracted false general inequality $\ge \min(w)\sigma_Z\phi(u)$. Floor holds at $u=0$. Zero cross-blocking achieved under Single-Link Operation. |

---

## 4. Retracted and Repaired Statements

1. **Retracted False Lower Bound Inequality:** The claim that $\min(C) \ge \min(w_a, w_b)\sigma_Z \phi(u)$ for all $u$ was proven mathematically false ($u=2.0 \implies \text{actual } 0.00849\sigma_Z < 0.05399\sigma_Z = \text{bound}$). Replaced with the exact symmetric floor $\min(w) \frac{\sigma_Z}{\sqrt{2\pi}}$ and asymptotic decay $C^*(u) \to 0$ as $|u| \to \infty$.
2. **Retracted "Almost Surely" Buffer Stall:** The claim that crossing $\lambda^*$ causes buffer stalls almost surely was disproven for Poisson arrivals ($\Pr(N < W) = 46.7\% > 0$ at $\lambda = \lambda^*$). Replaced with the exact Poisson tail formula and mean-drift analysis.
3. **Bounded Attribution Invariance (Lemma 1):** Explicitly acknowledged that attribution invariance is a trace accounting property, not a physical invariant under shared wireless contention (documented via Counterexample 1).
4. **Retracted Artificial Reviewer Scores:** Internal LLM review simulation scores (8.5/10) were permanently struck from the publication assessment.

---

## 5. Implementation Verification

- **Code Trace:** SASP is authentically implemented in `src/mlo_sim/schedulers.py:342-483`, executing batch predictive sequencing when parallel links are idle and evaluating in-flight cross-blocking penalties via `fast_partial_expectation` for single-link dispatches.
- **Sequence Allocation:** Sequence numbers are allocated strictly at dispatch time (`schedulers.py:426, 478`), not during queue ingestion.
- **Deterministic Testing:** 39 out of 39 automated tests pass cleanly in `.venv/bin/pytest tests/ -v` (0.96s), including 7 deterministic scenario tests covering identical links, predictive sequence inversion, unequal priorities, in-flight penalties, and window exhaustion.

---

## 6. IEEE 802.11be Protocol Feasibility

- **Architecture:** The 802.11be standard places per-TID sequence numbering strictly within the Upper MAC (U-MAC). Assigning sequence numbers at the dispatch epoch before handing MPDUs to L-MAC queues is standard-compliant.
- **Receiver Compatibility:** The receiver operates an unmodified standard IEEE 802.11be Block Ack reorder buffer. Standard commercial client stations receive frames seamlessly with zero protocol modifications.
- **Constraints:** Requires a centralized U-MAC scheduler with microsecond-level visibility into L-MAC transmit readiness. Once committed to PHY baseband transmission, frame sequence numbers cannot be retroactively modified.

---

## 7. Cited Novelty vs. Closest Prior Art

1. **Oliveira, Raposo, and Luís (IEEE OJCOMS 2026):** Conducted an empirical ns-3 characterization of aggregate BA reordering stalls. They proposed no mathematical models, no cross-flow decomposition, and no scheduling algorithms. SASP provides the analytical model, the closed-form stall conditions, and the predictive scheduling policy that Oliveira et al. left open.
2. **MediaTek Patent US12470496B2 / US20240244007A1 (Granted Nov 2025):** Claims a **receiving apparatus** that performs Deep Packet Inspection (DPI) to split receive queues per application flow. MediaTek requires custom receiver silicon. SASP is **purely transmitter U-MAC**, interoperating with 100% standard commercial receivers.
3. **MPTCP Schedulers (BLEST, LowRTT):** BLEST operates at Layer 4 across TCP socket buffers on 10–100 ms RTT scales. SASP operates at Layer 2 across hardware-constrained Block Ack bitmaps ($W \le 256$) on sub-millisecond timescales under EDCA contention.

---

## 8. Targeted Ablation Findings (Phase 6)

From 2,160 simulation runs across 30 paired seeds (`experiments/ablation_phase6/`):
- **Predictive Sequencing is the Primary Driver:** Both Mean-Only and Full SASP outperform FIFO across all regimes, reducing cross-blocking cost by **20% to 78%** (e.g. at $\Delta\mu = 2.0$ ms, FIFO cost is 4.85 vs SASP 1.06).
- **Theorem 3 Threshold Root Niche:** The variance-aware root $u^*$ provides a statistically significant **3.5% to 4.9% cost reduction ($p < 0.05$)** over Mean-Only Sequencing in the specific operating regime of **moderate-to-high priority asymmetry ($w \in [5, 50]$) with near-equal link means ($\Delta\mu \le 0.2$ ms)**.
- **Null/Equivalent Regimes:** Under equal flow weights ($w_a = w_b$) or large delay asymmetry ($\Delta\mu \ge 1.0$ ms), Full SASP and Mean-Only Sequencing make statistically identical decisions ($p = 0.96$ at 2.0 ms).

---

## 9. Reproducibility Status of Headline Claims

| Metric | Historical Claim | Recomputed from Raw CSVs | Status |
| :--- | :---: | :---: | :---: |
| Link Asymmetry ($\delta=5.0$ ms) Cross-Blocking Reduction | 16.1% | 16.14% (`exp1_link_asymmetry.csv`) | **REPRODUCIBLE** |
| Window Stall ($\lambda/\lambda^*=1.5$) Cross-Blocking Reduction | 96.8% | 96.81% (`exp2_window_collapse.csv`) | **REPRODUCIBLE** |
| Window Stall Tail Latency (p99) Reduction | 24.5% | 24.47% (`exp2_window_collapse.csv`) | **REPRODUCIBLE** |
| Priority Heterogeneity ($w=50$) Weighted Cost Reduction | 16.5% | 16.47% (`exp3_priority_heterogeneity.csv`) | **REPRODUCIBLE** |
| Frame Loss (FER=25%) Cross-Blocking Reduction | 36.2% | 36.16% (`exp4_contention_loss.csv`) | **REPRODUCIBLE** |
| Algorithmic Ablation Cost Reduction (FIFO $\to$ SASP) | 20.5% | 20.47% (`exp7_ablation_study.csv`) | **REPRODUCIBLE** |
| EXP-06 Constant 18.2% Advantage | 18.2% | 18.18% across all bias factors | **VERIFIED (Physical regime: $\Delta\mu \gg \sigma$)** |
| Scheduling Overhead | $\le 15.3\,\mu\text{s}$ | 1.27--16.26 $\mu$s in Python | **QUALIFIED (1.3--4.0 $\mu$s typical)** |

---

## 10. Limitations Preventing Stronger Claims

1. Custom Python discrete-event simulation rather than ns-3 or Omnet++.
2. Absence of physical over-the-air radio measurements on Wi-Fi 7 chipsets.
3. Gaussian completion time approximation under heavy retry escalation.
4. Assumption of simultaneous transmit and receive (STR) without in-device cross-talk.
5. SIFS timing compliance measured on host CPU rather than embedded network processor silicon.

---

## 11. Most Consequential Remaining Reviewer Objections

1. *"Why did the authors evaluate this in a custom Python discrete-event simulator rather than ns-3, which Oliveira et al. used?"*  
   *Defense:* Python allowed exact unit-level verification of sliding window mechanics and mathematical identities. The manuscript now explicitly lists this under Threats to Validity and frames results as an analytical proof-of-concept.
2. *"If Mean-Only Sequencing achieves ~99% of the gain over FIFO in wide-asymmetry regimes, why is the Theorem 3 threshold solver needed?"*  
   *Defense:* The Phase 6 ablation proves that the threshold root $u^*$ provides a statistically significant 3.5%--4.9% gain in near-equal mean regimes with priority asymmetry, and serves as the theoretical lower bound guarantee.

---

## 12. Highest-Impact Next Step

**Port the SASP Upper MAC scheduler to ns-3.41's `WifiMac` / `WifiDefaultAssocManager` MLO module.**  
Benchmarking SASP directly against the exact ns-3 model used by Oliveira et al. (IEEE OJCOMS 2026) would eliminate the custom simulator objection and provide direct, unimpeachable parity with existing literature.

---

## 13. Independent Verification Commands

To reproduce the complete audit from scratch:
```bash
cd /home/adhyan/Desktop/wifi7_mlo_hol

# 1. Run full unit and mathematical repair test suite (39 tests)
.venv/bin/pytest tests/ -v

# 2. Re-run Phase 6 ablation campaign (2,160 simulation runs)
.venv/bin/python3 experiments/ablation_phase6/run_ablation_campaign.py

# 3. Re-compile manuscript PDF (8 pages, clean build)
cd paper && pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
```

---
*End of Final Research Go/No-Go Decision Report.*
