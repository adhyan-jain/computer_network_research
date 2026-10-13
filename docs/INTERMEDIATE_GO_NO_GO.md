# Intermediate Go/No-Go Decision Gate (Phase 5)

**Evaluation Epoch:** Post-Phases 1–4 Verification Gate  
**Date:** October 13, 2026  
**Auditor Role:** Independent Research Oversight Auditor  

---

## 1. Gate Evaluation Summary

To prevent premature execution of new simulation campaigns on unverified premises, the project must satisfy six non-negotiable criteria before proceeding to Phase 6 ablation experiments.

| Gate ID | Verification Criterion | Audit Findings & Evidence Links | Gate Status |
| :---: | :--- | :--- | :---: |
| **GATE-1** | Core scheduler implemented as described | Code audit in `src/mlo_sim/schedulers.py:342-483` confirms joint batch sorting and in-flight penalty evaluation. Passed 7 deterministic scenario tests in `tests/test_deterministic_scenarios.py`. | **PASS** |
| **GATE-2** | Sequence allocation protocol-feasible | Feasibility audit in `docs/IMPLEMENTATION_AND_PROTOCOL_AUDIT.md` confirms 100% standard conformance to IEEE 802.11be U-MAC/L-MAC architecture with unmodified receiver entities. | **PASS** |
| **GATE-3** | Central analytical rule correct | Theorem 3 derivative $h'(u) > 0$ strictly proved; root solver matches SciPy `brentq` to $< 10^{-12}$ in `tests/test_mathematical_repair.py`. | **PASS** |
| **GATE-4** | Invalid theorems repaired or retracted | Theorem 4 false inequality retracted and replaced with exact symmetric floor; Theorem 2 "almost surely" replaced with exact Poisson tail stall probability in `theory/derivation.md`. | **PASS** |
| **GATE-5** | Historical headline numbers reproducible | All metrics reconciled against raw CSVs in `docs/CLAIM_EVIDENCE_AUDIT.md`; EXP-06 invariance artifact fully explained. | **PASS** |
| **GATE-6** | Plausible, specific literature novelty | Confirmed in `docs/INDEPENDENT_NOVELTY_VERDICT.md`; genuine transmitter-side architectural seam distinguishing SASP from Oliveira 2026 and MediaTek US12470496B2. | **PASS** |

---

## 2. Decision Verdict

**VERDICT: GO TO PHASE 6 ABLATION EXPERIMENTS.**

All six gates have been satisfied with verifiable evidence. The theoretical foundations are repaired, implementation verified, and historical results reconciled. Execution of the targeted ablation campaign in a separate, isolated output directory (`experiments/ablation_phase6/`) is approved.

---

## 3. Scope and Directives for Phase 6

1. **Isolation Rule:** New experiment scripts and outputs must reside in `experiments/ablation_phase6/` and must never overwrite historical files in `experiments/results/`.
2. **Target Hypothesis:** Test Full SASP versus Mean-Only Sequencing in the regime where the Theorem 3 threshold root $u^*$ is predicted to produce a divergence in scheduling decisions:
   - High priority asymmetry ($w_{\text{interactive}} / w_{\text{bulk}} \ge 50$)
   - Near-equal predicted completion means ($\mu_1 \approx \mu_2$)
   - Asymmetric link completion variances ($\sigma_1 \ne \sigma_2$)
3. **Statistical Discipline:** Paired random seeds across schedulers, reporting decision divergence counts, effect sizes, and 95% confidence intervals. If Full SASP and Mean-Only are statistically indistinguishable, report that null result honestly.
