#!/usr/bin/env bash
# build_ns3.sh - reproducible build of the patched ns-3.47 + experiment programs.
#   ./build_ns3.sh            optimized patched tree  (ns-3.47)            -> campaigns
#   ./build_ns3.sh stock      pristine tree           (ns-3.47.stock)      -> Gate-1 baseline
#   ./build_ns3.sh debug      patched, asserts+logs   (ns-3.47.dbg)        -> regression tests
# Exits non-zero on ANY failing stage (set -e + explicit checks). Logs under logs/.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$HERE/logs"; mkdir -p "$LOG"
KIND="${1:-optimized}"
MODULES=wifi,network,internet,applications,stats,core,mobility,spectrum,propagation,antenna
case "$KIND" in
  optimized) TREE=ns-3.47;       PROFILE=optimized; PATCHED=1; EXTRA="";;
  debug)     TREE=ns-3.47.dbg;   PROFILE=debug;     PATCHED=1; EXTRA="--disable-werror";;   # GCC 16 -Werror trips on an untouched ns-3 file
  stock)     TREE=ns-3.47.stock; PROFILE=optimized; PATCHED=0; EXTRA="";;
  *) echo "usage: $0 [optimized|debug|stock]"; exit 64;;
esac
"$HERE/fetch_ns3.sh" "$TREE"
cd "$HERE/$TREE"
{
  echo "=== BUILD ENVIRONMENT ($KIND) $(date -Iseconds)"
  echo "OS/kernel : $(uname -srvm)"; echo "compiler  : $(c++ --version | head -1)"
  echo "cmake     : $(cmake --version | head -1)"; echo "ninja     : $(ninja --version)"
  echo "python    : $(python3 --version)"; echo "ns-3      : $(cat VERSION) (archive sha256 $(sha256sum "$HERE/downloads/ns-3.47.tar.bz2" | cut -c1-16)...)"
  echo "modules   : $MODULES"; echo "profile   : $PROFILE $EXTRA  examples=off tests=off"
} | tee "$LOG/build_env_$KIND.log"

if [ "$PATCHED" = 1 ]; then
  for p in "$HERE"/patches/*.patch; do
    if patch -p1 -s --dry-run -N < "$p" >/dev/null 2>&1; then echo "[build] applying $(basename "$p")"; patch -p1 -s -N < "$p"
    elif patch -p1 -s --dry-run -R < "$p" >/dev/null 2>&1; then echo "[build] already applied: $(basename "$p")"
    else echo "[build] PATCH DOES NOT APPLY CLEANLY: $p" >&2; exit 3; fi
  done
  mkdir -p scratch/sasp-mlo-experiment scratch/stock-mlo-baseline
  ln -sf "$HERE/src/sasp-mlo-experiment.cc" scratch/sasp-mlo-experiment/sasp-mlo-experiment.cc
  ln -sf "$HERE/src/sasp-policy.h"          scratch/sasp-mlo-experiment/sasp-policy.h
  ln -sf "$HERE/src/stock-mlo-baseline.cc"  scratch/stock-mlo-baseline/stock-mlo-baseline.cc
else
  mkdir -p scratch/stock-mlo-baseline; cp "$HERE/src/stock-mlo-baseline.cc" scratch/stock-mlo-baseline/
fi
./ns3 configure --build-profile="$PROFILE" $EXTRA --enable-modules="$MODULES" --disable-examples --disable-tests 2>&1 | tee "$LOG/configure_$KIND.log" | tail -3
./ns3 build 2>&1 | tee "$LOG/build_$KIND.log" | tail -3
echo "[build] $KIND OK"
