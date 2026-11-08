"""Turn research-pipeline caches (scripts/run_same_worms.py, which runs the same procedure as
`nematica score`) into a benchmark report, so long research runs need not be repeated.

    python scripts/cache_to_report.py <spec> <name> [--out results/scores/reference/<file>.json]
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.score import write_report  # noqa: E402

CACHES = {"cv3": "results/emulator_select", "blocks1": "results/emulator_confirm"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("name"); ap.add_argument("--out"); ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--note", default=None, help="a caveat shown with the copy in its report and on the leaderboard")
    ap.add_argument("--command", default=None, help="the equivalent nematica command, shown under Reproduce")
    a = ap.parse_args()
    rows = []
    for split, cache in CACHES.items():
        for s in range(a.seeds):
            sfx = f"_s{s}" if s else ""
            for f in range(3):
                p = Path(cache) / f"fluct_f{f}_{a.spec}{sfx}.csv"
                if not p.exists():
                    raise FileNotFoundError(p)
                for r in pd.read_csv(p).to_dict("records"):
                    r = {k: (None if isinstance(v, float) and v != v else v) for k, v in r.items()}
                    r.update(split=split, seed=s, fold=f, n_folds=3, system=a.name)
                    rows.append(r)
    out = write_report(a.name, rows, a.out or f"results/scores/reference/{a.spec}.json",
                       meta={"date": "2026-11-08", "command": a.command or f"python scripts/run_same_worms.py --models {a.spec} --norm fluct --pci (per split, fold and seed)", "note": a.note})
    print(out)


if __name__ == "__main__":
    main()
