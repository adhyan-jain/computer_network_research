"""
Targeted Phase 6 Ablation Campaign Runner.
Compares:
1. DefaultFIFO
2. CongestionAware (CALA)
3. MeanOnlySequencing (SASP with use_variance=False)
4. FullSASP (SASP with use_variance=True, Theorem 3 threshold root)

Evaluates:
- Priority ratio sweep (w2/w1 from 1 to 100) at near-equal link means (delta_mu = 0.1 ms).
- Mean delta sweep (delta_mu from 0.0 to 2.0 ms) at weight_ratio = 50.
- Variance ratio sweep (sigma2/sigma1 from 1 to 10) at equal means (delta_mu = 0.0 ms).

Strict statistical discipline:
- 30 paired random seeds (3000..3029) per point.
- Fresh environment per run (zero state mutation).
- All raw outputs preserved in experiments/ablation_phase6/raw_runs.csv.
- Summaries in experiments/ablation_phase6/summary_ablation.csv.
"""

import os
import sys
import csv
import math
import time
from typing import Dict, List, Any, Tuple
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.mlo_sim.core import Flow, Link
from src.mlo_sim.channel import WirelessChannel
from src.mlo_sim.schedulers import (
    BaseScheduler,
    DefaultFifoScheduler,
    CongestionAwareScheduler,
    SASPScheduler
)
from src.mlo_sim.simulator import MloSimulator
from src.mlo_sim.metrics import compute_metrics

OUTPUT_DIR = os.path.dirname(__file__)
RAW_CSV = os.path.join(OUTPUT_DIR, "raw_runs.csv")
SUMMARY_CSV = os.path.join(OUTPUT_DIR, "summary_ablation.csv")

NUM_SEEDS = 30
SEEDS = [3000 + i for i in range(NUM_SEEDS)]


def confidence_interval_95(data: List[float]) -> Tuple[float, float]:
    """Compute sample mean and 95% Student-t confidence interval half-width."""
    if not data:
        return 0.0, 0.0
    arr = np.array(data)
    mean = float(np.mean(arr))
    if len(arr) <= 1:
        return mean, 0.0
    std_err = float(np.std(arr, ddof=1) / math.sqrt(len(arr)))
    ci_half = 2.045 * std_err  # t_{0.025, 29} = 2.045
    return mean, ci_half


def run_single_simulation(
    sched_type: str,
    weight_ratio: float,
    delta_mu_ms: float,
    sigma2_mult: float,
    seed: int,
    duration_ms: float = 300.0
) -> Dict[str, Any]:
    """Runs a single simulation instance with freshly initialized objects."""
    flows = [
        Flow(flow_id=1, name="Bulk", weight=1.0, rate_pkts_per_sec=400.0),
        Flow(flow_id=2, name="Interactive", weight=weight_ratio, rate_pkts_per_sec=400.0)
    ]

    base_l1_ms = 1.0
    base_l2_ms = 1.0 + delta_mu_ms

    links = [
        Link(link_id=0, name="Link0", bandwidth_mbps=20.0, base_delay_ms=base_l1_ms),
        Link(link_id=1, name="Link1", bandwidth_mbps=20.0, base_delay_ms=base_l2_ms)
    ]
    links[0].contention_sigma_ms = 0.1
    links[1].contention_sigma_ms = 0.1 * sigma2_mult

    channels = [
        WirelessChannel(bandwidth_mbps=20.0, base_propagation_ms=base_l1_ms, fer=0.01),
        WirelessChannel(bandwidth_mbps=20.0, base_propagation_ms=base_l2_ms, fer=0.01)
    ]

    # Instantiate scheduler
    if sched_type == "DefaultFIFO":
        sched = DefaultFifoScheduler()
    elif sched_type == "CongestionAware":
        sched = CongestionAwareScheduler()
    elif sched_type == "MeanOnly":
        sched = SASPScheduler(enable_predictive_sequencing=True, use_variance=False)
    elif sched_type == "FullSASP":
        sched = SASPScheduler(enable_predictive_sequencing=True, use_variance=True)
    else:
        raise ValueError(f"Unknown scheduler type: {sched_type}")

    t0 = time.perf_counter_ns()
    sim = MloSimulator(flows, links, channels, sched, win_size=64, seed=seed)
    rx = sim.run(duration_ms=duration_ms)
    elapsed_ns = time.perf_counter_ns() - t0

    m = compute_metrics(rx, duration_ms=duration_ms, scheduler_name=sched_type)
    
    inter_m = m.per_flow.get(2)
    bulk_m = m.per_flow.get(1)

    return {
        "sched_type": sched_type,
        "weight_ratio": weight_ratio,
        "delta_mu_ms": delta_mu_ms,
        "sigma2_mult": sigma2_mult,
        "seed": seed,
        "weighted_cost": m.weighted_cross_blocking,
        "mean_cross_ms": m.mean_cross_blocking_ms,
        "interactive_cross_ms": inter_m.mean_cross_blocking_ms if inter_m else 0.0,
        "bulk_cross_ms": bulk_m.mean_cross_blocking_ms if bulk_m else 0.0,
        "interactive_p95_ms": inter_m.p95_e2e_delay_ms if inter_m else 0.0,
        "interactive_p99_ms": inter_m.p99_e2e_delay_ms if inter_m else 0.0,
        "goodput_mbps": m.aggregate_goodput_mbps,
        "total_packets": len(rx.delivered_packets),
        "wall_time_ms": elapsed_ns / 1_000_000.0
    }


def main():
    print("=== Phase 6 Targeted Ablation Campaign Starting ===")
    start_time = time.time()

    schedulers = ["DefaultFIFO", "CongestionAware", "MeanOnly", "FullSASP"]

    # 1. Regime A: Priority Ratio Sweep at near-equal link means (delta_mu = 0.1 ms)
    regime_a_ratios = [1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]
    
    # 2. Regime B: Mean Delta Sweep at fixed weight_ratio = 50.0
    regime_b_deltas = [0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]

    # 3. Regime C: Variance Ratio Sweep at equal means (delta_mu = 0.0 ms, weight_ratio = 50.0)
    regime_c_sigma_mults = [1.0, 2.0, 5.0, 10.0]

    raw_records: List[Dict[str, Any]] = []

    print("\n--- Running Regime A: Priority Ratio Sweep (delta_mu = 0.1 ms) ---")
    for wr in regime_a_ratios:
        print(f"  Testing weight_ratio = {wr}...")
        for sched in schedulers:
            for seed in SEEDS:
                rec = run_single_simulation(sched, weight_ratio=wr, delta_mu_ms=0.1, sigma2_mult=1.0, seed=seed)
                rec["regime"] = "RegimeA_Priority"
                raw_records.append(rec)

    print("\n--- Running Regime B: Mean Delta Sweep (weight_ratio = 50.0) ---")
    for d_mu in regime_b_deltas:
        print(f"  Testing delta_mu = {d_mu} ms...")
        for sched in schedulers:
            for seed in SEEDS:
                rec = run_single_simulation(sched, weight_ratio=50.0, delta_mu_ms=d_mu, sigma2_mult=1.0, seed=seed)
                rec["regime"] = "RegimeB_MeanDelta"
                raw_records.append(rec)

    print("\n--- Running Regime C: Variance Ratio Sweep (delta_mu = 0.0 ms, weight_ratio = 50.0) ---")
    for sm in regime_c_sigma_mults:
        print(f"  Testing sigma2_mult = {sm}...")
        for sched in schedulers:
            for seed in SEEDS:
                rec = run_single_simulation(sched, weight_ratio=50.0, delta_mu_ms=0.0, sigma2_mult=sm, seed=seed)
                rec["regime"] = "RegimeC_VarianceRatio"
                raw_records.append(rec)

    # Save raw records
    with open(RAW_CSV, mode="w", newline="") as f:
        fieldnames = list(raw_records[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(raw_records)
    print(f"\nSaved {len(raw_records)} raw runs to {RAW_CSV}")

    # Generate summary CSV
    print("Generating statistical summary...")
    summary_rows = []
    
    # Group by (regime, weight_ratio, delta_mu_ms, sigma2_mult, sched_type)
    from collections import defaultdict
    groups = defaultdict(list)
    for r in raw_records:
        k = (r["regime"], r["weight_ratio"], r["delta_mu_ms"], r["sigma2_mult"], r["sched_type"])
        groups[k].append(r)

    with open(SUMMARY_CSV, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "regime", "weight_ratio", "delta_mu_ms", "sigma2_mult", "scheduler",
            "mean_weighted_cost", "ci_weighted_cost",
            "mean_interactive_cross_ms", "ci_interactive_cross",
            "mean_bulk_cross_ms",
            "p95_interactive_ms", "p99_interactive_ms",
            "mean_goodput_mbps"
        ])

        for (reg, wr, d_mu, sm, sched), recs in sorted(groups.items()):
            costs = [x["weighted_cost"] for x in recs]
            ic_cross = [x["interactive_cross_ms"] for x in recs]
            bk_cross = [x["bulk_cross_ms"] for x in recs]
            p95s = [x["interactive_p95_ms"] for x in recs]
            p99s = [x["interactive_p99_ms"] for x in recs]
            gps = [x["goodput_mbps"] for x in recs]

            m_cost, ci_cost = confidence_interval_95(costs)
            m_ic, ci_ic = confidence_interval_95(ic_cross)

            writer.writerow([
                reg, wr, d_mu, sm, sched,
                f"{m_cost:.6f}", f"{ci_cost:.6f}",
                f"{m_ic:.6f}", f"{ci_ic:.6f}",
                f"{np.mean(bk_cross):.6f}",
                f"{np.mean(p95s):.4f}", f"{np.mean(p99s):.4f}",
                f"{np.mean(gps):.4f}"
            ])

    print(f"Summary written to {SUMMARY_CSV}")
    print(f"Campaign completed in {time.time() - start_time:.2f} seconds.")


if __name__ == "__main__":
    main()
