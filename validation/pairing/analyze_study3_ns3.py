"""analyze_study3_ns3.py - H11 exactly as in PREREGISTRATION_STUDY3.md + Amendment 1, plus descriptive X8 shares.
With-bulk arm: pre-existing main campaign rows (scheduler=0). Without-bulk: results/raw_s3_ns3_nobulk.csv.
Bootstrap: 10,000 resamples, default_rng(20261021); seeds resampled independently in each arm (noise not coupled)."""
import csv
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
NS3 = HERE.parent / "ns3" / "results" / "main_campaign" / "main_campaign_raw.csv"
B = 10_000
rng = np.random.default_rng(20261021)


def ci(x):
    return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]


def load_rows(path, keep=lambda r: True):
    return [r for r in csv.DictReader(open(path)) if keep(r)]


def col(rows, key):
    return np.array([float(r[key]) for r in sorted(rows, key=lambda r: int(float(r["seed"])))])


def main():
    withb = load_rows(NS3, lambda r: int(float(r["scheduler"])) == 0)
    nob = load_rows(RES / "raw_s3_ns3_nobulk.csv")
    cells = {}
    v8_ok = all(float(r["bulk_sent"]) == 0 and float(r["cross_wait_ms"]) == 0 for r in nob)
    for cond in ("A0", "A1", "A2"):
        for load in ("L0", "L1", "L2"):
            w = [r for r in withb if r["cond"] == cond and r["load"] == load]
            n = [r for r in nob if r["cond"] == cond and r["load"] == load]
            assert len(w) == 30 and len(n) == 30
            dw, dn = col(w, "ls_delay_mean_ms"), col(n, "ls_delay_mean_ms")
            xw = col(w, "cross_wait_ms")
            iw = rng.integers(0, 30, (B, 30))
            inn = rng.integers(0, 30, (B, 30))
            Eb = dw[iw].mean(1) - dn[inn].mean(1)
            Xb = xw[iw].mean(1)
            E, X = dw.mean() - dn.mean(), xw.mean()
            parts = {k: float(col(w, k).mean() - col(n, k).mean()) for k in
                     ("ls_queue_wait_ms", "within_wait_ms", "cross_wait_ms", "forced_wait_ms")}
            parts["remainder_air_mac"] = float(E - sum(parts.values()))
            defined = bool(ci(Eb)[0] > 0)
            ratio_ci = ci(Xb / Eb) if defined else [float("nan"), float("nan")]
            cells[f"{cond}/{load}"] = dict(
                E_ms=dict(point=float(E), ci=ci(Eb)), X_ms=float(X), defined=defined,
                r=dict(point=float(X / E) if E != 0 else float("nan"), ci=ratio_ci),
                little_explained=bool(defined and ratio_ci[1] < 0.5),
                mostly_explained=bool(defined and ratio_ci[0] >= 0.5),
                component_shares_of_E={k: (v / E if E != 0 else float("nan")) for k, v in parts.items()},
                mean_ls_sent_with=float(col(w, "ls_sent").mean()), mean_ls_sent_without=float(col(n, "ls_sent").mean()),
                ls_pdr_with=float(col(w, "ls_pdr").mean()))
    nd = [c for c in cells.values() if c["defined"]]
    little = sum(c["little_explained"] for c in nd)
    mostly = sum(c["mostly_explained"] for c in nd)
    out = dict(cells=cells, n_defined=len(nd), n_little_explained=int(little), n_mostly_explained=int(mostly),
               V8_all_nobulk_runs_clean=bool(v8_ok), n_nobulk_runs=len(nob))
    if len(nd) < 5:
        verdict = "inconclusive (fewer than 5 defined cells)"
    elif mostly >= len(nd) / 3:
        verdict = "NOT replicated (heterogeneous: >= 1/3 of defined cells have r >= 0.5)"
    elif little >= 2 * len(nd) / 3:
        verdict = "confirmed (qualitative replication)"
    else:
        verdict = "not confirmed"
    out["H11_verdict"] = verdict
    (RES / "analysis_study3_ns3.json").write_text(json.dumps(out, indent=1, default=float))
    for k, c in cells.items():
        print(k, "E=%.4f [%.4f,%.4f]" % (c["E_ms"]["point"], *c["E_ms"]["ci"]), "X=%.4f" % c["X_ms"],
              "defined" if c["defined"] else "undefined", "r=%.3f [%.3f,%.3f]" % (c["r"]["point"], *c["r"]["ci"]),
              {kk: round(v, 2) for kk, v in c["component_shares_of_E"].items()})
    print({k: out[k] for k in ("n_defined", "n_little_explained", "n_mostly_explained", "V8_all_nobulk_runs_clean", "H11_verdict")})


if __name__ == "__main__":
    main()
