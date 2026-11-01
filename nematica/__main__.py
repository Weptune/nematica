"""Command line: python -m nematica score path/to/copy.py:ClassName"""

from __future__ import annotations

import argparse
import sys
import time
import warnings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="nematica", description="Score a brain copy on the NEMATICA ruler.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("score", help="score a copy: path/to/file.py:ClassName")
    sc.add_argument("copy")
    sc.add_argument("--data", default="data/raw/randi2023_wt_npz",
                    help="folder of converted recordings (scripts/convert_pumpprobe.py)")
    sc.add_argument("--split", choices=("cv3", "blocks1", "both"), default="both")
    sc.add_argument("--fold", type=int, action="append", help="score only this fold (repeatable)")
    sc.add_argument("--quick", action="store_true", help="split cv3, fold 0 only")
    sc.add_argument("--no-pci", action="store_true", help="skip the complexity levels (faster)")
    sc.add_argument("--out", default=None, help="JSON report path (default results/scores/<name>.json)")
    args = ap.parse_args(argv)
    warnings.filterwarnings("ignore", category=RuntimeWarning)   # NaN-heavy recordings: expected

    from .score import format_summary, load_copy, score, summary, write_report
    factory = load_copy(args.copy)
    splits = ("cv3",) if args.quick else ("cv3", "blocks1") if args.split == "both" else (args.split,)
    folds = [0] if args.quick else args.fold
    name = getattr(factory(), "name", "copy")
    t0 = time.time()
    rows = score(factory, args.data, splits=splits, folds=folds, pci=not args.no_pci,
                 log=lambda m: print(m, file=sys.stderr, flush=True))
    out = write_report(name, rows, args.out or f"results/scores/{name}.json")
    print(format_summary(name, summary(rows)))
    print(f"\nReport: {out}  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
