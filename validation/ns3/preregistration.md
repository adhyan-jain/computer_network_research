# Preregistration v2 — ns-3.47 validation of sequence-assignment scheduling under Wi-Fi 7 STR MLO

Protocol id: `PREREG-WIFI7-MLO-HOL-NS3-v2`  ·  written 2026-10-14, **before** any comparative
(Mean-Only / Full-SASP vs FIFO) campaign run. It supersedes `results/invalid_agy_run1/agy_preregistration.md`.
The files this document governs are hash-frozen in `configs/FREEZE.json` (written by `freeze.py`);
`run_campaign.py` refuses to start if any frozen file changed.

## 0. What happened before this document (disclosure)

* A first ns-3 campaign (`results/invalid_agy_run1/`, 1,620 runs) was produced by a previous agent
  session. It is **invalid** and excluded from every analysis: (i) the per-link estimators were never
  updated (the `Notify*` hooks were never connected) and were initialised from the asymmetry *label*;
  (ii) the hook reordered the MAC queue at `PeekNextMpdu` (a peek, not the sequence-commit point) and
  its Mean-Only rule inverted in the wrong direction (sent the latency-sensitive frame over the slower
  link); (iii) all three asymmetry levels used the same constant PHY rate (calibration reported identical
  capacity for A0/A1/A2, runs were 2 s and never saturated); (iv) the primary endpoint was PHY-rx→sink
  time of a packet tag, a proxy that is zero for A-MPDU subframes. Those files are kept only as evidence.
* The implementation in this directory was then rebuilt from a pristine ns-3.47. Before this freeze it
  went through the following **design iterations, driven by engineering defects found on scripted
  scenarios and on smoke seeds 101–104 (never on campaign seeds 1–30, never by a search over outcomes)**:
  1. hook moved to `QosTxop::GetNextMpdu` (the sequence-commit point) and made to use the *original*
     (MLD-address) MPDU, after a crash showed the instance handed to it carries link-specific addresses;
  2. candidate definition changed from "next 2 queue entries" to "first MPDU of each distinct flow in the
     next 8 entries" (makes intra-flow FIFO automatic);
  3. the per-link mean estimator was replaced by a size- and rate-aware model after a scripted test
     showed a frame-size-agnostic estimate made Mean-Only worse than FIFO in a trivial case.
  The smoke seeds showed that the predictive arms leave the primary endpoint roughly unchanged while
  lowering latency-sensitive delay; **this is why latency-sensitive median/p99 delay appear below as
  pre-declared secondary families, and it is disclosed here rather than presented as a surprise.**
* No parameter, estimator constant, weight, load, or analysis choice below was changed after seeing
  any of the 1,620 campaign runs.

## 1. Question, arms, scope of claims

Under IEEE 802.11be STR MLO with two heterogeneous application flows on the **same TID** (hence one
Block Ack reordering context), does a transmitter-side sequence-number assignment policy based on
causal predicted completion times reduce receiver-side *cross-flow* reordering delay?

Arms (identical ns-3 PHY/MAC/EDCA/BA/receiver; same binary; same hook):
* **A. FIFO (native)** — the stock allocation: sequence numbers are assigned in queue order at the
  commit point. The hook is installed but returns no reservation (decisions are computed *in shadow*
  and logged; they are not applied).
* **B. Mean-Only** — at each decision the candidates are ordered by scalar predicted completion time.
  For two candidates it reserves the other candidate first iff `T_head − T_other > 0`.
* **C. Full SASP** — two candidates: pairwise Gaussian threshold rule, reserve the other first iff
  `(T_head − T_other)/σ_pair > u*(w_head, w_other)` with `u*` the root of Theorem 3 (identical Newton
  iteration to `src/mlo_sim/schedulers.py`; unit-tested against it). Three or more candidates: the same
  scalar-mean sort as arm B. **No claim of global multi-frame optimality is made**; the ≥3 path is a
  heuristic whose performance is an empirical question.

What the policy **does not** do: it never chooses a link (native EDCA decides who transmits), never
holds the head frame, never changes the sequence number of an already-committed frame, and never skips
sequence numbers (no holes are created).

## 2. Integration (what is modified in ns-3.47)

`patches/0001` adds `QosTxop::SetSequenceReservationCallback` and calls it from `QosTxop::GetNextMpdu`
for the **initial MPDU of a frame exchange, immediately before `AssignSequenceNumber`** (the point where
`MacTxMiddle` hands out the sequence number). The callback may name other queued, *not yet sequenced*
MPDUs of the same recipient/TID; the MAC assigns them the next sequence numbers first (checking the
originator BA window for the head's final SN) and moves them ahead of the head in the queue so the
other link finds them next. It also adds `WifiMacQueue::MoveBefore` (queue order only).
`patches/0002` adds observation-only callbacks to `RecipientBlockAckAgreement` (insert / release /
forced window advance); the reordering logic is untouched. **Evidence of non-interference**: the
pristine ns-3.47 and the patched ns-3.47 with no hook installed produce a bit-identical 15,574-event
trace (`logs/gate1_*`), and `tests/test_ns3_integration.py::test_patches_reproduce_the_modified_tree`
proves tree == pristine + patches.

## 3. Predictor, candidates, constants (fixed)

3.1 **Candidates** at a decision on link *k* (the link that just won channel access; *j* the other):
the head of the shared TID queue (to be sent now on *k*) plus the first not-yet-sequenced MPDU of each
*other* flow found in the next **8** queue entries, at most **4** candidates. Tagged application MPDUs
only. A decision with fewer than two candidates is a no-op and is counted but not logged.

3.2 **Completion model** (causal): `T(bits) = o_link + bits/R_link`. `R_link` is the configured PHY data
rate (known configuration). `o_link` is learned **only at ACK/BA events** as the EWMA of
`(ACK time − first tx start) − PSDU_bits/R` (α = 0.1, warm-up weight 1/(n+2)); its variance is the EWMA
variance with floor (0.02 ms)². Initial values, identical for all arms and links: `o = 0.15 ms`,
`σ_o = 0.05 ms`. The head completes at `now + T(bits_head)`; candidate *i*≥1 completes at
`b_j + Σ_{m≤i} T(bits_m)` where `b_j = max(now, tx_start_j + T(bits of the PSDU in flight on j))`.
`σ_pair = sqrt(var_k + var_j)`. No oracle quantity, no future arrival, no future retransmission outcome
reaches the policy (tested by `test_12`: appending later traffic leaves earlier decisions unchanged).

3.3 Tie-breaking: strict inequalities; ties keep FIFO. Same sequence-number allocation in all arms.

3.4 Cost of coordination is measured, not assumed zero: `reserve_hold_*` (time a reserved frame waits for
a link), `dec_wall_us_mean` (decision wall-clock, a *simulation-host* number, not a hardware claim).

## 4. Physical conditions (calibrated scheduler-neutral, FIFO only, seeds 9001–9003)

Topology: AP MLD → STA MLD, two STR links, link 0 on 5 GHz and link 1 on 6 GHz, 20 MHz each, EHT, 1 SS,
`ConstantRateWifiManager`, `FixedRssLossModel` per link channel, UDP, TID 0 (AC_BE), A-MPDU ≤ 6000 B,
A-MSDU off, default EDCA, default queue limits (500 packets, 500 ms), BA agreement established
statically. Asymmetry is created only by per-link PHY rate (EHT MCS); variance regimes only by per-link
received power in the MCS-11 error-model transition region. No artificial per-packet delays.

* **Asymmetry** (`calibrate.py` stage 1): fast link 1 = MCS 7; slow link 0 = MCS m0 ∈ 0..7 chosen to minimise
  `|ln(ratio/target)|`, ratio = median per-MPDU completion time slow/fast at bulk 60 Mbps; targets 1.0 / 1.5 / 3.0.
* **Capacity** (stage 2): per condition, FIFO at saturating offered load; `C_ref` = mean total goodput.
  Load levels L0/L1/L2 = 0.30/0.60/0.85 × `C_ref` of *that* condition (capacity differs by condition because the
  conditions differ physically; the same `C_ref` is used for all three arms; arms are never re-calibrated).
  Bulk rate = fraction·C_ref − 0.2 Mbps (latency-sensitive flow).
* **Variance regimes** (stage 3, ablation only): both links MCS 11; fixed-RSS pair scanned on a 0.25 dB grid;
  eligible if `|mean0−mean1| ≤ 0.2 ms`, ≥ 500 completions per link, PDR > 99 %; pick the config whose
  max/min completion-variance ratio is closest (log) to 1, 2, 4 (ties within 0.03 → smaller mean level).
  The ratio is the ratio of the measured per-link variance of per-MPDU completion time, not a configured number.
* The achieved ratios are reported with bootstrap CIs from the 30 FIFO runs of each cell (`analyze_results.py`);
  the calibration output is `configs/conditions.json` (hash in `FREEZE.json`).
* Ablation operating load is fixed at **L2 (0.85 C_ref)** and weight ratios `w_LS/w_bulk ∈ {1, 10, 50}`.

## 5. Experiments (grids locked)

* **Main**: {A0,A1,A2} × {L0,L1,L2} × seeds 1..30 × {FIFO, Mean-Only, Full SASP} = **810 runs**; `w_LS/w_bulk = 10`.
* **Ablation**: {V1,V2,V4} × weights {1,10,50} × seeds 1..30 × 3 arms = **810 runs**, load L2.
* Per run: 10 s simulated; traffic 0.1–9.7 s; metrics over packets *generated* in [0.5, 9.7] s;
  latency-sensitive flow: Poisson, mean 8 ms, 200 B payload; bulk: CBR, 1200 B.
* Randomness: `RngSeed = seed`, `RngRun = 1` for every run. Application random streams (LS arrivals)
  are fixed ids (101, 102) so LS arrival times are **identical across arms**; device/PHY/MAC streams use
  the same stream ids in every arm but their *consumption order* diverges once arms transmit differently
  (e.g. different backoff draws). Consequently arms are matched on seed (a randomised block), **not** a
  perfect common-random-number coupling; the paired analysis is valid because seeds are independent
  replicates, but its variance reduction is not assumed — pairing diagnostics (correlation of arm values
  across seeds) are reported.
* A run is **valid** iff exit status 0 and the runtime audits hold: `audit_sn_changed = audit_sn_dup =
  audit_intra_flow_inv = 0`, `audit_untagged_tx ≤ 20` (ARP only). Invalid runs are preserved under
  `invalid/`, reported, and the campaign is not merged; a fix creates a new, separately identified run set.
  Operating points with unstable queues are reported (PDR/drops), never silently dropped.

## 6. Endpoint definitions (units, denominators, events)

Receiver events come from the *unmodified* `RecipientBlockAckAgreement` via the observation callbacks:
**insert** = MPDU stored in the reordering buffer; **release** = MPDU passed up (in order, or forced by a
window advance / BAR). For a latency-sensitive (LS) MPDU *p*: `wait(p) = release − insert` (ms).

* **PRIMARY — mean cross-flow reordering wait of LS packets** (ms): `(1/|P|) Σ_p cross(p)`, *P* = LS packets
  generated in the metric window and delivered (zeros included). `cross(p) = wait(p)` if `wait(p) > 0`, the
  release was **not** a forced window advance, and the **binding blocker** — the lower-sequence MPDU whose
  insertion (after p's) immediately preceded p's release (last-inserted lower-SN MPDU) — belongs to the
  *bulk* flow; else 0. **This is an inferred attribution, not a directly observable quantity**: the
  directly measured quantity is `total_wait_ms`; the split uses the stated rule. `cross_wait_anybulk_ms`
  (any bulk MPDU among the lower-SN MPDUs inserted during the wait) is a sensitivity version.
  `within_wait_ms` (blocker is LS) and `forced_wait_ms` (released by window advance) complete the partition
  of `total_wait_ms`.
* Secondary: LS one-way delay (generation → sink delivery) median/p95/p99/mean; LS fraction waiting /
  cross-waiting; bulk reorder wait; per-flow goodput (kbps/Mbps, delivered bytes of in-window packets ÷
  window); PDR (delivered ÷ generated, in-window); retries (attempts − unique transmitted MPDUs), NACKs,
  MAC drops; Jain index and minimum of normalised throughput (delivered ÷ offered) for the two flows;
  reorder-buffer occupancy (time-average and max, from insert/release events); forced window advances
  (count, slots skipped); decision counts, reservations applied, decisions where Mean-Only and Full SASP
  would disagree (`dec_full_ne_mean`), reservation hold time, decision wall time.
* "Stall" is claimed only from receiver evidence (`forced_adv_events`), never inferred from delay.

## 7. Statistical analysis plan

Experimental unit = one seed (30 independent replicates per cell and arm); packets within a run are never
treated as replicates. Per cell and comparison the paired difference `d_s = X_arm(s) − X_ref(s)` is analysed.

* **Single primary confirmatory test**: Full SASP vs FIFO on the PRIMARY endpoint in cell **A2 × L2**,
  two-sided paired t-test (df = 29), α = 0.05, 95 % t-interval of the mean difference. Report absolute paired
  effect (ms), relative reduction `100·(1 − mean_SASP/mean_FIFO)` with a paired-bootstrap 95 % CI (10,000
  resamples of seeds, fixed seed 20261014), Cohen's d_z, and a Wilcoxon signed-rank p as sensitivity.
  A non-significant result is reported as such; it is not evidence of equivalence.
* **Secondary families** (Holm step-down within each family; raw and adjusted p reported):
  F1 Mean-Only − FIFO, PRIMARY endpoint, 9 main cells · F2 Full SASP − Mean-Only, PRIMARY endpoint, 9 main
  cells · F3 Full SASP − FIFO, PRIMARY endpoint, the 8 cells other than the confirmatory one ·
  F4 Full SASP − Mean-Only, PRIMARY endpoint, 9 ablation cells ·
  F5 Mean-Only − FIFO, LS p99 delay, 9 cells · F6 Full SASP − FIFO, LS p99 delay, 9 cells ·
  F7 Full SASP − Mean-Only, LS p99 delay, 9 cells · F8 same three contrasts for LS median delay
  (9 cells each, Holm within each contrast). Everything else (throughput, PDR, retries, …) is descriptive
  with 95 % CIs and is not tested for significance.
* **Equivalence** is asserted only with a pre-specified margin: TOST (two one-sided paired t-tests, α = 0.05
  each) for Full SASP vs Mean-Only on the PRIMARY endpoint with margin `±5 % of the cell's FIFO mean`
  (± `0.05·mean_FIFO(cell)`); Holm over the 9 cells (max of the two one-sided p). "Not significantly
  different" is never reported as "equivalent".
* **Interaction (ablation)**: OLS of the per-seed difference (Full − Mean-Only) on variance regime (3) ×
  weight ratio (3), F-tests for the main effects and interaction; descriptive only.
* **Primary-cell sanity**: because a primary test that fails to reject is a possible outcome, the final
  report states the paired effect and CI regardless of the decision.
* Python-simulator results are never pooled with ns-3 results.

## 8. Cross-simulator comparison (fixed before any ns-3 comparative run)

Historical Python results are read-only. Overlap map (the Python study parameterises asymmetry by the
link-mean gap Δ in ms; ns-3 conditions are mapped by the measured slow−fast per-MPDU completion gap of the
FIFO runs):
* Python `experiments/results/exp1_link_asymmetry.csv` (SASP vs DefaultFIFO, `mean_cross_blocking_ms`) at
  Δ = 0.2 ms ↔ ns-3 **A1**, and Δ = 1.5 ms ↔ ns-3 **A2**.
* Python Phase-6 `raw_runs.csv` Regime B (Δμ ≤ 0.2 ms, w = 10; FIFO / Mean-Only / Full SASP) ↔ ns-3
  **ablation** regimes at weight 10.
Compared: sign and relative reduction of Full SASP vs FIFO and Mean-Only vs FIFO on the cross-flow wait,
dependence on asymmetry, and qualitative mechanism (which events produce the wait). Absolute milliseconds
are not expected to agree (different MAC/PHY, aggregation, EDCA, no explicit loads match). Configurations
that do not transfer are listed with the mechanistic reason. Agreement is reported as cross-model
corroboration, never as hardware validation or proof.

## 9. What is NOT claimed, whatever the results

No hardware or firmware deployability (the decision callback time is a simulation-host measurement);
no claim of stock ns-3 supporting SASP (it required the two documented source patches); no global
optimality for ≥ 3 candidates; no claim the receiver is unmodified *as an observed device* beyond
"the reordering logic is unchanged and instrumented read-only"; no legal/novelty/acceptance claims.
