"""The ruler's resolution: how large an error must a copy make before the ruler sees it?
Known errors of graded size are put into real held-out worms' own responses, and each damaged
set is scored against the other real worms of its pool, as a copy would be:

  pattern    the poked neuron's identity shuffled for a fraction f of a worm's pulses
  magnitude  every response scaled by k

Reported: in how many of the six pools the ruler calls the damaged worms outside, and in how
many the equivalence check still says they agree.

Usage:  python scripts/run_resolution.py
"""

from __future__ import annotations

import csv
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.causal import CAUSAL_LEVELS, response_set, scaled, score_sets  # noqa: E402
from nematica.bench.scorecard import (SPLITS, SPLITS_DIR, TOL_CONTROL_V2, equivalence, fold_parts,  # noqa: E402
                                      poke_tolerances, set_norm)
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402


def shuffled_fraction(rec, f: float, rng):
    stims = list(rec.stims)
    k = int(round(f * len(stims)))
    idx = rng.choice(len(stims), k, replace=False) if k else []
    targets = [stims[i][0] for i in idx]
    perm = rng.permutation(len(targets)) if k else []
    for i, p in zip(idx, perm):
        stims[i] = (targets[p], stims[i][1])
    return response_set(rec, f"shuffle{f}:{rec.uid}", stims=stims)


def main() -> int:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
    out_rows = []
    for split in SPLITS:
        folds = load_folds(SPLITS_DIR / SPLITS[split])["folds"]
        for fi in range(len(folds)):
            _, _, pool = fold_parts(recs, folds, fi)
            real = [response_set(r) for r in pool]
            tol = poke_tolerances(pool, real)
            tol2 = poke_tolerances(pool, real, controls=TOL_CONTROL_V2)["C2.magnitude"]["tolerance"]
            rng = np.random.default_rng(fi)
            trials = [("pattern", f, "C1.pattern", lambda r, f=f: shuffled_fraction(r, f, rng)) for f in (0.0, 0.25, 0.5, 0.75, 1.0)]
            trials += [("magnitude", k, "C2.magnitude", lambda r, k=k: scaled(r, k)) for k in (1.0, 1.1, 1.25, 1.5, 2.0)]
            for kind, size, level, make in trials:
                sets = []
                for r in pool:
                    s = make(r)
                    s.group = r.uid
                    sets.append(s)
                row = score_sets(f"{kind}{size}", sets, real, levels={level: CAUSAL_LEVELS[level]})[0]
                t = tol[level]["tolerance"]
                out_rows.append({"split": split, "fold": fi, "error": kind, "size": size, "verdict": row["verdict"],
                                 "agrees": equivalence(row, t), "agrees_x1.5": equivalence(row, tol2) if level == "C2.magnitude" else ""})
                print(split, fi, kind, size, row["verdict"], out_rows[-1]["agrees"], out_rows[-1]["agrees_x1.5"], flush=True)
    with Path("docs/figures/resolution.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
