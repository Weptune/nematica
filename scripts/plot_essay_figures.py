"""Figures for the essay "a brain is more than its activity" (weptune.dev, 8 Nov 2026), drawn from the
project's own result files (summary numbers only, no recordings).

Usage:  python scripts/plot_essay_figures.py OUTDIR
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import plot_post_figures as P  # noqa: E402  (shared style and two existing figures)

ORANGE, NAVY, RED, GREEN, INK, MUTED, GRID, BOX = P.ORANGE, P.NAVY, P.RED, P.GREEN, P.INK, P.MUTED, P.GRID, P.BOX
BAND = "#dcefe2"


def rows(name):
    return list(csv.DictReader(open(ROOT / "docs/figures" / name)))


def fig_average_worm(out):
    d = rows("shrinkage.csv")
    lam = np.array([float(r["lam"]) for r in d])
    r2 = np.array([float(r["within_worm_r2"]) for r in d])
    ind = np.array([float(r["individuality"]) for r in d])
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 5))
    a.plot(lam, r2, "-o", color=NAVY, lw=2.4, ms=7)
    k = int(np.argmax(r2))
    a.plot(lam[k], r2[k], "o", color=ORANGE, ms=13, mec="white", mew=2, zorder=4)
    a.annotate(f"Best forecaster\n(lambda = {lam[k]:,.0f})", xy=(lam[k], r2[k]), xytext=(9000, 0.722),
               color=ORANGE, fontweight="bold", fontsize=10.5, bbox={**BOX, "ec": ORANGE},
               arrowprops=dict(arrowstyle="->", color=ORANGE))
    a.set_xscale("log")
    a.set_xlabel("Pull towards one shared model (lambda)")
    a.set_ylabel("Forecasting skill (within-worm R²)")
    a.set_title("Forecasting rewards pulling every worm to the same model")
    b.axhspan(0.95, 1.05, color=BAND, lw=0)
    b.axhline(1.0, color=GREEN, lw=1.5)
    b.text(32, 1.07, "as varied as real worms", color=GREEN, fontsize=10, fontweight="bold")
    b.plot(lam, ind, "-o", color=RED, lw=2.4, ms=7)
    b.plot(lam[k], ind[k], "o", color=ORANGE, ms=13, mec="white", mew=2, zorder=4)
    b.annotate(f"Best forecaster: {ind[k]:.2f}\nsimulated worms too alike", xy=(lam[k], ind[k]), xytext=(15000, 0.95),
               color=ORANGE, fontweight="bold", fontsize=10.5, bbox={**BOX, "ec": ORANGE},
               arrowprops=dict(arrowstyle="->", color=ORANGE))
    b.set_xscale("log")
    b.set_ylim(0.35, 1.15)
    b.set_xlabel("Pull towards one shared model (lambda)")
    b.set_ylabel("Individuality of simulated worms")
    b.set_title("...and that turns many worms into one average worm")
    fig.text(0.5, -0.03, "27 freely moving worms; one linear model per worm, shrunk towards a shared model. "
             "Individuality 1 = simulated worms differ as much as real ones.", ha="center", color=MUTED, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(out / "fig-average-worm.png", bbox_inches="tight")


def fig_rest_vs_poke(out):
    d = rows("rest_vs_poke.csv")
    by = defaultdict(list)
    for r in d:
        by[r["brain"]].append((float(r["rest_score"]), float(r["poke_pattern"])))

    def group(name):
        if name.startswith("hybrid_kernels") and not any(s in name for s in ("connectome", "shuffled")):
            return "poke"
        if name.startswith("hybrid_kernels"):
            return "wiring"
        return "watch"
    style = {"watch": (NAVY, "o", "Learned by watching or forecasting (VARs, published models)"),
             "wiring": (ORANGE, "s", "Causal links only along a wiring diagram (real or shuffled)"),
             "poke": (GREEN, "D", "Causal links learned from pokes")}
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axhspan(0.89, 0.91, color=BAND, lw=0, zorder=0)
    ax.text(0.0215, 0.8935, "real worm to real worm", color=GREEN, fontsize=10, fontweight="bold", ha="left", va="center")
    seen = set()
    for name, v in by.items():
        g = group(name)
        x, y = np.mean(v, axis=0)
        c, m, lab = style[g]
        ax.plot(x, y, m, color=c, ms=10, mec="white", mew=1.5, label=None if g in seen else lab, zorder=3)
        seen.add(g)
    ax.set_xlabel("How unlike real worms the model is at rest (lower = more realistic)")
    ax.set_ylabel("How unlike real worms its poke responses are\n(pattern distance, lower = more realistic)")
    ax.set_title("Looking real at rest says nothing about answering a poke")
    ax.annotate("The most realistic models at rest\nare wrong about every poke", xy=(0.039, 0.99), xytext=(0.055, 0.955),
                color=NAVY, fontweight="bold", fontsize=10.5, bbox={**BOX, "ec": NAVY},
                arrowprops=dict(arrowstyle="->", color=NAVY))
    ax.legend(loc="lower right", fontsize=9.5)
    ax.set_xlim(0.02, 0.135)
    ax.set_ylim(0.86, 1.012)
    fig.text(0.5, -0.02, "30 models, each averaged over three held-out pools of the worm atlas. "
             "Rank correlation between the two axes: -0.12.", ha="center", color=MUTED, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(out / "fig-rest-vs-poke.png", bbox_inches="tight")


ABL = [("Full model (frozen)", "III ITT OIT IOI OII III III III III"),
       ("without causal links from pokes", "III ITT OII IOI OOI III OOO ITT III"),
       ("without slow brain-wide states", "III III TTT ITT OII III III OOO IOI"),
       ("without interactions between slow states", "III TTT OTT IIT OOI III III III OII"),
       ("without individual variation", "III TTT TTT ITT OII III III III III"),
       ("observed class by class, not neuron by neuron", "III ITT OII IOI OII III III OOO OOO"),
       ("without fast coupling between neuron types", "III ITT OII IOI OII III III III III"),
       ("without shared fast shocks", "III ITT OII III OII III III III III")]
LEVELS = ["activity\nshape", "time-\nscale", "corre-\nlation", "dimen-\nsion", "lead\nand lag", "state\ndwell",
          "poke\npattern", "poke\nsize", "poke\nspread"]


def fig_what_a_copy_needs(out):
    col = {"I": GREEN, "O": RED, "T": ORANGE}
    fig, ax = plt.subplots(figsize=(12, 5.6))
    nr = len(ABL)
    for i, (name, s) in enumerate(ABL):
        y = nr - 1 - i
        for j, trip in enumerate(s.split()):
            for k, ch in enumerate(trip):
                ax.add_patch(Rectangle((j + 0.08 + k * 0.28, y + 0.18), 0.26, 0.64, color=col[ch], lw=0))
        ax.text(-0.15, y + 0.5, name, ha="right", va="center", fontsize=10.5,
                color=INK, fontweight="bold" if i == 0 else "normal")
    ax.plot([6, 6], [-0.1, nr + 1.6], color=INK, lw=1.2)
    ax.text(3, nr + 1.35, "at rest", ha="center", color=INK, fontsize=11.5, fontweight="bold")
    ax.text(7.5, nr + 1.35, "when poked", ha="center", color=INK, fontsize=11.5, fontweight="bold")
    for j, lab in enumerate(LEVELS):
        ax.text(j + 0.5, nr + 0.1, lab, ha="center", va="bottom", fontsize=9.5, color=MUTED)
    ax.set_xlim(-4.3, 9.1)
    ax.set_ylim(-0.3, nr + 1.8)
    ax.axis("off")
    ax.grid(False)
    from matplotlib.patches import Patch
    handles = [Patch(color=col["I"], label="inside the real worm-to-worm range"), Patch(color=col["O"], label="outside"),
               Patch(color=col["T"], label="too typical: closer to every worm than worms are to each other")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=9.5, frameon=False, bbox_to_anchor=(0.5, -0.04))
    fig.suptitle("What a copy of a worm brain needs: remove one ingredient at a time", x=0.06, ha="left",
                 fontsize=14, fontweight="bold", color=INK)
    fig.text(0.5, -0.09, "Three squares per level = three pools of held-out atlas worms (independent split). "
             "Before the neuron-level readout fix; the corrected minimal model passes in 10 of 10 runs.",
             color=MUTED, fontsize=9.5, ha="center")
    fig.savefig(out / "fig-what-a-copy-needs.png", bbox_inches="tight")


def fig_brainlike(out):
    from nematica.brainlike.signatures import LABELS, SIGNATURES
    d = ROOT / "nematica/brainlike/calibration"
    worms = [json.loads((d / f"held-out-real-worms-group-{i}.json").read_text())["result"] for i in (1, 2, 3)]
    nets = [(json.loads((d / f"{f}.json").read_text())["result"], lab, c, m) for f, lab, c, m in (
        ("random-tanh-rnn", "Random tanh RNN", RED, "s"), ("random-gru", "Random GRU", ORANGE, "D"),
        ("lab-network-slow-drives-share-0-4", "Network with fast hidden drives", NAVY, "^"))]
    fig, ax = plt.subplots(figsize=(11, 6))
    n = len(SIGNATURES)
    ax.axvspan(-1, 1, color=BAND, lw=0)
    ax.axvline(0, color=GREEN, lw=1.5)
    ax.text(0, -0.75, "real worms", color=GREEN, ha="center", fontsize=10, fontweight="bold")
    clip = 8

    def X(v):
        return max(-clip, min(clip, v))
    for i, k in enumerate(SIGNATURES):
        y = n - 1 - i
        ax.axhline(y, color=GRID, lw=0.8, zorder=0)
        for j, w in enumerate(worms):
            ax.plot(X(w["signatures"][k]["distance"]), y + 0.12 - j * 0.06, "o", color=GREEN, ms=8, mec="white",
                    mew=1.2, label="Real worm groups the reference never saw" if (i == 0 and j == 0) else None, zorder=3)
        for j, (r, lab, c, m) in enumerate(nets):
            v = r["signatures"][k]["distance"]
            ax.plot(X(v), y - 0.12 - j * 0.06, m, color=c, ms=8, mec="white", mew=1.2,
                    label=lab if i == 0 else None, zorder=3)
    ax.set_yticks(range(n), [LABELS[k] for k in reversed(SIGNATURES)])
    ax.set_xlim(-clip - 0.5, clip + 0.5)
    ax.set_ylim(-0.95, n - 0.6)
    ax.set_xticks([-8, -4, -1, 0, 1, 4, 8], ["-8 or less", "-4", "-1", "0", "+1", "+4", "+8 or more"])
    ax.set_xlabel("Distance from the real-worm median, in units of the real-worm range")
    ax.set_title("A brain-likeness test any system can take", loc="left")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower left", fontsize=9.5, bbox_to_anchor=(0.0, -0.27), ncol=2)
    fig.text(0.5, -0.04, "Scores: real worm groups 7, 6 and 7 of 8 signatures inside; every untrained network 0 of 8.",
             ha="center", color=MUTED, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(out / "fig-brainlike.png", bbox_inches="tight")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    fig_average_worm(out)
    fig_rest_vs_poke(out)
    fig_what_a_copy_needs(out)
    fig_brainlike(out)
    P.fig_repeat_recovery(out)
    P.fig_silent_link(out)
    print(sorted(p.name for p in out.glob("*.png")))
