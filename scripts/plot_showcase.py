"""Showcase figures (8 Nov 2026) for the post and the paper, drawn only from committed result tables.

  fig-rest-vs-poke.png     rest realism against poke realism, one point per model (mean over pools)
  fig-fingerprints.png     each worm's echoes: distance to its own other half against other worms'
  fig-classifier.png       can a classifier tell model windows from real ones, by model memory

Usage:  python scripts/plot_showcase.py OUTDIR
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plot_post_figures as P  # noqa: E402  (shared style and palette)

plt = P.plt
FIG = ROOT / "docs" / "figures"
GREY = "#94a3b8"


def family(b):
    if b.startswith("creamer"):
        return "published"
    if b.startswith("hybrid"):
        return "hybrid"
    return "var"


def fig_rest_vs_poke(out):
    rows = list(csv.DictReader(open(FIG / "rest_vs_poke.csv")))
    d = defaultdict(list)
    for r in rows:
        d[r["brain"]].append((float(r["rest_score"]), float(r["poke_pattern"])))
    names = sorted(d)
    x = np.array([np.mean([v[0] for v in d[k]]) for k in names])
    y = np.array([np.mean([v[1] for v in d[k]]) for k in names])
    rho, p = spearmanr(x, y)
    fig, ax = plt.subplots(figsize=(9, 5.6))
    ax.axhspan(0.89, 0.91, color=P.GREEN, alpha=0.12, lw=0, zorder=0)
    ax.text(0.129, 0.893, "Real worm against real worm", color=P.GREEN, fontsize=10, ha="right", va="bottom")
    style = {"var": (GREY, "Linear models (VAR), fitted to rest or to all frames"),
             "published": (P.ORANGE, "Published atlas models (Creamer et al.)"),
             "hybrid": (P.NAVY, "Hybrids with causal links learned from pokes")}
    for fam, (col, lab) in style.items():
        sel = [i for i, k in enumerate(names) if family(k) == fam]
        ax.scatter(x[sel], y[sel], s=70, color=col, edgecolor="white", linewidth=1.5, zorder=3, label=lab)
    i = names.index("var3_spontaneous")
    ax.annotate("Fitted to rest: looks like a worm,\nanswers pokes almost at random", (x[i], y[i]), xytext=(0.045, 0.95),
                fontsize=10, color=P.INK, arrowprops=dict(arrowstyle="-", color=P.MUTED, lw=1))
    j = names.index("hybrid_kernels_regimes_obsfit")
    ax.annotate("Passes the poke test", (x[j], y[j]), xytext=(0.105, 0.925), fontsize=10, color=P.INK,
                arrowprops=dict(arrowstyle="-", color=P.MUTED, lw=1))
    ax.set_xlim(0.02, 0.135)
    ax.set_ylim(0.885, 1.005)
    ax.set_xlabel("At rest: distance from real worms (0 = as close as another real worm)")
    ax.set_ylabel("Under pokes: pattern distance (lower is better)")
    ax.set_title("How real a model looks at rest says nothing about how it answers a poke", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=9, framealpha=1, ncol=1)
    ax.text(0, -0.36, f"30 models, each averaged over 3 held-out pools of the worm atlas; Spearman rho = {rho:+.2f} (p = {p:.2f})",
            transform=ax.transAxes, color=P.MUTED, fontsize=9)
    fig.savefig(out / "fig-rest-vs-poke.png", bbox_inches="tight")
    return rho, p


def fig_fingerprints(out):
    rows = [r for r in csv.DictReader(open(FIG / "own_rest_fingerprint_fluct.csv")) if r["fp_within"] and r["fp_between"]]
    w = np.array([float(r["fp_within"]) for r in rows])
    b = np.array([float(r["fp_between"]) for r in rows])
    ok = np.isfinite(w) & np.isfinite(b)
    w, b = w[ok], b[ok]
    own = b > w
    fig, ax = plt.subplots(figsize=(6.6, 6.2))
    lo, hi = 0.45, 1.05
    ax.plot([lo, hi], [lo, hi], color=P.MUTED, ls="--", lw=1.2, zorder=1)
    ax.scatter(w[own], b[own], s=60, color=P.NAVY, edgecolor="white", linewidth=1.3, zorder=3,
               label=f"Closer to itself: {own.sum()} of {len(w)} worms")
    ax.scatter(w[~own], b[~own], s=60, color=GREY, edgecolor="white", linewidth=1.3, zorder=3,
               label=f"Closer to other worms: {(~own).sum()}")
    ax.text(0.47, 0.82, "Above the line: a worm's echoes\nresemble its own more than others'", fontsize=10, color=P.INK, va="top")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_xlabel("Distance to the same worm's other half of pokes")
    ax.set_ylabel("Distance to other worms' pokes")
    ax.set_title("Each worm answers pokes in its own way", loc="left")
    ax.legend(loc="lower right", fontsize=9, framealpha=1)
    ax.text(0, -0.17, "Worm atlas: each worm's pokes split into odd and even events; pattern distance of echoes; p = 5e-6",
            transform=ax.transAxes, color=P.MUTED, fontsize=9)
    fig.savefig(out / "fig-fingerprints.png", bbox_inches="tight")


def fig_classifier(out):
    rows = list(csv.DictReader(open(FIG / "l8_fair_lags.csv")))
    models = [("hyst", "1.5 s of memory"), ("hyst6", "3 s"), ("hyst10", "6 s")]
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ctrl = np.mean([float(r["auc"]) for r in rows if r["model"] == "real"])
    ax.axhline(0.5, color=P.MUTED, ls="--", lw=1.2, label="Chance: cannot tell them apart", zorder=4)
    for k, (m, lab) in enumerate(models):
        for off, comp, col, name in ((-0.17, "held_out", P.NAVY, "against held-out real worms"),
                                      (0.17, "in_sample", "#7d93d6", "against the worms it imitates")):
            v = [float(r["auc"]) for r in rows if r["model"] == m and r["comparison"] == comp]
            ax.bar(k + off, np.mean(v), width=0.3, color=col, label=name if k == 0 else None, zorder=2)
            ax.scatter([k + off] * len(v), v, s=14, color=P.INK, zorder=3)
            ax.text(k + off, 0.05, f"{np.mean(v):.2f}", ha="center", fontsize=11, color="white", fontweight="bold", zorder=5)
    ax.set_xticks(range(3), [lab for _, lab in models])
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Classifier AUC (1 = always spots the model)")
    ax.set_xlabel("Model's memory of its own past activity")
    ax.set_title("With 6 s of memory, a classifier can no longer spot the model", loc="left")
    ax.legend(loc="upper right", fontsize=9, framealpha=1)
    ax.set_ylim(0, 1.05)
    ax.grid(axis="x", visible=False)
    ax.text(0, -0.2, f"30 s windows of 27 freely moving worms; bars = mean of 3 pools (dots); real worm vs real worm control {ctrl:.2f}",
            transform=ax.transAxes, color=P.MUTED, fontsize=9)
    fig.savefig(out / "fig-classifier.png", bbox_inches="tight")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    print(fig_rest_vs_poke(out))
    fig_fingerprints(out)
    fig_classifier(out)
