# Amendment 2 to PREREGISTRATION.md (original sha256 abf0c16a...; Amendment 1 sha256 9c04bb72...)

Date: 2026-10-17. Made BEFORE any confirmatory run. Seeds 7000-7099 remain untouched.

## A. Disclosure of pilot observations (seeds 1-40, non-confirmatory)
- With the unmodified shared-RNG design D0, per-flow arrival sequences were IDENTICAL across the three arms in 120 of 120 (seed, scale) cells (S2, S4, S8 x seeds 1-40). Delivery schedules still differ between FIFO and FullSASP (0 of 20 seeds identical on S2).
- The authors saw weighted_cross_blocking (M) of the three arms for S2 seeds 1-8 (large between-seed spread, 0.0 to 0.41; arms visibly co-vary). No pilot correlation, CI or p-value was computed.
- Consequence: H1's premise ("the shared RNG desynchronises arrivals across arms") may be false for this simulator and operating point. Hypotheses and thresholds in the original H1 are NOT changed. If O1 gives 0 mismatches under D0 and delta_rho < 0.30, the paper reports H1 as not supported and states the mechanism (constant number of draws per attempt) as an explanation offered post hoc.

## B. Gaps in the original text closed (decisions fixed before any run)
1. LeakyGlobal (Amendment 1 used arrival-count parity, detectable in ~50% of seeds only) is redefined as in `study.py`: fastest link for the first half of the input trace's packets, slowest for the rest. Pass rule unchanged (>= 95/100 detected).
2. H4 arm: FIFO is primary; FullSASP secondary, reported but not part of the confirmation rule.
3. H3/H1 p-values: scipy is unavailable, so a paired sign-flip randomisation test (10,000 flips, numpy default_rng(20261017)) replaces the paired t p-value. Reported as such.
4. H5: both variants run on design D0, arm FIFO, seeds 7000-7099, S2.
5. O1 is computed for all three arm pairs; the headline is the fraction of (seed, pair) cells with any mismatch.
6. O1 power control (new): two D0 runs with fer 0.01 vs 0.30 must differ in arrival signature in every smoke seed (test `test_o1_oracle_has_power_via_positive_control`).

## C. New exploratory analysis (motivated by the pilot, labelled exploratory, no thresholds)
- E1: robustness of D0 arrival coupling. For fer in {0.01, 0.05, 0.10, 0.20, 0.30} and arm pair FIFO/FullSASP on S2, seeds 7000-7099: fraction of seeds with any arrival mismatch. Purpose: find where the shared-RNG pairing breaks, if anywhere.

## D. Deviations to date
None from the original hypotheses/thresholds. Amendments 1 and 2 are the only changes and were made before any confirmatory data existed.
