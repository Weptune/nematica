"""Mouse touch (barrel) cortex, Dalgleish et al. 2020 (figshare 13128950, MIT): download each
of the 11 session zips in turn, keep only what the watching-versus-poking test needs, delete
the zip.

Kept per session, in data/derived/touch/<session>/ (gitignored, local only):
  Fc.npy          F - 0.7 * Fneu for every ROI (float16; ROIs x frames, all planes)
  iscell.npy      Suite2p curation (column 0 = is a cell)
  rois.npz        per ROI: med (y, x pixels), iplane; frames_per_file and nplanes from ops
  *_paqanalysis.mat, targets/*.mat, cellPose/*cellPoseCentroids.mat   copied as they are
                  (timing of every stimulation, which neurons each trial type targeted)
The 665 MB Fall.mat is read once and dropped (spks and the movie-derived fields are not kept).

Usage:  python scripts/touch_stream.py     (about 12 GB downloaded, about 1 GB kept)
Resumable: finished sessions are skipped. Stops if free disk falls below --min-free-gb.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "derived" / "touch"
API = "https://api.figshare.com/v2/articles/13128950"
UA = {"User-Agent": "nematica-touch/1.0"}
NEUROPIL = 0.7


def download(url: str, dest: Path, tries: int = 5) -> None:
    for k in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as fh:
                total = int(r.headers.get("Content-Length") or 0)
                got, last = 0, time.time()
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    fh.write(b)
                    got += len(b)
                    if time.time() - last > 30:
                        last = time.time()
                        print(f"    {got / 1e9:.2f} of {total / 1e9:.2f} GB", flush=True)
            return
        except Exception as e:
            print(f"    download attempt {k} failed: {e}", flush=True)
            time.sleep(15 * k)
    raise RuntimeError(f"could not download {url}")


def reduce_fall(path: Path, out: Path) -> str:
    from scipy.io import loadmat
    m = loadmat(path, squeeze_me=True, struct_as_record=False,
                variable_names=["F", "Fneu", "iscell", "stat", "ops"])
    F = np.asarray(m["F"], np.float32)
    N = np.asarray(m["Fneu"], np.float32)
    np.save(out / "Fc.npy", (F - NEUROPIL * N).astype(np.float16))
    np.save(out / "iscell.npy", np.asarray(m["iscell"], np.float32))
    stat = np.atleast_1d(m["stat"])
    med = np.array([np.asarray(s.med, float)[:2] for s in stat])
    iplane = np.array([int(getattr(s, "iplane", 0)) for s in stat])
    ops = m["ops"]
    fpf = np.atleast_1d(getattr(ops, "frames_per_file", np.array([]))).astype(int)
    nplanes = int(getattr(ops, "nplanes", len(np.unique(iplane))))
    np.savez(out / "rois.npz", med=med, iplane=iplane, frames_per_file=fpf, nplanes=nplanes)
    return f"{F.shape[0]} ROIs x {F.shape[1]} frames, {nplanes} planes"


def handle(zpath: Path, out: Path) -> str:
    tmp = out.with_name(out.name + ".part")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    with zipfile.ZipFile(zpath) as z, tempfile.TemporaryDirectory() as td:
        msg = ""
        for info in z.infolist():
            name = info.filename
            base = name.rsplit("/", 1)[-1]
            if name.startswith("__MACOSX") or base.startswith(".") or info.is_dir():
                continue
            if base == "Fall.mat":
                p = Path(z.extract(info, td))
                msg = reduce_fall(p, tmp)
                p.unlink()
            elif base.endswith("_paqanalysis.mat"):
                (tmp / base).write_bytes(z.read(info))
            elif "/targets/" in name and base.endswith(".mat"):
                (tmp / "targets").mkdir(exist_ok=True)
                (tmp / "targets" / base).write_bytes(z.read(info))
            elif "/cellPose/" in name and base.endswith("cellPoseCentroids.mat"):
                (tmp / "cellPose").mkdir(exist_ok=True)
                (tmp / "cellPose" / base).write_bytes(z.read(info))
    if not (tmp / "Fc.npy").exists():
        raise RuntimeError("no Fall.mat in zip")
    tmp.rename(out)
    return msg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-free-gb", type=float, default=5.0)
    ap.add_argument("--only", default=None, help="comma-separated session names")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(API, headers=UA), timeout=60) as r:
        files = [f for f in json.load(r)["files"] if f["name"].endswith(".zip")]
    files.sort(key=lambda f: f["size"])
    if args.only:
        keep = set(args.only.split(","))
        files = [f for f in files if f["name"][:-4] in keep]
    fails = 0
    for i, f in enumerate(files, 1):
        sess = f["name"][:-4]
        out = OUT / sess
        if out.exists():
            print(f"{i}/{len(files)} {sess}: already done", flush=True)
            continue
        free = shutil.disk_usage(ROOT).free / 1e9
        if free - 2.5 * f["size"] / 1e9 < args.min_free_gb:
            print(f"stopping: {free:.1f} GB free", flush=True)
            return 1
        print(f"{i}/{len(files)} {sess} ({f['size'] / 1e9:.2f} GB)", flush=True)
        with tempfile.TemporaryDirectory(dir=OUT) as td:
            zp = Path(td) / "s.zip"
            try:
                download(f["download_url"], zp)
                print(f"    {handle(zp, out)}", flush=True)
                fails = 0
            except Exception as e:
                fails += 1
                print(f"    FAILED: {type(e).__name__}: {e}", flush=True)
                with open(OUT / "errors.txt", "a", encoding="utf-8") as fh:
                    fh.write(f"{sess}: {type(e).__name__}: {e}\n")
                if fails >= 3:
                    return 1
    n = sum(1 for p in OUT.iterdir() if p.is_dir() and not p.name.endswith(".part"))
    (OUT / "STREAM_DONE.txt").write_text(time.strftime("%Y-%m-%d %H:%M:%S") + f" {n} sessions\n")
    print(f"done: {n} sessions in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
