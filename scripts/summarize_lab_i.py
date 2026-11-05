"""Lab I summary: shares of the individuals' agreement and the pre-registered verdicts."""
import csv
import glob
from pathlib import Path

FIG = Path(__file__).resolve().parents[1] / "docs" / "figures"
lines = ["Lab I: the worm experiment's imperfections in lab brains (shares of the individuals' agreement)", ""]
for name in ("pool", "pool_hold16", "pool_hold30", "pool_hold60", "misid", "offtarget", "all", "offmatched", "offhalf", "leak", "allmeasured"):
    rows = []
    for f in sorted(glob.glob(str(FIG / f"ann_imperfect_{name}_folds*.csv"))):
        rows += list(csv.DictReader(open(f)))
    if not rows:
        continue
    lines.append(name)
    for p in sorted({int(r["fold"]) for r in rows}):
        rr = {r["copy"]: r for r in rows if int(r["fold"]) == p}
        if "hybrid_kernels" not in rr:
            lines.append(f"  pool {p}: incomplete")
            continue
        ind = float(rr["var3_spontaneous"]["real_agreement"])
        sh = {c: float(rr[c]["echo_agreement"]) / ind for c in rr}
        watch = max(sh["var3_spontaneous"], sh["stitch3_hp"])
        poke = sh["hybrid_kernels"]
        v = ("unusable" if poke < 0.6 or ind < 0.05 else "worm-like" if watch < 0.3 else "lab-like" if watch >= 0.5 else "intermediate")
        lines.append(f"  pool {p}: individuals agree {ind:.3f}; another individual {sh['another_individual']:.0%}; watching (VAR3) "
                     f"{sh['var3_spontaneous']:.0%}; stitched {sh['stitch3_hp']:.0%}; poke-trained {poke:.0%}; verdict {v}")
    lines.append("")
txt = "\n".join(lines)
print(txt)
(FIG / "ann_imperfect_summary.txt").write_text(txt + "\n")
