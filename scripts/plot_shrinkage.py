"""Figure for the shrinkage sweep: forecasting skill and realism along one knob.

Usage:  python scripts/plot_shrinkage.py [--csv results/shrinkage/shrinkage.csv] [--out results/shrinkage/shrinkage.png]
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

INK, INK2, SURFACE, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
MARKERS = ["o", "s", "^", "D"]
KEY = [("L2.correlation", "correlations"), ("L4.leadlag", "lead-lag"),
       ("L5.encoding", "velocity encoding"), ("L5.reversal", "reversal encoding")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="results/shrinkage/shrinkage.csv")
    ap.add_argument("--out", default="results/shrinkage/shrinkage.png")
    args = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter, NullLocator

    rows = list(csv.DictReader(open(args.csv)))
    lam = [float(r["lam"]) for r in rows]
    r2 = [float(r["within_worm_r2"]) for r in rows]
    best_f = lam[max(range(len(rows)), key=lambda i: r2[i])]

    fig, (a, b) = plt.subplots(2, 1, figsize=(8.2, 7.2), sharex=True, gridspec_kw={"height_ratios": [1, 1.6]})
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
        ax.axvline(best_f, color=INK2, lw=1, ls=(0, (2, 2)))

    a.plot(lam, r2, color=SERIES[0], lw=2, marker="o", ms=7, mec=SURFACE, mew=1.2)
    a.set_ylabel("forecasting skill\n(within-worm R²)", color=INK2, fontsize=9)
    a.text(best_f * 1.08, min(r2) + 0.002, "best forecast", color=INK2, fontsize=8)
    a.set_title("Shrinking each worm toward the shared model: forecasting vs realism", loc="left",
                fontsize=11, color=INK)

    b.axhline(1.0, color=INK2, lw=1, ls=(0, (4, 3)))
    b.text(lam[-1], 1.006, "as real as another worm", color=INK2, fontsize=8, va="bottom", ha="right")
    for i, (m, label) in enumerate(KEY):
        ys = [float(r[f"{m}_ratio"]) for r in rows]
        off = [1.0 + 0.05 * (i - 1.5)] * len(lam)
        lam_i = [l * o for l, o in zip(lam, off)]
        inside = [r[f"{m}_verdict"] == "inside" for r in rows]
        b.plot(lam_i, ys, color=SERIES[i], lw=2, zorder=2)
        b.scatter([l for l, ok in zip(lam_i, inside) if ok], [y for y, ok in zip(ys, inside) if ok],
                  marker=MARKERS[i], s=46, color=SERIES[i], edgecolor=SURFACE, lw=1.2, zorder=3, label=label)
        b.scatter([l for l, ok in zip(lam_i, inside) if not ok], [y for y, ok in zip(ys, inside) if not ok],
                  marker=MARKERS[i], s=46, facecolor=SURFACE, edgecolor=SERIES[i], lw=1.5, zorder=3)
    b.set_ylabel("distance to real worms / worm-to-worm distance\n(open marker = too typical)",
                 color=INK2, fontsize=9)
    b.set_xscale("log")
    b.xaxis.set_minor_locator(NullLocator())
    b.xaxis.set_minor_formatter(NullFormatter())
    b.set_xticks(lam)
    b.set_xticklabels([f"{int(l):,}" for l in lam])
    b.set_xlabel("shrinkage toward the shared model (λ)  → more average", color=INK2, fontsize=9)
    b.legend(loc="lower left", fontsize=8, frameon=False, labelcolor=INK2, ncol=2)
    fig.tight_layout()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=170, facecolor=SURFACE)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
