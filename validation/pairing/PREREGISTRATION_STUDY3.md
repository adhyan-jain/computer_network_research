# Preregistration, Study 3: boundary, cross-simulator replication and decision utility of interventional externality

Status: written and hashed BEFORE any Study 3 run. Date: 2026-10-17. Software-only (no hardware).
Motivation: reviewer-style weaknesses of Studies 1-2 (single home-grown simulator; main proposition untested; no decision payoff).

## 0. Disclosures
- Known to the authors before this file: all Study 1/2/2b results (committed through 30408d9, plus uncommitted Study 2b outputs). Study 2: with FIFO in S4, trace cross-blocking explained 0.7% of the externality; Study 2b: cross-blocking share 0.6%-36.6% across a load x asymmetry grid.
- ns-3 "with bulk" rows (FIFO arm, scheduler=0, seeds 1-30, 9 cells) already exist in `validation/ns3/results/main_campaign/main_campaign_raw.csv` and were produced before this study; they are reused and tagged pre-existing. The "without bulk" runs are new.
- Smoke seeds 1-3 only before the confirmatory pass. No Study 3 number has been computed.
- No model judge, no human annotation.

## 1. Definitions (as Studies 2/2b)
For victim flow i: E_i = e2e_i(N) - e2e_i({i}); X_i = mean cross-blocking of i in N; means over delivered packets of i. Gap ratio g = |sum E - sum X| / sum E (ratio of sums over seeds and victims).

## 2. H10: when does trace-level equal interventional? (Python, S2, keyed design, seeds 23000-23099, 300 ms)
Conditions: P256 = StaticPinning {flow1->link0, flow2->link1}, win_size 256; P64 = same, win_size 64; F64 = shared FIFO, win_size 64. Solo coalition uses the same mapping/window.
- Instrumentation (read-only): count dispatch stalls (scheduler returns None because next_seq >= win_start + win_size while some queue is non-empty), retry drops, forced window advances.
- V7 exact check: in every (seed) run of P256 with zero dispatch stalls, zero retry drops in both full and solo runs, max_i |E_i - X_i| <= 1e-9. (Prediction of Proposition 3: pinned disjoint links leave Net and S unchanged.)
- H10 confirmed if CI upper bound of g(P256) <= 0.05 AND CI lower bound of g(F64) >= 0.5.
- Reported without threshold: g(P64) with CI; fraction of runs with dispatch stalls under P64 and P256; the share of the P64 gap attributable to stalls (runs with vs without stalls).
- CI: percentile bootstrap over seeds, 10,000 resamples, numpy default_rng(20261020).

## 3. H11: cross-simulator replication in ns-3.47 (patched build used in Mission 1)
Cells: asymmetry A0,A1,A2 x load L0,L1,L2 (conditions.json, frozen), weight ratio 10, FIFO (scheduler 0), seeds 1-30, 10 s runs, warmup 0.5 s, drain 0.3 s. Victim = latency-sensitive (LS) flow; remover = bulk flow.
- With-bulk rows: pre-existing (bulk_mbps from conditions.json). Without-bulk rows: new runs identical except bulkMbps=0.
- E_cell = mean ls_delay_mean_ms(with) - mean(without). X_cell = mean cross_wait_ms(with) (LS cross-blocking per LS packet; forced_wait_ms reported separately and NOT added). r_cell = X_cell / E_cell. Noise is NOT coupled between with/without runs (device streams diverge), so E is a difference of independent means; the seed bootstrap resamples the 30 seeds independently for each arm.
- A cell is "defined" if the CI lower bound of E_cell > 0. Cross-blocking explains little in a cell if the CI upper bound of r_cell < 0.5.
- H11 confirmed (qualitative replication) if >= 5 cells are defined and cross-blocking explains little in >= 2/3 of the defined cells. If fewer than 5 cells are defined the replication is reported as inconclusive. If >= 1/3 of defined cells have CI lower bound of r_cell >= 0.5, H11 is reported as NOT replicated for those cells (heterogeneity).
- V8 exact check: every without-bulk run has bulk_sent = 0 and cross_wait_ms = 0 and passes the runtime audit.
- CI: default_rng(20261021), 10,000 resamples.

## 4. H12: does trace-level blame guide a removal decision as well as Shapley blame? (Python, S4, keyed)
Calibration seeds 22000-22049; evaluation seeds 22050-22099 (disjoint). Arms: FullSASP primary (flows unequal); FIFO secondary (exploratory).
- Calibration: for each candidate flow j, B^TR_j (mean over calibration seeds of the trace blame summed over victims, Study 2 definition) and B^SH_j (mean Shapley blame summed over victims). Policy TR removes argmax B^TR; policy SH removes argmax B^SH (ties to lowest id); policy RAND is the mean over the four flows.
- Evaluation outcome for removing j on a seed: G_j = sum_{i != j} w_i (D_i(N) - D_i(N \ {j})), w_i = flow weight, D right-censored mean e2e. gain(policy) = mean over evaluation seeds of G_j for the chosen j (RAND: mean over j).
- H12 confirmed ("trace blame is a worse guide") if the bootstrap CI (over evaluation seeds, 10,000, default_rng(20261022)) of gain(SH) - gain(TR) has lower bound > 0. If TR and SH choose the same flow the difference is exactly 0 and H12 is reported as not confirmed. Also reported: gain(TR) - gain(RAND), gain(SH) - gain(RAND), the oracle (best j on evaluation seeds) and capture ratios.
- Validity V9: coalition replay signatures (as V2) have zero violations; Shapley efficiency gap <= 1e-9.

## 5. Claims NOT made
No claim that online scheduling by externality improves performance (H12 is an offline, retrospective decision test, not a scheduler); no claim for hardware; ns-3 results are for one LS/bulk pair with unpaired noise.

## 6. Exploratory
FIFO arm in H12; LOO-based policy; stall decomposition of the P64 gap; ns-3 component shares (queue wait, MAC, within-wait); any additional analysis.
