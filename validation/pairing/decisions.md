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

## D05 Committed the preregistration (commit d3b1131) despite the earlier no-commit rule
- Why: the Mission 2 brief explicitly requires committing it before results exist; the no-commit rule belonged to Mission 1. Only the prereg files were staged; nothing pushed.

## D06 Amendment 1 (commit d7eeda6), before any run
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
- Paper files, exploratory outputs and these logs are left uncommitted; the user did not ask for a commit beyond the preregistration. Commits made so far: d3b1131, d7eeda6, f44b970, 3000f3f (all local, nothing pushed).

## D21 User asked for conceptual novelty; chose "interventional blocking externality" (Study 2)
- Gap search (limited): MLO literature = traffic allocation, delay models, contention anomalies; MPTCP schedulers (DAPS/BLEST/ECF) = within-flow HoL; no work found attributing receiver-side reorder blocking to causing flows, none applying interventional/Shapley attribution to scheduling delay. NetCause (RCA) and Shapley-for-queueing-fairness (economics) are the nearest, neither covers this.
- Concept: trace-level cross-blocking X is a fixed-schedule counterfactual; the real externality of flow j on flow i is the delay change when j is removed (exact replay via keyed noise); attribution over several flows via Shapley (exact, <=255 coalitions).
- Why this one: it follows from a confirmed Study 1 finding (H4), is testable with exact controls, and a null (X is a good proxy) is also informative.
- Preregistered as Study 2 before any run (PREREGISTRATION_STUDY2.md), fresh seeds 20000-20099, validity checks V1-V4 incl. a low-load control that must give explained fraction in [0.75,1.25].
- Risk acknowledged: it may come out as "X is an adequate proxy" (then the paper becomes a validation of the standard metric) or the low-load control may fail (then the method is reported as not validated).

## D22 Study 2 executed once (seeds 20000-20099, 0 errors). V3 low-load control FAILED.
- Nominal verdicts: H7 explained fraction 0.7% (S4 and S8), H8 Kendall tau 0.18/0.16, H9 non-additivity R 1.90/2.69 -> all "confirmed" by their preregistered rules.
- V1 (efficiency gap 0.0), V2 (0 replay violations), V4 (completeness gap 0.0) passed. V3 required explained fraction in [0.75,1.25] at LowLoad; observed 0.10 -> per the preregistration the method is "not validated" by that control and H7-H9 are reported with that caveat.
- Diagnosis (post hoc): the control was ill-posed. I assumed queueing would vanish at 25% load, but queueing externality shrinks with load without vanishing (mean E 0.39 ms vs mean X 0.039 ms). The failure is NOT hidden or redefined.
- Decision: do not rescue by editing V3. Add an exploratory Study 2b with an exact accounting identity E = dNet + dS + dX (checks V5, V6) and a load x asymmetry sweep, declared in STUDY2B_PLAN.md before running.
- Novelty caveat recorded: R > 1 (marginal > average externality) is classic queueing convexity (Naor-style); the non-additivity itself is not claimed as new.

## D23 Study 2b (exploratory) validated the accounting identity and explained the V3 failure
- V5 identity gap 1.4e-14, V6 solo cross-blocking exactly 0. Cross-blocking share of the externality: 0.6%-36.6% over 12 (load x asymmetry) cells, median 8.0%, <15% in 10/12; queueing/service 60-99%.
- Interpretation: V3 failed because queueing externality never vanishes; the method itself passed its exact checks.

## D24 Paper rewritten around the externality concept (main.tex); audit-only draft kept as main_audit_only.tex
- Lead contribution = concept + exact accounting; the Study 1 audit is supporting. V3 failure is stated in the abstract, results and limitations.
- Honesty edits: H8 under FIFO is a weak test (flows exchangeable), so the SASP result (flows unequal) is reported as the more informative, exploratory evidence; non-additivity credited to Naor-style queueing convexity, not claimed as new; Proposition 3 (pinned disjoint links) marked untested.
- Verified references added: Naor 1969 (Econometrica 37(1):15-24), Shapley 1953 (Annals of Math Studies 28, pp. 307-317).
- Not committed: paper/, Study 2b outputs, logs. Commits so far: d3b1131, d7eeda6, f44b970, 3000f3f, 477a64a, cce5dce (local, nothing pushed).

## D25 User asked to hunt for stronger, software-only foundations; Study 3 preregistered before any run (PREREGISTRATION_STUDY3.md)
- Targets the three main reviewer objections: (H10) test the untested pinned-link proposition, including the window-coupling subtlety I noticed (static pinning still shares the sequence-number window, so dispatch can stall and break exactness; hence P256 vs P64); (H11) replicate the externality in ns-3.47 (community simulator) with with/without-bulk runs, reusing pre-existing with-bulk rows; (H12) offline decision-utility test with disjoint calibration/evaluation seeds.
- ns-3 noise is not coupled between with/without runs, so E is a difference of independent means (wider CIs); stated in the prereg.
- Honest risk: H11 may be heterogeneous or inconclusive; H12 may be a tie (TR and SH choose the same flow). All outcomes will be reported.

## D26 Study 3 Python results (seeds 23000-23099, 22000-22099), 0 errors; hashes in results/STUDY3_PY_RAW.sha256
- H10 confirmed: gap ratio pinned P256 = 0.13% (CI upper 0.42%) vs shared FIFO 99.5%. BUT preregistered exact check V7 FAILED (max residual 0.0026 ms); diagnosis verified post hoc: 1 of 200 rows had different delivered counts (packet held in reorder buffer at the horizon); other 199 rows <= 1.2e-15. Reported as failed-with-diagnosis.
- P64 never stalled, so window coupling was not exercised by the preregistered runs -> exploratory X6 with small windows.
- H12 formally "confirmed" for FullSASP (Shapley beats trace, CI [3.2, 9.2]) but I judge it INVALID as decision-utility evidence: the preregistered gain metric weights victims by flow weight while excluding the removed flow, so removing heavy flows is penalised; both policies are below random, oracle flow differs. This design flaw was found AFTER seeing results; stated in the amendment/plan and will be in the paper. Aligned fresh-seed re-test is exploratory X7.
- ns-3 bulkMbps=0 hangs the binary (CBR gap = size*8/rate -> division by zero). Amendment: use 1e-6 Mbps (bulk_sent observed 0). Amendment written before any ns-3 Study 3 run.

## D27 Study 3 outcomes (ns-3 and exploratory) and what they changed
- H11 (ns-3, 270 new no-bulk runs, 0 errors): NOT replicated / heterogeneous. Cross-blocking explains 4%-88% of the bulk->LS externality (A0/L0 87%, A2/L0 88%, A2/L1 64%; A0/L1 4%, A0/L2 9%). So "trace cross-blocking is small" does NOT generalise; the share is regime-dependent. This corrects my earlier headline (Study 2: 0.7% at heavy load). Paper claim must be: a trace-level metric is a regime-dependent proxy.
- X6: window coupling for pinned flows is rare (stalls in 0-3% of runs); residual gaps come mostly from delivered-set composition at the horizon.
- X7 (fresh seeds, aligned unweighted objective): in FullSASP trace and Shapley blame pick the same flow (no difference); in FIFO the difference SH-TR is -0.09 (CI includes 0). So NO evidence that Shapley beats trace blame for a top-1 removal decision. The earlier H12 'confirmed' was an artifact of a misaligned objective and unstable calibration ranking (flow 3 vs 4).
- Post hoc observation (21 training cells): observable q = X/e2e_obs lower-bounds the explained fraction r (analytic: E <= e2e) and has Spearman 0.85 with r. Preregistered Study 4 to validate on 19 held-out cells (13 Python, 6 ns-3), with cut-off q>=0.30 frozen from the training cells.

## D28 Study 4 outcomes (single pass, 0 errors; hashes in results/STUDY4_RAW.sha256)
- H13 CONFIRMED: r >= q in 13/13 Python cells (exact, zero violations; also the d_min = 1.69 ms floor version, min solo delay >= d_min in all cells) and 6/6 ns-3 cells at the point estimate. All 19 cells were "defined" (E > 0, CI lower > 0), so nothing was excluded.
- H14 CONFIRMED but with a caveat I will state: pooled Spearman(q, r) = 0.928, cell-bootstrap CI [0.777, 0.979] (n=19). Within platform it is 0.852 (Python, n=13) and 0.600 (ns-3, n=6, no CI preregistered); the pooled value is helped by the Python cells having uniformly low q and r, the ns-3 cells high.
- H15 descriptive: cut-off q >= 0.30 gives precision 1.0 (2/2), recall 0.5 (2 of 4 cells with r >= 0.5 found). Only 4 positives, so no strong claim.
- Observation to report, not hide: in two ns-3 cells (A1/F0.15, A2/F0.15) r > 1 (1.22, 1.27): the cross-wait mean exceeds the unpaired-noise interventional delay difference, so r is not a bounded fraction in ns-3 (noise on E is large when E is ~0.01-0.06 ms). Certificate (r >= q) is unaffected; r as a "share" is not.
- Exploratory (not preregistered): OLS r on q slope 2.55, intercept 0.05, R^2 0.57. The certificate is a lower bound and a ranking, not a numeric predictor.
- V10 pass (0 replay-signature violations in 6,800 rows; identity gap max 5.3e-15 on a 340-row sample, 7.1e-15 on all rows; the 5% sample seed 20261027 was my choice, the prereg did not fix it). 1,199 rows have n_full != n_solo (horizon composition) yet the identity still holds because each side's averages are internally exact.
- V11 pass after a script fix: my first analysis run flagged audit_untagged_tx = 2 in every run as a violation; the frozen Mission 1 audit rule is untagged <= 20 (ARP priming), and the same value 2 appears in all 810 Mission 1 runs and all 270 Study 3 runs. Fixed the check to the frozen rule; the outcome was not changed by the fix (counters sn_changed, intra_flow_inv, sn_dup are 0 in all 360 runs).

## D29 Paper v3 written around the certificate and regime dependence; built and checked
- Title/abstract/contributions rewritten: lead = concept + exact identity, then the single-trace certificate (Proposition 4, confirmed on 19 held-out cells), then regime dependence, then the pinned-link boundary, then null/negative results. The old headline "cross-blocking is small" is demoted to "true at one heavy-load Python point, false in several ns-3 cells".
- Added Studies 3 and 4 with every number via make_numbers.py macros (tab_s3_h11.tex, tab_s4.tex, fig_cert.pdf generated from JSON). Macro names cannot contain digits (a build error FourOLSR2 was renamed FourOLSRsq).
- Disclosures kept in the text: V3 failed (Study 2), V7 failed with single-row diagnosis (Study 3), H12 flawed objective found after results and not used as evidence, X7 null, V11 first-run rule mismatch fixed to frozen audit, pooled-rho caveat (within platform 0.85 / 0.60), r > 1 in two ns-3 cells, ns-3 binary is project-patched (second implementation, not independent), 21-cell training set examined before Study 4.
- Claims explicitly NOT made: decision utility of Shapley, numerical prediction of r from q, hardware transfer.
- v2 manuscript kept as paper/main_v2_before_study34.tex. New tests/test_study4.py (smoke seeds only); full suite 101 passed. Paper is not committed (user has not asked).

## D30 User asked for a conceptual/theory paper; found a structural theory and preregistered Study 5 (commits aba3a8e, d8ebc33; results below)
- Novelty hunt: the reorder-buffer release law is a running maximum (classical resequencing), so cross-flow blocking of a packet is the MAX of the 'lateness' of the other flows' earlier packets: each packet is an AIRPORT GAME (Littlechild-Owen 1973). That gives (T3) a closed-form, exact, replay-free Shapley blame O(m log m) per packet (replay needs 2^(m-1) runs), (T4) leave-one-out masking (only the top blocker is charged) and sub-additivity, (T5) an L1-Lipschitz stability bound (releaser rule has none), (T6) reordering is sub-additive while FIFO M/G/1 queueing is super-additive (so the interventional non-additivity R=1.9 comes from queueing), (T7) closed-form expected blame for Poisson flows with independent path delays. Dubey 1982 gives the axiomatic uniqueness of Shapley on airport games. Verified references: Littlechild-Owen, Dubey, Baccelli-Gelenbe-Plateau, Han-Makowski, Ghorbani-Zou, Ma et al.
- Honest pre-run observation: in smoke runs all blocked packets in the simulator had a single late flow, so the three blame rules coincide there; this changed the plan (X12 on generators where several flows are late, X13 worst-case sensitivity).
- Study 5 outcomes (1,608 jobs, 0 errors, 73 s, hashes in results/STUDY5_RAW.sha256): H16 CONFIRMED (every exact oracle <= 1e-13 over 700 runs/7 cells incl. two non-Wi-Fi generators; zero forced advances in any run; the real receiver on a truncated trace equals the airport formula exactly). H17a CONFIRMED (R_Q 1.89 [1.85,1.93] and 1.74 [1.67,1.80]); replay R_X 0.77 [0.60,0.94] and 0.98 [0.92,1.03] (second CI includes 1). H18a CONFIRMED (0 violations of the Lipschitz bound) but H18b NOT confirmed: in simulator cells Shapley and releaser changes are identical (single late flow), on generators Shapley is not more stable on average (differences negative or CI includes 0); only the worst case differs (max ratio change/lateness-change: Shapley 1.0, bound 2; releaser up to 348). H19 NOT confirmed as preregistered: every MC z <= 2.7 and efficiency 9e-10, but the preregistered quadrature-convergence criterion (1e-6) failed for P6 (7e-4, atom in the deterministic delay) and P7 (1.4e-5); post hoc refinement script posthoc_h19_refine.py (labelled post hoc) checks convergence.
- X15 (exploratory): the stochastic closed form predicts cross-blocking from rates and delay laws within about +19% to +33% (ratios 1.19 [0.61,3.37], 1.33 [1.16,1.57], 1.23 [1.16,1.29]); blame matrix relative L1 error 0.81, 0.37, 0.23.
- ns-3 applicability (descriptive, existing data): forced_adv_events = 0 in all 810 + 270 + 360 ns-3 runs, so the ideal-resequencer regime also holds there. Python: 0 forced advances in all 1,700+ Study 5 simulator runs.

## D31 Theory paper written (paper/theory/main_theory.tex, 11 pages) and what it does and does not claim
- Positioning: resequencing blame as an airport game (Theorems 1-6), with the bridge propositions from the measurement studies restated with proofs. New verified references: Maniquet 2003 (J. Econ. Theory 109(1):90-103), Mitra-Gupta-Hemachandra (VALUETOOLS 2022, Springer 2023), Owen 1972 (Manag. Sci. 18:64-79). A search found no prior use of the airport game for resequencing or head-of-line blame (limited search, stated as such).
- Corrections made while writing: replay count is 2^m coalitions per victim (not 2^(m-1)); the leave-one-out shortfall is EXACTLY the second-largest lateness (ties included); the stability claim is worst-case only (H18b not confirmed: equal changes in simulator cells, Shapley not better on average on generators).
- Disclosed in the paper: H18b not confirmed; H19 not confirmed as preregistered (quadrature criterion), with a labelled post hoc refinement (posthoc_h19_refine.py: P7 converges to 4.3e-7, P6 slowly because of the atom, z unaffected); simulator blocked packets are 95-100% single-late so the three blame rules coincide there; ns-3 enters only through forced-advance counts (0 of 1,440 runs) and aggregate bridge results; the ideal-resequencer assumption (no forced advances/timeouts) is the main open theoretical question; reviewers may call the structure theorem short.
- Strength assessment given to the user: stronger conceptual core than the measurement paper (a structural theorem with exact consequences), but still a modest-depth theory paper whose practical payoff is bounded (rules coincide in the simulator regimes) and which is simulation-only.

## D32 Study 6 (finite window + hold timer, ns-3 reorder buffer as second implementation) - preregistered 817ad6e, results below (1,120 jobs, 0 errors, 3,207 s; hashes in results/STUDY6_RAW.sha256)
- Trigger: an adversarial review supplied by the user argued the ideal-resequencer theory is not a theory of the deployed receiver and that the only validation was our own simulator. We agreed on both points, closed them with a preregistered study, and also softened claims (see D33).
- Theory added: T8 window+timer release law R_k = max_{j<=k} min(A_j, F_j, T_j) (F_j window-forced time, T_j timer-forced time) with delivered-set characterisation; T9 airport structure on effective arrivals; T10 bound |l~ - l| <= delta_k and ||phi~ - phi||_1 <= 2 m delta_k; T11 per-packet applicability certificate (soundness: rejection implies an earlier resolution before physical arrival).
- Outcomes: H20 CONFIRMED (900 traces, 18 configs W x tau x loss, 249,142 packets, 16,554 forced events, max error 0, zero delivered-set mismatches, 96.8% of traces with >= 1 forced event; the only low-event config is W=64/no timer/no loss at 42%, as expected). H21a CONFIRMED (airport oracles on effective arrivals, max error 5.7e-14), H21b CONFIRMED (T10 bounds, zero violations, max ratio 0.18 of the bound), H21c CONFIRMED (zero false rejections by the certificate). H22 CONFIRMED (ns-3 own reorder buffer, 160 scripted 3-flow runs, 3,253,034 packets checked, 873,950 blocked, release-law error exactly 0, no forced advances, no SN duplicates). H23 CONFIRMED (our unmodified receiver reproduces ns-3 release times exactly; oracles exact). H24 CONFIRMED (trace reproduces ns-3's own cross_wait/within_wait columns to 5e-10).
- Honest observations: the applicability certificate is conservative (44% of delivered packets certified overall; 82,184 packets certified although an earlier slot had been skipped, because the cut did not bind). In ns-3 only 1.8%-16% of blocked packets have two or more late flows (higher at load scale 2.5), so the three blame rules still coincide for most blocked packets there.
- D2 (definition gap I found myself): ns-3's cross_wait_ms charges the whole wait to a cross-flow binding blocker, pure X excludes the self part. On the main-campaign configuration (60 runs) pure X / ns-3 cross wait is >= 98.8% in every cell (overall printed in the analysis), so the ns-3 'X' used in Studies 3-4 overstated pure X by at most ~1.2%; those conclusions are unaffected.

## D33 Theory paper v2 and the full audit (AUDIT_REPORT.md)
- Adversarial-review points adopted: precise game definition (players, outcome, coalition), minimal LOO/releaser/Shapley example, LOO shortfall stated as exactly the second-largest lateness, additivity claims scoped by set function, stability bound named with its constant (2, independent of load, flows, window) and its scope, Poisson closed form demoted to a validation baseline, "ideal resequencer" renamed "reference receiver", forced release (window + hold timer) moved into the main line with bounded error and a certificate, ns-3 reorder buffer as a second implementation, claims softened (no deployment-level robustness, no hardware, no ns-3 BAR-driven release, no duplicates).
- Not adopted / not done: comparison against standard reordering metrics (RFC reorder density, buffer-occupancy density); an external public trace (none available); duplicates and wraparound stress in the certificate test (wraparound handled in the ns-3 traces; duplicates untested).
- Audit outcome: all hash lists, preregistration ordering and byte-identity checks pass; analyses reproduce byte-for-byte; independent recomputation matches; three self-inflicted problems found and fixed (wording slip, unscoped D2 claim, uncommitted Study 2b results and scripts).
