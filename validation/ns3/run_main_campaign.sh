#!/usr/bin/env bash
# calibration (FIFO only) -> freeze -> 810-run main campaign -> analysis. Fails on any error.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$HERE"; PY="$HERE/../../.venv/bin/python"
[ -f configs/conditions.json ] || "$PY" calibrate.py
[ -f configs/FREEZE.json ]     || "$PY" freeze.py
"$PY" run_campaign.py main
"$PY" analyze_results.py --only main
