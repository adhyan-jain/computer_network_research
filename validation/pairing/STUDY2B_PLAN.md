# Study 2b plan (EXPLORATORY; declared after Study 2 results, before any Study 2b run)

Date: 2026-10-17. Fresh seeds 21000-21099. Everything here is exploratory and must be labelled so.

## Why
Study 2's preregistered low-load validity control FAILED (V3: explained fraction 0.10, required 0.75-1.25), so H7-H9 are reported as nominally confirmed but not validated by the control. The control was ill-posed: queueing externality shrinks with load but does not vanish, so the reordering share cannot approach 1 at 25% load. Study 2b replaces the failed control with an exact accounting identity and a load/asymmetry sweep.

## Definitions (delivered packets of the victim flow i)
e2e = Net + S + X per packet, where Net = physical arrival at receiver minus arrival at transmitter queue, S = self-blocking, X = cross-blocking. For coalition C containing i: Dd_i(C) = mean e2e over delivered packets; Net_i(C), S_i(C), X_i(C) the corresponding means.
Externality of the rest of the system on flow i: E_i = Dd_i(N) - Dd_i({i}) = dNet + dS + dX with dNet = Net_i(N) - Net_i({i}), dS = S_i(N) - S_i({i}), dX = X_i(N) - X_i({i}).

## Checks (exact, must hold or Study 2b is invalid)
- V5 identity: |E_i - (dNet + dS + dX)| <= 1e-9 for every (seed, flow, cell).
- V6 solo control: X_i({i}) = 0 exactly (a single flow cannot be cross-blocked) for every (seed, flow, cell).

## Sweep (FIFO, scale S4, full coalition and each single-flow coalition = 5 runs per seed)
- Load multiplier on all rates: 1.0, 0.5, 0.25, 0.1.
- Link-2 extra delay (ms): 0.1, 2.0, 5.0.
- 12 cells x 100 seeds x 5 runs.

## Outputs (no thresholds)
Per cell: shares dNet/E, dS/E, dX/E as ratios of sums with seed-cluster bootstrap CIs (10,000 resamples, default_rng(20261019)); mean E in ms; fraction of seeds with E_i < 0.

## Not claimed
No claim that a scheduler using these quantities performs better; no hardware claim.
