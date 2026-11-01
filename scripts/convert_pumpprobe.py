"""Convert the Randi et al. (2023) signal-propagation atlas from its original archive to the
one-.npz-per-worm format NEMATICA reads (nematica/data/pumpprobe.py).

Source: OSF project e2syt (https://osf.io/e2syt/), folder raw_extracted_data, which holds six
text files per recording, numbered 0..112 for the wild-type worms:

    <i>_ds_name.txt        path of the original recording; its last part is the worm's uid
    <i>_gcamp.txt          (T, N) fluorescence, nan where a neuron was not tracked
    <i>_labels.txt         N neuron names, one per line; blank where unidentified
    <i>_stim_neurons.txt   index of the stimulated neuron per stimulation; negative = not tracked
    <i>_stim_volume_i.txt  frame of each stimulation
    <i>_t.txt              (T,) frame times in seconds

The data are not redistributed with NEMATICA: download the archive from OSF yourself (the
whole project is about 4.7 GB; only raw_extracted_data, about 1.2 GB, is needed) and run

    python scripts/convert_pumpprobe.py --src path/to/raw_extracted_data --out data/raw/randi2023_wt_npz

Labels are kept as written, including the few that are not neuron names (such as
"smthng else" or a bare number); nematica.data.pumpprobe maps those to no class.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

def read_lines(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def convert_one(src: Path, i: int, out: Path) -> str:
    uid = Path(read_lines(src / f"{i}_ds_name.txt")[0].strip().rstrip("/")).name
    try:
        x = np.loadtxt(src / f"{i}_gcamp.txt", ndmin=2).astype(np.float32)
    except ValueError as e:              # a few files have rows of different lengths
        print(f"skipped recording {i} ({uid}): {e}", file=sys.stderr)
        return ""
    t = np.loadtxt(src / f"{i}_t.txt", ndmin=1).astype(float)
    labels = read_lines(src / f"{i}_labels.txt")
    while labels and labels[-1] == "" and len(labels) > x.shape[1]:
        labels.pop()                                       # trailing newline only
    ids = np.array([s.strip() for s in labels])
    if len(t) > 1 and not np.allclose(np.diff(t), 0.5):
        raise ValueError(f"recording {i} ({uid}): frames are not 0.5 s apart")
    sc = np.loadtxt(src / f"{i}_stim_neurons.txt", ndmin=1).astype(np.int64)
    sf = np.loadtxt(src / f"{i}_stim_volume_i.txt", ndmin=1).astype(np.int64)
    if len(ids) != x.shape[1] or len(t) != x.shape[0] or len(sc) != len(sf):
        raise ValueError(f"recording {i} ({uid}): inconsistent sizes")
    name = uid if uid.startswith("pumpprobe_") else f"pumpprobe_{uid}"
    np.savez(out / f"{name}.npz", x=x, ids=ids, stim_cell=sc, stim_frame=sf, t=t)
    return name


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="the archive's raw_extracted_data folder")
    ap.add_argument("--out", default="data/raw/randi2023_wt_npz")
    args = ap.parse_args()
    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    idx = sorted(int(p.name.split("_")[0]) for p in src.glob("*_ds_name.txt"))
    if not idx:
        print(f"no recordings found in {src}", file=sys.stderr)
        return 1
    done = [n for n in (convert_one(src, i, out) for i in idx) if n]
    print(f"{len(done)} of {len(idx)} recordings written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
