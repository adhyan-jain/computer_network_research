"""
Plot generation script for Wi-Fi 7 MLO Research Paper.
Generates publication-quality figures (PDF and PNG, 300 DPI) using matplotlib.
Reads data directly from experiments/results/*.csv.
"""

import os
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
PLOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# Publication styling
plt.rcParams.update({
    "font.size": 11,
    "font.family": "serif",
    "axes.labelsize": 12,
    "axes.titlesize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "figure.titlesize": 13,
    "lines.linewidth": 2.0,
    "lines.markersize": 6,
    "grid.alpha": 0.4,
    "grid.linestyle": "--"
})


def plot_fig1_link_asymmetry():
    csv_file = os.path.join(RESULTS_DIR, "exp1_link_asymmetry.csv")
    if not os.path.exists(csv_file):
        return

    data = {}
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sched = row["scheduler"]
            if sched not in data:
                data[sched] = {"delta": [], "cross": [], "ci_cross": []}
            data[sched]["delta"].append(float(row["delta_ms"]))
            data[sched]["cross"].append(float(row["mean_cross_blocking_ms"]))
            data[sched]["ci_cross"].append(float(row["ci_cross_blocking"]))

    fig, ax = plt.subplots(figsize=(7, 4.2))
    
    style_map = {
        "SingleLink": ("#7f7f7f", "s", "--", "Single-Link (SLO)"),
        "DefaultFIFO": ("#d62728", "o", "-", "Default FIFO MLO"),
        "RoundRobin": ("#ff7f0e", "^", "--", "Round-Robin"),
        "LowestLatency": ("#8c564b", "v", "--", "Lowest Latency First"),
        "CongestionAware": ("#9467bd", "D", "-.", "Congestion-Aware (CALA)"),
        "StaticPinning": ("#bcbd22", "x", ":", "Static Flow Pinning"),
        "RetransmissionSteering": ("#17becf", "<", "-.", "Retrans. Steering (WARS)"),
        "SASP": ("#1f77b4", "*", "-", "SASP (Proposed, Thm 3)"),
        "Oracle": ("#2ca02c", "p", ":", "Oracle (Offline Bound)")
    }

    for sched, (color, marker, ls, label) in style_map.items():
        if sched in data:
            d = data[sched]
            ax.errorbar(
                d["delta"], d["cross"], yerr=d["ci_cross"],
                color=color, marker=marker, linestyle=ls, label=label,
                capsize=3, alpha=0.9
            )

    ax.set_xlabel("Link Delay Asymmetry $\\delta = \\mu_1 - \\mu_2$ (ms)")
    ax.set_ylabel("Mean Cross-Flow Blocking $\\mathbb{E}[\\mathcal{X}]$ (ms)")
    ax.set_title("Cross-Flow Blocking vs. Link Asymmetry (EXP-01)")
    ax.grid(True)
    ax.legend(loc="upper left", framealpha=0.9, ncol=2)
    plt.tight_layout()

    fig.savefig(os.path.join(PLOTS_DIR, "fig1_asymmetry_sweep.pdf"))
    fig.savefig(os.path.join(PLOTS_DIR, "fig1_asymmetry_sweep.png"), dpi=300)
    plt.close(fig)
    print("Generated fig1_asymmetry_sweep.pdf/png")


def plot_fig2_window_collapse():
    csv_file = os.path.join(RESULTS_DIR, "exp2_window_collapse.csv")
    if not os.path.exists(csv_file):
        return

    data = {}
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sched = row["scheduler"]
            if sched not in data:
                data[sched] = {"load": [], "goodput": [], "ci_gp": [], "p99": []}
            data[sched]["load"].append(float(row["norm_load"]))
            data[sched]["goodput"].append(float(row["mean_goodput_mbps"]))
            data[sched]["ci_gp"].append(float(row["ci_goodput"]))
            data[sched]["p99"].append(float(row["p99_e2e_delay_ms"]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.0))

    colors = {
        "DefaultFIFO": ("#d62728", "o", "-", "Default FIFO"),
        "StaticPinning": ("#bcbd22", "x", "--", "Static Pinning"),
        "CongestionAware": ("#9467bd", "D", "-.", "Congestion-Aware"),
        "SASP": ("#1f77b4", "*", "-", "SASP (Proposed)")
    }

    # Left plot: Goodput vs normalized load
    for sched, (col, mark, ls, lbl) in colors.items():
        if sched in data:
            d = data[sched]
            ax1.errorbar(d["load"], d["goodput"], yerr=d["ci_gp"], color=col, marker=mark, linestyle=ls, label=lbl, capsize=3)

    ax1.axvline(1.0, color="black", linestyle=":", label="Collapse Boundary $\\lambda^*$")
    ax1.set_xlabel("Normalized Arrival Rate $\\lambda / \\lambda^*$ (Thm 2)")
    ax1.set_ylabel("Aggregate Goodput (Mbps)")
    ax1.set_title("(a) Goodput Collapse")
    ax1.grid(True)
    ax1.legend(loc="lower left", framealpha=0.9)

    # Right plot: p99 Latency vs normalized load
    for sched, (col, mark, ls, lbl) in colors.items():
        if sched in data:
            d = data[sched]
            ax2.plot(d["load"], d["p99"], color=col, marker=mark, linestyle=ls, label=lbl)

    ax2.axvline(1.0, color="black", linestyle=":", label="Collapse Boundary $\\lambda^*$")
    ax2.set_xlabel("Normalized Arrival Rate $\\lambda / \\lambda^*$ (Thm 2)")
    ax2.set_ylabel("99th Percentile Latency (ms)")
    ax2.set_title("(b) Tail Latency Surge")
    ax2.grid(True)
    ax2.legend(loc="upper left", framealpha=0.9)

    plt.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "fig2_window_collapse.pdf"))
    fig.savefig(os.path.join(PLOTS_DIR, "fig2_window_collapse.png"), dpi=300)
    plt.close(fig)
    print("Generated fig2_window_collapse.pdf/png")


def plot_fig3_priority_heterogeneity():
    csv_file = os.path.join(RESULTS_DIR, "exp3_priority_heterogeneity.csv")
    if not os.path.exists(csv_file):
        return

    data = {}
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sched = row["scheduler"]
            if sched not in data:
                data[sched] = {"ratio": [], "inter_cross": [], "p99": []}
            data[sched]["ratio"].append(float(row["weight_ratio"]))
            data[sched]["inter_cross"].append(float(row["interactive_cross_ms"]))
            data[sched]["p99"].append(float(row["interactive_p99_ms"]))

    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    colors = {
        "DefaultFIFO": ("#d62728", "o", "--", "Default FIFO"),
        "CongestionAware": ("#9467bd", "D", "-.", "Congestion-Aware"),
        "SASP": ("#1f77b4", "*", "-", "SASP (Thm 3 Threshold)")
    }

    for sched, (col, mark, ls, lbl) in colors.items():
        if sched in data:
            d = data[sched]
            ax.plot(d["ratio"], d["inter_cross"], color=col, marker=mark, linestyle=ls, label=lbl)

    ax.set_xlabel("Interactive Priority Weight Ratio $w_{\\mathrm{inter}} / w_{\\mathrm{bulk}}$")
    ax.set_ylabel("Interactive Flow Cross-Blocking $\\mathbb{E}[\\mathcal{X}_2]$ (ms)")
    ax.set_title("Interactive Flow Protection under SASP (EXP-03)")
    ax.grid(True)
    ax.legend(loc="center right", framealpha=0.9)
    plt.tight_layout()

    fig.savefig(os.path.join(PLOTS_DIR, "fig3_priority_weights.pdf"))
    fig.savefig(os.path.join(PLOTS_DIR, "fig3_priority_weights.png"), dpi=300)
    plt.close(fig)
    print("Generated fig3_priority_weights.pdf/png")


def plot_fig4_loss_contention():
    csv_file = os.path.join(RESULTS_DIR, "exp4_contention_loss.csv")
    if not os.path.exists(csv_file):
        return

    data = {}
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sched = row["scheduler"]
            if sched not in data:
                data[sched] = {"fer": [], "cross": [], "ci": []}
            data[sched]["fer"].append(float(row["fer"]) * 100.0)  # to percentage
            data[sched]["cross"].append(float(row["mean_cross_blocking_ms"]))
            data[sched]["ci"].append(float(row["ci_cross"]))

    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    colors = {
        "DefaultFIFO": ("#d62728", "o", "--", "Default FIFO"),
        "RetransmissionSteering": ("#17becf", "<", "-.", "Retrans. Steering (WARS)"),
        "CongestionAware": ("#9467bd", "D", ":", "Congestion-Aware"),
        "SASP": ("#1f77b4", "*", "-", "SASP (Proposed)")
    }

    for sched, (col, mark, ls, lbl) in colors.items():
        if sched in data:
            d = data[sched]
            ax.errorbar(d["fer"], d["cross"], yerr=d["ci"], color=col, marker=mark, linestyle=ls, label=lbl, capsize=3)

    ax.set_xlabel("Frame Error Rate FER (%)")
    ax.set_ylabel("Mean Cross-Flow Blocking $\\mathbb{E}[\\mathcal{X}]$ (ms)")
    ax.set_title("Cross-Flow Blocking under Loss and Contention (EXP-04)")
    ax.grid(True)
    ax.legend(loc="upper left", framealpha=0.9)
    plt.tight_layout()

    fig.savefig(os.path.join(PLOTS_DIR, "fig4_loss_contention.pdf"))
    fig.savefig(os.path.join(PLOTS_DIR, "fig4_loss_contention.png"), dpi=300)
    plt.close(fig)
    print("Generated fig4_loss_contention.pdf/png")


def plot_fig5_estimation_robustness():
    csv_file = os.path.join(RESULTS_DIR, "exp6_estimation_robustness.csv")
    if not os.path.exists(csv_file):
        return

    biases, sasp_cr, fifo_cr, rel_adv = [], [], [], []
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            biases.append(float(row["bias_factor"]) * 100.0)
            sasp_cr.append(float(row["sasp_cross_blocking_ms"]))
            fifo_cr.append(float(row["fifo_cross_blocking_ms"]))
            rel_adv.append(float(row["relative_advantage_pct"]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.0))

    ax1.plot(biases, sasp_cr, color="#1f77b4", marker="*", linestyle="-", label="SASP with Biased $\\hat{\\sigma}$")
    ax1.plot(biases, fifo_cr, color="#d62728", marker="o", linestyle="--", label="Default FIFO Baseline")
    ax1.set_xlabel("Variance Estimation Bias $\\epsilon_\\sigma$ (%)")
    ax1.set_ylabel("Mean Cross-Flow Blocking (ms)")
    ax1.set_title("(a) Delay Degradation Curve")
    ax1.grid(True)
    ax1.legend(loc="center right", framealpha=0.9)

    ax2.bar(biases, rel_adv, width=12, color="#2ca02c", alpha=0.8, edgecolor="black")
    ax2.set_xlabel("Variance Estimation Bias $\\epsilon_\\sigma$ (%)")
    ax2.set_ylabel("SASP Advantage over FIFO (%)")
    ax2.set_title("(b) Relative Gain Persistence")
    ax2.grid(True)

    plt.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "fig5_estimation_robustness.pdf"))
    fig.savefig(os.path.join(PLOTS_DIR, "fig5_estimation_robustness.png"), dpi=300)
    plt.close(fig)
    print("Generated fig5_estimation_robustness.pdf/png")


def plot_fig6_ablation():
    csv_file = os.path.join(RESULTS_DIR, "exp7_ablation_study.csv")
    if not os.path.exists(csv_file):
        return

    variants, cross_vals, ci_vals, p99_vals = [], [], [], []
    labels = ["FIFO\nBaseline", "Dispatch\nOnly", "Mean-Only\nSequencing", "Full SASP\n(Thm 3 Engine)"]
    
    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            variants.append(row["variant"])
            cross_vals.append(float(row["mean_cross_blocking_ms"]))
            ci_vals.append(float(row["ci_cross"]))
            p99_vals.append(float(row["interactive_p99_ms"]))

    fig, ax1 = plt.subplots(figsize=(6.5, 4.2))

    x = np.arange(len(variants))
    bar1 = ax1.bar(x - 0.2, cross_vals, yerr=ci_vals, width=0.38, color="#1f77b4", alpha=0.85, label="Cross-Flow Blocking (ms)", capsize=4)
    
    ax2 = ax1.twinx()
    bar2 = ax2.bar(x + 0.2, p99_vals, width=0.38, color="#ff7f0e", alpha=0.85, label="Interactive p99 Latency (ms)")

    ax1.set_ylabel("Cross-Flow Blocking (ms)", color="#1f77b4")
    ax2.set_ylabel("Interactive p99 Latency (ms)", color="#ff7f0e")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_title("Ablation Study of Algorithmic Components (EXP-07)")
    ax1.grid(True)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", framealpha=0.9)

    plt.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, "fig6_ablation.pdf"))
    fig.savefig(os.path.join(PLOTS_DIR, "fig6_ablation.png"), dpi=300)
    plt.close(fig)
    print("Generated fig6_ablation.pdf/png")


if __name__ == "__main__":
    plot_fig1_link_asymmetry()
    plot_fig2_window_collapse()
    plot_fig3_priority_heterogeneity()
    plot_fig4_loss_contention()
    plot_fig5_estimation_robustness()
    plot_fig6_ablation()
    print("All figures generated successfully.")
