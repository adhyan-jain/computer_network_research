#!/usr/bin/env bash
# run_smoke.sh - Gate-1 baseline on pristine vs patched ns-3, then a 3-arm smoke run. Non-zero on failure.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$HERE"; mkdir -p logs
B=build/scratch/stock-mlo-baseline/ns3.47-stock-mlo-baseline-optimized
for t in ns-3.47.stock ns-3.47; do
  LD_LIBRARY_PATH="$HERE/$t/build/lib" "$HERE/$t/$B" --seed=1 --simTime=2 --traceFile="logs/gate1_trace_$t.csv" | tee "logs/gate1_$t.log"
done
cmp "logs/gate1_trace_ns-3.47.stock.csv" "logs/gate1_trace_ns-3.47.csv" \
  && echo "[smoke] pristine and patched(no hook) traces are IDENTICAL"
for s in 0 1 2; do
  "$HERE/../../.venv/bin/python" - <<PY
import sys; sys.path.insert(0, "$HERE"); import nsrun
r = nsrun.run(dict(simTime=3, scheduler=$s, seed=1, bulkMbps=30, mcs0=1, mcs1=7))
print("[smoke] arm=$s ok: ls_rcvd=%d cross_wait_ms=%.4f audits clean" % (r["ls_rcvd"], r["cross_wait_ms"]))
PY
done
