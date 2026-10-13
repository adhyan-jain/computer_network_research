"""
Metrics aggregation, percentile calculation, and statistical reporting.
Computes fine-grained self-blocking, cross-blocking, goodput, and latency distributions.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import numpy as np
from .core import Packet, BlockAckReceiver


@dataclass
class FlowMetrics:
    flow_id: int
    packet_count: int
    mean_self_blocking_ms: float
    mean_cross_blocking_ms: float
    mean_reorder_delay_ms: float
    mean_e2e_delay_ms: float
    p50_e2e_delay_ms: float
    p95_e2e_delay_ms: float
    p99_e2e_delay_ms: float
    throughput_mbps: float


@dataclass
class SimulationMetrics:
    scheduler_name: str
    delivered_count: int
    duration_ms: float
    mean_self_blocking_ms: float
    mean_cross_blocking_ms: float
    mean_reorder_delay_ms: float
    mean_e2e_delay_ms: float
    p50_e2e_delay_ms: float
    p95_e2e_delay_ms: float
    p99_e2e_delay_ms: float
    aggregate_goodput_mbps: float
    stall_events: int
    window_advances_forced: int
    weighted_cross_blocking: float
    per_flow: Dict[int, FlowMetrics]


def compute_metrics(receiver: BlockAckReceiver, duration_ms: float, scheduler_name: str = "Unknown") -> SimulationMetrics:
    """Aggregates all per-packet metrics from BlockAckReceiver into SimulationMetrics."""
    packets = receiver.delivered_packets
    if not packets:
        return SimulationMetrics(
            scheduler_name=scheduler_name,
            delivered_count=0,
            duration_ms=duration_ms,
            mean_self_blocking_ms=0.0,
            mean_cross_blocking_ms=0.0,
            mean_reorder_delay_ms=0.0,
            mean_e2e_delay_ms=0.0,
            p50_e2e_delay_ms=0.0,
            p95_e2e_delay_ms=0.0,
            p99_e2e_delay_ms=0.0,
            aggregate_goodput_mbps=0.0,
            stall_events=receiver.stall_events,
            window_advances_forced=receiver.window_advances_forced,
            weighted_cross_blocking=0.0,
            per_flow={}
        )

    self_blockings = np.array([p.self_blocking for p in packets])
    cross_blockings = np.array([p.cross_blocking for p in packets])
    reorder_delays = np.array([p.total_reorder_delay for p in packets])
    e2e_delays = np.array([p.end_to_end_delay for p in packets])
    weights = np.array([p.weight for p in packets])

    total_bits = sum(p.size_bytes * 8 for p in packets)
    duration_sec = duration_ms / 1000.0
    goodput_mbps = (total_bits / 1e6) / duration_sec if duration_sec > 0 else 0.0

    weighted_cross = np.sum(weights * cross_blockings) / len(packets)

    # Per-flow analysis
    flow_ids = set(p.flow_id for p in packets)
    per_flow: Dict[int, FlowMetrics] = {}
    for f_id in flow_ids:
        f_pkts = [p for p in packets if p.flow_id == f_id]
        f_e2e = np.array([p.end_to_end_delay for p in f_pkts])
        f_bits = sum(p.size_bytes * 8 for p in f_pkts)
        f_goodput = (f_bits / 1e6) / duration_sec if duration_sec > 0 else 0.0

        per_flow[f_id] = FlowMetrics(
            flow_id=f_id,
            packet_count=len(f_pkts),
            mean_self_blocking_ms=float(np.mean([p.self_blocking for p in f_pkts])),
            mean_cross_blocking_ms=float(np.mean([p.cross_blocking for p in f_pkts])),
            mean_reorder_delay_ms=float(np.mean([p.total_reorder_delay for p in f_pkts])),
            mean_e2e_delay_ms=float(np.mean(f_e2e)),
            p50_e2e_delay_ms=float(np.percentile(f_e2e, 50)),
            p95_e2e_delay_ms=float(np.percentile(f_e2e, 95)),
            p99_e2e_delay_ms=float(np.percentile(f_e2e, 99)),
            throughput_mbps=f_goodput
        )

    return SimulationMetrics(
        scheduler_name=scheduler_name,
        delivered_count=len(packets),
        duration_ms=duration_ms,
        mean_self_blocking_ms=float(np.mean(self_blockings)),
        mean_cross_blocking_ms=float(np.mean(cross_blockings)),
        mean_reorder_delay_ms=float(np.mean(reorder_delays)),
        mean_e2e_delay_ms=float(np.mean(e2e_delays)),
        p50_e2e_delay_ms=float(np.percentile(e2e_delays, 50)),
        p95_e2e_delay_ms=float(np.percentile(e2e_delays, 95)),
        p99_e2e_delay_ms=float(np.percentile(e2e_delays, 99)),
        aggregate_goodput_mbps=goodput_mbps,
        stall_events=receiver.stall_events,
        window_advances_forced=receiver.window_advances_forced,
        weighted_cross_blocking=float(weighted_cross),
        per_flow=per_flow
    )
