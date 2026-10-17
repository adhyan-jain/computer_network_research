"""Harness validity tests. Smoke seeds 1-5 only: confirmatory seeds 7000-7099 are never used here."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import study as st  # noqa: E402
from src.mlo_sim.simulator import MloSimulator  # noqa: E402

SMOKE = [1, 2, 3, 4, 5]


def _orig(scale, arm, seed, **kw):
    flows, links, chans = st.build(scale, **kw)
    sim = MloSimulator(flows, links, chans, st.make_sched(arm), seed=seed)
    rx = sim.run(duration_ms=st.DURATION_MS)
    return sim, rx


@pytest.mark.parametrize("scale", ["S2", "S4", "S8"])
@pytest.mark.parametrize("arm", st.ARMS)
@pytest.mark.parametrize("seed", SMOKE)
def test_shared_mode_reproduces_shipped_simulator(scale, arm, seed):
    """Equivalence oracle: the harness in 'shared' mode == unmodified MloSimulator, field for field."""
    o_sim, o_rx = _orig(scale, arm, seed)
    sim, rx, _ = st.simulate(scale, "shared", arm, seed)
    assert [st.pkt_tuple(p) for p in rx.delivered_packets] == [st.pkt_tuple(p) for p in o_rx.delivered_packets]
    assert sim.total_generated_packets == o_sim.total_generated_packets
    assert rx.window_advances_forced == o_rx.window_advances_forced
    assert [(l.total_retries, l.total_dropped_pkts) for l in sim.links.values()] == \
           [(l.total_retries, l.total_dropped_pkts) for l in o_sim.links.values()]


@pytest.mark.parametrize("design", ["naive", "keyed"])
@pytest.mark.parametrize("seed", SMOKE)
def test_arrivals_identical_across_arms(design, seed):
    """O1 validity check: guaranteed zero mismatch for naive and keyed designs."""
    sigs = set()
    for arm in st.ARMS:
        sim, rx, w = st.simulate("S4", design, arm, seed)
        sigs.add(st.summarize(sim, rx, st.DURATION_MS, w)["arr_sig"])
    assert len(sigs) == 1


def test_o1_oracle_has_power_via_positive_control():
    """O1 must be able to see a mismatch. Positive control: two shared-RNG runs whose channel draw counts
    differ (fer 0.01 vs 0.30 -> different retry counts) must yield different arrival signatures."""
    diverged = 0
    for seed in SMOKE:
        sigs = set()
        for fer in (0.01, 0.30):
            sim, rx, w = st.simulate("S2", "shared", "FIFO", seed, fer=fer)
            sigs.add(st.summarize(sim, rx, st.DURATION_MS, w)["arr_sig"])
        diverged += len(sigs) > 1
    assert diverged == len(SMOKE)


def test_keyed_is_deterministic():
    a = st.simulate("S2", "keyed", "FullSASP", 3)[1].delivered_packets
    b = st.simulate("S2", "keyed", "FullSASP", 3)[1].delivered_packets
    assert [st.pkt_tuple(p) for p in a] == [st.pkt_tuple(p) for p in b]


@pytest.mark.parametrize("arm", st.ARMS)
@pytest.mark.parametrize("seed", SMOKE)
def test_drain_with_zero_loss_delivers_everything(arm, seed):
    """H2 validity check: with fer=0 the drained undelivered count is exactly 0."""
    sim, rx, w = st.simulate("S2", "keyed", arm, seed, fer=0.0, arrival_horizon=st.DURATION_MS, drain=True)
    s = st.summarize(sim, rx, st.DURATION_MS, w)
    assert s["undelivered"] == 0 and s["late_discards"] == 0


@pytest.mark.parametrize("seed", SMOKE)
def test_trace_control_for_self_blocking(seed):
    """H4 validity check: S_1 recomputed from receiver history without flow-2 records is unchanged."""
    sim, rx, _ = st.simulate("S2", "keyed", "FIFO", seed)
    f1 = [p for p in rx.delivered_packets if p.flow_id == 1]
    hist = {p.seq_num: p for p in rx.history.values() if p.flow_id == 1 and p.arr_rx_time is not None}
    for p in f1:
        preds = [q.arr_rx_time for s, q in hist.items() if s < p.seq_num]
        r_intra = max([p.arr_rx_time] + preds)
        assert abs(max(0.0, r_intra - p.arr_rx_time) - p.self_blocking) <= 1e-9


def test_single_vs_double_draw_counts():
    sim, _, _ = st.simulate("S2", "shared", "FIFO", 1)
    assert set(sim.attempt_draw_counts) == {2}
    sim1, _, _ = st.simulate("S2", "shared", "FIFO", 1, single_draw=True)
    assert set(sim1.attempt_draw_counts) == {1}


@pytest.mark.parametrize("arm", ["FIFO", "FullSASP", "MeanOnly"])
@pytest.mark.parametrize("seed", SMOKE[:3])
def test_truncated_input_prefix_identical_for_causal_arms(arm, seed):
    T = 150.0
    _, a, _ = st.simulate("S2", "keyed", arm, seed, duration=T, arrival_horizon=T, stop=T)
    _, b, _ = st.simulate("S2", "keyed", arm, seed, duration=st.DURATION_MS, arrival_horizon=st.DURATION_MS, stop=T)
    pa = [st.pkt_tuple(p) for p in a.delivered_packets if p.rel_time <= T]
    pb = [st.pkt_tuple(p) for p in b.delivered_packets if p.rel_time <= T]
    assert pa == pb and len(pa) > 20


def test_leaky_global_is_detected_by_truncation_test():
    T = 150.0
    hits = 0
    for seed in SMOKE:
        _, a, _ = st.simulate("S2", "keyed", "LeakyGlobal", seed, duration=T, arrival_horizon=T, stop=T, trace_horizon=T)
        _, b, _ = st.simulate("S2", "keyed", "LeakyGlobal", seed, duration=st.DURATION_MS,
                              arrival_horizon=st.DURATION_MS, stop=T, trace_horizon=st.DURATION_MS)
        pa = [st.pkt_tuple(p) for p in a.delivered_packets if p.rel_time <= T]
        pb = [st.pkt_tuple(p) for p in b.delivered_packets if p.rel_time <= T]
        hits += pa != pb
    assert hits == len(SMOKE)
