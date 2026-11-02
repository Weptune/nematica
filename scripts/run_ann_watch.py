"""Artificial lab A: can cause and effect be learned by watching a NONLINEAR brain, with
copies that are neural networks themselves?

Ground truth and estimators: nematica/annlab.py. Grid: hidden slow drives at 0, 5% or 25%
of input, with a 10 s or 90 s timescale; 2.5 to 70 hours of recording; two independently
drawn brains. Score: correlation of each estimate with the true K over pairs of units that
are ever seen. Output: docs/figures/ann_watch.csv (resumable).

Usage:  python scripts/run_ann_watch.py [--seeds 0,1]
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica import annlab as L  # noqa: E402

OUT = Path("docs/figures/ann_watch.csv")
SETTINGS = [(0.0, 10.0), (0.05, 10.0), (0.05, 90.0), (0.25, 10.0), (0.25, 90.0)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--hours", default="2.5,10,40,70")
    ap.add_argument("--rho", type=float, default=1.5)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--kick", type=float, default=1.5)
    ap.add_argument("--kick-frames", type=int, default=1)
    ap.add_argument("--q", type=float, default=0.3)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--hidden-frac", type=float, default=0.3, help="units never seen in any recording")
    ap.add_argument("--seen", type=float, default=0.5, help="fraction of the other units seen per recording")
    ap.add_argument("--settings", default=None, help="share:tau pairs, e.g. 0:10,0.25:90")
    args = ap.parse_args()
    L.KICK, L.KICK_FRAMES = args.kick, args.kick_frames
    out = Path(args.out)
    rows = list(csv.DictReader(out.open(encoding="utf-8"))) if out.exists() else []
    done = {(r["seed"], r["share"], r["tau"], r["hours"]) for r in rows}
    settings = SETTINGS if not args.settings else [tuple(float(v) for v in p.split(":")) for p in args.settings.split(",")]
    for seed in [int(s) for s in args.seeds.split(",")]:
        for share, tau in settings:
            br = L.make_brain(rho=args.rho, share=share, k=args.k, tau=tau, seed=seed, q=args.q)
            K = L.true_K(br, np.random.default_rng(100 + seed))
            hidden = L.design(br.n, np.random.default_rng(200 + seed), args.hidden_frac)
            mask = ~np.eye(br.n, dtype=bool) & ~hidden[:, None] & ~hidden[None, :]
            for hours in [float(h) for h in args.hours.split(",")]:
                key = (str(seed), str(share), str(tau), str(hours))
                if key in done:
                    continue
                t0 = time.time()
                rng = np.random.default_rng(1000 * seed + int(hours * 10))
                W = L.recordings(br, hours, rng, hidden, seen=args.seen)
                P = L.recordings(br, hours, rng, hidden, poke=True, seen=args.seen)
                res = {"linear": L.score(L.K_linear(W, br.n), K, mask),
                       "poke": L.score(L.K_poke(P, br.n), K, mask)}
                net = L.fit_mlp(W, br.n, seed=seed)
                res["mlp"] = L.score(L.K_mlp(net, W, br.n), K, mask)
                g = L.fit_gru(W, br.n, seed=seed)
                res["gru"] = L.score(L.K_gru(g, W, br.n), K, mask)
                row = {"seed": seed, "share": share, "tau": tau, "hours": hours, "recordings": len(W),
                       **{k: round(v, 4) for k, v in res.items()}, "rho": args.rho, "drives": args.k,
                       "kick": args.kick, "kick_frames": args.kick_frames, "q": args.q,
                       "hidden_frac": args.hidden_frac, "seen": args.seen}
                rows.append(row)
                print(row, f"({time.time() - t0:.0f} s)", flush=True)
                with out.open("w", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                    w.writeheader()
                    w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
