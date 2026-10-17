"""posthoc_h19_refine.py - POST HOC (not preregistered): re-evaluate the closed forms of H19 parameter sets P6 and P7, whose preregistered
quadrature-convergence check V16 failed, on a much finer grid, and recompute the z-scores against the stored Monte Carlo means.
Reads results/raw_s5_h19.csv; writes results/posthoc_h19_refine.json."""
import csv
import itertools
import json
from pathlib import Path

import numpy as np

import airport as ap
from run_study5 import H19, shapley_poisson_chunked

RES = Path(__file__).resolve().parent / "results"
rows = list(csv.DictReader(open(RES / "raw_s5_h19.csv")))
out = {}
for name in ("P6", "P7"):
    _, victim, others, rates = next(h for h in H19 if h[0] == name)
    m = len(others)
    res = {}
    for n, nt in ((20001, 2001), (80001, 2001), (320001, 1001)):
        phi = shapley_poisson_chunked(victim, others, rates, n, nt)
        v = {"".join(map(str, T)): ap.poisson_game_value(victim, others, rates, list(T), n=n)
             for r in range(1, m + 1) for T in itertools.combinations(range(m), r)}
        res[n] = (phi, v)
    ref_phi, ref_v = res[320001]
    zs, drift = [], []
    for r in rows:
        if r["param"] != name or r["kind"] not in ("v", "phi"):
            continue
        cf = ref_v[r["key"]] if r["kind"] == "v" else ref_phi[int(r["key"])]
        zs.append(abs((float(r["mc"]) - cf) / float(r["se"])))
        c80 = res[80001][0][int(r["key"])] if r["kind"] == "phi" else res[80001][1][r["key"]]
        drift.append(abs(c80 - cf) / abs(cf))
    out[name] = dict(max_abs_z_refined=float(max(zs)), max_rel_change_80k_vs_320k=float(max(drift)))
(RES / "posthoc_h19_refine.json").write_text(json.dumps(dict(label="POST HOC, not preregistered", **out), indent=1))
print(out)
