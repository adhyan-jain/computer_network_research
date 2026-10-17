#!/usr/bin/env python3
"""calibrate.py - scheduler-neutral calibration (FIFO arm ONLY, seeds 9001-9003).

Nothing in this script ever runs a predictive arm, so no scheduler outcome can influence the
selection of physical parameters. Selection rules are fixed in preregistration.md section 4.

Stages
  1. asymmetry: fast link 1 = EHT MCS7/20 MHz; slow link 0 = EHT MCS m0 in 0..7. Ratio of median
     per-MPDU completion time (slow/fast) at a fixed reference load (bulk 60 Mbps). Pick, for each
     target in {1.0, 1.5, 3.0}, the m0 minimising |ln(ratio/target)|.
  2. capacity: per condition, FIFO at saturating offered load; C_ref = mean total goodput.
  3. variance regimes (ablation): both links EHT MCS11/20 MHz, fixed RSS pair scanned on a 0.25 dB
     grid; eligible = |mean0-mean1| <= 0.2 ms, >=500 completions/link, PDR>99%. Pick for each
     target variance ratio in {1,2,4} the config minimising |ln(vr/target)| (ties within 0.03 broken
     by smaller max link mean).
  4. validation: FIFO at every main-grid cell (3 asymmetry x 3 load) reporting achieved ratios.
Outputs: results/calibration/*.csv and configs/conditions.json (frozen before the campaign).
"""
import csv
import json
import math
import statistics as st
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import nsrun

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "calibration"
OUT.mkdir(parents=True, exist_ok=True)
CAL_SEEDS = (9001, 9002, 9003)
WORKERS = 14
FAST_MCS = 7
LS_MBPS = 200 * 8 * (1000.0 / 8.0) / 1e6  # 200 B payload, mean 8 ms Poisson = 0.2 Mbps
LOAD_FRACTIONS = {"L0": 0.30, "L1": 0.60, "L2": 0.85}
TARGETS = {"A0": 1.0, "A1": 1.5, "A2": 3.0}
VAR_TARGETS = {"V1": 1.0, "V2": 2.0, "V4": 4.0}


def pmap(jobs, profile="optimized"):
    with ThreadPoolExecutor(WORKERS) as ex:
        return list(ex.map(lambda a: nsrun.run(a, profile=profile), jobs))


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def mean_of(rr, k):
    return st.mean(r[k] for r in rr)


def phys(p):
    return dict(mcs0=p["mcs0"], mcs1=p["mcs1"], width0=p["width0"], width1=p["width1"],
                rss0=p["rss0"], rss1=p["rss1"])


def stage1():
    jobs = [
        dict(simTime=4, scheduler=0, bulkMbps=60, seed=s, mcs0=m0, mcs1=FAST_MCS, warmup=0.5,
             cond="sweep", load="ref60")
        for m0 in range(8) for s in CAL_SEEDS
    ]
    res = pmap(jobs)
    rows = []
    for m0 in range(8):
        rr = [r for r in res if r["mcs0"] == m0]
        c0, c1 = mean_of(rr, "link0_comp_median_ms"), mean_of(rr, "link1_comp_median_ms")
        rows.append(dict(mcs0=m0, mcs1=FAST_MCS, comp0_median_ms=c0, comp1_median_ms=c1,
                         ratio=c0 / c1,
                         ratio_sd=st.pstdev([r["link0_comp_median_ms"] / r["link1_comp_median_ms"] for r in rr]),
                         goodput_mbps=mean_of(rr, "total_goodput_mbps")))
    write_csv(OUT / "stage1_asymmetry_sweep.csv", rows)
    picks = {}
    for cond, tgt in TARGETS.items():
        best = min(rows, key=lambda r: abs(math.log(r["ratio"] / tgt)))
        picks[cond] = dict(mcs0=best["mcs0"], mcs1=FAST_MCS, width0=20, width1=20, rss0=-55, rss1=-55,
                           target_ratio=tgt, calib_ratio=best["ratio"], calib_ratio_sd=best["ratio_sd"])
    return picks


def capacity(conds, tag):
    jobs, keys = [], []
    for c, p in conds.items():
        for s in CAL_SEEDS:
            keys.append(c)
            jobs.append(dict(simTime=5, scheduler=0, bulkMbps=400, seed=s, warmup=0.5, cond=c,
                             load="sat", **phys(p)))
    res = pmap(jobs)
    rows = []
    for c in conds:
        rr = [r for k, r in zip(keys, res) if k == c]
        cap = mean_of(rr, "total_goodput_mbps")
        conds[c]["capacity_mbps"] = cap
        conds[c]["capacity_sd"] = st.pstdev([r["total_goodput_mbps"] for r in rr])
        conds[c]["bulk_mbps"] = {L: max(0.5, f * cap - LS_MBPS) for L, f in LOAD_FRACTIONS.items()}
        rows.append(dict(set=tag, cond=c, capacity_mbps=cap, capacity_sd=conds[c]["capacity_sd"],
                         bulk_pdr=mean_of(rr, "bulk_pdr"), ls_pdr=mean_of(rr, "ls_pdr")))
    return rows


def stage3():
    A = [-77.5 + 0.25 * i for i in range(9)]
    B = [-77.5 + 0.25 * i for i in range(11)]
    jobs = [
        dict(simTime=3, scheduler=0, bulkMbps=30, seed=s, mcs0=11, mcs1=11, rss0=a, rss1=b,
             warmup=0.5, cond="varscan", load="ref30")
        for a in A for b in B if b >= a for s in CAL_SEEDS
    ]
    res = pmap(jobs)
    rows = []
    for a in A:
        for b in B:
            if b < a:
                continue
            rr = [r for r in res if r["rss0"] == a and r["rss1"] == b]
            v0, v1 = mean_of(rr, "link0_comp_std_ms") ** 2, mean_of(rr, "link1_comp_std_ms") ** 2
            m0, m1 = mean_of(rr, "link0_comp_mean_ms"), mean_of(rr, "link1_comp_mean_ms")
            rows.append(dict(rss0=a, rss1=b, mean0=m0, mean1=m1, std0=v0 ** 0.5, std1=v1 ** 0.5,
                             vr=max(v0, v1) / max(1e-12, min(v0, v1)), dmean=abs(m0 - m1),
                             n0=mean_of(rr, "link0_n"), n1=mean_of(rr, "link1_n"),
                             pdr=mean_of(rr, "bulk_pdr")))
    write_csv(OUT / "stage3_variance_scan.csv", rows)
    ok = [o for o in rows if o["dmean"] <= 0.2 and min(o["n0"], o["n1"]) >= 500 and o["pdr"] > 99]
    picks = {}
    for name, tgt in VAR_TARGETS.items():
        ranked = sorted(ok, key=lambda o: abs(math.log(o["vr"] / tgt)))
        best = abs(math.log(ranked[0]["vr"] / tgt))
        ties = [o for o in ranked if abs(math.log(o["vr"] / tgt)) <= best + 0.03]
        pick = min(ties, key=lambda o: max(o["mean0"], o["mean1"]))
        picks[name] = dict(mcs0=11, mcs1=11, width0=20, width1=20, rss0=pick["rss0"], rss1=pick["rss1"],
                           target_var_ratio=tgt, calib_var_ratio=pick["vr"], calib_dmean_ms=pick["dmean"],
                           calib_mean0_ms=pick["mean0"], calib_mean1_ms=pick["mean1"],
                           calib_std0_ms=pick["std0"], calib_std1_ms=pick["std1"])
    return picks


def stage4(conds):
    jobs, meta = [], []
    for c, p in conds.items():
        for L in LOAD_FRACTIONS:
            for s in CAL_SEEDS:
                meta.append((c, L))
                jobs.append(dict(simTime=6, scheduler=0, bulkMbps=p["bulk_mbps"][L], seed=s, warmup=0.5,
                                 cond=c, load=L, **phys(p)))
    res = pmap(jobs)
    rows = []
    for c, p in conds.items():
        for L in LOAD_FRACTIONS:
            rr = [r for m, r in zip(meta, res) if m == (c, L)]
            ratios = [r["link0_comp_median_ms"] / r["link1_comp_median_ms"] for r in rr]
            rows.append(dict(cond=c, load=L, bulk_mbps=p["bulk_mbps"][L],
                             achieved_ratio_mean=st.mean(ratios), achieved_ratio_sd=st.pstdev(ratios),
                             target_ratio=p["target_ratio"], bulk_pdr=mean_of(rr, "bulk_pdr"),
                             ls_pdr=mean_of(rr, "ls_pdr"), dropped=mean_of(rr, "dropped"),
                             goodput_mbps=mean_of(rr, "total_goodput_mbps"),
                             goodput_over_capacity=mean_of(rr, "total_goodput_mbps") / p["capacity_mbps"]))
    write_csv(OUT / "stage4_validation.csv", rows)
    return rows


def main():
    conds = stage1()
    cap_rows = capacity(conds, "main")
    var = stage3()
    cap_rows += capacity(var, "ablation")
    write_csv(OUT / "stage2_capacity.csv", cap_rows)
    val = stage4(conds)
    cfg = dict(
        description="Frozen physical conditions; produced by calibrate.py with FIFO only (seeds 9001-9003).",
        calibration_seeds=list(CAL_SEEDS), load_fractions=LOAD_FRACTIONS, ls_mbps=LS_MBPS,
        main_conditions=conds, ablation_regimes=var, ablation_load="L2",
        ablation_weight_ratios=[1, 10, 50], main_weight_ratio=10,
    )
    (HERE / "configs").mkdir(exist_ok=True)
    (HERE / "configs" / "conditions.json").write_text(json.dumps(cfg, indent=2))
    for c, p in {**conds, **var}.items():
        print(c, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in p.items() if k != "bulk_mbps"})
    for r in val:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})


if __name__ == "__main__":
    sys.exit(main())
