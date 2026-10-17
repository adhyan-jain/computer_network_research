"""study.py - harness for the measurement-validity study (see PREREGISTRATION.md).

Wraps the unmodified simulator in src/mlo_sim. Three RNG designs:
  shared : one random.Random(seed) for arrivals and channel (identical to MloSimulator)
  naive  : per-flow arrival streams, channel still from the shared stream
  keyed  : per-flow arrival streams; each channel draw keyed by (seed, flow, flow_idx, attempt, purpose)
Read-only instrumentation: late-discard capture, loss-draw counting, per-packet bookkeeping.
Nothing in src/ is modified.
"""
import hashlib
import heapq
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.mlo_sim.channel import WirelessChannel  # noqa: E402
from src.mlo_sim.core import BlockAckReceiver, Flow, Link, Packet  # noqa: E402
from src.mlo_sim.metrics import compute_metrics  # noqa: E402
from src.mlo_sim.schedulers import DefaultFifoScheduler, SASPScheduler  # noqa: E402
from src.mlo_sim.simulator import (EVENT_LINK_TX_COMPLETE, EVENT_PACKET_ARRIVAL,  # noqa: E402
                                   MloSimulator)

DURATION_MS = 300.0
PKT_FIELDS = ("packet_id", "flow_id", "size_bytes", "arr_time", "weight", "seq_num", "link_id",
              "disp_time", "attempts", "arr_rx_time", "rel_time", "self_blocking",
              "cross_blocking", "total_reorder_delay", "end_to_end_delay")


def pkt_tuple(p):
    return tuple(getattr(p, k) for k in PKT_FIELDS)


class ObservedReceiver(BlockAckReceiver):
    """Counts packets silently discarded because sn < win_start. Behaviour is otherwise unchanged."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.late_discards = []

    def receive_packet(self, packet, rx_time):
        if packet.seq_num is not None and packet.seq_num < self.win_start:
            self.late_discards.append(packet)
        return super().receive_packet(packet, rx_time)


class StudySimulator(MloSimulator):
    def __init__(self, flows, links, channels, scheduler, win_size=64, seed=42, design="shared",
                 single_draw=False, arrival_horizon_ms=None, stop_ms=None, drain=False):
        assert design in ("shared", "naive", "keyed")
        super().__init__(flows, links, channels, scheduler, win_size=win_size, seed=seed)
        self.receiver = ObservedReceiver(win_size=win_size)
        self.design = design
        self.single_draw = single_draw
        self.arrival_horizon_ms = arrival_horizon_ms
        self.stop_ms = stop_ms
        self.drain = drain
        if drain:
            assert arrival_horizon_ms is not None, "drain needs a finite arrival horizon"
        self.flow_rngs = {f.flow_id: random.Random(f"{seed}|arr|{f.flow_id}") for f in flows}
        self.flow_counter = {f.flow_id: 0 for f in flows}
        self.all_packets = []
        self.n_loss_draws = 0
        self.attempt_draw_counts = []          # draws consumed by each COMPLETED attempt
        self.loss_outcomes = {l.link_id: [] for l in links}   # the draws that actually decide loss
        for ch in self.channels.values():
            orig = ch.sample_frame_loss

            def wrapped(rng, _o=orig, _s=self):
                _s.n_loss_draws += 1
                return _o(rng)
            ch.sample_frame_loss = wrapped

    # ---- randomness plumbing -------------------------------------------------------------
    def _schedule_next_packet_arrival(self, flow):
        rate_per_ms = flow.rate_pkts_per_sec / 1000.0
        r = self.rng if self.design == "shared" else self.flow_rngs[flow.flow_id]
        t = self.current_time_ms + r.expovariate(rate_per_ms)
        if self.arrival_horizon_ms is None or t <= self.arrival_horizon_ms:
            self.schedule_event(t, EVENT_PACKET_ARRIVAL, flow.flow_id)

    def _rng_for(self, pkt, attempt, purpose):
        if self.design != "keyed":
            return self.rng
        return random.Random(f"{self.seed}|{pkt.flow_id}|{pkt.flow_idx}|{attempt}|{purpose}")

    def _attempt_delay(self, link_id, pkt, attempt):
        ch = self.channels[link_id]
        rng = self._rng_for(pkt, attempt, "tx")
        before = self.n_loss_draws
        if self.single_draw:
            d = ch.sample_backoff_duration_ms(attempt, rng) + ch.compute_phy_duration_ms(pkt.size_bytes)
        else:
            d, _ = ch.simulate_transmission_attempt(pkt.size_bytes, attempt, rng)
        pkt.dispatch_draws = self.n_loss_draws - before
        return d

    # ---- event loop (mirrors MloSimulator.run; equivalence is tested in test_study.py) ------
    def run(self, duration_ms=DURATION_MS):
        for flow in self.flows.values():
            self._schedule_next_packet_arrival(flow)
        stop = self.stop_ms if self.stop_ms is not None else duration_ms
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            self.current_time_ms = event.time
            if not self.drain and self.current_time_ms > stop:
                break
            if event.event_type == EVENT_PACKET_ARRIVAL:
                flow = self.flows[event.data]
                self.packet_counter += 1
                pkt = Packet(packet_id=self.packet_counter, flow_id=event.data,
                             size_bytes=flow.packet_size_bytes, arr_time=self.current_time_ms,
                             weight=flow.weight)
                pkt.flow_idx = self.flow_counter[event.data]
                self.flow_counter[event.data] += 1
                self.all_packets.append(pkt)
                self.queues[event.data].append(pkt)
                flow.packets_generated += 1
                self.total_generated_packets += 1
                self._schedule_next_packet_arrival(flow)
                self._trigger_scheduler()
            elif event.event_type == EVENT_LINK_TX_COMPLETE:
                link_id, packet = event.data
                link = self.links[link_id]
                channel = self.channels[link_id]
                packet.attempts += 1
                lost = channel.sample_frame_loss(self._rng_for(packet, packet.attempts, "loss"))
                self.attempt_draw_counts.append(packet.dispatch_draws + 1)
                self.loss_outcomes[link_id].append(bool(lost))
                if not lost:
                    link.total_transmitted_pkts += 1
                    link.busy_until = self.current_time_ms
                    link.current_packet = None
                    if packet in self.inflight_packets:
                        self.inflight_packets.remove(packet)
                    self.scheduler.on_packet_completed(packet, True, self.current_time_ms - packet.disp_time, link)
                    self.receiver.receive_packet(packet, self.current_time_ms)
                    self._trigger_scheduler()
                else:
                    link.total_retries += 1
                    if packet.attempts < link.max_retries:
                        d = self._attempt_delay(link_id, packet, packet.attempts + 1)
                        link.busy_until = self.current_time_ms + d
                        self.schedule_event(self.current_time_ms + d, EVENT_LINK_TX_COMPLETE, (link_id, packet))
                    else:
                        link.total_dropped_pkts += 1
                        link.busy_until = self.current_time_ms
                        link.current_packet = None
                        if packet in self.inflight_packets:
                            self.inflight_packets.remove(packet)
                        self._trigger_scheduler()
        return self.receiver

    def _trigger_scheduler(self):
        available = [l for l in self.links.values()
                     if l.current_packet is None and self.current_time_ms >= l.busy_until]
        while available:
            decision = self.scheduler.schedule(
                current_time=self.current_time_ms, available_links=available, queues=self.queues,
                flows=self.flows, inflight_packets=self.inflight_packets, win_size=self.win_size,
                win_start=self.receiver.win_start)
            if decision is None:
                break
            packet, link, sn = decision
            packet.seq_num = sn
            packet.link_id = link.link_id
            packet.disp_time = self.current_time_ms
            link.current_packet = packet
            self.inflight_packets.append(packet)
            available.remove(link)
            d = self._attempt_delay(link.link_id, packet, 1)
            link.busy_until = self.current_time_ms + d
            self.schedule_event(self.current_time_ms + d, EVENT_LINK_TX_COMPLETE, (link.link_id, packet))


# ---- scenarios -------------------------------------------------------------------------------
SCALES = {
    "S2": [(1.0, 400.0), (50.0, 400.0)],
    "S4": [(1.0, 200.0), (1.0, 200.0), (50.0, 200.0), (50.0, 200.0)],
    "S8": [(1.0, 100.0)] * 4 + [(50.0, 100.0)] * 4,
}


def build(scale, fer=0.01, burst_prob=0.0, burst_recovery=0.5, drop_flow_ids=()):
    flows = [Flow(flow_id=i + 1, name=f"F{i + 1}", weight=w, rate_pkts_per_sec=r)
             for i, (w, r) in enumerate(SCALES[scale]) if (i + 1) not in drop_flow_ids]
    links = [Link(link_id=0, name="L0", bandwidth_mbps=20.0, base_delay_ms=1.0),
             Link(link_id=1, name="L1", bandwidth_mbps=20.0, base_delay_ms=1.1)]
    for l in links:
        l.contention_sigma_ms = 0.1
    chans = [WirelessChannel(bandwidth_mbps=20.0, base_propagation_ms=b, fer=fer,
                             burst_prob=burst_prob, burst_recovery=burst_recovery)
             for b in (1.0, 1.1)]
    return flows, links, chans


def arrival_trace(seed, flows, horizon):
    """Pure function of (seed, flow ids, rates): the keyed/naive arrival process."""
    out = []
    for f in flows:
        r = random.Random(f"{seed}|arr|{f.flow_id}")
        t = 0.0
        while True:
            t += r.expovariate(f.rate_pkts_per_sec / 1000.0)
            if t > horizon:
                break
            out.append(t)
    return sorted(out)


class _LeakyBase(DefaultFifoScheduler):
    """FIFO sequencing with a deliberate lookahead leak. Positive controls for H6 only."""

    def __init__(self, trace):
        super().__init__()
        self.trace = trace
        self.n_dispatched = 0

    @staticmethod
    def _fifo_pick(queues):
        best, earliest = None, float("inf")
        for f_id, q in queues.items():
            if q and q[0].arr_time < earliest:
                earliest, best = q[0].arr_time, f_id
        return best


class LeakyGlobal(_LeakyBase):
    """Fastest link for the first half of the packets in the whole input trace, slowest afterwards."""

    def schedule(self, current_time, available_links, queues, flows, inflight_packets, win_size, win_start):
        if not available_links or self.next_seq_num >= win_start + win_size:
            return None
        f = self._fifo_pick(queues)
        if f is None:
            return None
        key = (lambda l: l.estimated_mean_ms)
        link = min(available_links, key=key) if self.n_dispatched < len(self.trace) / 2 \
            else max(available_links, key=key)
        self.n_dispatched += 1
        return queues[f].popleft(), link, self._allocate_fifo_sn(f)


class LeakyLocal(_LeakyBase):
    """Holds the idle link if any arrival exists in the next 1.0 ms of the full input trace."""

    def schedule(self, current_time, available_links, queues, flows, inflight_packets, win_size, win_start):
        if not available_links or self.next_seq_num >= win_start + win_size:
            return None
        if any(current_time < t <= current_time + 1.0 for t in self.trace):
            return None
        f = self._fifo_pick(queues)
        if f is None:
            return None
        link = min(available_links, key=lambda l: l.estimated_mean_ms)
        return queues[f].popleft(), link, self._allocate_fifo_sn(f)


ARMS = ("FIFO", "FullSASP", "MeanOnly")


def make_sched(arm, trace=None):
    if arm == "FIFO":
        return DefaultFifoScheduler()
    if arm == "FullSASP":
        return SASPScheduler(enable_predictive_sequencing=True, use_variance=True)
    if arm == "MeanOnly":
        return SASPScheduler(enable_predictive_sequencing=True, use_variance=False)
    if arm == "LeakyGlobal":
        return LeakyGlobal(trace)
    if arm == "LeakyLocal":
        return LeakyLocal(trace)
    raise ValueError(arm)


def simulate(scale, design, arm, seed, duration=DURATION_MS, fer=0.01, burst_prob=0.0, burst_recovery=0.5,
             single_draw=False, arrival_horizon=None, stop=None, drain=False, drop_flow_ids=(), trace_horizon=None):
    flows, links, chans = build(scale, fer, burst_prob, burst_recovery, drop_flow_ids)
    trace = None
    if arm.startswith("Leaky"):
        trace = arrival_trace(seed, flows, trace_horizon if trace_horizon is not None else duration)
    sim = StudySimulator(flows, links, chans, make_sched(arm, trace), seed=seed, design=design,
                         single_draw=single_draw, arrival_horizon_ms=arrival_horizon, stop_ms=stop, drain=drain)
    t0 = time.perf_counter_ns()
    rx = sim.run(duration_ms=duration)
    wall_ms = (time.perf_counter_ns() - t0) / 1e6
    return sim, rx, wall_ms


def hash_arrivals(gen, duration):
    h = hashlib.sha256()
    for p in sorted(gen, key=lambda p: (p.flow_id, p.arr_time)):
        if p.arr_time <= duration:
            h.update(f"{p.flow_id}:{p.arr_time!r};".encode())
    return h.hexdigest()[:16]


def summarize(sim, rx, duration, wall_ms):
    """Per-run scalar row. Censored delay of an undelivered packet = duration - arr_time (lower bound)."""
    m = compute_metrics(rx, duration_ms=duration, scheduler_name="x")
    delivered = {p.packet_id for p in rx.delivered_packets}
    gen = sim.all_packets
    und = [p for p in gen if p.packet_id not in delivered]
    del_e2e = [p.end_to_end_delay for p in rx.delivered_packets]
    cens = del_e2e + [max(0.0, duration - p.arr_time) for p in und]
    late = {p.packet_id for p in rx.late_discards}
    f1 = [p for p in rx.delivered_packets if p.flow_id == 1]
    return dict(
        M=m.weighted_cross_blocking, mean_cross=m.mean_cross_blocking_ms, mean_self=m.mean_self_blocking_ms,
        generated=len(gen), delivered=len(delivered), undelivered=len(und), late_discards=len(late),
        dropped_retry=sum(l.total_dropped_pkts for l in sim.links.values()),
        forced_adv=rx.window_advances_forced,
        e2e_delivered=(sum(del_e2e) / len(del_e2e)) if del_e2e else float("nan"),
        e2e_censored=(sum(cens) / len(cens)) if cens else float("nan"),
        self1=(sum(p.self_blocking for p in f1) / len(f1)) if f1 else float("nan"), n1=len(f1),
        arr_sig=hash_arrivals(gen, duration), wall_ms=wall_ms)
