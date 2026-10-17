#!/usr/bin/env python3
"""run_campaign.py - executes the preregistered ns-3.47 campaigns.

  main      : 3 asymmetry (A0,A1,A2) x 3 load (L0,L1,L2) x 30 seeds x 3 arms = 810 runs
  ablation  : 3 variance regimes (V1,V2,V4) x 3 weight ratios (1,10,50) x 30 seeds x 3 arms = 810 runs

Guarantees
  * the grid comes from configs/conditions.json (frozen by calibrate.py) - nothing is tuned here
  * seeds 1..30; the three arms of a (cell, seed) use the same RngSeed and the same stream ids
  * every row records the ns-3 source/patch/binary hashes (build_id); the freeze file is verified
    before any run starts (refuses to run if sources changed after the preregistration freeze)
  * a failed or audit-violating run is NOT dropped: its output is kept under <campaign>/invalid/
    and the campaign refuses to merge until the set is complete (or the failure is documented)
  * resumable: existing valid per-run files are reused
"""
import argparse
import csv
import gzip
import hashlib
import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import nsrun

HERE = Path(__file__).resolve().parent
SEEDS = list(range(1, 31))
ARMS = {0: "FIFO", 1: "MeanOnly", 2: "FullSASP"}
SIM_TIME = 10.0


def sha(path, n=16):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:n]


def build_id():
    exe, _ = nsrun.binary("optimized")
    patches = "".join(sha(p, 8) for p in sorted((HERE / "patches").glob("*.patch")))
    return f"ns3.47+p{patches}+exe{sha(exe, 8)}"


def verify_freeze():
    fz = HERE / "configs" / "FREEZE.json"
    if not fz.exists():
        sys.exit("refusing to run: configs/FREEZE.json missing (run freeze.py after writing the preregistration)")
    frozen = json.loads(fz.read_text())["sha256"]
    bad = [f for f, h in frozen.items() if hashlib.sha256((HERE / f).read_bytes()).hexdigest() != h]
    if bad:
        sys.exit(f"refusing to run: files changed after freeze: {bad}")


def grid(mode, cfg):
    jobs = []
    if mode == "main":
        for cond, p in cfg["main_conditions"].items():
            for load in cfg["load_fractions"]:
                for seed in SEEDS:
                    for arm in ARMS:
                        jobs.append(dict(campaign="main", cond=cond, load=load, seed=seed, scheduler=arm,
                                         weightRatio=cfg["main_weight_ratio"], bulkMbps=p["bulk_mbps"][load],
                                         mcs0=p["mcs0"], mcs1=p["mcs1"], width0=p["width0"], width1=p["width1"],
                                         rss0=p["rss0"], rss1=p["rss1"]))
    else:
        L = cfg["ablation_load"]
        for cond, p in cfg["ablation_regimes"].items():
            for w in cfg["ablation_weight_ratios"]:
                for seed in SEEDS:
                    for arm in ARMS:
                        jobs.append(dict(campaign="ablation", cond=f"{cond}_w{w}", load=L, seed=seed, scheduler=arm,
                                         weightRatio=w, bulkMbps=p["bulk_mbps"][L], mcs0=p["mcs0"], mcs1=p["mcs1"],
                                         width0=p["width0"], width1=p["width1"], rss0=p["rss0"], rss1=p["rss1"]))
    for i, j in enumerate(jobs, 1):
        j["runId"] = i
    return jobs


def run_one(job, outdir, bid, profile):
    rid = job["runId"]
    row_path = outdir / "runs" / f"run_{rid:05d}.csv"
    if row_path.exists():
        return job, "cached", None
    dlog = outdir / "decisions" / f"run_{rid:05d}.csv"
    args = {k: v for k, v in job.items() if k != "campaign"}
    args.update(simTime=SIM_TIME, warmup=0.5, drain=0.3, buildId=bid, decisionLog=dlog)
    try:
        row = nsrun.run(args, profile=profile, timeout=1800)
    except Exception as e:  # keep evidence of the failure, never drop silently
        (outdir / "invalid" / f"run_{rid:05d}.json").write_text(json.dumps(dict(job=job, error=str(e)[-4000:])))
        return job, "invalid", str(e)[-300:]
    with open(dlog, "rb") as f_in, gzip.open(str(dlog) + ".gz", "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    dlog.unlink()
    with open(row_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(list(row.keys()))
        w.writerow([row[k] for k in row])
    return job, "ok", None


def merge(outdir, jobs, name):
    rows, keys = [], set()
    header = None
    for j in jobs:
        p = outdir / "runs" / f"run_{j['runId']:05d}.csv"
        if not p.exists():
            sys.exit(f"cannot merge: missing run {j['runId']} ({j['cond']},{j['load']},seed {j['seed']},arm {j['scheduler']})")
        r = list(csv.reader(open(p)))
        if len(r) != 2:
            sys.exit(f"malformed per-run file {p}")
        header = header or r[0]
        if r[0] != header:
            sys.exit(f"schema mismatch in {p}")
        key = (j["cond"], j["load"], j["seed"], j["scheduler"])
        if key in keys:
            sys.exit(f"duplicate experiment identity {key}")
        keys.add(key)
        rows.append(r[1])
    out = outdir / f"{name}_raw.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"merged {len(rows)} runs -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["main", "ablation"])
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--profile", default="optimized")
    ap.add_argument("--limit", type=int, default=0, help="debug: only first N jobs (never merges)")
    a = ap.parse_args()
    verify_freeze()
    cfg = json.loads((HERE / "configs" / "conditions.json").read_text())
    jobs = grid(a.mode, cfg)
    assert len(jobs) == 810, f"grid has {len(jobs)} runs, expected 810"
    outdir = HERE / "results" / ("main_campaign" if a.mode == "main" else "threshold_ablation")
    for sub in ("runs", "decisions", "invalid"):
        (outdir / sub).mkdir(parents=True, exist_ok=True)
    bid = build_id()
    print(f"[{a.mode}] {len(jobs)} runs, build_id={bid}")
    todo = jobs[: a.limit] if a.limit else jobs
    t0, done, bad = time.time(), 0, 0
    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(run_one, j, outdir, bid, a.profile) for j in todo]
        for f in as_completed(futs):
            job, status, err = f.result()
            done += 1
            bad += status == "invalid"
            if status == "invalid":
                print(f"INVALID run {job['runId']}: {err}")
            if done % 50 == 0:
                print(f"  {done}/{len(todo)} ({time.time() - t0:.0f}s, {bad} invalid)")
    if a.limit:
        return 0
    if bad:
        sys.exit(f"{bad} invalid runs preserved under {outdir / 'invalid'}; not merging")
    merge(outdir, jobs, "main_campaign" if a.mode == "main" else "threshold_ablation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
