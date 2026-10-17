# Preregistration: Measurement validity of simulation-based MLO reordering studies

Status: written and hashed BEFORE any confirmatory run. Date: 2026-10-17.
Simulator under test: `src/mlo_sim/` (Python), unmodified. All new code lives in `validation/pairing/`.
No model-based judge or human annotation is used anywhere in this study. The "validate model-judge labels" step is not applicable.

## 0. Disclosures (prior knowledge at time of writing)
- The authors had read the simulator source (core, channel, simulator, metrics, scheduler interfaces) before writing this file.
- Earlier campaigns (`experiments/ablation_phase6`, seeds 3000-3029) and the ns-3 campaign (`validation/ns3`) exist. In the ns-3 analysis the correlation between arm and FIFO per-seed outcomes was already observed to be weak (-0.06, -0.32). That observation MOTIVATES H1; it is not evidence for the Python simulator and is not reused as a confirmatory result.
- No run of any study below has been executed. Smoke tests use seeds 1-5 only. Confirmatory seeds are 7000-7099 and are used exactly once.

## 1. Implicit invariants (one sentence each)
- I1 (pairing): arms run with the same seed face the same exogenous traffic, so a paired difference isolates the scheduler.
- I2 (completeness): reported delay metrics cover every packet generated, not only delivered ones.
- I3 (loss draw): each transmission attempt consumes exactly one frame-loss draw.
- I4 (attribution): a flow's self-blocking S_i does not depend on whether other flows exist.
- I5 (causality): a scheduler's decisions up to time T do not depend on events after T (positive control: OracleScheduler MUST violate it).

## 2. Designs compared
- D0 shipped: `MloSimulator` unchanged, one shared `random.Random(seed)`.
- D1 naive fix: arrivals drawn from one stream per flow, channel draws still from the shared stream.
- D2 keyed fix: arrivals from per-flow streams; every channel draw keyed by (seed, packet_id, attempt, purpose), so a packet sees identical random numbers whichever link or scheduler serves it.
- Equivalence oracle for the reimplementation: the new simulator class in "shared" mode must reproduce D0 packet-for-packet (all fields) on seeds 1-5 before any confirmatory run.

## 3. Scenarios, arms, seeds
- Link/channel: bw 20 Mbps both, base delays 1.0 ms and 1.1 ms, contention sigma 0.1 ms, fer 0.01, max_retries 7, win_size 64, duration 300 ms.
- Scale S2 (primary): flows (w=1, 400 pkt/s) and (w=50, 400 pkt/s).
- Scale S4: four flows, weights 1,1,50,50, 200 pkt/s each.
- Scale S8: eight flows, weights 1x4 and 50x4, 100 pkt/s each. (Total offered load is 800 pkt/s in all scales.)
- Arms: FIFO = `DefaultFifoScheduler`; FullSASP = `SASPScheduler(True, True)`; MeanOnly = `SASPScheduler(True, False)`.
- Seeds 7000-7099 (100 seeds). No seed is added, dropped or replaced after the first run. A crashed run is reported and counted, not replaced.
- Stopping rule: one pass over the full grid, then analysis. No interim looks.

## 4. Hypotheses, primary measures, thresholds
Cluster unit = seed. All CIs: percentile bootstrap, 10,000 resamples of seeds, numpy `default_rng(20261017)`, 95%. Packet-level pooled quantities are computed within each resample (event-level cluster bootstrap).

H1 (I1 pairing broken in D0). Primary cell: S2, FIFO vs FullSASP, metric M = `weighted_cross_blocking` from `compute_metrics`.
- O1 exact oracle: arrival mismatch rate = fraction of (seed, arm-pair) where the per-flow arrival-time sequences within the horizon differ at any index. Guaranteed 0 for D1 and D2 (validity check; if violated, the implementation is rejected and the study halts).
- P1: delta_rho = rho(D2) - rho(D0), rho = Pearson correlation across seeds of M between the two arms.
- Confirmed if delta_rho >= 0.30 and the CI lower bound > 0. Secondary: variance reduction factor VRF = Var(d_D0)/Var(d_D2) for d = M_FullSASP - M_FIFO per seed; reported with CI; "material" if VRF >= 2.
- Naive-fix comparison: same quantities for D1. D2 is "needed" only if rho(D2) - rho(D1) has CI lower bound > 0.

H2 (I2 survivor bias). Under D2 with no drain (as shipped), S2, each arm.
- P2a: undelivered fraction u = (generated - delivered) / generated, pooled over seeds, cluster bootstrap.
- P2b: relative understatement U = (mean e2e censored - mean e2e delivered-only) / mean e2e delivered-only, censored delay of an undelivered packet = horizon - arr_time (a lower bound).
- Confirmed (material) if u >= 0.02 with CI lower bound >= 0.01. U and ranking-flip (sign of FullSASP - FIFO differs between delivered-only and censored means, per seed fraction) reported without threshold.
- Late-discard count: packets reaching the receiver with sn < win_start (silently dropped by `receive_packet`), counted via a read-only subclass.
- Control: drain mode (arrivals stop at horizon, run until event queue empty) removes exactly the horizon cut. Validity check: with fer = 0, drained undelivered count is exactly 0 in every run.

H3 (consequence for the SASP comparison). Primary cell S2, d = M_FullSASP - M_FIFO per seed.
- P3: CI width of mean(d) under D2 divided by width under D0. Confirmed if ratio <= 0.70. Sign and paired t p-value of mean(d) reported under D0, D1, D2 (descriptive; no claim about SASP superiority is preregistered).

H4 (I4 attribution invariance is trace-level only). S2, flow 1 (w=1) mean self-blocking S_1 per seed, D2.
- Trace control: recompute S_1 from the receiver history after deleting flow 2 packets' arrival records. Guaranteed unchanged (validity check, max abs difference <= 1e-9) because S_i uses only same-flow predecessors.
- Intervention: rerun with flow 2 removed (flow 1 arrivals identical under D2). Dsigma = |S_1(with) - S_1(without)| per seed.
- Violation confirmed if mean Dsigma / mean S_1(with) >= 0.10 with CI lower bound >= 0.05. This tests the README wording ("strictly invariant to whether other flows exist"), not the algebra.

H5 (I3 double loss draw). Instrument `WirelessChannel.sample_frame_loss` call counts per attempt (read-only wrapper).
- O5 exact: draws per attempt. Violation rate = fraction of attempts with draws != 1. Expected 100% (simulate_transmission_attempt draws and discards; completion draws again).
- Effect (threshold fixed now): scenario S2 with Gilbert-Elliott burst_prob 0.02, burst_recovery 0.5, fer 0.01 on both links; mean consecutive-loss run length per link in D0-as-shipped vs a single-draw variant. Material if relative difference >= 0.20 with CI excluding 0.
- Validity check: with burst_prob = 0, observed loss frequency equals fer in both variants within the exact 95% binomial interval pooled over seeds.

H6 (I5 causality). Truncate-and-rebuild: run to T=150 ms and to 300 ms with the same seed under D0; delivered packets with rel_time <= 150 must be field-identical. Expected pass for FIFO, MeanOnly, FullSASP (all seeds). Positive control: OracleScheduler MUST fail on at least one seed; otherwise the oracle test lacks power and H6 is reported as "inconclusive".

## 5. Fix with guarantee and property tests (propositions)
- Prop A (arrival coupling): in D1 and D2, for any scheduler pair and seed, the arrival process is identical. Property-tested on 500 random scenarios (random flow counts 1-8, rates, weights, schedulers, seeds 100000+) with a seeded generator.
- Prop B (censoring bound): the censored mean e2e delay is a lower bound on the drained mean e2e delay for the same packet set, and nondecreasing in the horizon. Property-tested on the same 500 scenarios.
- Prop C (D2 vs D0 bias): not claimed as equivalence. We only check that per-arm metric means under D0 and D2 agree within 2 pooled standard errors (S2, FIFO) as a sanity check on bias.
- Cost: wall-clock per run (median, interquartile range) for D0, D1, D2; "seed-equivalents" = VRF x 100.

## 6. Claims NOT made
- No claim that SASP is superior or inferior in general. No claim about real Wi-Fi 7 hardware. No claim from ns-3 beyond the pre-existing observation in section 0. No human annotation exists. Scales S4 and S8 are replication cells with the same thresholds; they are not independent evidence of a general law.

## 7. Exploratory (labelled as such in the paper)
MeanOnly results, the ranking-flip fraction, any additional metric, any threshold not listed above, and every analysis added after seeing results.

## 8. Output provenance
Raw per-run rows: `validation/pairing/results/raw_*.csv`. Every number in the manuscript must be produced by `validation/pairing/analyze.py` from these files and recorded in `results/analysis_numbers.json`.
