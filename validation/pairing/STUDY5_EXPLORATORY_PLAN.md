# Study 5, exploratory plan (declared before the Study 5 run; hashed and committed before any confirmatory or exploratory Study 5 data exist)

Status: amendment to PREREGISTRATION_STUDY5.md (hash 3fff5423...). It adds exploratory analyses only; hypotheses H16-H19, cells, seeds and thresholds are unchanged. Date: 2026-10-17.

## Why this plan exists (disclosure from the smoke runs on seeds 1-5, which are not Study 5 data)
- In smoke runs of the Python simulator (cells like C1 and C4) every blocked packet had exactly one late flow, so releaser blame, Shapley blame and leave-one-out blame coincide there. H18b (Shapley more stable than releaser) may therefore be a tie (equal means, CI lower bound 0) in the simulator cells. That outcome will be reported as "not confirmed".
- On the two other generators (G2, G3) about 40-45% of blocked packets in smoke traces had two or more late flows, i.e. the regime in which the blame rules differ.
- In smoke runs on G2 the mean per-packet L1 change of Shapley blame was slightly LARGER than that of releaser blame (Shapley spreads blame over several flows, each moving with its lateness), so H18b may fail in the average-case direction; the theory (T5) is a worst-case bound, and X13 below measures worst-case sensitivity.
- The vectorised helpers (airport_fast.py) were added after the preregistration commit; equivalence with the frozen airport.py is tested (tests/test_study5.py, 15 tests).

## Exploratory analyses (no pass/fail thresholds; all outcomes reported)
X12 (stability where blame rules differ). Same procedure as H18 (timestamp noise U(-e, e), e in {0.01, 0.1, 1.0} ms; per-packet L1 change of Shapley and releaser blame vectors over packets with X > 0; exact bounds B1/B2 counted) on: simulator cell C5 (S8 FIFO, load 1.0, extra delay 3.0 ms), seeds 26400-26449; generator G2 and generator G3 traces, seeds 26600-26699. Noise streams default_rng(26400 + 1000*5 + 10*(seed-26400) + e_index) for C5 and default_rng(26700 + 1000*g + 10*(seed-26600) + e_index) for G2 (g=1) and G3 (g=2).

X15 (a-priori prediction of cross-blocking from the stochastic closed form). Cells (S4 FIFO, load multiplier, link-2 extra delay): (0.1, 2.0), (0.25, 2.0), (0.5, 3.0); seeds 26800-26899. Seeds 26800-26849 calibrate, seeds 26850-26899 evaluate. Calibration: per-flow empirical distribution of physical delay (arrival at the receiver minus arrival at the transmit queue, all received packets) and flow rates (packets/ms = rate x multiplier / 1000). Prediction (Theorem T7 with empirical delay laws): expected cross-blocking per delivered packet of each victim flow, and the expected airport-Shapley blame of each blocker for each victim. Observation on the evaluation seeds: mean cross-blocking per delivered packet of each victim, and mean airport-Shapley blame per delivered victim packet (full-run traces). Reported: per-cell ratio of sums predicted/observed for cross-blocking and the relative L1 error of the blame matrix, with seed-cluster bootstrap intervals (10,000 resamples, default_rng(20261032)). The stylised model assumes independent delays and sequence numbers in send order, so a poor fit is an acceptable and informative outcome.

X13 (worst-case sensitivity). In every stability analysis (H18 cells, X12 cells) also record, for each rule, the maximum over packets of ||blame' - blame||_1 / ||l' - l||_1 (packets with ||l' - l||_1 > 0). T5 bounds this ratio by 2 for Shapley blame; for the releaser rule it is unbounded. Reported per cell and noise level (descriptive).

## Claims not made
The stochastic model is not claimed to describe the simulator or any real device; X12 and X15 are descriptive and cannot support confirmatory claims.
