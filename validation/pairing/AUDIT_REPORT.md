# Audit report, Wi-Fi 7 MLO reordering project (Studies 1-6, two manuscripts)

Date: 2026-10-18. Scope: process integrity, reproducibility, independent recomputation, paper-versus-data consistency, scientific status of every claim, and an honest split of remaining gaps into inherent ones and ones we could still fix. The audit was run by the same assistant that did the work; it therefore uses only mechanical checks (hash verification, git history, re-running scripts, recomputation with separately written code) wherever possible, and says so where it cannot.

## A. Process integrity (mechanical)
| Check | Result |
|---|---|
| All preregistration, amendment and exploratory-plan files match their stored SHA-256 (10 files) | pass |
| All raw/analysis hash lists verify (RAW_AND_ANALYSIS 8, STUDY2 3, STUDY3_PY 4, STUDY3_NS3 2, STUDY4 5, STUDY5 14, STUDY6 6 files) | pass, 0 mismatches |
| Each preregistration was first committed before the first result file of its study (Studies 2-6; gaps 244 s to 7,710 s) | pass |
| Each preregistration is byte-identical to the version first committed (Studies 2-6 and the Study 5 exploratory plan) | pass |
| Frozen ns-3 files (binary, patches, configs) unchanged since the Mission 1 freeze, except the disclosed `analyze_results.py` | pass |
| Runners refuse to run if a hash changed or results exist (single use) | by construction; not re-tested by re-running |
| Study 1 ordering (prereg d3b1131 before results 3000f3f) | checked in an earlier session, not re-run here |

## B. Reproducibility
- Re-running `analyze_study4.py`, `analyze_study5.py`, `analyze_study6.py` reproduced the committed JSON byte-for-byte.
- Test suite: 131 tests pass (Studies 1-6, property tests, theory tests).
- Number macros are generated (`make_numbers.py`, `make_numbers_theory.py`); both papers build with no undefined references or citations.

## C. Independent recomputation from raw CSVs (separately written code)
All matched the analysis outputs: Study 6 (900 traces: packets 249,142, events 16,554, event share 96.8%, certified share 44.1%, false rejections 0; 160 ns-3 runs: 3,253,034 packets checked, 873,950 blocked, release-law error 0, instrumentation difference 4.75e-10, occupancy equal in 160 runs; D2 overall ratio 99.48%, S/X 1.24%), Study 5 (R_Q cell A 1.89099; 700 oracle runs, max error 2.27e-13), Study 4 (cell S4/0.75/3.0: r = 0.15596, q = 0.08222, r >= q).

## D. Problems the audit found, and what was done
1. **Wording error in the theory paper** ("held in 0/13 of 13 ..."): fixed.
2. **Unscoped claim about ns-3 conclusions** (D2 measured only conditions A1 and A2): wording now states the scope; the measurement paper's limitations now carry the finding.
3. **Uncommitted results and scripts**: Study 2b raw/analysis files and their scripts, `run_exploratory.py`, two test files had never been committed; committed with this report. The two papers, their generated tables and the deliverables hash list remain uncommitted (standing convention: papers are committed only when the user asks).
4. **A definitional gap found earlier and now measured**: the ns-3 column used as "X" in Studies 3 and 4 charges the whole wait to a cross-flow binding blocker (it includes self-blocking). Study 6 D2 (60 runs, A1 and A2, loads L0-L2): pure X is at least 98.8% of it in every cell (99.5% overall). Condition A0 was not measured.
5. **Audit-tool errors (mine, not the project's)**: my first hash and commit-order commands were malformed (wrong relative paths, bad shell test); they were redone in Python and the results above come from the redone checks.

## E. Failures, deviations and flawed pieces that remain on record (all disclosed in the papers)
- Study 1: 3 of 6 audit hypotheses were refuted or immaterial (H1, H2, H3); H4-H6 confirmed.
- Study 2: the low-load validity control V3 failed (explained fraction outside 0.75-1.25); H7-H9 therefore carry a caveat.
- Study 3: the exact check V7 failed (0.0026 ms; single-row diagnosis verified post hoc); H12's gain metric was misaligned (found after seeing results; not used as evidence); the aligned test X7 found no decision benefit.
- Study 4: first V11 check was stricter than the frozen audit rule (fixed, outcome unchanged); the V10 5% sample seed was chosen by us; pooled correlation is helped by two platforms occupying different ranges (within-platform 0.85 and 0.60); r > 1 in two ns-3 cells.
- Study 5: H18b (Shapley more stable than the releaser rule on average) not confirmed (equal in simulator cells, not better on generators); H19 not confirmed as preregistered (quadrature criterion, two parameter sets; labelled post hoc refinement attributes it to numerical integration).
- Study 6: all preregistered hypotheses confirmed; the amendment adding timers, the bounded-error comparison and the certificate was written before hashing and was prompted by an adversarial review the user supplied (disclosed).

## F. Scientific status of the theory paper's contributions
| Contribution | Basis | Strength | Main caveat |
|---|---|---|---|
| Cross-flow blocking is an airport game | proof + exact oracles (700 + 900 + 160 runs; real receiver rerun on truncated traces) | strong | short proof; release law is classical |
| Closed-form replay-free Shapley blame; LOO misses exactly the second-largest lateness | proof + exact oracles | strong (exact) | rules coincide for most blocked packets in simulator and ns-3 |
| Forced release (window + timer), bounded error, certificate | proof + 900 traces, 18 configs, exact | strong for the stated receiver | timer receiver is our reference implementation; ns-3's block-ack-request release and duplicates untested; certificate conservative (44% certified in stress traces) |
| Second implementation (ns-3 reorder buffer) | 3.25 M packets exact, receiver equivalence, instrumentation identity | strong for receiver semantics | traffic/scenarios/metrics are ours; not hardware |
| Worst-case stability (L1-Lipschitz, constant 2) | proof + zero violations | strong as a bound | no average-case advantage (H18b) |
| Scope of additivity | proof (frozen trace, M/G/1) + replay test (R_Q 1.89, 1.74) | moderate | M/G/1 is stylised; replay R_X interval includes 1 in one cell |
| Poisson closed form | proof + MC (max abs z 2.7) | baseline only | preregistered convergence criterion failed |
| Bridge (identity, boundary, explained-fraction bound) | proofs + held-out cells (0 violations) | moderate | pooled-correlation caveat; ns-3 noise |

## G. Remaining gaps, split honestly
**Inherent (a reviewer would be right and we cannot remove them in software):** simulation only (no hardware, no public external trace); the theory is for a stated class of receivers; the structure theorem is short, so technical depth may be rated modest; Shapley is an axiomatic choice, other allocations were not compared; in the regimes studied the practical difference between blame rules is small, and no decision benefit was shown.
**Ours and still fixable:** the manuscripts and the deliverables hash list are uncommitted; authors are placeholders; ns-3's own block-ack-request forced release and duplicate arrivals have not been tested (would need further ns-3 stress scenarios); standard reordering metrics (reorder density, buffer-occupancy density) were not computed; condition A0 not measured in D2; two unused bibliography entries; the measurement paper (separate) does not yet carry Studies 5 and 6.

## H. Where a hostile reviewer would still push, and the honest answer
- "Idealised receiver": answered for window and hold timer (proved, 900 traces); not for ns-3's BAR-driven release or hardware.
- "Own simulator": partly answered (ns-3's reorder buffer, exact); scenarios remain ours.
- "Trivial structure / Shapley applied to delay": answered only by the consequences list; the paper states the depth risk itself.
- "So what": no decision benefit is claimed; the benefits are exactness, cost, a clear account of why the usual rules are degenerate, and a worst-case guarantee.
