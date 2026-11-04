"""Gather every result the overnight pipeline produces into one file for whoever writes it up:
docs/figures/AUTO_REPORT.txt. Reads only files that exist; never changes them.
Usage: python scripts/collect_report.py
"""
import csv
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
DER = ROOT / "data" / "derived"


def section(title, lines):
    return [f"== {title} ==", *lines, ""]


def text(path):
    return path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else ["(not yet)"]


def ratios(path):
    if not path.exists():
        return ["(not yet)"]
    out = []
    for r in csv.DictReader(path.open(encoding="utf-8")):
        try:
            ratio = float(r["echo_agreement"]) / float(r["real_agreement"])
            out.append(f"fold {r['fold']}  {r['copy']:20s} {r['verdict']:12s} share of individuals' agreement "
                       f"{ratio:.2f}  (individuals agree at {float(r['real_agreement']):.3f})")
        except (KeyError, ValueError, ZeroDivisionError):
            pass
    return out or ["(empty)"]


def main():
    lines = [f"NEMATICA auto-report, {time.strftime('%Y-%m-%d %H:%M')}", ""]
    n = len(list((DER / "ccep").glob("*.npz"))) if (DER / "ccep").exists() else 0
    lines += section("Human (pre-registered): docs/figures/ccep_summary.txt",
                     [f"recordings reduced: {n} of 117"] + text(FIG / "ccep_summary.txt"))
    lines += section("Hippocampus download marker", text(DER / "hippo" / "STREAM_DONE.txt"))
    for name in ("hippo_summary", "hippo_reading-all_summary", "hippo_sham130_summary",
                 "hippo_sham130_reading-all_summary", "hippo_followup_summary"):
        lines += section(f"Hippocampus: {name}.txt", text(FIG / f"{name}.txt"))
    touch = DER / "touch"
    lines += section("Touch cortex download",
                     [f"sessions: {sorted(p.name for p in touch.iterdir() if p.is_dir())}" if touch.exists() else "(not yet)"]
                     + text(touch / "errors.txt")[:5])
    lines += section("Lab queue log", text(DER / "lab_queue_log.txt"))
    for p in sorted(FIG.glob("ann_queue_*.csv")):
        if ".part" not in p.name:
            lines += section(p.name, ratios(p))
    (FIG / "AUTO_REPORT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
