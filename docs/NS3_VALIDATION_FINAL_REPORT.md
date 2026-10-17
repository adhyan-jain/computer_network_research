# ns-3.47 Validation — Final Report

Date: 2026-10-14 · Scope: independent packet-level validation of the SASP / Mean-Only / FIFO sequence-assignment
policies under Wi-Fi 7 STR MLO with shared-TID flows. Everything below is **simulation evidence**; nothing was run on
hardware, firmware or a production MAC. No commit, push, tag or release was made.

## Decision: **CONDITIONAL GO** — only for a bounded paper; the previous headline framing is **NO-GO**

The preregistered confirmatory hypothesis (Full SASP reduces cross-flow reorder wait vs FIFO at strong asymmetry and
high load) was **not supported** (p = 0.88). The earlier Python-simulator headline percentages (16–18 %, up to 96.8 %,
78.1 %) are not corroborated by ns-3 in the asymmetric main grid and have been removed from the abstract. What the evidence
does support is a narrower paper (details in section F). Rationale in section F.

## A. Did actual ns-3 MLO run?

Yes. Pinned **ns-3.47** (archive SHA-256 `8b3adca956c834ea436b915986ab8fd053e90041acae7426895d595aaa3ccc39`, computed
locally; the project site publishes no checksum). Compiler GCC 16.2.1, CMake 4.4.4, Ninja 1.13.2, Python 3.14.7, Linux 7.2.4;
modules `wifi,network,internet,applications,stats,core,mobility,spectrum,propagation,antenna`, optimized profile, examples
and ns-3 tests off (`logs/build_env_*.log`, `logs/configure_*.log`, `logs/build_*.log`). Topology: AP MLD → STA MLD, two STR
links (5 GHz link 0, 6 GHz link 1, 20 MHz, EHT, 1 SS, `ConstantRateWifiManager`, `FixedRssLossModel`), UDP, two flows on TID 0
with one originator BA agreement (static setup helper).

Gate 1 evidence (`src/stock-mlo-baseline.cc`, stock APIs only, every property **computed**, `logs/gate1_ns-3.47*.log`):
NPhys = NLinks = 2 on both MLDs; 6 distinct addresses (MLD ≠ link addresses); BA agreement established for TID 0; 1,620 / 3,407
data PSDUs on links 0 / 1 with **overlapping airtime** (STR); every data MPDU has QoS TID 0 and two flow size classes; PPDUs
received on both links; 5,192 MPDUs delivered; 5,190 MPDU BA acknowledgements observed; 4,096 distinct sequence numbers seen.
The same program on the **pristine** tree and on the **patched tree with no hook installed** yields a bit-identical
15,574-event trace (`logs/gate1_trace_*.csv`, identical SHA-256) ⇒ the patches are inert unless the hook is installed.
*Correction*: the previous session's spike printed "VERIFIED" for items 5–7 as constants; it was replaced.

## B. Did SASP actually control sequence assignment?

Yes, for the order of sequence numbers among queued candidates; **no**, it does not choose links.
* Path traced in ns-3.47 (exact locations): app → UDP/IP → `WifiNetDevice` → `QosTxop` queue → `QosFrameExchangeManager::StartFrameExchange`
  → `QosTxop::PeekNextMpdu` (peek; assigns only a *provisional* SN) → **`QosTxop::GetNextMpdu` → `AssignSequenceNumber` →
  `MacTxMiddle::GetNextSequenceNumberFor` (the commit point)** → aggregation (`MpduAggregator`, which peeks again) → PHY → BA/ACK
  (`AckedMpdu`) → `RecipientBlockAckAgreement::NotifyReceivedMpdu` (reorder buffer) → `MacRxMiddle` → sink.
* Patch `patches/0001-sasp-sequence-reservation-hook.patch` (qos-txop.{h,cc}, wifi-mac-queue.{h,cc}, wifi-mac-queue-container.{h,cc}):
  callback at `GetNextMpdu(initialFrame)` immediately before `AssignSequenceNumber`; named queued, un-sequenced MPDUs of the same
  recipient/TID receive the next SNs first (BA-window check for the head's final SN) and are moved ahead of the head. A stock queue
  scheduler cannot do this: it chooses *which queue/link*, not which MPDU receives the next SN. Patch `0002-recipient-ba-reorder-observer.patch`
  (recipient-block-ack-agreement.{h,cc}) adds read-only observation callbacks; reordering logic unchanged. Apply/reverse: `patch -p1 < p` /
  `patch -p1 -R < p`; `build_ns3.sh` applies strictly and fails otherwise. The earlier attempt hooked `PeekNextMpdu` (a peek) and inverted in the wrong direction (see `preregistration.md` §0).
* Evidence it reached the normal MAC/PHY/receiver paths: 25 regression tests (`validation/ns3/tests`), incl. per-decision
  checks that traced SNs realise the independently computed order (tests 01–04), a **bypass control** (hook removed ⇒ strictly FIFO, hook installed ⇒
  re-ordered; test 10), **causality** (appending future traffic leaves earlier decisions unchanged; test 12), SN invariants incl. **wrap-around**
  over >8,192 MPDUs (test 08) and an assert-enabled (debug) build that raised no NS_ASSERT in any scenario.
* Sequence-number semantics (tested/measured): reservation happens at the commit point; no already-committed MPDU is ever re-sequenced
  (`audit_sn_changed = 0` in all 1,620 runs); no SN duplicates/holes created; retries keep their SN (test 06); aggregation consumes SNs in queue
  order after the head; if only one link/flow is eligible the policy is a no-op and bit-identical to FIFO (test 09); the head is never delayed
  (test 11); cost of coordination = reserved-frame hold time (mean 0.12–0.19 ms in L2 cells) and ≈0.14 µs mean decision time on the simulation host.
* Estimator is causal (updated only at ACK events; initial values from configuration; identical for all arms).

## C. Primary outcome

Confirmatory test (Full SASP vs FIFO, A2 × L2, 30 seeds, mean cross-flow reorder wait of LS packets):
FIFO **0.2474 ms**, Full SASP **0.2479 ms**; paired difference **+0.0005 ms**, 95 % CI **[−0.0064, +0.0075] ms**, p = **0.879**
(Wilcoxon sensitivity in `results/analysis/comparisons.csv`); relative reduction **−0.2 %** (bootstrap CI [−3.0 %, +2.4 %]).
**Decision: H0 not rejected; no reduction detected** (the CI excludes reductions larger than ≈3 %). Across all 9 cells neither
predictive arm reduced the cross wait after Holm (smallest adjusted p 0.099 / 0.074; the most extreme cell A2/L1 shows a 2.5–2.7 % *increase*).
Total reorder wait is also unchanged; no forced window advance occurred in any of 810 runs; peak reorder-buffer occupancy 11 MPDUs.

## D. Does Mean-Only explain the gain?

* **Main grid:** Full SASP and Mean-Only do not differ on the primary endpoint (min Holm p 0.61); 7/9 cells are equivalent within ±5 % of the FIFO mean
  (TOST+Holm), mostly because the arms take (near-)identical decisions. Both lower LS **p99 delay** vs FIFO (Full: 0.5–17.5 %, Holm-significant in 7/9 cells; Mean-Only: 8/9);
  median delay up to −12.3 %, but +1.7 % worse at A2/L1. Full SASP is 3.1 % *worse* than Mean-Only on p99 at A0/L2 (Holm p < 10⁻³). Throughput, PDR (100 %), retries (0) and fairness are identical across arms.
  Mechanism: reserving the LS frame's SN lets the faster link carry it sooner (less queueing/service delay) — **not** a smaller reorder wait.
* **Ablation (near-equal means, L2):** Mean-Only −16.5…−20.6 % vs FIFO; Full SASP up to −42 %. Full vs Mean-Only: identical at w = 1; −6.3…−27.1 % at w ∈ {10, 50}
  (Holm p < 0.05 in all six cells). But the per-seed difference shows **no main effect of variance regime** (p ≈ 1), strong weight and interaction effects (p < 10⁻²⁰), and
  the largest relative gain occurs at variance ratio ≈ 1. ⇒ the measured incremental value is a **priority-weighting** effect; **the experiment does not isolate a benefit of variance awareness.**
  Caveats: achieved variance ratios under load were 1.01 / 1.29 / 2.32 (targets 1/2/4); FIFO and Mean-Only ignore w, so their numbers repeat across w (not independent); a weight-aware
  mean-only arm was not part of the locked design and was not run.

## E. Does the result survive the simulator change?

Mixed (`results/analysis/cross_simulator.csv`, overlap map fixed in `preregistration.md` §8; one documented correction below).
* Asymmetric links: **does not transfer.** Python: cross-blocking −11.0 % (Δ=0.2 ms) / −17.7 % (Δ=1.5 ms) *with* +8.4 % / +12.1 % worse p99. ns-3: no cross-wait reduction, p99 *better* by up to 17.5 %. Plausible mechanisms: native EDCA picks the link, A-MPDU aggregation absorbs queued frames, no link steering (the Python policy also assigns flows to links); this is a hypothesis, not tested.
* Near-equal means: **same direction.** Python Regime A (w = 1/10/50): Mean-Only −31…−37 %, Full −34…−39 % (w≥10), identical at w = 1; ns-3 V1: Mean-Only −20 %, Full −20/−35/−39 %. Python's Full-vs-Mean gap (4–5 %) is much smaller than ns-3's (6–27 %).
* Documented deviation: the preregistration text mapped the ablation to Python "Regime B, w = 10", but Regime B exists only at w = 50; the comparison uses Regime A (Δμ = 0.1 ms, w = 1/10/50) ↔ ns-3 V1.
* Corroboration only — not hardware validation, not proof.

## F. Status of the paper — **CONDITIONAL GO**

Supported claims (what a submission may say): the formal results (pairwise optimality, non-transitivity for N ≥ 3, decomposition); a reproducible patched-ns-3 methodology;
a **null** result for the primary endpoint under asymmetry; significant LS tail-delay improvements with no throughput cost; an ablation whose incremental gain tracks priority weighting; and a documented
failure of the Python asymmetric-link effects to transfer. **Mandatory conditions:** (1) keep the revised framing — no headline reduction percentages, Python results labelled historical;
(2) complete the ATLAS author list from the publisher record (the project inputs gave none; invented authors/pages were removed from the `.bib`); (3) state that the variance-aware refinement's value is *not* established
(a priority-matched mean-only baseline would be a new, separately preregistered experiment); (4) no novelty, patent-clearance, deployability or acceptance claims (the prior-art/patent review is not exhaustive and not a freedom-to-operate opinion);
(5) accept that the contribution is a bounded/negative-forward result and choose the venue accordingly. If these cannot be met, the answer is NO-GO. Not "Q1-ready", not guaranteed novel.

## Experiments (counts)

Main: 3 asymmetry × 3 load × 30 seeds × 3 arms = **810 / 810 completed, 0 invalid**. Ablation: 3 variance regimes × 3 weights × 30 seeds × 3 arms = **810 / 810, 0 invalid**.
Calibration (FIFO only, seeds 9001–9003) reproduced bit-identically with the final binary. Achieved median completion ratios (FIFO, L2): 1.00 / 1.42 / 2.96 (targets 1/1.5/3);
variance ratios in the ablation: 1.01 / 1.29 / 2.32; |Δmean| ≤ 0.05 ms. Seeds 1–30, `RngSeed = seed`, `RngRun = 1`; LS arrival stream 101 and bulk stream 102 identical across arms; device streams 1000+/2000+ same ids but divergent consumption ⇒
**not** common-random-number coupling (arm-vs-FIFO correlation −0.06/−0.32 in the primary cell). Analysis aggregates per seed.

## Deviations, defects found, disclosures

* Previous session's 1,620-run campaign and spike were **invalid** and are quarantined (`validation/ns3/results/invalid_agy_run1/`, `ns-3.47.agy_invalid_tree/`): estimators never updated, wrong hook point and direction, identical PHY for all asymmetry levels, proxy endpoint, hard-coded "VERIFIED".
* Pre-freeze design iterations (hook point, candidate definition, size-aware predictor) were driven by engineering defects on scripted scenarios and smoke seeds 101–104, never by campaign seeds; the LS-delay families were declared because those smoke runs hinted at the effect (disclosed in the preregistration).
* `analyze_results.py` validator tolerance for `bulk_mbps` was loosened 1e-6 → 2e-5 relative (print precision) before any result was viewed; `analyze_results.py` is therefore not byte-identical to the frozen hash (the file hash in `configs/FREEZE.json` predates this one-line change).
* GCC 16 `-Werror` trips on an untouched ns-3 file in the debug profile; the debug tree is configured `--disable-werror` (flag only; sources untouched).
* ARP: scripted tests send one untagged priming packet because ns-3 drops all but 3 packets behind an unresolved ARP entry.

## Remaining limitations (requirements not fully met)

No hardware/firmware evidence; one AP, one station, two links, two flows, constant-rate adaptation, fixed per-link RSS, UDP only (TCP secondary campaign not run); ns-3 archive checksum only locally computed; the cross-flow split of the reorder wait is an inferred attribution (total wait is measured directly);
variance regimes were calibrated at light load and drifted at the ablation load; no priority-matched Mean-Only arm; decision-time numbers are simulation-host, not hardware; the novelty/patent review is not exhaustive.

## Artifacts

* Build/run: `validation/ns3/{fetch_ns3.sh,build_ns3.sh,run_smoke.sh,run_main_campaign.sh,run_threshold_ablation.sh,calibrate.py,freeze.py,run_campaign.py,nsrun.py}`; clean-room rebuild (fresh dir, scripts+patches+archive only) succeeded and reproduces all result columns except the wall-clock timer.
* Patches: `validation/ns3/patches/0001-*.patch`, `0002-*.patch`. Sources: `validation/ns3/src/{sasp-policy.h,sasp-mlo-experiment.cc,stock-mlo-baseline.cc}`.
* Raw data: `validation/ns3/results/{main_campaign,threshold_ablation}/{*_raw.csv,runs/,decisions/*.gz,invalid/}`, calibration `results/calibration/`, conditions `configs/{conditions.json,FREEZE.json}`.
* Analysis: `analyze_results.py`, `cross_simulator.py`, `make_paper_tables.py`, `audit_claims.py` → `results/analysis/*.csv`, `docs/NS3_NUMERIC_CLAIM_AUDIT.md` (55/55 claims verified).
* Tests: `validation/ns3/tests/` (25) + root `tests/` (44). Preregistration: `validation/ns3/preregistration.md`. Manuscript: `paper/main.tex`, `paper/ns3_tables.tex`, `paper/references.bib`, `paper/main.pdf`.
* Hash manifest: `validation/ns3/DELIVERABLES.sha256`. Backups: `backup_20261014_0006_ns3_handoff/` (+ manifest); baseline manifest hash verified (`f8074748…a925485`, 77 + 76 files OK).

## Reproduction

```
cd validation/ns3
./build_ns3.sh && ./build_ns3.sh stock && ./build_ns3.sh debug    # three trees (patched / pristine / assert-enabled)
./run_smoke.sh                                                    # Gate-1 baseline + 3-arm smoke
../../.venv/bin/python calibrate.py && ../../.venv/bin/python freeze.py
./run_main_campaign.sh && ./run_threshold_ablation.sh             # 810 + 810 runs, then analysis
../../.venv/bin/python cross_simulator.py && ../../.venv/bin/python audit_claims.py
cd ../.. && .venv/bin/python -m pytest tests validation/ns3/tests -q
```
