"""run_study2.py - the single Study 2 pass (seeds 20000-20099). Refuses to run if the Study 2 preregistration
changed or if results exist. Failed runs are recorded, never replaced."""
import csv
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

import study2 as s2

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
SEEDS = list(range(20000, 20100))
CONFIGS = [("S4", "FIFO"), ("S8", "FIFO"), ("S2", "FIFO"), ("LowLoad", "FIFO"), ("S4", "FullSASP"), ("S4", "MeanOnly")]
NFLOWS = {"S2": 2, "S4": 4, "S8": 8, "LowLoad": 4}


def main():
    want = (HERE / "PREREGISTRATION_STUDY2.sha256").read_text().split()[0]
    if hashlib.sha256((HERE / "PREREGISTRATION_STUDY2.md").read_bytes()).hexdigest() != want:
        sys.exit("refusing to run: Study 2 preregistration changed after hashing")
    if (RES / "raw_s2_delay.csv").exists():
        sys.exit("refusing to run: Study 2 results exist (single-use)")
    t0, errors = time.time(), []
    delay_rows, blame_rows = [], []
    for scenario, arm in CONFIGS:
        ids = list(range(1, NFLOWS[scenario] + 1))
        full = frozenset(ids)
        for seed in SEEDS:
            for mask, keep in s2.masks(ids):
                try:
                    sim, rx, out = s2.run_coalition(scenario, keep, arm, seed, blame=(keep == full))
                except Exception:
                    errors.append(dict(scenario=scenario, arm=arm, seed=seed, mask=mask, error=traceback.format_exc()[-400:]))
                    continue
                for f, v in out.items():
                    delay_rows.append(dict(scenario=scenario, arm=arm, seed=seed, mask=mask, flow=f, n_pkts=v["n"], D=v["D"], sig=v["sig"]))
                if keep == full:
                    for i in ids:
                        mine = [p for p in rx.delivered_packets if p.flow_id == i]
                        n = len(mine)
                        meanx = (sum(p.cross_blocking for p in mine) / n) if n else float("nan")
                        forced = rx.forced_cross.get(i, 0.0) / n if n else float("nan")
                        for j in ids:
                            if j == i:
                                continue
                            blame_rows.append(dict(scenario=scenario, arm=arm, seed=seed, blocker=j, victim=i,
                                                   blame_sum=rx.blame.get((j, i), 0.0), n_delivered_victim=n,
                                                   forced_cross_victim=forced, meanX_victim=meanx))
        print(f"done {scenario}/{arm} ({time.time() - t0:.0f}s, errors={len(errors)})", flush=True)
    RES.mkdir(exist_ok=True)
    with open(RES / "raw_s2_blame.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(blame_rows[0].keys()))
        w.writeheader()
        w.writerows(blame_rows)
    with open(RES / "raw_s2_delay.csv", "w", newline="") as f:      # written last = completion marker
        w = csv.DictWriter(f, fieldnames=list(delay_rows[0].keys()))
        w.writeheader()
        w.writerows(delay_rows)
    (RES / "run_manifest_study2.json").write_text(json.dumps(dict(
        seeds=[SEEDS[0], SEEDS[-1]], n_errors=len(errors), errors=errors, seconds=round(time.time() - t0, 1),
        prereg_sha256=hashlib.sha256((HERE / "PREREGISTRATION_STUDY2.md").read_bytes()).hexdigest()), indent=1))
    print(f"done in {time.time() - t0:.0f}s, errors={len(errors)}, delay_rows={len(delay_rows)}, blame_rows={len(blame_rows)}")


if __name__ == "__main__":
    main()
