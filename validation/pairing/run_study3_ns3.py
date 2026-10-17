"""run_study3_ns3.py - H11 new runs: 270 ns-3.47 FIFO runs with a negligible bulk flow (bulkMbps=1e-6, see
STUDY3_AMENDMENT_AND_EXPLORATORY_PLAN.md), same cells/seeds/binary as the Mission 1 main campaign.
Writes results/raw_s3_ns3_nobulk.csv (single use). A failed run is recorded, never replaced."""
import csv
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
NS3 = HERE.parent / "ns3"
sys.path.insert(0, str(NS3))
import nsrun  # noqa: E402
import run_campaign as rc  # noqa: E402

RES = HERE / "results"
SEEDS = list(range(1, 31))
NOBULK_MBPS = 1e-6


def main():
    for f in ("PREREGISTRATION_STUDY3.md", "STUDY3_AMENDMENT_AND_EXPLORATORY_PLAN.md"):
        want = (HERE / f.replace(".md", ".sha256")).read_text().split()[0]
        if hashlib.sha256((HERE / f).read_bytes()).hexdigest() != want:
            sys.exit(f"refusing to run: {f} changed after hashing")
    out = RES / "raw_s3_ns3_nobulk.csv"
    if out.exists():
        sys.exit("refusing to run: results exist (single-use)")
    # Mission 1 freeze check, except analyze_results.py (an analysis script edited after the freeze for
    # zero-variance t-tests, disclosed in Mission 1; it does not affect the simulator binary or the grid).
    frozen = json.loads((NS3 / "configs" / "FREEZE.json").read_text())["sha256"]
    bad = [f for f, h in frozen.items() if f != "analyze_results.py"
           and hashlib.sha256((NS3 / f).read_bytes()).hexdigest() != h]
    if bad:
        sys.exit(f"refusing to run: ns-3 files changed after freeze: {bad}")
    cfg = json.loads((NS3 / "configs" / "conditions.json").read_text())
    bid = rc.build_id()
    jobs = []
    for cond, p in cfg["main_conditions"].items():
        for load in cfg["load_fractions"]:
            for seed in SEEDS:
                jobs.append(dict(seed=seed, scheduler=0, cond=cond, load=load, weightRatio=cfg["main_weight_ratio"],
                                 bulkMbps=NOBULK_MBPS, mcs0=p["mcs0"], mcs1=p["mcs1"], width0=p["width0"],
                                 width1=p["width1"], rss0=p["rss0"], rss1=p["rss1"], simTime=rc.SIM_TIME,
                                 warmup=0.5, drain=0.3, buildId=bid, runId=len(jobs) + 1))
    assert len(jobs) == 270
    rows, errors, t0 = [], [], time.time()

    def one(j):
        return nsrun.run(dict(j), profile="optimized", timeout=1800)
    with ThreadPoolExecutor(14) as ex:
        futs = {ex.submit(one, j): j for j in jobs}
        for f in as_completed(futs):
            j = futs[f]
            try:
                rows.append(f.result())
            except Exception as e:
                errors.append(dict(cond=j["cond"], load=j["load"], seed=j["seed"], error=str(e)[-400:]))
    rows.sort(key=lambda r: (r["cond"], r["load"], r["seed"]))
    RES.mkdir(exist_ok=True)
    if rows:
        with open(out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(list(rows[0].keys()))
            for r in rows:
                w.writerow([r[k] for k in rows[0].keys()])
    (RES / "run_manifest_study3_ns3.json").write_text(json.dumps(dict(
        n_rows=len(rows), n_errors=len(errors), errors=errors, seconds=round(time.time() - t0, 1), build_id=bid), indent=1))
    print(f"done rows={len(rows)} errors={len(errors)} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
