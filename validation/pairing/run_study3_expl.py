"""run_study3_expl.py - EXPLORATORY X6 (window coupling for pinned flows) and X7 (aligned decision test), fresh seeds
(see STUDY3_AMENDMENT_AND_EXPLORATORY_PLAN.md). Writes results/exploratory_study3.json."""
import itertools
import json
from pathlib import Path

import numpy as np

import study as st
import study2 as s2
from run_study3 import CountingPinned

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
B = 10_000
D = st.DURATION_MS


def ci(x):
    return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]


# ---------------- X6 ----------------
def pinned_run(win, rate_mult, keep, seed):
    flows, links, chans = st.build("S2", fer=0.01)
    flows = [f for f in flows if f.flow_id in keep]
    for f in flows:
        f.rate_pkts_per_sec *= rate_mult
    sched = CountingPinned({1: 0, 2: 1})
    sim = st.StudySimulator(flows, links, chans, sched, win_size=win, seed=seed, design="keyed")
    rx = sim.run(duration_ms=D)
    out = {}
    for f in flows:
        mine = [p for p in rx.delivered_packets if p.flow_id == f.flow_id]
        n = len(mine)
        out[f.flow_id] = (n, sum(p.end_to_end_delay for p in mine) / n if n else float("nan"),
                          sum(p.cross_blocking for p in mine) / n if n else float("nan"))
    return out, sched.stalls


def x6():
    rng = np.random.default_rng(20261023)
    out = {}
    seeds = list(range(23100, 23200))
    for rate_mult in (1.0, 1.4):
        for win in (4, 8, 16, 64):
            sE, sX, stalled = [], [], 0
            for s in seeds:
                full, st_f = pinned_run(win, rate_mult, {1, 2}, s)
                E = X = 0.0
                ok = True
                stall_any = st_f > 0
                for i in (1, 2):
                    solo, st_s = pinned_run(win, rate_mult, {i}, s)
                    stall_any |= st_s > 0
                    if full[i][0] == 0 or solo[i][0] == 0:
                        ok = False
                        break
                    E += full[i][1] - solo[i][1]
                    X += full[i][2]
                if ok:
                    sE.append(E)
                    sX.append(X)
                    stalled += stall_any
            sE, sX = np.array(sE), np.array(sX)
            idx = rng.integers(0, len(sE), (B, len(sE)))
            g = abs(sE.sum() - sX.sum()) / sE.sum()
            out[f"load{rate_mult}_win{win}"] = dict(
                n_seeds=len(sE), frac_runs_with_stall=float(stalled / len(sE)), mean_E_ms=float(sE.mean() / 2),
                mean_X_ms=float(sX.mean() / 2),
                gap=dict(point=float(g), ci=ci(np.abs(sE[idx].sum(1) - sX[idx].sum(1)) / sE[idx].sum(1))))
        print("x6 load", rate_mult, flush=True)
    return out


# ---------------- X7 ----------------
IDS = [1, 2, 3, 4]
W = {1: 1.0, 2: 1.0, 3: 50.0, 4: 50.0}


def mask_of(s):
    return sum(1 << (i - 1) for i in s)


def x7():
    rng = np.random.default_rng(20261024)
    seeds = list(range(24000, 24100))
    cal, ev = seeds[:50], seeds[50:]
    full = frozenset(IDS)
    out = {}
    for arm in ("FullSASP", "FIFO"):
        stat = {}
        for s in seeds:
            dl, bl = {}, None
            for mask, keep in s2.masks(IDS):
                sim, rx, o = s2.run_coalition("S4", keep, arm, s, blame=(keep == full))
                for f, v in o.items():
                    dl[(f, mask)] = v["D"]
                if keep == full:
                    bl = rx
            btr, bsh, gu, gw = np.zeros(4), np.zeros(4), np.zeros(4), np.zeros(4)
            for i in IDS:
                others = [o for o in IDS if o != i]
                subs = [frozenset(T) | {i} for r_ in range(4) for T in itertools.combinations(others, r_)]
                vals = {sub: dl[(i, mask_of(sub))] for sub in subs}
                phi, E = s2.shapley_for_victim(vals, i, IDS)
                n = sum(1 for p in bl.delivered_packets if p.flow_id == i)
                for j in others:
                    btr[j - 1] += bl.blame.get((j, i), 0.0) / n if n else 0.0
                    bsh[j - 1] += phi[j]
                    loo = vals[full] - vals[full - {j}]
                    gu[j - 1] += loo
                    gw[j - 1] += W[i] * loo
            stat[s] = (btr, bsh, gu, gw)
        res = {}
        mTR = np.mean([stat[s][0] for s in cal], 0)
        mSH = np.mean([stat[s][1] for s in cal], 0)
        pick = dict(TR=int(np.argmax(mTR)), SH=int(np.argmax(mSH)))
        for obj, k in (("unweighted", 2), ("weighted", 3)):
            G = np.array([stat[s][k] for s in ev])
            gain = {p: G[:, j] for p, j in pick.items()}
            gain["RAND"] = G.mean(1)
            oj = int(np.argmax(G.mean(0)))
            idx = rng.integers(0, len(ev), (B, len(ev)))

            def diff(a, b):
                d = gain[a] - gain[b]
                return dict(mean=float(d.mean()), ci=ci(d[idx].mean(1)))
            res[obj] = dict(oracle_flow=oj + 1, mean_gain_by_flow=[float(x) for x in G.mean(0)],
                            gain={p: float(v.mean()) for p, v in gain.items()},
                            SH_minus_TR=diff("SH", "TR"), TR_minus_RAND=diff("TR", "RAND"), SH_minus_RAND=diff("SH", "RAND"),
                            capture_ratio={p: float(gain[p].mean() / G.mean(0)[oj]) for p in gain})
        res["picked_flow"] = {p: j + 1 for p, j in pick.items()}
        res["calibration_B_TR"] = [float(x) for x in mTR]
        res["calibration_B_SH"] = [float(x) for x in mSH]
        out[arm] = res
        print("x7", arm, flush=True)
    return out


def main():
    res = dict(label="EXPLORATORY: fresh seeds, no preregistered thresholds", X6_window_coupling=x6(), X7_aligned_decision=x7())
    (RES / "exploratory_study3.json").write_text(json.dumps(res, indent=1, default=float))
    r = lambda v: round(v, 4) if isinstance(v, float) else v
    for k, v in res["X6_window_coupling"].items():
        print(k, {a: (r(b) if not isinstance(b, dict) else {c: (r(d) if not isinstance(d, list) else [r(x) for x in d])
                                                           for c, d in b.items()}) for a, b in v.items()})
    for arm, v in res["X7_aligned_decision"].items():
        print(arm, "picked", v["picked_flow"])
        for obj in ("unweighted", "weighted"):
            print("  ", obj, "oracle", v[obj]["oracle_flow"], "gain", {p: r(x) for p, x in v[obj]["gain"].items()},
                  "SH-TR", r(v[obj]["SH_minus_TR"]["mean"]), [r(x) for x in v[obj]["SH_minus_TR"]["ci"]],
                  "TR-RAND", r(v[obj]["TR_minus_RAND"]["mean"]), [r(x) for x in v[obj]["TR_minus_RAND"]["ci"]],
                  "SH-RAND", r(v[obj]["SH_minus_RAND"]["mean"]), [r(x) for x in v[obj]["SH_minus_RAND"]["ci"]])


if __name__ == "__main__":
    main()
