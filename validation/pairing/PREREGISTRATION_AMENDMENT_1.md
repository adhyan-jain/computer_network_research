# Amendment 1 to PREREGISTRATION.md (sha256 abf0c16a044bf13f3faeb835f88eeaabd303ebb22300f31f782170a92c607b18)

Date: 2026-10-17. Made BEFORE any confirmatory run (seeds 7000-7099 unused; no results exist for any hypothesis). Only H6 changes. All other sections stand unchanged.

## Reason (found while reading `src/mlo_sim/schedulers.py` to write the test harness)
1. `OracleScheduler` (schedulers.py, class docstring: "Offline arrival-sorted lower bound: sorts frames by physical completion") does not use future information. Its `schedule` picks the max-weight non-empty queue and the link with the smallest `estimated_mean_ms`. It cannot violate causality, so it is not a valid positive control. This is itself reported as a finding (name/behaviour mismatch), not as a result of H6.
2. Truncating by `duration_ms` cannot detect lookahead: `run()` only breaks its loop at the horizon, so every event before the horizon is identical in a short and a long run. Truncation must act on the INPUT: arrivals after T must not exist.

## Replacement for H6
- Run A: arrivals generated only up to T = 150 ms (the next inter-arrival draw is still consumed and then discarded, so streams stay aligned); event loop stops at T.
- Run B: arrivals generated up to 300 ms; event loop stops at T.
- Oracle: packets with rel_time <= T must be field-identical between A and B. Uses design D2 (arrivals from per-flow streams).
- Arms under test: FIFO, FullSASP, MeanOnly. Expected: 0 violating seeds out of 100.
- Positive controls (defined in `validation/pairing/study.py`, never used outside H6):
  - LeakyGlobal: chooses the link by the parity of the total number of arrivals in the whole input trace. Must be detected in >= 95 of 100 seeds, otherwise the test is declared underpowered and H6 is reported as inconclusive.
  - LeakyLocal: holds the idle link if any arrival exists in the next 1.0 ms of the full trace. Its detection rate is a sensitivity estimate, reported without threshold (exploratory).
- Seeds: 7000-7099, same pass as the rest of the study. The decision rule "H6 passes" = shipped schedulers 0/100 violations AND LeakyGlobal >= 95/100.
