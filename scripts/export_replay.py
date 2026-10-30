"""Export copper-set test worms as replay bundles for the web lab.

Usage:  python scripts/export_replay.py data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
            --split configs/splits/copper2026.yaml --out lab/public/data [--uid 2024-06-18-12]

Only test worms are exported by default: the showcase shows animals no model trained on.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.data import load_copper_dir, load_split  # noqa: E402
from nematica.export.replay import export_replay  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--split", required=True)
    ap.add_argument("--out", default="lab/public/data")
    ap.add_argument("--uid", action="append", help="export only these uids (must be test worms)")
    args = ap.parse_args()

    split = load_split(args.split)
    wanted = set(args.uid) if args.uid else set(split["test"])
    not_test = wanted - set(split["test"])
    if not_test:
        print(f"Refusing to export non-test worms for the showcase: {sorted(not_test)}", file=sys.stderr)
        return 1

    out = Path(args.out)
    index = []
    for rec in load_copper_dir(args.folder):
        if rec.uid not in wanted:
            continue
        info = export_replay(rec, out / f"replay_{rec.uid}.json", split="test")
        index.append({"uid": rec.uid, "file": f"replay_{rec.uid}.json", "neurons": info["neurons"]})
        print(info)
    (out / "index.json").write_text(json.dumps({"replays": index}, indent=1), encoding="utf-8")
    print(f"Wrote {len(index)} replay bundles and index.json to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
