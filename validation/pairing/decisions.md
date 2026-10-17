# Decisions log (validation/pairing)

Append-only. Each entry: what was decided, why, what it changes. Dates are 2026-10-17 unless stated.

## D01 Paper framing: measurement validity, not scheduler novelty
- Decision: the paper's claim is about the *evaluation methodology* of simulation-based MLO reordering studies (paired-seed coupling, survivor bias, loss-draw spec conformance, attribution scope, causality), plus what those flaws do to the SASP comparison.
- Why: the Mission 1 ns-3 results showed SASP's gain is mostly null/priority-driven; a scheduler-superiority paper would not survive review. Invariant violations are checkable with exact oracles.
- Consequence: no claim that SASP wins; the SASP comparison is the worked example.

## D02 Cross-field transplants adopted (user request: borrow techniques from other fields)
- Survival analysis / right-censoring (clinical statistics) -> censored delay metric for undelivered packets (H2).
- Counterfactual replay with fixed exogenous noise / common random numbers (causal ML, Monte Carlo) -> keyed RNG design D2 (H1/H3).
- Metamorphic and truncate-and-rebuild testing (software testing) -> oracles for H4, H6.
- Shapley attribution (game theory): considered, NOT adopted for the confirmatory study (risk of null, scope). May appear as future work.
- Each transplant still needs a "to our knowledge" prior-art check before it is claimed (not yet done).

## D03 Scope: Python simulator only; ns-3 is motivation, not evidence
- Decision: all confirmatory work on `src/mlo_sim`. The ns-3 pairing correlations (-0.06, -0.32) are disclosed as motivating observations only.
- Why: fixing pairing in ns-3 needs patching ns-3 (out of scope); mixing simulators would blur provenance.
- Consequence: "generalises" is limited to 3 scales (S2/S4/S8) of one simulator. This goes in Limitations.

## D04 No model judge / no human annotation
- The repo has no LLM component; step 7 (judge validation) is marked not applicable. No human-annotation claim will be made.

## D05 Committed the preregistration (commit 4f4b8f0) despite the earlier no-commit rule
- Why: the Mission 2 brief explicitly requires committing it before results exist; the no-commit rule belonged to Mission 1. Only the prereg files were staged; nothing pushed.

## D06 Amendment 1 (commit d7448bb), before any run
- Found: `OracleScheduler` is not an oracle (no lookahead); duration-truncation cannot detect lookahead.
- Decision: truncate the input (arrival generation) instead; replace the positive control with LeakyGlobal/LeakyLocal schedulers defined in the study code.
- Why amend instead of silently editing: the original file is hashed; amendments are separate hashed files.

## D07 Reimplemented the event loop in a subclass instead of editing src/
- Decision: `StudySimulator` copies `run()`/`_trigger_scheduler()` with RNG plumbing hooks; `src/` untouched.
- Guard: equivalence test requires 'shared' mode to equal `MloSimulator` field-for-field (S2/S4/S8, 3 arms, seeds 1-5).
- Risk: a copied loop can drift from upstream; the equivalence test is the mitigation.

## D08 Keyed RNG indexed by (flow, per-flow index), not global packet_id
- Why: global packet_id shifts when a flow is removed, which would break the H4 intervention (flow 1 would get different noise). Per-flow index keeps flow 1's draws identical with and without flow 2.

## D09 Known gaps in the preregistration, to be closed in Amendment 2 BEFORE any confirmatory run
- LeakyGlobal in Amendment 1 (parity of arrival count) would be detected in only ~50% of seeds, so it cannot meet the >=95/100 bar. Redefined in code as "fastest link for the first half of the packets in the input trace, slowest after".
- H4 did not name the arm: FIFO is primary, FullSASP secondary.
- H3 asked for a paired t p-value but scipy is not installed: use a sign-flip randomisation test (10,000 flips) instead.
- H5 designs: both variants use design D0 (shared RNG), arm FIFO.
- O1 covers all three arm pairs.

## D10 Smoke seeds vs confirmatory seeds
- Smoke/test seeds 1-5 (and 100000+ for property tests). Confirmatory seeds 7000-7099 are used once, after tests pass.

## D11 Pilot on seeds 1-40 found that H1's premise is probably false (disclosed, hypotheses NOT changed)
- Observation: under the shipped shared RNG, arrivals were identical across arms in 120/120 (seed, scale) cells, while delivery schedules differ.
- Decision: keep H1 and its thresholds exactly as preregistered; if the confirmatory run agrees, report H1 as NOT SUPPORTED. Do not rescue it by redefining the metric.
- Why: changing hypotheses after seeing data is the failure that preregistration exists to prevent. A refuted premise is still a publishable finding about how robust paired-seed designs are in this simulator.
- Consequence: the paper's contribution ranking changes. Pairing may become a "robustness/negative" result with E1 (where it breaks); survivor bias (H2), the double loss draw (H5) and the attribution scope (H4) carry more weight. Ranking is decided after the confirmatory run, not before.

## D12 Replaced a test that encoded my wrong expectation with a positive control
- The test "arrivals diverge somewhere under D0" failed because the premise was false. Instead of deleting the check, the oracle's power is now proven by two D0 runs with different loss rates (different draw counts), which must differ.
- All 88 harness tests pass on seeds 1-5.

## D13 Amendment 2 written before any confirmatory run
- Records the pilot, closes the gaps in D09, adds exploratory E1 (fer sweep: where does shared-RNG coupling break).

## D14 Confirmatory pass executed once (seeds 7000-7099, 0 errors); hashes frozen in results/RAW_AND_ANALYSIS.sha256
- Outcomes: H1 NOT supported, H2 NOT material, H3 NOT confirmed, H4 confirmed, H5 confirmed, H6 pass (but release-level test blind to local lookahead).
- Decision: report the refutations as results. Do not redefine H1-H3 to rescue them.
- Decision: H2 "material" rule read conservatively (all three arms must satisfy); moot because none does.

## D15 Paper reframing after the results
- The defensible novelty is no longer "we fixed pairing". It is: a preregistered, oracle-based audit of a simulator and its evaluation protocol in which two invariants hold (pairing, completeness), two fail (loss-draw spec, attribution scope), and one passes with a documented blind spot (causality). Plus a cross-simulator contrast (pairing strength differs between Python and ns-3) if the exploratory re-analysis supports it.
- Why: negative/mixed audit results with exact oracles and controls are honest and checkable; inflating H1-H3 would not survive review.

## D16 Exploratory plan declared before exploratory runs (EXPLORATORY_PLAN.md); study.py got an optional delta_mu parameter after the confirmatory pass
- Safety check done: 88 tests pass and three confirmatory rows were recomputed bit-identically (M and delivered).
- Fresh seeds only (9000-9099, 10000-10999). Exploratory results are labelled exploratory in the paper.

## D17 Exploratory results reshaped the story again (X1-X5), reported as exploratory
- Pairing weakens with asymmetry under BOTH shared and keyed streams, and ns-3 shows weak pairing at higher load with identical traffic -> the cause is trajectory divergence between schedulers, not RNG design. This became contribution 1, tagged confirmatory-negative (H1, H3) plus exploratory (X1, X5).
- The 30-seed vs 1000-seed gain comparison is framed as imprecision (CIs overlap), NOT as an error in the earlier campaign.

## D18 Citation hygiene
- Only references verified by web search in this session are cited (9 entries). Inherited entries that could not be verified (Oliveira 2026, BLEST entry with inconsistent year/venue, ATLAS with blank authors) are excluded and the exclusion is disclosed in the paper.
- Pawlikowski 2002 and an IFIP 2024 TCP-over-MLO paper were looked for but could not be confirmed (title not retrievable / PDF unreadable); not cited.

## D19 All manuscript numbers come from macros generated by paper/make_numbers.py from stored JSON
- Remaining hard-coded literals are design constants (seed ranges, thresholds fixed in the preregistration, test counts, commit hashes).
- Wording was corrected where the draft overstated: "collapses" -> "falls toward zero" (non-monotone at 5 ms); ns-3 "same pattern" -> pairing weak at higher load (it varies with load, not asymmetry).

## D20 Not committed
- Paper files, exploratory outputs and these logs are left uncommitted; the user did not ask for a commit beyond the preregistration. Commits made so far: 4f4b8f0, d7448bb, 25d2ce1, 49437e6 (all local, nothing pushed).

## D21 User asked for conceptual novelty; chose "interventional blocking externality" (Study 2)
- Gap search (limited): MLO literature = traffic allocation, delay models, contention anomalies; MPTCP schedulers (DAPS/BLEST/ECF) = within-flow HoL; no work found attributing receiver-side reorder blocking to causing flows, none applying interventional/Shapley attribution to scheduling delay. NetCause (RCA) and Shapley-for-queueing-fairness (economics) are the nearest, neither covers this.
- Concept: trace-level cross-blocking X is a fixed-schedule counterfactual; the real externality of flow j on flow i is the delay change when j is removed (exact replay via keyed noise); attribution over several flows via Shapley (exact, <=255 coalitions).
- Why this one: it follows from a confirmed Study 1 finding (H4), is testable with exact controls, and a null (X is a good proxy) is also informative.
- Preregistered as Study 2 before any run (PREREGISTRATION_STUDY2.md), fresh seeds 20000-20099, validity checks V1-V4 incl. a low-load control that must give explained fraction in [0.75,1.25].
- Risk acknowledged: it may come out as "X is an adequate proxy" (then the paper becomes a validation of the standard metric) or the low-load control may fail (then the method is reported as not validated).
