"""analyze_study4.py - H13/H14/H15 and V10/V11 exactly as in PREREGISTRATION_STUDY4.md.
Python cells: r = sum X / sum E over (seed, victim) rows, q = sum X / sum e2e_full; bootstrap resamples seeds (all victims of a seed
together), 10,000, default_rng(20261025). ns-3 cells: ratio of means, with/without arms resampled independently.
H14 cell bootstrap: default_rng(20261026). V10 sample (5% of Python rows): default_rng(20261027) (seed not fixed by the
preregistration; chosen here and disclosed). Writes results/analysis_study4.json."""
import csv
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
B = 10_000
D_MIN_PY = 1.69
rng_cell = np.random.default_rng(20261025)
rng_h14 = np.random.default_rng(20261026)
rng_v10 = np.random.default_rng(20261027)


def ci(x):
    return [float(np.nanpercentile(x, 2.5)), float(np.nanpercentile(x, 97.5))]


def rank(a):
    a = np.asarray(a, float)
    order = np.argsort(a, kind="mergesort")
    r = np.empty(len(a))
    r[order] = np.arange(len(a))
    for v in np.unique(a):
        m = a == v
        if m.sum() > 1:
            r[m] = r[m].mean()
    return r


def spearman(a, b):
    ra, rb = rank(a), rank(b)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def read(path):
    return list(csv.DictReader(open(path)))


def python_cells():
    rows = read(RES / "raw_s4_py.csv")
    out = {}
    keys = sorted({(r["scale"], float(r["load"]), float(r["dmu"])) for r in rows})
    for k in keys:
        rr = [r for r in rows if (r["scale"], float(r["load"]), float(r["dmu"])) == k]
        seeds = sorted({int(r["seed"]) for r in rr})
        S = len(seeds)
        idx = {s: i for i, s in enumerate(seeds)}
        E, X, T = (np.zeros(S) for _ in range(3))
        cnt = np.zeros(S)
        for r in rr:
            i = idx[int(r["seed"])]
            E[i] += float(r["e2e_full"]) - float(r["e2e_solo"])
            X[i] += float(r["X_full"])
            T[i] += float(r["e2e_full"])
            cnt[i] += 1
        bi = rng_cell.integers(0, S, (B, S))
        Eb, Xb, Cb = E[bi].sum(1), X[bi].sum(1), cnt[bi].sum(1)
        Epoint = E.sum() / cnt.sum()
        defined = bool(ci(Eb / Cb)[0] > 0)
        r_ = X.sum() / E.sum()
        q = X.sum() / T.sum()
        qf = X.sum() / (T.sum() - D_MIN_PY * cnt.sum())
        min_solo = min(float(r["e2e_solo"]) for r in rr)
        out[f"{k[0]}/load{k[1]}/dmu{k[2]}"] = dict(
            kind="python", n_rows=len(rr), E_ms=dict(point=float(Epoint), ci=ci(Eb / Cb)), defined=defined,
            r=float(r_), r_ci=ci(Xb / Eb) if defined else [float("nan")] * 2, q=float(q), q_floor=float(qf),
            h13_exact_ok=bool(r_ >= q - 1e-9) if defined else None,
            h13_floor_ok=bool(r_ >= qf - 1e-9) if defined else None,
            min_row_e2e_solo=min_solo, d_min_valid=bool(min_solo >= D_MIN_PY))
    return out, rows


def ns3_cells():
    rows = read(RES / "raw_s4_ns3.csv")
    out = {}
    for cond in ("A1", "A2"):
        for frac in (0.15, 0.45, 0.70):
            w = [r for r in rows if r["cond"] == cond and float(r["frac"]) == frac and r["arm"] == "with"]
            n = [r for r in rows if r["cond"] == cond and float(r["frac"]) == frac and r["arm"] == "without"]
            assert len(w) == 30 and len(n) == 30
            dw = np.array([float(r["ls_delay_mean_ms"]) for r in w])
            dn = np.array([float(r["ls_delay_mean_ms"]) for r in n])
            xw = np.array([float(r["cross_wait_ms"]) for r in w])
            iw = rng_cell.integers(0, 30, (B, 30))
            inn = rng_cell.integers(0, 30, (B, 30))
            Eb = dw[iw].mean(1) - dn[inn].mean(1)
            Xb = xw[iw].mean(1)
            E, X, T = dw.mean() - dn.mean(), xw.mean(), dw.mean()
            defined = bool(ci(Eb)[0] > 0)
            r_, q = X / E, X / T
            out[f"{cond}/F{frac}"] = dict(
                kind="ns3", E_ms=dict(point=float(E), ci=ci(Eb)), defined=defined, r=float(r_),
                r_ci=ci(Xb / Eb) if defined else [float("nan")] * 2, q=float(q), q_floor=float(q),
                h13_point_ok=bool(r_ >= q - 1e-9) if defined else None, X_ms=float(X), e2e_obs_ms=float(T))
    return out, rows


def main():
    py, pyrows = python_cells()
    ns, nsrows = ns3_cells()
    cells = {**py, **ns}
    dfn = {k: c for k, c in cells.items() if c["defined"]}
    out = dict(n_cells=len(cells), n_defined=len(dfn), undefined_cells=[k for k, c in cells.items() if not c["defined"]],
               cells=cells)
    # H13
    py_def = [c for c in py.values() if c["defined"]]
    ns_def = [c for c in ns.values() if c["defined"]]
    out["H13"] = dict(
        python_violations=sum(not c["h13_exact_ok"] for c in py_def), python_defined=len(py_def),
        python_floor_violations=sum(not c["h13_floor_ok"] for c in py_def),
        python_d_min_valid_all_cells=all(c["d_min_valid"] for c in py_def),
        ns3_violations=sum(not c["h13_point_ok"] for c in ns_def), ns3_defined=len(ns_def),
        verdict=("confirmed" if all(c["h13_exact_ok"] for c in py_def) else "REFUTED (Python violation)"))

    # H14
    def corr_block(keys, rng=None):
        q = np.array([cells[k]["q"] for k in keys])
        r = np.array([cells[k]["r"] for k in keys])
        d = dict(n=len(keys), rho=spearman(q, r))
        if rng is not None and len(keys) >= 3:
            bi = rng.integers(0, len(keys), (B, len(keys)))
            bs = np.array([spearman(q[i], r[i]) for i in bi])
            d["n_degenerate_resamples"] = int(np.isnan(bs).sum())
            d["ci"] = ci(bs)
        return d
    pooled = corr_block(list(dfn), rng_h14)
    out["H14"] = dict(pooled=pooled,
                      python=corr_block([k for k, c in dfn.items() if c["kind"] == "python"]),
                      ns3=corr_block([k for k, c in dfn.items() if c["kind"] == "ns3"]))
    out["H14"]["verdict"] = "confirmed" if pooled["rho"] >= 0.70 and pooled["ci"][0] > 0.40 else "not confirmed"
    # H15 (descriptive)
    tp = sum(c["q"] >= 0.30 and c["r"] >= 0.5 for c in dfn.values())
    fp = sum(c["q"] >= 0.30 and c["r"] < 0.5 for c in dfn.values())
    fn = sum(c["q"] < 0.30 and c["r"] >= 0.5 for c in dfn.values())
    tn = sum(c["q"] < 0.30 and c["r"] < 0.5 for c in dfn.values())
    out["H15"] = dict(tp=tp, fp=fp, fn=fn, tn=tn, precision=(tp / (tp + fp) if tp + fp else None),
                      recall=(tp / (tp + fn) if tp + fn else None), descriptive_only=True)
    # V10
    sig_viol = sum(int(r["sig_equal"]) == 0 for r in pyrows)
    sample = rng_v10.choice(len(pyrows), size=int(round(0.05 * len(pyrows))), replace=False)

    def gap(r):
        E = float(r["e2e_full"]) - float(r["e2e_solo"])
        parts = (float(r["net_full"]) - float(r["net_solo"])) + (float(r["S_full"]) - float(r["S_solo"])) + float(r["X_full"])
        return abs(E - parts)
    gs = [gap(pyrows[i]) for i in sample]
    allg = [gap(r) for r in pyrows]
    out["V10"] = dict(replay_signature_violations=int(sig_viol), n_rows=len(pyrows), sample_n=len(sample),
                      identity_max_gap_sample=float(max(gs)), identity_max_gap_all_rows=float(max(allg)),
                      identity_ok_sample=bool(max(gs) <= 1e-9),
                      n_rows_n_full_ne_n_solo=int(sum(r["n_full"] != r["n_solo"] for r in pyrows)),
                      verdict="pass" if sig_viol == 0 and max(gs) <= 1e-9 else "FAIL")
    # V11
    nob = [r for r in nsrows if r["arm"] == "without"]
    wb = [r for r in nsrows if r["arm"] == "with"]
    clean = all(float(r["bulk_sent"]) == 0 and float(r["cross_wait_ms"]) == 0 for r in nob)
    # frozen runtime-audit rule (ns3/preregistration.md): three counters == 0, untagged_tx <= 20 (ARP priming only)
    aud = {k: int(sum(float(r[k]) != 0 for r in nsrows)) for k in ("audit_sn_changed", "audit_intra_flow_inv", "audit_sn_dup")}
    aud["audit_untagged_tx_over_20"] = int(sum(float(r["audit_untagged_tx"]) > 20 for r in nsrows))
    aud["audit_untagged_tx_max"] = int(max(float(r["audit_untagged_tx"]) for r in nsrows))
    out["V11"] = dict(nobulk_runs=len(nob), nobulk_all_clean=bool(clean), with_runs=len(wb),
                      runs_with_nonzero_audit_counter=aud,
                      verdict="pass" if clean and not any(v for k, v in aud.items() if k != "audit_untagged_tx_max") else "FAIL/inspect")
    # exploratory: OLS r ~ q on defined cells
    qs = np.array([c["q"] for c in dfn.values()])
    rs = np.array([c["r"] for c in dfn.values()])
    A = np.vstack([qs, np.ones_like(qs)]).T
    coef = np.linalg.lstsq(A, rs, rcond=None)[0]
    out["EXPLORATORY_ols_r_on_q"] = dict(slope=float(coef[0]), intercept=float(coef[1]),
                                         r2=float(1 - ((rs - A @ coef) ** 2).sum() / ((rs - rs.mean()) ** 2).sum()))
    (RES / "analysis_study4.json").write_text(json.dumps(out, indent=1, default=float))
    for k, c in cells.items():
        ok = c.get("h13_exact_ok", c.get("h13_point_ok"))
        print(k, "E=%.4f" % c["E_ms"]["point"], "def" if c["defined"] else "UNDEF", "r=%.3f q=%.3f" % (c["r"], c["q"]),
              "-" if ok is None else ("ok" if ok else "VIOL"))
    for k in ("H13", "H14", "H15", "V10", "V11", "EXPLORATORY_ols_r_on_q"):
        print(k, json.dumps(out[k], default=float))


if __name__ == "__main__":
    main()
