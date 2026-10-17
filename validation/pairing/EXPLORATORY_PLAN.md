# Exploratory plan (declared after the confirmatory pass, before any exploratory run)

Date: 2026-10-17. Everything below is EXPLORATORY: it was motivated by the confirmatory results, uses fresh seeds, has no preregistered thresholds, and must be labelled exploratory in the paper. Confirmatory raw/analysis hashes are in `results/RAW_AND_ANALYSIS.sha256` and were written before this file.

## What the confirmatory pass showed (motivation)
H1 not supported (0/900 arrival mismatches in D0, delta_rho(S2) = 0.06, CI [-0.16, 0.23]); H2 not material (undelivered 1.2%, no late discards, no retry drops); H3 not confirmed (CI width ratios 0.88, 1.14, 0.85); H4 confirmed (S_1 shifts by 54% when flow 2 is removed; trace control exactly 0); H5 confirmed (100% of attempts draw twice; burst run length -29%); H6 passes with LeakyGlobal caught 100/100 but LeakyLocal caught 0/100.

## Exploratory analyses (fresh seeds only; seeds 7000-7099 are not reused)
- X1 asymmetry sweep: second link base delay = 1.0 + delta_mu ms, delta_mu in {0.1, 0.5, 1, 2, 5}; FIFO vs FullSASP; designs shared and keyed; seeds 9000-9099. Outputs: fraction of seeds with arrival mismatch (shared), rho across seeds per design. Question: does shared-RNG pairing survive link asymmetry?
- X2 effect of the double draw on headline metrics: S2 with Gilbert-Elliott bursts (0.02 / 0.5, fer 0.01), keyed design, shipped vs single_draw, FIFO and FullSASP, seeds 9000-9099. Outputs: M, censored mean e2e, undelivered fraction, retry drops per run.
- X3 decision-level causality: repeat H6 comparing dispatch records (packet_id, link_id, seq_num, disp_time) with disp_time <= 150 ms instead of released packets; five arms; seeds 9000-9099. Question: does a decision-level comparison detect LeakyLocal where the release-level one did not?
- X4 SASP effect size, worked example: keyed design, S2, FIFO vs FullSASP, seeds 10000-10999 (1000 seeds): mean(d), bootstrap CI, sign-flip p; same seeds under the shared design for comparison.
- X5 cross-simulator pairing (re-analysis of PRE-EXISTING ns-3 results, no new ns-3 runs): per (cond, load) cell, the across-seed correlation of the primary metric between FIFO and FullSASP, and the fraction of (cell, seed) triples whose offered traffic counts (ls_sent, bulk_sent) are identical across arms.

## Not done / out of scope
No ns-3 code changes, no new ns-3 runs, no Shapley attribution, no model judge.

## Code change disclosure
`study.py` receives one new optional parameter (`delta_mu`, default 0.1 reproduces the confirmatory configuration) after the confirmatory pass. The 88 harness tests are rerun, and three confirmatory rows are recomputed and compared with the stored CSV, before any exploratory number is produced.
