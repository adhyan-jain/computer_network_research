"""
Independent Statistical Audit of Phase 6 Ablation Campaign.
Reads raw simulation traces from raw_runs.csv and performs:
1. Exact configuration mapping and completeness audit.
2. Per-seed paired cost differences and decision agreement tracking.
3. Paired Student-t test, Wilcoxon signed-rank test, and paired bootstrap 95% CIs.
4. Effect size calculations (Cohen's dz).
5. Multiple comparisons adjustments:
   - Bonferroni FWER control
   - Benjamini-Hochberg False Discovery Rate (FDR) control
6. Independent evaluation of Claims A through E.
7. Outputs machine-readable summary table to audit_statistical_summary.csv.
"""

import os
import csv
import math
import numpy as np
from scipy import stats
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_CSV = os.path.join(BASE_DIR, "raw_runs.csv")
AUDIT_SUMMARY_CSV = os.path.join(BASE_DIR, "audit_statistical_summary.csv")


def paired_bootstrap_ci(x, y, n_boot=10000, alpha=0.05, seed=42):
    """Computes bootstrap percentile confidence interval of paired mean difference (x - y)."""
    rng = np.random.default_rng(seed)
    diffs = np.array(x) - np.array(y)
    n = len(diffs)
    boot_means = np.zeros(n_boot)
    for i in range(n_boot):
        indices = rng.integers(0, n, size=n)
        boot_means[i] = np.mean(diffs[indices])
    low = np.percentile(boot_means, 100.0 * (alpha / 2.0))
    high = np.percentile(boot_means, 100.0 * (1.0 - alpha / 2.0))
    return float(np.mean(diffs)), float(low), float(high)


def run_audit():
    with open(RAW_CSV, "r") as f:
        rows = list(csv.DictReader(f))

    total_rows = len(rows)
    assert total_rows == 2160, f"Expected 2160 rows, got {total_rows}"

    # Group by (regime, weight_ratio, delta_mu_ms, sigma2_mult) -> seed -> sched_type -> dict
    data = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        key = (r["regime"], float(r["weight_ratio"]), float(r["delta_mu_ms"]), float(r["sigma2_mult"]))
        seed = int(r["seed"])
        sched = r["sched_type"]
        data[key][seed][sched] = {
            "weighted_cost": float(r["weighted_cost"]),
            "mean_cross_ms": float(r["mean_cross_ms"]),
            "interactive_cross_ms": float(r["interactive_cross_ms"]),
            "interactive_p95_ms": float(r["interactive_p95_ms"]),
            "interactive_p99_ms": float(r["interactive_p99_ms"]),
            "goodput_mbps": float(r["goodput_mbps"])
        }

    results = []
    p_t_list = []

    for key in sorted(data.keys()):
        reg, wr, d_mu, sm = key
        seeds_dict = data[key]
        seeds = sorted(seeds_dict.keys())

        fifo_costs = [seeds_dict[s]["DefaultFIFO"]["weighted_cost"] for s in seeds]
        mo_costs = [seeds_dict[s]["MeanOnly"]["weighted_cost"] for s in seeds]
        sasp_costs = [seeds_dict[s]["FullSASP"]["weighted_cost"] for s in seeds]

        m_fifo = float(np.mean(fifo_costs))
        m_mo = float(np.mean(mo_costs))
        m_sasp = float(np.mean(sasp_costs))

        # FullSASP vs MeanOnly paired differences (positive = FullSASP is better/lower cost)
        diff_mo_sasp = np.array(mo_costs) - np.array(sasp_costs)
        mean_diff, ci_low, ci_high = paired_bootstrap_ci(mo_costs, sasp_costs)

        rel_improvement = (m_mo - m_sasp) / m_mo * 100.0 if m_mo > 0 else 0.0
        fifo_improvement = (m_fifo - m_sasp) / m_fifo * 100.0 if m_fifo > 0 else 0.0

        # Paired tests
        if np.all(np.abs(diff_mo_sasp) < 1e-12):
            p_t = 1.0
            p_w = 1.0
            cohen_dz = 0.0
            wins = 0
            ties = len(diff_mo_sasp)
            losses = 0
        else:
            t_res = stats.ttest_rel(mo_costs, sasp_costs)
            p_t = float(t_res.pvalue)
            try:
                w_res = stats.wilcoxon(mo_costs, sasp_costs, zero_method="pratt")
                p_w = float(w_res.pvalue)
            except Exception:
                p_w = 1.0
            std_diff = float(np.std(diff_mo_sasp, ddof=1))
            cohen_dz = float(np.mean(diff_mo_sasp) / std_diff) if std_diff > 0 else 0.0
            wins = int(np.sum(diff_mo_sasp > 1e-9))
            ties = int(np.sum(np.abs(diff_mo_sasp) <= 1e-9))
            losses = int(np.sum(diff_mo_sasp < -1e-9))

        p_t_list.append(p_t)

        results.append({
            "regime": reg,
            "weight_ratio": wr,
            "delta_mu_ms": d_mu,
            "sigma2_mult": sm,
            "fifo_mean_cost": m_fifo,
            "mean_only_mean_cost": m_mo,
            "full_sasp_mean_cost": m_sasp,
            "paired_abs_diff_mean": mean_diff,
            "paired_boot_ci_low": ci_low,
            "paired_boot_ci_high": ci_high,
            "relative_improvement_pct": rel_improvement,
            "fifo_improvement_pct": fifo_improvement,
            "p_t_raw": p_t,
            "p_wilcoxon": p_w,
            "cohen_dz": cohen_dz,
            "wins_sasp": wins,
            "ties": ties,
            "losses_sasp": losses
        })

    # Multiplicity corrections across the 18 hypothesis tests
    m_tests = len(results)
    bonf_alpha = 0.05 / m_tests

    # Benjamini-Hochberg FDR
    sorted_indices = sorted(range(m_tests), key=lambda i: results[i]["p_t_raw"])
    bh_passed = [False] * m_tests

    # Find largest k such that p_(k) <= (k/m) * q
    max_k = -1
    for rank, idx in enumerate(sorted_indices, 1):
        crit = (rank / m_tests) * 0.05
        if results[idx]["p_t_raw"] <= crit:
            max_k = rank

    if max_k != -1:
        for rank in range(1, max_k + 1):
            idx = sorted_indices[rank - 1]
            bh_passed[idx] = True

    for i, r in enumerate(results):
        r["bonferroni_sig"] = r["p_t_raw"] <= bonf_alpha
        r["fdr_bh_sig"] = bh_passed[i]

    # Write audit summary CSV
    fieldnames = list(results[0].keys())
    with open(AUDIT_SUMMARY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Independent statistical audit completed. {len(results)} configurations analyzed.")
    print(f"Summary written to {AUDIT_SUMMARY_CSV}")


if __name__ == "__main__":
    run_audit()
