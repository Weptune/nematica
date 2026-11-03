"""Mouse hippocampus (Bocchio, Vorobyev et al., Zenodo 11500028, CC BY 4.0): one pass over
the 18.5 GB archive, keeping only what the watching-versus-poking test needs.

The archive's files are shuffled (session folders are interleaved), so it cannot be handled
session by session. Instead this streams it once, never storing the archive, and keeps:

  F.npy + Fneu.npy  ->  one neuropil-corrected trace per ROI, Fc = F - 0.7 * Fneu (float16)
  iscell.npy, old_cell_idx.npy and other small plain arrays (as they are)
  stat.npy          ->  ROI centre positions only (read with a restricted unpickler that can
                        only rebuild plain numpy arrays and dicts; nothing else is executed)
  small text/csv    ->  stimulation frames, stimulated ROI, interneuron ROIs, speed, frame times

Skipped: imaging movies (.tif), ops.npy, spks*.npy, pickles other than stat.

Output: data/derived/hippo/<session>/...  (gitignored, local only)
Usage:  python scripts/hippo_stream.py            (about 18.5 GB of download, ~5 GB kept)
If the connection drops it starts the pass again and skips what it already has.
"""
from __future__ import annotations

import argparse
import io
import os
import pickle
import re
import shutil
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "derived" / "hippo"
URL = "https://zenodo.org/records/11500028/files/all-optical.tar.gz?download=1"
UA = {"User-Agent": "nematica-hippo/1.0"}
TEXT_EXT = (".txt", ".csv")
SMALL_NPY = ("iscell.npy", "old_cell_idx.npy")
NEUROPIL = 0.7

SESSION_RE = re.compile(r"all-optical/(?:s2p_processed/)?(\d+)/(.*)$")


class SafeUnpickler(pickle.Unpickler):
    """Only lets numpy arrays, dtypes, scalars and plain containers through."""
    ALLOWED = {
        ("numpy.core.multiarray", "_reconstruct"), ("numpy._core.multiarray", "_reconstruct"),
        ("numpy.core.multiarray", "scalar"), ("numpy._core.multiarray", "scalar"),
        ("numpy.core.numeric", "_frombuffer"), ("numpy._core.numeric", "_frombuffer"),
        ("numpy", "ndarray"), ("numpy", "dtype"),
        ("builtins", "dict"), ("builtins", "list"), ("builtins", "tuple"),
        ("builtins", "bool"), ("builtins", "int"), ("builtins", "float"),
        ("collections", "OrderedDict"),
    }

    def find_class(self, module, name):
        if (module, name) in self.ALLOWED:
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"refused to load {module}.{name}")


def stat_positions(raw: bytes) -> np.ndarray:
    """ROI centres (y, x) in pixels from a Suite2p stat.npy, without running arbitrary code."""
    f = io.BytesIO(raw)
    version = np.lib.format.read_magic(f)
    if version == (1, 0):
        np.lib.format.read_array_header_1_0(f)
    else:
        np.lib.format.read_array_header_2_0(f)
    obj = SafeUnpickler(f).load()
    items = list(obj.ravel()) if isinstance(obj, np.ndarray) else list(obj)
    pos = np.full((len(items), 2), np.nan, dtype=np.float32)
    for i, d in enumerate(items):
        if isinstance(d, dict):
            if "med" in d:
                pos[i] = np.asarray(d["med"], dtype=np.float32)[:2]
            elif "ypix" in d and "xpix" in d:
                pos[i] = [np.median(d["ypix"]), np.median(d["xpix"])]
    return pos


def plain_npy(raw: bytes) -> np.ndarray:
    return np.load(io.BytesIO(raw), allow_pickle=False)


def combine_if_ready(sdir: Path) -> None:
    """When both raw halves are present, write Fc.npy and remove the two temporary halves."""
    a, b = sdir / "_F.npy", sdir / "_Fneu.npy"
    if (sdir / "Fc.npy").exists() or not (a.exists() and b.exists()):
        return
    F = np.load(a).astype(np.float32)
    N = np.load(b).astype(np.float32)
    if F.shape == N.shape:
        np.save(sdir / "Fc.npy", (F - NEUROPIL * N).astype(np.float16))
    else:
        (sdir / "SHAPE_MISMATCH.txt").write_text(f"{F.shape} vs {N.shape}\n")
    a.unlink()
    b.unlink()


def handle(member: tarfile.TarInfo, tar, stats: dict) -> None:
    m = SESSION_RE.search(member.name)
    if not m or not member.isfile():
        return
    sess, rest = m.group(1), m.group(2)
    base = os.path.basename(rest)
    if base.startswith("._") or base == ".DS_Store":
        return
    sdir = OUT / sess
    in_s2p = "/s2p_processed/" in member.name
    target = None
    if in_s2p and base in ("F.npy", "Fneu.npy"):
        if (sdir / "Fc.npy").exists():
            return
        target = sdir / ("_" + base)
    elif in_s2p and base == "stat.npy":
        target = sdir / "pos.npy"
    elif in_s2p and base in SMALL_NPY:
        target = sdir / base
    elif not in_s2p and base.lower().endswith(TEXT_EXT) and member.size < 5e6:
        target = sdir / base
    if target is None or target.exists():
        return
    fh = tar.extractfile(member)
    if fh is None:
        return
    raw = fh.read()
    sdir.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    try:
        if target.name in ("_F.npy", "_Fneu.npy"):
            arr = plain_npy(raw).astype(np.float16)
        elif target.name == "pos.npy":
            arr = stat_positions(raw)
        elif target.suffix == ".npy":
            arr = plain_npy(raw)
        else:
            arr = None
        if arr is None:
            tmp.write_bytes(raw)
        else:
            with open(tmp, "wb") as out:
                np.save(out, arr)
        os.replace(tmp, target)
        stats["kept"] += 1
    except Exception as e:
        stats["errors"] += 1
        with open(OUT / "errors.txt", "a", encoding="utf-8") as log:
            log.write(f"{member.name}: {type(e).__name__}: {e}\n")
        if tmp.exists():
            tmp.unlink()
        return
    combine_if_ready(sdir)


def one_pass(min_free_gb: float) -> None:
    req = urllib.request.Request(URL, headers=UA)
    r = urllib.request.urlopen(req, timeout=300)
    total = int(r.headers.get("Content-Length") or 0)

    class Counting(io.RawIOBase):
        n = 0

        def readable(self):
            return True

        def readinto(self, b):
            data = r.read(len(b))
            Counting.n += len(data)
            b[: len(data)] = data
            return len(data)

    stats = {"kept": 0, "errors": 0}
    t0 = last = time.time()
    with tarfile.open(fileobj=io.BufferedReader(Counting(), 1 << 20), mode="r|gz") as tar:
        for member in tar:
            handle(member, tar, stats)
            if time.time() - last > 60:
                last = time.time()
                free = shutil.disk_usage(ROOT).free / 1e9
                rate = Counting.n / max(1.0, last - t0) / 1e6
                print(f"  {Counting.n / 1e9:.2f} of {total / 1e9:.2f} GB read ({rate:.1f} MB/s), "
                      f"{stats['kept']} files kept, {free:.1f} GB free", flush=True)
                if free < min_free_gb:
                    raise RuntimeError(f"free disk below {min_free_gb} GB; stopping")
    print(f"pass complete: {Counting.n / 1e9:.2f} GB read, {stats['kept']} files kept, "
          f"{stats['errors']} errors", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-free-gb", type=float, default=5.0)
    ap.add_argument("--tries", type=int, default=3)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "STREAM_DONE.txt").exists():
        print("already done (delete data/derived/hippo/STREAM_DONE.txt to run again)")
        return 0
    for attempt in range(1, args.tries + 1):
        try:
            one_pass(args.min_free_gb)
            for sdir in OUT.iterdir():
                if sdir.is_dir():
                    combine_if_ready(sdir)
            (OUT / "STREAM_DONE.txt").write_text(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
            n = sum(1 for s in OUT.iterdir() if (s / "Fc.npy").exists())
            print(f"done: {n} sessions with traces in {OUT}")
            return 0
        except Exception as e:
            print(f"pass {attempt} stopped: {type(e).__name__}: {e}", flush=True)
            if "free disk" in str(e):
                return 1
            time.sleep(60 * attempt)
    return 1


if __name__ == "__main__":
    sys.exit(main())
