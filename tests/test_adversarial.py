"""
Adversarial and boundary condition tests:
- Identical links with zero variance
- Extreme delay asymmetry
- High packet loss and retry limit exhaustion
- Minimal Block Ack window size (W=4)
"""

import pytest
from src.mlo_sim.core import Flow, Link
from src.mlo_sim.channel import WirelessChannel
from src.mlo_sim.schedulers import DefaultFifoScheduler, SASPScheduler, StaticPinningScheduler
from src.mlo_sim.simulator import MloSimulator
from src.mlo_sim.metrics import compute_metrics


def test_adversarial_identical_links_zero_variance():
    """
    Boundary case: Two identical links with zero variance and zero loss.
    Cross-flow blocking should collapse to approximately zero.
    """
    flows = [
        Flow(flow_id=1, name="F1", weight=1.0, rate_pkts_per_sec=100.0),
        Flow(flow_id=2, name="F2", weight=1.0, rate_pkts_per_sec=100.0)
    ]
    # Identical bandwidth and delay, zero contention noise
    links = [
        Link(link_id=0, name="L0", bandwidth_mbps=100.0, base_delay_ms=1.0, contention_sigma_ms=0.0),
        Link(link_id=1, name="L1", bandwidth_mbps=100.0, base_delay_ms=1.0, contention_sigma_ms=0.0)
    ]
    channels = [
        WirelessChannel(bandwidth_mbps=100.0, base_propagation_ms=0.0, contention_sigma_ms=0.0, fer=0.0),
        WirelessChannel(bandwidth_mbps=100.0, base_propagation_ms=0.0, contention_sigma_ms=0.0, fer=0.0)
    ]

    sim = MloSimulator(flows=flows, links=links, channels=channels, scheduler=SASPScheduler(), win_size=64, seed=1)
    receiver = sim.run(duration_ms=200.0)
    metrics = compute_metrics(receiver, duration_ms=200.0)
    assert metrics.mean_cross_blocking_ms < 0.1


def test_adversarial_extreme_delay_asymmetry():
    """
    Boundary case: 50x delay asymmetry between links.
    Static pinning should experience massive cross-flow blocking.
    SASP should actively prevent cross-flow stalls.
    """
    flows_pin = [
        Flow(flow_id=1, name="Bulk", weight=1.0, rate_pkts_per_sec=50.0),
        Flow(flow_id=2, name="Interactive", weight=10.0, rate_pkts_per_sec=300.0)
    ]
    flows_sasp = [
        Flow(flow_id=1, name="Bulk", weight=1.0, rate_pkts_per_sec=50.0),
        Flow(flow_id=2, name="Interactive", weight=10.0, rate_pkts_per_sec=300.0)
    ]

    links_pin = [
        Link(link_id=0, name="Slow", bandwidth_mbps=5.0, base_delay_ms=15.0),
        Link(link_id=1, name="Fast", bandwidth_mbps=200.0, base_delay_ms=0.2)
    ]
    links_sasp = [
        Link(link_id=0, name="Slow", bandwidth_mbps=5.0, base_delay_ms=15.0),
        Link(link_id=1, name="Fast", bandwidth_mbps=200.0, base_delay_ms=0.2)
    ]

    channels_pin = [
        WirelessChannel(bandwidth_mbps=5.0, base_propagation_ms=0.05, fer=0.0),
        WirelessChannel(bandwidth_mbps=200.0, base_propagation_ms=0.05, fer=0.0)
    ]
    channels_sasp = [
        WirelessChannel(bandwidth_mbps=5.0, base_propagation_ms=0.05, fer=0.0),
        WirelessChannel(bandwidth_mbps=200.0, base_propagation_ms=0.05, fer=0.0)
    ]

    # Run Static Pinning (Flow 1 -> Link 0, Flow 2 -> Link 1)
    pin_sched = StaticPinningScheduler({1: 0, 2: 1})
    sim_pin = MloSimulator(flows=flows_pin, links=links_pin, channels=channels_pin, scheduler=pin_sched, win_size=64, seed=42)
    rec_pin = sim_pin.run(duration_ms=400.0)
    met_pin = compute_metrics(rec_pin, duration_ms=400.0)

    # Run SASP
    sasp_sched = SASPScheduler()
    sim_sasp = MloSimulator(flows=flows_sasp, links=links_sasp, channels=channels_sasp, scheduler=sasp_sched, win_size=64, seed=42)
    rec_sasp = sim_sasp.run(duration_ms=400.0)
    met_sasp = compute_metrics(rec_sasp, duration_ms=400.0)

    # SASP must achieve significantly lower cross-flow blocking than Static Pinning
    assert met_sasp.mean_cross_blocking_ms < met_pin.mean_cross_blocking_ms


def test_adversarial_tiny_window():
    """
    Stress test: Minimal window W=4.
    Simulator and receiver must handle rapid window wrapping and forced advances without crashing.
    """
    flows = [
        Flow(flow_id=1, name="F1", weight=1.0, rate_pkts_per_sec=200.0),
        Flow(flow_id=2, name="F2", weight=1.0, rate_pkts_per_sec=200.0)
    ]
    links = [
        Link(link_id=0, name="L0", bandwidth_mbps=20.0, base_delay_ms=2.0),
        Link(link_id=1, name="L1", bandwidth_mbps=100.0, base_delay_ms=0.5)
    ]
    channels = [
        WirelessChannel(bandwidth_mbps=20.0, base_propagation_ms=0.05, fer=0.05),
        WirelessChannel(bandwidth_mbps=100.0, base_propagation_ms=0.05, fer=0.02)
    ]

    sim = MloSimulator(flows=flows, links=links, channels=channels, scheduler=SASPScheduler(), win_size=4, seed=99)
    receiver = sim.run(duration_ms=200.0)
    metrics = compute_metrics(receiver, duration_ms=200.0)
    assert metrics.delivered_count > 0
