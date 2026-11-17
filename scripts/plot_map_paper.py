"""Preprint draft 2, figure 1: per-mouse slow memory (map study, amendment 27), in the light style of
figure 2 (scripts/plot_slow_paper.py). Same data as plot_map.py permouse(): docs/figures/map_permouse.json.
Summary numbers only."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
d = json.loads((ROOT / "docs/figures/map_permouse.json").read_text())
pa, ps = d["pairs"]["A1"], {p["mouse"]: p for p in d["pairs"]["A1-slow"]}
order = sorted(pa, key=lambda p: p["mouse_value"])
x = np.arange(len(order))
mv = np.array([p["mouse_value"] for p in order])
a1 = np.array([p["ai_value"] for p in order])
a1s = np.array([ps[p["mouse"]]["ai_value"] if p["mouse"] in ps else np.nan for p in order], dtype=float)

INK, MUTED, GRID = "#1f2328", "#5b6470", "#e3e6ea"
C_MICE, C_NET, C_SLOW = "#c2185b", "#1f6fb2", "#b26a00"
fig, ax = plt.subplots(figsize=(8.2, 4.9), dpi=200)
for i in x:
    ax.plot([i, i], [a1[i], mv[i]], color=GRID, lw=1.4, zorder=1)
ax.scatter(x, mv, s=30, color=C_MICE, zorder=3, edgecolors="white", linewidths=0.8, label="Mouse")
ax.scatter(x, a1, s=26, color=C_NET, zorder=3, edgecolors="white", linewidths=0.8,
           label="Random RNN at that mouse's instrument")
ax.scatter(x, a1s, s=26, facecolors="white", edgecolors=C_SLOW, linewidths=1.4, zorder=3,
           label="Same RNN with slow drives")
ax.set_xticks([])
ax.set_xlabel(f"{len(order)} Allen mice, ordered by their own slow memory (spontaneous activity)",
              color=INK, fontsize=9.5)
ax.set_ylabel("Slow memory", color=INK, fontsize=9.5)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color(MUTED)
ax.tick_params(axis="y", colors=MUTED, labelsize=8.5)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, labelcolor=INK,
          handletextpad=0.3, columnspacing=1.4)
n_low = int(np.sum(a1 < mv))
n_slow = int(np.sum(np.isfinite(a1s)))
n_high = int(np.sum(a1s[np.isfinite(a1s)] > mv[np.isfinite(a1s)]))
ax.set_title("Mouse by mouse, cortex sits between the two networks", loc="left", color=INK, fontsize=11.5,
             fontweight="bold", pad=26)
fig.text(0.01, 0.01, f"Random RNN lower in {n_low} of {len(order)} mice; with slow drives higher in {n_high} of "
         f"{n_slow} measured. Map study, amendment 27.", color=MUTED, fontsize=7.5)
fig.tight_layout(rect=(0, 0.03, 1, 1))
out = ROOT / "docs/figures/slow_paper/fig1_permouse.png"
fig.savefig(out, facecolor="white")
print(out, n_low, len(order), n_high, n_slow)
