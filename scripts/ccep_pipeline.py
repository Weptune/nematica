"""Human test, the whole workflow in one command: stream and reduce every recording, then
score them. Safe to start while ccep_stream.py is already running in another window: it
waits until that run has gone quiet for 30 minutes before doing anything, so the two never
download at the same time. Then it finishes whatever is missing (including recordings that
failed earlier), and runs the pre-registered analysis.

Usage (from the project folder):
  python scripts/ccep_pipeline.py
Results: docs/figures/ccep_summary.txt, ccep_patients.csv, ccep_recordings.csv
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "derived" / "ccep"
WORK = ROOT / "data" / "raw" / "ds004080_work"
QUIET_S = 30 * 60


def last_activity() -> float:
    times = [0.0]
    for base in (OUT, WORK):
        if base.exists():
            times += [p.stat().st_mtime for p in base.rglob("*") if p.is_file()]
    return max(times)


def main() -> int:
    while True:
        idle = time.time() - last_activity()
        if idle >= QUIET_S:
            break
        print(f"Another run is still working (last activity {idle / 60:.0f} min ago); checking again in 10 min.", flush=True)
        time.sleep(600)
    py = sys.executable
    print("Streaming any recordings still missing ...", flush=True)
    r = subprocess.run([py, str(ROOT / "scripts" / "ccep_stream.py")], cwd=ROOT)
    if r.returncode != 0:
        print("Streaming stopped with an error; fix it and run this again.")
        return r.returncode
    print("Scoring ...", flush=True)
    r = subprocess.run([py, str(ROOT / "scripts" / "run_ccep_test.py")], cwd=ROOT)
    if r.returncode == 0:
        (OUT / "PIPELINE_DONE.txt").write_text(time.strftime("%Y-%m-%d %H:%M:%S") + "\n", encoding="utf-8")
        print("All done. Results in docs/figures/ccep_summary.txt")
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
