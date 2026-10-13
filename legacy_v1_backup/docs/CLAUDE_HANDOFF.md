# Claude Code Cleanup and Independent Verification Handoff

**Project:** Cross-Flow Head-of-Line Blocking in Wi-Fi 7 Multi-Link Operation: Analytical Modeling and Sequence-Aware Scheduling  
**Directory:** `/home/adhyan/Desktop/wifi7_mlo_hol`  
**Date:** 2026-10-13  
**Status:** Theoretical derivations proved, simulation framework implemented, 20 tests passing, 7 evaluation experiments executed across 30 seeds.  

---

## 1. Project Objective and Selection Reasoning

- **Core Problem:** In IEEE 802.11be (Wi-Fi 7) Multi-Link Operation (MLO), multiple application flows sharing a single Traffic Identifier ($\text{TID}$) share a single 12-bit sequence-number space and a single receiver Block Acknowledgment (BA) reorder buffer. When packets are dispatched across heterogeneous wireless links, frames from faster flows on faster links arrive out of sequence order and are blocked at the receiver waiting for earlier-sequenced frames of other flows.
- **Why Selected:** Survives all 10 novelty kill criteria. MediaTek holds a patent (US12470496B2) on *receiver-side* multi-queue reordering using DPI, which requires non-standard receivers. Our work solves the problem entirely at the **transmitter U-MAC scheduler** under standard unmodified IEEE 802.11be receiver semantics.

---

## 2. Competing Works and Theoretical References

1. **Oliveira, Raposo, Luís (IEEE OJCOMS 2026):** *Characterizing Block Acknowledgment Window Reordering in Multi-Link Wi-Fi*. DOI: `10.1109/OJCOMS.2026.3686295`. (Empirical characterization only; no model, no scheduling algorithm).
2. **MediaTek Patent US12470496B2 / US20240244007A1:** *Data Reordering Method and Apparatus Thereof*. (Receiver-side DPI reordering; strictly avoided in our sender-side architecture).
3. **Carreño et al. (arXiv:2105.10199, 2021):** Evaluated static vs congestion-aware link selection heuristics.
4. **Sangeetha et al. (Computer Networks 2026):** Performance assessment with unsaturated queues.
5. **Choi et al. (Computer Networks 2025):** L-MAC/U-MAC scheduling for NSTR half-duplex blinding.

---

## 3. Theorem Statements, Assumptions, and Proof Locations

All formal proofs reside in `theory/derivation.md`:
- **Theorem 1 (Orthogonal Decomposition):** $\Delta_i = \mathcal{S}_i + \mathcal{X}_i$, where $\mathcal{S}_i = \max(0, R_i^{\text{intra}} - A_i)$ (self-blocking) and $\mathcal{X}_i = \max(0, R_i - R_i^{\text{intra}})$ (cross-flow blocking). Unique and non-negative.
- **Theorem 2 (Multi-Link BA Window Stall Boundary):** Fast-link throughput collapses when arrival rate exceeds $\lambda^* = W / \delta$ due to sliding window stall.
- **Theorem 3 (Optimal Threshold Scheduling):** Optimal sequence order $s_a < s_b \iff \frac{\mu_a - \mu_b}{\sqrt{\sigma_a^2 + \sigma_b^2}} \le u^*(w_a, w_b)$, where $u^*$ is the unique root of $h(u) = 0$.
- **Theorem 4 (Causal Uncertainty Lower Bound):** Any online causal scheduler satisfies $\mathbb{E}[\mathcal{X}] \ge \frac{\sigma_Z}{\sqrt{2\pi}} e^{-u^2/2}$.

**Formal Assumptions:** Specified in `theory/assumptions.md` (Assumptions A1–A10).  
**Counterexamples:** Documented in `theory/counterexamples.md` (Counterexamples 1–3).

---

## 4. Code Architecture and Implementation Locations

- `src/mlo_sim/core.py`:
  - `Packet`, `Flow`, `Link` data structures.
  - `BlockAckReceiver`: Standard IEEE 802.11be sliding window receiver implementing Theorem 1 orthogonal attribution.
- `src/mlo_sim/channel.py`:
  - `WirelessChannel`: EDCA backoff, CWmin/CWmax, slot times, PHY transmission duration, Rayleigh fading, and Gilbert-Elliott burst loss.
- `src/mlo_sim/schedulers.py`:
  - `compute_threshold_root()`: Newton-Raphson solver for Theorem 3 root $u^*$.
  - `gaussian_partial_expectation()`: $\mathbb{E}[Z^+]$ evaluator.
  - Schedulers: `SingleLinkScheduler` (SLO), `DefaultFifoScheduler` (FIFO), `RoundRobinScheduler`, `LowestLatencyScheduler`, `CongestionAwareScheduler`, `StaticPinningScheduler`, `RetransmissionSteeringScheduler`, `SASPScheduler` (proposed), `OracleScheduler` (offline lower bound).
- `src/mlo_sim/simulator.py`:
  - `MloSimulator`: Discrete-event engine managing Poisson arrivals, channel execution, and scheduling triggers.
- `src/mlo_sim/metrics.py`:
  - `compute_metrics()`: Calculates self-blocking, cross-blocking, goodput, p50/p95/p99 tail latencies, and Student-t confidence intervals.

---

## 5. Verification Commands

All commands run inside the project virtual environment:

```bash
# 1. Activate environment
source /home/adhyan/Desktop/wifi7_mlo_hol/.venv/bin/activate

# 2. Run unit and property tests (20 automated tests)
PYTHONPATH=. pytest tests/ -v

# 3. Run full experimental campaign (EXP-01 through EXP-07, 30 seeds each)
PYTHONPATH=. python experiments/scripts/run_campaign.py

# 4. Generate all publication figures (PDF and PNG, 300 DPI)
PYTHONPATH=. python experiments/scripts/plot_results.py

# 5. Compile LaTeX Manuscript
cd paper && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

---

## 6. Location of Experimental Results

- Summary CSVs: `experiments/results/`
  - `exp1_link_asymmetry.csv` (EXP-01: Delay asymmetry sweep across all 9 schedulers)
  - `exp2_window_collapse.csv` (EXP-02: Window stall boundary $\lambda / \lambda^*$)
  - `exp3_priority_heterogeneity.csv` (EXP-03: Flow priority ratio $w_2 / w_1 \in [1, 50]$)
  - `exp4_contention_loss.csv` (EXP-04: Frame error rate and burst loss)
  - `exp5_scalability.csv` (EXP-05: Multi-link scaling up to 4 links and 8 flows)
  - `exp6_estimation_robustness.csv` (EXP-06: Sensitivity to variance estimation bias $\pm 50\%$)
  - `exp7_ablation_study.csv` (EXP-07: 4-way ablation breakdown)
- Generated Figures: `experiments/plots/` (`fig1_asymmetry_sweep.pdf`, `fig2_window_collapse.pdf`, etc.)

---

## 7. Tasks Claude Should Perform First

1. **Verify Mathematical Proofs:** Check the derivation of $h'(u) = w_a(1-\Phi(u)) + w_b\Phi(u)$ in `theory/derivation.md` to ensure zero possibility of algebraic gaps.
2. **Review LaTeX Paper Draft:** Check `paper/main.tex` and ensure all equation labels, figure references, and citations in `paper/references.bib` are properly linked and compiled.
3. **Audit Code-Model Divergence:** Verify that `SASPScheduler` in `src/mlo_sim/schedulers.py` strictly adheres to Theorem 3 without heuristic shortcuts.
4. **Reproduce End-to-End Campaign:** Execute `pytest` and `run_campaign.py` to confirm identical numerical reproduction on different execution runs.
