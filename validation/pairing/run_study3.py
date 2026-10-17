"""run_study3.py - Study 3 Python parts: H10 (pinned-link boundary, seeds 23000-23099) and H12 raw coalition data
(seeds 22000-22099). Refuses to run if the Study 3 preregistration changed or results exist (single use).
Writes results/raw_s3_h10.csv, results/raw_s3_h12_delay.csv, results/raw_s3_h12_blame.csv, results/run_manifest_study3.json."""
import csv
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

import study as st
import study2 as s2
from src.mlo_sim.schedulers import StaticPinningScheduler

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
H10_SEEDS = list(range(23000, 23100))
H12_SEEDS = list(range(22000, 22100))
D = st.DURATION_MS


class CountingPinned(StaticPinningScheduler):
    """StaticPinning that counts true dispatch stalls (window blocks a pinned flow whose link is idle)."""

    def __init__(self, mapping):
        super().__init__(mapping=mapping)
        self.stalls = 0

    def schedule(self, current_time, available_links, queues, flows, inflight_packets, win_size, win_start):
        if available_links and self.next_seq_num >= win_start + win_size:
            for link in available_links:
                if any(l == link.link_id and f in queues and queues[f] for f, l in self.mapping.items()):
                    self.stalls += 1
                    break
        return super().schedule(current_time, available_links, queues, flows, inflight_packets, win_size, win_start)


def run_h10(cond, keep, seed):
    flows, links, chans = st.build("S2", fer=0.01)
    flows = [f for f in flows if f.flow_id in keep]
    if cond == "F64":
        sched, win = st.make_sched("FIFO"), 64
    else:
        sched, win = CountingPinned({1: 0, 2: 1}), (256 if cond == "P256" else 64)
    sim = st.StudySimulator(flows, links, chans, sched, win_size=win, seed=seed, design="keyed")
    rx = sim.run(duration_ms=D)
    out = {}
    for f in flows:
        mine = [p for p in rx.delivered_packets if p.flow_id == f.flow_id]
        n = len(mine)
        out[f.flow_id] = dict(n=n, e2e=sum(p.end_to_end_delay for p in mine) / n if n else float("nan"),
                              X=sum(p.cross_blocking for p in mine) / n if n else float("nan"))
    drops = sum(l.total_dropped_pkts for l in sim.links.values())
    return out, dict(stalls=getattr(sched, "stalls", 0), drops=drops, forced=rx.window_advances_forced)


def main():
    want = (HERE / "PREREGISTRATION_STUDY3.sha256").read_text().split()[0]
    if hashlib.sha256((HERE / "PREREGISTRATION_STUDY3.md").read_bytes()).hexdigest() != want:
        sys.exit("refusing to run: Study 3 preregistration changed after hashing")
    if (RES / "raw_s3_h10.csv").exists():
        sys.exit("refusing to run: Study 3 results exist (single-use)")
    t0, errors = time.time(), []
    h10 = []
    for cond in ("P256", "P64", "F64"):
        for seed in H10_SEEDS:
            try:
                full, mf = run_h10(cond, {1, 2}, seed)
                for i in (1, 2):
                    solo, ms = run_h10(cond, {i}, seed)
                    h10.append(dict(cond=cond, seed=seed, victim=i, n_full=full[i]["n"], n_solo=solo[i]["n"],
                                    e2e_full=full[i]["e2e"], X_full=full[i]["X"], e2e_solo=solo[i]["e2e"],
                                    stalls_full=mf["stalls"], stalls_solo=ms["stalls"], drops_full=mf["drops"],
                                    drops_solo=ms["drops"], forced_full=mf["forced"]))
            except Exception:
                errors.append(dict(kind="h10", cond=cond, seed=seed, error=traceback.format_exc()[-400:]))
    print(f"h10 done ({time.time() - t0:.0f}s, errors={len(errors)})", flush=True)

    delay_rows, blame_rows = [], []
    ids = [1, 2, 3, 4]
    full = frozenset(ids)
    for arm in ("FullSASP", "FIFO"):
        for seed in H12_SEEDS:
            for mask, keep in s2.masks(ids):
                try:
                    sim, rx, out = s2.run_coalition("S4", keep, arm, seed, blame=(keep == full))
                except Exception:
                    errors.append(dict(kind="h12", arm=arm, seed=seed, mask=mask, error=traceback.format_exc()[-400:]))
                    continue
                for f, v in out.items():
                    delay_rows.append(dict(arm=arm, seed=seed, mask=mask, flow=f, D=v["D"], sig=v["sig"]))
                if keep == full:
                    for i in ids:
                        n = sum(1 for p in rx.delivered_packets if p.flow_id == i)
                        for j in ids:
                            if j != i:
                                blame_rows.append(dict(arm=arm, seed=seed, blocker=j, victim=i,
                                                       blame_sum=rx.blame.get((j, i), 0.0), n_victim=n))
    print(f"h12 done ({time.time() - t0:.0f}s, errors={len(errors)})", flush=True)
    RES.mkdir(exist_ok=True)

    def dump(name, rows):
        with open(RES / name, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    dump("raw_s3_h12_blame.csv", blame_rows)
    dump("raw_s3_h12_delay.csv", delay_rows)
    dump("raw_s3_h10.csv", h10)                      # last = completion marker
    (RES / "run_manifest_study3.json").write_text(json.dumps(dict(
        n_errors=len(errors), errors=errors, seconds=round(time.time() - t0, 1),
        prereg_sha256=hashlib.sha256((HERE / "PREREGISTRATION_STUDY3.md").read_bytes()).hexdigest()), indent=1))
    print(f"done errors={len(errors)}")


if __name__ == "__main__":
    main()
