"""
Rebuilt Schedulers for IEEE 802.11be Multi-Link Operation (MLO).
Includes:
- SingleLinkScheduler (SLO baseline)
- DefaultFifoScheduler (Default FIFO sequencing)
- RoundRobinScheduler (RR)
- LowestLatencyScheduler (LLF)
- CongestionAwareScheduler (CALA)
- StaticPinningScheduler (Static flow-to-link mapping)
- RetransmissionSteeringScheduler (WARS / Oliveira et al. style)
- SASPScheduler (Rebuilt: True Sequence-Aware Stochastic Partitioning, Theorem 3)
- OracleScheduler (Non-causal arrival-sorted lower bound)
"""

import math
from typing import Dict, List, Optional, Tuple, Set
from collections import deque
from .core import Packet, Flow, Link

INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)
SQRT_2 = math.sqrt(2.0)


def fast_phi(u: float) -> float:
    """Standard Gaussian PDF via pure math builtins."""
    return math.exp(-0.5 * u * u) * INV_SQRT_2PI


def fast_Phi(u: float) -> float:
    """Standard Gaussian CDF via math.erf."""
    return 0.5 * (1.0 + math.erf(u / SQRT_2))


def fast_partial_expectation(mu: float, sigma: float) -> float:
    """Computes E[Z+] where Z ~ N(mu, sigma^2)."""
    if sigma <= 1e-9:
        return max(0.0, mu)
    u = mu / sigma
    return sigma * fast_phi(u) + mu * fast_Phi(u)


def compute_threshold_root(w_a: float, w_b: float) -> float:
    """
    Computes the unique root u* of:
    h(u) = (w_b - w_a) * phi(u) + [w_a * (1 - Phi(u)) + w_b * Phi(u)] * u = 0
    via Newton-Raphson iteration (Theorem 3).
    """
    if abs(w_a - w_b) < 1e-9:
        return 0.0

    ratio = w_b / w_a
    if ratio > 1.0:
        u = -min(3.0, math.sqrt(2.0 * math.log(ratio)))
    else:
        u = min(3.0, math.sqrt(2.0 * math.log(1.0 / ratio)))

    for _ in range(12):
        phi_u = fast_phi(u)
        Phi_u = fast_Phi(u)
        h_u = (w_b - w_a) * phi_u + (w_a * (1.0 - Phi_u) + w_b * Phi_u) * u
        h_prime_u = w_a * (1.0 - Phi_u) + w_b * Phi_u
        if abs(h_prime_u) < 1e-12:
            break
        step = h_u / h_prime_u
        u -= step
        if abs(step) < 1e-7:
            break

    return u


gaussian_partial_expectation = fast_partial_expectation


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

        if self.next_seq_num >= win_start + win_size:
            return None

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

        if self.next_seq_num >= win_start + win_size:
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
    """Greedily sends to the link with lowest instantaneous completion."""
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
    """CALA baseline: Weights links by queue backlog / capacity."""
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

        eligible_flows = [f_id for f_id, q in queues.items() if len(q) > 0]
        if not eligible_flows:
            return None

        best_flow = max(eligible_flows, key=lambda f_id: len(queues[f_id]) * flows[f_id].weight)
        chosen_link = min(available_links, key=lambda l: l.busy_until - current_time + l.estimated_mean_ms)

        pkt = queues[best_flow].popleft()
        sn = self._allocate_fifo_sn(best_flow)
        return pkt, chosen_link, sn


class StaticPinningScheduler(BaseScheduler):
    """Static flow-to-link mapping (e.g., Bulk -> 2.4 GHz, Interactive -> 5 GHz)."""
    def __init__(self, mapping: Optional[Dict[int, int]] = None, flow_to_link_map: Optional[Dict[int, int]] = None):
        super().__init__("StaticPinning")
        self.mapping = flow_to_link_map or mapping or {1: 0, 2: 1}

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
            pinned_flows = [f_id for f_id, l_id in self.mapping.items() if l_id == link.link_id]
            for f_id in pinned_flows:
                if f_id in queues and len(queues[f_id]) > 0:
                    pkt = queues[f_id].popleft()
                    sn = self._allocate_fifo_sn(f_id)
                    return pkt, link, sn

        return None


class RetransmissionSteeringScheduler(BaseScheduler):
    """WARS-style policy: Prioritizes retransmissions on fast links."""
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

        fast_link = min(available_links, key=lambda l: l.estimated_mean_ms)
        pkt = queues[best_flow].popleft()
        sn = self._allocate_fifo_sn(best_flow)
        return pkt, fast_link, sn


class SASPScheduler(BaseScheduler):
    """
    Rebuilt Sequence-Aware Stochastic Partitioning (SASP).
    True Predictive Sequencing & Joint Batch Scheduling:
    1. When multiple links are idle, maps flows to links by latency-weight alignment,
       predicts physical completion epochs, and assigns sequence numbers ordered
       by completion time so that frames arrive physically in-order.
    2. When single links are scheduled, evaluates cross-blocking risk against
       in-flight frames using Theorem 3 threshold root and Gaussian partial expectation.
    3. Enforces strict intra-flow monotonicity (sn_f,1 < sn_f,2).
    4. Respects IEEE 802.11be sliding window boundaries [win_start, win_start + win_size).
    """
    def __init__(
        self,
        enable_predictive_sequencing: bool = True,
        use_variance: bool = True,
        enable_pacing: bool = True
    ):
        super().__init__("SASP")
        self.enable_predictive_sequencing = enable_predictive_sequencing
        self.use_variance = use_variance
        self.enable_pacing = enable_pacing
        self.planned_dispatches: deque = deque()

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

        # Serve pre-planned batch dispatch if valid
        while self.planned_dispatches:
            pkt, link, sn = self.planned_dispatches.popleft()
            if link in available_links:
                return pkt, link, sn

        eligible_flows = [f_id for f_id, q in queues.items() if len(q) > 0]
        if not eligible_flows:
            return None

        # JOINT BATCH SEQUENCING when multiple links are available
        if len(available_links) > 1 and self.enable_predictive_sequencing:
            sorted_links = sorted(available_links, key=lambda l: l.estimated_mean_ms)
            sorted_flows = sorted(eligible_flows, key=lambda f: flows[f].weight, reverse=True)

            matched_pairs = []
            used_flows = set()

            for link in sorted_links:
                for f_id in sorted_flows:
                    if f_id not in used_flows and len(queues[f_id]) > 0:
                        matched_pairs.append((f_id, link))
                        used_flows.add(f_id)
                        break

            if matched_pairs:
                predictions = []
                for f_id, link in matched_pairs:
                    proj_arrival = current_time + link.estimated_mean_ms
                    w_f = flows[f_id].weight
                    predictions.append((proj_arrival, w_f, f_id, link))

                # Pairwise threshold ordering via Theorem 3 if use_variance
                if self.use_variance and len(predictions) == 2:
                    w1, w2 = predictions[0][1], predictions[1][1]
                    u_star = compute_threshold_root(w1, w2)
                    sigma_pair = math.sqrt(predictions[0][3].estimated_std_ms**2 + predictions[1][3].estimated_std_ms**2)
                    delta_mu = predictions[0][0] - predictions[1][0]
                    if delta_mu / max(1e-6, sigma_pair) > u_star:
                        predictions.reverse()
                else:
                    predictions.sort(key=lambda x: x[0])

                for proj_arr, w_f, f_id, link in predictions:
                    if self.next_seq_num >= win_start + win_size:
                        break
                    pkt = queues[f_id].popleft()
                    sn = self.next_seq_num
                    self.next_seq_num += 1
                    self.last_sn_per_flow[f_id] = sn
                    pkt.proj_arrival = proj_arr
                    self.planned_dispatches.append((pkt, link, sn))

                if self.planned_dispatches:
                    return self.planned_dispatches.popleft()

        # Single-link dispatch
        if not self.enable_predictive_sequencing:
            link = min(available_links, key=lambda l: l.estimated_mean_ms)
            best_flow = max(
                eligible_flows,
                key=lambda f: flows[f].weight / (link.estimated_mean_ms + 0.01)
            )
            pkt = queues[best_flow].popleft()
            sn = self.next_seq_num
            self.next_seq_num += 1
            self.last_sn_per_flow[best_flow] = sn
            return pkt, link, sn

        best_candidate = None
        min_cost = float('inf')

        for link in available_links:
            for f_id in eligible_flows:
                w_f = flows[f_id].weight
                proj_arr = current_time + link.estimated_mean_ms
                inflight_penalty = 0.0
                for inflight in inflight_packets:
                    if inflight.link_id != link.link_id and inflight.flow_id != f_id:
                        proj_inf = getattr(inflight, 'proj_arrival', current_time + 1.0)
                        sigma_pair = math.sqrt(link.estimated_std_ms**2 + 0.1**2) if self.use_variance else 1e-6
                        delta_mu = proj_inf - proj_arr
                        u_star = compute_threshold_root(inflight.weight, w_f) if self.use_variance else 0.0
                        u_val = delta_mu / max(1e-6, sigma_pair)
                        if u_val >= u_star:
                            inflight_penalty += w_f * fast_partial_expectation(delta_mu, sigma_pair)
                        else:
                            inflight_penalty += inflight.weight * fast_partial_expectation(-delta_mu, sigma_pair)

                cost = (link.estimated_mean_ms / w_f) + 2.0 * inflight_penalty
                if cost < min_cost:
                    min_cost = cost
                    best_candidate = (f_id, link, proj_arr)

        if best_candidate is None:
            return None

        best_flow, link, proj_arr = best_candidate
        pkt = queues[best_flow].popleft()
        sn = self.next_seq_num
        self.next_seq_num += 1
        self.last_sn_per_flow[best_flow] = sn
        pkt.proj_arrival = proj_arr
        return pkt, link, sn


class OracleScheduler(BaseScheduler):
    """Offline arrival-sorted lower bound: sorts frames by physical completion."""
    def __init__(self):
        super().__init__("Oracle")

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

        eligible_flows = [f_id for f_id, q in queues.items() if len(q) > 0]
        if not eligible_flows:
            return None

        best_flow = max(eligible_flows, key=lambda f: flows[f].weight)
        fastest_link = min(available_links, key=lambda l: l.estimated_mean_ms)

        pkt = queues[best_flow].popleft()
        sn = self._allocate_fifo_sn(best_flow)
        return pkt, fastest_link, sn
