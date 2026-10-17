#!/usr/bin/env bash
# fetch_ns3.sh - deterministic acquisition of the pinned ns-3.47 release (no network if cached).
# The official release page publishes no checksum; EXPECTED_SHA256 below is the SHA-256 of the
# official tarball as downloaded on 2026-10-13 (https://www.nsnam.org/releases/ns-3.47.tar.bz2,
# Last-Modified 2026-02-17). Any different archive is rejected.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCH="$HERE/downloads/ns-3.47.tar.bz2"
EXPECTED_SHA256="8b3adca956c834ea436b915986ab8fd053e90041acae7426895d595aaa3ccc39"
URL="https://www.nsnam.org/releases/ns-3.47.tar.bz2"
mkdir -p "$HERE/downloads"
[ -f "$ARCH" ] || curl -L --fail --retry 3 -o "$ARCH" "$URL"
GOT="$(sha256sum "$ARCH" | awk '{print $1}')"
if [ "$GOT" != "$EXPECTED_SHA256" ]; then echo "[fetch] CHECKSUM MISMATCH: $GOT" >&2; exit 2; fi
echo "[fetch] archive sha256 OK ($GOT)"
# extract a pristine tree into the given directory (default: ns-3.47) if absent
extract() { local d="$HERE/$1"; if [ -d "$d" ]; then echo "[fetch] $1 exists, not touching"; return; fi
  mkdir -p "$d" && tar -xjf "$ARCH" -C "$d" --strip-components=1 && echo "[fetch] extracted pristine -> $1"; }
for t in "$@"; do extract "$t"; done
[ $# -gt 0 ] || extract ns-3.47
