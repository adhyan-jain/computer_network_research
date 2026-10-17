#!/usr/bin/env python3
"""freeze.py - hash-freeze everything the preregistration governs. Run once, after writing
preregistration.md and calibrating; run_campaign.py refuses to start if any frozen file changes."""
import datetime
import hashlib
import json
import platform
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = (["preregistration.md", "configs/conditions.json", "nsrun.py", "calibrate.py", "run_campaign.py",
          "analyze_results.py", "src/sasp-policy.h", "src/sasp-mlo-experiment.cc",
          "ns-3.47/build/scratch/sasp-mlo-experiment/ns3.47-sasp-mlo-experiment-optimized",
          "ns-3.47/build/lib/libns3.47-wifi-optimized.so"]
         + [str(p.relative_to(HERE)) for p in sorted((HERE / "patches").glob("*.patch"))])


def main():
    fz = HERE / "configs" / "FREEZE.json"
    if fz.exists():
        raise SystemExit("FREEZE.json already exists; refusing to overwrite (delete it deliberately to re-freeze)")
    out = dict(created=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
               sha256={f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in FILES},
               environment=dict(platform=platform.platform(), python=platform.python_version(),
                                compiler=subprocess.run(["c++", "--version"], capture_output=True, text=True).stdout.splitlines()[0]))
    fz.write_text(json.dumps(out, indent=2))
    print(f"frozen {len(FILES)} files at {out['created']}")


if __name__ == "__main__":
    main()
