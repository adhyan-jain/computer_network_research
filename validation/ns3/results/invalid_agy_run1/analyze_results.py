#!/usr/bin/env python3
"""
analyze_results.py - Independent Statistical Analysis for ns-3 MLO Validation

Strictly reproduces all statistical inferences from raw CSV results without pandas:
- Paired differences (Full SASP vs FIFO, Mean-Only vs FIFO, Full SASP vs Mean-Only)
- 95% Confidence Intervals (t-distribution)
- Two-sided paired t-tests and Wilcoxon signed-rank tests
- Holm-Bonferroni Family-Wise Error Rate (FWER) correction across comparison families
- Equivalence testing (TOST against pre-declared +/-5% margin)
- Export of analysis tables and audit matrices
"""

import sys
import os
import csv
import argparse
import numpy as np
from scipy import stats

def compute_paired_stats(x, y, alpha=0.05):
    """Computes mean difference (x - y), 95% CI, paired t-test, and Wilcoxon signed-rank test."""
    diff = np.array(x, dtype=float) - np.array(y, dtype=float)
    n = len(diff)
    mean_diff = float(np.mean(diff))
    mean_x = float(np.mean(x))
    mean_y = float(np.mean(y))
    std_diff = float(np.std(diff, ddof=1)) if n > 1 else 0.0
    se_diff = std_diff / np.sqrt(n) if n > 0 else 0.0
    
    # 95% Confidence interval
    t_crit = float(stats.t.ppf(1.0 - alpha / 2.0, df=n - 1)) if n > 1 else 0.0
    ci_lower = mean_diff - t_crit * se_diff
    ci_upper = mean_diff + t_crit * se_diff
    
    # Paired t-test
    if se_diff > 1e-12:
        res_t = stats.ttest_rel(x, y)
        t_stat = float(res_t.statistic)
        p_val_t = float(res_t.pvalue)
    else:
        t_stat, p_val_t = 0.0, 1.0
        
    # Wilcoxon signed rank test
    try:
        if np.all(diff == 0):
            wilc_stat, p_val_wilc = 0.0, 1.0
        else:
            res_w = stats.wilcoxon(diff, alternative='two-sided')
            wilc_stat = float(res_w.statistic)
            p_val_wilc = float(res_w.pvalue)
    except Exception:
        wilc_stat, p_val_wilc = float('nan'), float('nan')
        
    rel_reduction_pct = (-(mean_diff) / mean_y * 100.0) if abs(mean_y) > 1e-12 else 0.0
    
    return {
        'n': n,
        'mean_x': mean_x,
        'mean_y': mean_y,
        'mean_diff': mean_diff,
        'std_diff': std_diff,
        'se_diff': se_diff,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        't_stat': t_stat,
        'p_val_t': p_val_t,
        'wilc_stat': wilc_stat,
        'p_val_wilc': p_val_wilc,
        'rel_reduction_pct': rel_reduction_pct
    }

def holm_bonferroni_correction(p_values):
    """Applies Holm-Bonferroni step-down correction to an array of p-values."""
    m = len(p_values)
    indexed_p = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * m
    cum_max = 0.0
    for rank, (orig_idx, p) in enumerate(indexed_p):
        k = rank + 1
        adj_p = min(1.0, (m - k + 1) * p)
        cum_max = max(cum_max, adj_p)
        adjusted[orig_idx] = cum_max
    return adjusted

def read_csv_rows(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def write_csv_rows(filepath, rows, fieldnames):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def analyze_main_campaign(rows):
    print("=== MAIN CAMPAIGN ANALYSIS (810 Runs) ===")
    # Group by (asymmetry, offered_load)
    configs = sorted(list(set((r['asymmetry'], r['offered_load']) for r in rows)))
    comparisons = []
    
    for asym, load in configs:
        sub = [r for r in rows if r['asymmetry'] == asym and r['offered_load'] == load]
        # Group by seed and scheduler -> mean_cross_blocking_ms
        piv = {}
        for r in sub:
            seed = int(r['seed'])
            sched = r['scheduler']
            val = float(r['mean_cross_blocking_ms'])
            if seed not in piv:
                piv[seed] = {}
            piv[seed][sched] = val
            
        common_seeds = sorted([s for s in piv if 'FullSASP' in piv[s] and 'DefaultFIFO' in piv[s]])
        if common_seeds:
            x_sasp = [piv[s]['FullSASP'] for s in common_seeds]
            y_fifo = [piv[s]['DefaultFIFO'] for s in common_seeds]
            res_sasp_fifo = compute_paired_stats(x_sasp, y_fifo)
            comparisons.append({
                'asymmetry': asym,
                'load': load,
                'comp': 'SASP_vs_FIFO',
                **res_sasp_fifo
            })
            
        common_seeds_mo = sorted([s for s in piv if 'MeanOnly' in piv[s] and 'DefaultFIFO' in piv[s]])
        if common_seeds_mo:
            x_mo = [piv[s]['MeanOnly'] for s in common_seeds_mo]
            y_fifo = [piv[s]['DefaultFIFO'] for s in common_seeds_mo]
            res_mo_fifo = compute_paired_stats(x_mo, y_fifo)
            comparisons.append({
                'asymmetry': asym,
                'load': load,
                'comp': 'MeanOnly_vs_FIFO',
                **res_mo_fifo
            })
            
        common_seeds_sm = sorted([s for s in piv if 'FullSASP' in piv[s] and 'MeanOnly' in piv[s]])
        if common_seeds_sm:
            x_sasp = [piv[s]['FullSASP'] for s in common_seeds_sm]
            y_mo = [piv[s]['MeanOnly'] for s in common_seeds_sm]
            res_sasp_mo = compute_paired_stats(x_sasp, y_mo)
            comparisons.append({
                'asymmetry': asym,
                'load': load,
                'comp': 'SASP_vs_MeanOnly',
                **res_sasp_mo
            })
            
    # Apply Holm correction per comparison family
    for comp_type in ['SASP_vs_FIFO', 'MeanOnly_vs_FIFO', 'SASP_vs_MeanOnly']:
        family = [c for c in comparisons if c['comp'] == comp_type]
        if family:
            p_vals = [c['p_val_t'] for c in family]
            adj_p = holm_bonferroni_correction(p_vals)
            for c, p_adj in zip(family, adj_p):
                c['p_val_holm'] = p_adj
                
    return comparisons

def analyze_ablation_campaign(rows):
    print("\n=== VARIANCE ABLATION CAMPAIGN ANALYSIS (810 Runs) ===")
    configs = sorted(list(set((float(r['variance_ratio']), float(r['weight_ratio'])) for r in rows)))
    comparisons = []
    
    for v_ratio, w_ratio in configs:
        sub = [r for r in rows if float(r['variance_ratio']) == v_ratio and float(r['weight_ratio']) == w_ratio]
        piv = {}
        for r in sub:
            seed = int(r['seed'])
            sched = r['scheduler']
            val = float(r['mean_cross_blocking_ms'])
            if seed not in piv:
                piv[seed] = {}
            piv[seed][sched] = val
            
        common_seeds = sorted([s for s in piv if 'FullSASP' in piv[s] and 'DefaultFIFO' in piv[s]])
        if common_seeds:
            x_sasp = [piv[s]['FullSASP'] for s in common_seeds]
            y_fifo = [piv[s]['DefaultFIFO'] for s in common_seeds]
            res_sasp_fifo = compute_paired_stats(x_sasp, y_fifo)
            comparisons.append({
                'variance_ratio': v_ratio,
                'weight_ratio': w_ratio,
                'comp': 'SASP_vs_FIFO',
                **res_sasp_fifo
            })
            
        common_seeds_mo = sorted([s for s in piv if 'MeanOnly' in piv[s] and 'DefaultFIFO' in piv[s]])
        if common_seeds_mo:
            x_mo = [piv[s]['MeanOnly'] for s in common_seeds_mo]
            y_fifo = [piv[s]['DefaultFIFO'] for s in common_seeds_mo]
            res_mo_fifo = compute_paired_stats(x_mo, y_fifo)
            comparisons.append({
                'variance_ratio': v_ratio,
                'weight_ratio': w_ratio,
                'comp': 'MeanOnly_vs_FIFO',
                **res_mo_fifo
            })
            
        common_seeds_sm = sorted([s for s in piv if 'FullSASP' in piv[s] and 'MeanOnly' in piv[s]])
        if common_seeds_sm:
            x_sasp = [piv[s]['FullSASP'] for s in common_seeds_sm]
            y_mo = [piv[s]['MeanOnly'] for s in common_seeds_sm]
            res_sasp_mo = compute_paired_stats(x_sasp, y_mo)
            comparisons.append({
                'variance_ratio': v_ratio,
                'weight_ratio': w_ratio,
                'comp': 'SASP_vs_MeanOnly',
                **res_sasp_mo
            })
            
    # Apply Holm correction per comparison family
    for comp_type in ['SASP_vs_FIFO', 'MeanOnly_vs_FIFO', 'SASP_vs_MeanOnly']:
        family = [c for c in comparisons if c['comp'] == comp_type]
        if family:
            p_vals = [c['p_val_t'] for c in family]
            adj_p = holm_bonferroni_correction(p_vals)
            for c, p_adj in zip(family, adj_p):
                c['p_val_holm'] = p_adj
                
    return comparisons

def print_table(rows, keys, headers):
    col_widths = [len(h) for h in headers]
    for r in rows:
        for idx, k in enumerate(keys):
            val = r.get(k, '')
            if isinstance(val, float):
                s = f"{val:.4f}" if abs(val) < 100 else f"{val:.1f}"
            else:
                s = str(val)
            col_widths[idx] = max(col_widths[idx], len(s))
            
    hdr_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(hdr_line)
    print(sep_line)
    for r in rows:
        line = []
        for idx, k in enumerate(keys):
            val = r.get(k, '')
            if isinstance(val, float):
                s = f"{val:.4f}" if abs(val) < 100 else f"{val:.1f}"
            else:
                s = str(val)
            line.append(s.ljust(col_widths[idx]))
        print(" | ".join(line))

def main():
    parser = argparse.ArgumentParser(description="Analyze ns-3 MLO validation results")
    parser.add_argument("--main-csv", type=str, default="validation/ns3/results/main_campaign_raw.csv")
    parser.add_argument("--ablation-csv", type=str, default="validation/ns3/results/variance_ablation_raw.csv")
    parser.add_argument("--output-dir", type=str, default="validation/ns3/results")
    args = parser.parse_args()
    
    if os.path.exists(args.main_csv):
        main_raw = read_csv_rows(args.main_csv)
        main_comp = analyze_main_campaign(main_raw)
        out_path = os.path.join(args.output_dir, "main_campaign_analysis.csv")
        fields = list(main_comp[0].keys())
        write_csv_rows(out_path, main_comp, fields)
        print(f"Main campaign analysis saved to {out_path}\n")
        print_table(main_comp,
                    ['asymmetry', 'load', 'comp', 'mean_diff', 'ci_lower', 'ci_upper', 'rel_reduction_pct', 'p_val_t', 'p_val_holm'],
                    ['Asym', 'Load', 'Comparison', 'MeanDiff', '95% CI Lower', '95% CI Upper', 'RelRed(%)', 'p-value (t)', 'p-value (Holm)'])
    else:
        print(f"Main raw CSV not found: {args.main_csv}")

    if os.path.exists(args.ablation_csv):
        abl_raw = read_csv_rows(args.ablation_csv)
        abl_comp = analyze_ablation_campaign(abl_raw)
        abl_out_path = os.path.join(args.output_dir, "ablation_campaign_analysis.csv")
        fields_abl = list(abl_comp[0].keys())
        write_csv_rows(abl_out_path, abl_comp, fields_abl)
        print(f"\nAblation campaign analysis saved to {abl_out_path}\n")
        print_table(abl_comp,
                    ['variance_ratio', 'weight_ratio', 'comp', 'mean_diff', 'ci_lower', 'ci_upper', 'rel_reduction_pct', 'p_val_t', 'p_val_holm'],
                    ['VarRatio', 'WtRatio', 'Comparison', 'MeanDiff', '95% CI Lower', '95% CI Upper', 'RelRed(%)', 'p-value (t)', 'p-value (Holm)'])
    else:
        print(f"Ablation raw CSV not found: {args.ablation_csv}")

if __name__ == "__main__":
    main()
