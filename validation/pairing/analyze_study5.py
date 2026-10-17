"""analyze_study5.py - H16-H19 exactly as in PREREGISTRATION_STUDY5.md, plus exploratory X9, X10, X12, X13, X15 as in
STUDY5_EXPLORATORY_PLAN.md. Bootstrap: 10,000 resamples; H17/H18/X12 seeds-cluster default_rng(20261031); X15 default_rng(20261032).
Writes results/analysis_study5.json."""
import csv
import itertools
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import airport as ap
import study as st
from run_study5 import shapley_poisson_chunked, X15_CELLS
from study2 import shapley_for_victim

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
B = 10_000
rng_main = np.random.default_rng(20261031)
rng_x15 = np.random.default_rng(20261032)


def read(name):
    return list(csv.DictReader(open(RES / name)))


def ci(x):
    return [float(np.nanpercentile(x, 2.5)), float(np.nanpercentile(x, 97.5))]


def fl(v):
    return float("nan") if v in ("", "nan") else float(v)


# ------------------------------------------------------------------------------------------------ H16
def h16():
    rows = read("raw_s5_h16.csv")
    out, ok_all = {}, True
    for cell in sorted({r["cell"] for r in rows}):
        rr = [r for r in rows if r["cell"] == cell]
        clean = [r for r in rr if int(r["forced"]) == 0]
        is_sim = cell.startswith("C")
        err = lambda k: max((fl(r[k]) for r in clean if r[k] != ""), default=0.0)
        d = dict(n_runs=len(rr), n_forced_runs=len(rr) - len(clean), frac_forced=(len(rr) - len(clean)) / len(rr),
                 max_O1=err("O1"), max_O2=err("O2"), max_O3=err("O3"), max_O4=err("O4"), max_O5=err("O5") if is_sim else None,
                 max_O6_err=err("O6_err"), O6_violations=sum(int(r["O6_viol"]) for r in clean),
                 O7_violations=sum(int(r["O7_viol"]) for r in clean), n_O4_packets=sum(int(r["n_O4"]) for r in clean),
                 total_packets=sum(int(r["n_pkts"]) for r in clean),
                 mean_frac_blocked=float(np.mean([fl(r["frac_blocked"]) for r in clean])),
                 mean_frac_single_late=float(np.mean([fl(r["frac_single_late"]) for r in clean])),
                 mean_t_closed_ms=float(np.mean([fl(r["t_closed_ms"]) for r in clean])))
        tol = max(d["max_O1"], d["max_O2"], d["max_O3"], d["max_O4"], d["max_O5"] or 0.0, d["max_O6_err"]) <= 1e-9 \
            and d["O6_violations"] == 0 and d["O7_violations"] == 0
        d["cell_ok"] = bool(tol and (not is_sim or d["frac_forced"] <= 0.05))
        ok_all &= d["cell_ok"]
        out[cell] = d
    tr = read("raw_s5_h17_time.csv")
    cost = {c: dict(mean_replay_s=float(np.mean([fl(r["t_replay_s"]) for r in tr if r["cell"] == c])),
                    mean_closed_ms=float(np.mean([fl(r["t_closed_ms"]) for r in tr if r["cell"] == c])),
                    forced_total=sum(int(r["forced_total"]) for r in tr if r["cell"] == c)) for c in ("A", "B")}
    return dict(cells=out, verdict="confirmed" if ok_all else "NOT confirmed (see cells)", cost_S4_replay_vs_closed=cost)


# ------------------------------------------------------------------------------------------------ H17 / X9
def h17():
    coal = read("raw_s5_h17_coal.csv")
    blame = read("raw_s5_h17_blame.csv")
    res, x9 = {}, {}
    ids = [1, 2, 3, 4]
    full = 15
    for cell in ("A", "B"):
        data = defaultdict(dict)
        sig, forced = defaultdict(set), 0
        for r in coal:
            if r["cell"] != cell:
                continue
            key = (int(r["seed"]), int(r["victim"]))
            data[key][int(r["mask"])] = dict(Q=fl(r["net"]) + fl(r["S"]), X=fl(r["X"]), E=fl(r["e2e"]), net=fl(r["net"]), S=fl(r["S"]))
            sig[key].add(r["sig"])
            forced += int(r["forced"])
        seeds = sorted({k[0] for k in data})
        v13 = sum(len(s) > 1 for s in sig.values())
        gap, bad = 0.0, set()
        EQ, EX, EE, LQ, LX, LE = (np.zeros(len(seeds)) for _ in range(6))
        for si, s in enumerate(seeds):
            for i in ids:
                d = data[(s, i)]
                solo = 1 << (i - 1)
                if any(np.isnan(d[m][z]) for m in d for z in ("Q", "X", "E")):
                    bad.add(s)
                    continue
                EQ[si] += d[full]["Q"] - d[solo]["Q"]
                EX[si] += d[full]["X"] - d[solo]["X"]
                EE[si] += d[full]["E"] - d[solo]["E"]
                gap = max(gap, abs((d[full]["E"] - d[solo]["E"]) - ((d[full]["net"] - d[solo]["net"]) + (d[full]["S"] - d[solo]["S"])
                                                                       + (d[full]["X"] - d[solo]["X"]))))
                for j in ids:
                    if j == i:
                        continue
                    m = full - (1 << (j - 1))
                    LQ[si] += d[full]["Q"] - d[m]["Q"]
                    LX[si] += d[full]["X"] - d[m]["X"]
                    LE[si] += d[full]["E"] - d[m]["E"]
        good = [s for s in seeds if s not in bad]
        keep = np.array([s not in bad for s in seeds])
        EQ, EX, EE, LQ, LX, LE = (a[keep] for a in (EQ, EX, EE, LQ, LX, LE))
        n = len(EQ)
        bi = rng_main.integers(0, n, (B, n))
        R = lambda L, E: L.sum() / E.sum()
        Rb = lambda L, E: L[bi].sum(1) / E[bi].sum(1)
        r_ = dict(n_seeds=int(n), n_seeds_dropped=int((~keep).sum()),
                  R_Q=dict(point=R(LQ, EQ), ci=ci(Rb(LQ, EQ))), R_X=dict(point=R(LX, EX), ci=ci(Rb(LX, EX))),
                  R_e2e=dict(point=R(LE, EE), ci=ci(Rb(LE, EE))),
                  mean_E_ms=float(EE.sum() / (n * 4)), share_Q=float(EQ.sum() / EE.sum()), share_X=float(EX.sum() / EE.sum()),
                  V13_signature_violations=int(v13), V14_identity_gap=float(gap),
                  H17c_identity_gap=float(abs((LE.sum() - EE.sum()) - ((LQ.sum() - EQ.sum()) + (LX.sum() - EX.sum())))),
                  forced_advance_total=int(forced))
        r_["H17a_ok"] = bool(r_["R_Q"]["ci"][0] > 1)
        res[cell] = r_
        # ---- X9 (exploratory): blame matrices
        bl = defaultdict(dict)
        for r in blame:
            if r["cell"] == cell:
                bl[int(r["seed"])][(int(r["blocker"]), int(r["victim"]))] = [fl(r["airport"]), fl(r["releaser"])]
        pairs = [(j, i) for i in ids for j in ids if j != i]
        A = np.zeros((n, len(pairs)))
        Rl, RX, RE = np.zeros_like(A), np.zeros_like(A), np.zeros_like(A)
        for si, s in enumerate(good):
            for i in ids:
                DX = {frozenset(c): data[(s, i)][sum(1 << (f - 1) for f in c)]["X"]
                      for r_n in range(1, 5) for c in itertools.combinations(ids, r_n) if i in c}
                DE = {k: data[(s, i)][sum(1 << (f - 1) for f in k)]["E"] for k in DX}
                phiX, _ = shapley_for_victim(DX, i, ids)
                phiE, _ = shapley_for_victim(DE, i, ids)
                for pi, (j, ii) in enumerate(pairs):
                    if ii == i:
                        a, rl = bl[s].get((j, i), [0.0, 0.0])
                        A[si, pi], Rl[si, pi], RX[si, pi], RE[si, pi] = a, rl, phiX[j], phiE[j]
        bi2 = rng_main.integers(0, n, (B, n))

        def rel(M, ref):
            return np.abs(M.mean(0) - ref.mean(0)).sum() / np.abs(ref.mean(0)).sum()

        def rel_b(M, ref):
            return np.array([np.abs(M[b].mean(0) - ref[b].mean(0)).sum() / np.abs(ref[b].mean(0)).sum() for b in bi2])
        x9[cell] = dict(
            relL1_airport_vs_replayX=dict(point=float(rel(A, RX)), ci=ci(rel_b(A, RX))),
            relL1_releaser_vs_replayX=dict(point=float(rel(Rl, RX)), ci=ci(rel_b(Rl, RX))),
            relL1_airport_vs_replayE2E=dict(point=float(rel(A, RE)), ci=ci(rel_b(A, RE))),
            total_airport_over_total_replayE2E=float(A.mean(0).sum() / RE.mean(0).sum()),
            total_airport_over_total_replayX=float(A.mean(0).sum() / RX.mean(0).sum()),
            airport_vs_releaser_max_abs_diff=float(np.abs(A - Rl).max()))
    return dict(cells=res, verdict_H17a="confirmed" if all(c["H17a_ok"] for c in res.values()) else "NOT confirmed", X9=x9)


# ------------------------------------------------------------------------------------------------ H18 / X12 / X13
def stability(name, cells):
    rows = read(name)
    out, ok_b = {}, True
    for cell in cells:
        for e in (0.01, 0.1, 1.0):
            rr = [r for r in rows if r["cell"] == cell and abs(float(r["eps"]) - e) < 1e-12 and int(r["n_pos"]) > 0]
            n = np.array([int(r["n_pos"]) for r in rr], float)
            dsh = np.array([fl(r["mean_Dsh"]) for r in rr])
            drel = np.array([fl(r["mean_Drel"]) for r in rr])
            bi = rng_main.integers(0, len(rr), (B, len(rr)))
            diff = (n[bi] * (drel[bi] - dsh[bi])).sum(1) / n[bi].sum(1)
            point = float((n * (drel - dsh)).sum() / n.sum())
            c = ci(diff)
            allr = [r for r in rows if r["cell"] == cell and abs(float(r["eps"]) - e) < 1e-12]
            out[f"{cell}/eps{e}"] = dict(
                n_runs=len(rr), n_packets=int(n.sum()), mean_Dsh=float((n * dsh).sum() / n.sum()),
                mean_Drel=float((n * drel).sum() / n.sum()), diff_rel_minus_sh=dict(point=point, ci=c),
                B1_violations=sum(int(r["viol_B1"]) for r in allr), B2_violations=sum(int(r["viol_B2"]) for r in allr),
                max_ratio_shapley=max(fl(r["max_ratio_sh"]) for r in allr), max_ratio_releaser=max(fl(r["max_ratio_rel"]) for r in allr),
                H18b_ok=bool(c[0] > 0))
            ok_b &= c[0] > 0
    viol = sum(v["B1_violations"] + v["B2_violations"] for v in out.values())
    return dict(cells=out, bounds_violations=int(viol), all_H18b_ok=bool(ok_b))


# ------------------------------------------------------------------------------------------------ H19
def h19():
    rows = read("raw_s5_h19.csv")
    q = [r for r in rows if r["kind"] in ("v", "phi")]
    z = np.array([float(r["z"]) for r in q])
    eff = max(float(r["dbl_rel"]) for r in rows if r["kind"] == "efficiency")
    dbl = max(float(r["dbl_rel"]) for r in q)
    per = {}
    for p in sorted({r["param"] for r in rows}):
        zz = [abs(float(r["z"])) for r in q if r["param"] == p]
        per[p] = dict(n=len(zz), max_abs_z=max(zz),
                      max_rel_diff=max(abs(float(r["mc"]) - float(r["closed"])) / max(abs(float(r["closed"])), 1e-12)
                                       for r in q if r["param"] == p))
    ok = bool(np.abs(z).max() <= 4 and eff <= 1e-6 and dbl <= 1e-6)
    return dict(n_quantities=len(q), max_abs_z=float(np.abs(z).max()), n_abs_z_gt_3=int((np.abs(z) > 3).sum()),
                n_abs_z_gt_4=int((np.abs(z) > 4).sum()), efficiency_max_rel_gap=eff, quadrature_doubling_max_rel_change=dbl,
                per_param=per, verdict="confirmed" if ok else "NOT confirmed")


# ------------------------------------------------------------------------------------------------ X15
class Emp:
    def __init__(self, d):
        self.s = np.sort(np.asarray(d, float))
        self.cs = np.concatenate([[0.0], np.cumsum(self.s)])

    def cdf(self, x):
        return np.searchsorted(self.s, x, side="right") / len(self.s)

    def resid(self, x):
        x = np.asarray(x, float)
        k = np.searchsorted(self.s, x, side="right")
        return ((self.cs[-1] - self.cs[k]) - x * (len(self.s) - k)) / len(self.s)

    def upper(self, q=None):
        return float(self.s[-1])


def x15():
    dly = read("raw_s5_x15_delay.csv")
    obs = read("raw_s5_x15_obs.csv")
    out = {}
    for cell, (lm, dm) in X15_CELLS.items():
        flows, _, _ = st.build("S4", fer=0.01, delta_mu=dm)
        rate = {f.flow_id: f.rate_pkts_per_sec * lm / 1000.0 for f in flows}
        ids = sorted(rate)
        calib = {i: Emp([float(r["delay"]) for r in dly if r["cell"] == cell and int(r["seed"]) < 26850 and int(r["flow"]) == i])
                 for i in ids}
        pred_X, pred_phi = {}, {}
        for i in ids:
            others = [j for j in ids if j != i]
            others_d = [calib[j] for j in others]
            rates = [rate[i]] + [rate[j] for j in others]
            pred_X[i] = ap.poisson_game_value(calib[i], others_d, rates, list(range(len(others))))
            for j, v in zip(others, shapley_poisson_chunked(calib[i], others_d, rates, 20001, 1001)):
                pred_phi[(j, i)] = float(v)
        ev = [r for r in obs if r["cell"] == cell and int(r["seed"]) >= 26850]
        seeds = sorted({int(r["seed"]) for r in ev})
        pairs = [(j, i) for i in ids for j in ids if j != i]
        n_i = np.zeros((len(seeds), 4))
        Xs = np.zeros((len(seeds), 4))
        Ph = np.zeros((len(seeds), len(pairs)))
        si = {s: k for k, s in enumerate(seeds)}
        for r in ev:
            s, i, j = si[int(r["seed"])], int(r["victim"]) - 1, int(r["blocker"])
            nn = int(r["n"])
            n_i[s, i] = nn
            if j == 0:
                Xs[s, i] = fl(r["X_mean"]) * nn if nn else 0.0
            else:
                Ph[s, pairs.index((j, i + 1))] = fl(r["airport"]) * nn if nn else 0.0
        nb = len(seeds)
        bi = rng_x15.integers(0, nb, (B, nb))
        pX = np.array([pred_X[i] for i in ids])
        pP = np.array([pred_phi[p] for p in pairs])
        vp = np.array([p[1] - 1 for p in pairs])
        oX = Xs.sum(0) / n_i.sum(0)
        oP = Ph.sum(0) / n_i.sum(0)[vp]
        ratio_b = np.array([pX.mean() / (Xs[b].sum(0) / n_i[b].sum(0)).mean() if Xs[b].sum() > 0 else np.nan for b in bi])
        err_b = np.array([np.abs(pP - Ph[b].sum(0) / n_i[b].sum(0)[vp]).sum() / np.abs(Ph[b].sum(0) / n_i[b].sum(0)[vp]).sum()
                          if Ph[b].sum() > 0 else np.nan for b in bi])
        out[cell] = dict(load_multiplier=lm, extra_delay_ms=dm,
                         pred_cross_blocking_by_victim=[float(v) for v in pX], obs_cross_blocking_by_victim=[float(v) for v in oX],
                         mean_pred_cross_blocking_ms=float(pX.mean()), mean_obs_cross_blocking_ms=float(oX.mean()),
                         cell_pred_over_obs=dict(point=(float(pX.mean() / oX.mean()) if oX.mean() > 0 else None),
                                                 ci=ci(ratio_b) if np.isfinite(ratio_b).any() else None),
                         blame_relL1_error=dict(point=(float(np.abs(pP - oP).sum() / np.abs(oP).sum()) if np.abs(oP).sum() > 0 else None),
                                                ci=ci(err_b) if np.isfinite(err_b).any() else None))
    return out


def main():
    out = dict(H16=h16(), H17=h17(), H18=stability("raw_s5_h18.csv", ("C1", "C2", "C3")),
               X12=stability("raw_s5_x12.csv", ("C5", "G2", "G3")), H19=h19(), X15=x15())
    (RES / "analysis_study5.json").write_text(json.dumps(out, indent=1, default=float))
    h = out["H16"]
    print("H16", h["verdict"])
    keep = ("n_runs", "n_forced_runs", "max_O1", "max_O2", "max_O3", "max_O4", "max_O5", "max_O6_err", "O6_violations",
            "O7_violations", "mean_frac_blocked", "mean_frac_single_late", "cell_ok")
    for c, d in h["cells"].items():
        print("  ", c, {k: d[k] for k in keep})
    print("cost", h["cost_S4_replay_vs_closed"])
    for c, d in out["H17"]["cells"].items():
        print("H17", c, {k: d[k] for k in ("R_Q", "R_X", "R_e2e", "share_Q", "share_X", "V13_signature_violations", "V14_identity_gap",
                                         "H17c_identity_gap", "H17a_ok", "n_seeds_dropped")})
    print("H17a", out["H17"]["verdict_H17a"])
    print("X9", json.dumps(out["H17"]["X9"], default=float))
    for nm in ("H18", "X12"):
        print(nm, "bounds_violations", out[nm]["bounds_violations"], "all_H18b_ok", out[nm]["all_H18b_ok"])
        for k, v in out[nm]["cells"].items():
            print("  ", k, {a: v[a] for a in ("n_packets", "mean_Dsh", "mean_Drel", "diff_rel_minus_sh", "max_ratio_shapley",
                                              "max_ratio_releaser", "H18b_ok")})
    print("H19", {k: v for k, v in out["H19"].items() if k != "per_param"})
    print("X15", json.dumps(out["X15"], default=float))


if __name__ == "__main__":
    main()
