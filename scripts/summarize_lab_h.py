"""Lab H summary: shares of the individuals' agreement and the pre-registered verdicts."""
import csv
import glob
from pathlib import Path

FIG = Path(__file__).resolve().parents[1] / "docs" / "figures"


def load(pattern):
    rows = []
    for f in sorted(glob.glob(str(FIG / pattern))):
        rows += list(csv.DictReader(open(f)))
    return rows


lines = ["Lab H: trained networks through the worm pipeline (shares of the individuals' agreement)", ""]
lines.append("Pre-registered poke (hold 8), pool 0, unusable runs: individuals agree")
for f in sorted(glob.glob(str(FIG / "ann_trained_*_fold0.csv"))):
    if "hold" in f or "calib" in f:
        continue
    r = list(csv.DictReader(open(f)))
    lines.append(f"  {Path(f).name}: {r[0]['real_agreement']}")
lines.append("")
for task in ("flipflop", "cdi"):
    for tag in ("init", "trained"):
        rows = load(f"ann_trained_{task}_{tag}_hold*_fold*.csv")
        if not rows:
            continue
        pools = sorted({int(r["fold"]) for r in rows})
        lines.append(f"{task} {tag} (hold {Path(glob.glob(str(FIG / f'ann_trained_{task}_{tag}_hold*_fold0.csv'))[0]).name.split('hold')[1].split('_')[0]} frames)")
        for p in pools:
            rr = {r["copy"]: r for r in rows if int(r["fold"]) == p}
            ind = float(rr["var3_spontaneous"]["real_agreement"])
            sh = {c: float(rr[c]["echo_agreement"]) / ind for c in rr}
            watch = max(sh["var3_spontaneous"], sh["stitch3_hp"])
            poke = sh["hybrid_kernels"]
            if poke < 0.6 or ind < 0.05:
                v = "unusable"
            elif watch < 0.3:
                v = "worm-like"
            elif watch >= 0.5:
                v = "lab-like"
            else:
                v = "intermediate"
            lines.append(f"  pool {p}: individuals agree {ind:.3f}; another individual {sh['another_individual']:.0%}; "
                         f"watching (VAR3) {sh['var3_spontaneous']:.0%}; stitched {sh['stitch3_hp']:.0%}; "
                         f"poke-trained {poke:.0%}; verdict {v}")
        lines.append("")
txt = "\n".join(lines)
print(txt)
(FIG / "ann_trained_summary.txt").write_text(txt + "\n")
