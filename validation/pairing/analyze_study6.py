"""analyze_study6.py - H20-H24 and descriptives (T10 bound, certificate, X16, D2) exactly as in PREREGISTRATION_STUDY6.md.
Bootstrap: 10,000 resamples over runs, default_rng(20261041). Writes results/analysis_study6.json."""
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
B = 10_000
rng = np.random.default_rng(20261041)


def read(name):
    return list(csv.DictReader(open(RES / name)))


def fl(v):
    return float("nan") if v in ("", "nan") else float(v)


def ci(x):
    return [float(np.nanpercentile(x, 2.5)), float(np.nanpercentile(x, 97.5))]


def g4():
    rows = read("raw_s6_g4.csv")
    cells = defaultdict(list)
    for r in rows:
        cells[r["cell"]].append(r)
    out = {}
    for c, rr in cells.items():
        n = len(rr)
        nb = sum(int(r["n_blocked"]) for r in rr)
        out[c] = dict(
            n_traces=n, forced_events_mean=float(np.mean([int(r["forced_events"]) for r in rr])),
            frac_traces_with_event=float(np.mean([int(r["forced_events"]) > 0 for r in rr])),
            delivered_share=float(np.mean([int(r["n_delivered"]) / 300 for r in rr])),
            max_O1=max(fl(r["O1"]) for r in rr), set_mismatch=sum(int(r["set_mismatch"]) for r in rr),
            max_O2=max(fl(r["O2"]) for r in rr), max_O3=max(fl(r["O3"]) for r in rr), max_O4=max(fl(r["O4"]) for r in rr),
            max_O6_err=max(fl(r["O6_err"]) for r in rr), O6_viol=sum(int(r["O6_viol"]) for r in rr),
            O7_viol=sum(int(r["O7_viol"]) for r in rr),
            blocked_from_skipped=(sum(int(r["n_blocked_skipped"]) for r in rr) / nb) if nb else float("nan"),
            certified_share=sum(int(r["n_cert"]) for r in rr) / max(1, sum(int(r["n_cert"]) + int(r["n_rej"]) for r in rr)),
            false_rejections=sum(int(r["n_false_rej"]) for r in rr), skipped_but_certified=sum(int(r["n_skip_but_cert"]) for r in rr),
            T10_l_viol=sum(int(r["T10_l_viol"]) for r in rr), T10_phi_viol=sum(int(r["T10_phi_viol"]) for r in rr),
            T10_max_ratio=max(fl(r["T10_max_ratio"]) for r in rr))
    ok20 = (max(v["max_O1"] for v in out.values()) <= 1e-9 and sum(v["set_mismatch"] for v in out.values()) == 0
            and np.mean([int(r["forced_events"]) > 0 for r in rows]) >= 0.90)
    ok21a = (max(max(v["max_O2"], v["max_O3"], v["max_O4"], v["max_O6_err"]) for v in out.values()) <= 1e-9
             and sum(v["O6_viol"] + v["O7_viol"] for v in out.values()) == 0)
    ok21b = sum(v["T10_l_viol"] + v["T10_phi_viol"] for v in out.values()) == 0
    ok21c = sum(v["false_rejections"] for v in out.values()) == 0
    tot = dict(n_traces=len(rows), frac_traces_with_event=float(np.mean([int(r["forced_events"]) > 0 for r in rows])),
               n_packets=sum(int(r["n_pkts"]) for r in rows),
               max_error_O1_O6=max(max(v["max_O1"], v["max_O2"], v["max_O3"], v["max_O4"], v["max_O6_err"]) for v in out.values()),
               total_events=sum(int(r["forced_events"]) for r in rows),
               certified_share_overall=sum(int(r["n_cert"]) for r in rows) / sum(int(r["n_cert"]) + int(r["n_rej"]) for r in rows),
               skipped_but_certified=sum(int(r["n_skip_but_cert"]) for r in rows),
               T10_max_ratio=max(v["T10_max_ratio"] for v in out.values()))
    return dict(cells=out, totals=tot, H20="confirmed" if ok20 else "NOT confirmed", H21a="confirmed" if ok21a else "NOT confirmed",
                H21b="confirmed" if ok21b else "NOT confirmed", H21c="confirmed" if ok21c else "NOT confirmed")


def ns3():
    rows = read("raw_s6_ns3.csv")
    inc = [r for r in rows if fl(r["forced_adv_events"]) == 0]
    excl = len(rows) - len(inc)
    d = dict(n_runs=len(rows), n_excluded_forced=excl, n_packets_checked=sum(int(r["n_checked"]) for r in inc),
             n_blocked_packets=sum(int(r["n_blocked_ns3"]) for r in inc),
             N1_max_err=max(fl(r["N1_max_err"]) for r in inc), N1_viol=sum(int(r["N1_viol"]) for r in inc),
             V18_ext_dups=sum(int(r["ext_dups"]) for r in inc),
             py_max_err=max(fl(r["py_max_err"]) for r in inc), py_mismatch=sum(int(r["py_mismatch"]) for r in inc),
             O2=max(fl(r["O2"]) for r in inc), O3=max(fl(r["O3"]) for r in inc), O4=max(fl(r["O4"]) for r in inc),
             O6_viol=sum(int(r["O6_viol"]) for r in inc), O6_err=max(fl(r["O6_err"]) for r in inc),
             O7_viol=sum(int(r["O7_viol"]) for r in inc),
             H24_max_diff_cross=max(abs(fl(r["h24_cross"]) - fl(r["csv_cross"])) for r in inc),
             H24_max_diff_within=max(abs(fl(r["h24_within"]) - fl(r["csv_within"])) for r in inc),
             H24_count_mismatch=sum(int(r["h24_n1"]) != int(float(r["h24_ls_rcvd"])) for r in inc),
             X16_equal_runs=sum(int(r["occ_trace_max"]) == int(float(r["occ_csv_max"])) for r in inc),
             X16_max_abs_diff=max(abs(int(r["occ_trace_max"]) - float(r["occ_csv_max"])) for r in inc))
    by = {}
    for c in ("A1", "A2"):
        for s in ("1.0", "2.5"):
            rr = [r for r in inc if r["cond"] == c and abs(float(r["scale"]) - float(s)) < 1e-9]
            if rr:
                by[f"{c}/x{s}"] = dict(n_runs=len(rr), frac_blocked=float(np.mean([fl(r["frac_blocked"]) for r in rr])),
                                       multi_late_share=float(1 - np.mean([fl(r["frac_single_late"]) for r in rr])))
    d["by_cell"] = by
    d["H22"] = "confirmed" if d["N1_viol"] == 0 and d["N1_max_err"] <= 1e-6 else "NOT confirmed"
    d["H23"] = "confirmed" if (d["py_max_err"] <= 1e-6 and d["py_mismatch"] == 0 and max(d["O2"], d["O3"], d["O4"], d["O6_err"]) <= 1e-9
                               and d["O6_viol"] == 0 and d["O7_viol"] == 0) else "NOT confirmed"
    d["H24"] = "confirmed" if (d["H24_max_diff_cross"] <= 1e-6 and d["H24_max_diff_within"] <= 1e-6
                               and d["H24_count_mismatch"] == 0) else "NOT confirmed"
    return d


def d2():
    rows = read("raw_s6_d2.csv")
    out, allr = {}, []
    for c in ("A1", "A2"):
        for l in ("L0", "L1", "L2"):
            rr = [r for r in rows if r["cond"] == c and r["load"] == l]
            n = np.array([float(r["n"]) for r in rr])
            sx = np.array([float(r["sum_X"]) for r in rr])
            ss = np.array([float(r["sum_S"]) for r in rr])
            sc = np.array([float(r["sum_ns3cross"]) for r in rr])
            bi = rng.integers(0, len(rr), (B, len(rr)))
            ratio_b = sx[bi].sum(1) / sc[bi].sum(1) if sc.sum() > 0 else np.full(B, np.nan)
            out[f"{c}/{l}"] = dict(
                n_runs=len(rr), n_packets=int(n.sum()), mean_X_ms=float(sx.sum() / n.sum()), mean_S_ms=float(ss.sum() / n.sum()),
                mean_ns3cross_ms=float(sc.sum() / n.sum()),
                ratio_X_over_ns3cross=dict(point=float(sx.sum() / sc.sum()) if sc.sum() > 0 else None, ci=ci(ratio_b)),
                forced_runs=sum(float(r["forced_adv_events"]) > 0 for r in rr))
            allr += rr
    sx = sum(float(r["sum_X"]) for r in allr)
    sc = sum(float(r["sum_ns3cross"]) for r in allr)
    ss = sum(float(r["sum_S"]) for r in allr)
    return dict(cells=out, overall_ratio_X_over_ns3cross=sx / sc if sc else None, overall_S_over_X=ss / sx if sx else None,
                min_cell_ratio=min((v["ratio_X_over_ns3cross"]["point"] for v in out.values()
                                    if v["ratio_X_over_ns3cross"]["point"] is not None), default=None))


def main():
    out = dict(G4=g4(), NS3=ns3(), D2=d2())
    (RES / "analysis_study6.json").write_text(json.dumps(out, indent=1, default=float))
    G = out["G4"]
    print("H20", G["H20"], "H21a", G["H21a"], "H21b", G["H21b"], "H21c", G["H21c"], json.dumps(G["totals"], default=float))
    keys = ("frac_traces_with_event", "forced_events_mean", "delivered_share", "max_O1", "set_mismatch", "certified_share",
            "false_rejections", "T10_phi_viol", "T10_max_ratio", "blocked_from_skipped")
    for c, v in G["cells"].items():
        print("  ", c, {k: (round(v[k], 4) if isinstance(v[k], float) else v[k]) for k in keys})
    N = out["NS3"]
    print("NS3", {k: v for k, v in N.items() if k != "by_cell"})
    print("NS3 by cell", json.dumps(N["by_cell"]))
    print("D2", json.dumps(out["D2"], default=float))


if __name__ == "__main__":
    main()
