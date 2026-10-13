"""
Integration tests for schedulers running inside MloSimulator.
Verifies all 8 schedulers on standardized network topologies.
"""

import pytest
from src.mlo_sim.core import Flow, Link
from src.mlo_sim.channel import WirelessChannel
from src.mlo_sim.schedulers import (
    SingleLinkScheduler,
    DefaultFifoScheduler,
    RoundRobinScheduler,
    LowestLatencyScheduler,
    CongestionAwareScheduler,
    StaticPinningScheduler,
    RetransmissionSteeringScheduler,
    SASPScheduler,
    OracleScheduler
)
from src.mlo_sim.simulator import MloSimulator
from src.mlo_sim.metrics import compute_metrics


def build_test_topology():
    flows = [
        Flow(flow_id=1, name="Bulk", weight=1.0, rate_pkts_per_sec=150.0),
        Flow(flow_id=2, name="Interactive", weight=5.0, rate_pkts_per_sec=150.0)
    ]
    links = [
        Link(link_id=0, name="2.4GHz", bandwidth_mbps=20.0, base_delay_ms=2.0),
        Link(link_id=1, name="5GHz", bandwidth_mbps=100.0, base_delay_ms=0.5)
    ]
    channels = [
        WirelessChannel(bandwidth_mbps=20.0, base_propagation_ms=0.05, fer=0.02),
        WirelessChannel(bandwidth_mbps=100.0, base_propagation_ms=0.05, fer=0.01)
    ]
    return flows, links, channels


@pytest.mark.parametrize("scheduler_cls,kwargs", [
    (SingleLinkScheduler, {"primary_link_id": 1}),
    (DefaultFifoScheduler, {}),
    (RoundRobinScheduler, {}),
    (LowestLatencyScheduler, {}),
    (CongestionAwareScheduler, {}),
    (StaticPinningScheduler, {"flow_to_link_map": {1: 0, 2: 1}}),
    (RetransmissionSteeringScheduler, {}),
    (SASPScheduler, {}),
    (OracleScheduler, {})
])
def test_all_schedulers_executable(scheduler_cls, kwargs):
    """Verify that every scheduler completes a simulation run cleanly and produces valid metrics."""
    flows, links, channels = build_test_topology()
    scheduler = scheduler_cls(**kwargs)
    sim = MloSimulator(flows=flows, links=links, channels=channels, scheduler=scheduler, win_size=64, seed=42)
    receiver = sim.run(duration_ms=200.0)
    metrics = compute_metrics(receiver, duration_ms=200.0, scheduler_name=scheduler.name)
    
    assert metrics.delivered_count > 0
    assert metrics.aggregate_goodput_mbps > 0.0
    assert metrics.mean_e2e_delay_ms > 0.0
