#!/usr/bin/env python3
"""analyze_results.py - analysis of the preregistered ns-3.47 campaigns, from raw CSV only.

Implements preregistration.md section 7 exactly:
  * strict validation of the raw data (fails loudly, never repairs);
  * single primary confirmatory test: Full SASP vs FIFO, primary endpoint, cell A2 x L2 (paired t);
  * secondary families F1..F8 with Holm step-down (raw and adjusted p);
  * TOST equivalence for Full SASP vs Mean-Only (margin 5 % of the cell's FIFO mean);
  * descriptive tables, calibration achieved ratios with bootstrap CIs, pairing diagnostics,
    decision statistics, ablation interaction (OLS F-tests).
Nothing is read except the raw CSVs and configs/conditions.json.
"""
import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "analysis"
ARMS = {0: "FIFO", 1: "MeanOnly", 2: "FullSASP"}
SEEDS = list(range(1, 31))
BOOT = 10000
BOOT_SEED = 20261014
PRIMARY = "cross_wait_ms"
AUDITS = ("audit_sn_changed", "audit_intra_flow_inv", "audit_sn_dup")
TEXT = {"cond", "load", "build_id"}

DESCRIPTIVE = [
    "cross_wait_ms", "within_wait_ms", "forced_wait_ms", "total_wait_ms", "cross_wait_anybulk_ms",
    "ls_frac_waiting", "ls_frac_cross", "bulk_total_wait_ms", "ls_delay_median_ms", "ls_delay_p95_ms",
    "ls_delay_p99_ms", "ls_delay_mean_ms", "ls_queue_wait_ms", "ls_goodput_kbps", "bulk_goodput_mbps",
    "total_goodput_mbps", "ls_pdr", "bulk_pdr", "jain", "min_norm_tput", "retries", "nacked", "dropped",
    "buf_occ_mean", "buf_occ_max", "forced_adv_events", "forced_adv_slots", "dec_multiflow",
    "dec_pairwise", "dec_ge3", "dec_reserve_applied", "dec_full_ne_mean", "reserved_mpdus",
    "reserve_hold_mean_ms", "reserve_hold_max_ms", "dec_wall_us_mean", "decisions",
]

# (family, endpoint, (arm, ref)) - main campaign, preregistration section 7
MAIN_FAMILIES = [
    ("F1", PRIMARY, (1, 0)), ("F2", PRIMARY, (2, 1)), ("F3", PRIMARY, (2, 0)),
    ("F5", "ls_delay_p99_ms", (1, 0)), ("F6", "ls_delay_p99_ms", (2, 0)), ("F7", "ls_delay_p99_ms", (2, 1)),
    ("F8a", "ls_delay_median_ms", (1, 0)), ("F8b", "ls_delay_median_ms", (2, 0)),
    ("F8c", "ls_delay_median_ms", (2, 1)),
]


# ----------------------------------------------------------------------------- loading / validation
def load_raw(path, expect_rows=810):
    rows = list(csv.DictReader(open(path)))
    if len(rows) != expect_rows:
        sys.exit(f"{path}: expected {expect_rows} rows, found {len(rows)}")
    for r in rows:
        for k, v in r.items():
            if k not in TEXT:
                try:
                    r[k] = float(v)
                except ValueError:
                    sys.exit(f"{path}: non-numeric value {k}={v!r} in run {r.get('run_id')}")
                if not math.isfinite(r[k]):
                    sys.exit(f"{path}: non-finite {k} in run {r.get('run_id')}")
    return rows


def validate(rows, cfg, campaign):
    ident = set()
    cells = defaultdict(lambda: defaultdict(dict))
    builds = {r["build_id"] for r in rows}
    if len(builds) != 1:
        sys.exit(f"mixed build ids in one run set: {builds}")
    for r in rows:
        key = (r["cond"], r["load"], int(r["seed"]), int(r["scheduler"]))
        if key in ident:
            sys.exit(f"duplicate experiment identity {key}")
        ident.add(key)
        if int(r["scheduler"]) not in ARMS:
            sys.exit(f"bad scheduler id in {key}")
        for a in AUDITS:
            if r[a] != 0:
                sys.exit(f"audit violation {a}={r[a]} in {key}")
        if r["audit_untagged_tx"] > 20:
            sys.exit(f"audit violation untagged_tx={r['audit_untagged_tx']} in {key}")
        if r["sim_time_s"] != 10.0:
            sys.exit(f"unexpected sim time in {key}")
        if campaign == "main":
            p = cfg["main_conditions"][r["cond"]]
            w = cfg["main_weight_ratio"]
            bulk = p["bulk_mbps"][r["load"]]
        else:
            reg, wtxt = r["cond"].split("_w")
            p = cfg["ablation_regimes"][reg]
            w = float(wtxt)
            bulk = p["bulk_mbps"][cfg["ablation_load"]]
        for k, v in (("mcs0", p["mcs0"]), ("mcs1", p["mcs1"]), ("rss0", p["rss0"]), ("rss1", p["rss1"]),
                     ("width0", p["width0"]), ("width1", p["width1"]), ("weight_ratio", w)):
            if abs(r[k] - v) > 1e-9:
                sys.exit(f"config mismatch {k}: run has {r[k]}, frozen conditions say {v} ({key})")
        if abs(r["bulk_mbps"] - bulk) > 2e-5 * max(1, bulk):
            sys.exit(f"config mismatch bulk_mbps ({key})")
        cells[(r["cond"], r["load"])][int(r["seed"])][int(r["scheduler"])] = r
    for cell, bys in cells.items():
        if sorted(bys) != SEEDS:
            sys.exit(f"cell {cell}: seeds are {sorted(bys)}")
        for s, arms in bys.items():
            if sorted(arms) != [0, 1, 2]:
                sys.exit(f"cell {cell} seed {s}: arms {sorted(arms)}")
    return cells


def vec(cells, cell, arm, key):
    return np.array([cells[cell][s][arm][key] for s in SEEDS])


# ----------------------------------------------------------------------------- statistics
def holm(pvals):
    """Holm step-down adjusted p-values (same order as input)."""
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    run = 0.0
    for rank, idx in enumerate(order):
        run = max(run, (m - rank) * pvals[idx])
        adj[idx] = min(1.0, run)
    return adj.tolist()


def paired(x, y, rng):
    """Paired comparison of arm x against reference y (x - y)."""
    d = x - y
    n = len(d)
    mean_d = float(d.mean())
    sd = float(d.std(ddof=1))
    se = sd / math.sqrt(n)
    if sd == 0:
        t, p = (0.0, 1.0) if mean_d == 0 else (math.copysign(math.inf, mean_d), 0.0)
    else:
        t, p = stats.ttest_rel(x, y)
        t, p = float(t), float(p)
    tcrit = stats.t.ppf(0.975, n - 1)
    try:
        pw = float(stats.wilcoxon(d, zero_method="wilcox").pvalue) if np.any(d != 0) else 1.0
    except ValueError:
        pw = 1.0
    idx = rng.integers(0, n, size=(BOOT, n))
    ref_means = y[idx].mean(axis=1)
    arm_means = x[idx].mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = 100.0 * (1.0 - arm_means / ref_means)
    rel = rel[np.isfinite(rel)]
    rel_lo, rel_hi = (np.percentile(rel, 2.5), np.percentile(rel, 97.5)) if len(rel) else (math.nan,) * 2
    ref_mean = float(y.mean())
    return dict(mean_ref=ref_mean, mean_arm=float(x.mean()), diff=mean_d, ci_lo=mean_d - tcrit * se,
                ci_hi=mean_d + tcrit * se, t=t, p_raw=p, p_wilcoxon=pw,
                rel_reduction_pct=100.0 * (1 - x.mean() / ref_mean) if ref_mean != 0 else math.nan,
                rel_lo=float(rel_lo), rel_hi=float(rel_hi),
                dz=mean_d / sd if sd > 0 else 0.0,
                wins=int((d < 0).sum()), ties=int((d == 0).sum()), losses=int((d > 0).sum()))


def tost(x, y, margin):
    d = x - y
    n = len(d)
    sd = d.std(ddof=1)
    se = sd / math.sqrt(n)
    if se == 0:
        return 0.0 if abs(d.mean()) < margin else 1.0
    p_low = 1 - stats.t.cdf((d.mean() + margin) / se, n - 1)
    p_up = stats.t.cdf((d.mean() - margin) / se, n - 1)
    return float(max(p_low, p_up))


def ols_ftests(rows):
    """Nested-model F-tests for factors A, B and A:B on a response. rows: (a, b, y)."""
    levels_a = sorted({r[0] for r in rows})
    levels_b = sorted({r[1] for r in rows})
    y = np.array([r[2] for r in rows])

    def design(terms):
        cols = [np.ones(len(rows))]
        if "A" in terms:
            cols += [np.array([1.0 if r[0] == a else 0 for r in rows]) for a in levels_a[1:]]
        if "B" in terms:
            cols += [np.array([1.0 if r[1] == b else 0 for r in rows]) for b in levels_b[1:]]
        if "AB" in terms:
            cols += [np.array([1.0 if (r[0] == a and r[1] == b) else 0 for r in rows])
                     for a in levels_a[1:] for b in levels_b[1:]]
        return np.column_stack(cols)

    def rss(terms):
        X = design(terms)
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ beta
        return float(res @ res), X.shape[1]

    full_rss, full_p = rss(["A", "B", "AB"])
    n = len(y)
    out = {}
    for name, red in (("A", ["B", "AB"]), ("B", ["A", "AB"]), ("A:B", ["A", "B"])):
        rss_r, p_r = rss(red)
        df1 = full_p - p_r
        df2 = n - full_p
        F = ((rss_r - full_rss) / df1) / (full_rss / df2) if full_rss > 0 else math.inf
        out[name] = (F, df1, df2, float(stats.f.sf(F, df1, df2)))
    return out


# ----------------------------------------------------------------------------- main analysis
def analyse(campaign, raw_path, cfg, rng):
    rows = load_raw(raw_path)
    cells = validate(rows, cfg, campaign)
    cell_keys = sorted(cells)
    means = []
    for cell in cell_keys:
        for arm in ARMS:
            rec = dict(campaign=campaign, cond=cell[0], load=cell[1], arm=ARMS[arm])
            for k in DESCRIPTIVE:
                v = vec(cells, cell, arm, k)
                rec[k + "_mean"] = float(v.mean())
                rec[k + "_sd"] = float(v.std(ddof=1))
            means.append(rec)

    comps = []

    def add(family, endpoint, cell, arm, ref):
        x, y = vec(cells, cell, arm, endpoint), vec(cells, cell, ref, endpoint)
        c = paired(x, y, rng)
        c.update(campaign=campaign, family=family, endpoint=endpoint, cond=cell[0], load=cell[1],
                 arm=ARMS[arm], ref=ARMS[ref])
        if (arm, ref) == (2, 1):
            fifo_mean = float(vec(cells, cell, 0, endpoint).mean())
            c["tost_margin"] = 0.05 * fifo_mean
            c["tost_p"] = tost(x, y, 0.05 * fifo_mean)
        comps.append(c)

    primary = None
    if campaign == "main":
        for cell in cell_keys:
            for fam, ep, (arm, ref) in MAIN_FAMILIES:
                if fam == "F3" and cell == ("A2", "L2"):
                    add("PRIMARY", ep, cell, arm, ref)  # the confirmatory cell is excluded from F3
                else:
                    add(fam, ep, cell, arm, ref)
        primary = next(c for c in comps if c["family"] == "PRIMARY")
    else:
        for cell in cell_keys:
            add("F4", PRIMARY, cell, 2, 1)
            add("D1", PRIMARY, cell, 1, 0)
            add("D2", PRIMARY, cell, 2, 0)
            add("D3", "ls_delay_p99_ms", cell, 2, 1)

    groups = defaultdict(list)
    for c in comps:
        if c["family"] in ("PRIMARY", "D1", "D2", "D3"):
            c["p_holm"] = c["p_raw"]  # single test / descriptive: no multiplicity adjustment
        else:
            groups[c["family"]].append(c)
    for fam, cs in groups.items():
        for c, a in zip(cs, holm([c["p_raw"] for c in cs])):
            c["p_holm"] = a
    for fam in ("F2", "F4"):
        cs = [c for c in comps if c["family"] == fam]
        if cs:
            for c, a in zip(cs, holm([c["tost_p"] for c in cs])):
                c["tost_p_holm"] = a
                c["equivalent_at_5pct"] = bool(a < 0.05)

    pairing = []
    for cell in cell_keys:
        f = vec(cells, cell, 0, PRIMARY)
        for arm in (1, 2):
            a = vec(cells, cell, arm, PRIMARY)
            r = float(np.corrcoef(f, a)[0, 1]) if f.std() > 0 and a.std() > 0 else math.nan
            pairing.append(dict(campaign=campaign, cond=cell[0], load=cell[1], arm=ARMS[arm], corr_with_fifo=r))

    calib = []
    for cell in cell_keys:
        c0 = vec(cells, cell, 0, "link0_comp_median_ms")
        c1 = vec(cells, cell, 0, "link1_comp_median_ms")
        ratio = c0 / c1
        v0 = vec(cells, cell, 0, "link0_comp_std_ms") ** 2
        v1 = vec(cells, cell, 0, "link1_comp_std_ms") ** 2
        vr = np.maximum(v0, v1) / np.minimum(v0, v1)
        idx = rng.integers(0, 30, size=(2000, 30))
        calib.append(dict(campaign=campaign, cond=cell[0], load=cell[1], ratio_mean=float(ratio.mean()),
                          ratio_lo=float(np.percentile(ratio[idx].mean(1), 2.5)),
                          ratio_hi=float(np.percentile(ratio[idx].mean(1), 97.5)),
                          median_gap_ms=float((c0 - c1).mean()), var_ratio_mean=float(vr.mean()),
                          var_ratio_lo=float(np.percentile(vr[idx].mean(1), 2.5)),
                          var_ratio_hi=float(np.percentile(vr[idx].mean(1), 97.5)),
                          mean_gap_ms=float(abs(vec(cells, cell, 0, "link0_comp_mean_ms") -
                                                vec(cells, cell, 0, "link1_comp_mean_ms")).mean()),
                          goodput_mbps=float(vec(cells, cell, 0, "total_goodput_mbps").mean()),
                          bulk_pdr=float(vec(cells, cell, 0, "bulk_pdr").mean()),
                          dropped=float(vec(cells, cell, 0, "dropped").mean())))

    dec = []
    for cell in cell_keys:
        for arm in (1, 2):
            multi = vec(cells, cell, arm, "dec_multiflow")
            dec.append(dict(campaign=campaign, cond=cell[0], load=cell[1], arm=ARMS[arm],
                            multi_flow_decisions=float(multi.mean()),
                            reservations_applied=float(vec(cells, cell, arm, "dec_reserve_applied").mean()),
                            frac_decisions_reserved=float((vec(cells, cell, arm, "dec_reserve_applied") /
                                                           np.maximum(1, multi)).mean()),
                            frac_full_ne_mean=float((vec(cells, cell, arm, "dec_full_ne_mean") /
                                                     np.maximum(1, multi)).mean()),
                            reserve_hold_mean_ms=float(vec(cells, cell, arm, "reserve_hold_mean_ms").mean()),
                            dec_wall_us_mean=float(vec(cells, cell, arm, "dec_wall_us_mean").mean())))

    inter = []
    if campaign == "ablation":
        data = []
        for cell in cell_keys:
            reg, w = cell[0].split("_w")
            for s in SEEDS:
                data.append((reg, w, cells[cell][s][2][PRIMARY] - cells[cell][s][1][PRIMARY]))
        names = {"A": "variance_regime", "B": "weight_ratio", "A:B": "interaction"}
        for term, (F, d1, d2, p) in ols_ftests(data).items():
            inter.append(dict(term=names[term], F=F, df1=d1, df2=d2, p=p))
    return means, comps, pairing, calib, dec, inter, primary


def write_csv(path, rows):
    if not rows:
        return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", default=str(HERE / "results/main_campaign/main_campaign_raw.csv"))
    ap.add_argument("--ablation", default=str(HERE / "results/threshold_ablation/threshold_ablation_raw.csv"))
    ap.add_argument("--only", choices=["main", "ablation"])
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    out = Path(a.out)
    cfg = json.loads((HERE / "configs/conditions.json").read_text())
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(BOOT_SEED)
    acc = defaultdict(list)
    primary = None
    for camp, path in (("main", a.main), ("ablation", a.ablation)):
        if a.only and a.only != camp:
            continue
        if not Path(path).exists():
            print(f"skip {camp}: {path} missing")
            continue
        m, c, p, cal, d, i, prim = analyse(camp, path, cfg, rng)
        for name, v in (("arm_means", m), ("comparisons", c), ("pairing", p), ("calibration_achieved", cal),
                        ("decisions", d), ("ablation_interaction", i)):
            acc[name] += v
        primary = prim or primary
    for name, rows in acc.items():
        write_csv(out / f"{name}.csv", rows)
    if primary:
        (out / "primary.json").write_text(json.dumps(primary, indent=2))
        print("PRIMARY (Full SASP vs FIFO, A2 x L2, mean cross-flow reorder wait of LS packets):")
        print(f"  FIFO {primary['mean_ref']:.5f} ms  SASP {primary['mean_arm']:.5f} ms  "
              f"diff {primary['diff']:+.5f} ms 95%CI [{primary['ci_lo']:+.5f}, {primary['ci_hi']:+.5f}]  "
              f"p={primary['p_raw']:.4g}  rel.reduction {primary['rel_reduction_pct']:.2f}% "
              f"[{primary['rel_lo']:.2f}, {primary['rel_hi']:.2f}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
