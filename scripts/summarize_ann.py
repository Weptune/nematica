"""Markdown tables for the artificial lab (README), straight from the result files.

Usage:  python scripts/summarize_ann.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

FIG = Path("docs/figures")


def lab_a():
    out = []
    d = pd.read_csv(FIG / "ann_watch.csv")
    f = pd.read_csv(FIG / "ann_watch_fullobs.csv")
    out.append("| Recording | Hidden drives | Hours | Linear watcher | Neural-network watcher | Recurrent watcher | Poking |")
    out.append("|---|---|---|---|---|---|---|")
    for name, df in (("every unit, every time", f), ("half the units, 30% never", d)):
        g = df.groupby(["share", "tau", "hours"])[["linear", "mlp", "gru", "poke"]].mean()
        for (share, tau, hours), r in g.iterrows():
            if hours not in (2.5, 10.0, 40.0, 70.0):
                continue
            drv = "none" if share == 0 else f"{share:.0%}, {tau:.0f} s"
            out.append(f"| {name} | {drv} | {hours:g} | {r.linear:.2f} | {r.mlp:.2f} | {r.gru:.2f} | {r.poke:.2f} |")
    return "\n".join(out)


def lab_b():
    out = ["| Species | Copy | True agreement with individuals (individuals with each other) | Noise-averaged echo agreement (individuals) | Ruler: pattern | Ruler: shown to agree |",
           "|---|---|---|---|---|---|"]
    order = ["species_mean", "another_individual", "scrambled_0.1", "scrambled_0.25", "scrambled_1.0", "hybrid_kernels", "var3_spontaneous"]
    for tag, label in (("base", "sigma 0.3, drives 5%"), ("nodrive", "sigma 0.3, no drives"), ("strongdrive", "sigma 0.3, drives 25%"),
                       ("sigma0.1", "sigma 0.1, drives 5%"), ("sigma0.6", "sigma 0.6, drives 5%")):
        p = FIG / f"ann_ruler_{tag}.csv"
        if not p.exists():
            continue
        d = pd.read_csv(p)
        for c in order:
            s = d[d["copy"] == c]
            if s.empty:
                continue
            tk = s.true_copy_vs_individuals.mean()
            tki = s.true_individuals_vs_each_other.mean()
            truth = f"{tk:.2f} ({tki:.2f})" if pd.notna(tk) else f"not defined ({tki:.2f})"
            me = f"{s.mean_echo_copy_vs_individuals.mean():.2f} ({s.mean_echo_individuals_vs_each_other.mean():.2f})"
            inside = int((s.verdict == "inside").sum())
            agrees = int((s.equivalence == "agrees").sum())
            out.append(f"| {label} | {c} | {truth} | {me} | inside {inside} of {len(s)} | {agrees} of {len(s)} |")
    return "\n".join(out)


def lab_memory():
    m = pd.read_csv(FIG / "ann_memory.csv")
    full, atl = pd.read_csv(FIG / "ann_watch_fullobs.csv"), pd.read_csv(FIG / "ann_watch.csv")
    rows = ["| Recording (one brain, 40 h) | Linear, added / held | Network, added / held | Network with 5 s of history, held | Recurrent (4x training, larger), added / held | Poking, same brain |",
            "|---|---|---|---|---|---|"]
    for _, r in m.iterrows():
        df = full if r.recording == "every unit" else atl
        pk = df[(df.seed == 0) & (df.share == r.share) & (df.tau == r.tau) & (df.hours == 40.0)].poke.iloc[0]
        drv = "no drives" if r.share == 0 else f"drives {r.share:.0%}, {r.tau:.0f} s"
        rows.append(f"| {r.recording}, {drv} | {r.linear_add:.2f} / {r.linear_clamp:.2f} | {r.mlp_add:.2f} / {r.mlp_clamp:.2f} | "
                    f"{r.mlp_5s_history_clamp:.2f} | {r.gru_long_add:.2f} / {r.gru_long_clamp:.2f} | {pk:.2f} |")
    return "\n".join(rows)


if __name__ == "__main__":
    print(lab_a())
    print()
    print(lab_b())
    print()
    print(lab_memory())
