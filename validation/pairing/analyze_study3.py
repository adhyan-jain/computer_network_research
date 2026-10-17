"""analyze_study3.py - H10 and H12 exactly as in PREREGISTRATION_STUDY3.md (H11 is analysed in analyze_study3_ns3.py).
Percentile bootstraps over seeds, 10,000 resamples; rng seeds 20261020 (H10) and 20261022 (H12)."""
import csv
import itertools
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import study2 as s2

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
B = 10_000
W = {1: 1.0, 2: 1.0, 3: 50.0, 4: 50.0}
IDS = [1, 2, 3, 4]


def ci(x):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]


def mask_of(s):
    return sum(1 << (i - 1) for i in s)


def h10():
    rng = np.random.default_rng(20261020)
    rows = list(csv.DictReader(open(RES / "raw_s3_h10.csv")))
    out = {}
    for cond in ("P256", "P64", "F64"):
        rs = [r for r in rows if r["cond"] == cond and int(r["n_full"]) > 0 and int(r["n_solo"]) > 0]
        seeds = sorted({int(r["seed"]) for r in rs})
        sidx = {s: k for k, s in enumerate(seeds)}
        sE, sX = np.zeros(len(seeds)), np.zeros(len(seeds))
        stall_seeds = set()
        for r in rs:
            k = sidx[int(r["seed"])]
            sE[k] += float(r["e2e_full"]) - float(r["e2e_solo"])
            sX[k] += float(r["X_full"])
            if int(r["stalls_full"]) + int(r["stalls_solo"]) > 0:
                stall_seeds.add(int(r["seed"]))
        idx = rng.integers(0, len(seeds), (B, len(seeds)))
        g = abs(sE.sum() - sX.sum()) / sE.sum()
        bg = np.abs(sE[idx].sum(1) - sX[idx].sum(1)) / sE[idx].sum(1)
        res = dict(n_seeds=len(seeds), mean_E_ms=float(sE.sum() / (2 * len(seeds))),
                   mean_X_ms=float(sX.sum() / (2 * len(seeds))), gap=dict(point=float(g), ci=ci(bg)),
                   seeds_with_stall=len(stall_seeds))
        clean = [r for r in rs if int(r["seed"]) not in stall_seeds and int(r["drops_full"]) == 0 and int(r["drops_solo"]) == 0]
        if clean:
            res["V7_max_abs_E_minus_X_clean_runs"] = float(max(abs(float(r["e2e_full"]) - float(r["e2e_solo"]) - float(r["X_full"])) for r in clean))
            res["V7_n_clean_rows"] = len(clean)
        stall = [r for r in rs if int(r["seed"]) in stall_seeds]
        if stall:
            res["mean_abs_gap_ms_in_stall_runs"] = float(np.mean([abs(float(r["e2e_full"]) - float(r["e2e_solo"]) - float(r["X_full"])) for r in stall]))
        out[cond] = res
    out["H10_confirmed"] = bool(out["P256"]["gap"]["ci"][1] <= 0.05 and out["F64"]["gap"]["ci"][0] >= 0.5)
    out["V7_passed"] = bool(out["P256"].get("V7_n_clean_rows", 0) > 0 and out["P256"]["V7_max_abs_E_minus_X_clean_runs"] <= 1e-9)
    return out


def h12():
    rng = np.random.default_rng(20261022)
    delay = defaultdict(dict)
    sigs = defaultdict(set)
    for r in csv.DictReader(open(RES / "raw_s3_h12_delay.csv")):
        delay[(r["arm"], int(r["seed"]))][(int(r["flow"]), int(r["mask"]))] = float(r["D"])
        sigs[(r["arm"], int(r["seed"]), int(r["flow"]))].add(r["sig"])
    blame = defaultdict(dict)
    for r in csv.DictReader(open(RES / "raw_s3_h12_blame.csv")):
        blame[(r["arm"], int(r["seed"]))][(int(r["blocker"]), int(r["victim"]))] = (float(r["blame_sum"]), int(r["n_victim"]))
    out = dict(V9_replay_violations=int(sum(len(v) != 1 for v in sigs.values())))
    eff_gap = 0.0
    full = frozenset(IDS)
    for arm in ("FullSASP", "FIFO"):
        seeds = sorted(s for (a, s) in delay if a == arm)
        cal, ev = seeds[:50], seeds[50:]
        BTR, BSH, BLOO, G = {}, {}, {}, {}
        for s in seeds:
            d = delay[(arm, s)]
            btr, bsh, bloo, g = np.zeros(4), np.zeros(4), np.zeros(4), np.zeros(4)
            for i in IDS:
                others = [o for o in IDS if o != i]
                subs = [frozenset(T) | {i} for r_ in range(4) for T in itertools.combinations(others, r_)]
                vals = {sub: d[(i, mask_of(sub))] for sub in subs}
                phi, E = s2.shapley_for_victim(vals, i, IDS)
                eff_gap = max(eff_gap, abs(sum(phi.values()) - E))
                for j in others:
                    bs, n = blame[(arm, s)][(j, i)]
                    btr[j - 1] += bs / n if n else 0.0
                    bsh[j - 1] += phi[j]
                    loo = vals[full] - vals[full - {j}]
                    bloo[j - 1] += loo
                    g[j - 1] += W[i] * loo
            BTR[s], BSH[s], BLOO[s], G[s] = btr, bsh, bloo, g
        mTR = np.mean([BTR[s] for s in cal], 0)
        mSH = np.mean([BSH[s] for s in cal], 0)
        mLOO = np.mean([BLOO[s] for s in cal], 0)
        pick = dict(TR=int(np.argmax(mTR)), SH=int(np.argmax(mSH)), LOO=int(np.argmax(mLOO)))
        Gev = np.array([G[s] for s in ev])            # eval seeds x candidate flows
        gain = {p: Gev[:, j] for p, j in pick.items()}
        gain["RAND"] = Gev.mean(1)
        oracle_j = int(np.argmax(Gev.mean(0)))
        n = len(ev)
        idx = rng.integers(0, n, (B, n))

        def diff(a, b):
            dd = gain[a] - gain[b]
            return dict(mean=float(dd.mean()), ci=ci(dd[idx].mean(1)))
        res = dict(picked_flow={p: j + 1 for p, j in pick.items()}, oracle_flow=oracle_j + 1,
                   calibration_B_TR=[float(x) for x in mTR], calibration_B_SH=[float(x) for x in mSH],
                   eval_mean_gain_by_flow=[float(x) for x in Gev.mean(0)],
                   gain={p: float(v.mean()) for p, v in gain.items()},
                   SH_minus_TR=diff("SH", "TR"), TR_minus_RAND=diff("TR", "RAND"), SH_minus_RAND=diff("SH", "RAND"),
                   capture_ratio={p: float(gain[p].mean() / Gev.mean(0)[oracle_j]) for p in gain})
        res["H12_confirmed"] = bool(res["SH_minus_TR"]["ci"][0] > 0)
        out[arm] = res
    out["V9_shapley_efficiency_gap"] = float(eff_gap)
    return out


def main():
    out = dict(H10=h10(), H12=h12())
    (RES / "analysis_study3_python.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
