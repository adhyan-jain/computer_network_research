# AUDIT BASELINE REPORT (PHASE 0)

**Date & Time:** October 13, 2026 (15:30 IST)  
**Repository Path:** `/home/adhyan/Desktop/wifi7_mlo_hol/`  
**Git Remote:** `git@github.com:adhyan-jain/computer_network_research.git`  
**Branch:** `master` (Commit `a759df3`)  
**Timestamped Backup:** `/home/adhyan/Desktop/wifi7_mlo_hol/backup_20261013_1525/`

---

## 1. Executive Summary & Purpose

This baseline audit establishes the ground-truth state of the Wi-Fi 7 MLO SASP research repository prior to Phase 1 mathematical repair, Phase 2 protocol feasibility auditing, and subsequent verification gates. 

Per audit protocol:
- No claims are accepted on trust from previous agent summaries.
- Exact hashes, file sizes, test logs, and build artifacts are recorded.
- Historical raw results in `experiments/results/` are locked and will never be overwritten.
- All subsequent experiments will use dedicated directories (`experiments/ablation_phase6/`, etc.).

---

## 2. Version Control & Backup Integrity

1. **Git Initialization:**
   - Git repository initialized on `master`.
   - Remote added: `origin -> git@github.com:adhyan-jain/computer_network_research.git`.
   - Rule enforcement: Local commits only. Remote push is strictly disabled / reserved for user.
   - Initial commit: `a759df3: Baseline: Wi-Fi 7 MLO SASP repository state prior to mathematical repair and audit`.
2. **Preservation Backup:**
   - A complete timestamped mirror was created at `backup_20261013_1525/` containing copies of `src/`, `tests/`, `theory/`, `paper/`, `experiments/`, `docs/`, `README.md`, `FINAL_REPORT.md`, and `pyproject.toml`.
   - Historical backup `legacy_v1_backup/` remains preserved.

---

## 3. Test Suite Status

Command: `.venv/bin/pytest tests/ -v` (pytest 9.1.1, Python 3.14.7)  
Result: **23 passed in 1.00s**

| Test Module | Tests | Status | Target Verifications |
| :--- | :---: | :---: | :--- |
| `tests/test_adversarial.py` | 3 | PASSED | Zero variance, 100x asymmetry, tiny window ($W=2$) |
| `tests/test_ba_window.py` | 2 | PASSED | Sliding window monotonic release, forced advance |
| `tests/test_decomposition.py` | 2 | PASSED | Theorem 1 identity ($\Delta \equiv \mathcal{S} + \mathcal{X}$), attribution invariance |
| `tests/test_rebuilt_sequencing.py` | 3 | PASSED | Predictive inversion, stall mitigation, intra-flow monotonicity |
| `tests/test_schedulers.py` | 9 | PASSED | Standard API execution across all 9 schedulers |
| `tests/test_threshold.py` | 4 | PASSED | Theorem 3 symmetry ($u^*(w,w)=0$), direction, root accuracy, Gaussian expectation identities |

*Note:* While the existing 23 tests pass, they test specific identities and configurations; they do not stress the mathematical flaws identified in Theorems 2 and 4 (such as non-universal lower bound or stochastic window collapse).

---

## 4. Current Experiment Files & Row Counts

Historical CSVs in `experiments/results/`:

| File Name | Header Lines | Data Rows | Total Lines | Parameters Evaluated |
| :--- | :---: | :---: | :---: | :--- |
| `exp1_link_asymmetry.csv` | 1 | 72 | 73 | 8 delay asymmetries $\times$ 9 schedulers |
| `exp2_window_collapse.csv` | 1 | 32 | 33 | 8 normalized loads $\times$ 4 schedulers |
| `exp3_priority_heterogeneity.csv` | 1 | 18 | 19 | 6 weight ratios $\times$ 3 schedulers |
| `exp4_contention_loss.csv` | 1 | 24 | 25 | 6 FER rates $\times$ 4 schedulers |
| `exp5_scalability.csv` | 1 | 18 | 19 | 9 topology configs $\times$ 2 schedulers |
| `exp6_estimation_robustness.csv` | 1 | 7 | 8 | 7 estimation bias factors |
| `exp7_ablation_study.csv` | 1 | 4 | 5 | 4 algorithmic variants |
| **Total** | **7** | **175** | **182** | Across 30 random seeds each |

---

## 5. Manuscript Build Verification

Manuscript source: `paper/main.tex`  
Compilation command: `pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex`  
- Output: `paper/main.pdf` (8 pages, 502,227 bytes).
- Build status: **Clean exit code 0**, all references and citations resolved, 6 vector figures included.
- Warning logs: Contains minor underfull hbox warnings on text layout and table styling, but zero compilation errors.

---

## 6. Baseline SHA-256 Hash Manifest

The following cryptographic hashes establish the immutable baseline for the audited files:

```text
# Python Source
56596bb06bdd9e6dbfc84c3cc67c79678eb222ef56ea36ac278357d2b81f61a0  src/mlo_sim/channel.py
3345359008ed3a40f5493a8e776d822d29869e6da88a1ce956748dba4e3fd6c3  src/mlo_sim/core.py
792953d7e2ab71b09f852027d4ecc5cdbd3269c98472e052133544280933ca79  src/mlo_sim/__init__.py
03c1d75fa73cc3f55db53a336224fbf7c39b96a181d0ee370c77f356f3cb34a6  src/mlo_sim/metrics.py
2937de235dbd167182f098cf5b0e3e95e39707df3e46f0bcfa4f5350fee7ad62  src/mlo_sim/schedulers.py
53d501a9e5b4778473955b6ccfd59f18d20ca547b981f79ab289337b957cf150  src/mlo_sim/simulator.py

# Tests
433ed7dedab1890aed1202487cb29d015b4a1a12b6ac065c9ba3fdcc8b16f60e  tests/test_adversarial.py
6219c905594dc6ed8f85b7ac6716a059626749444941efbdca8d042c3fdff8b0  tests/test_ba_window.py
555b3ab57171e421f4a87fa479ea5bbd405d492debcd0418e065694bee0fc13e  tests/test_decomposition.py
863ee477ef84b0163b4524c121e4b803334df5a286ec633d708b6cd807b0ab72  tests/test_rebuilt_sequencing.py
e188f52fa0e0b08cae6d8a8a03d7d948725a18cba889ed3aa12fa561fd98df0c  tests/test_schedulers.py
82602bccd4e450cf9216bc842c4addaedc5d1799f8a12d4a072b7832eebe73c5  tests/test_threshold.py

# Experiment Scripts
bf892effb8d10a38be505e9ed624beb0f38496c77e0c5d85a04305ca9849fc44  experiments/scripts/plot_results.py
ff843cd9ec2f937bd98a00549f860d1f2c3f680d907aed19bf08b2ada4fd0aa6  experiments/scripts/run_campaign.py

# Raw Historical Results
c33c2ec0fc149b1b8ddf78e6a08daa41ab4675477582008d33c3367cf4978e09  experiments/results/exp1_link_asymmetry.csv
398e0f3aa404c576781bdecfb0abb058aa7cdbcf11e44a1d32033fb65a77b80e  experiments/results/exp2_window_collapse.csv
1db66c0e7dd38cd6ed6c6fedfdeea8081085365e6dbb135b9079846d5b032cf3  experiments/results/exp3_priority_heterogeneity.csv
0503b2c610b5a7f36881ad5a089776e568c00b32f3bcff304355577929177114  experiments/results/exp4_contention_loss.csv
1533fe1b55adbae3b6c423d05771858de433615e599d1fb5cc29d0f130f49c46  experiments/results/exp5_scalability.csv
c9ca972f62e02523b4e27920d52637147d8f1087adcde4243811d3870161c8d3  experiments/results/exp6_estimation_robustness.csv
dba046fdb45c3c7d77982b4621fd61e923be454dd45323a5e756cdaef1addfee  experiments/results/exp7_ablation_study.csv

# Theory Formulations
b059aab7fe8bff3ebce99db8f5a18c45b2de2e2c548dd30d768034f6730602e1  theory/assumptions.md
2bfd7e0c263b92dcac59c12c99a2aee3e0fbac6bf3ac057fb2d4f6d388dd1d6b  theory/counterexamples.md
1aabc5e2f8aa5b99d63c873cf5445c43a4126abfd0d1527ba3ae4db1605feaa8  theory/derivation.md
dac4096e24b3adac97418d7173c526e42fed49ed80b72206c0ec68aa4f03a2b6  theory/problem_statement.md
65ce95e86be94ee402613f5bd6ec4e9b366e7732c9edf804f94e5f298710110b  theory/system_model.md
7065ca0dc04641a4bd2fb35b27171519ef88aac972c218c172460f16dc038119  theory/theorem_status.md

# Manuscript
b1c1084f747fd3db8008a26f7a77bb8b6a5a5126ba673e816b5886b34ebe45b7  paper/main.tex
```

---

## 7. Immediate Mathematical Deficiencies Flagged for Phase 1

1. **Theorem 4 Inequality Flaw:**
   - In `theory/derivation.md` line 132, the step claiming $\mathbb{E}[(-Z)^+] = \sigma_Z [\phi(u) - u(1 - \Phi(u))] \ge \sigma_Z \phi(u)$ is mathematically false for all $u > 0$.
   - Counterexample: $d = 2\sigma_Z \implies \mathbb{E}[(-Z)^+] \approx 0.00849\sigma_Z < 0.05399\sigma_Z = \sigma_Z \phi(2)$.
   - The universal causal bound as stated does not hold and must be formally repaired or replaced with an exact characterization.
2. **Theorem 2 "Almost Surely" Stall Collapse:**
   - The claim that crossing $\lambda^* = W/\delta$ leads to buffer stall "almost surely" is mathematically invalid for finite Poisson arrival rates where $\Pr(N < W) > 0$.
   - Must be reformulated in terms of exact Poisson tail stall probabilities $\Pr(N \ge W) = 1 - \sum_{k=0}^{W-1} \frac{(\lambda\delta)^k e^{-\lambda\delta}}{k!}$, mean queue drift, and finite-horizon buffer overflow analysis.
3. **Theorem 1 Accounting Identity Status:**
   - $\Delta_i \equiv \mathcal{S}_i + \mathcal{X}_i$ is an exact post-facto reorder accounting identity on an observed trace. Lemma 1 attribution invariance does not hold counterfactually under shared medium contention. This must be explicitly acknowledged as an analytical accounting tool rather than an immutable physical conservation law.
4. **Theorem 3 Pairwise vs. Multi-frame Scope:**
   - Theorem 3 is proved strictly for pairwise candidate frames. For $N \ge 3$ frames, joint order statistics render greedy pairwise sorting a heuristic, not a globally optimal policy.

---
*End of Baseline Report. Proceeding to Phase 1.*
