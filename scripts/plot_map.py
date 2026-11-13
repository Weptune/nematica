"""Figures for the map (docs/MAP.md): drawn only from the result files, in the project palette.
  instrument  which measurements survive recording at each preparation's instrument (step 2)
  worm        the worm map: worms, their envelope and every AI (map_worm.json), when it exists
Output: docs/figures/map/*.png (and .svg)."""
import json
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures/map"
FONTS = Path("/tmp/fonts")
BG, INK, MUTED, FAINT = "#0d0a24", "#e4dcff", "#9a90c4", "#2a2350"
CAT = {"pink": "#e0468f", "blue": "#3f8fd2", "amber": "#c47f2f", "violet": "#8a74e0"}
NAMES = {"shared_fraction": "Shared fraction", "slow_fraction": "Slow memory", "timescale_spread": "Timescale spread",
         "coupling_spread": "Coupling spread", "sparsity": "Sparsity", "drift": "Drift",
         "spectrum_steepness": "Spectrum steepness"}


def fonts():
    for f in FONTS.glob("*.ttf"):
        font_manager.fontManager.addfont(str(f))
    plt.rcParams.update({"font.family": "Schibsted Grotesk", "text.color": INK, "axes.labelcolor": MUTED,
                         "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": BG, "axes.facecolor": BG,
                         "savefig.facecolor": BG, "axes.edgecolor": FAINT})


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=220, bbox_inches="tight", pad_inches=0.35)
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", pad_inches=0.35)


def instrument():
    s150 = json.loads(Path("/tmp/step2_150.json").read_text())
    s1000 = json.loads((ROOT / "docs/figures/map_step2.json").read_text())
    worm = json.loads((ROOT / "docs/figures/map_step2_worm.json").read_text())
    cols = [("The network\nitself", "native/-", None, "no instrument"),
            ("Worm\ncalcium imaging", "calcium/R2", "worm", "8 frames per\ntimescale"),
            ("Mouse cortex\nNeuropixels", "spikes/R4", "s", "0.16 spikes per\nunit per timescale"),
            ("Rat culture\nHD-MEA", "spikes/R9", "s", "0.22"),
            ("Mouse\norganoid", "spikes/R10b", "s", "0.46"),
            ("Rat planar\nculture", "spikes/R10d", "s", "0.09")]
    rows = ["shared_fraction", "slow_fraction", "timescale_spread", "coupling_spread", "sparsity", "drift",
            "spectrum_steepness"]
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    for j, (title, key, kind, sub) in enumerate(cols):
        for i, m in enumerate(rows):
            if kind == "worm":
                ok, ok2 = m in worm["used"]["calcium/R2"], None
            elif kind == "s":
                ok, ok2 = m in s150["used"].get(key, []), m in s1000["used"].get(key, [])
            else:
                ok, ok2 = m in s1000["used"]["native/-"], None
            y = -i
            if m == "sparsity" and kind == "s":
                ax.text(j, y, "undefined\nfor spikes", ha="center", va="center", fontsize=7.5, color=FAINT, linespacing=1.1)
                continue
            if ok:
                ax.scatter([j], [y], s=230, color=INK, zorder=3)
            elif ok2:
                ax.scatter([j], [y], s=230, facecolor=BG, edgecolor=CAT["amber"], linewidth=2.2, zorder=3)
            else:
                ax.scatter([j], [y], s=26, color=FAINT, zorder=3)
        ax.text(j, 1.25, title, ha="center", va="bottom", fontsize=10.5, color=INK, linespacing=1.15)
        ax.text(j, 0.55, sub, ha="center", va="bottom", fontsize=8, color=MUTED, linespacing=1.15)
    for i, m in enumerate(rows):
        ax.text(-0.62, -i, NAMES[m], ha="right", va="center", fontsize=10.5, color=INK)
    ax.plot([1.5, 1.5], [-len(rows) + 0.6, 0.4], color=FAINT, lw=1)
    ax.set_xlim(-2.4, len(cols) - 0.4)
    ax.axis("off")
    fig.text(0.07, 1.06, "Record an AI the way a brain is recorded, and most measurements stop working",
             fontsize=17, family="Newsreader 16pt", color=INK)
    fig.text(0.07, 0.995, "Does each measurement still track the property it is meant to measure after the recording?\n"
             "Synthetic networks with known properties, recorded through each real dataset's own instrument.",
             fontsize=9.5, color=MUTED)
    ly = -len(rows) + 0.1
    ax.scatter([0.0], [ly], s=120, color=INK); ax.text(0.15, ly, "passes calibration", va="center", fontsize=9, color=MUTED)
    ax.scatter([1.9], [ly], s=120, facecolor=BG, edgecolor=CAT["amber"], linewidth=2); ax.text(2.05, ly, "passes only with 6.7x longer windows", va="center", fontsize=9, color=MUTED)
    ax.scatter([4.35], [ly], s=20, color=FAINT); ax.text(4.5, ly, "fails", va="center", fontsize=9, color=MUTED)
    ax.set_ylim(-len(rows) - 0.2, 2.3)
    fig.text(0.07, -0.02, "C1: rank correlation with the true property at least 0.9; C4: robust to unit count and network speed. "
             "50 units per draw. Spike rows: 20 ms bins, spikes per unit per timescale as shown. docs/MAP.md, step 2.",
             fontsize=7.8, color="#6a5f9a")
    save(fig, "instrument")


if __name__ == "__main__":
    fonts()
    for name in sys.argv[1:] or ["instrument"]:
        globals()[name]()
