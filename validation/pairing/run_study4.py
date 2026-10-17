"""run_study4.py - the single Study 4 pass: 13 held-out Python cells (seeds 25000-25099) and 6 held-out ns-3 cells
(seeds 31-60, with and without bulk). Refuses to run if the preregistration changed or results exist.
Writes results/raw_s4_py.csv, results/raw_s4_ns3.csv, results/run_manifest_study4.json."""
import csv
import hashlib
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import study as st

HERE = Path(__file__).resolve().parent
NS3 = HERE.parent / "ns3"
sys.path.insert(0, str(NS3))
import nsrun  # noqa: E402
import run_campaign as rc  # noqa: E402

RES = HERE / "results"
PY_SEEDS = list(range(25000, 25100))
NS_SEEDS = list(range(31, 61))
D = st.DURATION_MS
PY_CELLS = [("S4", lm, dm) for lm in (0.75, 0.35, 0.15) for dm in (0.5, 1.0, 3.0)] + \
           [("S8", lm, dm) for lm in (1.0, 0.5) for dm in (0.5, 3.0)]
NS_FRACS = (0.15, 0.45, 0.70)
NOBULK = 1e-6


def py_run(scale, lm, dm, keep, seed):
    flows, links, chans = st.build(scale, fer=0.01, delta_mu=dm)
    flows = [f for f in flows if f.flow_id in keep]
    for f in flows:
        f.rate_pkts_per_sec *= lm
    sim = st.StudySimulator(flows, links, chans, st.make_sched("FIFO"), seed=seed, design="keyed")
    rx = sim.run(duration_ms=D)
    out = {}
    for f in flows:
        mine = [p for p in rx.delivered_packets if p.flow_id == f.flow_id]
        n = len(mine)
        allp = [p for p in sim.all_packets if p.flow_id == f.flow_id]

        def avg(g):
            return (sum(g(p) for p in mine) / n) if n else float("nan")
        out[f.flow_id] = dict(n=n, e2e=avg(lambda p: p.end_to_end_delay), X=avg(lambda p: p.cross_blocking),
                              S=avg(lambda p: p.self_blocking), net=avg(lambda p: p.arr_rx_time - p.arr_time),
                              sig=st.hash_arrivals(allp, D))
    return out


def run_python(errors):
    rows = []
    for scale, lm, dm in PY_CELLS:
        ids = list(range(1, len(st.SCALES[scale]) + 1))
        for seed in PY_SEEDS:
            try:
                full = py_run(scale, lm, dm, set(ids), seed)
                for i in ids:
                    solo = py_run(scale, lm, dm, {i}, seed)[i]
                    f = full[i]
                    rows.append(dict(scale=scale, load=lm, dmu=dm, seed=seed, victim=i, n_full=f["n"], n_solo=solo["n"],
                                     e2e_full=f["e2e"], X_full=f["X"], S_full=f["S"], net_full=f["net"],
                                     e2e_solo=solo["e2e"], S_solo=solo["S"], net_solo=solo["net"],
                                     sig_equal=int(f["sig"] == solo["sig"])))
            except Exception:
                errors.append(dict(kind="py", scale=scale, load=lm, dmu=dm, seed=seed, error=traceback.format_exc()[-300:]))
        print("py cell done", scale, lm, dm, flush=True)
    return rows


def run_ns3(errors):
    cfg = json.loads((NS3 / "configs" / "conditions.json").read_text())
    bid = rc.build_id()
    jobs = []
    for cond in ("A1", "A2"):
        p = cfg["main_conditions"][cond]
        for frac in NS_FRACS:
            for seed in NS_SEEDS:
                for arm, mbps in (("with", frac * p["capacity_mbps"]), ("without", NOBULK)):
                    jobs.append((dict(seed=seed, scheduler=0, cond=cond, load=f"F{frac}", weightRatio=cfg["main_weight_ratio"],
                                      bulkMbps=mbps, mcs0=p["mcs0"], mcs1=p["mcs1"], width0=p["width0"], width1=p["width1"],
                                      rss0=p["rss0"], rss1=p["rss1"], simTime=rc.SIM_TIME, warmup=0.5, drain=0.3,
                                      buildId=bid, runId=len(jobs) + 1), arm, frac))
    rows = []
    with ThreadPoolExecutor(14) as ex:
        futs = {ex.submit(nsrun.run, dict(j), "optimized", 1800): (j, arm, frac) for j, arm, frac in jobs}
        for fu in as_completed(futs):
            j, arm, frac = futs[fu]
            try:
                r = fu.result()
                r["arm"], r["frac"] = arm, frac
                rows.append(r)
            except Exception as e:
                errors.append(dict(kind="ns3", cond=j["cond"], frac=frac, arm=arm, seed=j["seed"], error=str(e)[-300:]))
    rows.sort(key=lambda r: (r["cond"], r["frac"], r["arm"], r["seed"]))
    return rows


def dump(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        keys = list(rows[0].keys())
        w.writerow(keys)
        for r in rows:
            w.writerow([r[k] for k in keys])


def main():
    want = (HERE / "PREREGISTRATION_STUDY4.sha256").read_text().split()[0]
    if hashlib.sha256((HERE / "PREREGISTRATION_STUDY4.md").read_bytes()).hexdigest() != want:
        sys.exit("refusing to run: Study 4 preregistration changed after hashing")
    if (RES / "raw_s4_py.csv").exists():
        sys.exit("refusing to run: Study 4 results exist (single-use)")
    frozen = json.loads((NS3 / "configs" / "FREEZE.json").read_text())["sha256"]
    bad = [f for f, h in frozen.items() if f != "analyze_results.py" and hashlib.sha256((NS3 / f).read_bytes()).hexdigest() != h]
    if bad:
        sys.exit(f"refusing to run: ns-3 files changed after freeze: {bad}")
    t0, errors = time.time(), []
    py = run_python(errors)
    print(f"python done ({time.time() - t0:.0f}s, errors={len(errors)})", flush=True)
    ns = run_ns3(errors)
    print(f"ns3 done ({time.time() - t0:.0f}s, errors={len(errors)}, rows={len(ns)})", flush=True)
    RES.mkdir(exist_ok=True)
    dump(RES / "raw_s4_ns3.csv", ns)
    dump(RES / "raw_s4_py.csv", py)                  # last = completion marker
    (RES / "run_manifest_study4.json").write_text(json.dumps(dict(
        n_errors=len(errors), errors=errors, seconds=round(time.time() - t0, 1), n_py_rows=len(py), n_ns3_rows=len(ns),
        prereg_sha256=hashlib.sha256((HERE / "PREREGISTRATION_STUDY4.md").read_bytes()).hexdigest()), indent=1))
    print("done", len(errors), "errors")


if __name__ == "__main__":
    main()
