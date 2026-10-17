"""run_exploratory.py - EXPLORATORY analyses X1-X5 (see EXPLORATORY_PLAN.md). Fresh seeds only.
Writes results/exploratory_numbers.json (every number is labelled exploratory in the manuscript)."""
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import study as st

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
B = 10_000
rng = np.random.default_rng(20261017)
D = st.DURATION_MS


def ci(x):
    return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]


def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else float("nan")


def bcorr_ci(a, b):
    idx = rng.integers(0, len(a), size=(B, len(a)))
    A, Bm = a[idx], b[idx]
    A = A - A.mean(1, keepdims=True)
    Bm = Bm - Bm.mean(1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return ci((A * Bm).sum(1) / np.sqrt((A ** 2).sum(1) * (Bm ** 2).sum(1)))


def signflip_p(d):
    obs = abs(d.mean())
    s = rng.choice([-1.0, 1.0], size=(B, len(d)))
    return float(((np.abs((s * d).mean(1)) >= obs - 1e-15).sum() + 1) / (B + 1))


def x1():
    out = {}
    seeds = range(9000, 9100)
    for dm in (0.1, 0.5, 1.0, 2.0, 5.0):
        res = {}
        for design in ("shared", "keyed"):
            M = {a: [] for a in ("FIFO", "FullSASP")}
            sig = {a: [] for a in M}
            for s in seeds:
                for a in M:
                    sim, rx, w = st.simulate("S2", design, a, s, delta_mu=dm)
                    r = st.summarize(sim, rx, D, w)
                    M[a].append(r["M"])
                    sig[a].append(r["arr_sig"])
            f, g = np.array(M["FIFO"]), np.array(M["FullSASP"])
            mm = sum(x != y for x, y in zip(sig["FIFO"], sig["FullSASP"]))
            res[design] = dict(arrival_mismatch_seeds=int(mm), rho=corr(f, g), rho_ci=bcorr_ci(f, g),
                               mean_d=float((g - f).mean()))
        out[f"delta_mu_{dm}"] = res
        print("x1", dm, flush=True)
    return out


def x2():
    out = {}
    seeds = range(9000, 9100)
    for variant, single in (("shipped", False), ("single", True)):
        for arm in ("FIFO", "FullSASP"):
            rows = []
            for s in seeds:
                sim, rx, w = st.simulate("S2", "keyed", arm, s, burst_prob=0.02, burst_recovery=0.5, single_draw=single)
                rows.append(st.summarize(sim, rx, D, w))
            g = lambda k: np.array([r[k] for r in rows], dtype=float)
            out[f"{variant}_{arm}"] = dict(
                M_mean=float(g("M").mean()), M_ci=ci(g("M")[rng.integers(0, 100, (B, 100))].mean(1)),
                e2e_censored_mean=float(np.nanmean(g("e2e_censored"))), undelivered_frac=float(g("undelivered").sum() / g("generated").sum()),
                retry_drops_per_run=float(g("dropped_retry").mean()), late_discards_per_run=float(g("late_discards").mean()))
    return out


def dispatch_records(sim, T):
    return sorted((p.packet_id, p.link_id, p.seq_num, p.disp_time) for p in sim.all_packets
                  if p.disp_time is not None and p.disp_time <= T)


def x3():
    T, out = 150.0, {}
    for arm in ("FIFO", "FullSASP", "MeanOnly", "LeakyGlobal", "LeakyLocal"):
        viol = 0
        for s in range(9000, 9100):
            a = st.simulate("S2", "keyed", arm, s, duration=T, arrival_horizon=T, stop=T, trace_horizon=T)[0]
            b = st.simulate("S2", "keyed", arm, s, duration=D, arrival_horizon=D, stop=T, trace_horizon=D)[0]
            viol += dispatch_records(a, T) != dispatch_records(b, T)
        out[arm] = dict(violations=int(viol), n=100)
    return out


def x4():
    out = {}
    seeds = range(10000, 11000)
    for design in ("keyed", "shared"):
        f, g = [], []
        for s in seeds:
            for arm, store in (("FIFO", f), ("FullSASP", g)):
                sim, rx, w = st.simulate("S2", design, arm, s)
                store.append(st.summarize(sim, rx, D, w)["M"])
        f, g = np.array(f), np.array(g)
        d = g - f
        idx = rng.integers(0, len(d), (B, len(d)))
        out[design] = dict(n=len(d), mean_FIFO=float(f.mean()), mean_FullSASP=float(g.mean()), mean_d=float(d.mean()),
                           ci=ci(d[idx].mean(1)), signflip_p=signflip_p(d), rho=corr(f, g), frac_seeds_sasp_lower=float((d < 0).mean()))
        print("x4", design, flush=True)
    return out


def x5():
    path = HERE.parent / "ns3" / "results" / "main_campaign" / "main_campaign_raw.csv"
    rows = list(csv.DictReader(open(path)))
    by = defaultdict(dict)
    for r in rows:
        by[(r["cond"], r["load"], int(float(r["seed"])))][int(float(r["scheduler"]))] = r
    out = dict(cells={}, traffic_identical_fraction=None)
    ident = tot = 0
    for k, arms in by.items():
        tot += 1
        ident += len({(a["ls_sent"], a["bulk_sent"]) for a in arms.values()}) == 1
    out["traffic_identical_fraction"] = ident / tot
    out["n_triples"] = tot
    cells = sorted({(c, l) for c, l, _ in by})
    for c, l in cells:
        seeds = sorted(s for cc, ll, s in by if (cc, ll) == (c, l))
        f = np.array([float(by[(c, l, s)][0]["cross_wait_ms"]) for s in seeds])
        g = np.array([float(by[(c, l, s)][2]["cross_wait_ms"]) for s in seeds])
        out["cells"][f"{c}/{l}"] = dict(rho=corr(f, g), n=len(seeds), mean_FIFO=float(f.mean()), mean_FullSASP=float(g.mean()))
    return out


def main():
    res = dict(label="EXPLORATORY: motivated by confirmatory results; fresh seeds; no preregistered thresholds")
    for name, fn in (("X1_asymmetry", x1), ("X2_double_draw_effect", x2), ("X3_decision_level_causality", x3),
                     ("X4_sasp_effect_size", x4), ("X5_ns3_pairing_reanalysis", x5)):
        res[name] = fn()
        print("done", name, flush=True)
    (RES / "exploratory_numbers.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
