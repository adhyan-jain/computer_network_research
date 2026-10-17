"""nsrun.py - thin, strict wrapper around the ns-3.47 sasp-mlo-experiment binary.

Every call returns the parsed one-row CSV as a dict of floats/strings. A nonzero exit, a missing
row, a malformed row or any failed runtime audit raises RuntimeError (fail loudly).
"""
import csv
import io
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE_DIRS = {"optimized": HERE / "ns-3.47", "debug": HERE / "ns-3.47.dbg"}
EXE = "build/scratch/sasp-mlo-experiment/ns3.47-sasp-mlo-experiment-{profile}"
TEXT_COLS = {"cond", "load", "build_id"}


def binary(profile="optimized"):
    root = PROFILE_DIRS[profile]
    return root / EXE.format(profile=profile), root / "build" / "lib"


def run(args, profile="optimized", timeout=3600, check_audit=True):
    exe, lib = binary(profile)
    env = dict(os.environ, LD_LIBRARY_PATH=str(lib))
    cmd = [str(exe)] + [f"--{k}={v}" for k, v in args.items()]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"ns-3 run failed rc={p.returncode}: {' '.join(cmd)}\n{p.stderr[-2000:]}")
    return parse_row(p.stdout, check_audit)


def parse_row(text, check_audit=True):
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) != 2 or len(rows[0]) != len(rows[1]):
        raise RuntimeError(f"malformed result CSV ({len(rows)} rows)")
    d = {}
    for h, v in zip(rows[0], rows[1]):
        d[h] = v if h in TEXT_COLS else float(v)
    if check_audit:
        for k in ("audit_sn_changed", "audit_intra_flow_inv", "audit_sn_dup"):
            if d[k] != 0:
                raise RuntimeError(f"runtime audit failed: {k}={d[k]}")
        # untagged QoS-data MPDUs are non-application frames (ARP); app data always carries a tag
        if d["audit_untagged_tx"] > 20:
            raise RuntimeError(f"runtime audit failed: audit_untagged_tx={d['audit_untagged_tx']}")
    return d
