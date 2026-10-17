#!/usr/bin/env bash
# 810-run variance-aware threshold ablation (requires calibration + freeze from run_main_campaign.sh).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$HERE"; PY="$HERE/../../.venv/bin/python"
"$PY" run_campaign.py ablation
"$PY" analyze_results.py
