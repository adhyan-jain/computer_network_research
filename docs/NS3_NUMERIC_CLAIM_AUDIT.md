# NS3 numeric-claim audit

Every ns-3 (and cited Python-historical) number in `paper/main.tex` recomputed independently by `validation/ns3/audit_claims.py` from the raw per-run CSVs (no shared code with `analyze_results.py`).

**55 / 55 claims match their recomputation.**

| Manuscript claim | Manuscript value | Exact source | Independent recomputation | Result |
|---|---|---|---|---|
| Primary: FIFO mean cross wait (ms) | 0.2474 | main_campaign_raw.csv, A2/L2, 30 seeds, cross_wait_ms | 0.2474 | PASS |
| Primary: Full SASP mean cross wait (ms) | 0.2479 | main_campaign_raw.csv, A2/L2, 30 seeds, cross_wait_ms | 0.2479 | PASS |
| Primary: paired difference (ms) | 0.0005 | main_campaign_raw.csv, A2/L2, 30 seeds, cross_wait_ms | 0.0005 | PASS |
| Primary: 95% CI low (ms) | -0.0064 | main_campaign_raw.csv, A2/L2, 30 seeds, cross_wait_ms | -0.0064 | PASS |
| Primary: 95% CI high (ms) | 0.0075 | main_campaign_raw.csv, A2/L2, 30 seeds, cross_wait_ms | 0.0075 | PASS |
| Primary: two-sided paired-t p | 0.880 | main_campaign_raw.csv, A2/L2, 30 seeds, cross_wait_ms | 0.879 | PASS |
| Primary: relative change (%) | -0.20 | main_campaign_raw.csv, A2/L2, 30 seeds, cross_wait_ms | -0.21 | PASS |
| Seed pairing: corr(FIFO, Mean-Only), primary cell | -0.06 | main_campaign_raw.csv, A2/L2, 30 seeds, cross_wait_ms | -0.06 | PASS |
| Seed pairing: corr(FIFO, Full), primary cell | -0.32 | main_campaign_raw.csv, A2/L2, 30 seeds, cross_wait_ms | -0.32 | PASS |
| F1 smallest Holm-adjusted p (Mean-Only vs FIFO, cross wait) | 0.099 | recomputed Holm over 9 cells | 0.099 | PASS |
| F3 smallest Holm-adjusted p (Full vs FIFO, 8 cells) | 0.074 | recomputed Holm over 8 cells | 0.074 | PASS |
| A2/L1 Mean-Only relative change in cross wait (%) | -2.5 | A2/L1 | -2.5 | PASS |
| A2/L1 Full relative change in cross wait (%) | -2.7 | A2/L1 | -2.7 | PASS |
| F2 smallest Holm-adjusted p (Full vs Mean, cross wait) | 0.612 | recomputed Holm | 0.612 | PASS |
| p99: Full vs FIFO, number of cells with Holm p<0.05 | 7 | recomputed F6 | 7 | PASS |
| p99: Mean-Only vs FIFO, number of cells with Holm p<0.05 | 8 | recomputed F5 | 8 | PASS |
| p99: Full vs FIFO, A2/L1 reduction (%) | 17.5 | A2/L1 | 17.5 | PASS |
| p99: Full vs FIFO, A1/L2 reduction (%) | 11.3 | A1/L2 | 11.3 | PASS |
| p99: Full vs FIFO, A2/L2 reduction (%) | 7.4 | A2/L2 | 7.4 | PASS |
| p99: smallest (most negative) Full vs FIFO change (%) | -0.5 | min over cells | -0.5 | PASS |
| p99: Full vs Mean at A0/L2 (%, negative = Full worse) | -3.1 | A0/L2 | -3.1 | PASS |
| p99: Full vs Mean A0/L2 Holm p < 1e-3 | 1 | recomputed F7 | 1 | PASS |
| median: Full vs FIFO best reduction (%) | 12.3 | max over cells | 12.3 | PASS |
| median: Full vs FIFO A2/L1 change (%, negative = worse) | -1.7 | A2/L1 | -1.7 | PASS |
| main: total forced window advances | 0 | sum forced_adv_events | 0 | PASS |
| main: total MAC retries | 0 | sum retries | 0 | PASS |
| main: largest reorder-buffer occupancy in any run | 11 | max buf_occ_max | 11 | PASS |
| main: min packet delivery ratio (%) over all runs | 100.0 | min ls_pdr,bulk_pdr | 100.0 | PASS |
| main: (cell,seed) groups whose bulk goodput differs between arms | 0 | 270 groups | 0 | PASS |
| decision wall time on simulation host: mean (us) | 0.14 | dec_wall_us_mean, predictive arms | 0.14 | PASS |
| decision wall time: smallest run mean (us) | 0.005 | same | 0.005 | PASS |
| decision wall time: largest run mean (us) | 0.44 | same | 0.44 | PASS |
| ablation: Mean-Only vs FIFO minimum reduction (%) | 16.5 | min over 9 cells | 16.5 | PASS |
| ablation: Mean-Only vs FIFO maximum reduction (%) | 20.6 | max over 9 cells | 20.6 | PASS |
| ablation: Full vs FIFO maximum reduction (%) | 42 | max over 9 cells | 42 | PASS |
| ablation: Full vs Mean at w=1, max |difference| (%) | 0.0 | 3 cells | 0.0 | PASS |
| ablation: Full vs Mean (w>=10) minimum gain (%) | 6.3 | min over 6 cells | 6.3 | PASS |
| ablation: Full vs Mean (w>=10) maximum gain (%) | 27.1 | max over 6 cells | 27.1 | PASS |
| ablation: cells (w>=10) with Holm p<0.05 | 6 | recomputed Holm over 9 cells | 6 | PASS |
| ablation: FIFO cross wait identical across w (V1, max spread, ms) | 0.0000 | FIFO ignores w | 0.0000 | PASS |
| ablation: achieved variance ratio V1 | 1.01 | FIFO runs, measured | 1.01 | PASS |
| ablation: achieved variance ratio V2 | 1.29 | FIFO runs, measured | 1.29 | PASS |
| ablation: achieved variance ratio V4 | 2.32 | FIFO runs, measured | 2.32 | PASS |
| calibration: achieved median completion ratio A0 (L2) | 1.00 | FIFO runs | 1.00 | PASS |
| calibration: achieved median completion ratio A1 (L2) | 1.42 | FIFO runs | 1.42 | PASS |
| calibration: achieved median completion ratio A2 (L2) | 2.96 | FIFO runs | 2.96 | PASS |
| Gate 1: events in identical stock/patched trace | 15574 | logs/gate1_ns-3.47*.log | 15574 | PASS |
| Python exp1 delta=0.2: cross-blocking reduction (%) | 11.0 | experiments/results/exp1_link_asymmetry.csv | 11.0 | PASS |
| Python exp1 delta=0.2: p99 delay change (%, negative = SASP worse) | -8.4 | same file | -8.4 | PASS |
| Python exp1 delta=1.5: cross-blocking reduction (%) | 17.7 | experiments/results/exp1_link_asymmetry.csv | 17.7 | PASS |
| Python exp1 delta=1.5: p99 delay change (%, negative = SASP worse) | -12.1 | same file | -12.1 | PASS |
| Python RegimeA: Mean-Only vs FIFO min (%) | 31 | experiments/ablation_phase6/raw_runs.csv | 31 | PASS |
| Python RegimeA: Mean-Only vs FIFO max (%) | 37 | same | 37 | PASS |
| Python RegimeA: Full vs FIFO (w>=10) min (%) | 34 | same | 34 | PASS |
| Python RegimeA: Full vs FIFO (w>=10) max (%) | 39 | same | 39 | PASS |
