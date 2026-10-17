# Preregistration, Study 4: a single-trace certificate for when trace-level cross-blocking is a faithful externality proxy

Status: written and hashed BEFORE any Study 4 run. Date: 2026-10-17. Software-only.

## 0. Disclosures (what is already known)
- Study 2b (12 Python cells), Study 3/H11 (9 ns-3 cells) and Study 3 H10 are known. In an exploratory look at those 21 cells (post hoc, not preregistered) the observable q = X / e2e_obs (cross-blocking share of the OBSERVED delay of the victim flow, computable from one trace) satisfied r >= q in all 21 cells and had Spearman 0.85 with the explained fraction r = X / E (E = interventional externality). Those 21 cells are the TRAINING set: nothing below is tuned on the held-out cells.
- Proposition (analytic): since the solo delay e2e_solo(i) >= 0, E = e2e(N) - e2e_solo <= e2e(N), so r = X/E >= X/e2e(N) = q whenever E > 0. If a lower bound d_min on any solo delay is known (e.g. the airtime of one frame), r >= X / (e2e(N) - d_min).
- No Study 4 cell has been simulated. Smoke runs: seeds 1-3 only.
- No model judge, no human annotation.

## 1. Held-out cells
Python (keyed design, 300 ms, FIFO, fer 0.01; seeds 25000-25099; victim = every flow; E = e2e_full - e2e_solo over delivered packets, X = full-run cross-blocking):
- P-S4: 4 flows (weights 1,1,50,50; 200 pkt/s each), load multiplier {0.75, 0.35, 0.15} x link-2 extra delay {0.5, 1.0, 3.0} ms = 9 cells.
- P-S8: 8 flows (100 pkt/s each), load multiplier {1.0, 0.5} x extra delay {0.5, 3.0} ms = 4 cells.
ns-3.47 (FIFO, seeds 31-60 for both arms, 10 s runs, same binary and freeze as Study 3): conditions A1 and A2 x bulk load fractions {0.15, 0.45, 0.70} of the calibrated capacity (bulk_mbps = fraction x capacity_mbps from conditions.json, capacity per condition) = 6 cells. With-bulk and without-bulk (bulkMbps = 1e-6, see Study 3 Amendment 1) runs are both new. E_cell = mean ls_delay_mean_ms(with) - mean(without); X_cell = mean cross_wait_ms(with); noise unpaired.
Total: 19 held-out cells.

## 2. Measures
For each cell: r_cell = X_cell / E_cell (ratio of sums over seeds and victims in Python; ratio of means in ns-3), q_cell = X_cell / mean e2e_obs of the victim flow(s) in the full system. A cell is "defined" if E_cell > 0 with the seed-bootstrap CI lower bound > 0 (10,000 resamples, default_rng(20261025)); undefined cells are reported and excluded from H13-H14, but the number excluded must be reported.

## 3. Hypotheses and thresholds
- H13 (certificate holds): r_cell >= q_cell - 1e-9 for every defined Python cell (exact), and for every defined ns-3 cell at the point estimate. Confirmed if there are zero violations among Python cells; ns-3 violations (unpaired noise) are counted and reported. The same check is run with the floor version: Python d_min = 1.69 ms (propagation 1.0 ms + frame airtime at 20 Mbps + overheads, computed from the model constants) and ns-3 d_min = 0.
- H14 (rank diagnostic): across all defined held-out cells pooled, Spearman(q, r) >= 0.70 AND the cell-bootstrap CI lower bound (cells resampled, 10,000, default_rng(20261026)) > 0.40. Also reported separately for the Python and ns-3 cells.
- H15 (practical cut-off, frozen from the training set): classify a cell "trace faithful" (r >= 0.5) if q >= 0.30 (training set: all cells with q >= 0.30 had r >= 0.40; q >= 0.40 had r >= 0.64; threshold chosen before looking at any held-out data). Report precision/recall on held-out cells; no pass/fail threshold, it is a descriptive utility check.

## 4. Validity checks
V10: Python replay signature violations = 0 (as V2) and coalition identity gap |E - (dNet + dS + dX)| <= 1e-9 on a 5% random sample of runs; V11: every ns-3 without-bulk run has bulk_sent = 0 and cross_wait_ms = 0, with-bulk runs pass the runtime audit.

## 5. Claims NOT made
No claim for real hardware or traces; the certificate is a sufficient lower bound and a regime ranking, not an estimator of E; no claim that r is predicted numerically from q.

## 6. Exploratory
Regression of r on q; combining q with load/asymmetry covariates; other victims; the Python training-set tightness of the floor version.
