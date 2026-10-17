"""analyze_study2.py - Study 2 analysis exactly as in PREREGISTRATION_STUDY2.md.
Cluster = seed; percentile bootstrap, 10,000 resamples, numpy default_rng(20261018)."""
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
rng = np.random.default_rng(20261018)
NFLOWS = {"S2": 2, "S4": 4, "S8": 8, "LowLoad": 4}


def ci(x):
    x = x[~np.isnan(x)]
    return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]


def kendall_tau_b(a, b):
    n, conc, disc, ta, tb = len(a), 0, 0, 0, 0
    for i in range(n):
        for j in range(i + 1, n):
            da, db = a[i] - a[j], b[i] - b[j]
            if da == 0 and db == 0:
                continue
            if da == 0:
                ta += 1
            elif db == 0:
                tb += 1
            elif da * db > 0:
                conc += 1
            else:
                disc += 1
    den = ((conc + disc + ta) * (conc + disc + tb)) ** 0.5
    return (conc - disc) / den if den > 0 else float("nan")


def load():
    delay = defaultdict(dict)   # (scn,arm,seed) -> {(flow, mask): (D, sig, n)}
    for r in csv.DictReader(open(RES / "raw_s2_delay.csv")):
        delay[(r["scenario"], r["arm"], int(r["seed"]))][(int(r["flow"]), int(r["mask"]))] = (float(r["D"]), r["sig"], int(r["n_pkts"]))
    blame = defaultdict(dict)
    for r in csv.DictReader(open(RES / "raw_s2_blame.csv")):
        blame[(r["scenario"], r["arm"], int(r["seed"]))][(int(r["blocker"]), int(r["victim"]))] = r
    return delay, blame


def subsets_with(victim, ids):
    others = [f for f in ids if f != victim]
    for r in range(len(others) + 1):
        for T in itertools.combinations(others, r):
            yield frozenset(T) | {victim}


def mask_of(s):
    return sum(1 << (i - 1) for i in s)


def nanmean_safe(x):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    return float(x.mean()) if len(x) else float("nan")


def analyze_config(scn, arm, delay, blame):
    ids = list(range(1, NFLOWS[scn] + 1))
    seeds = sorted(k[2] for k in delay if k[0] == scn and k[1] == arm)
    S, N = len(seeds), len(ids)
    sumX, sumE, sumLOO = np.zeros(S), np.zeros(S), np.zeros(S)
    tau_tr_sh, tau_loo_sh, agree = np.full(S, np.nan), np.full(S, np.nan), np.full(S, np.nan)
    BTR_all, BSH_all = np.zeros((S, N)), np.zeros((S, N))
    v1_max, v2_bad, v4_max, dropped, negE, total_pairs = 0.0, 0, 0.0, 0, 0, 0
    for si, seed in enumerate(seeds):
        d, bl = delay[(scn, arm, seed)], blame[(scn, arm, seed)]
        BTR, BSH, BLOO = np.zeros(N), np.zeros(N), np.zeros(N)
        for i in ids:
            total_pairs += 1
            subs = list(subsets_with(i, ids))
            vals = {s: d[(i, mask_of(s))][0] for s in subs}
            v2_bad += len({d[(i, mask_of(s))][1] for s in subs}) != 1
            if any(np.isnan(v) for v in vals.values()):
                dropped += 1
                continue
            first = bl[(next(j for j in ids if j != i), i)]
            if int(first["n_delivered_victim"]) == 0:
                dropped += 1
                continue
            phi, E = s2.shapley_for_victim(vals, i, ids)
            v1_max = max(v1_max, abs(sum(phi.values()) - E))
            full = frozenset(ids)
            loo = {j: vals[full] - vals[full - {j}] for j in ids if j != i}
            nx = float(first["meanX_victim"])
            tsum = 0.0
            for j in ids:
                if j == i:
                    continue
                r = bl[(j, i)]
                t = float(r["blame_sum"]) / int(r["n_delivered_victim"])
                tsum += t
                BTR[j - 1] += t
                BSH[j - 1] += phi[j]
                BLOO[j - 1] += loo[j]
            v4_max = max(v4_max, abs(tsum + float(first["forced_cross_victim"]) - nx))
            sumX[si] += nx
            sumE[si] += E
            sumLOO[si] += sum(loo.values())
            negE += E < 0
        BTR_all[si], BSH_all[si] = BTR, BSH
        tau_tr_sh[si] = kendall_tau_b(BTR, BSH)
        tau_loo_sh[si] = kendall_tau_b(BLOO, BSH)
        agree[si] = float(int(np.argmax(BTR)) == int(np.argmax(BSH)))
    idx = rng.integers(0, S, size=(B, S))
    valid = total_pairs - dropped
    tau_boot = np.array([nanmean_safe(tau_tr_sh[ix]) for ix in idx])
    return dict(
        n_seeds=S, n_victim_pairs=total_pairs, dropped_pairs=int(dropped),
        explained_fraction=dict(point=float(sumX.sum() / sumE.sum()), ci=ci(sumX[idx].sum(1) / sumE[idx].sum(1))),
        kendall_trace_vs_shapley=dict(mean=nanmean_safe(tau_tr_sh), ci=ci(tau_boot),
                                      n_valid_seeds=int((~np.isnan(tau_tr_sh)).sum())),
        top_offender_agreement=nanmean_safe(agree),
        nonadditivity_R=dict(point=float(sumLOO.sum() / sumE.sum()), ci=ci(sumLOO[idx].sum(1) / sumE[idx].sum(1))),
        exploratory_kendall_loo_vs_shapley=nanmean_safe(tau_loo_sh),
        frac_negative_externality=float(negE / max(1, valid)),
        mean_E_ms=float(sumE.sum() / max(1, valid)), mean_X_ms=float(sumX.sum() / max(1, valid)),
        mean_blame_TR_by_flow=[float(x) for x in BTR_all.mean(0)],
        mean_blame_SH_by_flow=[float(x) for x in BSH_all.mean(0)],
        validity=dict(V1_max_efficiency_gap=float(v1_max), V2_replay_signature_violations=int(v2_bad),
                      V4_max_completeness_gap=float(v4_max)),
    )


def main():
    delay, blame = load()
    out = {}
    for scn, arm in sorted({(k[0], k[1]) for k in delay}):
        out[f"{scn}/{arm}"] = analyze_config(scn, arm, delay, blame)
        print("analysed", scn, arm, flush=True)
    for key in ("S4/FIFO", "S8/FIFO"):
        a = out[key]
        r, t, R = a["explained_fraction"]["ci"], a["kendall_trace_vs_shapley"]["ci"], a["nonadditivity_R"]["ci"]
        a["H7_verdict"] = "confirmed (X does not capture externality)" if r[1] < 0.5 else (
            "adequate proxy" if r[0] > 0.8 else "inconclusive")
        a["H8_verdict"] = "confirmed (misranking)" if t[1] < 0.5 else ("adequate proxy" if t[0] > 0.8 else "inconclusive")
        a["H9_verdict"] = "confirmed (non-additive)" if (R[1] < 0.8 or R[0] > 1.2) else "not confirmed"
    ll = out["LowLoad/FIFO"]["explained_fraction"]["point"]
    out["V3_lowload_control"] = dict(explained_fraction=ll, passed=bool(0.75 <= ll <= 1.25))
    (RES / "analysis_study2.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
