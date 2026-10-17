#!/usr/bin/env python3
"""cross_simulator.py - preregistered (section 8) comparison of historical Python-simulator results
(read-only) with the ns-3 results. Never pools the two. Output: results/analysis/cross_simulator.csv"""
import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "results" / "analysis"


def ns3(fam_rows, cond, load, arm, ref, ep):
    for r in fam_rows:
        if (r["cond"], r["load"], r["arm"], r["ref"], r["endpoint"]) == (cond, load, arm, ref, ep) and r["family"] != "D3":
            return r
    raise KeyError((cond, load, arm, ref, ep))


def main():
    comps = list(csv.DictReader(open(OUT / "comparisons.csv")))
    main_c = [r for r in comps if r["campaign"] == "main"]
    abl_c = [r for r in comps if r["campaign"] == "ablation"]
    rows = []
    # (1) Python exp1: SASP vs DefaultFIFO at delta 0.2 / 1.5 ms  <->  ns-3 A1 / A2 (all loads)
    p1 = {(r["delta_ms"], r["scheduler"]): r for r in csv.DictReader(open(REPO / "experiments/results/exp1_link_asymmetry.csv"))}
    for delta, cond in (("0.2", "A1"), ("1.5", "A2")):
        f, s = p1[(delta, "DefaultFIFO")], p1[(delta, "SASP")]
        rel_x = 100 * (1 - float(s["mean_cross_blocking_ms"]) / float(f["mean_cross_blocking_ms"]))
        rel_d = 100 * (1 - float(s["p99_e2e_delay_ms"]) / float(f["p99_e2e_delay_ms"]))
        rows.append(dict(model="python", scenario=f"exp1 delta={delta}ms", maps_to=cond, contrast="SASP vs FIFO",
                         cross_wait_rel_reduction_pct=rel_x, p99_delay_rel_reduction_pct=rel_d))
        for load in ("L0", "L1", "L2"):
            a = ns3(main_c, cond, load, "FullSASP", "FIFO", "cross_wait_ms")
            b = ns3(main_c, cond, load, "FullSASP", "FIFO", "ls_delay_p99_ms")
            rows.append(dict(model="ns3", scenario=f"{cond}/{load}", maps_to=cond, contrast="FullSASP vs FIFO",
                             cross_wait_rel_reduction_pct=float(a["rel_reduction_pct"]), cross_wait_p=float(a["p_raw"]),
                             p99_delay_rel_reduction_pct=float(b["rel_reduction_pct"]), p99_delay_p=float(b["p_raw"])))
    # (2) Python Phase-6 Regime A (delta_mu = 0.1 ms, sigma ratio 1, w in {1,10,50}): FIFO / MeanOnly / FullSASP
    #     <-> ns-3 ablation regime V1 (measured variance ratio ~1, mean gap ~0) at the same weights.
    #     (The preregistration text said "Regime B, w=10"; Regime B exists only at w=50 - documented deviation.)
    d = defaultdict(list)
    for r in csv.DictReader(open(REPO / "experiments/ablation_phase6/raw_runs.csv")):
        if r["regime"] == "RegimeA_Priority" and float(r["weight_ratio"]) in (1.0, 10.0, 50.0):
            d[(float(r["weight_ratio"]), r["sched_type"])].append(float(r["interactive_cross_ms"]))
    for w in (1.0, 10.0, 50.0):
        m = {s: st.mean(d[(w, s)]) for s in ("DefaultFIFO", "MeanOnly", "FullSASP")}
        for arm in ("MeanOnly", "FullSASP"):
            rows.append(dict(model="python", scenario=f"phase6 RegimeA dmu=0.1 w={int(w)}", maps_to=f"V1_w{int(w)}",
                             contrast=f"{arm} vs FIFO", cross_wait_rel_reduction_pct=100 * (1 - m[arm] / m["DefaultFIFO"])))
        rows.append(dict(model="python", scenario=f"phase6 RegimeA dmu=0.1 w={int(w)}", maps_to=f"V1_w{int(w)}",
                         contrast="FullSASP vs MeanOnly", cross_wait_rel_reduction_pct=100 * (1 - m["FullSASP"] / m["MeanOnly"])))
    for r in abl_c:
        if r["family"] in ("D1", "D2", "F4") and r["cond"].startswith("V1_w") and r["endpoint"] == "cross_wait_ms":
            rows.append(dict(model="ns3", scenario=r["cond"], maps_to=r["cond"],
                             contrast=f"{r['arm']} vs {r['ref']}", cross_wait_rel_reduction_pct=float(r["rel_reduction_pct"]),
                             cross_wait_p=float(r["p_raw"])))
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(OUT / "cross_simulator.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})


if __name__ == "__main__":
    main()
