# BASELINE EXECUTION & PRESERVATION INVENTORY
**Date:** October 13, 2026 (22:12 IST)  
**Host:** Linux 7.2.4-arch1-2 x86_64, GCC 16.2.1, Python 3.14.7, CMake 4.4.4, Ninja 1.13.0  
**Repository:** `/home/adhyan/Desktop/wifi7_mlo_hol/`  
**Git Remote (Read-Only):** `git@github.com:adhyan-jain/computer_network_research.git`

---

## 1. Baseline Backup & Manifest Verification
1. **Historical Baseline Backup (`backup_20261013_1525/`):**
   - Manifest File: `backup_20261013_1525_manifest.sha256`
   - Manifest File SHA-256: `f8074748fe4d8d0c330f26097cef754c61d8c693523f234c0942397a4a925485` (MATCH VERIFIED)
   - File-by-file verification (`sha256sum -c backup_20261013_1525_manifest.sha256`): 78 files checked, 78 OK, 0 failures.
2. **Pre-Audit Working Snapshot (`backup_pre_final_audit/`):**
   - Directory present and verified intact.
3. **Execution Phase Timestamped Backup (`backup_20261013_2212/`):**
   - Created at `/home/adhyan/Desktop/wifi7_mlo_hol/backup_20261013_2212/` outside all experiment results directories.
   - Preserves: `src/`, `tests/`, `theory/`, `paper/`, `docs/`, `pyproject.toml`, `README.md`, `FINAL_REPORT.md`, `experiments/ablation_phase6/`.
   - Manifest File: `backup_20261013_2212_manifest.sha256`
   - Manifest File SHA-256: `41d1be29943180b89ce6937749ef6ccb6314ccb0a651beb53da1f8ec515d0fa1`

---

## 2. Baseline Test Suite Status
- Command: `.venv/bin/pytest tests/ -v`
- Result: **44 passed in 1.03s**
- Modules:
  - `tests/test_adversarial.py` (3 tests)
  - `tests/test_ba_window.py` (2 tests)
  - `tests/test_decomposition.py` (2 tests)
  - `tests/test_deterministic_scenarios.py` (7 tests)
  - `tests/test_mathematical_repair.py` (9 tests)
  - `tests/test_pairwise_transitivity.py` (5 tests)
  - `tests/test_rebuilt_sequencing.py` (3 tests)
  - `tests/test_schedulers.py` (9 tests)
  - `tests/test_threshold.py` (4 tests)

---

## 3. Baseline Manuscript State
- `paper/main.tex`: `f7c104bd6c3c645fcbae068508a8de99c6fc4af75ba02051d34da7f011e65d1e`
- `paper/references.bib`: `ffaa9e3b03bae8af1ac11b6ae18d439c5780ba4ab4a715faf54cc8b3ec6f7fbd`
- `paper/main.pdf`: `71ac05bfd77294ba84579791171d741d3fc045d451f31d2582e4a4408c755694`
- Existing compiled PDF preserved in backup `backup_20261013_2212/paper/main.pdf`.

---

## 4. Historical Experiment Inventory (Immutable)
- Historical CSVs in `experiments/results/`:
  - `exp1_link_asymmetry.csv` (72 rows)
  - `exp2_window_collapse.csv` (32 rows)
  - `exp3_priority_heterogeneity.csv` (18 rows)
  - `exp4_contention_loss.csv` (24 rows)
  - `exp5_scalability.csv` (18 rows)
  - `exp6_estimation_robustness.csv` (7 rows)
  - `exp7_ablation_study.csv` (4 rows)
- Phase 6 Ablation CSVs in `experiments/ablation_phase6/`:
  - `raw_runs.csv` (2,160 rows)
  - `summary_ablation.csv` (72 rows)
  - `audit_statistical_summary.csv` (18 rows)

All historical files remain strictly untouched.

---

## 5. Manifest of Files to be Created or Modified
### Files to be created:
- `validation/ns3/`:
  - `README.md`
  - `fetch_ns3.sh`
  - `build_ns3.sh`
  - `run_smoke.sh`
  - `run_main_campaign.sh`
  - `run_threshold_ablation.sh`
  - `analyze_results.py`
  - `preregistration.md`
  - `configs/`
  - `patches/`
  - `src/`
  - `tests/`
  - `results/`
  - `logs/`
- `docs/NS3_VALIDATION_FINAL_REPORT.md`

### Files to be modified (after validation evidence is established):
- `docs/FINAL_RESEARCH_GO_NO_GO.md`
- `paper/main.tex`
- `paper/references.bib`
- `paper/main.pdf`
