"""run_study2b.py - EXPLORATORY Study 2b (see STUDY2B_PLAN.md). Seeds 21000-21099.
Writes results/raw_s2b.csv and results/exploratory_study2b.json."""
import csv
import json
import sys
from pathlib import Path

import numpy as np

from study import StudySimulator, build, make_sched, DURATION_MS

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
SEEDS = list(range(21000, 21100))
LOADS = (1.0, 0.5, 0.25, 0.1)
ASYM = (0.1, 2.0, 5.0)
IDS = (1, 2, 3, 4)
B = 10_000


def run_decomp(rate_scale, dm, keep, seed):
    flows, links, chans = build("S4", fer=0.01, delta_mu=dm)
    flows = [f for f in flows if f.flow_id in keep]
    for f in flows:
        f.rate_pkts_per_sec *= rate_scale
    sim = StudySimulator(flows, links, chans, make_sched("FIFO"), seed=seed, design="keyed")
    rx = sim.run(duration_ms=DURATION_MS)
    out = {}
    for f in flows:
        mine = [p for p in rx.delivered_packets if p.flow_id == f.flow_id]
        n = len(mine)
        if n:
            out[f.flow_id] = dict(n=n, net=sum(p.arr_rx_time - p.arr_time for p in mine) / n,
                                  S=sum(p.self_blocking for p in mine) / n, X=sum(p.cross_blocking for p in mine) / n,
                                  e2e=sum(p.end_to_end_delay for p in mine) / n)
        else:
            out[f.flow_id] = dict(n=0, net=float("nan"), S=float("nan"), X=float("nan"), e2e=float("nan"))
    return out


def ci(x):
    return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]


def main():
    if (RES / "raw_s2b.csv").exists():
        sys.exit("Study 2b results exist (single-use)")
    rows = []
    for ls in LOADS:
        for dm in ASYM:
            for seed in SEEDS:
                full = run_decomp(ls, dm, set(IDS), seed)
                for i in IDS:
                    solo = run_decomp(ls, dm, {i}, seed)[i]
                    f = full[i]
                    rows.append(dict(load=ls, asym=dm, seed=seed, flow=i, n_full=f["n"], n_solo=solo["n"],
                                     net_full=f["net"], S_full=f["S"], X_full=f["X"], e2e_full=f["e2e"],
                                     net_solo=solo["net"], S_solo=solo["S"], X_solo=solo["X"], e2e_solo=solo["e2e"]))
        print("done load", ls, flush=True)
    with open(RES / "raw_s2b.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    rng = np.random.default_rng(20261019)
    out, v5, v6 = {}, 0.0, 0.0
    for ls in LOADS:
        for dm in ASYM:
            cell = [r for r in rows if r["load"] == ls and r["asym"] == dm]
            valid = [r for r in cell if r["n_full"] > 0 and r["n_solo"] > 0]
            seeds = sorted({r["seed"] for r in valid})
            sidx = {s: k for k, s in enumerate(seeds)}
            sums = np.zeros((len(seeds), 5))   # E, dNet, dS, dX, count
            neg = 0
            for r in valid:
                E = r["e2e_full"] - r["e2e_solo"]
                dN, dS, dX = r["net_full"] - r["net_solo"], r["S_full"] - r["S_solo"], r["X_full"] - r["X_solo"]
                v5 = max(v5, abs(E - (dN + dS + dX)))
                v6 = max(v6, abs(r["X_solo"]))
                sums[sidx[r["seed"]]] += [E, dN, dS, dX, 1]
                neg += E < 0
            idx = rng.integers(0, len(seeds), (B, len(seeds)))
            tot = sums.sum(0)
            res = dict(n_pairs=int(tot[4]), dropped=len(cell) - len(valid), mean_E_ms=float(tot[0] / tot[4]),
                       frac_negative_E=float(neg / max(1, len(valid))))
            for name, col in (("net", 1), ("self", 2), ("cross", 3)):
                res[f"share_{name}"] = dict(point=float(tot[col] / tot[0]),
                                            ci=ci(sums[idx][:, :, col].sum(1) / sums[idx][:, :, 0].sum(1)))
            out[f"load{ls}_asym{dm}"] = res
    out["checks"] = dict(V5_max_identity_gap=float(v5), V6_max_solo_cross_blocking=float(v6),
                         V5_passed=bool(v5 <= 1e-9), V6_passed=bool(v6 == 0.0))
    (RES / "exploratory_study2b.json").write_text(json.dumps(out, indent=1, default=float))
    for k, v in out.items():
        if k == "checks":
            print(k, v)
        else:
            print(k, "E=%.3f ms" % v["mean_E_ms"], "net=%.3f self=%.3f cross=%.4f" % (
                v["share_net"]["point"], v["share_self"]["point"], v["share_cross"]["point"]))


if __name__ == "__main__":
    main()
