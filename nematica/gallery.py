"""A gallery of artificial neural networks, each written as a BrainCopy (nematica.score), so
every family is judged on the same ruler: where does it differ from real worms, measured in
units of how real worms differ from each other?

Families here:
  LinearRest    trained on recordings: a linear network of neuron classes learned from
                activity with no light pulse nearby (it watches, never sees a poke)
  RandomNet     randomly wired: the same size, density of couplings, stability and noise as
                LinearRest, but who drives whom is random (never fitted to it)
  KunertNet     shaped by the wiring diagram and never fitted to any recording: the Kunert
                et al. 2014 graded-potential model of 279 neurons on the White/Varshney
                connectome, driven by coloured noise

Families scored elsewhere and added to the gallery by name in scripts/run_gallery.py: the
poke-trained hybrid, the GRU trained on recordings, and Creamer et al.'s published model.
Choices marked [A] are assumptions, not measurements.
"""

from __future__ import annotations

import numpy as np

from .score import BrainCopy, Template

POST = 61          # frames after a pulse treated as stimulated (30 s at 0.5 s per frame)


def class_traces(worm, classes) -> np.ndarray:
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


class ClassNet(BrainCopy):
    """A linear network of neuron classes, z(t) = A z(t-1) + noise; the poked class is held to
    its drive, the rest follow. Subclasses decide A."""

    def _clamped_run(self, worm: Template, rng, burn: int = 200) -> np.ndarray:
        idx = {c: i for i, c in enumerate(self.classes)}
        C, T = len(self.classes), worm.n_frames
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
        # one trace per class: the poked neuron's partner would otherwise copy the clamped
        # drive exactly, a same-class "response" no neuron-level copy produces
        for p in worm.pokes:
            c = worm.classes[p.index]
            for j, cj in enumerate(worm.classes):
                if cj == c and j != p.index:
                    out[j, p.frame:p.frame + len(p.drive)] = np.nan
        return out

    def run(self, worm, rng):
        return self._clamped_run(worm, rng)


class LinearRest(ClassNet):
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
            X.append(np.nan_to_num(z[:, :-1][:, ok]))    # an unseen class contributes nothing as input
            Y.append(z[:, 1:][:, ok])                    # ...but is not a target of zero
        X, Y = np.hstack(X), np.hstack(Y)
        self.A = np.zeros((C, C))
        self.noise = np.ones(C)
        res = []
        for i in range(C):                               # each class fitted only where it was seen
            m = np.isfinite(Y[i])
            if m.sum() < 50:
                continue
            Xi = X[:, m]
            self.A[i] = Y[i, m] @ Xi.T @ np.linalg.inv(Xi @ Xi.T + self.ridge * np.eye(C))
            res.append((i, Y[i, m] - self.A[i] @ Xi))
        r = np.abs(np.linalg.eigvals(self.A)).max()
        if r > 0.99:
            self.A *= 0.99 / r                           # keep the free run stable
        for i, e in res:
            self.noise[i] = e.std()


class RandomNet(LinearRest):
    """LinearRest's size, self-coupling, density, coupling strengths, stability and noise,
    with who-drives-whom shuffled: the fitted off-diagonal couplings are dealt out to random
    pairs (signs and sizes kept), then the network is rescaled to the fitted spectral
    radius. Learned statistics, random wiring."""

    name = "random-wiring"

    def __init__(self, ridge: float = 300.0, seed: int = 0):
        super().__init__(ridge)
        self.seed = seed

    def fit(self, worms):
        super().fit(worms)
        rng = np.random.default_rng(self.seed)
        A = self.A
        C = len(A)
        off = ~np.eye(C, dtype=bool)
        R = np.diag(np.diag(A)).astype(float)
        R[off] = rng.permutation(A[off])
        target = np.abs(np.linalg.eigvals(A)).max()
        r = np.abs(np.linalg.eigvals(R)).max()
        if r > 0:
            R *= target / r
        self.A = R


class KunertNet(BrainCopy):
    """The Kunert et al. 2014 connectome model as a copy (no fitting). Ongoing activity:
    coloured-noise current into every neuron (amplitude 0.5, 1 s correlation time, as in the
    benchmark's driving condition D1). A poke: depolarising current into the poked neuron,
    `gain` x its positive drive, frame by frame [A]. Calcium: the model's own synaptic
    activation phi(V), filtered by a GCaMP decay of `tau_ca` s [A], plus white measurement
    noise of `meas` x its SD [A]."""

    name = "kunert2014"

    def __init__(self, gain: float = 1.0, tau_ca: float = 1.5, meas: float = 0.2, dt: float = 0.05,
                 amplitude: float = 0.5, warmup_s: float = 30.0):
        from .systems.kunert import KunertModel
        self.model = KunertModel.load()
        from .data.pumpprobe import neuron_class
        self.cell = {n.upper(): i for i, n in enumerate(self.model.names)}
        self.members = {}                               # class -> model neurons, for labels
        for i, n in enumerate(self.model.names):        # without a side (SAAD, RIG, VB1)
            self.members.setdefault(neuron_class(n), []).append(i)
        self.gain, self.tau_ca, self.meas, self.dt = gain, tau_ca, meas, dt
        self.amplitude, self.warmup = amplitude, warmup_s

    def run(self, worm, rng):
        from .systems.kunert import BETA, coloured_noise_drive
        m, dt = self.model, self.dt
        n = m.n
        total = self.warmup + worm.n_frames * worm.dt
        seed = int(rng.integers(1 << 31))
        noise = coloured_noise_drive(n, self.amplitude, 1.0, total + 1.0, seed=seed)
        stim = {}
        for p in worm.pokes:
            idx = self._rows(p.neuron)
            if not idx:
                continue
            for k, v in enumerate(p.drive):
                if np.isfinite(v) and v > 0:
                    for i in idx:                       # a side-less label: both partners
                        stim.setdefault(p.frame + k, []).append((i, self.gain * float(v)))
        warm, fdt = self.warmup, worm.dt

        def drive(t):
            I = noise(t)
            f = int((t - warm) // fdt)
            if t >= warm and f in stim:
                I = I.copy()
                for i, a in stim[f]:
                    I[i] += a
            return I

        t, V = m.simulate(total, dt=dt, drive=drive, record_every_s=fdt, seed=seed)
        keep = t >= warm
        act = 1.0 / (1.0 + np.exp(-BETA * V[:, keep]))[:, :worm.n_frames]
        a = np.exp(-fdt / self.tau_ca)
        ca = np.empty_like(act)
        ca[:, 0] = act[:, 0]
        for k in range(1, act.shape[1]):
            ca[:, k] = a * ca[:, k - 1] + (1 - a) * act[:, k]
        ca += self.meas * ca.std(axis=1, keepdims=True) * rng.standard_normal(ca.shape)
        out = np.full((len(worm.names), worm.n_frames), np.nan)
        L = min(ca.shape[1], worm.n_frames)
        for j, nm in enumerate(worm.names):
            idx = self._rows(nm)
            if idx:
                out[j, :L] = ca[idx, :L].mean(axis=0)
        return out

    def _rows(self, name: str) -> list[int]:
        """Model neurons for a real label: the neuron itself, or its class when the label has
        no side or a different spelling (VB1 for VB01). Pharyngeal neurons are not in the
        model and stay unmodelled."""
        from .data.pumpprobe import neuron_class
        if not name:
            return []
        if name.upper() in self.cell:
            return [self.cell[name.upper()]]
        return self.members.get(neuron_class(name), [])
