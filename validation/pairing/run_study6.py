"""run_study6.py - the single confirmatory Study 6 pass (H20-H24, D2; see PREREGISTRATION_STUDY6.md). Refuses to run if the
preregistration changed or results exist. Writes results/raw_s6_*.csv and results/run_manifest_study6.json.
ns-3 per-packet traces are processed in the worker and deleted (they are regenerable: ns-3 runs are deterministic given seed and script)."""
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import airport as ap
import study6 as s6
from run_study5 import oracle_errors
from src.mlo_sim.core import BlockAckReceiver, Packet

HERE = Path(__file__).resolve().parent
NS3 = HERE.parent / "ns3"
sys.path.insert(0, str(NS3))
import nsrun  # noqa: E402
import run_campaign as rc  # noqa: E402

RES = HERE / "results"
TMP = Path(os.environ.get("S6_TMP", "/tmp/claude-1000/-home-adhyan-Desktop-wifi7-mlo-hol/9ba076f6-e9e7-4d20-a641-40966f8bb6c8/scratchpad/s6"))
NS_SEEDS = list(range(61, 101))
D2_SEEDS = list(range(101, 111))
CONDS = ("A1", "A2")
SCALES = (1.0, 2.5)
WARM_MS = 200.0
FLOWS = ((1, 400.0, 200), (2, 1500.0, 1000), (3, 800.0, 600))   # flow, packets/s at scale 1, bytes
CFG = json.loads((NS3 / "configs" / "conditions.json").read_text())


# ------------------------------------------------------------------------------------------------ H20 / H21
INF = float("inf")
G4_CONFIGS = [(W, tau, pl) for W in (8, 16, 64) for tau in (INF, 3.0, 10.0) for pl in (0.05, 0.0)]
G4_N = 50


def task_g4(ci, i):
    W, tau, pl = G4_CONFIGS[ci]
    seed = 27000 + 100 * ci + i
    rx, A, F, T_, At, fl, t = s6.gen_trace(seed, W, tau, ploss=pl)
    n = len(A)
    R = np.maximum.accumulate(At)
    deliv = {p.seq_num: p for p in rx.delivered_packets}
    want = {k for k in range(n) if A[k] < min(F[k], T_[k]) and np.isfinite(R[k])}
    mismatch = len(want ^ set(deliv))
    slots = s6.slot_packets(fl, t, At)
    hist = {p.seq_num: p for p in slots if p.arr_rx_time is not None}
    ids = {p.packet_id for p in rx.delivered_packets}
    T = ap.lateness_table(list(hist.values()), ids)
    bmap = {p.packet_id: b for p, b in zip(T["packets"], T["b"])}
    for p in rx.delivered_packets:                       # copy the receiver's release times onto the slot packets
        sp = hist[p.seq_num]
        sp.rel_time = p.rel_time
        sp.cross_blocking = p.rel_time - bmap[p.packet_id]
    n_events = rx.window_advances_forced + rx.timeout_events
    fake = SimpleNamespace(history=hist, window_advances_forced=n_events, delivered_packets=[hist[p.seq_num] for p in rx.delivered_packets])
    row = oracle_errors(fake, seed, False)
    # descriptive: blocked packets whose largest lateness is produced by a skipped slot
    nb = ns = 0
    flows_sorted = T["flows"]
    for k, p in enumerate(T["packets"]):
        l = np.delete(T["ell"][k], T["flow"][k])
        if len(l) and l.max() > 0:
            nb += 1
            oth = [f for f in flows_sorted if f != p.flow_id]
            jstar = oth[int(np.argmax(l))]
            cand = [s for s in range(p.seq_num) if int(fl[s]) == jstar and np.isfinite(At[s])]
            s_star = max(cand, key=lambda s: At[s])
            ns += int(At[s_star] < A[s_star])
    # certificate (T11): release equals the maximum PHYSICAL arrival over received packets with SN <= k
    phys = [p for p in s6.slot_packets(fl, t, np.where(np.isfinite(A), A, np.inf)) if p.arr_rx_time is not None]
    Tp = ap.lateness_table(phys, ids)
    skipped = np.maximum.accumulate((At < A).astype(int))          # a slot <= k resolved before its physical arrival
    n_cert = n_rej = n_false_rej = n_skip_cert = 0
    for k, p in enumerate(Tp["packets"]):
        ok = abs(hist[p.seq_num].rel_time - Tp["prefix_max"][k]) <= 1e-9
        sk = bool(skipped[p.seq_num])
        n_cert += ok
        n_rej += (not ok)
        n_false_rej += (not ok) and (not sk)
        n_skip_cert += ok and sk
    # T10 bounded error (loss-free traces): ideal lateness from physical arrivals vs effective lateness
    t10_viol = t10_l_viol = 0
    t10_max_ratio = 0.0
    if pl == 0.0:
        delta = np.maximum.accumulate(np.where(np.isfinite(A), A - At, 0.0))
        for k, p in enumerate(T["packets"]):
            f = T["flow"][k]
            l1, l0 = np.delete(T["ell"][k], f), np.delete(Tp["ell"][k], f)
            if not len(l1):
                continue
            dk = delta[p.seq_num]
            if np.abs(l1 - l0).max() > dk + 1e-12:
                t10_l_viol += 1
            dphi = np.abs(ap.shapley_airport(l1) - ap.shapley_airport(l0)).sum()
            if dphi > 2 * len(l1) * dk + 1e-12:
                t10_viol += 1
            if dk > 0:
                t10_max_ratio = max(t10_max_ratio, dphi / (2 * len(l1) * dk))
    row.update(cell=f"W{W}_tau{'none' if not np.isfinite(tau) else int(tau)}_loss{pl}", seed=seed, W=W, tau=(-1 if not np.isfinite(tau) else tau),
               ploss=pl, forced_events=n_events, n_delivered=len(deliv), n_lost=int(np.isinf(A).sum()),
               n_late_discard=int(np.sum(np.isfinite(A) & (A >= np.minimum(F, T_)))), set_mismatch=mismatch, n_blocked=nb,
               n_blocked_skipped=ns, n_cert=n_cert, n_rej=n_rej, n_false_rej=n_false_rej, n_skip_but_cert=n_skip_cert,
               T10_l_viol=t10_l_viol, T10_phi_viol=t10_viol, T10_max_ratio=t10_max_ratio, t_sim_s=0.0)
    return "g4", row


# ------------------------------------------------------------------------------------------------ ns-3
def read_trace(path):
    rows = []
    for r in csv.DictReader(open(path)):
        rows.append(dict(flow=int(r["flow"]), app_seq=int(r["app_seq"]), sn=int(r["sn"]), ins=float(r["rx_insert_ms"]),
                         rel=float(r["rx_release_ms"]), first_tx=float(r["first_tx_ms"]), sink=float(r["sink_ms"])))
    return rows


def python_receiver(rec):
    pk = []
    for dense, r in enumerate(rec):
        p = Packet(packet_id=dense + 1, flow_id=r["flow"], size_bytes=1, arr_time=r["first_tx"])
        p.seq_num = dense
        pk.append(p)
    rx = BlockAckReceiver(win_size=10 ** 9)
    for i in sorted(range(len(rec)), key=lambda i: (rec[i]["ins"], i)):
        rx.receive_packet(pk[i], rec[i]["ins"])
    return rx, pk


def analyze_trace(rows):
    """Common per-run analysis. Returns (rec sorted by ext, rx, pk, dict of H22/H23 metrics)."""
    rec = [r for r in rows if r["ins"] >= 0]
    s6.unwrap_ext(rec)
    dup = len(rec) - len({r["ext"] for r in rec})
    rec.sort(key=lambda r: r["ext"])
    ins = np.array([r["ins"] for r in rec])
    rel = np.array([r["rel"] for r in rec])
    pm = np.maximum.accumulate(ins)
    mask = (rel >= 0) & (ins >= WARM_MS)
    err = np.abs(rel - pm)[mask]
    rx, pk = python_receiver(rec)
    dl = {p.packet_id: p for p in rx.delivered_packets}
    perr, pmis = 0.0, 0
    for i, r in enumerate(rec):
        if r["ins"] < WARM_MS:
            continue
        d = dl.get(i + 1)
        if r["rel"] >= 0:
            if d is None:
                pmis += 1
            else:
                perr = max(perr, abs(d.rel_time - r["rel"]))
        elif d is not None:
            pmis += 1
    m = dict(n_traced=len(rows), n_received=len(rec), n_checked=int(mask.sum()), n_blocked_ns3=int(((rel - ins) > 1e-9).sum()),
             ext_dups=dup, N1_max_err=float(err.max()) if len(err) else 0.0, N1_viol=int((err > 1e-6).sum()),
             py_max_err=perr, py_mismatch=pmis)
    return rec, rx, pk, m


def blocker_stats(rec, flow=1):
    """Whole-wait cross/within attribution of the ns-3 binary for packets of `flow` (delivered)."""
    bb = s6.binding_blockers(rec)
    cross = within = 0.0
    n = 0
    for i, r in enumerate(rec):
        if r["flow"] != flow or r["rel"] < 0 or r["sink"] <= 0:
            continue
        n += 1
        w = max(0.0, r["rel"] - r["ins"])
        if i in bb and bb[i] is not None:
            if bb[i] == flow:
                within += w
            else:
                cross += w
    return n, cross, within


def run_ns3(args, tdir, tag):
    trace = Path(tdir) / f"{tag}.trace.csv"
    args = dict(args, traceOut=trace)
    row = nsrun.run(args, profile="optimized", timeout=1800)
    return row, read_trace(trace)


def task_ns3(ci, li, seed):
    cond, scale = CONDS[ci], SCALES[li]
    p = CFG["main_conditions"][cond]
    rng = np.random.default_rng([seed, ci, li])
    ev = []
    for fl, rate, size in FLOWS:
        r = rate * scale
        t = np.cumsum(rng.exponential(1.0 / r, int(r * 5 * 1.4) + 50))
        ev += [(float(x), fl, size) for x in t if 0.1 < x < 4.5]
    ev.sort()
    TMP.mkdir(parents=True, exist_ok=True)
    tdir = tempfile.mkdtemp(dir=TMP)
    try:
        sp = Path(tdir) / "s.csv"
        with open(sp, "w") as f:
            f.write("# t_s,flow,size\n")
            for t, fl, s in ev:
                f.write(f"{t:.9f},{fl},{s}\n")
        args = dict(simTime=5, scheduler=0, seed=seed, script=sp, warmup=0, drain=0, mcs0=p["mcs0"], mcs1=p["mcs1"],
                    width0=p["width0"], width1=p["width1"], rss0=p["rss0"], rss1=p["rss1"])
        t0 = time.perf_counter()
        csvrow, rows = run_ns3(args, tdir, "a")
        t_run = time.perf_counter() - t0
        rec, rx, pk, m = analyze_trace(rows)
        n1, cross, within = blocker_stats(rec, 1)
        orc = oracle_errors(rx, seed, False)
        # X16: maximum simultaneously buffered packets reconstructed from the trace (insert before release at equal times)
        ev2 = sorted([(r["ins"], 0) for r in rec] + [(r["rel"], 1) for r in rec if r["rel"] >= 0])
        cur = mx = 0
        for _, typ in ev2:
            cur += 1 if typ == 0 else -1
            mx = max(mx, cur)
        row = dict(cond=cond, scale=scale, seed=seed, forced_adv_events=csvrow["forced_adv_events"],
                   audit_untagged_tx=csvrow["audit_untagged_tx"], **m,
                   h24_n1=n1, h24_ls_rcvd=csvrow["ls_rcvd"],
                   h24_cross=(cross / n1) if n1 else float("nan"), h24_within=(within / n1) if n1 else float("nan"),
                   csv_cross=csvrow["cross_wait_ms"], csv_within=csvrow["within_wait_ms"],
                   O2=orc["O2"], O3=orc["O3"], O4=orc["O4"], n_O4=orc["n_O4"], O6_viol=orc["O6_viol"], O6_err=orc["O6_err"],
                   O7_viol=orc["O7_viol"], frac_blocked=orc["frac_blocked"], frac_single_late=orc["frac_single_late"],
                   occ_trace_max=mx, occ_csv_max=csvrow["buf_occ_max"], t_run_s=t_run)
        return "ns3", row
    finally:
        shutil.rmtree(tdir, ignore_errors=True)


def task_d2(ci, load, seed):
    cond = CONDS[ci]
    p = CFG["main_conditions"][cond]
    TMP.mkdir(parents=True, exist_ok=True)
    tdir = tempfile.mkdtemp(dir=TMP)
    try:
        args = dict(seed=seed, scheduler=0, cond=cond, load=load, weightRatio=CFG["main_weight_ratio"],
                    bulkMbps=p["bulk_mbps"][load], mcs0=p["mcs0"], mcs1=p["mcs1"], width0=p["width0"], width1=p["width1"],
                    rss0=p["rss0"], rss1=p["rss1"], simTime=rc.SIM_TIME, warmup=0.5, drain=0.3, buildId=rc.build_id(), runId=seed)
        csvrow, rows = run_ns3(args, tdir, "d")
        rec, rx, pk, m = analyze_trace(rows)
        bb = s6.binding_blockers(rec)
        dl = {p_.packet_id: p_ for p_ in rx.delivered_packets}
        n = 0
        sx = ss = sc = sw = 0.0
        for i, r in enumerate(rec):
            if r["flow"] != 1 or r["rel"] < 0 or not (500.0 <= r["first_tx"] <= 9700.0):
                continue
            d = dl.get(i + 1)
            if d is None:
                continue
            n += 1
            w = max(0.0, r["rel"] - r["ins"])
            sx += d.cross_blocking
            ss += d.self_blocking
            sw += w
            if i in bb and bb[i] is not None and bb[i] != 1:
                sc += w
        return "d2", dict(cond=cond, load=load, seed=seed, n=n, sum_X=sx, sum_S=ss, sum_ns3cross=sc, sum_wait=sw,
                          forced_adv_events=csvrow["forced_adv_events"], N1_viol=m["N1_viol"], ext_dups=m["ext_dups"])
    finally:
        shutil.rmtree(tdir, ignore_errors=True)


# ------------------------------------------------------------------------------------------------ driver
def dump(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        keys = list(rows[0].keys())
        w.writerow(keys)
        for r in rows:
            w.writerow([r[k] for k in keys])


def main():
    want = (HERE / "PREREGISTRATION_STUDY6.sha256").read_text().split()[0]
    if hashlib.sha256((HERE / "PREREGISTRATION_STUDY6.md").read_bytes()).hexdigest() != want:
        sys.exit("refusing to run: Study 6 preregistration changed after hashing")
    if (RES / "raw_s6_d2.csv").exists():
        sys.exit("refusing to run: Study 6 results exist (single-use)")
    frozen = json.loads((NS3 / "configs" / "FREEZE.json").read_text())["sha256"]
    bad = [f for f, h in frozen.items() if f != "analyze_results.py" and hashlib.sha256((NS3 / f).read_bytes()).hexdigest() != h]
    if bad:
        sys.exit(f"refusing to run: ns-3 files changed after freeze: {bad}")
    t0 = time.time()
    jobs = []
    for ci in range(len(G4_CONFIGS)):
        jobs += [(task_g4, (ci, i)) for i in range(G4_N)]
    for ci in range(2):
        for li in range(2):
            jobs += [(task_ns3, (ci, li, s)) for s in NS_SEEDS]
    for ci in range(2):
        for load in ("L0", "L1", "L2"):
            jobs += [(task_d2, (ci, load, s)) for s in D2_SEEDS]
    g4, ns, d2, errors = [], [], [], []
    with ProcessPoolExecutor(12) as ex:
        futs = {ex.submit(fn, *a): (fn.__name__, a) for fn, a in jobs}
        for n, fu in enumerate(as_completed(futs), 1):
            name, a = futs[fu]
            try:
                kind, res = fu.result()
                {"g4": g4, "ns3": ns, "d2": d2}[kind].append(res)
            except Exception:
                errors.append(dict(task=name, args=str(a), error=traceback.format_exc()[-400:]))
            if n % 50 == 0:
                print(f"{n}/{len(jobs)} done ({time.time() - t0:.0f}s, errors={len(errors)})", flush=True)
    RES.mkdir(exist_ok=True)
    dump(RES / "raw_s6_g4.csv", sorted(g4, key=lambda r: r["seed"]))
    dump(RES / "raw_s6_ns3.csv", sorted(ns, key=lambda r: (r["cond"], r["scale"], r["seed"])))
    dump(RES / "raw_s6_d2.csv", sorted(d2, key=lambda r: (r["cond"], r["load"], r["seed"])))        # last = completion marker
    (RES / "run_manifest_study6.json").write_text(json.dumps(dict(
        n_errors=len(errors), errors=errors, seconds=round(time.time() - t0, 1), n_jobs=len(jobs), n_g4=len(g4), n_ns3=len(ns),
        n_d2=len(d2), prereg_sha256=hashlib.sha256((HERE / "PREREGISTRATION_STUDY6.md").read_bytes()).hexdigest()), indent=1))
    print(f"done {len(jobs)} jobs, {len(errors)} errors, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
