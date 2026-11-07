"""Figures for the website write-up (7 Nov 2026), drawn from the project's own result files.

Palette (validated for colour-blind separation, in this order): orange, navy, red, green.
Roles are fixed across figures: bound = navy dashed, best watcher = green, VAR watcher = red.

Usage:  python scripts/plot_post_figures.py OUTDIR
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica import limits as L  # noqa: E402

ORANGE, NAVY, RED, GREEN = "#d97706", "#2a4fb8", "#dc2626", "#059669"
INK, MUTED, GRID = "#0f172a", "#475569", "#e2e8f0"

plt.rcParams.update({
    "font.size": 11, "axes.titlesize": 14, "axes.titleweight": "bold", "axes.titlecolor": INK,
    "axes.labelcolor": INK, "axes.edgecolor": "#94a3b8", "axes.spines.top": False,
    "axes.spines.right": False, "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "legend.frameon": True, "legend.edgecolor": GRID,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.dpi": 200,
})
BOX = dict(boxstyle="round,pad=0.4", fc="white", lw=1.2)


def rows(path):
    return list(csv.DictReader(open(path)))


def fig_two_regimes(out):
    d = rows(ROOT / "docs/figures/limit_lab.csv")
    sel = {"unit": lambda r: r["kind"] == "unit",
           "drive": lambda r: r["kind"] == "drive" and r["load"] == "2.0" and r["drho"] == "0.98"}
    titles = {"unit": "Hidden neurons wired both ways: the model was wrong",
              "drive": "Strong slow hidden drives: the data runs out"}
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
    for ax, key in zip(axes, ("unit", "drive")):
        rr = [r for r in d if sel[key](r)]
        Ts = sorted({int(r["T"]) for r in rr})
        for col, colr, ls, name in (("bound", NAVY, "--", "Limit for any unbiased watcher"),
                                     ("best", GREEN, "-", "Best watcher (right model)"),
                                     ("var", RED, "-.", "VAR watcher (used for the worm headline)")):
            med = [np.median([float(r[col]) for r in rr if int(r["T"]) == T]) for T in Ts]
            lo = [min(float(r[col]) for r in rr if int(r["T"]) == T) for T in Ts]
            hi = [max(float(r[col]) for r in rr if int(r["T"]) == T) for T in Ts]
            off = {"bound": 0.97, "best": 1.0, "var": 1.03}[col]
            xs = [T * off for T in Ts]
            ax.plot(xs, med, ls, color=colr, lw=2.2, marker="o", ms=7, label=name, zorder=3)
            ax.errorbar(xs, med, yerr=[np.subtract(med, lo), np.subtract(hi, med)], fmt="none",
                        ecolor=colr, elinewidth=1.2, capsize=3, alpha=0.7, zorder=2)
        ax.set_xscale("log")
        ax.set_xticks(Ts)
        ax.set_xticklabels([f"{T:,}" for T in Ts])
        ax.set_xlabel("Rest recording length (frames)")
        ax.set_title(titles[key], fontsize=12.5)
        ax.set_ylim(-0.3, 1.05)
    axes[0].set_ylabel("Agreement with the true poke responses")
    axes[0].annotate("VAR stuck near 0.6\nhowever long you record", xy=(16000, 0.60), xytext=(1500, 0.25),
                     color=RED, fontweight="bold", fontsize=10.5, bbox={**BOX, "ec": RED},
                     arrowprops=dict(arrowstyle="->", color=RED))
    axes[1].annotate("Even the limit is low:\nrest data barely constrains\nthe answer", xy=(3880, 0.355), xytext=(1100, 0.88),
                     color=NAVY, fontweight="bold", fontsize=10.5, bbox={**BOX, "ec": NAVY},
                     arrowprops=dict(arrowstyle="->", color=NAVY))
    axes[1].legend(loc="lower right", fontsize=9.5)
    fig.text(0.5, -0.02, "Medians over 3 networks; whiskers: range. Linear lab networks, 10 seen units, 2 hidden.",
             ha="center", color=MUTED, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(out / "fig-two-regimes.png", bbox_inches="tight")


def fig_transformer(out):
    d = rows(ROOT / "docs/figures/limit_tlab.csv")
    fig, ax = plt.subplots(figsize=(9, 5))
    for cond, colr, ls, name in (("untrained", NAVY, "-", "Untrained transformers"), ("trained", ORANGE, "--", "Trained transformers")):
        for i in range(3):
            rr = sorted((int(r["contexts"]), float(r["watch_offdiag"])) for r in d
                        if r["condition"] == cond and r["individual"] == str(i))
            ax.plot([a for a, _ in rr], [b for _, b in rr], ls, color=colr, lw=2, marker="o", ms=6,
                    label=name if i == 0 else None)
    ax.set_xscale("log")
    ax.set_xticks([6, 12, 24, 48, 96])
    ax.set_xticklabels(["6", "12", "24", "48", "96"])
    ax.set_xlabel("Contexts watched (300 tokens each)")
    ax.set_ylabel("Watching vs true cause and effect\n(correlation, off-diagonal)")
    ax.set_ylim(0, 0.3)
    ax.set_title("More watching does not help a transformer")
    ax.annotate("Gain from 24 to 96 contexts:\n-0.010 to +0.014 in all six networks", xy=(48, 0.145), xytext=(7, 0.04),
                color=INK, fontweight="bold", fontsize=10, bbox={**BOX, "ec": "#94a3b8"},
                arrowprops=dict(arrowstyle="->", color=MUTED))
    ax.legend(loc="upper right", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "fig-transformer-plateau.png", bbox_inches="tight")


def fig_silent_link(out):
    thetas = [0, 1, 2, 3, 4, 5, 6]
    res = [L.silent_link_demo(th, 4000, reps=80, seed=10 + i) for i, th in enumerate(thetas)]
    act = np.array([r["active"] for r in res])
    emp = np.array([r["emp_sd"] for r in res])
    pred = np.array([r["pred_sd"] for r in res])
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axvspan(0.003, 0.014, color=ORANGE, alpha=0.12, lw=0)
    ax.text(0.0065, 2.0, "silent links in\nour lab brains", color=ORANGE, ha="center", fontsize=10, fontweight="bold")
    ax.plot(act, pred, "--", color=NAVY, lw=2, marker="s", ms=6, label="Theory (Fisher information)")
    ax.plot(act, emp, "-", color=GREEN, lw=2.2, marker="o", ms=7, label="Best watcher, simulated")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Fraction of rest frames on which the link fires")
    ax.set_ylabel("Error in the link's estimated weight\n(true weight 1, 4,000 frames)")
    ax.set_title("A link that rarely fires at rest is nearly invisible to watching")
    ax.annotate("fires on 0.5% of frames: error as big as the weight.\nNever fires: no estimate at all, at any length",
                xy=(act.min(), emp[-1]), xytext=(0.03, 0.9),
                color=RED, fontweight="bold", fontsize=10, bbox={**BOX, "ec": RED},
                arrowprops=dict(arrowstyle="->", color=RED))
    ax.set_ylim(0.01, 3)
    ax.legend(loc="lower left", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "fig-silent-link.png", bbox_inches="tight")


def fig_decomposition(out):
    d = rows(ROOT / "docs/figures/latent_watch.csv")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.axvspan(0.8, 1.0, ymin=0, ymax=1, color=RED, alpha=0.05, lw=0)
    ax.axvspan(0.0, 0.5, color=NAVY, alpha=0.05, lw=0)
    ax.text(0.9, 1.33, "data enough (0.8 and up)", ha="center", color=MUTED, fontsize=10)
    ax.text(0.25, 1.33, "data too short (below 0.5)", ha="center", color=MUTED, fontsize=10)
    ax.axhline(0.25, color="#94a3b8", lw=1, ls=":")
    ax.text(0.99, 0.12, "worm decision line (pre-registered):\nwatching failed if at most 0.25", color=MUTED, fontsize=9.5, ha="right")
    style = {"worms": (ORANGE, "o"), "ladder:G": (RED, "s"), "ladder:D": (NAVY, "D"),
             "ladder:DG": (GREEN, "^"), "ladder:base": (MUTED, "v")}
    for r in d:
        c, m = style[r["data"]]
        ax.errorbar(float(r["data_limited_agreement"]), float(r["share"]), xerr=float(r["data_limited_sd"]),
                    fmt=m, color=c, ms=10, mec="white", mew=1.5, elinewidth=1.4, capsize=3)
    pts = {k: [(float(r["data_limited_agreement"]), float(r["share"])) for r in d if r["data"] == k] for k in style}
    lab = {"worms": "Worms, one point per held-out pool:\nabout as much data as the drives brain,\nyet watching predicts nothing",
           "ladder:G": "Lab brain with silent links:\ndata enough, watching weak\n(structural, as built)",
           "ladder:D": "Lab brain with hidden drives:\nwatching works\n(noisy: its individuals barely agree)",
           "ladder:DG": "Lab brain, drives + silent links", "ladder:base": "Plain lab brain"}
    where = {"worms": (0.12, 0.30), "ladder:G": (0.52, 0.62), "ladder:D": (0.12, 1.02),
             "ladder:DG": (0.3, 0.9), "ladder:base": (0.3, 0.75)}
    for k, pp in pts.items():
        if not pp:
            continue
        x, y = np.mean(pp, axis=0)
        ax.annotate(lab[k], xy=(x, y), xytext=where[k], color=style[k][0], fontweight="bold", fontsize=10,
                    bbox={**BOX, "ec": style[k][0]}, arrowprops=dict(arrowstyle="->", color=style[k][0]))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.2, 1.42)
    ax.set_xlabel("Data check: could the best watcher recover its own model from data like this?")
    ax.set_ylabel("Best watcher's poke predictions\n(share of individual-to-individual agreement)")
    ax.set_title("Same data sufficiency, opposite outcomes")
    fig.tight_layout()
    fig.savefig(out / "fig-decomposition.png", bbox_inches="tight")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    fig_two_regimes(out)
    fig_transformer(out)
    fig_decomposition(out)
    fig_silent_link(out)
    print("done")
