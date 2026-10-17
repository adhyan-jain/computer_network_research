"""make_fig.py - Figure 1: pairing strength rho (FIFO vs FullSASP, across seeds) in the Python simulator
versus link asymmetry (exploratory X1) and in pre-existing ns-3 cells (exploratory X5). Reads JSON only."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
X = json.loads((HERE.parent / "results" / "exploratory_numbers.json").read_text())

fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.7))
x1 = X["X1_asymmetry"]
dms = [float(k.split("_")[-1]) for k in x1]
for design, mk, off in (("shared", "o", 0.97), ("keyed", "s", 1.03)):
    rho = [x1[k][design]["rho"] for k in x1]
    lo = [x1[k][design]["rho"] - x1[k][design]["rho_ci"][0] for k in x1]
    hi = [x1[k][design]["rho_ci"][1] - x1[k][design]["rho"] for k in x1]
    ax[0].errorbar([d * off for d in dms], rho, yerr=[lo, hi], marker=mk, capsize=2, label=f"{design} RNG", lw=1)
ax[0].set_xscale("log")
ax[0].axhline(0, color="gray", lw=0.5)
ax[0].set_xlabel(r"link-2 extra delay $\Delta\mu$ (ms)")
ax[0].set_ylabel(r"across-seed $\rho$(FIFO, FullSASP)")
ax[0].set_title("(a) Python simulator", fontsize=9)
ax[0].legend(fontsize=7)

cells = X["X5_ns3_pairing_reanalysis"]["cells"]
for load, mk in (("L0", "o"), ("L1", "s"), ("L2", "^")):
    ys = [cells[f"{a}/{load}"]["rho"] for a in ("A0", "A1", "A2")]
    ax[1].plot(["A0", "A1", "A2"], ys, marker=mk, label=load, lw=1)
ax[1].axhline(0, color="gray", lw=0.5)
ax[1].set_xlabel("ns-3 asymmetry level")
ax[1].set_title("(b) ns-3 (pre-existing runs)", fontsize=9)
ax[1].legend(fontsize=7, title="load", title_fontsize=7)
fig.tight_layout()
fig.savefig(HERE / "fig_pairing.pdf")
print("wrote fig_pairing.pdf")


# Figure 2: share of the interventional externality that is cross-flow blocking (Study 2b, exploratory)
import numpy as np
S2B = json.loads((HERE.parent / "results" / "exploratory_study2b.json").read_text())
loads, asyms = [1.0, 0.5, 0.25, 0.1], [0.1, 2.0, 5.0]
grid = np.array([[100 * S2B[f"load{l}_asym{a}"]["share_cross"]["point"] for a in asyms] for l in loads])
fig2, ax2 = plt.subplots(figsize=(3.6, 2.6))
im = ax2.imshow(grid, cmap="viridis", aspect="auto")
ax2.set_xticks(range(len(asyms)), [str(a) for a in asyms])
ax2.set_yticks(range(len(loads)), [str(l) for l in loads])
ax2.set_xlabel(r"link-2 extra delay $\Delta\mu$ (ms)")
ax2.set_ylabel("load multiplier")
for i in range(len(loads)):
    for j in range(len(asyms)):
        ax2.text(j, i, f"{grid[i, j]:.1f}", ha="center", va="center", color="w" if grid[i, j] < 20 else "k", fontsize=8)
fig2.colorbar(im, label="cross-blocking share of externality (%)")
fig2.tight_layout()
fig2.savefig(HERE / "fig_share.pdf")
print("wrote fig_share.pdf")


# Figure 3: certificate on the held-out cells (Study 4, preregistered): q = X/e2e_obs (one trace) vs r = X/E (interventional)
S4 = json.loads((HERE.parent / "results" / "analysis_study4.json").read_text())["cells"]
fig3, ax3 = plt.subplots(figsize=(3.8, 3.2))
for kind, mk, lab in (("python", "o", "Python simulator (13 cells)"), ("ns3", "s", "ns-3.47 (6 cells)")):
    pts = [(c["q"], c["r"]) for c in S4.values() if c["kind"] == kind]
    ax3.scatter([p[0] for p in pts], [p[1] for p in pts], marker=mk, s=22, label=lab)
lim = [1e-4, 3]
ax3.plot(lim, lim, color="gray", lw=0.8, ls="--", label=r"$r=q$ (certificate bound)")
ax3.set_xscale("log")
ax3.set_yscale("log")
ax3.set_xlim(lim)
ax3.set_ylim(lim)
ax3.set_xlabel(r"observable $q=X/\mathrm{e2e}_{\rm obs}$ (one trace)")
ax3.set_ylabel(r"explained fraction $r=X/E$ (replay)")
ax3.legend(fontsize=6.5, loc="upper left")
fig3.tight_layout()
fig3.savefig(HERE / "fig_cert.pdf")
print("wrote fig_cert.pdf")
