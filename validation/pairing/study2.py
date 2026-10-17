"""study2.py - coalition replay, trace-level blame observer and exact Shapley (see PREREGISTRATION_STUDY2.md).

Rows written by run_study2.py:
  raw_s2_delay.csv : scenario,arm,seed,mask,flow,n_pkts,D,sig         (D = right-censored mean e2e of `flow` in coalition `mask`)
  raw_s2_blame.csv : scenario,arm,seed,blocker,victim,blame_sum,n_delivered_victim,forced_cross_victim,meanX_victim
"""
import itertools
import math
from collections import defaultdict

import study as st
from study import StudySimulator, ObservedReceiver, build, make_sched, DURATION_MS

SCENARIOS = {  # name: (scale, rate_scale, delta_mu)
    "S2": ("S2", 1.0, 0.1),
    "S4": ("S4", 1.0, 0.1),
    "S8": ("S8", 1.0, 0.1),
    "LowLoad": ("S4", 0.25, 2.0),
}


class BlameReceiver(ObservedReceiver):
    """Attributes each blocked packet's cross-blocking to the flow of the packet whose arrival released it."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.blame = defaultdict(float)         # (blocker_flow, victim_flow) -> summed ms
        self.forced_cross = defaultdict(float)  # victim_flow -> ms released by forced window advance

    def receive_packet(self, packet, rx_time):
        before = self.window_advances_forced
        released = super().receive_packet(packet, rx_time)
        forced = self.window_advances_forced != before
        for p in released:
            if p is packet or p.cross_blocking <= 0:
                continue
            if forced:
                self.forced_cross[p.flow_id] += p.cross_blocking
            else:
                self.blame[(packet.flow_id, p.flow_id)] += p.cross_blocking
        return released


def run_coalition(scenario, keep, arm, seed, blame=False):
    scale, rate_scale, dm = SCENARIOS[scenario]
    flows, links, chans = build(scale, fer=0.01, delta_mu=dm)
    flows = [f for f in flows if f.flow_id in keep]
    for f in flows:
        f.rate_pkts_per_sec *= rate_scale
    sim = StudySimulator(flows, links, chans, make_sched(arm), seed=seed, design="keyed")
    if blame:
        sim.receiver = BlameReceiver(win_size=sim.win_size)
    rx = sim.run(duration_ms=DURATION_MS)
    delivered = {p.packet_id for p in rx.delivered_packets}
    out = {}
    for f in flows:
        mine = [p for p in sim.all_packets if p.flow_id == f.flow_id]
        d = [p.end_to_end_delay for p in mine if p.packet_id in delivered]
        d += [max(0.0, DURATION_MS - p.arr_time) for p in mine if p.packet_id not in delivered]
        sig = st.hash_arrivals(mine, DURATION_MS)
        out[f.flow_id] = dict(n=len(mine), D=(sum(d) / len(d)) if d else float("nan"), sig=sig)
    return sim, rx, out


def masks(flow_ids):
    ids = sorted(flow_ids)
    for r in range(1, len(ids) + 1):
        for comb in itertools.combinations(ids, r):
            yield sum(1 << (i - 1) for i in comb), frozenset(comb)


def shapley_for_victim(D, victim, flow_ids):
    """D: dict frozenset(coalition)->D_victim (victim in coalition). Returns ({blocker: phi}, E_victim)."""
    others = [f for f in flow_ids if f != victim]
    m = len(others)
    base = D[frozenset([victim])]
    phi = {}
    for j in others:
        rest = [o for o in others if o != j]
        total = 0.0
        for r in range(len(rest) + 1):
            w = math.factorial(r) * math.factorial(m - r - 1) / math.factorial(m)
            for T in itertools.combinations(rest, r):
                s = frozenset(T) | {victim}
                total += w * (D[s | {j}] - D[s])
        phi[j] = total
    return phi, D[frozenset(flow_ids)] - base
