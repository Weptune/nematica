"""Arc 4: calibrations of the causal levels on the optogenetic atlas (designed outcomes in
the README). For each frozen rotation (configs/splits/pumpprobe_cv3.yaml) the pool's real
response sets are the reference; calibration sets are derived from the same pool worms and
compared with every other pool worm.

Usage:
  python scripts/run_causal_calib.py --data data/raw/2025_creamer_lds_npz --folds configs/splits/pumpprobe_cv3.yaml
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.causal import CALIBRATIONS, EXPECTED, response_set, score_sets  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="docs/figures")
    args = ap.parse_args()
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    folds = load_folds(args.folds)["folds"]
    rows = []
    hits = total = 0
    for fi, pool_uids in enumerate(folds):
        pool = [recs[u] for u in pool_uids]
        real = [response_set(r) for r in pool]
        sizes = [len(s.traces) for s in real]
        print(f"fold {fi}: {len(pool)} worms, {int(np.median(sizes))} measured pairs per worm (median)", flush=True)
        for kind, make in CALIBRATIONS.items():
            rng = np.random.default_rng(100 + fi)
            sys_sets = [make(r, rng) for r in pool]
            for row in score_sets(kind, sys_sets, real):
                exp = EXPECTED[kind][row["metric"]]
                ok = exp == "either" or exp == row["verdict"]
                if exp != "either":
                    total += 1
                    hits += ok
                rows.append({"fold": fi, **row, "expected": exp, "as_designed": ok})
                print(f"  {kind:17s} {row['metric']:13s} {row['verdict']:11s} (expected {exp:7s}) "
                      f"median {row.get('system_median')} vs real {row.get('bio_median')} "
                      f"[{row.get('bio_p05')}, {row.get('bio_p95')}]", flush=True)
    print(f"\ndesigned outcomes hit: {hits} / {total}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (out / "causal_calibration.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
