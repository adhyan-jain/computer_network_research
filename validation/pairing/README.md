# Cross-flow reordering blame in Wi-Fi 7 MLO (validation/pairing)

Authors: Adhyan Jain, Atharva Sheersh Pandey, Kshitij Manikshete. Simulation-only research code, preregistered studies, and two manuscripts.

## What this project claims (one paragraph)
In a shared reorder buffer a packet's cross-flow blocking is the maximum "lateness" of the other flows, so each packet defines an **airport game**. This gives an exact, replay-free, closed-form Shapley blame; proves that leave-one-out and the usual "last arrival takes all" rules are degenerate; extends the structure to receivers with a finite window and hold timer (with a bounded error and a per-packet applicability certificate); and is confirmed by exact oracles on our simulator, on synthetic generators, and on ns-3.47's own reorder buffer. Read the manuscript for scope and limits.

## Start here
| File | What it is |
|---|---|
| `paper/theory/main_theory.pdf` | Main manuscript (theory + validation), source `main_theory.tex` |
| `paper/main.pdf` | Companion measurement paper (interventional externality, single-trace explained-fraction bound) |
| `AUDIT_REPORT.md` | Full audit: integrity checks, independent recomputation, failures, remaining gaps |
| `decisions.md` | Log of every major decision (D01-D33) |
| `NOVELTY_SUMMARY.md` | One-page novelty and limits summary for presentation |
| `PRESENTATION_GUIDE.pdf` | How to explain it: 30-second pitch, board example, talk outlines, demo, likely questions |

## Studies (each preregistered, hashed, committed before its data)
| Study | Preregistration | Runner / analysis | Results |
|---|---|---|---|
| 1 simulator audit | `PREREGISTRATION*.md` | `run_study.py`, `analyze.py` | `results/raw_*.csv`, `analysis_numbers.json` |
| 2 explained fraction, blame | `PREREGISTRATION_STUDY2.md` | `run_study2.py`, `analyze_study2.py` | `results/*s2*` |
| 3 pinned links, ns-3 replication | `PREREGISTRATION_STUDY3.md` | `run_study3*.py`, `analyze_study3*.py` | `results/*s3*` |
| 4 explained-fraction bound | `PREREGISTRATION_STUDY4.md` | `run_study4.py`, `analyze_study4.py` | `results/*s4*` |
| 5 airport-game theory | `PREREGISTRATION_STUDY5.md` | `run_study5.py`, `analyze_study5.py`, `airport.py` | `results/*s5*` |
| 6 windows, timers, ns-3 buffer | `PREREGISTRATION_STUDY6.md` | `run_study6.py`, `analyze_study6.py`, `study6.py` | `results/*s6*` |

Each study has `results/STUDY*_RAW.sha256` (or `RAW_AND_ANALYSIS.sha256`) and `PREREGISTRATION*.sha256`. Runners refuse to run if a preregistration hash changed or results already exist.

## Reproduce
```bash
cd validation/pairing
../../.venv/bin/python -m pytest -q tests          # 131 tests
../../.venv/bin/python analyze_study6.py            # regenerates results/analysis_study6.json from the stored raw CSVs
../../.venv/bin/python paper/theory/make_numbers_theory.py   # regenerates every number/table in the manuscript
cd paper/theory && pdflatex main_theory && bibtex main_theory && pdflatex main_theory && pdflatex main_theory
```
Re-running the single-use runners is deliberately blocked once results exist; to regenerate raw data, move the results aside and re-run (ns-3 runs need the built binary: `validation/ns3/build_ns3.sh`).

## Code map
- `src/mlo_sim/`: the original simulator (unmodified by this work). `validation/ns3/`: the frozen ns-3.47 experiment, patches and configs.
- `study.py`, `study2.py`, `study6.py`: harnesses (keyed random numbers, coalition replay, window/timer receiver). `airport.py`, `airport_fast.py`: airport-game blame, oracles, Poisson closed form.
- `paper/`: manuscripts, generated numbers and tables (`make_numbers*.py`).

## Honest status
Simulation only; no hardware or public external trace. Preregistered failures and null results are kept in the papers and in `AUDIT_REPORT.md`. Affiliations, funding and the public archive URL are placeholders in the manuscript.
