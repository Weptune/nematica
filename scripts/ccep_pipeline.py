"""The whole workflow in one command. Human test: stream and reduce every recording, then
score them. Then the mouse hippocampus test: finish its one-pass download if needed, then
score it. Then download the mouse touch-cortex sessions (about 12 GB, about 1 GB kept). Then, if
the hippocampus download was cut short, read its archive once more and rescore (with the
exploratory controls). Last, run the queued artificial-lab checks (scripts/lab_queue.py). After
each stage, docs/figures/AUTO_REPORT.txt gathers every result. Safe to start while ccep_stream.py is already running in another window: it
waits until that run has gone quiet for 30 minutes before doing anything, so the two never
download at the same time. Then it finishes whatever is missing (including recordings that
failed earlier), and runs the pre-registered analysis.

Usage (from the project folder):
  python scripts/ccep_pipeline.py
Results: docs/figures/ccep_summary.txt, ccep_patients.csv, ccep_recordings.csv,
         docs/figures/hippo_summary.txt, hippo_sessions.csv
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "derived" / "ccep"
WORK = ROOT / "data" / "raw" / "ds004080_work"
HIPPO = ROOT / "data" / "derived" / "hippo"
QUIET_S = 30 * 60


def last_activity(bases=(OUT, WORK)) -> float:
    times = [0.0]
    for base in bases:
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
        print("Human streaming stopped with an error; scoring what there is, then the hippocampus.")
    print("Scoring ...", flush=True)
    r = subprocess.run([py, str(ROOT / "scripts" / "run_ccep_test.py")], cwd=ROOT)
    if r.returncode == 0:
        (OUT / "PIPELINE_DONE.txt").write_text(time.strftime("%Y-%m-%d %H:%M:%S") + "\n", encoding="utf-8")
        print("Human test done. Results in docs/figures/ccep_summary.txt", flush=True)
    human_rc = r.returncode
    report(py)
    hippo_rc = hippo(py)
    report(py)
    print("Touch cortex: downloading (scoring is added once its prediction is written) ...", flush=True)
    touch_rc = subprocess.run([py, str(ROOT / "scripts" / "touch_stream.py")], cwd=ROOT).returncode
    refetch_rc = 0
    done = HIPPO / "STREAM_DONE.txt"
    if not done.exists() or "complete pass" not in done.read_text(encoding="utf-8", errors="replace"):
        print("Hippocampus: reading the archive once more to replace crash-damaged files and add the "
              "sessions the interrupted download never reached (about 2.5 hours) ...", flush=True)
        refetch_rc = subprocess.run([py, str(ROOT / "scripts" / "hippo_stream.py"), "--refetch"], cwd=ROOT).returncode
        if refetch_rc == 0:
            # the pre-registered analysis, the follow-up, and the exploratory controls of 3 Nov
            for extra in ([], ["--multi"], ["--reading", "all"], ["--sham", "130"], ["--sham", "130", "--reading", "all"]):
                subprocess.run([py, str(ROOT / "scripts" / "run_hippo_test.py"), *extra], cwd=ROOT)
            print("Hippocampus rescored on every recovered session.", flush=True)
    report(py)
    print("Artificial lab: running the queued checks (several hours, no downloads) ...", flush=True)
    lab_rc = subprocess.run([py, str(ROOT / "scripts" / "lab_queue.py")], cwd=ROOT).returncode
    report(py)
    print("Everything finished. Summary: docs/figures/AUTO_REPORT.txt", flush=True)
    return max(human_rc, hippo_rc, touch_rc, refetch_rc, lab_rc)


def report(py: str) -> None:
    subprocess.run([py, str(ROOT / "scripts" / "collect_report.py")], cwd=ROOT,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def hippo(py: str) -> int:
    """Mouse hippocampus. If a separate hippo_stream.py run is still going, wait for it."""
    while not (HIPPO / "STREAM_DONE.txt").exists():
        idle = time.time() - last_activity((HIPPO,))
        if idle >= QUIET_S:
            break
        print(f"Hippocampus download still working (last activity {idle / 60:.0f} min ago); "
              "checking again in 10 min.", flush=True)
        time.sleep(600)
    print("Hippocampus: finishing the download if needed ...", flush=True)
    r = subprocess.run([py, str(ROOT / "scripts" / "hippo_stream.py")], cwd=ROOT)
    if r.returncode != 0:
        print("Hippocampus download stopped with an error; run this again later.")
        return r.returncode
    print("Hippocampus: scoring ...", flush=True)
    r = subprocess.run([py, str(ROOT / "scripts" / "run_hippo_test.py")], cwd=ROOT)
    if r.returncode == 0:
        (HIPPO / "PIPELINE_DONE.txt").write_text(time.strftime("%Y-%m-%d %H:%M:%S") + "\n", encoding="utf-8")
        print("Hippocampus done. Results in docs/figures/hippo_summary.txt")
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
