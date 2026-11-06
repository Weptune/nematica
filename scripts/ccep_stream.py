"""Human test, on your own computer: stream the whole CCEP dataset (OpenNeuro ds004080) one
recording at a time, reduce each with ccep_extract.py, delete the raw file, move on.

Peak disk use is one recording (at most about 3 GB) plus the summaries (a few hundred MB),
so it fits on a nearly full drive. It can be stopped (Ctrl+C) and restarted at any time:
recordings already reduced are skipped. Needs Python with numpy and scipy, and git.

Usage (from the project folder):
  python scripts/ccep_stream.py                  # everything, into data/derived/ccep
  python scripts/ccep_stream.py --only sub-ccepAgeUMCU68 --only sub-ccepAgeUMCU45
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MIRROR = "https://github.com/OpenNeuroDatasets/ds004080.git"
BASE = "https://s3.amazonaws.com/openneuro.org/ds004080/"
ANNEXED = ("_ieeg.vhdr", "_ieeg.vmrk", "_ieeg.eeg")


def is_placeholder(p: Path) -> bool:
    """git-annex leaves a symlink (or, on Windows, a tiny text file) where a large file goes."""
    if p.is_symlink():
        return True
    if not p.exists():
        return True
    if p.stat().st_size < 600:
        head = p.read_bytes()[:80]
        return head.startswith(b"../") or b".git/annex" in head
    return False


def download(url: str, dst: Path, base_wait: float = 10.0):
    tmp = dst.with_name(dst.name + ".part")
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, length=1 << 24)
            os.replace(tmp, dst)
            return
        except Exception as e:                     # network hiccups: wait and retry
            print(f"    retry {attempt + 1}: {e}", flush=True)
            time.sleep(base_wait * (attempt + 1))
    raise RuntimeError(f"could not download {url}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/derived/ccep")
    ap.add_argument("--meta", default="data/raw/ds004080_meta")
    ap.add_argument("--work", default="data/raw/ds004080_work")
    ap.add_argument("--only", action="append", default=[], help="patient folder(s) to do, e.g. sub-ccepAgeUMCU68")
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--min-free-gb", type=float, default=5.0)
    ap.add_argument("--extractor", default="ccep_extract", help="ccep_extract or ccep_extract_v2")
    args = ap.parse_args()
    try:
        import scipy  # noqa: F401
        import numpy as np
    except ImportError:
        print("Needs numpy and scipy: python -m pip install numpy scipy")
        return 1
    import importlib
    E = importlib.import_module(args.extractor)

    meta, out, work = Path(args.meta), Path(args.out), Path(args.work)
    out.mkdir(parents=True, exist_ok=True)
    if not (meta / "participants.tsv").exists():
        print("Fetching the dataset's file list (small) ...", flush=True)
        meta.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-c", "core.symlinks=false", "clone", "-q", "--depth", "1", MIRROR, str(meta)], check=True)
    shutil.copy(meta / "participants.tsv", out / "participants.tsv")
    runs = sorted(Path(p) for p in glob.glob(str(meta / "sub-*" / "ses-*" / "ieeg" / "*_ieeg.vhdr")))
    if args.only:
        runs = [r for r in runs if r.parts[-4] in args.only]
    print(f"{len(runs)} recordings to consider; summaries go to {out}", flush=True)
    log = open(out / "log.txt", "a", encoding="utf-8")
    fails = 0
    for i, v in enumerate(runs):
        stem = v.name.replace("_ieeg.vhdr", "")
        dst = out / f"{stem}.npz"
        if dst.exists():
            continue
        free = shutil.disk_usage(out.resolve()).free / 1e9
        if free < args.min_free_gb:
            print(f"Stopping: only {free:.1f} GB free (need {args.min_free_gb}). Free some space and run again.")
            break
        rel = v.relative_to(meta)
        wdir = work / rel.parent
        if work.exists():
            shutil.rmtree(work)
        wdir.mkdir(parents=True)
        t0 = time.time()
        try:
            for f in v.parent.iterdir():                 # small metadata files travel with the clone
                if f.is_file() and not f.is_symlink() and not is_placeholder(f) and not f.name.endswith(ANNEXED):
                    shutil.copy(f, wdir / f.name)
            for ext in ANNEXED:
                name = v.name.replace("_ieeg.vhdr", ext)
                download(args.base + rel.parent.as_posix() + "/" + name, wdir / name)
            res = E.process(wdir / v.name)
            np.savez_compressed(str(dst) + ".part.npz", **res)
            os.replace(str(dst) + ".part.npz", dst)
            msg = (f"{i + 1}/{len(runs)} {stem}: {len(res['names'])} channels, {len(res['sites'])} sites, "
                   f"{int(res['n_odd'].sum() + res['n_even'].sum())} pulses, {res['seg_seconds']:.0f} s between pulses, "
                   f"{time.time() - t0:.0f} s")
            del res
        except KeyboardInterrupt:
            shutil.rmtree(work, ignore_errors=True)
            print("Stopped. Run the same command again to continue.")
            return 0
        except Exception:
            msg = f"{i + 1}/{len(runs)} {stem}: FAILED\n" + traceback.format_exc()
        finally:
            shutil.rmtree(work, ignore_errors=True)
        print(msg, flush=True)
        log.write(msg + "\n")
        log.flush()
        fails = fails + 1 if "FAILED" in msg else 0
        if fails >= 3:
            print("Stopping: three recordings in a row failed. Send the message above to fix it.")
            break
    else:
        print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
