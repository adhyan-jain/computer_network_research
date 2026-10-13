"""
Unit and property-based tests verifying Theorem 1:
Orthogonal Decomposition and Attributable Uniqueness of Reordering Delay.
"""

import pytest
import numpy as np
from src.mlo_sim.core import Packet, BlockAckReceiver


def test_theorem_1_orthogonal_decomposition_identity():
    """
    Verify for any arrival sequence that:
    1. Delta_i = S_i + X_i
    2. S_i >= 0
    3. X_i >= 0
    """
    receiver = BlockAckReceiver(win_size=64)

    # Sequence of packets from two flows with out-of-order physical arrivals
    # Packet 1 (Flow 1, SN 0): arrived at t = 5.0
    # Packet 2 (Flow 2, SN 1): arrived at t = 2.0 (faster link)
    # Packet 3 (Flow 1, SN 2): arrived at t = 4.0
    # Packet 4 (Flow 2, SN 3): arrived at t = 3.0
    packets = [
        Packet(packet_id=1, flow_id=1, size_bytes=1500, arr_time=0.0, seq_num=0),
        Packet(packet_id=2, flow_id=2, size_bytes=1500, arr_time=0.1, seq_num=1),
        Packet(packet_id=3, flow_id=1, size_bytes=1500, arr_time=0.2, seq_num=2),
        Packet(packet_id=4, flow_id=2, size_bytes=1500, arr_time=0.3, seq_num=3),
    ]

    # Arrivals happen out of SN order:
    # At t=2.0, Packet 2 arrives (held in buffer)
    # At t=3.0, Packet 4 arrives (held in buffer)
    # At t=4.0, Packet 3 arrives (held in buffer)
    # At t=5.0, Packet 1 arrives -> all packets released!
    receiver.receive_packet(packets[1], rx_time=2.0)
    receiver.receive_packet(packets[3], rx_time=3.0)
    receiver.receive_packet(packets[2], rx_time=4.0)
    released = receiver.receive_packet(packets[0], rx_time=5.0)

    assert len(released) == 4
    for pkt in released:
        # Check non-negativity
        assert pkt.self_blocking >= -1e-9
        assert pkt.cross_blocking >= -1e-9
        assert pkt.total_reorder_delay >= -1e-9
        # Check Theorem 1 exact additive sum identity
        assert abs((pkt.self_blocking + pkt.cross_blocking) - pkt.total_reorder_delay) < 1e-9

    # Check exact values:
    # Packet 1 (SN 0): arrived at 5.0, released at 5.0 -> Delta = 0, S = 0, X = 0
    p1 = packets[0]
    assert p1.total_reorder_delay == 0.0

    # Packet 2 (SN 1, Flow 2): arrived at 2.0, released at 5.0 -> Delta = 3.0
    # Flow 2 has no predecessors -> R_intra = 2.0.
    # Therefore, S_2 = 0.0, X_2 = 3.0 (pure cross-flow blocking by Packet 1!)
    p2 = packets[1]
    assert p2.total_reorder_delay == 3.0
    assert p2.self_blocking == 0.0
    assert p2.cross_blocking == 3.0

    # Packet 3 (SN 2, Flow 1): arrived at 4.0, released at 5.0 -> Delta = 1.0
    # Flow 1 predecessor is Packet 1 which arrived at 5.0 -> R_intra = max(4.0, 5.0) = 5.0.
    # Therefore, S_3 = 1.0, X_3 = 0.0 (pure self-blocking by Flow 1's own Packet 1!)
    p3 = packets[2]
    assert p3.total_reorder_delay == 1.0
    assert p3.self_blocking == 1.0
    assert p3.cross_blocking == 0.0


def test_theorem_1_attribution_invariance():
    """
    Property test: Removing all other flows leaves intra-flow self-blocking S_i invariant!
    """
    rng = np.random.default_rng(12345)
    for _ in range(20):
        receiver_full = BlockAckReceiver(win_size=128)
        receiver_solo = BlockAckReceiver(win_size=128)

        n_pkts = 30
        flow_ids = rng.integers(1, 3, size=n_pkts)  # Flows 1 and 2
        rx_times = rng.uniform(1.0, 50.0, size=n_pkts)

        pkts_full = [
            Packet(packet_id=i, flow_id=int(flow_ids[i]), size_bytes=1500, arr_time=0.0, seq_num=i)
            for i in range(n_pkts)
        ]
        
        # Order of physical arrivals is sorted by rx_times
        arrival_indices = np.argsort(rx_times)
        for idx in arrival_indices:
            receiver_full.receive_packet(pkts_full[idx], rx_time=float(rx_times[idx]))

        # Now simulate Flow 1 completely isolated
        flow1_indices = [i for i in range(n_pkts) if flow_ids[i] == 1]
        pkts_solo = [
            Packet(packet_id=i, flow_id=1, size_bytes=1500, arr_time=0.0, seq_num=seq)
            for seq, i in enumerate(flow1_indices)
        ]
        arrival_order_solo = sorted(range(len(flow1_indices)), key=lambda k: rx_times[flow1_indices[k]])
        for k in arrival_order_solo:
            receiver_solo.receive_packet(pkts_solo[k], rx_time=float(rx_times[flow1_indices[k]]))

        # Verify that for all Flow 1 packets, S_i in the full system equals S_i in the solo system
        for full_p, solo_p in zip([pkts_full[i] for i in flow1_indices], pkts_solo):
            assert abs(full_p.self_blocking - solo_p.self_blocking) < 1e-9
            # In the solo system, cross-flow blocking must be identically zero
            assert abs(solo_p.cross_blocking) < 1e-9
