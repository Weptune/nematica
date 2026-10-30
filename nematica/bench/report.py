"""The fidelity-profile figure, shared by run_benchmark.py and plot_profile.py.

Rows come either straight from score_system() or from fidelity_<dataset>.csv (strings).
An optional Level 8 table (l8_<dataset>.csv rows) adds a discriminability column showing the
classifier AUC; green = indistinguishable from real held-out worms, red = distinguishable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

COLOURS = {"inside": "#2e8b57", "outside": "#c0504d", "too typical": "#d9a441",
           "not scored": "#9aa3a8", "indistinguishable": "#2e8b57", "distinguishable": "#c0504d"}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _truthy(v) -> bool:
    return v is True or str(v).lower() == "true"


def plot_profile(rows: Sequence[dict], metrics: Sequence[str], systems: Sequence[str], path: Path,
                 l8: Sequence[dict] | None = None, subtitle: str = "") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    l8 = {r["system"]: r for r in (l8 or []) if not r["system"].startswith("_")}
    cols = list(metrics) + (["L8.discriminability"] if l8 else [])
    fig, ax = plt.subplots(figsize=(1.35 * len(cols) + 2.6, 0.55 * len(systems) + 1.6))
    for yi, s in enumerate(systems):
        for xi, m in enumerate(cols):
            if m == "L8.discriminability":
                r = l8.get(s)
                v = r["verdict"] if r else "not scored"
                label = f"AUC {_num(r['auc']):.2f}" if r and _num(r.get("auc")) is not None else "n/a"
            else:
                r = next((x for x in rows if x["system"] == s and x["metric"] == m), None)
                v = r["verdict"] if r else "not scored"
                pct = _num(r.get("percentile_of_bio")) if r else None
                label = f"{pct:.2f}" if pct is not None else "n/a"
            ax.add_patch(plt.Rectangle((xi, yi), 0.94, 0.88, color=COLOURS.get(v, "#9aa3a8"), alpha=0.85))
            ax.text(xi + 0.47, yi + 0.44, label, ha="center", va="center", color="white", fontsize=9)
    n = len(cols)
    ax.set_xlim(0, n + 0.9)
    ax.set_ylim(len(systems), 0)
    ax.set_xticks(np.arange(n) + 0.47)
    ax.set_xticklabels(cols, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(np.arange(len(systems)) + 0.44)
    ax.set_yticklabels(systems, fontsize=9)
    for yi, s in enumerate(systems):
        ratios = [_num(x.get("self_spread_ratio")) for x in rows
                  if x["system"] == s and _truthy(x.get("primary"))]
        ratios = [r for r in ratios if r is not None]
        if ratios:
            ax.text(n + 0.15, yi + 0.44, f"{np.median(ratios):.2f}", va="center", fontsize=9)
    ax.text(n + 0.15, -0.15, "individuality", fontsize=8, va="bottom")
    title = ("Fidelity profile: green = inside the real worm-to-worm range, red = outside, "
             "amber = too typical (an average worm)\n"
             "number = percentile of real worm-to-worm distances; individuality: real worms = 1")
    if l8:
        title += "; L8: classifier AUC vs held-out real worms"
    if subtitle:
        title += "\n" + subtitle
    ax.set_title(title, fontsize=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
