"""Figure: the emulator and its ablations on the confirmation split (blocks1, seed 0): one cell per
level, three letters for the three pools, coloured by how many pools are inside."""
import glob, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
CACHE = "results/emulator_confirm"
LEVELS = [("L1.distribution", "distribution"), ("L1.timescale", "timescale"), ("L2.correlation", "correlation"),
          ("L2.dimension", "dimension"), ("L4.leadlag", "lead-lag"), ("L4.dwell", "reversal bouts"),
          ("C1.pattern", "echo pattern"), ("C2.magnitude", "echo size"), ("P2.spread", "echo spread")]
F = "hybrid_kernels_indivshock_innov6_slow6d_indivslow1_hp_mem"
ROWS = [("hybrid_kernels_slow6d_indivslow1_hp_mem_diag_hsd1", "minimal + neuron-level slow participation"),
        ("hybrid_kernels_slow6d_indivslow1_hp_mem_diag", "minimal emulator"),
        (F, "frozen emulator (registered: fail)"),
        ("hybrid_kernels_slow6d_indivslow1_hp_mem", "  minus common fast shocks"),
        (F + "_diag", "  minus coupling between neuron types"),
        ("hybrid_kernels_innov6_slow6d_hp_mem", "  minus individuality"),
        ("hybrid_kernels_indivshock_innov6_slow6_indivslow1_hp_mem", "  minus slow-state interactions"),
        ("hybrid_kernels_indivshock_innov6_mem", "  minus slow states"),
        (F + "_nokernels", "  minus causal links from pokes"),
        ("hybrid_kernels_indivshock_innov6_slow6d_indivslow1_hp", "  read out class by class")]
AB = {"inside": "I", "outside": "O", "too typical": "T"}
FILL = {3: "#2e8b57", 2: "#8cc5a0", 1: "#f0d9a0", 0: "#d98b84"}
rows = []
for spec, label in ROWS:
    fs = sorted(glob.glob(f"{CACHE}/fluct_f[012]_{spec}.csv"))
    if len(fs) < 3:
        continue
    d = pd.concat([pd.read_csv(f) for f in fs])
    rows.append((label, ["".join(d[d.metric == m].sort_values("fold").verdict.map(AB)) for m, _ in LEVELS]))
fig, ax = plt.subplots(figsize=(11, 0.48 * len(rows) + 1.6))
for r, (label, cells) in enumerate(rows):
    for c, v in enumerate(cells):
        n = v.count("I")
        ax.add_patch(plt.Rectangle((c + 0.04, r + 0.06), 0.92, 0.88, color=FILL[n], lw=0))
        ax.text(c + 0.5, r + 0.5, " ".join(v), ha="center", va="center", fontsize=9,
                color="white" if n == 3 else "#222")
ax.axvline(6, color="#444", lw=1.2)
ax.set_xlim(0, len(LEVELS)); ax.set_ylim(len(rows), 0)
ax.set_xticks(np.arange(len(LEVELS)) + 0.5); ax.set_xticklabels([n for _, n in LEVELS], fontsize=9)
ax.xaxis.tick_top()
ax.set_yticks(np.arange(len(rows)) + 0.5); ax.set_yticklabels([l for l, _ in rows], fontsize=9)
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
ax.text(3, -1.25, "at rest", ha="center", fontsize=10, weight="bold")
ax.text(7.5, -1.25, "when one neuron is poked", ha="center", fontsize=10, weight="bold")
fig.text(0.01, 0.01, "Held-out pools of the confirmation split, simulation seed 0. Letters per pool: I inside the real "
         "worm-to-worm range, O outside, T too typical. Green = passes (at least 2 of 3 pools inside); amber and red fail.", fontsize=8, color="#444")
plt.tight_layout(rect=(0, 0.04, 1, 1))
out = Path("docs/figures/emulator_ablations.png")
fig.savefig(out, dpi=170)
print(out)
