"""Signatures of a mind at rest (README): calibrations with designed outcomes, then models,
on the behaving-worm datasets (copper, Atanas), with the frozen rotating pools.

Usage:
  python scripts/run_mind.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --folds configs/splits/copper2026_cv3.yaml --models hyst10,hyst
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nematica.bench import build_reference, from_recording, score_system  # noqa: E402
from nematica.bench.calib import frame_shuffle, gaussian_noise, independent_shift, phase_randomised  # noqa: E402
from nematica.bench.mind import MIND_LEVELS, summary  # noqa: E402
from nematica.data import load_any_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from run_l8_fair import build  # noqa: E402

EXPECTED = {
    "real": {"M1.complexity": "inside", "M2.integration": "inside", "M3.repertoire": "inside"},
    "independent_shift": {"M1.complexity": "either", "M2.integration": "outside", "M3.repertoire": "either"},
    "frame_shuffle": {"M1.complexity": "outside", "M2.integration": "inside", "M3.repertoire": "either"},
    "phase_randomised": {"M1.complexity": "either", "M2.integration": "inside", "M3.repertoire": "either"},
    "gaussian_noise": {"M1.complexity": "outside", "M2.integration": "outside", "M3.repertoire": "either"},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--models", default="hyst10,hyst")
    ap.add_argument("--out", default="docs/figures")
    ap.add_argument("--tag", default="copper")
    args = ap.parse_args()
    recs = load_any_dir(Path(args.data))
    by = {r.uid: r for r in recs}
    classes = tuple(canonical_classes(recs, 0.25))
    folds = load_folds(args.folds)["folds"]
    rows, hits, total = [], 0, 0
    for fi, pool_uids in enumerate(folds):
        t0 = time.time()
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        val_uids = [rest[len(rest) // 3], rest[2 * len(rest) // 3]]
        train_uids = [u for u in rest if u not in val_uids]
        S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
        pool, train, val = S(pool_uids), S(train_uids), S(val_uids)
        ref = build_reference(pool, metrics=tuple(MIND_LEVELS), levels=MIND_LEVELS)
        rng = np.random.default_rng(10 + fi)
        systems = {
            "real": pool,
            "independent_shift": [independent_shift(s, rng) for s in pool],
            "frame_shuffle": [frame_shuffle(s, rng) for s in pool],
            "phase_randomised": [phase_randomised(s, rng) for s in pool],
            "gaussian_noise": [gaussian_noise(s, rng) for s in pool],
        }
        for name in args.models.split(","):
            m = build(name, train).fit(train, val)
            systems[name] = [m.generate(s, np.random.default_rng(100 * fi + i), which=i) for i, s in enumerate(pool)]
        for kind, samples in systems.items():
            summ = [summary(s) for s in samples]
            raw = {k: round(float(np.nanmedian([x[k] for x in summ])), 4) for k in summ[0]}
            for row in score_system(kind, samples, pool, ref, levels=MIND_LEVELS):
                exp = EXPECTED.get(kind, {}).get(row["metric"], "model")
                ok = exp in ("either", "model") or exp == row["verdict"]
                if exp not in ("either", "model"):
                    total += 1
                    hits += ok
                rows.append({"dataset": args.tag, "fold": fi, **row, "expected": exp, **{f"raw_{k}": v for k, v in raw.items()}})
                print(f"fold {fi} {kind:18s} {row['metric']:15s} {row['verdict']:11s} (expected {exp:7s}) "
                      f"KS {row.get('system_median')} vs real {row.get('bio_median')}  raw {raw}", flush=True)
        print(f"fold {fi} done ({time.time() - t0:.0f} s)", flush=True)
    print(f"\ndesigned calibration outcomes hit: {hits} / {total}")
    with (Path(args.out) / f"mind_{args.tag}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
