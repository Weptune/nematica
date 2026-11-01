"""Which pokes should a lab run? On the synthetic worm of scripts/run_synthetic_watch.py
(shared unrecorded drives at 5% of input, half the neurons seen per recording, 30% never
seen), a fixed budget of pokes is spent three ways, each combined with 10 hours of watching:

  random     a random observed neuron each pulse (as in the atlas)
  spread     the observed neuron poked least so far
  guided     neurons ranked by how much a watching model (fitted first) says they drive
             others; each pulse goes to the highest-ranked observed neuron not yet poked
             more than the others in its rank band

Combined estimate of cause and effect per pair: poke average where pokes exist, shrunk
toward the watching model's value: (n x poke mean + L x watching) / (n + L). Single pokes are
very noisy, so the weight L matters; it is chosen from a grid (2 to 1000) as the value best
for the three strategies on average, using the ground truth: an oracle-tuned upper bound,
applied equally to every strategy. Every strategy is scored on the same pairs (not hidden,
off-diagonal).

Usage:  python scripts/run_synthetic_design.py [--model connectome_constrained]
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sw", HERE / "run_synthetic_watch.py")
sw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="connectome_constrained")
    ap.add_argument("--share", type=float, default=0.05)
    ap.add_argument("--budgets", default="500,2000,8000")
    args = ap.parse_args()
    z = np.load(Path(HERE.parent) / "data/external/creamer_lds" / f"{args.model}.npz")
    A, Q, R = z["A"], z["Q"], z["R"]
    n = len(A)
    Lq = np.sqrt(np.diag(Q)) * np.eye(n)
    sr = np.sqrt(np.diag(R))
    K = sw.true_K(A)
    hidden = np.random.default_rng(0).random(n) < 0.3
    mask = ~np.eye(n, dtype=bool) & ~hidden[:, None] & ~hidden[None, :]
    D = sw.shared_drive(Lq, args.share, 3, np.random.default_rng(7))
    g = np.random.default_rng(1)
    watch = []
    for _ in range(16):                                    # 10 hours of watching
        obs = (g.random(n) < 0.5) & ~hidden
        y = sw.simulate(A, Lq, sr, sw.FRAMES, g, D=D)
        y[:, ~obs] = np.nan
        watch.append(y)
    Kw = sw.true_K(sw.fit_watching(watch, n))
    influence = np.abs(np.where(np.eye(n, dtype=bool), 0, Kw)).sum(axis=0)    # how much j drives others
    rank = np.argsort(-influence)
    per_rec = len(range(sw.EVERY, sw.FRAMES - sw.WIN, sw.EVERY))
    rows = []
    print(f"watching only: {sw.score(Kw, K, mask):.3f}", flush=True)
    for budget in [int(b) for b in args.budgets.split(",")]:
        for strategy in ("random", "spread", "guided"):
            gg = np.random.default_rng(2)
            psum, pn = np.zeros((n, n)), np.zeros((n, n))
            count = np.zeros(n)
            done = 0
            while done < budget:
                obs = (gg.random(n) < 0.5) & ~hidden
                targets = np.flatnonzero(obs)
                kicks = {}
                for f in range(sw.EVERY, sw.FRAMES - sw.WIN, sw.EVERY):
                    if done >= budget:
                        break
                    if strategy == "random":
                        j = int(gg.choice(targets))
                    elif strategy == "spread":
                        j = int(targets[np.argmin(count[targets] + 1e-3 * gg.random(len(targets)))])
                    else:
                        order = [t for t in rank if obs[t]][: max(5, len(targets) // 3)]
                        j = int(order[np.argmin(count[order] + 1e-3 * gg.random(len(order)))])
                    kicks[f] = j
                    count[j] += 1
                    done += 1
                yp = sw.simulate(A, Lq, sr, sw.FRAMES, gg, kicks, D=D)
                for f, j in kicks.items():
                    resp = (yp[f:f + sw.WIN] - yp[f - 10:f].mean(axis=0)).sum(axis=0)
                    psum[obs, j] += resp[obs]
                    pn[obs, j] += 1
            for L in (2, 10, 50, 200, 1000):
                Kc = (psum + L * Kw) / (pn + L)
                rows.append({"model": args.model, "share": args.share, "budget": budget, "strategy": strategy,
                             "weight": L, "combined": round(sw.score(Kc, K, mask), 3),
                             "neurons_poked": int((count > 0).sum())})
        sub = [r for r in rows if r["budget"] == budget]
        best = max((2, 10, 50, 200, 1000), key=lambda L: np.mean([r["combined"] for r in sub if r["weight"] == L]))
        for r in sub:
            if r["weight"] == best:
                print(f"budget {budget:5d}  weight {best:4d}  {r['strategy']:7s} {r['combined']:.3f}  ({r['neurons_poked']} neurons poked)", flush=True)
    out = Path(HERE.parent) / f"docs/figures/synthetic_design_{args.model}.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
