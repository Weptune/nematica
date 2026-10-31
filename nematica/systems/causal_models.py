"""Arc 4: brain models that can be stimulated, for the causal levels.

ClassVAR    a pooled ridge VAR(p) on class-level activity (z-scored per worm), fitted on the
            atlas training worms: either spontaneous frames only (no stimulation in the
            previous 30 s) or all frames. Missing classes enter as zero (the mean) and are
            never targets [A]; in simulation, classes a worm does not show stay at zero, as in training.
            Where the fitted dynamics are explosive for a worm's class set, they are scaled to
            spectral radius 0.99 [A].

Stimulation protocol (the same for every model): the model runs the worm's whole recording
length with its own noise (diagonal Gaussian residuals [A]); at each of the worm's
stimulations, the stimulated class is clamped for 30 s to its pre-pulse model value plus the
stimulated neuron's own measured response (in its SD units) [M]. The simulated recording then
goes through exactly the response pipeline used for real worms.
"""

from __future__ import annotations

import numpy as np

from ..bench.causal import window
from ..data.pumpprobe import PumpProbe


def class_matrix(rec: PumpProbe, classes) -> np.ndarray:
    """(len(classes), T) class means of per-neuron z-scores; NaN where not observed."""
    T = rec.n_frames
    out = np.full((len(classes), T), np.nan)
    idx = {c: i for i, c in enumerate(classes)}
    groups: dict = {}
    for j, c in enumerate(rec.classes):
        if c in idx:
            groups.setdefault(c, []).append(j)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (rec.x - np.nanmean(rec.x, axis=1, keepdims=True)) / np.nanstd(rec.x, axis=1, keepdims=True)
    for c, rows in groups.items():
        with np.errstate(invalid="ignore"):
            out[idx[c]] = np.nanmean(z[rows], axis=0) if len(rows) > 1 else z[rows[0]]
    return out


def spontaneous_mask(rec: PumpProbe) -> np.ndarray:
    _, npost = window(rec.dt)
    m = np.ones(rec.n_frames, bool)
    for f in rec.all_stim_frames:
        m[max(f, 0):f + npost] = False
    return m


class ClassVAR:
    def __init__(self, lags: int = 3, frames: str = "spontaneous", min_fraction: float = 0.3,
                 ridges=(1.0, 10.0, 100.0, 1000.0, 10000.0), max_radius: float = 0.99):
        self.lags, self.frames, self.min_fraction, self.ridges = lags, frames, min_fraction, ridges
        self.max_radius = max_radius
        self.name = f"var{lags}_{frames}"

    # -------------------------------------------------------------- fitting
    def _design(self, recs):
        p, C = self.lags, len(self.classes)
        Xs, Ys = [], []
        for r in recs:
            z = class_matrix(r, self.classes)
            use = spontaneous_mask(r) if self.frames == "spontaneous" else np.ones(r.n_frames, bool)
            zf = np.nan_to_num(z)
            T = z.shape[1]
            ok = np.array([use[t - p:t + 1].all() for t in range(p, T)])
            ts = np.arange(p, T)[ok]
            if ts.size == 0:
                continue
            X = np.hstack([zf[:, ts - L].T for L in range(1, p + 1)] + [np.ones((ts.size, 1))])
            Xs.append(X)
            Ys.append(z[:, ts].T)
        return np.vstack(Xs), np.vstack(Ys)

    def _solve(self, X, Y, lam):
        W = np.zeros((X.shape[1], Y.shape[1]))
        pen = np.full(X.shape[1], lam)
        pen[-1] = 0.0
        for j in range(Y.shape[1]):
            m = np.isfinite(Y[:, j])
            if m.sum() < 50:
                continue
            Xm = X[m]
            W[:, j] = np.linalg.solve(Xm.T @ Xm + np.diag(pen), Xm.T @ Y[m, j])
        return W

    def fit(self, train, val):
        from collections import Counter
        cnt = Counter(c for r in train for c in set(r.classes) if c)
        self.classes = sorted(c for c, n in cnt.items() if n >= self.min_fraction * len(train))
        X, Y = self._design(train)
        Xv, Yv = self._design(val)
        best = None
        for lam in self.ridges:
            W = self._solve(X, Y, lam)
            P = Xv @ W
            m = np.isfinite(Yv)
            r2 = 1 - np.sum((Yv - P)[m] ** 2) / np.sum((Yv - np.nanmean(Yv, axis=0))[m] ** 2)
            if best is None or r2 > best[1]:
                best = (lam, r2, W)
        X = np.vstack([X, Xv])
        Y = np.vstack([Y, Yv])
        self.W = self._solve(X, Y, best[0])
        R = Y - X @ self.W
        self.noise_sd = np.sqrt(np.nanmean(R ** 2, axis=0))
        self.noise_sd[~np.isfinite(self.noise_sd)] = 1.0
        self.radius = self.spectral_radius()
        self.info = {"radius": round(self.radius, 4), "ridge": best[0], "val_r2": round(float(best[1]), 4), "classes": len(self.classes),
                     "rows": int(X.shape[0])}
        return self

    def spectral_radius(self, seen=None) -> float:
        C, p = len(self.classes), self.lags
        A = self.W[:-1].reshape(p, C, C)
        if seen is not None:
            A = A[:, seen][:, :, seen]
            C = int(np.sum(seen))
        comp = np.zeros((p * C, p * C))
        comp[:C, :] = np.hstack([A[L].T for L in range(p)])
        if p > 1:
            comp[C:, :-C] = np.eye((p - 1) * C)
        return float(np.abs(np.linalg.eigvals(comp)).max())

    # -------------------------------------------------------------- stimulation
    def simulate(self, rec: PumpProbe, rng: np.random.Generator, burn: int = 200) -> PumpProbe:
        """A simulated version of `rec`: the model's classes observed in this worm, one row
        each, stimulated on the worm's schedule."""
        C, p = len(self.classes), self.lags
        idx = {c: i for i, c in enumerate(self.classes)}
        T = rec.n_frames
        npre, npost = window(rec.dt)
        sd = np.nanstd(rec.x, axis=1)
        clamp = {}                                     # frame -> (class index, offset from baseline)
        stims_out = []
        own = [c for c in sorted(set(rec.classes)) if c in idx]
        row_of = {c: i for i, c in enumerate(own)}
        for k, f in rec.stims:
            c = rec.classes[k]
            if c not in idx or f - npre < 0 or f + npost > T or not sd[k] > 0:
                continue
            self_tr = (rec.x[k, f:f + npost] - np.nanmean(rec.x[k, f - npre:f])) / sd[k]
            for t, v in enumerate(self_tr):
                if np.isfinite(v):
                    clamp[f + t] = (idx[c], f, float(v))
            stims_out.append((row_of[c], f))
        # classes this worm does not show stay at zero, as missing classes did in training
        seen = np.zeros(C, bool)
        seen[[idx[c] for c in own]] = True
        z = np.zeros((C, T + burn))
        A = self.W[:-1].reshape(p, C, C).copy()        # A[L-1][from, to]
        # the fitted dynamics are slightly explosive for some worms' class sets (slow drifts in
        # the recordings); scaling lag L by g**L scales every eigenvalue by g, so the system
        # is made just stable (radius 0.99) where needed [A]
        rad = self.spectral_radius(seen)
        g = min(1.0, self.max_radius / rad) if rad > 0 else 1.0
        for L in range(1, p + 1):
            A[L - 1] *= g ** L
        self.last_gain = g
        b = self.W[-1]
        base = {}
        for t in range(p, T + burn):
            nxt = b + sum(z[:, t - L] @ A[L - 1] for L in range(1, p + 1))
            nxt += self.noise_sd * rng.standard_normal(C)
            nxt[~seen] = 0.0
            tt = t - burn
            if tt in clamp:
                ci, f0, v = clamp[tt]
                if (ci, f0) not in base:
                    base[(ci, f0)] = z[ci, t - 1]
                nxt[ci] = base[(ci, f0)] + v
            z[:, t] = nxt
        x = z[[idx[c] for c in own], burn:]
        return PumpProbe(uid=rec.uid, x=x, names=own, classes=own, stims=stims_out, dt=rec.dt,
                         all_stim_frames=list(rec.all_stim_frames))


class CreamerCausal:
    """The published Creamer, Leifer & Pillow (2024) linear dynamical systems (fitted to this
    atlas, 154 named neurons, 2 Hz, one lag) under the same stimulation protocol: the
    stimulated neuron is clamped to its pre-pulse value plus its own measured response, the
    rest evolve with the published dynamics and noise (y = x + v). Neuron-level rows for the
    worm's named neurons the model has. The published parameters were fitted to atlas worms,
    possibly including the scored ones [L: in-sample unless shown otherwise]."""

    def __init__(self, variant: str = "connectome_constrained", folder=None):
        from .published import DEFAULT_DIR
        from pathlib import Path
        z = np.load(Path(folder or DEFAULT_DIR) / f"{variant}.npz")
        self.variant = variant
        self.name = f"creamer2024_{variant}"
        self.A, self.Q, self.R = z["A"], z["Q"], z["R"]
        self.cells = [str(c) for c in z["cell_ids"]]
        self.Lq = np.linalg.cholesky(self.Q + 1e-12 * np.eye(len(self.Q)))
        self.sr = np.sqrt(np.clip(np.diag(self.R), 0, None))
        self.info = {"neurons": len(self.cells),
                     "radius": round(float(np.max(np.abs(np.linalg.eigvals(self.A)))), 4)}

    def fit(self, train=None, val=None):
        return self

    def simulate(self, rec: PumpProbe, rng: np.random.Generator, burn: int = 600) -> PumpProbe:
        from ..data.pumpprobe import neuron_class
        n = len(self.cells)
        cell_of = {c.upper(): i for i, c in enumerate(self.cells)}
        T = rec.n_frames
        npre, npost = window(rec.dt)
        sd = np.nanstd(rec.x, axis=1)
        own = sorted({rec.names[j].upper() for j, c in enumerate(rec.classes) if c and rec.names[j].upper() in cell_of})
        row_of = {nm: i for i, nm in enumerate(own)}
        clamp, stims_out = {}, []
        for k, f in rec.stims:
            nm = rec.names[k].upper()
            if nm not in cell_of or nm not in row_of or f - npre < 0 or f + npost > T or not sd[k] > 0:
                continue
            tr = (rec.x[k, f:f + npost] - np.nanmean(rec.x[k, f - npre:f])) / sd[k]
            for t, v in enumerate(tr):
                if np.isfinite(v):
                    clamp[f + t] = (cell_of[nm], f, float(v))
            stims_out.append((row_of[nm], f))
        x = np.zeros(n)
        out = np.empty((n, T))
        base = {}
        for t in range(-burn, T):
            x = self.A @ x + self.Lq @ rng.standard_normal(n)
            if t in clamp:
                ci, f0, v = clamp[t]
                if (ci, f0) not in base:
                    base[(ci, f0)] = float(out[ci, t - 1]) if t > 0 else 0.0
                x[ci] = base[(ci, f0)] + v
            if t >= 0:
                out[:, t] = x + self.sr * rng.standard_normal(n)
        rows = [cell_of[nm] for nm in own]
        return PumpProbe(uid=rec.uid, x=out[rows], names=own, classes=[neuron_class(nm) for nm in own],
                         stims=stims_out, dt=rec.dt, all_stim_frames=list(rec.all_stim_frames))
