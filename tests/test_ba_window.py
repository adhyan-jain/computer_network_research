"""
Unit tests for BlockAckReceiver:
Sliding window semantics, forced advances, and stall boundaries.
"""

import pytest
from src.mlo_sim.core import Packet, BlockAckReceiver


def test_ba_sliding_window_in_order():
    """Verify perfectly in-order packet arrivals slide win_start continuously."""
    receiver = BlockAckReceiver(win_size=64)
    for sn in range(100):
        pkt = Packet(packet_id=sn, flow_id=1, size_bytes=1500, arr_time=float(sn), seq_num=sn)
        released = receiver.receive_packet(pkt, rx_time=float(sn) + 1.0)
        assert len(released) == 1
        assert released[0].seq_num == sn
        assert receiver.win_start == sn + 1
        assert len(receiver.buffer) == 0


def test_ba_window_forced_advance():
    """
    Verify that receiving a sequence number beyond win_start + win_size - 1
    forces win_start to advance under standard 802.11 rules.
    """
    win_size = 64
    receiver = BlockAckReceiver(win_size=win_size)

    # Missing SN 0. Receive SN 1 through 63.
    for sn in range(1, 64):
        pkt = Packet(packet_id=sn, flow_id=1, size_bytes=1500, arr_time=0.0, seq_num=sn)
        released = receiver.receive_packet(pkt, rx_time=float(sn))
        assert len(released) == 0
        assert receiver.win_start == 0

    assert len(receiver.buffer) == 63

    # Now receive SN 64. This exceeds win_start (0) + win_size (64) - 1 = 63!
    pkt64 = Packet(packet_id=64, flow_id=1, size_bytes=1500, arr_time=0.0, seq_num=64)
    released = receiver.receive_packet(pkt64, rx_time=64.0)

    # Window should force-advance: new_win_start = 64 - 64 + 1 = 1!
    # SN 1 was in buffer, so advancing to 1 causes SN 1..64 to all release!
    assert receiver.win_start == 65
    assert receiver.window_advances_forced == 1
    assert len(released) == 64  # SN 1..64 released
    assert len(receiver.buffer) == 0
