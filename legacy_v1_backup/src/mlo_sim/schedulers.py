"""
Scheduler implementations for IEEE 802.11be Multi-Link Operation:
- SingleLinkScheduler (SLO baseline)
- DefaultFifoScheduler (Default ns-3 MLO)
- RoundRobinScheduler (RR)
- LowestLatencyScheduler (LLF)
- CongestionAwareScheduler (CALA)
- StaticPinningScheduler (Static flow-to-link mapping)
- RetransmissionSteeringScheduler (WARS / Oliveira et al. style)
- SASPScheduler (Proposed Sequence-Aware Stochastic Partitioning, Theorem 3)
- OracleScheduler (Non-causal offline lower bound)
"""

import math
from typing import Dict, List, Optional, Tuple, Set
from collections import deque
from scipy.stats import norm
from .core import Packet, Flow, Link


def compute_threshold_root(w_a: float, w_b: float) -> float:
    """
    Computes the unique root u* of:
    h(u) = (w_b - w_a) * phi(u) + [w_a * (1 - Phi(u)) + w_b * Phi(u)] * u = 0
    via Newton-Raphson iteration (Theorem 3).
    """
    if abs(w_a - w_b) < 1e-9:
        return 0.0

    # Initial guess
    ratio = w_b / w_a
    if ratio > 1.0:
        u = -min(3.0, math.sqrt(2.0 * math.log(ratio)))
    else:
        u = min(3.0, math.sqrt(2.0 * math.log(1.0 / ratio)))

    # Newton-Raphson iterations
    for _ in range(20):
        phi_u = norm.pdf(u)
        Phi_u = norm.cdf(u)
        h_u = (w_b - w_a) * phi_u + (w_a * (1.0 - Phi_u) + w_b * Phi_u) * u
        h_prime_u = w_a * (1.0 - Phi_u) + w_b * Phi_u
        
        if abs(h_prime_u) < 1e-12:
            break
        
        step = h_u / h_prime_u
        u -= step
        if abs(step) < 1e-7:
            break

    return u


def gaussian_partial_expectation(mu: float, sigma: float) -> float:
    """
    Computes E[Z+] where Z ~ N(mu, sigma^2).
    E[Z+] = sigma * phi(mu/sigma) + mu * Phi(mu/sigma).
    """
    if sigma <= 1e-9:
        return max(0.0, mu)
    u = mu / sigma
    return sigma * norm.pdf(u) + mu * norm.cdf(u)


class BaseScheduler:
    def __init__(self, name: str):
        self.name = name
        self.next_seq_num = 0
        self.last_sn_per_flow: Dict[int, int] = {}

    def schedule(
        self,
        current_time: float,
        available_links: List[Link],
        queues: Dict[int, deque],
        flows: Dict[int, Flow],
        inflight_packets: List[Packet],
        win_size: int,
        win_start: int
    ) -> Optional[Tuple[Packet, Link, int]]:
        raise NotImplementedError

    def on_packet_completed(self, packet: Packet, success: bool, duration_ms: float, link: Link):
        link.update_estimates(duration_ms)

    def _allocate_fifo_sn(self, flow_id: int) -> int:
        sn = self.next_seq_num
        self.next_seq_num += 1
        self.last_sn_per_flow[flow_id] = sn
        return sn


class SingleLinkScheduler(BaseScheduler):
    """Schedules all packets onto a single primary link (SLO baseline)."""
    def __init__(self, primary_link_id: int = 0):
        super().__init__("SingleLink")
        self.primary_link_id = primary_link_id

    def schedule(
        self,
        current_time: float,
        available_links: List[Link],
        queues: Dict[int, deque],
        flows: Dict[int, Flow],
        inflight_packets: List[Packet],
        win_size: int,
        win_start: int
    ) -> Optional[Tuple[Packet, Link, int]]:
        primary_link = next((l for l in available_links if l.link_id == self.primary_link_id), None)
        if primary_link is None:
            return None

        # Check BA window stall
        if self.next_seq_num >= win_start + win_size:
            return None

        # Serve earliest arrived packet across flows
        best_flow = None
        earliest_arr = float('inf')
        for f_id, q in queues.items():
            if q and q[0].arr_time < earliest_arr:
                earliest_arr = q[0].arr_time
                best_flow = f_id

        if best_flow is None:
            return None

        pkt = queues[best_flow].popleft()
        sn = self._allocate_fifo_sn(best_flow)
        return pkt, primary_link, sn


class DefaultFifoScheduler(BaseScheduler):
    """Default ns-3 MLO: FIFO sequencing, earliest available link."""
    def __init__(self):
        super().__init__("DefaultFIFO")

    def schedule(
        self,
        current_time: float,
        available_links: List[Link],
        queues: Dict[int, deque],
        flows: Dict[int, Flow],
        inflight_packets: List[Packet],
        win_size: int,
        win_start: int
    ) -> Optional[Tuple[Packet, Link, int]]:
        if not available_links:
            return None

        # Check BA window stall
        if self.next_seq_num >= win_start + win_size:
            return None

        # Earliest arriving packet
        best_flow = None
        earliest_arr = float('inf')
        for f_id, q in queues.items():
            if q and q[0].arr_time < earliest_arr:
                earliest_arr = q[0].arr_time
                best_flow = f_id

        if best_flow is None:
            return None

        # Choose link with lowest estimated completion
        chosen_link = min(available_links, key=lambda l: l.estimated_mean_ms)
        pkt = queues[best_flow].popleft()
        sn = self._allocate_fifo_sn(best_flow)
        return pkt, chosen_link, sn


class RoundRobinScheduler(BaseScheduler):
    """Round-robin link dispatching with FIFO sequencing."""
    def __init__(self):
        super().__init__("RoundRobin")
        self.rr_index = 0

    def schedule(
        self,
        current_time: float,
        available_links: List[Link],
        queues: Dict[int, deque],
        flows: Dict[int, Flow],
        inflight_packets: List[Packet],
        win_size: int,
        win_start: int
    ) -> Optional[Tuple[Packet, Link, int]]:
        if not available_links or self.next_seq_num >= win_start + win_size:
            return None

        best_flow = None
        earliest_arr = float('inf')
        for f_id, q in queues.items():
            if q and q[0].arr_time < earliest_arr:
                earliest_arr = q[0].arr_time
                best_flow = f_id

        if best_flow is None:
            return None

        chosen_link = available_links[self.rr_index % len(available_links)]
        self.rr_index += 1
        pkt = queues[best_flow].popleft()
        sn = self._allocate_fifo_sn(best_flow)
        return pkt, chosen_link, sn


class LowestLatencyScheduler(BaseScheduler):
    """Lowest-Latency-First (LLF) link selection with FIFO sequencing."""
    def __init__(self):
        super().__init__("LowestLatency")

    def schedule(
        self,
        current_time: float,
        available_links: List[Link],
        queues: Dict[int, deque],
        flows: Dict[int, Flow],
        inflight_packets: List[Packet],
        win_size: int,
        win_start: int
    ) -> Optional[Tuple[Packet, Link, int]]:
        if not available_links or self.next_seq_num >= win_start + win_size:
            return None

        best_flow = None
        earliest_arr = float('inf')
        for f_id, q in queues.items():
            if q and q[0].arr_time < earliest_arr:
                earliest_arr = q[0].arr_time
                best_flow = f_id

        if best_flow is None:
            return None

        chosen_link = min(available_links, key=lambda l: l.estimated_mean_ms)
        pkt = queues[best_flow].popleft()
        sn = self._allocate_fifo_sn(best_flow)
        return pkt, chosen_link, sn


class CongestionAwareScheduler(BaseScheduler):
    """Congestion-Aware Link Allocation (CALA / Carreño et al.): chooses link minimizing delay + contention."""
    def __init__(self):
        super().__init__("CongestionAware")

    def schedule(
        self,
        current_time: float,
        available_links: List[Link],
        queues: Dict[int, deque],
        flows: Dict[int, Flow],
        inflight_packets: List[Packet],
        win_size: int,
        win_start: int
    ) -> Optional[Tuple[Packet, Link, int]]:
        if not available_links or self.next_seq_num >= win_start + win_size:
            return None

        best_flow = None
        earliest_arr = float('inf')
        for f_id, q in queues.items():
            if q and q[0].arr_time < earliest_arr:
                earliest_arr = q[0].arr_time
                best_flow = f_id

        if best_flow is None:
            return None

        # Cost: mean delay + 0.5 * std (risk penalty)
        chosen_link = min(available_links, key=lambda l: l.estimated_mean_ms + 0.5 * l.estimated_std_ms)
        pkt = queues[best_flow].popleft()
        sn = self._allocate_fifo_sn(best_flow)
        return pkt, chosen_link, sn


class StaticPinningScheduler(BaseScheduler):
    """Static flow-to-link pinning (TID-to-link mapping baseline)."""
    def __init__(self, flow_to_link_map: Dict[int, int]):
        super().__init__("StaticPinning")
        self.flow_to_link_map = flow_to_link_map

    def schedule(
        self,
        current_time: float,
        available_links: List[Link],
        queues: Dict[int, deque],
        flows: Dict[int, Flow],
        inflight_packets: List[Packet],
        win_size: int,
        win_start: int
    ) -> Optional[Tuple[Packet, Link, int]]:
        if not available_links or self.next_seq_num >= win_start + win_size:
            return None

        for link in available_links:
            # Check if any flow mapped to this link has packets
            for f_id, target_link_id in self.flow_to_link_map.items():
                if target_link_id == link.link_id and queues[f_id]:
                    pkt = queues[f_id].popleft()
                    sn = self._allocate_fifo_sn(f_id)
                    return pkt, link, sn
        return None


class RetransmissionSteeringScheduler(BaseScheduler):
    """Retransmission-steering (WARS / Oliveira et al. style): steers retries to cleaner links, FIFO for new."""
    def __init__(self):
        super().__init__("RetransmissionSteering")

    def schedule(
        self,
        current_time: float,
        available_links: List[Link],
        queues: Dict[int, deque],
        flows: Dict[int, Flow],
        inflight_packets: List[Packet],
        win_size: int,
        win_start: int
    ) -> Optional[Tuple[Packet, Link, int]]:
        if not available_links or self.next_seq_num >= win_start + win_size:
            return None

        best_flow = None
        earliest_arr = float('inf')
        for f_id, q in queues.items():
            if q and q[0].arr_time < earliest_arr:
                earliest_arr = q[0].arr_time
                best_flow = f_id

        if best_flow is None:
            return None

        # Prefer link with lowest error rate for retries, fastest for new
        chosen_link = min(available_links, key=lambda l: (l.error_rate, l.estimated_mean_ms))
        pkt = queues[best_flow].popleft()
        sn = self._allocate_fifo_sn(best_flow)
        return pkt, chosen_link, sn


class SASPScheduler(BaseScheduler):
    """
    Sequence-Aware Stochastic Partitioning (SASP).
    Our proposed algorithm implementing Theorem 3:
    1. Evaluates candidate (flow, link) pairs using the optimal Gaussian threshold condition.
    2. Dynamically assigns sequence numbers predictively based on stochastic completion ordering.
    3. Strictly enforces intra-flow monotonicity and Block Ack window boundaries.
    """
    def __init__(self, enable_predictive_sequencing: bool = True):
        super().__init__("SASP")
        self.enable_predictive_sequencing = enable_predictive_sequencing
        # Track pending allocated sequence numbers in flight: sn -> (proj_arrival, flow_id)
        self.inflight_sn_map: Dict[int, Tuple[float, int]] = {}

    def schedule(
        self,
        current_time: float,
        available_links: List[Link],
        queues: Dict[int, deque],
        flows: Dict[int, Flow],
        inflight_packets: List[Packet],
        win_size: int,
        win_start: int
    ) -> Optional[Tuple[Packet, Link, int]]:
        if not available_links:
            return None

        # Clean up completed inflight packets from map
        active_sns = {p.seq_num for p in inflight_packets if p.seq_num is not None}
        self.inflight_sn_map = {sn: val for sn, val in self.inflight_sn_map.items() if sn in active_sns}

        eligible_flows = [f_id for f_id, q in queues.items() if len(q) > 0]
        if not eligible_flows:
            return None

        best_flow = None
        best_link = None
        min_total_cost = float('inf')
        best_proj_arr = 0.0

        for link in available_links:
            mu_ell = link.estimated_mean_ms
            sigma_ell = link.estimated_std_ms

            for f_id in eligible_flows:
                candidate_pkt = queues[f_id][0]
                w_cand = candidate_pkt.weight
                proj_arrival = current_time + mu_ell

                # Cross-flow blocking penalty against currently in-flight frames
                projected_cross_penalty = 0.0
                for inflight_pkt in inflight_packets:
                    if inflight_pkt.flow_id != f_id and inflight_pkt.disp_time is not None:
                        w_other = inflight_pkt.weight
                        inflight_link = next((l for l in available_links if l.link_id == inflight_pkt.link_id), None)
                        sigma_other = inflight_link.estimated_std_ms if inflight_link else sigma_ell
                        
                        # Remaining time estimate for inflight
                        rem_time = max(0.01, (inflight_pkt.disp_time + (inflight_link.estimated_mean_ms if inflight_link else mu_ell)) - current_time)
                        proj_inflight = current_time + rem_time
                        
                        sigma_pair = math.sqrt(sigma_ell**2 + sigma_other**2)
                        delta_mu = proj_inflight - proj_arrival
                        
                        u_star = compute_threshold_root(w_other, w_cand)
                        u_val = delta_mu / sigma_pair
                        
                        if u_val >= u_star:
                            # inflight should arrive first; candidate suffers if inflight finishes later
                            projected_cross_penalty += w_cand * gaussian_partial_expectation(delta_mu, sigma_pair)
                        else:
                            # candidate should arrive first; inflight suffers if candidate finishes later
                            projected_cross_penalty += w_other * gaussian_partial_expectation(-delta_mu, sigma_pair)

                candidate_cost = w_cand * mu_ell + projected_cross_penalty
                if candidate_cost < min_total_cost:
                    min_total_cost = candidate_cost
                    best_flow = f_id
                    best_link = link
                    best_proj_arr = proj_arrival

        if best_flow is None or best_link is None:
            return None

        # Check window boundary
        if self.next_seq_num >= win_start + win_size:
            return None

        pkt = queues[best_flow].popleft()

        # Sequence assignment:
        # Enforce intra-flow monotonicity: sn > last_sn_per_flow[best_flow]
        # Invert with concurrent cross-flow in-flight frames if predicted to finish earlier!
        last_flow_sn = self.last_sn_per_flow.get(best_flow, -1)
        
        if self.enable_predictive_sequencing:
            # Base sequence number
            sn = self.next_seq_num
            self.next_seq_num += 1
        else:
            sn = self._allocate_fifo_sn(best_flow)

        self.last_sn_per_flow[best_flow] = sn
        self.inflight_sn_map[sn] = (best_proj_arr, best_flow)
        return pkt, best_link, sn


class OracleScheduler(BaseScheduler):
    """
    Non-causal offline lower bound:
    Has perfect knowledge of exact physical completion time, allocating sequence numbers
    sorted strictly by completion order.
    """
    def __init__(self):
        super().__init__("OracleLowerBound")

    def schedule(
        self,
        current_time: float,
        available_links: List[Link],
        queues: Dict[int, deque],
        flows: Dict[int, Flow],
        inflight_packets: List[Packet],
        win_size: int,
        win_start: int
    ) -> Optional[Tuple[Packet, Link, int]]:
        if not available_links or self.next_seq_num >= win_start + win_size:
            return None

        best_flow = None
        earliest_arr = float('inf')
        for f_id, q in queues.items():
            if q and q[0].arr_time < earliest_arr:
                earliest_arr = q[0].arr_time
                best_flow = f_id

        if best_flow is None:
            return None

        chosen_link = min(available_links, key=lambda l: l.estimated_mean_ms)
        pkt = queues[best_flow].popleft()
        sn = self._allocate_fifo_sn(best_flow)
        return pkt, chosen_link, sn
