# Study 3: Amendment 1 (H11, made before any ns-3 Study 3 run) and exploratory plan (after the Python results)

Date: 2026-10-17. Preregistration sha256 0cc9b333... (commit ca602dc).

## A. Amendment 1 to H11 (no ns-3 Study 3 data exist yet; one smoke run on seed 1 was inspected)
- Finding: `--bulkMbps=0` hangs the ns-3 binary (the CBR gap is size*8/rate, a division by zero). A single smoke run was killed after >2.5 minutes. No metric was read from it.
- Change: the "without bulk" arm uses `--bulkMbps=1e-6` (first bulk packet would be due after ~9600 s, i.e. never within a 10 s run). Smoke run, seed 1, A2/L2: bulk_sent = 0, bulk_rcvd = 0, cross_wait_ms = 0, runtime 0.4 s. The smoke row is not part of the analysis (seed 1 is re-run in the campaign).
- V8 is changed from "bulk_sent = 0 and cross_wait_ms = 0" to the same condition measured, i.e. required to hold for all 270 runs: bulk_sent = 0 AND cross_wait_ms = 0 AND runtime audit passed. Nothing else in H11 changes.

## B. Reporting of the Python results (post hoc, no thresholds changed)
- V7 (exact check) as preregistered FAILED: max |E - X| over 200 clean P256 rows was 0.0026 ms (> 1e-9). Diagnosis (post hoc, verified on the stored rows): the one offending row has different delivered-packet counts in the full and solo runs (a packet blocked in the reorder buffer at the horizon); the other 199 rows have residual <= 1.2e-15. V7 is reported as failed with this diagnosis, not as passed.
- H10 as preregistered (gap ratio) is confirmed. P64 never stalled in this scenario, so the window-coupling question is untested by the preregistered runs (P64 == P256).
- H12 as preregistered: the gain metric weights victims by flow weight while excluding the removed flow's own delay, which penalises removing heavy flows and does not match what the (unweighted) blame measures; both the trace and Shapley policies fell below the random baseline in both arms. The preregistered rule says "confirmed" for FullSASP (Shapley beats trace) but the result is NOT valid evidence of decision utility, and will be reported that way. This flaw was found after seeing the results.

## C. Exploratory analyses (labelled exploratory; fresh seeds)
- X6 window coupling: S2 pinned {1->0, 2->1}, win_size in {4, 8, 16, 64}, load multiplier 1 and 2, FIFO sequence allocation, seeds 23100-23199. Outputs: fraction of runs with dispatch stalls, gap ratio g with seed-bootstrap CI (default_rng(20261023)). Question: does sequence-window sharing reintroduce a trace/intervention gap for pinned flows?
- X7 aligned decision test: S4, arms FullSASP and FIFO, fresh seeds (calibration 24000-24049, evaluation 24050-24099). Objective = unweighted total delay of the remaining flows, G_j = sum_{i != j} (D_i(N) - D_i(N \ {j})) (aligned with unweighted blame), plus the weighted variant as a sensitivity row. Policies TR (trace blame), SH (Shapley), RAND; oracle best j on evaluation seeds; paired bootstrap CI of differences over evaluation seeds (default_rng(20261024)).
- X8 ns-3 component shares: for each ns-3 cell, the shares of the externality due to LS queue wait, within-wait, cross-wait, forced wait, and the remainder (MAC/air). Descriptive.
