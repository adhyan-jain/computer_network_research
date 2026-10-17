"""run_study5.py - the single confirmatory Study 5 pass (H16-H19, see PREREGISTRATION_STUDY5.md). Refuses to run if the
preregistration changed or results exist. Writes results/raw_s5_*.csv and results/run_manifest_study5.json."""
import csv
import hashlib
import itertools
import json
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

import airport as ap
import airport_fast as af
import study as st
from study2 import BlameReceiver, masks
from src.mlo_sim.core import BlockAckReceiver, Packet

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
D = st.DURATION_MS
CELLS = {"C1": ("S4", "FIFO", 1.0, 0.1), "C2": ("S4", "FullSASP", 1.0, 0.1), "C3": ("S4", "FIFO", 0.75, 3.0),
         "C4": ("S8", "FIFO", 1.0, 0.1), "C5": ("S8", "FIFO", 1.0, 3.0)}
H16_SEEDS = list(range(26000, 26100))
H17_CELLS = {"A": ("S4", 1.0, 0.1, list(range(26200, 26300))), "B": ("S4", 0.75, 3.0, list(range(26300, 26400)))}
GEN_SEEDS = list(range(26600, 26700))
H18_SEEDS = list(range(26400, 26450))
H18_CELLS = {"C1": 1, "C2": 2, "C3": 3}
EPS = (0.01, 0.1, 1.0)

DF, DS = ap.PathDelay([(1, 1, 0.3)]), ap.PathDelay([(1, 3, 0.5)])
DM, DD = ap.PathDelay([(.5, 1, .3), (.5, 3, .5)]), ap.PathDelay([(1, 2, 0.0)])
DH = ap.PathDelay([(.8, 1, .2), (.2, 6, 2)])
H19 = [("P1", DF, [DS], [0.2, 0.1]), ("P2", DF, [DS, DM], [0.2, 0.1, 0.15]),
       ("P3", DM, [DF, DS, DD], [0.15, 0.1, 0.1, 0.2]), ("P4", DM, [DM, DM, DM], [0.2, 0.2, 0.2, 0.2]),
       ("P5", DF, [DH, DH], [0.3, 0.05, 0.05]), ("P6", DD, [DF, DS], [0.1, 0.3, 0.1]),
       ("P7", DH, [DF, DM, DS], [0.05, 0.25, 0.15, 0.1]), ("P8", DF, [DS, DS, DS, DS], [0.2, 0.05, 0.05, 0.05, 0.05])]


# ------------------------------------------------------------------------------------------------ simulator helpers
def make_sim(scale, sched, lm, dm, seed, keep=None, blame=False):
    flows, links, chans = st.build(scale, fer=0.01, delta_mu=dm)
    if keep is not None:
        flows = [f for f in flows if f.flow_id in keep]
    for f in flows:
        f.rate_pkts_per_sec *= lm
    sim = st.StudySimulator(flows, links, chans, st.make_sched(sched), seed=seed, design="keyed")
    if blame:
        sim.receiver = BlameReceiver(win_size=sim.win_size)
    return sim, flows


def oracle_errors(rx, seed, with_o5):
    rng = np.random.default_rng(seed)
    rec = list(rx.history.values())
    deliv = {p.packet_id for p in rx.delivered_packets}
    T = ap.lateness_table(rec, deliv)
    pk, ell, fo = T["packets"], T["ell"], T["flow"]
    P = len(pk)
    o1 = max((abs(p.rel_time - T["prefix_max"][k]) for k, p in enumerate(pk)), default=0.0)
    o2 = max((abs(p.cross_blocking - ell[k].max()) for k, p in enumerate(pk)), default=0.0)
    ls = [np.delete(ell[k], fo[k]) for k in range(P)]
    t0 = time.perf_counter()
    phis = [ap.shapley_airport(l) for l in ls]
    t_closed = (time.perf_counter() - t0) * 1000
    sample = rng.choice(P, size=min(100, P), replace=False) if P else []
    o3 = 0.0
    o7 = 0
    for k in sample:
        l = ls[k]
        brute = ap.shapley_bruteforce(l)
        o3 = max(o3, float(np.abs(phis[k] - brute).max()) if len(l) else 0.0, abs(phis[k].sum() - (l.max() if len(l) else 0.0)))
        m = len(l)
        for _ in range(20):
            S = [j for j in range(m) if rng.random() < 0.5]
            if S and phis[k][S].sum() > l[S].max() + 1e-12:
                o7 += 1
    # O4: delete flows from the trace, rebuild with the unmodified receiver
    ids = T["flows"]
    o4, n4 = 0.0, 0
    for _ in range(3):
        vic = int(rng.choice(ids))
        Tset = [o for o in ids if o != vic and rng.random() < 0.5]
        out = ap.rebuild_cross_blocking(rec, set(Tset) | {vic})
        col = [ids.index(o) for o in Tset]
        for k, p in enumerate(pk):
            if p.flow_id == vic and p.packet_id in out:
                o4 = max(o4, abs(out[p.packet_id] - max([ell[k][c] for c in col], default=0.0)))
                n4 += 1
    o5 = None
    if with_o5:
        got = {}
        for k, p in enumerate(pk):
            oth = [f for f in ids if f != p.flow_id]
            for f, v in zip(oth, ap.releaser_blame(ls[k])):
                if v:
                    got[(f, p.flow_id)] = got.get((f, p.flow_id), 0.0) + v
        o5 = max((abs(got.get(key, 0.0) - rx.blame.get(key, 0.0)) for key in set(got) | set(rx.blame)), default=0.0)
    o6_viol, o6_err = 0, 0.0
    for k in range(P):
        l = ls[k]
        if not len(l):
            continue
        loo = ap.loo_blame(l)
        X = l.max()
        if loo.sum() > X + 1e-12 or X > l.sum() + 1e-12:
            o6_viol += 1
        srt = np.sort(l)
        want = np.zeros(len(l))
        if (l == X).sum() == 1:
            want[int(np.argmax(l))] = X - (srt[-2] if len(l) > 1 else 0.0)
        o6_err = max(o6_err, float(np.abs(loo - want).max()))
    blocked = [l for l in ls if len(l) and l.max() > 0]
    return dict(forced=rx.window_advances_forced, n_pkts=P, O1=o1, O2=o2, O3=o3, O4=o4, n_O4=n4,
                O5=("" if o5 is None else o5), O6_viol=o6_viol, O6_err=o6_err, O7_viol=o7,
                frac_blocked=len(blocked) / P if P else 0.0,
                frac_single_late=float(np.mean([(l > 0).sum() == 1 for l in blocked])) if blocked else 0.0,
                t_closed_ms=t_closed)


def task_h16_sim(cell, seed):
    scale, sched, lm, dm = CELLS[cell]
    sim, _ = make_sim(scale, sched, lm, dm, seed, blame=True)
    t0 = time.perf_counter()
    rx = sim.run(duration_ms=D)
    t_sim = time.perf_counter() - t0
    row = oracle_errors(rx, seed, True)
    row.update(cell=cell, seed=seed, t_sim_s=t_sim)
    return "h16", row


def gen_trace(kind, seed):
    rng = np.random.default_rng(seed)
    n = 300
    t = np.cumsum(rng.exponential(1.0, n))
    if kind == "G2":      # streams multiplexed on one ordered connection: base delay plus 50 ms per (geometric) loss
        fl = rng.integers(1, 6, n)
        delay = rng.uniform(10, 12, n) + 50.0 * (rng.geometric(0.98, n) - 1)
    else:                 # G3: flows over statistically identical heavy-tailed paths, Pareto(shape 1.5, scale 1 ms)
        fl = rng.integers(1, 5, n)
        delay = (1.0 - rng.random(n)) ** (-1 / 1.5)
    rx = BlockAckReceiver(win_size=10 ** 9)
    pk = []
    for sn in range(n):
        p = Packet(packet_id=sn + 1, flow_id=int(fl[sn]), size_bytes=1500, arr_time=float(t[sn]))
        p.seq_num = sn
        pk.append((float(t[sn] + delay[sn]), sn, p))
    for a, sn, p in sorted(pk, key=lambda z: (z[0], z[1])):
        rx.receive_packet(p, a)
    return rx


def task_gen(kind, seed):
    rx = gen_trace(kind, seed)
    row = oracle_errors(rx, seed, False)
    row.update(cell=kind, seed=seed, t_sim_s=0.0)
    return "h16", row


# ------------------------------------------------------------------------------------------------ H17
def coalition_means(scale, lm, dm, keep, seed, full):
    sim, flows = make_sim(scale, "FIFO", lm, dm, seed, keep=keep)
    rx = sim.run(duration_ms=D)
    out, extra = {}, None
    for f in flows:
        mine = [p for p in rx.delivered_packets if p.flow_id == f.flow_id]
        n = len(mine)
        allp = [p for p in sim.all_packets if p.flow_id == f.flow_id]

        def avg(g):
            return (sum(g(p) for p in mine) / n) if n else float("nan")
        out[f.flow_id] = dict(n=n, net=avg(lambda p: p.arr_rx_time - p.arr_time), S=avg(lambda p: p.self_blocking),
                              X=avg(lambda p: p.cross_blocking), e2e=avg(lambda p: p.end_to_end_delay),
                              sig=st.hash_arrivals(allp, D))
    if full:
        deliv = {p.packet_id for p in rx.delivered_packets}
        T = ap.lateness_table(list(rx.history.values()), deliv)
        ids = T["flows"]
        t0 = time.perf_counter()
        acc, cnt = {}, {}
        for k, p in enumerate(T["packets"]):
            l = np.delete(T["ell"][k], T["flow"][k])
            oth = [f for f in ids if f != p.flow_id]
            cnt[p.flow_id] = cnt.get(p.flow_id, 0) + 1
            for f, a, r in zip(oth, ap.shapley_airport(l), ap.releaser_blame(l)):
                s = acc.setdefault((f, p.flow_id), [0.0, 0.0])
                s[0] += a
                s[1] += r
        extra = dict(blame={k: (v[0] / cnt[k[1]], v[1] / cnt[k[1]]) for k, v in acc.items()},
                     t_closed_ms=(time.perf_counter() - t0) * 1000)
    return out, rx.window_advances_forced, extra


def task_h17(cell, seed):
    scale, lm, dm, _ = H17_CELLS[cell]
    ids = list(range(1, len(st.SCALES[scale]) + 1))
    coal, blame, t0 = [], [], time.perf_counter()
    forced_total, ext = 0, None
    for mask, keep in masks(ids):
        full = keep == frozenset(ids)
        out, forced, extra = coalition_means(scale, lm, dm, set(keep), seed, full)
        forced_total += forced
        for f, v in out.items():
            coal.append(dict(cell=cell, seed=seed, victim=f, mask=mask, n=v["n"], net=v["net"], S=v["S"], X=v["X"], e2e=v["e2e"],
                             sig=v["sig"], forced=forced))
        if full:
            ext = extra
    t_replay = time.perf_counter() - t0
    for (j, i), (a, r) in ext["blame"].items():
        blame.append(dict(cell=cell, seed=seed, victim=i, blocker=j, airport=a, releaser=r))
    timing = dict(cell=cell, seed=seed, t_replay_s=t_replay, t_closed_ms=ext["t_closed_ms"], forced_total=forced_total)
    return "h17", (coal, blame, timing)


# ------------------------------------------------------------------------------------------------ H18
class _P:
    def __init__(self, p, a):
        self.seq_num, self.flow_id, self.arr_rx_time, self.packet_id = p.seq_num, p.flow_id, a, p.packet_id


def stability_rows(rx, cell, seed, base):
    rec = sorted(rx.history.values(), key=lambda p: p.seq_num)
    deliv = {p.packet_id for p in rx.delivered_packets}
    T0 = ap.lateness_table(rec, deliv)
    rows = []
    for ei, e in enumerate(EPS):
        rng = np.random.default_rng(base + ei)
        noise = rng.uniform(-e, e, len(rec))
        T1 = ap.lateness_table([_P(p, p.arr_rx_time + z) for p, z in zip(rec, noise)], deliv)
        assert [p.packet_id for p in T0["packets"]] == [p.packet_id for p in T1["packets"]]
        dsh, drel, v1, v2, rs, rr = [], [], 0, 0, 0.0, 0.0
        for k in range(len(T0["packets"])):
            f = T0["flow"][k]
            l0, l1 = np.delete(T0["ell"][k], f), np.delete(T1["ell"][k], f)
            if not len(l0):
                continue
            if np.abs(l1 - l0).max() > 2 * e + 1e-12:
                v2 += 1
            s_sh = np.abs(ap.shapley_airport(l1) - ap.shapley_airport(l0)).sum()
            s_rel = np.abs(ap.releaser_blame(l1) - ap.releaser_blame(l0)).sum()
            dl = np.abs(l1 - l0).sum()
            if s_sh > 2 * dl + 1e-12:
                v1 += 1
            if dl > 0:
                rs, rr = max(rs, s_sh / dl), max(rr, s_rel / dl)
            if l0.max() > 0:
                dsh.append(s_sh)
                drel.append(s_rel)
        rows.append(dict(cell=cell, seed=seed, eps=e, n_pos=len(dsh), mean_Dsh=float(np.mean(dsh)) if dsh else float("nan"),
                         mean_Drel=float(np.mean(drel)) if drel else float("nan"), viol_B1=v1, viol_B2=v2,
                         max_ratio_sh=rs, max_ratio_rel=rr))
    return rows


def task_h18(cell, seed):
    scale, sched, lm, dm = CELLS[cell]
    sim, _ = make_sim(scale, sched, lm, dm, seed)
    rx = sim.run(duration_ms=D)
    return "h18", stability_rows(rx, cell, seed, 26400 + 1000 * H18_CELLS[cell] + 10 * (seed - 26400))


def task_x12(kind, seed):
    if kind == "C5":
        scale, sched, lm, dm = CELLS["C5"]
        sim, _ = make_sim(scale, sched, lm, dm, seed)
        rx = sim.run(duration_ms=D)
        base = 26400 + 1000 * 5 + 10 * (seed - 26400)
    else:
        rx = gen_trace(kind, seed)
        base = 26700 + 1000 * (1 if kind == "G2" else 2) + 10 * (seed - 26600)
    return "x12", stability_rows(rx, kind, seed, base)


X12_SEEDS = {"C5": H18_SEEDS, "G2": GEN_SEEDS, "G3": GEN_SEEDS}
X15_CELLS = {"X1": (0.1, 2.0), "X2": (0.25, 2.0), "X3": (0.5, 3.0)}
X15_SEEDS = list(range(26800, 26900))


def task_x15(cell, seed):
    lm, dm = X15_CELLS[cell]
    sim, flows = make_sim("S4", "FIFO", lm, dm, seed)
    rx = sim.run(duration_ms=D)
    deliv = {p.packet_id for p in rx.delivered_packets}
    T = ap.lateness_table(list(rx.history.values()), deliv)
    delays = [dict(cell=cell, seed=seed, flow=p.flow_id, delay=p.arr_rx_time - p.arr_time) for p in rx.history.values()]
    ids = T["flows"]
    sx, cnt, bl = {}, {}, {}
    for k, p in enumerate(T["packets"]):
        l = np.delete(T["ell"][k], T["flow"][k])
        cnt[p.flow_id] = cnt.get(p.flow_id, 0) + 1
        sx[p.flow_id] = sx.get(p.flow_id, 0.0) + (l.max() if len(l) else 0.0)
        for f, a in zip([f for f in ids if f != p.flow_id], ap.shapley_airport(l)):
            bl[(f, p.flow_id)] = bl.get((f, p.flow_id), 0.0) + a
    obs = [dict(cell=cell, seed=seed, victim=i, n=cnt.get(i, 0), X_mean=(sx.get(i, 0.0) / cnt[i]) if cnt.get(i) else float("nan"),
                blocker=0, airport=float("nan")) for i in ids]
    obs += [dict(cell=cell, seed=seed, victim=i, n=cnt.get(i, 0), X_mean=float("nan"), blocker=j,
                 airport=(v / cnt[i]) if cnt.get(i) else float("nan")) for (j, i), v in bl.items()]
    return "x15", (delays, obs)


# ------------------------------------------------------------------------------------------------ H19
def shapley_poisson_chunked(victim, others, rates, n, nt, chunk=200):
    """Same quantity as airport.shapley_poisson, evaluated in chunks to bound memory (trapezoid rule in t)."""
    dists = [victim] + list(others)
    x = ap._grid(dists, n)
    Lam = [r * d.resid(x) for r, d in zip(rates, dists)]
    f = victim.cdf(x) * np.exp(-Lam[0])
    m = len(others)
    t = np.linspace(0, 1, nt)
    w = np.full(nt, 1.0 / (nt - 1))
    w[0] = w[-1] = 0.5 / (nt - 1)
    phi = []
    for j in range(m):
        inner = np.zeros_like(x)
        for a in range(0, nt, chunk):
            tt = t[a:a + chunk]
            prod = np.ones((len(tt), len(x)))
            for k in range(m):
                if k != j:
                    prod *= (1 - tt[:, None] * (1 - np.exp(-Lam[1 + k]))[None, :])
            inner += (w[a:a + chunk, None] * prod).sum(0)
        phi.append(float(ap.trap(f * (1 - np.exp(-Lam[1 + j])) * inner, x)))
    return np.array(phi)


def task_h19(idx):
    name, victim, others, rates = H19[idx]
    rng = np.random.default_rng(26500 + idx)
    L = af.mc_poisson_vec(victim, others, rates, 100_000, rng)
    N, m = L.shape
    PH = af.shapley_airport_batch(L)
    phi_cf = shapley_poisson_chunked(victim, others, rates, 20001, 2001)
    phi_dbl = shapley_poisson_chunked(victim, others, rates, 40001, 4001)
    rows = []
    for r in range(1, m + 1):
        for T in itertools.combinations(range(m), r):
            xs = L[:, list(T)].max(1)
            cf = ap.poisson_game_value(victim, others, rates, list(T))
            cf2 = ap.poisson_game_value(victim, others, rates, list(T), n=40001)
            se = xs.std(ddof=1) / np.sqrt(N)
            rows.append(dict(param=name, kind="v", key="".join(map(str, T)), closed=cf, mc=float(xs.mean()), se=float(se),
                             z=float((xs.mean() - cf) / se) if se > 0 else 0.0, dbl_rel=abs(cf2 - cf) / max(abs(cf), 1e-300)))
    for j in range(m):
        se = PH[:, j].std(ddof=1) / np.sqrt(N)
        rows.append(dict(param=name, kind="phi", key=str(j), closed=float(phi_cf[j]), mc=float(PH[:, j].mean()), se=float(se),
                         z=float((PH[:, j].mean() - phi_cf[j]) / se) if se > 0 else 0.0,
                         dbl_rel=abs(phi_dbl[j] - phi_cf[j]) / max(abs(phi_cf[j]), 1e-300)))
    full = ap.poisson_game_value(victim, others, rates, list(range(m)))
    rows.append(dict(param=name, kind="efficiency", key="sum_phi_vs_v", closed=float(phi_cf.sum()), mc=full, se=0.0,
                     z=0.0, dbl_rel=abs(phi_cf.sum() - full) / max(abs(full), 1e-300)))
    return "h19", rows


# ------------------------------------------------------------------------------------------------ driver
def dump(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        keys = list(rows[0].keys())
        w.writerow(keys)
        for r in rows:
            w.writerow([r[k] for k in keys])


def main():
    for name in ("PREREGISTRATION_STUDY5", "STUDY5_EXPLORATORY_PLAN"):
        want = (HERE / f"{name}.sha256").read_text().split()[0]
        if hashlib.sha256((HERE / f"{name}.md").read_bytes()).hexdigest() != want:
            sys.exit(f"refusing to run: {name} changed after hashing")
    if (RES / "raw_s5_h19.csv").exists():
        sys.exit("refusing to run: Study 5 results exist (single-use)")
    t0 = time.time()
    jobs = []
    for cell in CELLS:
        jobs += [(task_h16_sim, (cell, s)) for s in H16_SEEDS]
    for g in ("G2", "G3"):
        jobs += [(task_gen, (g, s)) for s in GEN_SEEDS]
    for cell, (_, _, _, seeds) in H17_CELLS.items():
        jobs += [(task_h17, (cell, s)) for s in seeds]
    for cell in H18_CELLS:
        jobs += [(task_h18, (cell, s)) for s in H18_SEEDS]
    jobs += [(task_h19, (i,)) for i in range(len(H19))]
    for kind, seeds in X12_SEEDS.items():
        jobs += [(task_x12, (kind, s)) for s in seeds]
    for cell in X15_CELLS:
        jobs += [(task_x15, (cell, s)) for s in X15_SEEDS]
    h16, coal, blame, timing, h18, h19, x12, x15d, x15o, errors = [], [], [], [], [], [], [], [], [], []
    with ProcessPoolExecutor(12) as ex:
        futs = {ex.submit(fn, *a): (fn.__name__, a) for fn, a in jobs}
        for n, fu in enumerate(as_completed(futs), 1):
            name, a = futs[fu]
            try:
                kind, res = fu.result()
                if kind == "h16":
                    h16.append(res)
                elif kind == "h17":
                    coal += res[0]
                    blame += res[1]
                    timing.append(res[2])
                elif kind == "h18":
                    h18 += res
                elif kind == "x12":
                    x12 += res
                elif kind == "x15":
                    x15d += res[0]
                    x15o += res[1]
                else:
                    h19 += res
            except Exception:
                errors.append(dict(task=name, args=str(a), error=traceback.format_exc()[-400:]))
            if n % 200 == 0:
                print(f"{n}/{len(jobs)} done ({time.time() - t0:.0f}s, errors={len(errors)})", flush=True)
    RES.mkdir(exist_ok=True)
    srt = lambda rows, *k: sorted(rows, key=lambda r: tuple(r[x] for x in k))
    dump(RES / "raw_s5_h16.csv", srt(h16, "cell", "seed"))
    dump(RES / "raw_s5_h17_coal.csv", srt(coal, "cell", "seed", "mask", "victim"))
    dump(RES / "raw_s5_h17_blame.csv", srt(blame, "cell", "seed", "victim", "blocker"))
    dump(RES / "raw_s5_h17_time.csv", srt(timing, "cell", "seed"))
    dump(RES / "raw_s5_h18.csv", srt(h18, "cell", "seed", "eps"))
    dump(RES / "raw_s5_x12.csv", srt(x12, "cell", "seed", "eps"))
    dump(RES / "raw_s5_x15_delay.csv", srt(x15d, "cell", "seed", "flow"))
    dump(RES / "raw_s5_x15_obs.csv", srt(x15o, "cell", "seed", "victim", "blocker"))
    dump(RES / "raw_s5_h19.csv", srt(h19, "param", "kind", "key"))         # last = completion marker
    (RES / "run_manifest_study5.json").write_text(json.dumps(dict(
        n_errors=len(errors), errors=errors, seconds=round(time.time() - t0, 1), n_jobs=len(jobs), n_h16=len(h16),
        n_h17_coal=len(coal), n_h18=len(h18), n_h19=len(h19), n_x12=len(x12), n_x15_obs=len(x15o),
        prereg_sha256=hashlib.sha256((HERE / "PREREGISTRATION_STUDY5.md").read_bytes()).hexdigest(),
        exploratory_plan_sha256=hashlib.sha256((HERE / "STUDY5_EXPLORATORY_PLAN.md").read_bytes()).hexdigest()), indent=1))
    print(f"done {len(jobs)} jobs, {len(errors)} errors, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
