"""Merge the reference reports, write the leaderboard and the emulator's report with the references
marked, copy both to docs/benchmark/ (scores only), and fill the reference table in docs/BENCHMARK.md.

    python scripts/build_benchmark_pages.py
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.verdicts import ALL_LEVELS, answers  # noqa: E402
from nematica.report_html import render, render_leaderboard  # noqa: E402

REF = Path("results/scores/reference")
OUT = Path("docs/benchmark")
OUT.mkdir(parents=True, exist_ok=True)
for slug in ("silent", "linear_model_from_rest", "var3_from_rest", "first_hybrid"):
    parts = [REF / f"{slug}.cv3.json", REF / f"{slug}.blocks1.json"]
    if all(p.exists() for p in parts):
        subprocess.run([sys.executable, "scripts/merge_reports.py", str(REF / f"{slug}.json"), *map(str, parts)], check=True)
reports = {}
for p in sorted(REF.glob("*.json")):
    if p.name.count(".") > 1:                      # per-split parts
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    reports[d["copy"]] = d
(OUT / "leaderboard.html").write_text(render_leaderboard(reports), encoding="utf-8")
emu = reports.get("NEMATICA emulator")
if emu:
    (OUT / "emulator.html").write_text(render(emu, {k: v for k, v in reports.items() if k != "NEMATICA emulator"}),
                                       encoding="utf-8")
rows = ["| copy | cv3: rest, poked (seeds passing) | blocks1: rest, poked | echo size, median excess | dimensionality, median excess |",
        "|---|---|---|---|---|"]
for k, d in reports.items():
    a = answers(d["rows"])
    def cell(s):
        x = a.get(s)
        if not x:
            return "-"
        if not x["judged"]:
            return "not judged"
        return f"{x['rest_pass_seeds']}/{x['seeds']}, {x['poke_pass_seeds']}/{x['seeds']}"
    def ex(lv):
        v = [a[s]["levels"][lv]["excess_median"] for s in a if lv in a[s]["levels"] and a[s]["levels"][lv]["excess_median"] is not None]
        return " / ".join(f"{x:+.2f}" for x in v) if v else "-"
    rows.append(f"| {k} | {cell('cv3')} | {cell('blocks1')} | {ex('C2.magnitude')} | {ex('L2.dimension')} |")
table = "\n".join(rows) + ("\n\nThe full table, every level: [`docs/benchmark/leaderboard.html`](benchmark/leaderboard.html); "
                           "the emulator's report: [`docs/benchmark/emulator.html`](benchmark/emulator.html). The emulator was "
                           "designed on these worms (cv3 for selection), so its passes are not a confirmation; on unc-31 worms it "
                           "passed 3 of 5 seeds (bar 4 of 5) and it fails on freely moving worms (README, tests U and T). VAR(3) and "
                           "the first hybrid read out one row per neuron class, which inflates echo size and spread.")
doc = Path("docs/BENCHMARK.md")
s = doc.read_text(encoding="utf-8")
start, end = "<!-- reference table -->", "<!-- /reference table -->"
block = f"{start}\n{table}\n{end}"
if "REFERENCE_TABLE" in s:
    s = s.replace("REFERENCE_TABLE", block)
elif start in s:
    s = s[:s.index(start)] + block + s[s.index(end) + len(end):]
doc.write_text(s, encoding="utf-8")
print("written:", ", ".join(sorted(reports)))
