"""analyze.py - computes every number in the manuscript from results/raw_*.csv, following the preregistration
(PREREGISTRATION.md + Amendments 1-2). Cluster unit = seed; percentile bootstrap, 10,000 resamples,
numpy default_rng(20261017); p-values by paired sign-flip randomisation (10,000 flips)."""
import csv
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
B = 10_000
SEED = 20261017
ARMS = ("FIFO", "FullSASP", "MeanOnly")


def load(name):
    with open(RES / name) as f:
        return list(csv.DictReader(f))


def fl(rows, key):
    return np.array([float(r[key]) for r in rows])


def ci(samples):
    s = samples[~np.isnan(samples)]
    return [float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))]


def corr(a, b):
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def boot_idx(n, rng):
    return rng.integers(0, n, size=(B, n))


def bcorr(a, b, idx):
    A, Bm = a[idx], b[idx]
    A = A - A.mean(1, keepdims=True)
    Bm = Bm - Bm.mean(1, keepdims=True)
    den = np.sqrt((A ** 2).sum(1) * (Bm ** 2).sum(1))
    with np.errstate(invalid="ignore", divide="ignore"):
        return (A * Bm).sum(1) / den


def signflip_p(d, rng):
    obs = abs(d.mean())
    signs = rng.choice([-1.0, 1.0], size=(B, len(d)))
    return float(((np.abs((signs * d).mean(1)) >= obs - 1e-15).sum() + 1) / (B + 1))


def per_seed(rows, scale, design, arm, key):
    r = sorted((x for x in rows if x["scale"] == scale and x["design"] == design and x["arm"] == arm),
               key=lambda x: int(x["seed"]))
    return fl(r, key), [int(x["seed"]) for x in r]


def clopper_pearson(k, n, alpha=0.05):
    """Exact binomial CI by bisection on the CDF (no scipy)."""
    def cdf(x, p):                      # P(X <= x)
        ks = np.arange(0, x + 1)
        lg = np.array([math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) for i in ks])
        return float(np.exp(lg + ks * math.log(p) + (n - ks) * math.log1p(-p)).sum())

    def solve(f):
        lo, hi = 1e-12, 1 - 1e-12
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(lambda p: 1 - cdf(k - 1, p) < alpha / 2)
    upper = 1.0 if k == n else solve(lambda p: cdf(k, p) > alpha / 2)
    return [lower, upper]


def main():
    rng = np.random.default_rng(SEED)
    main_rows = load("raw_main.csv")
    out = dict(n_main_rows=len(main_rows))

    # ---------------- H1 / H3 / O1 per scale ----------------
    out["H1_H3"] = {}
    for scale in ("S2", "S4", "S8"):
        res = {}
        M = {d: {a: per_seed(main_rows, scale, d, a, "M")[0] for a in ARMS} for d in ("shared", "naive", "keyed")}
        sig = {d: {a: [r["arr_sig"] for r in sorted((x for x in main_rows if x["scale"] == scale and x["design"] == d
                                                      and x["arm"] == a), key=lambda x: int(x["seed"]))] for a in ARMS}
               for d in M}
        n = len(M["shared"]["FIFO"])
        idx = boot_idx(n, rng)
        pairs = [("FIFO", "FullSASP"), ("FIFO", "MeanOnly"), ("MeanOnly", "FullSASP")]
        for d in M:
            mm = np.array([[sig[d][a][i] != sig[d][b][i] for (a, b) in pairs] for i in range(n)], dtype=float)
            per_seed_mm = mm.mean(1)
            res[f"O1_mismatch_rate_{d}"] = dict(rate=float(per_seed_mm.mean()), ci=ci(per_seed_mm[idx].mean(1)),
                                                n_cells=int(mm.size), n_mismatch=int(mm.sum()))
        rho = {d: corr(M[d]["FIFO"], M[d]["FullSASP"]) for d in M}
        brho = {d: bcorr(M[d]["FIFO"], M[d]["FullSASP"], idx) for d in M}
        res["rho"] = {d: dict(point=rho[d], ci=ci(brho[d])) for d in M}
        dd = brho["keyed"] - brho["shared"]
        res["delta_rho_keyed_minus_shared"] = dict(point=rho["keyed"] - rho["shared"], ci=ci(dd))
        res["delta_rho_keyed_minus_naive"] = dict(point=rho["keyed"] - rho["naive"], ci=ci(brho["keyed"] - brho["naive"]))
        d_arr = {d: M[d]["FullSASP"] - M[d]["FIFO"] for d in M}
        vrf_point = float(d_arr["shared"].var(ddof=1) / d_arr["keyed"].var(ddof=1)) if d_arr["keyed"].var() > 0 else float("nan")
        bv = d_arr["shared"][idx].var(1, ddof=1) / d_arr["keyed"][idx].var(1, ddof=1)
        res["VRF_shared_over_keyed"] = dict(point=vrf_point, ci=ci(bv))
        res["VRF_shared_over_naive"] = dict(point=float(d_arr["shared"].var(ddof=1) / d_arr["naive"].var(ddof=1)),
                                            ci=ci(d_arr["shared"][idx].var(1, ddof=1) / d_arr["naive"][idx].var(1, ddof=1)))
        res["H1_confirmed"] = bool(rho["keyed"] - rho["shared"] >= 0.30 and ci(dd)[0] > 0)
        # H3
        widths = {}
        for d in d_arr:
            bm = d_arr[d][idx].mean(1)
            lo, hi = ci(bm)
            widths[d] = hi - lo
            res[f"H3_mean_d_{d}"] = dict(mean=float(d_arr[d].mean()), ci=[lo, hi], width=hi - lo,
                                         signflip_p=signflip_p(d_arr[d], rng), frac_seeds_positive=float((d_arr[d] > 0).mean()))
        res["H3_width_ratio_keyed_over_shared"] = widths["keyed"] / widths["shared"]
        res["H3_confirmed"] = bool(res["H3_width_ratio_keyed_over_shared"] <= 0.70)
        # Prop C sanity: FIFO mean M shared vs keyed within 2 pooled SE
        a, b = M["shared"]["FIFO"], M["keyed"]["FIFO"]
        se = math.sqrt(a.var(ddof=1) / n + b.var(ddof=1) / n)
        res["PropC_FIFO_mean_M"] = dict(shared=float(a.mean()), keyed=float(b.mean()), abs_diff=float(abs(a.mean() - b.mean())),
                                        pooled_se=se, within_2se=bool(abs(a.mean() - b.mean()) <= 2 * se))
        # cost
        cost = {}
        for d in M:
            w = fl([x for x in main_rows if x["scale"] == scale and x["design"] == d], "wall_ms")
            cost[d] = dict(median_ms=float(np.median(w)), q1=float(np.percentile(w, 25)), q3=float(np.percentile(w, 75)))
        res["cost_wall_ms"] = cost
        out["H1_H3"][scale] = res

    # ---------------- H2 (keyed, no drain) ----------------
    out["H2"] = {}
    for scale in ("S2", "S4", "S8"):
        res = {}
        for arm in ARMS:
            g, _ = per_seed(main_rows, scale, "keyed", arm, "generated")
            u, _ = per_seed(main_rows, scale, "keyed", arm, "undelivered")
            ld, _ = per_seed(main_rows, scale, "keyed", arm, "late_discards")
            dr, _ = per_seed(main_rows, scale, "keyed", arm, "dropped_retry")
            ed, _ = per_seed(main_rows, scale, "keyed", arm, "e2e_delivered")
            ec, _ = per_seed(main_rows, scale, "keyed", arm, "e2e_censored")
            n = len(g)
            idx = boot_idx(n, rng)
            bu = u[idx].sum(1) / g[idx].sum(1)
            U = (ec.mean() - ed.mean()) / ed.mean()
            bU = (ec[idx].mean(1) - ed[idx].mean(1)) / ed[idx].mean(1)
            res[arm] = dict(undelivered_fraction=dict(point=float(u.sum() / g.sum()), ci=ci(bu)),
                            understatement_U=dict(point=float(U), ci=ci(bU)),
                            late_discards_per_run=float(ld.mean()), dropped_after_retry_per_run=float(dr.mean()),
                            generated_per_run=float(g.mean()),
                            material=bool(u.sum() / g.sum() >= 0.02 and ci(bu)[0] >= 0.01))
        res["all_arms_material"] = all(res[a]["material"] for a in ARMS)
        out["H2"][scale] = res
    # ranking flip (exploratory), S2
    ed_f, _ = per_seed(main_rows, "S2", "keyed", "FIFO", "e2e_delivered")
    ed_s, _ = per_seed(main_rows, "S2", "keyed", "FullSASP", "e2e_delivered")
    ec_f, _ = per_seed(main_rows, "S2", "keyed", "FIFO", "e2e_censored")
    ec_s, _ = per_seed(main_rows, "S2", "keyed", "FullSASP", "e2e_censored")
    out["H2"]["exploratory_ranking_flip_fraction_S2"] = float((np.sign(ed_s - ed_f) != np.sign(ec_s - ec_f)).mean())
    drain = load("raw_drain.csv")
    dz = [r for r in drain if float(r["fer"]) == 0.0]
    d1 = [r for r in drain if float(r["fer"]) == 0.01]
    out["H2"]["drain_control"] = dict(
        fer0_rows=len(dz), fer0_max_undelivered=int(max(float(r["undelivered"]) for r in dz)),
        fer0_max_late_discards=int(max(float(r["late_discards"]) for r in dz)),
        validity_check_passed=bool(all(float(r["undelivered"]) == 0 for r in dz)),
        fer001_undelivered_per_run={a: float(np.mean([float(r["undelivered"]) for r in d1 if r["arm"] == a])) for a in ARMS},
        fer001_late_discards_per_run={a: float(np.mean([float(r["late_discards"]) for r in d1 if r["arm"] == a])) for a in ARMS})

    # ---------------- H4 ----------------
    h4 = load("raw_h4.csv")
    out["H4"] = {}
    for arm in ("FIFO", "FullSASP"):
        r = sorted((x for x in h4 if x["arm"] == arm), key=lambda x: int(x["seed"]))
        w, wo = fl(r, "self1_with"), fl(r, "self1_without")
        ok = ~(np.isnan(w) | np.isnan(wo))
        w, wo = w[ok], wo[ok]
        dsig = np.abs(w - wo)
        idx = boot_idx(len(w), rng)
        ratio = dsig.mean() / w.mean() if w.mean() > 0 else float("nan")
        bratio = dsig[idx].mean(1) / w[idx].mean(1)
        out["H4"][arm] = dict(n_seeds_used=int(ok.sum()), mean_S1_with=float(w.mean()), mean_S1_without=float(wo.mean()),
                              mean_abs_diff=float(dsig.mean()), ratio=float(ratio), ratio_ci=ci(bratio),
                              trace_control_max_abs_diff=float(fl(r, "trace_control_maxdiff").max()),
                              trace_validity_passed=bool(fl(r, "trace_control_maxdiff").max() <= 1e-9),
                              violation_confirmed=bool(ratio >= 0.10 and ci(bratio)[0] >= 0.05))

    # ---------------- H5 ----------------
    h5 = load("raw_h5.csv")

    def sel(v, s):
        return sorted((x for x in h5 if x["variant"] == v and x["scen"] == s), key=lambda x: int(x["seed"]))
    out["H5"] = {}
    for v in ("shipped", "single"):
        r = sel(v, "default")
        out["H5"][f"O5_{v}"] = dict(attempts=int(fl(r, "attempts").sum()), draws=int(fl(r, "draws").sum()),
                                    violation_rate=float(fl(r, "not_one").sum() / fl(r, "attempts").sum()))
    rs, r1 = sel("shipped", "bursts"), sel("single", "bursts")
    ss, ns_, s1, n1 = fl(rs, "sum_len"), fl(rs, "n_runs"), fl(r1, "sum_len"), fl(r1, "n_runs")
    idx = boot_idx(len(rs), rng)
    L_s, L_1 = ss.sum() / ns_.sum(), s1.sum() / n1.sum()
    rel = (L_s - L_1) / L_1
    brel = ((ss[idx].sum(1) / ns_[idx].sum(1)) - (s1[idx].sum(1) / n1[idx].sum(1))) / (s1[idx].sum(1) / n1[idx].sum(1))
    out["H5"]["burst_run_length"] = dict(shipped=float(L_s), single=float(L_1), rel_diff=float(rel), ci=ci(brel),
                                         material=bool(abs(rel) >= 0.20 and (ci(brel)[0] > 0 or ci(brel)[1] < 0)))
    for v in ("shipped", "single"):
        r = sel(v, "nobursts")
        k, n = int(fl(r, "n_lost").sum()), int(fl(r, "n_att").sum())
        cp = clopper_pearson(k, n)
        out["H5"][f"loss_frequency_nobursts_{v}"] = dict(k=k, n=n, freq=k / n, exact95=cp, contains_fer=bool(cp[0] <= 0.01 <= cp[1]))

    # ---------------- H6 ----------------
    h6 = load("raw_h6.csv")
    out["H6"] = {}
    for arm in ("FIFO", "FullSASP", "MeanOnly", "LeakyGlobal", "LeakyLocal"):
        r = [x for x in h6 if x["arm"] == arm]
        out["H6"][arm] = dict(violations=int(fl(r, "violated").sum()), n=len(r), mean_packets_compared=float(fl(r, "n_compared").mean()))
    out["H6"]["pass"] = bool(all(out["H6"][a]["violations"] == 0 for a in ARMS) and out["H6"]["LeakyGlobal"]["violations"] >= 95)

    # ---------------- E1 (exploratory) ----------------
    e1 = load("raw_e1.csv")
    out["E1_exploratory_D0_arrival_mismatch_by_fer"] = {
        f"{fer}": dict(mismatch_seeds=int(sum(int(x["mismatch"]) for x in e1 if float(x["fer"]) == fer)),
                       n=int(sum(1 for x in e1 if float(x["fer"]) == fer)))
        for fer in sorted({float(x["fer"]) for x in e1})}

    out["manifest"] = json.loads((RES / "run_manifest.json").read_text())
    (RES / "analysis_numbers.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "manifest"}, indent=1, default=float)[:200000])


if __name__ == "__main__":
    main()
