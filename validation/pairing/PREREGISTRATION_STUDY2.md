# Preregistration, Study 2: interventional blocking externality in shared-resequencer scheduling

Status: written and hashed BEFORE any Study 2 run. Date: 2026-10-17. Fresh seeds 20000-20099, single pass.
Simulator and harness: `src/mlo_sim` (unmodified) via `validation/pairing/study.py`; new code in `study2.py`.

## 0. Disclosures
- Study 1 (PREREGISTRATION.md + amendments, results committed) is known to the authors. Relevant to this study: in Study 1 / H4, removing a competing flow changed a flow's self-blocking by 54% although trace-level recomputation was exactly invariant. That finding motivates Study 2. No Study 2 quantity has been computed. Smoke seeds 1-5 only before the confirmatory pass.
- Literature gap (limited, non-exhaustive search, October 2026): MLO papers we found study traffic allocation, delay models and contention anomalies; MPTCP schedulers (DAPS, BLEST, ECF) reduce head-of-line blocking within a flow; we found no work that attributes receiver-side reorder blocking to the flows that cause it, and none applying interventional or Shapley attribution to scheduling/reordering delay. This is a claim about our search, not about the literature.
- No model judge and no human annotation are used.

## 1. Concept
- Trace-level cross-blocking X_i (used by the codebase and, to our knowledge, by reordering-delay studies) holds the transmission schedule fixed and measures the extra wait of packet i caused by missing packets of other flows.
- Interventional externality of flow j on flow i: the change in flow i's delay when flow j is removed from the system, with every other flow's arrivals and per-packet channel noise held identical (the keyed design makes this an exact counterfactual replay). It contains reordering, load/queueing and scheduling effects.
- Shapley externality: with players = flows other than i and v_i(T) = D_i(T u {i}) - D_i({i}), phi_{j->i} is the Shapley value of j. Efficiency: sum_j phi_{j->i} = E_i = D_i(N) - D_i({i}).

## 2. Definitions
- D_i(S): mean end-to-end delay of flow i in coalition S (flow i in S), right-censored at the horizon (undelivered packets contribute horizon - arrival time), 300 ms runs, keyed design, arm FIFO unless stated. If flow i has no packet in some coalition the (seed, flow) pair is dropped and counted.
- Trace blame matrix T_{j->i}: over flow i's delivered packets in the full-coalition run, the mean cross-blocking X attributed to the flow j of the packet whose arrival released the blocked packet (read-only receiver observer; self-blocking is not attributed). Sum over j of T_{j->i} = mean X of flow i, excluding forced-advance releases which are counted separately.
- Flow-level totals: B^TR_j = sum_{i != j} T_{j->i}; B^SH_j = sum_{i != j} phi_{j->i}.
- Leave-one-out: LOO_{j->i} = D_i(N) - D_i(N \ {j}).

## 3. Scenarios, arms, seeds
- Primary scale S4 (four flows, weights 1,1,50,50, 200 pkt/s each, links 1.0 and 1.1 ms, fer 0.01), 15 coalitions per seed. Replication scale S8 (eight flows, 100 pkt/s each, weights 1x4, 50x4), 255 coalitions per seed. Scale S2 reported for completeness.
- Validity-control scenario LowLoad: S4 with every rate multiplied by 0.25 and link-2 extra delay 2.0 ms (little queueing, reordering still occurs).
- Arms: FIFO primary. FullSASP and MeanOnly on S4 are secondary (exploratory).
- Seeds 20000-20099 for every run of this study. Cluster = seed. 95% percentile bootstrap, 10,000 resamples, numpy default_rng(20261018). One pass; failed runs are recorded, not replaced.

## 4. Hypotheses, measures, thresholds
H7 (trace-level X does not capture the externality). Explained fraction r = sum over (seed, i) of mean X_i divided by sum over (seed, i) of E_i, primary S4/FIFO. Confirmed if the CI upper bound of r < 0.5. "X is an adequate proxy" if the CI lower bound > 0.8. Otherwise inconclusive. S8 replication uses the same rule.
H8 (trace-level blame misranks flows). Per seed, Kendall tau_b between B^TR and B^SH across the flows; averaged over seeds. Confirmed (misranking) if the CI upper bound < 0.5; "adequate proxy" if the CI lower bound > 0.8. Also reported: fraction of seeds in which argmax_j B^TR = argmax_j B^SH (ties broken to lowest flow id).
H9 (non-additivity). R = sum_{seeds,i} sum_{j != i} LOO_{j->i} / sum_{seeds,i} E_i. Confirmed (externalities not additive) if the CI of R lies entirely outside [0.8, 1.2].

## 5. Validity checks (must pass or Study 2 is reported as invalid)
- V1 efficiency: max over (seed, i) of |sum_j phi_{j->i} - E_i| <= 1e-9 (tests the Shapley code).
- V2 replay: flow i's arrival sequence is identical in every coalition containing it (signature check, 0 mismatches).
- V3 low-load control: in LowLoad/S4/FIFO the explained fraction r must lie in [0.75, 1.25]. If it does not, the method is reported as not validated and H7-H9 are reported with that caveat.
- V4 attribution completeness: for every full-coalition run, sum_j T_{j->i} equals the flow's mean X (excluding forced advances) within 1e-9.

## 6. Exploratory (labelled as such)
Arms FullSASP and MeanOnly; S2; per-flow-weight breakdown of blame; agreement of leave-one-out blame with Shapley blame; any additional threshold.

## 7. Claims NOT made
No claim that a scheduler minimising Shapley externality performs better; no claim for real hardware; no claim beyond this simulator at these scales; the concept is a measurement/attribution contribution, not a new scheduler.
