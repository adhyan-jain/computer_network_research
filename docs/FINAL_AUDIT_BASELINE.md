# FINAL AUDIT BASELINE REPORT

**Audit Date & Time:** October 13, 2026 (18:05 IST)  
**Repository Path:** `/home/adhyan/Desktop/wifi7_mlo_hol/`  
**Git Remote:** `git@github.com:adhyan-jain/computer_network_research.git`  
**Current Git Head:** Commit `bbd68be` on branch `master`  
**Auditor:** Independent Research Auditor & Verification Specialist  

---

## 1. Executive Summary & Purpose

This report establishes the verified, ground-truth physical state of the Wi-Fi 7 MLO Cross-Flow HOL / SASP repository prior to the execution of the final scientific, mathematical, implementation, statistical, and novelty audit.

In accordance with audit directives:
- No claims from previous summaries or handoff documents are accepted on trust.
- Every file path, line count, test execution, CSV record, and build output was directly verified on the host system.
- The immutable historical backup `backup_20261013_1525/` and its cryptographic hash manifest are verified and preserved.
- A pre-audit snapshot of the working state has been created at `backup_pre_final_audit/`.
- Historical CSVs in `experiments/results/` are locked and will never be overwritten.
- All new evaluation and verification runs will be placed in dedicated directories.

---

## 2. Version Control, Backup & Preservation Integrity

1. **Git State:**
   - Commit: `bbd68be: Phase 8: Final independent review and research decision (CONDITIONAL GO)`
   - Branch: `master`
   - Non-negotiable audit protocol: Zero commits, pushes, submissions, or git re-initializations will occur during this audit.
2. **Preservation Backups:**
   - Primary timestamped backup: `backup_20261013_1525/` (matches commit `a759df3`).
   - Hash manifest file: `backup_20261013_1525_manifest.sha256` (SHA-256: `f8074748fe4d8d0c330f26097cef754c61d8c693523f234c0942397a4a925485`).
   - Secondary historical backup: `legacy_v1_backup/` intact.
   - Pre-audit current state snapshot: `backup_pre_final_audit/` created outside all experiment output directories.

---

## 3. Test Suite Verification

- **Environment:** Linux x86_64, Python 3.14.7, pytest 9.1.1 (`.venv/bin/pytest`)
- **Execution Command:** `.venv/bin/pytest tests/ -v`
- **Result:** **39 passed in 2.44s** (Exit code: 0)

### Module Breakdown
| Test Module | Test Count | Result | Scope / Identities Tested |
| :--- | :---: | :---: | :--- |
| `tests/test_adversarial.py` | 3 | PASSED | Zero variance, 100x delay asymmetry, tiny window ($W=2$) |
| `tests/test_ba_window.py` | 2 | PASSED | Monotonic sliding window release, forced advance upon gap |
| `tests/test_decomposition.py` | 2 | PASSED | Theorem 1 identity ($\Delta \equiv \mathcal{S} + \mathcal{X}$), attribution invariance |
| `tests/test_rebuilt_sequencing.py` | 3 | PASSED | Predictive sequence inversion, stall mitigation, intra-flow monotonicity |
| `tests/test_schedulers.py` | 9 | PASSED | Functional API execution across all 9 schedulers |
| `tests/test_threshold.py` | 4 | PASSED | Symmetry ($u^*(w,w)=0$), direction, root accuracy, Gaussian expectation |
| `tests/test_mathematical_repair.py` | 9 | PASSED | Theorem 1 counterexample, Theorem 2 Poisson tail stall probabilities, Theorem 3 derivative positivity & Brent root comparison, Theorem 4 falsification of $\sigma_Z \phi(u)$ and symmetric floor |
| `tests/test_deterministic_scenarios.py` | 7 | PASSED | Scenarios 1–7: Identical links, fast/slow predictive inversion, unequal variances, unequal priorities, in-flight penalty, window exhaustion, environment isolation |
| **Total** | **39** | **ALL PASSED** | |

---

## 4. Experiment CSV Inventory & Verification

### Historical Experiment CSVs (`experiments/results/`)
| File Name | Header | Data Rows | Total Lines | Parameters Tested |
| :--- | :---: | :---: | :---: | :--- |
| `exp1_link_asymmetry.csv` | 1 | 72 | 73 | 8 delay asymmetries $	imes$ 9 schedulers |
| `exp2_window_collapse.csv` | 1 | 32 | 33 | 8 normalized loads $	imes$ 4 schedulers |
| `exp3_priority_heterogeneity.csv` | 1 | 18 | 19 | 6 weight ratios $	imes$ 3 schedulers |
| `exp4_contention_loss.csv` | 1 | 24 | 25 | 6 FER rates $	imes$ 4 schedulers |
| `exp5_scalability.csv` | 1 | 18 | 19 | 9 topology configs $	imes$ 2 schedulers |
| `exp6_estimation_robustness.csv` | 1 | 7 | 8 | 7 estimation bias factors |
| `exp7_ablation_study.csv` | 1 | 4 | 5 | 4 algorithmic variants |
| **Subtotal** | **7** | **175** | **182** | Across 30 random seeds each |

### Phase 6 Ablation Campaign CSVs (`experiments/ablation_phase6/`)
| File Name | Header | Data Rows | Total Lines | Verification Details |
| :--- | :---: | :---: | :---: | :--- |
| `raw_runs.csv` | 1 | 2,160 | 2,161 | 18 configurations $	imes$ 4 schedulers $	imes$ 30 seeds = 2,160 simulation runs |
| `summary_ablation.csv` | 1 | 72 | 73 | 18 configurations $	imes$ 4 schedulers = 72 aggregate rows with 95% CIs |

---

## 5. Manuscript Build Verification

- **Source:** `paper/main.tex`, `paper/references.bib`
- **Compiler:** pdfTeX, Version 3.141592653-2.6-1.40.29 (TeX Live 2026/Arch Linux)
- **Compilation Command:**
  ```bash
  pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
  ```
- **Output:** `paper/main.pdf`
- **Build Status:** Clean compilation, exit code 0.
- **Page Count:** Exactly 8 pages.
- **File Size:** 488,950 bytes.
- **Figures:** 6 vector PDF figures embedded from `experiments/plots/` (`fig1` through `fig6`).
- **Citations / References:** All references in `references.bib` resolve cleanly; 0 unresolved citation warnings in `main.log`.

---

## 6. Cryptographic Baseline SHA-256 Manifest

The following SHA-256 hashes establish the verified state of all primary files at the start of the final audit:

```text
# Python Simulator Core & Schedulers
56596bb06bdd9e6dbfc84c3cc67c79678eb222ef56ea36ac278357d2b81f61a0  src/mlo_sim/channel.py
3345359008ed3a40f5493a8e776d822d29869e6da88a1ce956748dba4e3fd6c3  src/mlo_sim/core.py
792953d7e2ab71b09f852027d4ecc5cdbd3269c98472e052133544280933ca79  src/mlo_sim/__init__.py
03c1d75fa73cc3f55db53a336224fbf7c39b96a181d0ee370c77f356f3cb34a6  src/mlo_sim/metrics.py
2937de235dbd167182f098cf5b0e3e95e39707df3e46f0bcfa4f5350fee7ad62  src/mlo_sim/schedulers.py
53d501a9e5b4778473955b6ccfd59f18d20ca547b981f79ab289337b957cf150  src/mlo_sim/simulator.py

# Test Suite
433ed7dedab1890aed1202487cb29d015b4a1a12b6ac065c9ba3fdcc8b16f60e  tests/test_adversarial.py
6219c905594dc6ed8f85b7ac6716a059626749444941efbdca8d042c3fdff8b0  tests/test_ba_window.py
555b3ab57171e421f4a87fa479ea5bbd405d492debcd0418e065694bee0fc13e  tests/test_decomposition.py
8efffda7286f7130e76ae4f53a4616a2b5b98f7b343f336a29c1e98e5f009a3a  tests/test_deterministic_scenarios.py
9729d58cf1828996f8042197bbbe882b17ee118630c42c0c79f2ef0ae568485d  tests/test_mathematical_repair.py
863ee477ef84b0163b4524c121e4b803334df5a286ec633d708b6cd807b0ab72  tests/test_rebuilt_sequencing.py
e188f52fa0e0b08cae6d8a8a03d7d948725a18cba889ed3aa12fa561fd98df0c  tests/test_schedulers.py
82602bccd4e450cf9216bc842c4addaedc5d1799f8a12d4a072b7832eebe73c5  tests/test_threshold.py

# Theoretical Derivations
b059aab7fe8bff3ebce99db8f5a18c45b2de2e2c548dd30d768034f6730602e1  theory/assumptions.md
017b24f86b1c79526c27c9d9ffb5b9ae6e581c4069f8869300e43207a0a595f6  theory/counterexamples.md
848fdb90b86de8a460d1c7aa79242bc1677691eac7a04d44ced01f045490b5e1  theory/derivation.md
dac4096e24b3adac97418d7173c526e42fed49ed80b72206c0ec68aa4f03a2b6  theory/problem_statement.md
65ce95e86be94ee402613f5bd6ec4e9b366e7732c9edf804f94e5f298710110b  theory/system_model.md
13a58f1716724418eb5309c3029de01152b93af775874951c7f43ac059d63c3a  theory/theorem_status.md

# Manuscript
7d80380019fae30ebee1c099831792bcca03d489dc89bd1f9be9c7c9cebfd8cd  paper/main.tex
6b144a29088ea0937b2278b294f7d4c5c3f1f111169644f097073b8e9ba6deb3  paper/references.bib

# Phase 6 Ablation Data & Script
c40308f42321e8030a782095ecc5a2e497305a0ce5b2f7e3be62616ff06fc824  experiments/ablation_phase6/run_ablation_campaign.py
93f4ab323a0786a2f4a8372b420181e0e993d993b7aa78281d128e34c3de5b86  experiments/ablation_phase6/raw_runs.csv
3c1321a474c811b12336adc99eb09ccb6a8ef76df06f6a80f4628585962f058f  experiments/ablation_phase6/summary_ablation.csv

# Historical Experiment Results
c33c2ec0fc149b1b8ddf78e6a08daa41ab4675477582008d33c3367cf4978e09  experiments/results/exp1_link_asymmetry.csv
398e0f3aa404c576781bdecfb0abb058aa7cdbcf11e44a1d32033fb65a77b80e  experiments/results/exp2_window_collapse.csv
1db66c0e7dd38cd6ed6c6fedfdeea8081085365e6dbb135b9079846d5b032cf3  experiments/results/exp3_priority_heterogeneity.csv
0503b2c610b5a7f36881ad5a089776e568c00b32f3bcff304355577929177114  experiments/results/exp4_contention_loss.csv
1533fe1b55adbae3b6c423d05771858de433615e599d1fb5cc29d0f130f49c46  experiments/results/exp5_scalability.csv
c9ca972f62e02523b4e27920d52637147d8f1087adcde4243811d3870161c8d3  experiments/results/exp6_estimation_robustness.csv
dba046fdb45c3c7d77982b4621fd61e923be454dd45323a5e756cdaef1addfee  experiments/results/exp7_ablation_study.csv
```

---

## 7. Critical Technical & Discrepancy Findings Identified During Baseline Audit

Initial direct inspection of the codebase has revealed several substantive technical issues requiring thorough resolution in subsequent phases:

1. **Multi-Frame Ordering & Cycle Vulnerability (Phase 2 Focus):**
   - In `src/mlo_sim/schedulers.py:412-421`, the code applies Theorem 3's threshold comparison **strictly when $N=2$** (`if self.use_variance and len(predictions) == 2:`).
   - When $N > 2$ candidates exist, SASP falls back to `predictions.sort(key=lambda x: x[0])`, which is Mean-Only Sequencing!
   - Furthermore, if a general pairwise comparator is used for multi-frame sorting, the pairwise preference relation may fail transitivity (generating Condorcet-style cycles $a \prec b \prec c \prec a$). This requires direct formal and empirical investigation.
2. **Phase 6 Ablation Campaign Discrepancies (Phase 3 Focus):**
   - In `experiments/ablation_phase6/run_ablation_campaign.py:85`, `links[1].contention_sigma_ms = 0.1 * sigma2_mult` is modified after instantiation, but `channels[1]` is instantiated without passing `contention_sigma_ms`.
   - `WirelessChannel` defaults to `0.1` ms. Consequently, in the physical channel simulation, the channel contention noise variance was identical (0.1 ms) across all multiplier levels ($\sigma_2 / \sigma_1 \in \{1, 2, 5, 10\}$)! This explains why summary values across Regime C are numerically identical.
   - Common Random Number (CRN) synchronization: In `simulator.py`, the same `self.rng` instance is consumed for packet arrivals, contention backoff draws, and packet error sampling. Different scheduling decisions alter the order and timing of RNG calls, causing the sequence of packet arrivals to diverge across arms.
   - Multiple comparisons: 18 configurations were tested. The claimed significant gains ($p=0.032, p=0.038$) must be audited under family-wise error rate (FWER) and false discovery rate (FDR) corrections.
3. **Protocol Feasibility & Claim Boundaries (Phase 4 Focus):**
   - Historical docs claimed "100% compliant" and "strictly transmitter-deployable".
   - The distinction between a Python simulator model, a feasible architectural design proposal, and an experimentally validated hardware MAC must be strictly enforced.

---
*End of Final Audit Baseline Report. Proceeding to Phase 2.*
