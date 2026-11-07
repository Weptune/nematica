"""Watching limit, parts B and C (pre-registered 7 Nov 2026, README "The watching limit").

Scores the best watcher (nematica/systems/latent.py) on the same ruler as every copy, for the
worms (split cv3) or a ladder brain (scripts/run_ladder.py, seed 0, the folds of
run_ladder_ruler.py), and measures its data-limited agreement: the fitted model generates
recordings with exactly the real recordings' structure (same classes tracked, same gaps, same
stimulation frames so the same rest stretches), the best watcher is refitted on them (same k),
and its poke responses are correlated with the generating model's (seen classes, off-diagonal,
15 s summed).

Usage:  python scripts/run_latent_watch.py --data worms|ladder:D [--folds 0,1,2] [--reps 5]
Output: docs/figures/latent_watch.csv (resumable)
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica.bench.scorecard import SPLITS, SPLITS_DIR, FoldRuler, fold_parts, set_norm  # noqa: E402
from nematica.data.pumpprobe import PumpProbe, load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.limits import poke_response  # noqa: E402
from nematica.systems.causal_models import class_matrix  # noqa: E402
from nematica.systems.latent import LatentCopy  # noqa: E402

OUT = ROOT / "docs" / "figures" / "latent_watch.csv"
WIN = 30


def load(data):
    if data == "worms":
        recs = {r.uid: r for r in load_pumpprobe_dir(ROOT / "data/raw/randi2023_wt_npz")}
        folds = load_folds(SPLITS_DIR / SPLITS["cv3"])["folds"]
        return recs, folds
    import run_ladder as LD
    code = data.split(":")[1]
    recs = {r.uid: r for r in LD.variant_recs("" if code == "base" else code, 0)}
    uids = sorted(recs)
    perm = np.random.default_rng(1).permutation(uids)
    return recs, [sorted(perm[i::3]) for i in range(3)]


def simulate_like(m: LatentCopy, recs, rng, burn=200):
    """Recordings from the fitted model with the real recordings' structure."""
    C = len(m.classes) - m.k
    F = m.W[:-1].T
    q = m.noise_sd ** 2
    r = np.exp(m.lr_)
    d = len(F)
    out = []
    for rec in recs:
        z_real = class_matrix(rec, m.classes[:C])
        T = rec.n_frames
        z = np.zeros(d)
        X = np.empty((d, T))
        for t in range(-burn, T):
            z = F @ z + np.sqrt(q) * rng.standard_normal(d)
            if t >= 0:
                X[:, t] = z
        y = X[:C] + np.sqrt(r)[:, None] * rng.standard_normal((C, T))
        y[~np.isfinite(z_real)] = np.nan
        rows = [i for i in range(C) if np.isfinite(y[i]).any()]
        names = [m.classes[i] for i in rows]
        out.append(PumpProbe(uid=rec.uid, x=y[rows], names=names, classes=names, stims=[], dt=rec.dt,
                             all_stim_frames=list(rec.all_stim_frames)))
    return out


def model_G(m: LatentCopy, classes):
    C = len(m.classes) - m.k
    G = poke_response(m.W[:-1].T, len(m.classes), WIN)[:C, :C]
    idx = [m.classes.index(c) for c in classes]
    G = G[np.ix_(idx, idx)]
    return G[~np.eye(len(idx), dtype=bool)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", default="0,1,2")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--polish", type=int, default=200)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    out = Path(a.out)
    warnings.filterwarnings("ignore")
    set_norm("fluct")
    recs, folds = load(a.data)
    rows = list(csv.DictReader(out.open())) if out.exists() else []
    done = {(r["data"], r["fold"]) for r in rows}
    for fi in [int(f) for f in a.folds.split(",")]:
        if (a.data, str(fi)) in done:
            continue
        t0 = time.time()
        train, val, _ = fold_parts(recs, folds, fi)
        ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=False)
        m = LatentCopy(steps=a.steps, polish=a.polish)
        res = ruler.score("latent", m, seed_base=1000 * fi)
        c1 = next(r for r in res if r["metric"] == "C1.pattern")
        echo, real = 1 - c1["system_median"], 1 - c1["bio_median"]
        print(f"[{a.data} fold {fi}] latent k={m.k} echo {echo:.4f} real {real:.4f} share {echo / real:.3f} "
              f"({time.time() - t0:.0f} s) {m.info}", flush=True)
        # data-limited agreement
        C = len(m.classes) - m.k
        G0 = model_G(m, m.classes[:C])
        rng = np.random.default_rng(100 + fi)
        agrees = []
        for rep in range(a.reps):
            sim = simulate_like(m, list(train) + list(val), rng)
            ntr = len(train)
            m2 = LatentCopy(steps=a.steps, polish=a.polish, fixed_k=m.k, min_fraction=0.0)
            m2.fit(sim[:ntr], sim[ntr:])
            common = [c for c in m.classes[:C] if c in m2.classes]
            g_true = model_G(m, common)
            g_hat = model_G(m2, common)
            agrees.append(float(np.corrcoef(g_true, g_hat)[0, 1]))
            print(f"   self-check rep {rep}: {agrees[-1]:.3f}", flush=True)
        row = dict(data=a.data, fold=fi, k=m.k, classes=C, echo_agreement=round(echo, 4),
                   real_agreement=round(real, 4), share=round(echo / real, 4), verdict=c1["verdict"],
                   data_limited_agreement=round(float(np.mean(agrees)), 4),
                   data_limited_sd=round(float(np.std(agrees)), 4), radius=m.info["radius"],
                   val_loss=str(m.info["val_loss"]).replace(",", ";"), secs=round(time.time() - t0))
        rows = list(csv.DictReader(out.open())) if out.exists() else []
        rows.append(row)
        with out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(row))
            w.writeheader()
            w.writerows(rows)
        print(row, flush=True)


if __name__ == "__main__":
    main()
