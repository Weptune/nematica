"""Preprint draft 2, figure 2: internal share (M1) of each network family against the 49 mice (Study 2,
reached recordings, S7 retries replacing originals). Summary numbers only."""
import glob
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "docs/figures/slow_runs"
mice_ids = set(json.load(open(R / "mice_table.json"))["rows"])
mice = [json.loads(l) for l in open(R / "mice.jsonl")]
m1 = np.array([m["M1"] for m in mice if m["id"] in mice_ids])
rows = []
for f in sorted(glob.glob(str(R / "ais*.jsonl"))):
    if "dry" in f or "retry" in f:
        continue
    rows += [json.loads(l) for l in open(f)]
rt = {(r["family"], r["run"], r["id"]): r for r in map(json.loads, open(R / "ais_retry.jsonl"))}
rows = [rt.get((r["family"], r["run"], r.get("id")), r) for r in rows]
rows = [r for r in rows if "error" not in r and r.get("reached") and r["id"] in mice_ids]

name = {"A2": "Task-trained RNN", "A3": "GRU", "A5": "CfC"}
groups = defaultdict(list)
for r in rows:
    fam, run = r["family"], r["run"]
    if fam in name:
        groups[name[fam]].append(r["M1"])
    elif fam == "A6":
        groups["Pythia " + run.split("pythia-")[1].split("-")[0].upper()].append(r["M1"])
    elif fam == "A7":
        groups["Mamba " + run.split("mamba-")[1].split("-")[0].upper()].append(r["M1"])
    elif fam in ("A1", "A4"):
        groups[("Random RNN" if fam == "A1" else "Spiking network") + " gain " + run.split("gain")[1]].append(r["M1"])

INK, MUTED, GRID = "#1f2328", "#5b6470", "#e3e6ea"
C_MICE, C_NET, C_SWEEP = "#c2185b", "#1f6fb2", "#8a96a3"
fixed = [k for k in groups if "gain" not in k]
fixed.sort(key=lambda k: np.median(groups[k]))
fig, ax = plt.subplots(figsize=(8.2, 5.6), dpi=200)
q1, q2, q3 = np.percentile(m1, [25, 50, 75])
ax.axvspan(q1, q3, color=C_MICE, alpha=0.12, lw=0)
ax.axvline(q2, color=C_MICE, lw=2)
labels = []
y = 0
for k in fixed:
    v = np.array(groups[k])
    a, b, c = np.percentile(v, [25, 50, 75])
    ax.plot([a, c], [y, y], color=C_NET, lw=2.2, solid_capstyle="round")
    ax.plot(b, y, "o", color=C_NET, ms=7, mec="white", mew=1.2)
    labels.append(k)
    y += 1
for fam in ("Random RNN", "Spiking network"):
    meds = sorted(np.median(groups[k]) for k in groups if k.startswith(fam))
    ax.plot([meds[0], meds[-1]], [y, y], color=C_SWEEP, lw=2.2, ls=(0, (1, 1.6)))
    ax.plot(meds, [y] * len(meds), "o", color=C_SWEEP, ms=5, mec="white", mew=0.8)
    labels.append(f"{fam} (8 input gains)")
    y += 1
ax.set_yticks(range(len(labels)), labels, color=INK, fontsize=9)
ax.set_xlim(-0.05, 1.02)
ax.set_xlabel("Internal share M1 (lag 2), at each mouse's own instrument", color=INK, fontsize=9.5)
ax.grid(axis="x", color=GRID, lw=0.8)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(MUTED)
ax.tick_params(axis="x", colors=MUTED, labelsize=8.5)
ax.tick_params(axis="y", length=0)
ax.text(q3 + 0.012, len(labels) - 0.25, f"49 mice: median {q2:.2f}\nband = middle half", color=C_MICE,
        fontsize=8.5, ha="left", va="center")
ax.set_ylim(-0.7, len(labels) + 0.6)
ax.set_title("Networks fall on both sides of mouse visual cortex", loc="left", color=INK, fontsize=11.5,
             fontweight="bold", pad=14)
fig.text(0.01, 0.01, "Dots: median over mice; bars: middle half. Grey: medians at each of 8 input gains. "
         "Study 2, reached recordings only.", color=MUTED, fontsize=7.5)
fig.tight_layout(rect=(0, 0.03, 1, 1))
out = ROOT / "docs/figures/slow_paper/fig2_m1_by_family.png"
fig.savefig(out, facecolor="white")
print(out, {k: round(float(np.median(v)), 3) for k, v in groups.items() if "gain" not in k})
