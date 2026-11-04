"""Queue of artificial-lab checks requested by the 3 Nov review, run one at a time (each needs
1 to 2 GB of memory). Every job writes its own CSV; jobs whose CSV already exists are skipped,
so the queue can be stopped and restarted. All settings of each job are listed below and in
docs/figures/ann_queue_settings.md (written by this script).

Usage:  python scripts/lab_queue.py            (several hours of computing; no downloads)
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
LOG = ROOT / "data" / "derived" / "lab_queue_log.txt"
COPIES = "another_individual,var3_spontaneous,stitch3_hp,hybrid_kernels"
BASE = {"NEMATICA_LEAD": "230", "NEMATICA_SUBSTEPS": "1", "NEMATICA_CALCIUM": "0", "OMP_NUM_THREADS": "2",
        "OPENBLAS_NUM_THREADS": "2"}

# (output name, environment, extra arguments). Silent links on independently drawn species
# brains, each with the same brain without silent links for comparison; then the calcium test
# with a slower indicator and on the remaining pools.
JOBS = [
    ("ann_queue_silent_seed1_fold0.csv", {"NEMATICA_BRAIN_SEED": "1", "NEMATICA_GATED": "1.5", "NEMATICA_KICK_FRAMES": "4"},
     ["--share", "0.05", "--folds", "0"]),
    ("ann_queue_baseline_seed1_fold0.csv", {"NEMATICA_BRAIN_SEED": "1", "NEMATICA_KICK_FRAMES": "4"},
     ["--share", "0.05", "--folds", "0"]),
    ("ann_queue_silent_seed2_fold0.csv", {"NEMATICA_BRAIN_SEED": "2", "NEMATICA_GATED": "1.5", "NEMATICA_KICK_FRAMES": "4"},
     ["--share", "0.05", "--folds", "0"]),
    ("ann_queue_baseline_seed2_fold0.csv", {"NEMATICA_BRAIN_SEED": "2", "NEMATICA_KICK_FRAMES": "4"},
     ["--share", "0.05", "--folds", "0"]),
    ("ann_queue_calcium3.0_fold0.csv", {"NEMATICA_SUBSTEPS": "5", "NEMATICA_CALCIUM": "3.0"},
     ["--share", "0.05", "--folds", "0"]),
    ("ann_queue_calcium1.5_fold1.csv", {"NEMATICA_SUBSTEPS": "5", "NEMATICA_CALCIUM": "1.5"},
     ["--share", "0.05", "--folds", "1"]),
    ("ann_queue_calcium1.5_fold2.csv", {"NEMATICA_SUBSTEPS": "5", "NEMATICA_CALCIUM": "1.5"},
     ["--share", "0.05", "--folds", "2"]),
]


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    with (FIG / "ann_queue_settings.md").open("w", encoding="utf-8") as fh:
        fh.write("# Settings of the queued lab checks (scripts/lab_queue.py)\n\n"
                 "All: `scripts/run_ann_calcium.py --n 113`, kick 6, first poke at frame 230, copies "
                 f"{COPIES}. Unlisted variables at defaults (BRAIN_SEED 0, GATED 0, KICK_FRAMES 8, "
                 "SUBSTEPS 1, CALCIUM 0).\n\n| File | Environment | Arguments |\n|---|---|---|\n")
        for out, env, args in JOBS:
            fh.write(f"| {out} | {' '.join(f'{k[9:]}={v}' for k, v in env.items())} | {' '.join(args)} |\n")
    py = sys.executable
    for out, env, args in JOBS:
        path = FIG / out
        if path.exists():
            log(f"skip {out} (exists)")
            continue
        tmp = FIG / (out + ".part.csv")
        log(f"start {out}")
        t0 = time.time()
        r = subprocess.run([py, str(ROOT / "scripts" / "run_ann_calcium.py"), "--n", "113", *args,
                            "--copies", COPIES, "--out", str(tmp)],
                           cwd=ROOT, env={**os.environ, **BASE, **env})
        if r.returncode == 0 and tmp.exists():
            os.replace(tmp, path)
            log(f"done {out} ({(time.time() - t0) / 60:.0f} min)")
        else:
            log(f"FAILED {out} (exit {r.returncode})")
    log("queue finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
