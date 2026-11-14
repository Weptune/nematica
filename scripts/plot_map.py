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


LABEL = {"A1": "Random RNN", "A1-slow": "Random RNN + slow drives", "A2": "Task-trained RNN", "A3": "GRU (characters)",
         "A4": "Spiking network", "A5": "CfC 'liquid' (characters)", "A6-14m": "Pythia 14M", "A6-160m": "Pythia 160M",
         "A6-410m": "Pythia 410M", "A6-1b": "Pythia 1B", "A6-410m-ou": "Pythia 410M + slow latent",
         "A7-130m": "Mamba 130M", "A7-370m": "Mamba 370M", "A10": "Lab network (tuned on worms)"}


def worm():
    d = json.loads((ROOT / "docs/figures/map_worm.json").read_text())["primary"]
    ais = d["ais"]
    order = sorted(ais, key=lambda k: ais[k]["median_crop_distance"])
    fig, ax = plt.subplots(figsize=(11, 0.42 * len(order) + 2.6))
    env, (elo, ehi) = d["envelope"], d["envelope_ci90"]
    top = len(order) + 0.6
    ax.axvspan(0, env, color="#1d1840", zorder=0)
    ax.axvspan(elo, ehi, color="#2a2350", zorder=0)
    ax.axvline(env, color=MUTED, lw=1, zorder=1)
    ax.text(env, top + 0.15, "worm envelope", ha="center", va="bottom", fontsize=9, color=MUTED)
    for v in d["worm_loo"].values():                    # each worm, to the other 13
        ax.plot([v, v], [top - 0.35, top + 0.05], color=INK, lw=1.4)
    ax.text(-0.05, top - 0.15, "14 real worms", ha="right", va="center", fontsize=10, color=INK)
    col = lambda a: CAT["amber"] if a["fitted_on_worms"] else (CAT["pink"] if a["role"] == "augmented" else CAT["blue"])
    for i, k in enumerate(order):
        a = ais[k]
        y = len(order) - 1 - i
        lo, hi = a["ci90"]
        ax.plot([lo, hi], [y, y], color=col(a), lw=2, solid_capstyle="round", alpha=0.8)
        ax.scatter([a["median_crop_distance"]], [y], s=70, color=col(a), zorder=3, edgecolor=BG, linewidth=1.5)
        ax.text(-0.05, y, LABEL.get(k, k), ha="right", va="center", fontsize=10, color=INK)
    xmax = max(max(ais[k]["ci90"][1] for k in order), ehi) * 1.08
    ax.set_xlim(0, min(xmax, 10.5))
    ax.set_ylim(-0.8, top + 0.9)
    ax.set_yticks([])
    for s_ in ("top", "right", "left"):
        ax.spines[s_].set_visible(False)
    ax.set_xlabel("distance from the average worm, in units of how much real worms differ (BVU)", fontsize=9.5)
    fig.text(0.02, 1.02, "Which artificial networks look like a worm, when recorded like one?", fontsize=17,
             family="Newsreader 16pt", color=INK)
    fig.text(0.02, 0.985, f"Each network recorded through the worm's calcium instrument and cut into worm-length pieces; "
             f"measured on {len(d['measures'])} calibrated measurements. Dot: median piece; bar: 90% interval.",
             fontsize=9.3, color=MUTED)
    fig.text(0.02, -0.03, "Blue: standard networks. Pink: with added slow state. Amber: tuned on worm data. "
             "Shaded: inside the largest distance of any real worm from the other 13 (band: its 90% interval). "
             "Descriptive, one species (docs/MAP.md, amendments 12 and 13).", fontsize=7.8, color="#6a5f9a")
    save(fig, "worm_distance")


def worm_measures():
    d = json.loads((ROOT / "docs/figures/map_worm.json").read_text())["primary"]
    use = d["measures"]
    W = d["positions"]["worms"]
    C = d["positions"]["ai_crops"]
    ais = d["ais"]
    fig, axes = plt.subplots(1, len(use), figsize=(3.0 * len(use), 7.5), sharey=True)
    order = sorted(ais, key=lambda k: ais[k]["median_crop_distance"])
    col = lambda a: CAT["amber"] if a["fitted_on_worms"] else (CAT["pink"] if a["role"] == "augmented" else CAT["blue"])
    for ax, m in zip(np.atleast_1d(axes), use):
        wv = [w[m] for w in W.values()]
        ax.axvspan(min(wv), max(wv), color="#1d1840")
        ax.scatter(wv, [len(order) + 0.8] * len(wv), s=22, color=INK, zorder=3)
        for i, k in enumerate(order):
            y = len(order) - 1 - i
            v = [c[m] for c in C[k]]
            ax.scatter(v, [y] * len(v), s=6, color=col(ais[k]), alpha=0.35, linewidth=0)
            ax.scatter([np.median(v)], [y], s=40, color=col(ais[k]), zorder=3, edgecolor=BG, linewidth=1)
        ax.set_title(NAMES[m], fontsize=10.5, color=INK, pad=8)
        for s_ in ("top", "right", "left"):
            ax.spines[s_].set_visible(False)
        ax.tick_params(axis="x", labelsize=8)
    ax0 = np.atleast_1d(axes)[0]
    ax0.set_yticks(list(range(len(order))) + [len(order) + 0.8])
    ax0.set_yticklabels([LABEL.get(k, k) for k in order[::-1]] + ["real worms"], fontsize=9.5, color=INK)
    ax0.tick_params(axis="y", length=0)
    fig.text(0.01, 1.03, "Where the networks differ from worms, measurement by measurement", fontsize=17,
             family="Newsreader 16pt", color=INK)
    fig.text(0.01, 0.995, "Shaded: the range of the 14 real worms. Small dots: worm-length pieces of each network; "
             "large dot: their median.", fontsize=9.3, color=MUTED)
    save(fig, "worm_measures")


LABEL = {"A1": "Random RNN", "A1-slow": "Random RNN + slow drives", "A2": "Task-trained RNN", "A3": "GRU (characters)",
         "A4": "Spiking network", "A5": "CfC (characters)", "A6-14m": "Pythia 14M", "A6-160m": "Pythia 160M",
         "A6-410m": "Pythia 410M", "A6-410m-ou": "Pythia 410M + slow latent", "A6-1b": "Pythia 1B",
         "A7-130m": "Mamba 130M", "A7-370m": "Mamba 370M", "A10": "Lab network (fitted to worms)"}


def species():
    """Where every AI sits relative to the real individuals, per measurement, in the worms (discovery) and
    the pooled mouse (confirmation), from map_species.json. Filled marker: counted for that measurement;
    hollow: outside calibrated speed (temporal measures) or augmented."""
    d = json.loads((ROOT / "docs/figures/map_species.json").read_text())
    panels = [("Worms, calcium imaging (14 worms, discovery)", d["discovery_worm"]),
              ("Mice, Neuropixels, units pooled in 8s (3 mice)", d["confirmatory_mouse"])]
    order = [a for a in LABEL if any(a in S["measures"][m]["ai"] for _, S in panels for m in S["measures"])]
    ms = ["shared_fraction", "slow_fraction", "timescale_spread", "coupling_spread"]
    fig, axes = plt.subplots(2, len(ms), figsize=(15, 11), gridspec_kw={"hspace": 0.32, "wspace": 0.08})
    for r, (title, S) in enumerate(panels):
        for c, m in enumerate(ms):
            ax = axes[r, c]
            ax.set_yticks(range(len(order) + 1))
            ax.set_yticklabels(["Real individuals"] + [LABEL[a] for a in order] if c == 0 else [], fontsize=9)
            ax.invert_yaxis()
            ax.tick_params(length=0)
            for sp in ("top", "right", "left"):
                ax.spines[sp].set_visible(False)
            row = S["measures"].get(m)
            if row is None:
                ax.text(0.5, 0.5, "not calibrated here", transform=ax.transAxes, ha="center", color=MUTED, fontsize=9)
                ax.set_xticks([])
                continue
            lo, hi = row["envelope"]
            ax.axvspan(lo, hi, color=CAT["pink"], alpha=0.13, lw=0)
            ax.scatter(row["real"], [0] * len(row["real"]), s=36, color=CAT["pink"], zorder=3)
            for i, a in enumerate(order, start=1):
                y = row["ai"].get(a)
                if not y or not np.isfinite(y["value"]):
                    continue
                col = CAT["blue"] if y["role"] == "standard" else CAT["amber"]
                ax.plot(y["ci90"], [i, i], color=col, lw=1.6, alpha=0.7)
                ax.scatter([y["value"]], [i], s=40, zorder=3, color=col if y["counted"] else BG, edgecolors=col, lw=1.4)
            gate = ("" if row["usable"] else "  (fails a gate)" if row.get("calibrated", True)
                    else "  (not calibrated)")
            ax.set_title(NAMES[m] + gate, fontsize=11, color=INK if row["usable"] else MUTED, loc="left")
            ax.grid(axis="x", color=FAINT, lw=0.6)
            ax.set_axisbelow(True)
        axes[r, 0].annotate(title, xy=(0, 1.1), xycoords="axes fraction", fontsize=13, color=INK,
                            fontfamily="Newsreader 16pt")
    save(fig, "species")


def allen():
    """Test B in the Allen mice: slow memory of every usable mouse against the random RNN, the slow-drive RNN,
    and the random RNN recorded at five single mice's instruments (the transfer check)."""
    d = json.loads((ROOT / "docs/figures/map_species.json").read_text())["confirmatory_allen"]
    row = d["mice"]["measures"]["slow_fraction"]
    tr = d["transfer"]["values"]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    v = np.sort(np.array(row["real"]))
    ax.scatter(v, np.zeros_like(v) + np.random.default_rng(0).uniform(-0.12, 0.12, len(v)), s=26, color=CAT["pink"],
               zorder=3, label=f"{len(v)} Allen mice")
    lo, hi = row["envelope"]
    ax.axvspan(lo, hi, color=CAT["pink"], alpha=0.10, lw=0)
    for i, (a, lab, col) in enumerate([("A1", "Random RNN (median instrument)", CAT["blue"]),
                                       ("A1-slow", "Random RNN + slow drives", CAT["amber"])], start=1):
        y = row["ai"][a]
        ax.plot(y["ci90"], [i, i], color=col, lw=2)
        ax.scatter([y["value"]], [i], s=60, color=col, zorder=3)
        ax.text(y["ci90"][1] + 0.006, i, lab, va="center", fontsize=10, color=INK)
    xs = [x for k, x in tr.items() if k != "median instrument"]
    ax.scatter(xs, [3] * len(xs), s=40, facecolors=BG, edgecolors=CAT["blue"], lw=1.5, zorder=3)
    ax.text(max(xs) + 0.006, 3, "Random RNN at five single mice's instruments", va="center", fontsize=10, color=INK)
    ax.set_yticks([])
    ax.set_ylim(-0.6, 3.6)
    ax.invert_yaxis()
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.set_xlabel("Slow memory", fontsize=11)
    ax.grid(axis="x", color=FAINT, lw=0.6)
    ax.set_axisbelow(True)
    ax.set_title("Test B in 35 Allen mice: the random RNN sits inside the mouse range, and the instrument moves it more "
                 "than mice differ", fontsize=11.5, loc="left", color=INK, fontfamily="Newsreader 16pt")
    save(fig, "allen")


if __name__ == "__main__":
    fonts()
    for name in sys.argv[1:] or ["instrument"]:
        globals()[name]()
