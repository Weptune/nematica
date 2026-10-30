"""Figure for arc 1: forecasting skill vs fidelity, and what per-worm dynamics change.

Usage:  python scripts/plot_arc1.py --results results [--out results/arc1/arc1.png]
Reads arc1_summary.csv / arc1_levels.csv from every results/arc1* folder (later folders
override earlier ones for the same system).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

INK, INK2, SURFACE, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]       # validated categorical order
MARKERS = ["o", "s", "^", "D"]
LABEL = {"diag_ar1": "AR(1) per neuron", "diag_ar4": "AR(4) per neuron", "var1": "VAR(1) shared",
         "var3": "VAR(3) shared", "esn400": "Reservoir 400", "esn1500": "Reservoir 1500",
         "indiv_var1": "VAR(1) per worm", "indiv_var3": "VAR(3) per worm",
         "indivnoise_var3": "own noise only", "indivshuf_var3": "scrambled deviations"}


def load(results: Path):
    summ, levels = {}, {}
    for d in sorted(results.glob("arc1*")):
        for r in csv.DictReader((d / "arc1_summary.csv").open()) if (d / "arc1_summary.csv").exists() else []:
            summ[r["system"]] = r
        for r in csv.DictReader((d / "arc1_levels.csv").open()) if (d / "arc1_levels.csv").exists() else []:
            levels[(r["system"], r["metric"])] = r
    return summ, levels


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="results/arc1/arc1.png")
    args = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    summ, levels = load(Path(args.results))
    metrics = list(dict.fromkeys(m for (_, m) in levels))
    fig, (a, b) = plt.subplots(1, 2, figsize=(13.5, 5.2), gridspec_kw={"width_ratios": [1.45, 1]})
    fig.patch.set_facecolor(SURFACE)
    for ax in (a, b):
        ax.set_facecolor(SURFACE)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=9)
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)

    # ---- A: per-level distance ratio, VAR(3) variants
    variants = ["var3", "indivnoise_var3", "indivshuf_var3", "indiv_var3"]
    x = np.arange(len(metrics))
    real = [levels.get(("real_other_worms", m)) for m in metrics]
    rr = [float(r["system_median"]) / float(r["bio_median"]) if r else np.nan for r in real]
    a.scatter(x, rr, marker="_", s=420, color=INK2, lw=2, zorder=2, label="other real worms")
    a.axhline(1.0, color=INK2, lw=1, ls=(0, (4, 3)), zorder=1)
    for i, v in enumerate(variants):
        ys, edge = [], []
        for m in metrics:
            r = levels.get((v, m))
            ok = r and r["verdict"] != "not scored"
            ys.append(float(r["system_median"]) / float(r["bio_median"]) if ok else np.nan)
            edge.append(r["verdict"] if ok else "")
        off = (i - 1.5) * 0.15
        a.scatter(x + off, ys, s=46, marker=MARKERS[i], color=SERIES[i], edgecolor=SURFACE, lw=1.2,
                  zorder=3, label=LABEL[v])
    a.set_yscale("log")
    from matplotlib.ticker import NullFormatter, NullLocator
    a.yaxis.set_minor_locator(NullLocator())
    a.yaxis.set_minor_formatter(NullFormatter())
    a.set_yticks([0.5, 0.7, 1, 1.5, 2, 3, 5])
    a.set_yticklabels(["0.5", "0.7", "1", "1.5", "2", "3", "5"])
    a.set_xticks(x)
    a.set_xticklabels([m.replace(".", "\n") for m in metrics], fontsize=8.5, color=INK2)
    a.set_ylabel("distance to real worms / real worm-to-worm distance", color=INK2, fontsize=9)
    a.text(len(metrics) - 0.5, 1.03, "as real as another worm", ha="right", va="bottom", fontsize=8, color=INK2)
    a.set_title("A  Per-worm dynamics land on 1 where shared models are too typical", loc="left",
                fontsize=10.5, color=INK)
    a.legend(loc="upper center", ncol=3, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.17), labelcolor=INK2)

    # ---- B: forecasting skill vs individuality
    ladder = ["diag_ar1", "diag_ar4", "var1", "var3", "esn400", "esn1500"]
    indiv = ["indiv_var1", "indiv_var3"]
    b.axhline(1.0, color=INK2, lw=1, ls=(0, (4, 3)))
    b.text(0.443, 1.02, "real worms", fontsize=8, color=INK2, va="bottom")
    nudge = {"esn1500": (-8, 8), "esn400": (6, -12), "var1": (6, -12), "var3": (6, 4)}
    for group, col, mk, name in [(ladder, SERIES[0], "o", "shared across worms"),
                                 (indiv, SERIES[3], "D", "one model per worm")]:
        pts = [(float(summ[s]["r2_5step"]), float(summ[s]["individuality"]), s) for s in group if s in summ]
        b.scatter([p[0] for p in pts], [p[1] for p in pts], s=60, marker=mk, color=col, edgecolor=SURFACE,
                  lw=1.2, zorder=3, label=name)
        for px, py, s in pts:
            dx, dy = nudge.get(s, (6, 4))
            b.annotate(LABEL[s], (px, py), xytext=(dx, dy), textcoords="offset points", fontsize=7.5,
                       color=INK2, ha="right" if dx < 0 else "left")
    b.set_xlabel("forecasting skill on test worms (R², 3 s ahead)", color=INK2, fontsize=9)
    b.set_ylabel("individuality (spread between samples / real spread)", color=INK2, fontsize=9)
    b.set_ylim(0, 1.6)
    b.set_xlim(0.43, 0.58)
    b.set_title("B  Forecasting skill does not predict individuality", loc="left", fontsize=10.5, color=INK)
    b.legend(loc="upper center", ncol=2, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.17), labelcolor=INK2)

    fig.tight_layout()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=170, facecolor=SURFACE)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
