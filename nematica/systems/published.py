"""Published whole-brain models as benchmark systems.

CreamerLDS: the linear dynamical systems of Creamer, Leifer & Pillow (2024), fitted to the
Randi et al. (2023) optogenetic atlas (immobilised worms, 154 neurons, 2 Hz):

    x_{t+1} = A x_t + w_t,  w ~ N(0, Q);     y_t = x_t + v_t,  v ~ N(0, R)

Three variants from the paper: A restricted to connectome edges (connectome_constrained),
unrestricted (fully_connected), restricted to a shuffled connectome (shuffled_constrained).
Spontaneous activity = the model run with no stimulation input [L: the model as published,
inputs off]. Generated at 2 Hz, interpolated to the template worm's frame times, neurons
averaged into NEMATICA's classes (left/right pooled as for real worms), z-scored, and the
template's unlabelled classes blanked. The models produce no behaviour, so behaviour
levels are not scored. Parameters come from scripts/fetch_creamer_lds.py.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..bench.sample import BenchSample
from ..data.canonical import zscore_rows

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "data" / "external" / "creamer_lds"


def _members(names, classes):
    out = {}
    for c in classes:
        idx = [i for i, n in enumerate(names)
               if n == c or (n.startswith(c) and n[len(c):].strip("DVLR") == "" and len(n) - len(c) <= 2)]
        if idx:
            out[c] = idx
    return out


class CreamerLDS:
    def __init__(self, variant: str = "connectome_constrained", folder: Path | None = None, burn_s: float = 300.0):
        z = np.load(Path(folder or DEFAULT_DIR) / f"{variant}.npz")
        self.variant = variant
        self.A, self.Q, self.R = z["A"], z["Q"], z["R"]
        self.cells = [str(c) for c in z["cell_ids"]]
        self.rate = float(z["sample_rate"])
        self.burn = int(burn_s * self.rate)
        self.Lq = np.linalg.cholesky(self.Q + 1e-12 * np.eye(len(self.Q)))
        self.sr = np.sqrt(np.clip(np.diag(self.R), 0, None))
        self.info = {"neurons": len(self.cells), "spectral_radius": round(float(np.max(np.abs(np.linalg.eigvals(self.A)))), 4)}

    @property
    def name(self) -> str:
        return "creamer2024_" + self.variant

    def fit(self, train, val):          # published parameters: nothing is fitted here
        self.classes = train[0].classes
        self.members = _members(self.cells, self.classes)
        self.info["classes_covered"] = len(self.members)
        return self

    def simulate(self, n_steps: int, rng: np.random.Generator) -> np.ndarray:
        n = len(self.cells)
        x = np.zeros(n)
        out = np.empty((n, n_steps))
        for t in range(self.burn + n_steps):
            x = self.A @ x + self.Lq @ rng.standard_normal(n)
            if t >= self.burn:
                out[:, t - self.burn] = x + self.sr * rng.standard_normal(n)
        return out

    def generate(self, template: BenchSample, rng: np.random.Generator) -> BenchSample:
        T = template.x.shape[1]
        t_frames = np.arange(T) * template.dt
        n_steps = int(np.ceil(t_frames[-1] * self.rate)) + 2
        y = self.simulate(n_steps, rng)
        t_model = np.arange(n_steps) / self.rate
        x = np.full((len(self.classes), T), np.nan)
        for i, c in enumerate(self.classes):
            if c in self.members:
                x[i] = np.interp(t_frames, t_model, y[self.members[c]].mean(axis=0))
        x[~template.observed] = np.nan
        return BenchSample(f"{self.name}:{template.origin}", self.classes, zscore_rows(x), template.dt,
                           origin=None, behaviour={})
