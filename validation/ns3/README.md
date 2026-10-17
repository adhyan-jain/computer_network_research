# ns-3.47 validation of sequence-assignment scheduling (SASP / Mean-Only / FIFO)

Independent packet-level check of the Python-simulator results, using a pinned ns-3.47 STR-MLO model.
**Start with `../../docs/NS3_VALIDATION_FINAL_REPORT.md`** (decision, evidence, limitations).

| Path | Content |
|---|---|
| `preregistration.md` | locked design, endpoints, statistics (written before the comparative runs) |
| `fetch_ns3.sh`, `build_ns3.sh [stock\|debug]`, `run_smoke.sh` | reproducible acquisition (checksum-pinned), strict patching, build, Gate-1 smoke |
| `patches/0001`, `0002` | the only modifications to ns-3.47 (sequence-reservation hook at `QosTxop::GetNextMpdu`; read-only receiver observer) |
| `src/` | `sasp-policy.h` (pure policy), `sasp-mlo-experiment.cc` (experiment), `stock-mlo-baseline.cc` (Gate 1, stock APIs only) |
| `calibrate.py` → `configs/conditions.json`; `freeze.py` → `configs/FREEZE.json` | FIFO-only calibration; hash freeze checked by the runner |
| `run_campaign.py`, `run_main_campaign.sh`, `run_threshold_ablation.sh` | 810 + 810 runs; per-run files, gzipped decision logs, `invalid/` for failures |
| `analyze_results.py`, `cross_simulator.py`, `make_paper_tables.py`, `audit_claims.py` | analysis from raw CSV only, Python-vs-ns-3 comparison, paper tables, independent numeric audit |
| `tests/` | 25 tests (policy vs Python reference, patch==tree, 10 scenario classes, bypass/causality controls, analysis on planted effects) |
| `results/` | `calibration/`, `main_campaign/`, `threshold_ablation/`, `analysis/`, `invalid_agy_run1/` (quarantined invalid earlier attempt) |
| `logs/` | build environment/compiler logs, Gate-1 logs and traces |
| `DELIVERABLES.sha256` | hash manifest of sources, patches, raw results, analysis outputs, manuscript |

Third-party trees (`ns-3.47*/`, `downloads/`) are not part of the deliverable; `fetch_ns3.sh` + `build_ns3.sh` + the two patches rebuild them.
Run the tests with the project venv: `.venv/bin/python -m pytest validation/ns3/tests -q`.
No result here is hardware or firmware evidence.
