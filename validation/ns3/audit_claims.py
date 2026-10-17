#!/usr/bin/env python3
"""audit_claims.py - independent recomputation of every ns-3 number quoted in paper/main.tex.

Deliberately shares no code with analyze_results.py: it re-derives each figure directly from the raw
per-run CSVs with plain loops (numpy for means, scipy only for t tail probabilities).
Exits non-zero if any claim does not match its recomputation within the stated tolerance.
"""
import csv
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MAIN = list(csv.DictReader(open(HERE / "results/main_campaign/main_campaign_raw.csv")))
ABL = list(csv.DictReader(open(HERE / "results/threshold_ablation/threshold_ablation_raw.csv")))
ARM = {"FIFO": 0, "Mean": 1, "Full": 2}


def iv(r, k):
    return int(round(float(r[k])))


def series(rows, cond, load, arm, key):
    d = {iv(r, "seed"): float(r[key]) for r in rows
         if r["cond"] == cond and r["load"] == load and iv(r, "scheduler") == ARM[arm]}
    assert len(d) == 30, (cond, load, arm, len(d))
    return np.array([d[s] for s in sorted(d)])


def ttest(x, y):
    d = x - y
    n = len(d)
    se = d.std(ddof=1) / math.sqrt(n)
    if se == 0:  # identical arms: no evidence of a difference
        return d.mean(), d.mean(), d.mean(), (1.0 if d.mean() == 0 else 0.0)
    t = d.mean() / se
    p = 2 * stats.t.sf(abs(t), n - 1)
    h = stats.t.ppf(0.975, n - 1) * se
    return d.mean(), d.mean() - h, d.mean() + h, p


def holm(ps):
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    out, run = [0] * m, 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * ps[i]))
        out[i] = run
    return out


rows = []  # (claim, manuscript, source, recomputed, result)


def check(claim, manuscript, source, recomputed, tol, fmt="{:.4f}"):
    ok = abs(recomputed - manuscript) <= tol
    rows.append((claim, fmt.format(manuscript), source, fmt.format(recomputed), "PASS" if ok else "FAIL"))


# ---------------------------------------------------------------- primary
f = series(MAIN, "A2", "L2", "FIFO", "cross_wait_ms")
u = series(MAIN, "A2", "L2", "Full", "cross_wait_ms")
d, lo, hi, p = ttest(u, f)
S = "main_campaign_raw.csv, A2/L2, 30 seeds, cross_wait_ms"
check("Primary: FIFO mean cross wait (ms)", 0.2474, S, f.mean(), 5e-5)
check("Primary: Full SASP mean cross wait (ms)", 0.2479, S, u.mean(), 5e-5)
check("Primary: paired difference (ms)", 0.0005, S, d, 5e-5)
check("Primary: 95% CI low (ms)", -0.0064, S, lo, 5e-5)
check("Primary: 95% CI high (ms)", 0.0075, S, hi, 5e-5)
check("Primary: two-sided paired-t p", 0.88, S, p, 5e-3, "{:.3f}")
check("Primary: relative change (%)", -0.2, S, 100 * (1 - u.mean() / f.mean()), 0.05, "{:.2f}")
r1 = float(np.corrcoef(f, series(MAIN, "A2", "L2", "Mean", "cross_wait_ms"))[0, 1])
r2 = float(np.corrcoef(f, u)[0, 1])
check("Seed pairing: corr(FIFO, Mean-Only), primary cell", -0.06, S, r1, 0.005, "{:.2f}")
check("Seed pairing: corr(FIFO, Full), primary cell", -0.32, S, r2, 0.005, "{:.2f}")

# ---------------------------------------------------------------- families (recomputed from scratch)
cells = [(c, ld) for c in ("A0", "A1", "A2") for ld in ("L0", "L1", "L2")]


def family(arm, ref, key, drop=None):
    cs = [c for c in cells if c != drop]
    res, ps = {}, []
    for c in cs:
        x, y = series(MAIN, *c, arm, key), series(MAIN, *c, ref, key)
        pp = ttest(x, y)[3]
        res[c] = (100 * (1 - x.mean() / y.mean()), pp)
        ps.append(pp)
    for c, a in zip(cs, holm(ps)):
        res[c] = res[c] + (a,)
    return res


F1 = family("Mean", "FIFO", "cross_wait_ms")
F3 = family("Full", "FIFO", "cross_wait_ms", drop=("A2", "L2"))
F2 = family("Full", "Mean", "cross_wait_ms")
check("F1 smallest Holm-adjusted p (Mean-Only vs FIFO, cross wait)", 0.099, "recomputed Holm over 9 cells",
      min(v[2] for v in F1.values()), 1e-3, "{:.3f}")
check("F3 smallest Holm-adjusted p (Full vs FIFO, 8 cells)", 0.074, "recomputed Holm over 8 cells",
      min(v[2] for v in F3.values()), 1e-3, "{:.3f}")
check("A2/L1 Mean-Only relative change in cross wait (%)", -2.5, "A2/L1", F1[("A2", "L1")][0], 0.06, "{:.1f}")
check("A2/L1 Full relative change in cross wait (%)", -2.7, "A2/L1", F3[("A2", "L1")][0], 0.06, "{:.1f}")
check("F2 smallest Holm-adjusted p (Full vs Mean, cross wait)", 0.612, "recomputed Holm",
      min(v[2] for v in F2.values()), 1e-3, "{:.3f}")

F6 = family("Full", "FIFO", "ls_delay_p99_ms")
F5 = family("Mean", "FIFO", "ls_delay_p99_ms")
F7 = family("Full", "Mean", "ls_delay_p99_ms")
check("p99: Full vs FIFO, number of cells with Holm p<0.05", 7, "recomputed F6",
      sum(v[2] < 0.05 for v in F6.values()), 0, "{:.0f}")
check("p99: Mean-Only vs FIFO, number of cells with Holm p<0.05", 8, "recomputed F5",
      sum(v[2] < 0.05 for v in F5.values()), 0, "{:.0f}")
check("p99: Full vs FIFO, A2/L1 reduction (%)", 17.5, "A2/L1", F6[("A2", "L1")][0], 0.06, "{:.1f}")
check("p99: Full vs FIFO, A1/L2 reduction (%)", 11.3, "A1/L2", F6[("A1", "L2")][0], 0.06, "{:.1f}")
check("p99: Full vs FIFO, A2/L2 reduction (%)", 7.4, "A2/L2", F6[("A2", "L2")][0], 0.06, "{:.1f}")
check("p99: smallest (most negative) Full vs FIFO change (%)", -0.5, "min over cells",
      min(v[0] for v in F6.values()), 0.06, "{:.1f}")
check("p99: Full vs Mean at A0/L2 (%, negative = Full worse)", -3.1, "A0/L2", F7[("A0", "L2")][0], 0.06, "{:.1f}")
check("p99: Full vs Mean A0/L2 Holm p < 1e-3", 1, "recomputed F7", float(F7[("A0", "L2")][2] < 1e-3), 0, "{:.0f}")
F8b = family("Full", "FIFO", "ls_delay_median_ms")
check("median: Full vs FIFO best reduction (%)", 12.3, "max over cells", max(v[0] for v in F8b.values()), 0.06, "{:.1f}")
check("median: Full vs FIFO A2/L1 change (%, negative = worse)", -1.7, "A2/L1", F8b[("A2", "L1")][0], 0.06, "{:.1f}")

# ---------------------------------------------------------------- invariants
check("main: total forced window advances", 0, "sum forced_adv_events",
      sum(float(r["forced_adv_events"]) for r in MAIN), 0, "{:.0f}")
check("main: total MAC retries", 0, "sum retries", sum(float(r["retries"]) for r in MAIN), 0, "{:.0f}")
check("main: largest reorder-buffer occupancy in any run", 11, "max buf_occ_max",
      max(float(r["buf_occ_max"]) for r in MAIN), 0, "{:.0f}")
check("main: min packet delivery ratio (%) over all runs", 100, "min ls_pdr,bulk_pdr",
      min(min(float(r["ls_pdr"]), float(r["bulk_pdr"])) for r in MAIN), 1e-9, "{:.1f}")
g = defaultdict(set)
for r in MAIN:
    g[(r["cond"], r["load"], r["seed"])].add(round(float(r["bulk_goodput_mbps"]), 2))
check("main: (cell,seed) groups whose bulk goodput differs between arms", 0, "270 groups",
      sum(1 for v in g.values() if max(v) - min(v) > 0.05), 0, "{:.0f}")
walls = [float(r["dec_wall_us_mean"]) for r in MAIN if iv(r, "scheduler") != 0]
check("decision wall time on simulation host: mean (us)", 0.14, "dec_wall_us_mean, predictive arms", float(np.mean(walls)), 0.005, "{:.2f}")
check("decision wall time: smallest run mean (us)", 0.005, "same", min(walls), 0.0005, "{:.3f}")
check("decision wall time: largest run mean (us)", 0.44, "same", max(walls), 0.005, "{:.2f}")


# ---------------------------------------------------------------- ablation
def abl(cell, arm):
    return series(ABL, cell, "L2", arm, "cross_wait_ms")


rel = {}
for reg in ("V1", "V2", "V4"):
    for w in (1, 10, 50):
        c = f"{reg}_w{w}"
        rel[c] = (100 * (1 - abl(c, "Mean").mean() / abl(c, "FIFO").mean()),
                  100 * (1 - abl(c, "Full").mean() / abl(c, "FIFO").mean()),
                  100 * (1 - abl(c, "Full").mean() / abl(c, "Mean").mean()),
                  ttest(abl(c, "Full"), abl(c, "Mean"))[3])
check("ablation: Mean-Only vs FIFO minimum reduction (%)", 16.5, "min over 9 cells",
      min(v[0] for v in rel.values()), 0.06, "{:.1f}")
check("ablation: Mean-Only vs FIFO maximum reduction (%)", 20.6, "max over 9 cells",
      max(v[0] for v in rel.values()), 0.06, "{:.1f}")
check("ablation: Full vs FIFO maximum reduction (%)", 42, "max over 9 cells", max(v[1] for v in rel.values()), 0.5,
      "{:.0f}")
check("ablation: Full vs Mean at w=1, max |difference| (%)", 0, "3 cells",
      max(abs(rel[f"{r}_w1"][2]) for r in ("V1", "V2", "V4")), 1e-9, "{:.1f}")
nz = [v[2] for k, v in rel.items() if not k.endswith("_w1")]
check("ablation: Full vs Mean (w>=10) minimum gain (%)", 6.3, "min over 6 cells", min(nz), 0.06, "{:.1f}")
check("ablation: Full vs Mean (w>=10) maximum gain (%)", 27.1, "max over 6 cells", max(nz), 0.06, "{:.1f}")
ad = dict(zip(rel, holm([rel[k][3] for k in rel])))
check("ablation: cells (w>=10) with Holm p<0.05", 6, "recomputed Holm over 9 cells",
      sum(ad[k] < 0.05 for k in rel if not k.endswith("_w1")), 0, "{:.0f}")
check("ablation: FIFO cross wait identical across w (V1, max spread, ms)", 0, "FIFO ignores w",
      float(np.ptp([abl(f"V1_w{w}", "FIFO").mean() for w in (1, 10, 50)])), 1e-12, "{:.4f}")
vr = {}
for reg in ("V1", "V2", "V4"):
    ratios = []
    for s in range(1, 31):
        r = [x for x in ABL if x["cond"] == f"{reg}_w10" and iv(x, "scheduler") == 0 and iv(x, "seed") == s][0]
        v0, v1 = float(r["link0_comp_std_ms"]) ** 2, float(r["link1_comp_std_ms"]) ** 2
        ratios.append(max(v0, v1) / min(v0, v1))
    vr[reg] = float(np.mean(ratios))
check("ablation: achieved variance ratio V1", 1.01, "FIFO runs, measured", vr["V1"], 0.01, "{:.2f}")
check("ablation: achieved variance ratio V2", 1.29, "FIFO runs, measured", vr["V2"], 0.01, "{:.2f}")
check("ablation: achieved variance ratio V4", 2.32, "FIFO runs, measured", vr["V4"], 0.01, "{:.2f}")
ratio = {c: np.mean([float(r["link0_comp_median_ms"]) / float(r["link1_comp_median_ms"]) for r in MAIN
                     if r["cond"] == c and iv(r, "scheduler") == 0 and r["load"] == "L2"]) for c in ("A0", "A1", "A2")}
check("calibration: achieved median completion ratio A0 (L2)", 1.00, "FIFO runs", ratio["A0"], 0.005, "{:.2f}")
check("calibration: achieved median completion ratio A1 (L2)", 1.42, "FIFO runs", ratio["A1"], 0.005, "{:.2f}")
check("calibration: achieved median completion ratio A2 (L2)", 2.96, "FIFO runs", ratio["A2"], 0.005, "{:.2f}")

# ---------------------------------------------------------------- Gate 1 and Python numbers
ev = int(re.search(r"EVENTS=(\d+)", (HERE / "logs/gate1_ns-3.47.log").read_text()).group(1))
check("Gate 1: events in identical stock/patched trace", 15574, "logs/gate1_ns-3.47*.log", ev, 0, "{:.0f}")
py = {(r["delta_ms"], r["scheduler"]): r
      for r in csv.DictReader(open(REPO / "experiments/results/exp1_link_asymmetry.csv"))}
for dl, tx, tp in (("0.2", 11.0, -8.4), ("1.5", 17.7, -12.1)):
    a, b = py[(dl, "DefaultFIFO")], py[(dl, "SASP")]
    check(f"Python exp1 delta={dl}: cross-blocking reduction (%)", tx, "experiments/results/exp1_link_asymmetry.csv",
          100 * (1 - float(b["mean_cross_blocking_ms"]) / float(a["mean_cross_blocking_ms"])), 0.06, "{:.1f}")
    check(f"Python exp1 delta={dl}: p99 delay change (%, negative = SASP worse)", tp, "same file",
          100 * (1 - float(b["p99_e2e_delay_ms"]) / float(a["p99_e2e_delay_ms"])), 0.06, "{:.1f}")
pa = defaultdict(list)
for r in csv.DictReader(open(REPO / "experiments/ablation_phase6/raw_runs.csv")):
    if r["regime"] == "RegimeA_Priority" and float(r["weight_ratio"]) in (1.0, 10.0, 50.0):
        pa[(float(r["weight_ratio"]), r["sched_type"])].append(float(r["interactive_cross_ms"]))


def red(w, s):
    return 100 * (1 - float(np.mean(pa[(w, s)])) / float(np.mean(pa[(w, "DefaultFIFO")])))


mn = [red(w, "MeanOnly") for w in (1.0, 10.0, 50.0)]
fl = [red(w, "FullSASP") for w in (10.0, 50.0)]
check("Python RegimeA: Mean-Only vs FIFO min (%)", 31, "experiments/ablation_phase6/raw_runs.csv", min(mn), 0.6,
      "{:.0f}")
check("Python RegimeA: Mean-Only vs FIFO max (%)", 37, "same", max(mn), 0.6, "{:.0f}")
check("Python RegimeA: Full vs FIFO (w>=10) min (%)", 34, "same", min(fl), 0.6, "{:.0f}")
check("Python RegimeA: Full vs FIFO (w>=10) max (%)", 39, "same", max(fl), 0.6, "{:.0f}")

# ---------------------------------------------------------------- report
bad = [r for r in rows if r[4] == "FAIL"]
out = ["# NS3 numeric-claim audit", "",
       "Every ns-3 (and cited Python-historical) number in `paper/main.tex` recomputed independently by "
       "`validation/ns3/audit_claims.py` from the raw per-run CSVs (no shared code with `analyze_results.py`).", "",
       f"**{len(rows) - len(bad)} / {len(rows)} claims match their recomputation.**", "",
       "| Manuscript claim | Manuscript value | Exact source | Independent recomputation | Result |",
       "|---|---|---|---|---|"]
out += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows]
(REPO / "docs").mkdir(exist_ok=True)
(REPO / "docs" / "NS3_NUMERIC_CLAIM_AUDIT.md").write_text("\n".join(out) + "\n")
for r in bad:
    print("FAIL:", r)
print(f"{len(rows) - len(bad)}/{len(rows)} claims verified")
sys.exit(1 if bad else 0)
