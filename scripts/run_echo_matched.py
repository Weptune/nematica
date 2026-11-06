"""The echo test re-run with a matched readout (exploratory, after review 4; README section "The sparse,
sustained echo"). Differences from run_echo_sparse.py --calcium: the calcium decay acts on tanh(x)
before measurement noise is added (as in a worm, where camera noise comes after the indicator); decays
of 1, 1.5 and 3 s; lab units are averaged in fixed random pairs into classes, as worm classes average
left and right neurons; two lab brains; intervals by resampling individuals.

Usage: python scripts/run_echo_matched.py
Output: docs/figures/echo_matched.csv
"""
from __future__ import annotations

import csv
import dataclasses
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica.bench.perturbational import event_matrices  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
import run_ladder as LD  # noqa: E402
from nematica import annlab as L  # noqa: E402

OUT = ROOT / "docs" / "figures" / "echo_matched.csv"
TAU = {"t": None}


def record_ca(br, rng, obs, kicks, scale, spread):
    """run_ladder.record, with tanh(x) passed through a calcium decay before measurement noise."""
    n = br.n
    Dm = getattr(br, "Dm", None)
    k = (0 if br.D is None else br.D.shape[1]) or (0 if Dm is None else Dm.shape[1])
    x, s, c = np.zeros(n), np.zeros(k), np.zeros(n)
    a_ca = np.exp(-0.5 / TAU["t"])
    y = np.full((L.FRAMES, n), np.nan)
    active = {f + d: (j, scale[f]) for f, j in kicks.items() for d in range(LD.KICK_HOLD["frames"])}
    Wg = getattr(br, "Wg", None)
    for t in range(-400, L.FRAMES):
        if k:
            a_ = np.exp(-0.5 / br.tau)
            s = a_ * s + np.sqrt(1 - a_ * a_) * rng.standard_normal(k)
        rec = br.W @ np.tanh(x)
        if Dm is not None:
            rec = rec * (1.0 + br.gain * (Dm @ s))
        inp = rec + br.b + (br.D @ s if br.D is not None else 0.0)
        if Wg is not None:
            inp = inp + Wg @ (np.maximum(np.tanh(x) - LD.GATE_TH, 0.0) / (1 - LD.GATE_TH))
        x = (1 - L.LEAK) * x + L.LEAK * inp + br.q * rng.standard_normal(n)
        if t in active:
            j, a = active[t]
            x[j] += LD.KICK * a
            if spread:
                x[LD.NEIGH[j]] += spread * LD.KICK * a
        c = a_ca * c + (1 - a_ca) * np.tanh(x)
        if t >= 0:
            v = c + br.r * rng.standard_normal(n)
            y[t, obs] = v[obs]
    return y


def paired(recs, seed=5):
    """Units averaged in fixed random pairs: both units of a pair get the same class name."""
    out = []
    pr = np.random.default_rng(seed).permutation(120)
    cls_of = {int(u): f"P{i // 2:03d}" for i, u in enumerate(pr)}
    for r in recs:
        cls = [cls_of[int(nm[1:])] if nm and nm[1:].isdigit() else c for nm, c in zip(r.names, r.classes)]
        out.append(dataclasses.replace(r, classes=cls))
    return out


def per_rec(recs):
    """The three measures per recording, so they can be resampled over individuals."""
    rows = []
    for r in recs:
        ever, runs, change = [], [], []
        for e in event_matrices(r, keep=True):
            B = np.abs(np.nan_to_num(e["R"])) > 3
            ever.append(B.any(axis=1).mean())
            change.append(np.mean(np.any(B[:, 1:] != B[:, :-1], axis=0)))
            for row in B:
                n = 0
                for v in row:
                    if v:
                        n += 1
                    elif n:
                        runs.append(n); n = 0
                if n:
                    runs.append(n)
        if ever:
            rows.append((np.median(ever), np.mean(runs) if runs else 0.0, np.median(change)))
    return np.array(rows)


def summary(name, M, seed=0):
    rng = np.random.default_rng(seed)
    med = np.median(M, axis=0)
    bs = np.array([np.median(M[rng.integers(0, len(M), len(M))], axis=0) for _ in range(1000)])
    lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
    row = {"system": name, "ever": med[0], "ever_lo": lo[0], "ever_hi": hi[0], "mean_run": med[1],
           "run_lo": lo[1], "run_hi": hi[1], "change": med[2], "change_lo": lo[2], "change_hi": hi[2], "n": len(M)}
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
    return row


def main():
    rows = []
    worms = load_pumpprobe_dir(str(ROOT / "data" / "raw" / "randi2023_wt_npz"))
    rows.append(summary("worms", per_rec(worms)))
    LD.record = record_ca
    for tau in (1.0, 1.5, 3.0):
        TAU["t"] = tau
        for brain in (0, 1):
            for code in ("base", "D", "Q", "DGQ"):
                recs = paired(LD.variant_recs("" if code == "base" else code, brain, n_ind=30))
                rows.append(summary(f"{code} brain{brain} tau{tau}", per_rec(recs)))
            LD.KICK_HOLD["frames"] = 6
            recs = paired(LD.param_recs({"share": 0.4, "g": 0.75, "spread": 0.15, "quiet": 0.3, "mod": 0}, brain, n_ind=30, sigma=0.8))
            LD.KICK_HOLD["frames"] = LD.KICK_FRAMES
            rows.append(summary(f"round9 brain{brain} tau{tau}", per_rec(recs)))
            with OUT.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)


if __name__ == "__main__":
    main()
