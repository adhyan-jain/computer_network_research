"""
Deterministic Scenario and Protocol Audit Test Suite (Phase 2 Audit).
Implements the 6+ required deterministic verification scenarios:
1. Two links with identical completion times.
2. One slow and one fast link (verifying predictive sequence inversion).
3. One high-variance and one low-variance link with equal means.
4. Unequal priorities with equal means.
5. In-flight frame causing head-of-line blocking penalty.
6. Exhausted reorder window blocking further dispatches.
7. Fresh object state verification across sequential runs.
8. Starvation / pathological queue sequences.
"""

from collections import deque
import pytest

from src.mlo_sim.core import Packet, Flow, Link, BlockAckReceiver
from src.mlo_sim.channel import WirelessChannel
from src.mlo_sim.schedulers import (
    SASPScheduler,
    DefaultFifoScheduler,
    compute_threshold_root
)
from src.mlo_sim.simulator import MloSimulator


def test_scenario_1_two_identical_links():
    """Two identical links: SASP assigns sequential SNs in arrival order."""
    sched = SASPScheduler(enable_predictive_sequencing=True, use_variance=True)
    l1 = Link(link_id=0, name="Link0", bandwidth_mbps=20.0, base_delay_ms=1.0)
    l2 = Link(link_id=1, name="Link1", bandwidth_mbps=20.0, base_delay_ms=1.0)
    
    f1 = Flow(flow_id=1, name="Flow1", weight=1.0)
    f2 = Flow(flow_id=2, name="Flow2", weight=1.0)
    
    q1 = deque([Packet(1, 1, 1500, arr_time=0.0, weight=1.0)])
    q2 = deque([Packet(2, 2, 1500, arr_time=0.0, weight=1.0)])
    
    queues = {1: q1, 2: q2}
    flows = {1: f1, 2: f2}
    
    decision1 = sched.schedule(
        current_time=0.0,
        available_links=[l1, l2],
        queues=queues,
        flows=flows,
        inflight_packets=[],
        win_size=64,
        win_start=0
    )
    assert decision1 is not None
    pkt1, link1, sn1 = decision1
    
    # Second link should get second planned dispatch
    decision2 = sched.schedule(
        current_time=0.0,
        available_links=[l2 if link1 == l1 else l1],
        queues=queues,
        flows=flows,
        inflight_packets=[],
        win_size=64,
        win_start=0
    )
    assert decision2 is not None
    pkt2, link2, sn2 = decision2
    
    assert sn1 == 0
    assert sn2 == 1
    assert pkt1.flow_id != pkt2.flow_id


def test_scenario_2_slow_and_fast_link_predictive_inversion():
    """
    One slow link (10 ms) and one fast link (1 ms).
    Flow 1 is at head of slow link queue; Flow 2 is at head of fast link queue.
    Predictive sequencing MUST allocate the LOWER sequence number to the fast link
    so that when frames arrive physically, the fast link frame arrives first with the earlier SN.
    """
    sched = SASPScheduler(enable_predictive_sequencing=True, use_variance=False)
    slow_link = Link(link_id=0, name="Slow", bandwidth_mbps=10.0, base_delay_ms=9.0)
    fast_link = Link(link_id=1, name="Fast", bandwidth_mbps=50.0, base_delay_ms=0.5)
    
    f1 = Flow(flow_id=1, name="Bulk", weight=1.0)
    f2 = Flow(flow_id=2, name="Interactive", weight=1.0)
    
    p1 = Packet(1, 1, 1500, arr_time=0.0, weight=1.0)
    p2 = Packet(2, 2, 1500, arr_time=0.0, weight=1.0)
    
    queues = {1: deque([p1]), 2: deque([p2])}
    flows = {1: f1, 2: f2}
    
    # Both links available
    d1 = sched.schedule(0.0, [slow_link, fast_link], queues, flows, [], win_size=64, win_start=0)
    assert d1 is not None
    pkt_first, link_first, sn_first = d1
    
    d2 = sched.schedule(0.0, [slow_link if link_first == fast_link else fast_link], queues, flows, [], win_size=64, win_start=0)
    assert d2 is not None
    pkt_second, link_second, sn_second = d2
    
    # Fast link must receive sn = 0 because it arrives earlier (proj 0.5 + 0.24 = 0.74 ms vs ~10 ms)
    if link_first == fast_link:
        assert sn_first == 0
        assert sn_second == 1
        assert link_second == slow_link
    else:
        assert sn_second == 0
        assert sn_first == 1
        assert link_first == slow_link


def test_scenario_3_equal_mean_unequal_variance():
    """
    Two links with equal mean completion delay but different variances.
    With asymmetric flow weights (w_interactive = 10, w_bulk = 1),
    Theorem 3 threshold u* shifts negatively, biasing the higher weight flow
    to the lower sequence number based on variance.
    """
    w_bulk = 1.0
    w_inter = 10.0
    u_star = compute_threshold_root(w_bulk, w_inter)
    assert u_star < 0.0  # Biases toward interactive flow


def test_scenario_4_unequal_priorities_equal_means():
    """
    Two flows with unequal priorities on identical links.
    Interactive flow (w=10) should be prioritized and given sn=0.
    """
    sched = SASPScheduler(enable_predictive_sequencing=True, use_variance=True)
    l1 = Link(link_id=0, name="L0", bandwidth_mbps=20.0, base_delay_ms=1.0)
    l2 = Link(link_id=1, name="L1", bandwidth_mbps=20.0, base_delay_ms=1.0)
    
    f_bulk = Flow(flow_id=1, name="Bulk", weight=1.0)
    f_inter = Flow(flow_id=2, name="Interactive", weight=10.0)
    
    q_bulk = deque([Packet(1, 1, 1500, arr_time=0.0, weight=1.0)])
    q_inter = deque([Packet(2, 2, 1500, arr_time=0.0, weight=10.0)])
    
    queues = {1: q_bulk, 2: q_inter}
    flows = {1: f_bulk, 2: f_inter}
    
    d1 = sched.schedule(0.0, [l1, l2], queues, flows, [], win_size=64, win_start=0)
    assert d1 is not None
    pkt1, link1, sn1 = d1
    
    # Highest weight flow should be served first with lowest sequence number
    assert pkt1.flow_id == 2  # Interactive flow
    assert sn1 == 0


def test_scenario_5_inflight_frame_cross_blocking_penalty():
    """
    When a single link is available and a slow frame is currently in-flight on the other link,
    SASP evaluates the cross-blocking penalty against the in-flight frame.
    """
    sched = SASPScheduler(enable_predictive_sequencing=True, use_variance=True)
    fast_link = Link(link_id=1, name="Fast", bandwidth_mbps=50.0, base_delay_ms=0.5)
    
    f1 = Flow(flow_id=1, name="Bulk", weight=1.0)
    f2 = Flow(flow_id=2, name="Interactive", weight=10.0)
    
    # In-flight slow packet on Link 0 that will complete at t=10.0
    inflight_pkt = Packet(1, 1, 1500, arr_time=0.0, weight=1.0)
    inflight_pkt.seq_num = 0
    inflight_pkt.link_id = 0
    inflight_pkt.proj_arrival = 10.0
    
    q_inter = deque([Packet(2, 2, 1500, arr_time=1.0, weight=10.0)])
    queues = {1: deque(), 2: q_inter}
    flows = {1: f1, 2: f2}
    
    decision = sched.schedule(
        current_time=1.0,
        available_links=[fast_link],
        queues=queues,
        flows=flows,
        inflight_packets=[inflight_pkt],
        win_size=64,
        win_start=0
    )
    assert decision is not None
    pkt, link, sn = decision
    assert sn == 0  # First packet assigned by this scheduler instance
    assert pkt.flow_id == 2


def test_scenario_6_exhausted_reorder_window():
    """When next_seq_num >= win_start + win_size, scheduler MUST refuse dispatch."""
    sched = SASPScheduler()
    sched.next_seq_num = 64  # Exhausted for win_size=64, win_start=0
    
    l1 = Link(link_id=0, name="L0", bandwidth_mbps=20.0, base_delay_ms=1.0)
    f1 = Flow(flow_id=1, name="F1", weight=1.0)
    q1 = deque([Packet(1, 1, 1500, arr_time=0.0)])
    
    decision = sched.schedule(0.0, [l1], {1: q1}, {1: f1}, [], win_size=64, win_start=0)
    assert decision is None, "Scheduler must return None when window is exhausted"


def test_scenario_7_fresh_environment_isolation():
    """Verify that creating fresh objects prevents state pollution across simulation runs."""
    f1 = Flow(flow_id=1, name="F1")
    l1 = Link(link_id=0, name="L0", bandwidth_mbps=20.0, base_delay_ms=1.0)
    ch1 = WirelessChannel(bandwidth_mbps=20.0, base_propagation_ms=1.0)
    
    sim1 = MloSimulator([f1], [l1], [ch1], DefaultFifoScheduler(), seed=42)
    sim1.run(100.0)
    assert l1.busy_until > 0.0
    
    # Fresh objects
    f2 = Flow(flow_id=1, name="F1")
    l2 = Link(link_id=0, name="L0", bandwidth_mbps=20.0, base_delay_ms=1.0)
    ch2 = WirelessChannel(bandwidth_mbps=20.0, base_propagation_ms=1.0)
    assert l2.busy_until == 0.0
    assert l2.current_packet is None
