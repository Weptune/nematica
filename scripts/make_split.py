"""Create and freeze the worm-level split for a dataset. Refuses to overwrite.

Usage:  python scripts/make_split.py <data folder (JSON or *-cudata.h5)> <out.yaml> \
            --n-test 8 --n-val 4 --seed 0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.data import (load_copper_dir, load_wormwideweb_dir,  # noqa: E402
                           make_worm_split, save_split)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("out")
    ap.add_argument("--dataset", default="atanas2023")
    ap.add_argument("--n-test", type=int, default=8)
    ap.add_argument("--n-val", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    folder = Path(args.folder)
    if any(folder.glob("*-cudata.h5")):
        recs = load_copper_dir(folder)
    else:
        recs = load_wormwideweb_dir(folder, dataset=args.dataset)
    conds = ["heat" if "heat" in r.conditions else "baseline" for r in recs]
    split = make_worm_split([r.uid for r in recs], conds, args.n_test, args.n_val, args.seed)
    save_split(split, args.out, args.dataset)
    print(f"Froze split to {args.out}: {len(split['train'])} train, "
          f"{len(split['val'])} val, {len(split['test'])} test")
    print("Test worms:", ", ".join(split["test"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
