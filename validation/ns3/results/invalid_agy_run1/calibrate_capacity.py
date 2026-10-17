#!/usr/bin/env python3
"""
calibrate_capacity.py - Calibrate Neutral Capacity (C_ref) and Asymmetry Levels (A0, A1, A2)
"""

import subprocess
import os
import re

NS3_BIN = "/home/adhyan/Desktop/wifi7_mlo_hol/validation/ns3/ns-3.47/build/scratch/mlo-experiment/ns3.47-mlo-experiment-optimized"

def run_sim(asym, load, sched=0, sim_time=2.0):
    cmd = [
        NS3_BIN,
        f"--asymmetry={asym}",
        f"--offeredLoad={load}",
        f"--scheduler={sched}",
        f"--simulationTime={sim_time}",
        "--seed=1",
        "--run=1"
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert res.returncode == 0, f"Error running {cmd}: {res.stderr}"
    
    # Parse output: e.g. Tput=15.2395 Mbps
    m_tp = re.search(r"Tput=([0-9\.]+)\s*Mbps", res.stdout)
    tput = float(m_tp.group(1)) if m_tp else 0.0
    
    m_cb = re.search(r"Cross-Blocking:\s*([0-9\.]+)\s*ms", res.stdout)
    cb = float(m_cb.group(1)) if m_cb else 0.0
    
    return {"tput": tput, "cross_blocking": cb, "stdout": res.stdout}

def main():
    print("=== CALIBRATING NEUTRAL CAPACITY AND ASYMMETRY RATIOS ===")
    
    # 1. Measure reference saturation throughput on symmetric A0
    res_a0 = run_sim("A0", "L2", sched=0)
    c_ref = res_a0["tput"]
    print(f"Symmetric Link Reference Capacity (A0, L2): {c_ref:.3f} Mbps")
    
    # 2. Check asymmetry levels under L2 load
    res_a1 = run_sim("A1", "L2", sched=0)
    res_a2 = run_sim("A2", "L2", sched=0)
    
    print(f"Throughput A0 (Symmetric): {res_a0['tput']:.3f} Mbps, Cross-Blocking: {res_a0['cross_blocking']:.4f} ms")
    print(f"Throughput A1 (Moderate):  {res_a1['tput']:.3f} Mbps, Cross-Blocking: {res_a1['cross_blocking']:.4f} ms")
    print(f"Throughput A2 (Strong):    {res_a2['tput']:.3f} Mbps, Cross-Blocking: {res_a2['cross_blocking']:.4f} ms")
    
    report_path = "/home/adhyan/Desktop/wifi7_mlo_hol/validation/ns3/logs/calibration_report.txt"
    with open(report_path, "w") as f:
        f.write(f"Reference Capacity C_ref: {c_ref:.3f} Mbps\n")
        f.write(f"A0: {res_a0['tput']:.3f} Mbps, Cross-Blocking: {res_a0['cross_blocking']:.4f} ms\n")
        f.write(f"A1: {res_a1['tput']:.3f} Mbps, Cross-Blocking: {res_a1['cross_blocking']:.4f} ms\n")
        f.write(f"A2: {res_a2['tput']:.3f} Mbps, Cross-Blocking: {res_a2['cross_blocking']:.4f} ms\n")
    print(f"Saved calibration report to {report_path}")

if __name__ == "__main__":
    main()
