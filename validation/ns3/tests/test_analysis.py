"""Tests of analyze_results.py on synthetic campaigns with PLANTED effects and injected defects.

The expected statistics are computed here with an independent hand implementation (manual paired
t-test via numpy + scipy.stats.t.sf only for the tail probability) - not by calling the code under test.
"""
import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

HERE = Path(__file__).resolve().parent
NS3 = HERE.parent
sys.path.insert(0, str(NS3))
import nsrun  # noqa: E402

CFG = json.loads((NS3 / "configs" / "conditions.json").read_text())
SEEDS = range(1, 31)


@pytest.fixture(scope="module")
def template():
    return nsrun.run(dict(simTime=1.5, scheduler=0, seed=1, bulkMbps=20, warmup=0.2), profile="optimized")


def synth_main(template, rng, effects):
    """effects[(cond,load)] = (mean_scale_for_arm1, mean_scale_for_arm2); FIFO primary ~ N(0.25,0.03)."""
    rows, rid = [], 0
    for cond, p in CFG["main_conditions"].items():
        for load in CFG["load_fractions"]:
            s1, s2 = effects.get((cond, load), (1.0, 1.0))
            for seed in SEEDS:
                base = max(0.01, rng.normal(0.25, 0.03))
                vals = {0: base, 1: base * s1 + rng.normal(0, 0.005), 2: base * s2 + rng.normal(0, 0.005)}
                for arm in (0, 1, 2):
                    rid += 1
                    r = dict(template)
                    r.update(run_id=rid, seed=seed, scheduler=arm, cond=cond, load=load, mcs0=p["mcs0"],
                             mcs1=p["mcs1"], width0=p["width0"], width1=p["width1"], rss0=p["rss0"],
                             rss1=p["rss1"], bulk_mbps=p["bulk_mbps"][load], weight_ratio=CFG["main_weight_ratio"],
                             sim_time_s=10.0, build_id="synthetic", cross_wait_ms=vals[arm],
                             ls_delay_p99_ms=1.0 + rng.normal(0, 0.05) - (0.1 if arm else 0),
                             ls_delay_median_ms=0.6 + rng.normal(0, 0.02),
                             link0_comp_median_ms=1.0, link1_comp_median_ms=0.5,
                             link0_comp_std_ms=0.2, link1_comp_std_ms=0.1,
                             audit_sn_changed=0, audit_intra_flow_inv=0, audit_sn_dup=0, audit_untagged_tx=2)
                    rows.append(r)
    return rows


def dump(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def analyse(tmp, rows):
    raw = tmp / "main.csv"
    dump(rows, raw)
    p = subprocess.run([sys.executable, str(NS3 / "analyze_results.py"), "--only", "main", "--main", str(raw),
                        "--out", str(tmp / "out")], capture_output=True, text=True)
    return p


def manual_paired(x, y):
    d = np.asarray(x) - np.asarray(y)
    n = len(d)
    se = d.std(ddof=1) / math.sqrt(n)
    t = d.mean() / se
    return d.mean(), t, 2 * stats.t.sf(abs(t), n - 1)


def test_planted_effects_recovered(template, tmp_path):
    rng = np.random.default_rng(1)
    eff = {("A2", "L2"): (1.0, 0.7), ("A1", "L1"): (0.8, 0.8)}
    rows = synth_main(template, rng, eff)
    p = analyse(tmp_path, rows)
    assert p.returncode == 0, p.stderr
    comps = list(csv.DictReader(open(tmp_path / "out" / "comparisons.csv")))
    prim = [c for c in comps if c["family"] == "PRIMARY"]
    assert len(prim) == 1 and (prim[0]["cond"], prim[0]["load"]) == ("A2", "L2")
    # expected values recomputed independently from the raw rows
    sel = lambda arm: np.array([r["cross_wait_ms"] for r in rows if r["cond"] == "A2" and r["load"] == "L2" and r["scheduler"] == arm])  # noqa: E731
    d, t, pv = manual_paired(sel(2), sel(0))
    assert float(prim[0]["diff"]) == pytest.approx(d, rel=1e-9)
    assert float(prim[0]["p_raw"]) == pytest.approx(pv, rel=1e-6)
    se = np.std(sel(2) - sel(0), ddof=1) / math.sqrt(30)
    assert float(prim[0]["ci_lo"]) == pytest.approx(d - stats.t.ppf(0.975, 29) * se, rel=1e-9)
    assert float(prim[0]["p_raw"]) < 1e-6 and float(prim[0]["rel_reduction_pct"]) == pytest.approx(30, abs=3)
    # F1 (Mean-Only vs FIFO): only A1xL1 has an effect; Holm must adjust upward by at most the family size
    f1 = {(c["cond"], c["load"]): c for c in comps if c["family"] == "F1"}
    assert len(f1) == 9
    for c in f1.values():
        assert float(c["p_holm"]) >= float(c["p_raw"]) - 1e-15
    assert float(f1[("A1", "L1")]["p_holm"]) < 0.05
    # every cell's raw p-value must equal an independent hand-computed paired t-test
    for (cond, load), c in f1.items():
        x = np.array([r["cross_wait_ms"] for r in rows if r["cond"] == cond and r["load"] == load and r["scheduler"] == 1])
        y = np.array([r["cross_wait_ms"] for r in rows if r["cond"] == cond and r["load"] == load and r["scheduler"] == 0])
        _, _, pv_hand = manual_paired(x, y)
        assert float(c["p_raw"]) == pytest.approx(pv_hand, rel=1e-6)
    # F3 excludes the confirmatory cell
    assert len([c for c in comps if c["family"] == "F3"]) == 8
    # Holm hand check on F1
    ps = sorted(float(c["p_raw"]) for c in f1.values())
    m = 9
    run, hand = 0.0, {}
    for i, pv_ in enumerate(ps):
        run = max(run, min(1.0, (m - i) * pv_))
        hand[pv_] = run
    for c in f1.values():
        assert float(c["p_holm"]) == pytest.approx(hand[float(c["p_raw"])], rel=1e-9)


def test_tost_declares_equivalence_only_when_inside_margin(template, tmp_path):
    rng = np.random.default_rng(2)
    rows = synth_main(template, rng, {("A0", "L0"): (1.0, 1.0)})  # Full ~ Mean up to noise 0.005 ~ 2% of mean
    # Mean and Full share the same underlying value -> difference only noise; margin = 5% of 0.25 = 0.0125
    p = analyse(tmp_path, rows)
    assert p.returncode == 0, p.stderr
    f2 = [c for c in csv.DictReader(open(tmp_path / "out" / "comparisons.csv")) if c["family"] == "F2"]
    assert all(c["equivalent_at_5pct"] == "True" for c in f2)
    # a real 20% difference must NOT be declared equivalent
    rows = synth_main(template, np.random.default_rng(3), {("A0", "L0"): (1.0, 0.8)})
    p = analyse(tmp_path, rows)
    f2 = {(c["cond"], c["load"]): c for c in csv.DictReader(open(tmp_path / "out" / "comparisons.csv")) if c["family"] == "F2"}
    assert f2[("A0", "L0")]["equivalent_at_5pct"] == "False"


@pytest.mark.parametrize("defect", ["duplicate", "missing_seed", "audit", "config", "rows", "build", "nan"])
def test_analysis_fails_loudly_on_invalid_data(template, tmp_path, defect):
    rows = synth_main(template, np.random.default_rng(4), {})
    if defect == "duplicate":
        rows[5]["seed"], rows[5]["scheduler"] = rows[0]["seed"], rows[0]["scheduler"]
        rows[5]["cond"], rows[5]["load"] = rows[0]["cond"], rows[0]["load"]
    elif defect == "missing_seed":
        rows[7]["seed"] = 99
    elif defect == "audit":
        rows[3]["audit_sn_dup"] = 1
    elif defect == "config":
        rows[9]["mcs0"] = 3
    elif defect == "rows":
        rows = rows[:-1]
    elif defect == "build":
        rows[2]["build_id"] = "other"
    elif defect == "nan":
        rows[4]["cross_wait_ms"] = "nan"
    p = analyse(tmp_path, rows)
    assert p.returncode != 0, "analysis accepted invalid data"
