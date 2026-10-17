#!/usr/bin/env python3
"""
run_campaign.py - High-throughput Parallel Execution Runner for ns-3.47 MLO Validation

Executes:
1. Main Campaign (810 runs): 3 asymmetries x 3 loads x 30 seeds x 3 schedulers
2. Variance-Aware Ablation Campaign (810 runs): 3 variance ratios x 3 weight ratios x 30 seeds x 3 schedulers

Guarantees:
- Exactly reproducible seeds (seed=1..30)
- Paired evaluation across schedulers (DefaultFIFO, MeanOnly, FullSASP)
- Thread-safe CSV output with pre-registered schema
- Zero run truncation
"""

import os
import sys
import argparse
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

NS3_BINARY = "/home/adhyan/Desktop/wifi7_mlo_hol/validation/ns3/ns-3.47/build/scratch/mlo-experiment/ns3.47-mlo-experiment-optimized"

CSV_HEADER = (
    "run_id,seed,scheduler,asymmetry,offered_load,weight_ratio,variance_ratio,"
    "sim_time_s,ls_sent,ls_rcvd,bulk_sent,bulk_rcvd,ls_pdr,bulk_pdr,"
    "mean_cross_blocking_ms,ls_delay_median_ms,ls_delay_p95_ms,ls_delay_p99_ms,"
    "ls_goodput_kbps,bulk_goodput_mbps,total_goodput_mbps,mac_retries,mac_drops,"
    "total_decisions,inverted_decisions,inversion_rate_pct\n"
)

def run_single(task):
    """Executes a single simulation run and returns CSV row."""
    run_id, seed, sched, asym, load, w_ratio, v_ratio, sim_time = task
    temp_csv = f"/tmp/ns3_run_{run_id}_{os.getpid()}_{time.time_ns()}.csv"
    
    cmd = [
        NS3_BINARY,
        f"--run={run_id}",
        f"--seed={seed}",
        f"--scheduler={sched}",
        f"--asymmetry={asym}",
        f"--offeredLoad={load}",
        f"--weightRatio={w_ratio}",
        f"--varianceRatio={v_ratio}",
        f"--simulationTime={sim_time}",
        f"--csvOutput={temp_csv}"
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
        raise RuntimeError(f"Run {run_id} failed (code {res.returncode}):\n{res.stderr}\n{res.stdout}")
        
    csv_line = ""
    if os.path.exists(temp_csv):
        with open(temp_csv, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
            if len(lines) >= 2:
                csv_line = lines[-1]
            elif len(lines) == 1 and not lines[0].startswith("run_id"):
                csv_line = lines[0]
        os.remove(temp_csv)
        
    if not csv_line:
        raise RuntimeError(f"Run {run_id} produced no CSV output line!")
        
    return run_id, csv_line

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["main", "ablation"], required=True)
    parser.add_argument("--workers", type=int, default=14)
    parser.add_argument("--sim-time", type=float, default=2.0)
    args = parser.parse_args()

    tasks = []
    run_id = 1

    if args.mode == "main":
        out_csv = "/home/adhyan/Desktop/wifi7_mlo_hol/validation/ns3/results/main_campaign_raw.csv"
        # 3 Asymmetries x 3 Loads x 30 Seeds x 3 Schedulers = 810 runs
        asymmetries = ["A0", "A1", "A2"]
        loads = ["L0", "L1", "L2"]
        schedulers = [0, 1, 2] # 0=FIFO, 1=MeanOnly, 2=FullSASP
        seeds = list(range(1, 31))
        
        for asym in asymmetries:
            for load in loads:
                for seed in seeds:
                    for sched in schedulers:
                        tasks.append((run_id, seed, sched, asym, load, 10.0, 1.0, args.sim_time))
                        run_id += 1

    elif args.mode == "ablation":
        out_csv = "/home/adhyan/Desktop/wifi7_mlo_hol/validation/ns3/results/variance_ablation_raw.csv"
        # 3 Variance Ratios x 3 Weight Ratios x 30 Seeds x 3 Schedulers = 810 runs
        variance_ratios = [1.0, 2.0, 4.0]
        weight_ratios = [1.0, 10.0, 50.0]
        schedulers = [0, 1, 2]
        seeds = list(range(1, 31))
        asym = "A2"
        load = "L2"
        
        for v_ratio in variance_ratios:
            for w_ratio in weight_ratios:
                for seed in seeds:
                    for sched in schedulers:
                        tasks.append((run_id, seed, sched, asym, load, w_ratio, v_ratio, args.sim_time))
                        run_id += 1

    total_runs = len(tasks)
    print(f"=== STARTING {args.mode.upper()} CAMPAIGN ({total_runs} RUNS, {args.workers} WORKERS) ===")
    print(f"Destination CSV: {out_csv}")
    
    with open(out_csv, "w") as f:
        f.write(CSV_HEADER)

    start_time = time.time()
    completed = 0
    results = {}

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_single, t): t[0] for t in tasks}
        
        for future in as_completed(futures):
            rid = futures[future]
            try:
                r_id, line = future.result()
                results[r_id] = line
                completed += 1
                if completed % 50 == 0 or completed == total_runs:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed
                    eta = (total_runs - completed) / rate if rate > 0 else 0
                    print(f"Progress: [{completed}/{total_runs}] ({completed/total_runs*100:.1f}%) | "
                          f"Elapsed: {elapsed:.1f}s | Rate: {rate:.1f} runs/s | ETA: {eta:.1f}s")
            except Exception as e:
                print(f"ERROR in run {rid}: {e}", file=sys.stderr)
                sys.exit(1)

    # Write sorted by run_id
    with open(out_csv, "a") as f:
        for r_id in sorted(results.keys()):
            f.write(results[r_id] + "\n")

    total_elapsed = time.time() - start_time
    print(f"=== COMPLETED {args.mode.upper()} CAMPAIGN: {completed} runs in {total_elapsed:.1f}s ({total_elapsed/60:.2f} min) ===")

if __name__ == "__main__":
    main()
