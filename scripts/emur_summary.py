"""Test R feasibility summary (docs/EMU_R.md): from structure_<dandiset>.json (metadata only), per file:
calcium time series found (path, shape, rate or time stamps), number of ROI labels, protocol text, and any
stimulus or interval tables. Applies the stop rule's checkable parts. Prints a table; reads no activity.

Usage: python -I scripts/emur_summary.py 000565 [000541 ...]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / "docs/figures/emur"
SKIP = ("specifications/", "general/optophysiology", "NeuroPALImageRaw", "ProcessedImage")


def summarise(ds):
    rows = json.loads((F / f"structure_{ds}.json").read_text())
    out = []
    for f in rows:
        if "error" in f:
            out.append({"file": f["path"], "error": f["error"]})
            continue
        dd = [d for d in f["datasets"] if not any(s in d["path"] for s in SKIP)]
        series, labels, text, stim = [], 0, {}, []
        for d in dd:
            p = d["path"]
            if p.endswith("/data") and len(d["shape"]) == 2 and d["dtype"].startswith(("float", "int", "uint")):
                series.append({"path": p, "shape": d["shape"], "attrs": d.get("attrs", {})})
            if p.endswith("/timestamps") and "timestamps_first_second_last" in d:
                series.append({"path": p, "ts": d["timestamps_first_second_last"], "n": d["shape"][0]})
            if p.endswith("/starting_time"):
                series.append({"path": p, "attrs": d.get("attrs", {})})
            if "ID_labels" in p and "index" not in p:
                labels = max(labels, d["shape"][0])
            if p in ("session_description", "general/experiment_description", "general/lab",
                     "general/subject/description", "general/subject/strain"):
                text[p.rsplit("/", 1)[-1]] = (d.get("values") or [""])[0]
            if p.startswith(("intervals/", "stimulus/")) or "ogen" in p.lower() or "stim" in p.lower():
                stim.append({"path": p, "shape": d["shape"], "first": (d.get("values") or [])[:6]})
        out.append({"file": f["path"], "text": text, "series": series, "labels_rows": labels, "stim": stim})
    return out


if __name__ == "__main__":
    for ds in sys.argv[1:]:
        res = summarise(ds)
        (F / f"summary_{ds}.json").write_text(json.dumps(res, indent=1))
        print(f"== {ds}: {len(res)} files")
        for r in res:
            if "error" in r:
                print("  ", r["file"], "ERROR", r["error"][:80])
                continue
            s = "; ".join(f"{x['path']} {x.get('shape', '')}{x.get('attrs', '')}{x.get('ts', '')}" for x in r["series"])
            print("  ", r["file"].split("/")[-1][:40], "| labels", r["labels_rows"], "|", r["text"].get("session_description", "")[:60],
                  "|", s[:260], "| stim", len(r["stim"]))
