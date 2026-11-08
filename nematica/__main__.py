"""Command line for the NEMATICA worm benchmark.

    python -m nematica check path/to/copy.py:ClassName        (a fast contract check, about a minute)
    python -m nematica score path/to/copy.py:ClassName [--seeds 3] [--quick]
    python -m nematica report results/scores/<name>.json [--compare other.json ...]
    python -m nematica export --out kit/                      (for copies written in other languages)
    python -m nematica score-files sims/ --name my-copy
"""

from __future__ import annotations

import argparse
import datetime as _dt
import subprocess
import sys
import time
import warnings
from pathlib import Path

DATA = "data/raw/randi2023_wt_npz"


def _commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=Path(__file__).resolve().parents[1], timeout=5).stdout.strip() or None
    except Exception:
        return None


def _slug(name: str) -> str:
    """A safe file name from a copy's name."""
    import re
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "copy"


def _finish(name, rows, out, html, compare, t0, command, data=None, extra_meta=None):
    from .report_html import write_html
    from .score import format_answers, write_report
    meta = {**(extra_meta or {}), "date": _dt.date.today().isoformat(), "commit": _commit(), "command": command,
            "seconds": round(time.time() - t0),
            }
    suffix = ".quick" if (extra_meta or {}).get("quick") else ""
    path = write_report(name, rows, out or f"results/scores/{_slug(name)}{suffix}.json", meta=meta)
    print(format_answers(name, rows))
    print(f"\nReport: {path}  ({time.time() - t0:.0f} s)")
    if html:
        print(f"HTML:   {write_html(path, compare=compare or [])}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="nematica", description="The NEMATICA worm benchmark.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("score", help="score a copy written in Python: path/to/file.py:ClassName")
    sc.add_argument("copy")
    sc.add_argument("--data", default=DATA, help="folder of converted recordings (scripts/convert_pumpprobe.py)")
    sc.add_argument("--split", choices=("cv3", "blocks1", "both"), default="both")
    sc.add_argument("--fold", type=int, action="append", help="score only this fold (repeatable)")
    sc.add_argument("--seeds", type=int, default=1, help="noise seeds per held-out worm (3 recommended for claims)")
    sc.add_argument("--quick", action="store_true", help="split cv3, fold 0, one seed (a first look, not a verdict)")
    sc.add_argument("--no-pci", action="store_true",
                    help="skip echo spread and complexity (faster; the poke half is then not judged)")
    sc.add_argument("--out", default=None, help="JSON report path (default results/scores/<name>.json)")
    sc.add_argument("--no-html", action="store_true", help="do not write the HTML report")
    sc.add_argument("--compare", nargs="*", default=[], help="other reports to mark on the charts")

    ck = sub.add_parser("check", help="a fast contract check of a copy before a full run")
    ck.add_argument("copy")
    ck.add_argument("--data", default=DATA)

    rp = sub.add_parser("report", help="write the HTML report for a saved JSON report")
    rp.add_argument("report")
    rp.add_argument("--compare", nargs="*", default=[])
    rp.add_argument("--out", default=None)

    lb = sub.add_parser("leaderboard", help="one HTML table of several saved reports")
    lb.add_argument("reports", nargs="+")
    lb.add_argument("--out", default="results/scores/leaderboard.html")

    ex = sub.add_parser("export", help="write the benchmark kit (templates and fold lists) for other languages")
    ex.add_argument("--data", default=DATA)
    ex.add_argument("--out", default="kit")

    sf = sub.add_parser("score-files", help="score simulations saved as sims/<split>/fold<k>/seed<s>/<uid>.npz")
    sf.add_argument("sims")
    sf.add_argument("--name", required=True)
    sf.add_argument("--data", default=DATA)
    sf.add_argument("--no-pci", action="store_true")
    sf.add_argument("--out", default=None)
    sf.add_argument("--no-html", action="store_true")
    sf.add_argument("--compare", nargs="*", default=[])
    sf.add_argument("--kit", default=None, help="the kit folder: checks that the data matches the kit's manifest")

    args = ap.parse_args(argv)
    warnings.filterwarnings("ignore", category=RuntimeWarning)   # NaN-heavy recordings: expected
    log = lambda m: print(m, file=sys.stderr, flush=True)  # noqa: E731
    command = "python -m nematica " + " ".join(argv if argv is not None else sys.argv[1:])
    t0 = time.time()

    if args.cmd == "score":
        from .score import load_copy, score
        factory = load_copy(args.copy)
        splits = ("cv3",) if args.quick else ("cv3", "blocks1") if args.split == "both" else (args.split,)
        folds = [0] if args.quick else args.fold
        seeds = 1 if args.quick else args.seeds
        if seeds < 1:
            ap.error("--seeds must be at least 1")
        name = getattr(factory(), "name", "copy")
        rows = score(factory, args.data, splits=splits, folds=folds, pci=not args.no_pci, seeds=seeds, log=log)
        _finish(name, rows, args.out, not args.no_html, args.compare, t0, command, args.data,
                {"quick": bool(args.quick), "folds": folds, "seeds": seeds, "splits": list(splits)})
    elif args.cmd == "check":
        from .score import check, load_copy
        return 1 if check(load_copy(args.copy), args.data, log=print) else 0
    elif args.cmd == "report":
        from .report_html import write_html
        print(write_html(args.report, args.out, compare=args.compare))
    elif args.cmd == "leaderboard":
        import json
        from .report_html import render_leaderboard
        reps = {}
        for p in args.reports:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
            k = d.get("copy", Path(p).stem)
            if k in reps:
                k = f"{k} ({Path(p).name})"
            reps[k] = d
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(render_leaderboard(reps), encoding="utf-8")
        print(args.out)
    elif args.cmd == "export":
        from .kit import export
        out = export(args.data, args.out)
        print(f"Kit written to {out} (templates are derived from your local copy of the atlas: do not redistribute)")
    elif args.cmd == "score-files":
        from .kit import score_files, verify_data
        if args.kit:
            bad = verify_data(args.kit, args.data)
            if bad:
                print(f"the data in {args.data} does not match the kit: {', '.join(bad[:3])}", file=sys.stderr)
                return 2
        rows = score_files(args.sims, args.data, args.name, pci=not args.no_pci, log=log)
        _finish(args.name, rows, args.out, not args.no_html, args.compare, t0, command, args.data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
