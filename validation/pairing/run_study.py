"""run_study.py - the single confirmatory pass (seeds 7000-7099). Refuses to run if the preregistration
files changed since their recorded hashes, or if results already exist. Never drops a failed run."""
import csv
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

import study as st

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
SEEDS = list(range(7000, 7100))
PREREG = ["PREREGISTRATION.md", "PREREGISTRATION_AMENDMENT_1.md", "PREREGISTRATION_AMENDMENT_2.md"]
T_TRUNC = 150.0


def verify():
    for f in PREREG:
        want = (HERE / f.replace(".md", ".sha256")).read_text().split()[0]
        got = hashlib.sha256((HERE / f).read_bytes()).hexdigest()
        if want != got:
            sys.exit(f"refusing to run: {f} changed after hashing")
    if (RES / "raw_main.csv").exists():
        sys.exit("refusing to run: results already exist (confirmatory pass is single-use)")
    RES.mkdir(exist_ok=True)


def write(name, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(RES / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {name}: {len(rows)} rows", flush=True)


def safe(fn, log, **ctx):
    try:
        return fn()
    except Exception:  # a failed run is recorded, not replaced
        log.append(dict(ctx, error=traceback.format_exc()[-500:]))
        return None


def run_runs(errors):
    main, drain, h4, h5, h6, e1 = [], [], [], [], [], []
    D = st.DURATION_MS

    for scale in st.SCALES:
        for design in ("shared", "naive", "keyed"):
            for arm in st.ARMS:
                for seed in SEEDS:
                    r = safe(lambda: st.simulate(scale, design, arm, seed), errors,
                             kind="main", scale=scale, design=design, arm=arm, seed=seed)
                    if r:
                        main.append(dict(scale=scale, design=design, arm=arm, seed=seed, **st.summarize(*r[:2], D, r[2])))
    print("main done", flush=True)

    for arm in st.ARMS:
        for fer in (0.01, 0.0):
            for seed in SEEDS:
                r = safe(lambda: st.simulate("S2", "keyed", arm, seed, fer=fer, arrival_horizon=D, drain=True), errors,
                         kind="drain", arm=arm, fer=fer, seed=seed)
                if r:
                    drain.append(dict(arm=arm, fer=fer, seed=seed, **st.summarize(*r[:2], D, r[2])))
    print("drain done", flush=True)

    for arm in ("FIFO", "FullSASP"):
        for seed in SEEDS:
            a = safe(lambda: st.simulate("S2", "keyed", arm, seed), errors, kind="h4", arm=arm, seed=seed)
            b = safe(lambda: st.simulate("S2", "keyed", arm, seed, drop_flow_ids=(2,)), errors, kind="h4b", arm=arm, seed=seed)
            if a and b:
                sa, sb = st.summarize(*a[:2], D, a[2]), st.summarize(*b[:2], D, b[2])
                rx = a[1]
                hist = {p.seq_num: p for p in rx.history.values() if p.flow_id == 1 and p.arr_rx_time is not None}
                tdiff = 0.0
                for p in (q for q in rx.delivered_packets if q.flow_id == 1):
                    preds = [q.arr_rx_time for s, q in hist.items() if s < p.seq_num]
                    tdiff = max(tdiff, abs(max(0.0, max([p.arr_rx_time] + preds) - p.arr_rx_time) - p.self_blocking))
                h4.append(dict(arm=arm, seed=seed, self1_with=sa["self1"], n1_with=sa["n1"], self1_without=sb["self1"],
                               n1_without=sb["n1"], trace_control_maxdiff=tdiff))
    print("h4 done", flush=True)

    for variant, single in (("shipped", False), ("single", True)):
        for scen, kw in (("default", dict(fer=0.01)), ("nobursts", dict(fer=0.01, burst_prob=0.0)),
                         ("bursts", dict(fer=0.01, burst_prob=0.02, burst_recovery=0.5))):
            for seed in SEEDS:
                r = safe(lambda: st.simulate("S2", "shared", "FIFO", seed, single_draw=single, **kw), errors,
                         kind="h5", variant=variant, scen=scen, seed=seed)
                if not r:
                    continue
                sim = r[0]
                row = dict(variant=variant, scen=scen, seed=seed, attempts=len(sim.attempt_draw_counts),
                           draws=sum(sim.attempt_draw_counts), not_one=sum(1 for c in sim.attempt_draw_counts if c != 1))
                n_att = n_lost = n_runs = sum_len = 0
                for outs in sim.loss_outcomes.values():
                    cur = 0
                    for o in outs:
                        n_att += 1
                        n_lost += o
                        if o:
                            cur += 1
                        elif cur:
                            n_runs += 1
                            sum_len += cur
                            cur = 0
                    if cur:
                        n_runs += 1
                        sum_len += cur
                row.update(n_att=n_att, n_lost=n_lost, n_runs=n_runs, sum_len=sum_len)
                h5.append(row)
    print("h5 done", flush=True)

    for arm in ("FIFO", "FullSASP", "MeanOnly", "LeakyGlobal", "LeakyLocal"):
        for seed in SEEDS:
            a = safe(lambda: st.simulate("S2", "keyed", arm, seed, duration=T_TRUNC, arrival_horizon=T_TRUNC,
                                         stop=T_TRUNC, trace_horizon=T_TRUNC), errors, kind="h6a", arm=arm, seed=seed)
            b = safe(lambda: st.simulate("S2", "keyed", arm, seed, duration=D, arrival_horizon=D, stop=T_TRUNC,
                                         trace_horizon=D), errors, kind="h6b", arm=arm, seed=seed)
            if a and b:
                pa = [st.pkt_tuple(p) for p in a[1].delivered_packets if p.rel_time <= T_TRUNC]
                pb = [st.pkt_tuple(p) for p in b[1].delivered_packets if p.rel_time <= T_TRUNC]
                h6.append(dict(arm=arm, seed=seed, violated=int(pa != pb), n_compared=len(pb)))
    print("h6 done", flush=True)

    for fer in (0.01, 0.05, 0.10, 0.20, 0.30):
        for seed in SEEDS:
            sigs = []
            for arm in ("FIFO", "FullSASP"):
                r = safe(lambda: st.simulate("S2", "shared", arm, seed, fer=fer), errors, kind="e1", arm=arm, fer=fer, seed=seed)
                sigs.append(st.summarize(*r[:2], D, r[2])["arr_sig"] if r else None)
            if None not in sigs:
                e1.append(dict(fer=fer, seed=seed, mismatch=int(sigs[0] != sigs[1])))
    print("e1 done", flush=True)
    return main, drain, h4, h5, h6, e1


def main():
    verify()
    t0 = time.time()
    errors = []
    main_, drain, h4, h5, h6, e1 = run_runs(errors)
    for name, rows in (("raw_drain.csv", drain), ("raw_h4.csv", h4), ("raw_h5.csv", h5), ("raw_h6.csv", h6),
                       ("raw_e1.csv", e1), ("raw_main.csv", main_)):     # raw_main last = completion marker
        write(name, rows)
    (RES / "run_manifest.json").write_text(json.dumps(dict(
        seeds=[SEEDS[0], SEEDS[-1]], n_errors=len(errors), errors=errors, seconds=round(time.time() - t0, 1),
        prereg_sha256={f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in PREREG}), indent=1))
    print(f"done in {time.time() - t0:.0f}s, errors={len(errors)}")


if __name__ == "__main__":
    main()
