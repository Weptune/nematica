"""Arc 3, what the wiring buys: the per-worm calcium-drive VAR with its neuron-to-neuron
weights restricted to a wiring diagram.

    class_wiring(classes)      j -> i allowed if any member of class j makes a chemical
                               synapse onto any member of class i, or they share a gap
                               junction (Kunert et al. 2014 / Neural Interactome matrices,
                               data_assets/kunert2014; Gs[i, j] = synapses from j onto i)
    shuffled_wiring(A, seed)   same number of inputs per class, inputs drawn at random
    diagonal_wiring(n)         no coupling between classes

Self-connections and the two behaviour channels (velocity, reversal) are always allowed,
and the behaviour channels are fitted without restriction: only neuron-to-neuron weights
are constrained. Fitting is column-separable ridge: each output is regressed on its allowed
inputs only, pooled over training worms (ridge chosen on validation worms), then each
training worm's own fit is shrunk toward the pooled one, as in IndividualVAR.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .forecasters import Forecaster, IndividualVAR, _masked_r2

KUNERT = Path(__file__).resolve().parents[2] / "data_assets" / "kunert2014"


def _members(names, cls):
    return [i for i, n in enumerate(names)
            if n == cls or (n.startswith(cls) and n[len(cls):].strip("DVLR") == "" and len(n) - len(cls) <= 2)]


def class_wiring(classes, folder: Path = KUNERT) -> np.ndarray:
    """(n, n) bool, A[i, j] = class j may influence class i. Classes without any member in
    the connectome get only self-connections."""
    names = [str(n) for n in ast.literal_eval((folder / "neuron_names.txt").read_text())]
    Gs, Gg = np.load(folder / "Gs.npy"), np.load(folder / "Gg.npy")
    mem = [_members(names, c) for c in classes]
    n = len(classes)
    A = np.eye(n, dtype=bool)
    for i in range(n):
        for j in range(n):
            if i != j and mem[i] and mem[j]:
                sub = np.ix_(mem[i], mem[j])
                A[i, j] = bool(Gs[sub].sum() > 0 or Gg[sub].sum() > 0 or Gg[np.ix_(mem[j], mem[i])].sum() > 0)
    return A


def shuffled_wiring(A: np.ndarray, seed: int) -> np.ndarray:
    """Same number of inputs per class (row), drawn uniformly from the other classes."""
    rng = np.random.default_rng(seed)
    n = len(A)
    S = np.eye(n, dtype=bool)
    for i in range(n):
        k = int(A[i].sum() - A[i, i])
        others = np.array([j for j in range(n) if j != i])
        S[i, rng.choice(others, size=k, replace=False)] = True
    return S


def diagonal_wiring(n: int) -> np.ndarray:
    return np.eye(n, dtype=bool)


def feature_mask(A: np.ndarray, lags: int) -> np.ndarray:
    """(lags * k, k) bool over LagFeatures columns (lag-major blocks of the k-dim state:
    n_core neurons then velocity, reversal) x outputs."""
    n = len(A)
    k = n + 2
    Ak = np.ones((k, k), dtype=bool)          # behaviour rows/columns unrestricted
    Ak[:n, :n] = A
    return np.vstack([Ak.T for _ in range(lags)])   # entry [l*k + j, c] = Ak[c, j]


def _masked_solve(G, B, allowed, ridge, prior=None):
    """Column-separable ridge: W[:, c] uses only features allowed[:, c]."""
    F, k = allowed.shape
    W = np.zeros((F, k))
    for c in range(k):
        idx = np.flatnonzero(allowed[:, c])
        Gc = G[np.ix_(idx, idx)] + ridge * np.eye(len(idx))
        rhs = B[idx, c] if prior is None else B[idx, c] + ridge * prior[idx, c]
        W[idx, c] = np.linalg.solve(Gc, rhs)
    return W


@dataclass
class MaskedForecaster(Forecaster):
    allowed: np.ndarray | None = None

    def _solve(self, X, Y, M, ridge):
        return _masked_solve(X.T @ X, X.T @ Y, self.allowed, ridge)


@dataclass
class WiredVAR(IndividualVAR):
    """IndividualVAR whose pooled and per-worm fits obey a wiring mask. `wiring` is a
    callable classes -> (n, n) bool, applied to the core classes of the fitted space."""
    wiring: object = None
    label: str = "wired"
    connections: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"wired_{self.label}_" + self.pooled.name

    def fit(self, train, val, lams=(10, 100, 1000, 3000, 10000, 1e5)):
        sp = self.pooled.space
        core_names = [sp.classes[c] for c in sp.core]
        A = self.wiring(core_names)
        self.pooled.allowed = feature_mask(A, self.pooled.feats.lags)
        off = A.sum() - len(A)
        self.connections = {"classes": len(A), "inputs_per_class_mean": round(off / len(A), 2),
                            "density": round(off / (len(A) * (len(A) - 1)), 3)}
        super().fit(train, val, lams)
        self.info.update(self.connections)
        return self

    def _fit_one(self, F, Y, lam):
        return _masked_solve(F.T @ F, F.T @ Y, self.pooled.allowed, lam, prior=self.pooled.Wout)


__all__ = ["class_wiring", "shuffled_wiring", "diagonal_wiring", "feature_mask", "WiredVAR",
           "MaskedForecaster"]
