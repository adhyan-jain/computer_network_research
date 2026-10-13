"""
Regression tests for true predictive sequence-number allocation in Wi-Fi 7 MLO.
Verifies that SASP genuinely inverts sequence numbers for concurrent fast/slow dispatches,
preventing the silent FIFO fallback that compromised legacy v1.
"""

from collections import deque
import pytest
from src.mlo_sim.core import Packet, Flow, Link, BlockAckReceiver
from src.mlo_sim.schedulers import SASPScheduler, DefaultFifoScheduler


def test_predictive_sequence_inversion():
    """
    Regression test: When a slow link (3.0 ms) and a fast link (0.5 ms) are both available,
    SASP must allocate the lower sequence number to the fast link's packet,
    ensuring that physical completion occurs in strictly increasing sequence order.
    """
    sasp = SASPScheduler(enable_predictive_sequencing=True)

    links = [
        Link(link_id=0, name="SlowLink", bandwidth_mbps=20.0, base_delay_ms=3.0),
        Link(link_id=1, name="FastLink", bandwidth_mbps=100.0, base_delay_ms=0.5)
    ]
    flows = {
        1: Flow(flow_id=1, name="Bulk", weight=1.0),
        2: Flow(flow_id=2, name="Interactive", weight=10.0)
    }
    p_bulk = Packet(packet_id=1, flow_id=1, size_bytes=1500, arr_time=0.0, weight=1.0)
    p_inter = Packet(packet_id=2, flow_id=2, size_bytes=1500, arr_time=0.0, weight=10.0)

    queues = {
        1: deque([p_bulk]),
        2: deque([p_inter])
    }

    # First dispatch from batch
    d1 = sasp.schedule(0.0, links.copy(), queues, flows, [], 64, 0)
    assert d1 is not None, "First dispatch must succeed"
    pkt1, link1, sn1 = d1

    # Second dispatch from batch
    remaining_links = [l for l in links if l.link_id != link1.link_id]
    d2 = sasp.schedule(0.0, remaining_links, queues, flows, [pkt1], 64, 0)
    assert d2 is not None, "Second dispatch must succeed"
    pkt2, link2, sn2 = d2

    # Verify that the fast link got the LOWER sequence number!
    if link1.link_id == 1:  # FastLink
        assert sn1 < sn2, f"FastLink packet must get lower SN: sn_fast={sn1}, sn_slow={sn2}"
        assert pkt1.flow_id == 2, "FastLink should carry high-priority interactive packet"
    else:
        assert sn2 < sn1, f"FastLink packet must get lower SN: sn_fast={sn2}, sn_slow={sn1}"
        assert pkt2.flow_id == 2, "FastLink should carry high-priority interactive packet"


def test_predictive_sequencing_eliminates_rx_stall():
    """
    End-to-end receiver test: Feeds the dispatches from SASP into BlockAckReceiver
    and verifies that the interactive frame suffers ZERO cross-flow blocking.
    """
    sasp = SASPScheduler(enable_predictive_sequencing=True)
    rx = BlockAckReceiver(win_size=64)

    links = [
        Link(link_id=0, name="SlowLink", bandwidth_mbps=20.0, base_delay_ms=3.0),
        Link(link_id=1, name="FastLink", bandwidth_mbps=100.0, base_delay_ms=0.5)
    ]
    flows = {
        1: Flow(flow_id=1, name="Bulk", weight=1.0),
        2: Flow(flow_id=2, name="Interactive", weight=10.0)
    }
    p_bulk = Packet(packet_id=1, flow_id=1, size_bytes=1500, arr_time=0.0, weight=1.0)
    p_inter = Packet(packet_id=2, flow_id=2, size_bytes=1500, arr_time=0.0, weight=10.0)
    queues = {1: deque([p_bulk]), 2: deque([p_inter])}

    pkt1, link1, sn1 = sasp.schedule(0.0, links.copy(), queues, flows, [], 64, 0)
    pkt1.seq_num = sn1
    rem_links = [l for l in links if l.link_id != link1.link_id]
    pkt2, link2, sn2 = sasp.schedule(0.0, rem_links, queues, flows, [pkt1], 64, 0)
    pkt2.seq_num = sn2

    # Physical arrivals: Fast link arrives at 0.5 ms, Slow link arrives at 3.0 ms
    fast_pkt = pkt1 if link1.link_id == 1 else pkt2
    slow_pkt = pkt2 if link1.link_id == 1 else pkt1

    rel_fast = rx.receive_packet(fast_pkt, rx_time=0.5)
    assert len(rel_fast) == 1, "Fast packet must be released immediately upon physical arrival!"
    assert fast_pkt.cross_blocking == 0.0, f"Fast packet must have 0 cross-blocking, got {fast_pkt.cross_blocking}"

    rel_slow = rx.receive_packet(slow_pkt, rx_time=3.0)
    assert len(rel_slow) == 1, "Slow packet must be released immediately upon physical arrival!"
    assert slow_pkt.cross_blocking == 0.0, f"Slow packet must have 0 cross-blocking, got {slow_pkt.cross_blocking}"


def test_intra_flow_monotonicity_preserved():
    """
    Verifies that for multiple packets of the same flow, sequence numbers
    are strictly increasing, preserving TCP and stream ordering.
    """
    sasp = SASPScheduler(enable_predictive_sequencing=True)
    links = [Link(link_id=1, name="FastLink", bandwidth_mbps=100.0, base_delay_ms=0.5)]
    flows = {2: Flow(flow_id=2, name="Interactive", weight=10.0)}
    pkts = [
        Packet(packet_id=i, flow_id=2, size_bytes=1500, arr_time=float(i), weight=10.0)
        for i in range(5)
    ]
    queues = {2: deque(pkts)}

    sns = []
    for _ in range(5):
        d = sasp.schedule(0.0, links.copy(), queues, flows, [], 64, 0)
        assert d is not None
        sns.append(d[2])

    assert sns == sorted(sns), f"Intra-flow sequence numbers must be monotonic: {sns}"
    assert len(set(sns)) == 5, "All sequence numbers must be distinct"
