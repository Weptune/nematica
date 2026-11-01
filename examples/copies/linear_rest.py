"""A copy built by watching: a linear model of how neuron classes drive each other, learned
only from the stretches of each training worm with no light pulse nearby. On held-out worms
it runs freely, the poked class is held to its drive, and the others follow the learned
couplings. Written against the public interface only, as a template for your own copy.

    python -m nematica score examples/copies/linear_rest.py:LinearRest --quick
"""

import numpy as np

from nematica.score import BrainCopy

POST = 61          # frames after a pulse treated as stimulated (30 s at 0.5 s per frame)


def class_traces(worm, classes):
    """(classes, frames) mean z-scored trace per class; NaN where a class is not seen."""
    out = np.full((len(classes), worm.x.shape[1]), np.nan)
    idx = {c: i for i, c in enumerate(classes)}
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (worm.x - np.nanmean(worm.x, 1, keepdims=True)) / np.nanstd(worm.x, 1, keepdims=True)
    for c in set(worm.classes) & set(idx):
        rows = [j for j, k in enumerate(worm.classes) if k == c]
        with np.errstate(invalid="ignore"):
            out[idx[c]] = np.nanmean(z[rows], axis=0)
    return out


class LinearRest(BrainCopy):
    name = "linear-rest"

    def __init__(self, ridge: float = 300.0):
        self.ridge = ridge

    def fit(self, worms):
        counts = {}
        for w in worms:
            for c in set(w.classes) - {""}:
                counts[c] = counts.get(c, 0) + 1
        self.classes = sorted(c for c, n in counts.items() if n >= 0.3 * len(worms))
        C = len(self.classes)
        X, Y = [], []
        for w in worms:
            z = class_traces(w, self.classes)
            quiet = np.ones(z.shape[1], bool)
            for f in w.all_stim_frames:
                quiet[max(f, 0):f + POST] = False
            ok = quiet[:-1] & quiet[1:]
            a, b = np.nan_to_num(z[:, :-1][:, ok]), np.nan_to_num(z[:, 1:][:, ok])
            X.append(a)
            Y.append(b)
        X, Y = np.hstack(X), np.hstack(Y)
        self.A = Y @ X.T @ np.linalg.inv(X @ X.T + self.ridge * np.eye(C))
        r = np.abs(np.linalg.eigvals(self.A)).max()
        if r > 0.99:
            self.A *= 0.99 / r                       # keep the free run stable
        self.noise = (Y - self.A @ X).std(axis=1)

    def run(self, worm, rng):
        idx = {c: i for i, c in enumerate(self.classes)}
        C, T, burn = len(self.classes), worm.n_frames, 200
        clamp = {}
        for p in worm.pokes:
            c = worm.classes[p.index]
            if c in idx:
                for t, v in enumerate(p.drive):
                    if np.isfinite(v):
                        clamp[p.frame + t] = (idx[c], p.frame, float(v))
        z = np.zeros((C, T + burn))
        base = {}
        for t in range(1, T + burn):
            z[:, t] = self.A @ z[:, t - 1] + self.noise * rng.standard_normal(C)
            tt = t - burn
            if tt in clamp:
                ci, f0, v = clamp[tt]
                base.setdefault((ci, f0), z[ci, t - 1])
                z[ci, t] = base[(ci, f0)] + v
        z = z[:, burn:]
        out = np.full((len(worm.names), T), np.nan)
        for j, c in enumerate(worm.classes):
            if c in idx and worm.names[j]:
                out[j] = z[idx[c]]
        return out
