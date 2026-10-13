"""
Core data structures and protocol primitives for IEEE 802.11be MLO simulation.
Includes Packet, Flow, Link, and standard IEEE 802.11be BlockAckReceiver
with exact orthogonal decomposition of reordering delay (Theorem 1).
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set, Any
import math


@dataclass
class Packet:
    packet_id: int
    flow_id: int
    size_bytes: int
    arr_time: float  # Arrival at Tx U-MAC queue
    weight: float = 1.0
    
    # Scheduling decisions
    seq_num: Optional[int] = None
    link_id: Optional[int] = None
    disp_time: Optional[float] = None
    
    # Transmission history
    attempts: int = 0
    arr_rx_time: Optional[float] = None  # Physical arrival at receiver PHY
    rel_time: Optional[float] = None     # Release from receive reorder buffer to LLC
    
    # Decomposed delay metrics (computed upon release)
    self_blocking: float = 0.0           # S_i: intra-flow reorder wait
    cross_blocking: float = 0.0          # X_i: inter-flow reorder wait
    total_reorder_delay: float = 0.0     # Delta_i = S_i + X_i = rel_time - arr_rx_time
    end_to_end_delay: float = 0.0        # rel_time - arr_time


@dataclass
class Flow:
    flow_id: int
    name: str
    weight: float = 1.0
    rate_pkts_per_sec: float = 200.0
    packet_size_bytes: int = 1500
    last_assigned_sn: int = -1
    packets_generated: int = 0


@dataclass
class Link:
    link_id: int
    name: str
    bandwidth_mbps: float
    base_delay_ms: float
    error_rate: float = 0.0
    contention_sigma_ms: float = 0.1
    max_retries: int = 7
    
    # State
    busy_until: float = 0.0
    current_packet: Optional[Packet] = None
    total_transmitted_pkts: int = 0
    total_retries: int = 0
    total_dropped_pkts: int = 0

    # Moving average estimators for runtime scheduling
    estimated_mean_ms: float = field(init=False)
    estimated_std_ms: float = field(init=False)

    def __post_init__(self):
        self.estimated_mean_ms = self.base_delay_ms + (1500 * 8 / (self.bandwidth_mbps * 1000.0))
        self.estimated_std_ms = max(0.05, self.contention_sigma_ms)

    def update_estimates(self, observed_delay_ms: float, alpha: float = 0.1, beta: float = 0.05):
        """Update runtime exponentially weighted moving estimates of completion delay."""
        diff = observed_delay_ms - self.estimated_mean_ms
        self.estimated_mean_ms += alpha * diff
        self.estimated_std_ms = math.sqrt(max(0.001, (1.0 - beta) * (self.estimated_std_ms ** 2) + beta * (diff ** 2)))


class BlockAckReceiver:
    """
    Standard IEEE 802.11be Block Ack Receiver.
    Operates a single reordering buffer for a single TID across all links.
    Maintains a sliding window [win_start, win_start + win_size - 1].
    Releases packets strictly in monotonically increasing sequence number order.
    Computes exact, orthogonal decomposition: Delta_i = S_i + X_i (Theorem 1).
    """

    def __init__(self, win_size: int = 64, max_seq_num: int = 4096):
        self.win_size = win_size
        self.max_seq_num = max_seq_num
        self.win_start = 0
        
        # Buffer of arrived but unreleased packets: seq_num -> Packet
        self.buffer: Dict[int, Packet] = {}
        
        # History of physical arrival times for delay attribution: seq_num -> Packet
        self.history: Dict[int, Packet] = {}
        
        # Delivered packets in chronological release order
        self.delivered_packets: List[Packet] = []
        
        # Window stall statistics
        self.stall_events: int = 0
        self.window_advances_forced: int = 0

    def receive_packet(self, packet: Packet, rx_time: float) -> List[Packet]:
        """
        Process physical frame arrival at receiver.
        Returns list of packets released to higher layers during this event.
        """
        assert packet.seq_num is not None
        sn = packet.seq_num
        packet.arr_rx_time = rx_time
        self.history[sn] = packet

        released: List[Packet] = []

        # Case 1: Packet is behind win_start (duplicate or late retransmission already advanced)
        if sn < self.win_start:
            # Drop as duplicate / already passed
            return released

        # Case 2: Packet exceeds window boundary [win_start, win_start + win_size - 1]
        if sn >= self.win_start + self.win_size:
            # Force advance win_start under IEEE 802.11 rules
            self.window_advances_forced += 1
            new_win_start = sn - self.win_size + 1
            # Release any buffered packets strictly below new_win_start
            for old_sn in range(self.win_start, new_win_start):
                if old_sn in self.buffer:
                    buffered_pkt = self.buffer.pop(old_sn)
                    self._finalize_release(buffered_pkt, rx_time)
                    released.append(buffered_pkt)
            self.win_start = new_win_start

        # Store in reordering buffer
        self.buffer[sn] = packet

        # Case 3: Release all contiguous in-order packets starting from win_start
        while self.win_start in self.buffer:
            next_pkt = self.buffer.pop(self.win_start)
            self._finalize_release(next_pkt, rx_time)
            released.append(next_pkt)
            self.win_start += 1

        return released

    def _finalize_release(self, packet: Packet, rel_time: float):
        """
        Finalize packet release and calculate exact delay decomposition (Theorem 1).
        """
        packet.rel_time = rel_time
        assert packet.arr_rx_time is not None
        sn = packet.seq_num
        f_i = packet.flow_id
        A_i = packet.arr_rx_time

        # Compute intra-flow arrival upper bound: max_{j: f_j = f_i, s_j < s_i} A_j
        intra_predecessors_rx = [
            p.arr_rx_time for s, p in self.history.items()
            if p.flow_id == f_i and s < sn and p.arr_rx_time is not None
        ]
        
        if intra_predecessors_rx:
            R_intra = max(A_i, max(intra_predecessors_rx))
        else:
            R_intra = A_i

        # Theorem 1 orthogonal decomposition:
        # S_i = max(0, R_intra - A_i)
        # X_i = max(0, rel_time - R_intra)
        # Delta_i = S_i + X_i = rel_time - A_i
        packet.self_blocking = max(0.0, R_intra - A_i)
        packet.cross_blocking = max(0.0, rel_time - R_intra)
        packet.total_reorder_delay = max(0.0, rel_time - A_i)
        packet.end_to_end_delay = rel_time - packet.arr_time

        # Numerical identity sanity check
        assert abs((packet.self_blocking + packet.cross_blocking) - packet.total_reorder_delay) < 1e-9, (
            f"Decomposition invariant violation: S={packet.self_blocking}, X={packet.cross_blocking}, Delta={packet.total_reorder_delay}"
        )

        self.delivered_packets.append(packet)
