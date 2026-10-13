"""
Experiment Campaign Orchestration Script.
Executes EXP-01 through EXP-07 across 30 independent random seeds.
Saves raw per-run results in experiments/raw/ and summarized statistics in experiments/results/.
"""

import os
import csv
import math
import time
from typing import Dict, List, Any
import numpy as np

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
from src.mlo_sim.metrics import compute_metrics, SimulationMetrics

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "raw")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

NUM_SEEDS = 30
BASE_SEEDS = [1000 + i for i in range(NUM_SEEDS)]


def confidence_interval_95(data: List[float]) -> Tuple[float, float]:
    """Compute mean and 95% Student-t confidence interval half-width."""
    if not data:
        return 0.0, 0.0
    arr = np.array(data)
    mean = float(np.mean(arr))
    if len(arr) <= 1:
        return mean, 0.0
    std_err = float(np.std(arr, ddof=1) / math.sqrt(len(arr)))
    ci_half = 2.045 * std_err  # t_{0.025, 29} = 2.045
    return mean, ci_half


def run_experiment_1_link_asymmetry():
    """
    EXP-01: Link Asymmetry Sweep.
    Varies delay asymmetry delta = mu_1 - mu_2 by adjusting Link 0 base delay.
    Tests Hypotheses H1 and H3.
    """
    print("--- Running EXP-01: Link Asymmetry Sweep ---")
    delta_values = [0.2, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]  # ms
    schedulers = [
        ("SingleLink", lambda: SingleLinkScheduler(primary_link_id=1)),
        ("DefaultFIFO", lambda: DefaultFifoScheduler()),
        ("RoundRobin", lambda: RoundRobinScheduler()),
        ("LowestLatency", lambda: LowestLatencyScheduler()),
        ("CongestionAware", lambda: CongestionAwareScheduler()),
        ("StaticPinning", lambda: StaticPinningScheduler({1: 0, 2: 1})),
        ("RetransmissionSteering", lambda: RetransmissionSteeringScheduler()),
        ("SASP", lambda: SASPScheduler(enable_predictive_sequencing=True)),
        ("Oracle", lambda: OracleScheduler())
    ]

    summary_file = os.path.join(RESULTS_DIR, "exp1_link_asymmetry.csv")
    with open(summary_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "delta_ms", "scheduler",
            "mean_cross_blocking_ms", "ci_cross_blocking",
            "mean_self_blocking_ms", "ci_self_blocking",
            "mean_total_reorder_ms", "ci_total_reorder",
            "mean_goodput_mbps", "ci_goodput",
            "p95_e2e_delay_ms", "p99_e2e_delay_ms"
        ])

        for delta in delta_values:
            print(f"  Evaluating delta = {delta} ms...")
            for sched_name, sched_factory in schedulers:
                cross_list, self_list, total_list, goodput_list = [], [], [], []
                p95_list, p99_list = [], []

                for seed in BASE_SEEDS:
                    flows = [
                        Flow(flow_id=1, name="Bulk", weight=1.0, rate_pkts_per_sec=200.0),
                        Flow(flow_id=2, name="Interactive", weight=1.0, rate_pkts_per_sec=200.0)
                    ]
                    # Link 1 fast (5 GHz / 6 GHz): 100 Mbps, 0.5 ms
                    # Link 0 slow: base delay = 0.5 + delta
                    links = [
                        Link(link_id=0, name="SlowLink", bandwidth_mbps=20.0, base_delay_ms=0.5 + delta),
                        Link(link_id=1, name="FastLink", bandwidth_mbps=100.0, base_delay_ms=0.5)
                    ]
                    channels = [
                        WirelessChannel(bandwidth_mbps=20.0, base_propagation_ms=0.5 + delta, fer=0.02),
                        WirelessChannel(bandwidth_mbps=100.0, base_propagation_ms=0.5, fer=0.01)
                    ]

                    sim = MloSimulator(
                        flows=flows, links=links, channels=channels,
                        scheduler=sched_factory(), win_size=64, seed=seed
                    )
                    receiver = sim.run(duration_ms=400.0)
                    m = compute_metrics(receiver, duration_ms=400.0, scheduler_name=sched_name)

                    cross_list.append(m.mean_cross_blocking_ms)
                    self_list.append(m.mean_self_blocking_ms)
                    total_list.append(m.mean_reorder_delay_ms)
                    goodput_list.append(m.aggregate_goodput_mbps)
                    p95_list.append(m.p95_e2e_delay_ms)
                    p99_list.append(m.p99_e2e_delay_ms)

                m_cross, ci_cross = confidence_interval_95(cross_list)
                m_self, ci_self = confidence_interval_95(self_list)
                m_tot, ci_tot = confidence_interval_95(total_list)
                m_gp, ci_gp = confidence_interval_95(goodput_list)

                writer.writerow([
                    delta, sched_name,
                    f"{m_cross:.4f}", f"{ci_cross:.4f}",
                    f"{m_self:.4f}", f"{ci_self:.4f}",
                    f"{m_tot:.4f}", f"{ci_tot:.4f}",
                    f"{m_gp:.4f}", f"{ci_gp:.4f}",
                    f"{np.mean(p95_list):.4f}", f"{np.mean(p99_list):.4f}"
                ])


def run_experiment_2_ba_window_collapse():
    """
    EXP-02: Multi-Link BA Window Collapse Boundary.
    Evaluates throughput and tail latency across normalized arrival rate lambda / lambda*,
    where lambda* = W / delta (Theorem 2).
    """
    print("--- Running EXP-02: BA Window Collapse Boundary ---")
    W = 64
    delta = 1.0  # ms
    # lambda* = W / delta = 64 / 1.0 ms = 64 pkts/ms = 64,000 pkts/sec
    # We test normalized loads relative to link capacity
    normalized_loads = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0]
    
    summary_file = os.path.join(RESULTS_DIR, "exp2_window_collapse.csv")
    with open(summary_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "norm_load", "scheduler",
            "mean_goodput_mbps", "ci_goodput",
            "mean_cross_blocking_ms", "ci_cross",
            "p99_e2e_delay_ms", "forced_advances"
        ])

        for load in normalized_loads:
            # Interactive arrival rate scaled by load
            rate_fast = 300.0 * load
            for sched_name, sched_factory in [
                ("DefaultFIFO", lambda: DefaultFifoScheduler()),
                ("StaticPinning", lambda: StaticPinningScheduler({1: 0, 2: 1})),
                ("CongestionAware", lambda: CongestionAwareScheduler()),
                ("SASP", lambda: SASPScheduler(enable_predictive_sequencing=True))
            ]:
                goodput_list, cross_list, p99_list, adv_list = [], [], [], []
                for seed in BASE_SEEDS:
                    flows = [
                        Flow(flow_id=1, name="Bulk", weight=1.0, rate_pkts_per_sec=100.0),
                        Flow(flow_id=2, name="Interactive", weight=1.0, rate_pkts_per_sec=rate_fast)
                    ]
                    links = [
                        Link(link_id=0, name="SlowLink", bandwidth_mbps=10.0, base_delay_ms=1.5),
                        Link(link_id=1, name="FastLink", bandwidth_mbps=100.0, base_delay_ms=0.5)
                    ]
                    channels = [
                        WirelessChannel(bandwidth_mbps=10.0, base_propagation_ms=1.5, fer=0.02),
                        WirelessChannel(bandwidth_mbps=100.0, base_propagation_ms=0.5, fer=0.01)
                    ]

                    sim = MloSimulator(
                        flows=flows, links=links, channels=channels,
                        scheduler=sched_factory(), win_size=W, seed=seed
                    )
                    receiver = sim.run(duration_ms=400.0)
                    m = compute_metrics(receiver, duration_ms=400.0, scheduler_name=sched_name)

                    goodput_list.append(m.aggregate_goodput_mbps)
                    cross_list.append(m.mean_cross_blocking_ms)
                    p99_list.append(m.p99_e2e_delay_ms)
                    adv_list.append(m.window_advances_forced)

                m_gp, ci_gp = confidence_interval_95(goodput_list)
                m_cr, ci_cr = confidence_interval_95(cross_list)
                writer.writerow([
                    load, sched_name,
                    f"{m_gp:.4f}", f"{ci_gp:.4f}",
                    f"{m_cr:.4f}", f"{ci_cr:.4f}",
                    f"{np.mean(p99_list):.4f}", f"{np.mean(adv_list):.2f}"
                ])


def run_experiment_3_priority_heterogeneity():
    """
    EXP-03: Flow Priority Heterogeneity.
    Varies interactive weight w_2 while keeping bulk weight w_1 = 1.0 (Theorem 3).
    Tests Hypothesis H4.
    """
    print("--- Running EXP-03: Priority Heterogeneity ---")
    weight_ratios = [1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
    summary_file = os.path.join(RESULTS_DIR, "exp3_priority_heterogeneity.csv")

    with open(summary_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "weight_ratio", "scheduler",
            "bulk_cross_ms", "interactive_cross_ms",
            "weighted_cross_ms", "ci_weighted_cross",
            "interactive_p95_ms", "interactive_p99_ms"
        ])

        for ratio in weight_ratios:
            for sched_name, sched_factory in [
                ("DefaultFIFO", lambda: DefaultFifoScheduler()),
                ("CongestionAware", lambda: CongestionAwareScheduler()),
                ("SASP", lambda: SASPScheduler(enable_predictive_sequencing=True))
            ]:
                bulk_cross, inter_cross, weighted_cross = [], [], []
                inter_p95, inter_p99 = [], []

                for seed in BASE_SEEDS:
                    flows = [
                        Flow(flow_id=1, name="Bulk", weight=1.0, rate_pkts_per_sec=200.0),
                        Flow(flow_id=2, name="Interactive", weight=ratio, rate_pkts_per_sec=200.0)
                    ]
                    links = [
                        Link(link_id=0, name="SlowLink", bandwidth_mbps=20.0, base_delay_ms=2.5),
                        Link(link_id=1, name="FastLink", bandwidth_mbps=100.0, base_delay_ms=0.5)
                    ]
                    channels = [
                        WirelessChannel(bandwidth_mbps=20.0, base_propagation_ms=2.5, fer=0.02),
                        WirelessChannel(bandwidth_mbps=100.0, base_propagation_ms=0.5, fer=0.01)
                    ]

                    sim = MloSimulator(
                        flows=flows, links=links, channels=channels,
                        scheduler=sched_factory(), win_size=64, seed=seed
                    )
                    receiver = sim.run(duration_ms=400.0)
                    m = compute_metrics(receiver, duration_ms=400.0, scheduler_name=sched_name)

                    f1_m = m.per_flow.get(1)
                    f2_m = m.per_flow.get(2)
                    if f1_m and f2_m:
                        bulk_cross.append(f1_m.mean_cross_blocking_ms)
                        inter_cross.append(f2_m.mean_cross_blocking_ms)
                        inter_p95.append(f2_m.p95_e2e_delay_ms)
                        inter_p99.append(f2_m.p99_e2e_delay_ms)
                    weighted_cross.append(m.weighted_cross_blocking)

                m_wc, ci_wc = confidence_interval_95(weighted_cross)
                writer.writerow([
                    ratio, sched_name,
                    f"{np.mean(bulk_cross):.4f}", f"{np.mean(inter_cross):.4f}",
                    f"{m_wc:.4f}", f"{ci_wc:.4f}",
                    f"{np.mean(inter_p95):.4f}", f"{np.mean(inter_p99):.4f}"
                ])


def run_experiment_4_contention_and_loss():
    """
    EXP-04: Channel Contention and Frame Error Rate Sweep.
    Varies frame error rate p in [0.0, 0.25] and contention noise.
    Tests Hypothesis H3 under lossy environments.
    """
    print("--- Running EXP-04: Contention and Frame Loss Sweep ---")
    fer_values = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]
    summary_file = os.path.join(RESULTS_DIR, "exp4_contention_loss.csv")

    with open(summary_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "fer", "scheduler",
            "mean_cross_blocking_ms", "ci_cross",
            "goodput_mbps", "ci_goodput",
            "total_retries"
        ])

        for fer in fer_values:
            for sched_name, sched_factory in [
                ("DefaultFIFO", lambda: DefaultFifoScheduler()),
                ("RetransmissionSteering", lambda: RetransmissionSteeringScheduler()),
                ("CongestionAware", lambda: CongestionAwareScheduler()),
                ("SASP", lambda: SASPScheduler(enable_predictive_sequencing=True))
            ]:
                cross_list, gp_list, retries_list = [], [], []

                for seed in BASE_SEEDS:
                    flows = [
                        Flow(flow_id=1, name="Bulk", weight=1.0, rate_pkts_per_sec=200.0),
                        Flow(flow_id=2, name="Interactive", weight=3.0, rate_pkts_per_sec=200.0)
                    ]
                    links = [
                        Link(link_id=0, name="SlowLink", bandwidth_mbps=20.0, base_delay_ms=2.0),
                        Link(link_id=1, name="FastLink", bandwidth_mbps=100.0, base_delay_ms=0.5)
                    ]
                    # Link 0 suffers higher FER
                    channels = [
                        WirelessChannel(bandwidth_mbps=20.0, base_propagation_ms=2.0, fer=fer * 1.5, burst_prob=0.02),
                        WirelessChannel(bandwidth_mbps=100.0, base_propagation_ms=0.5, fer=fer, burst_prob=0.01)
                    ]

                    sim = MloSimulator(
                        flows=flows, links=links, channels=channels,
                        scheduler=sched_factory(), win_size=64, seed=seed
                    )
                    receiver = sim.run(duration_ms=400.0)
                    m = compute_metrics(receiver, duration_ms=400.0, scheduler_name=sched_name)

                    cross_list.append(m.mean_cross_blocking_ms)
                    gp_list.append(m.aggregate_goodput_mbps)
                    total_ret = sum(l.total_retries for l in sim.links.values())
                    retries_list.append(total_ret)

                m_cr, ci_cr = confidence_interval_95(cross_list)
                m_gp, ci_gp = confidence_interval_95(gp_list)
                writer.writerow([
                    fer, sched_name,
                    f"{m_cr:.4f}", f"{ci_cr:.4f}",
                    f"{m_gp:.4f}", f"{ci_gp:.4f}",
                    f"{np.mean(retries_list):.1f}"
                ])


def run_experiment_5_multi_link_scaling():
    """
    EXP-05: Multi-Link and Multi-Flow Scalability.
    Evaluates 2, 3, and 4 links across 2, 4, and 8 flows.
    Measures scheduling computation overhead in microseconds.
    """
    print("--- Running EXP-05: Multi-Link Scalability ---")
    configs = [
        (2, 2), (2, 4), (2, 8),
        (3, 2), (3, 4), (3, 8),
        (4, 2), (4, 4), (4, 8)
    ]
    summary_file = os.path.join(RESULTS_DIR, "exp5_scalability.csv")

    with open(summary_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "num_links", "num_flows", "scheduler",
            "mean_cross_blocking_ms", "goodput_mbps",
            "decision_overhead_us"
        ])

        for num_links, num_flows in configs:
            flows = [
                Flow(flow_id=i+1, name=f"F{i+1}", weight=1.0 + (i % 3), rate_pkts_per_sec=100.0)
                for i in range(num_flows)
            ]
            links = [
                Link(link_id=k, name=f"Link{k}", bandwidth_mbps=20.0 + k * 30.0, base_delay_ms=0.5 + (3 - k) * 0.5)
                for k in range(num_links)
            ]
            channels = [
                WirelessChannel(bandwidth_mbps=l.bandwidth_mbps, base_propagation_ms=l.base_delay_ms, fer=0.01 * (k + 1))
                for k, l in enumerate(links)
            ]

            for sched_name, sched_factory in [
                ("DefaultFIFO", lambda: DefaultFifoScheduler()),
                ("SASP", lambda: SASPScheduler(enable_predictive_sequencing=True))
            ]:
                overhead_list = []
                sched = sched_factory()
                
                # Benchmark scheduling decision overhead
                start_t = time.perf_counter()
                sim = MloSimulator(
                    flows=flows, links=links, channels=channels,
                    scheduler=sched, win_size=64, seed=42
                )
                receiver = sim.run(duration_ms=400.0)
                elapsed = time.perf_counter() - start_t
                
                m = compute_metrics(receiver, duration_ms=400.0, scheduler_name=sched_name)
                # Compute overhead per scheduling decision in microseconds
                num_decisions = max(1, m.delivered_count)
                overhead_us = (elapsed / num_decisions) * 1e6

                writer.writerow([
                    num_links, num_flows, sched_name,
                    f"{m.mean_cross_blocking_ms:.4f}",
                    f"{m.aggregate_goodput_mbps:.4f}",
                    f"{overhead_us:.2f}"
                ])


def run_experiment_6_estimation_robustness():
    """
    EXP-06: Sensitivity to Parameter Estimation Error.
    Injects bias into link delay estimates: hat_sigma = (1 + eps) * sigma.
    Tests Hypothesis H5.
    """
    print("--- Running EXP-06: Estimation Error Robustness ---")
    error_biases = [-0.5, -0.3, -0.1, 0.0, 0.1, 0.3, 0.5]
    summary_file = os.path.join(RESULTS_DIR, "exp6_estimation_robustness.csv")

    with open(summary_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "bias_factor",
            "sasp_cross_blocking_ms", "ci_sasp_cross",
            "fifo_cross_blocking_ms", "relative_advantage_pct"
        ])

        for bias in error_biases:
            sasp_cross = []
            fifo_cross = []

            for seed in BASE_SEEDS:
                flows = [
                    Flow(flow_id=1, name="Bulk", weight=1.0, rate_pkts_per_sec=200.0),
                    Flow(flow_id=2, name="Interactive", weight=5.0, rate_pkts_per_sec=200.0)
                ]
                links = [
                    Link(link_id=0, name="SlowLink", bandwidth_mbps=20.0, base_delay_ms=2.5),
                    Link(link_id=1, name="FastLink", bandwidth_mbps=100.0, base_delay_ms=0.5)
                ]
                channels = [
                    WirelessChannel(bandwidth_mbps=20.0, base_propagation_ms=2.5, fer=0.02),
                    WirelessChannel(bandwidth_mbps=100.0, base_propagation_ms=0.5, fer=0.01)
                ]

                # SASP with artificially biased link variance estimator
                sasp = SASPScheduler()
                for l in links:
                    l.estimated_std_ms *= (1.0 + bias)

                sim_sasp = MloSimulator(flows=flows, links=links, channels=channels, scheduler=sasp, win_size=64, seed=seed)
                m_sasp = compute_metrics(sim_sasp.run(duration_ms=400.0), 400.0)
                sasp_cross.append(m_sasp.mean_cross_blocking_ms)

                # Baseline FIFO
                sim_fifo = MloSimulator(flows=flows, links=links, channels=channels, scheduler=DefaultFifoScheduler(), win_size=64, seed=seed)
                m_fifo = compute_metrics(sim_fifo.run(duration_ms=400.0), 400.0)
                fifo_cross.append(m_fifo.mean_cross_blocking_ms)

            m_s, ci_s = confidence_interval_95(sasp_cross)
            m_f, _ = confidence_interval_95(fifo_cross)
            rel_gain = ((m_f - m_s) / m_f) * 100.0 if m_f > 0 else 0.0

            writer.writerow([
                bias,
                f"{m_s:.4f}", f"{ci_s:.4f}",
                f"{m_f:.4f}", f"{rel_gain:.2f}"
            ])


def run_experiment_7_ablation_study():
    """
    EXP-07: Algorithmic Ablation Study.
    Isolates each component:
    (1) Baseline FIFO
    (2) Congestion-Aware Link Dispatch without Sequencing
    (3) Mean-only Sequencing (ignoring variance)
    (4) Full SASP (Theorem 3 Threshold Engine)
    """
    print("--- Running EXP-07: Algorithmic Ablation Study ---")
    summary_file = os.path.join(RESULTS_DIR, "exp7_ablation_study.csv")

    variants = [
        ("1_DefaultFIFO", lambda: DefaultFifoScheduler()),
        ("2_DispatchOnly", lambda: CongestionAwareScheduler()),
        ("3_MeanOnlySequencing", lambda: SASPScheduler(enable_predictive_sequencing=False)),
        ("4_FullSASP", lambda: SASPScheduler(enable_predictive_sequencing=True))
    ]

    with open(summary_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "variant",
            "mean_cross_blocking_ms", "ci_cross",
            "weighted_cost", "ci_weighted",
            "interactive_p95_ms", "interactive_p99_ms"
        ])

        for v_name, v_factory in variants:
            cross_list, weight_list, p95_list, p99_list = [], [], [], []

            for seed in BASE_SEEDS:
                flows = [
                    Flow(flow_id=1, name="Bulk", weight=1.0, rate_pkts_per_sec=200.0),
                    Flow(flow_id=2, name="Interactive", weight=10.0, rate_pkts_per_sec=200.0)
                ]
                links = [
                    Link(link_id=0, name="SlowLink", bandwidth_mbps=20.0, base_delay_ms=3.0),
                    Link(link_id=1, name="FastLink", bandwidth_mbps=100.0, base_delay_ms=0.5)
                ]
                channels = [
                    WirelessChannel(bandwidth_mbps=20.0, base_propagation_ms=3.0, fer=0.02),
                    WirelessChannel(bandwidth_mbps=100.0, base_propagation_ms=0.5, fer=0.01)
                ]

                sim = MloSimulator(flows=flows, links=links, channels=channels, scheduler=v_factory(), win_size=64, seed=seed)
                m = compute_metrics(sim.run(duration_ms=400.0), 400.0, scheduler_name=v_name)

                cross_list.append(m.mean_cross_blocking_ms)
                weight_list.append(m.weighted_cross_blocking)
                f2_m = m.per_flow.get(2)
                if f2_m:
                    p95_list.append(f2_m.p95_e2e_delay_ms)
                    p99_list.append(f2_m.p99_e2e_delay_ms)

            m_cr, ci_cr = confidence_interval_95(cross_list)
            m_wc, ci_wc = confidence_interval_95(weight_list)
            writer.writerow([
                v_name,
                f"{m_cr:.4f}", f"{ci_cr:.4f}",
                f"{m_wc:.4f}", f"{ci_wc:.4f}",
                f"{np.mean(p95_list):.4f}", f"{np.mean(p99_list):.4f}"
            ])


if __name__ == "__main__":
    t0 = time.time()
    print("Starting Comprehensive MLO Experimental Campaign...")
    run_experiment_1_link_asymmetry()
    run_experiment_2_ba_window_collapse()
    run_experiment_3_priority_heterogeneity()
    run_experiment_4_contention_and_loss()
    run_experiment_5_multi_link_scaling()
    run_experiment_6_estimation_robustness()
    run_experiment_7_ablation_study()
    print(f"Experimental Campaign Completed Successfully in {time.time() - t0:.2f} seconds.")
