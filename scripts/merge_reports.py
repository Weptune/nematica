"""Merge benchmark reports of the same copy scored on different splits into one report.

    python scripts/merge_reports.py out.json part1.json part2.json ...
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.score import write_report  # noqa: E402

out, parts = sys.argv[1], sys.argv[2:]
docs = [json.loads(Path(p).read_text(encoding="utf-8")) for p in parts]
names = {d["copy"] for d in docs}
if len(names) != 1:
    raise SystemExit(f"different copies: {names}")
splits = [{r["split"] for r in d["rows"]} for d in docs]
if any(a & b for i, a in enumerate(splits) for b in splits[i + 1:]):
    raise SystemExit("the parts overlap in splits; refusing to merge")
rows = [r for d in docs for r in d["rows"]]
print(write_report(names.pop(), rows, out, meta={**docs[0].get("meta", {}), "merged_from": [Path(p).name for p in parts]}))
