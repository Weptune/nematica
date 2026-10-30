"""Kunert et al. 2014 connectome model (as in the Neural Interactome), fast integrator.

Graded-potential model of 279 neurons with gap junctions and chemical synapses on the
White/Varshney connectome:

    C dV/dt = -Gc (V - Ec) - sum_j Gg_ij (V_i - V_j) - sum_j Gs_ij s_j (V_i - E_j) + I_i(t)
    ds/dt   = ar * phi(V) * (1 - s) - ad * s,   phi(V) = 1 / (1 + exp(-B (V - Vth)))

Vth is the equilibrium threshold of Kunert 2014 (solved from the linear system at the
synaptic equilibrium). Integration: LSODA (the equations are stiff); simple fixed-step
schemes were either unstable or inaccurate relative to the small voltage fluctuations.

Provenance: connectivity [M] (EM counts), every parameter and the model form [A].
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import linalg
from scipy.integrate import solve_ivp

DATA = Path(__file__).resolve().parents[2] / "data_assets" / "kunert2014"

GC, CAP, EC, AR, AD, BETA = 0.1, 0.015, -35.0, 1 / 1.5, 5 / 1.5, 0.125
E_INH = -48.0


@dataclass
class KunertModel:
    names: list[str]
    Gg: np.ndarray
    Gs: np.ndarray
    E: np.ndarray
    Vth: np.ndarray

    @classmethod
    def load(cls, data: Path = DATA) -> "KunertModel":
        names = ast.literal_eval((data / "neuron_names.txt").read_text())
        Gg = np.load(data / "Gg.npy").astype(float)
        Gs = np.load(data / "Gs.npy").astype(float)
        n = len(names)
        E = E_INH * np.load(data / "emask.npy").reshape(n).astype(float)
        seq = round(AR / (AR + 2 * AD), 4)
        Ggd = Gg - np.diag(np.diag(Gg))
        Gsd = seq * Gs
        Gsd = Gsd - np.diag(np.diag(Gsd))
        M = -GC * np.eye(n) - (np.diag(Ggd.sum(1)) - Ggd) - np.diag(Gsd.sum(1))
        b = -(GC * EC * np.ones(n)) - Gs @ (seq * E)
        Vth = linalg.solve(M, b)
        return cls(names, Gg, Gs, E, Vth)

    @property
    def n(self) -> int:
        return len(self.names)

    def rhs(self, V: np.ndarray, S: np.ndarray, I: np.ndarray):
        gap = self.Gg.sum(1) * V - self.Gg @ V
        gs = self.Gs * S[None, :]
        syn = gs.sum(1) * V - gs @ self.E
        dV = (-(GC * (V - EC) + gap + syn) + I) / CAP
        phi = 1.0 / (1.0 + np.exp(-BETA * (V - self.Vth)))
        dS = AR * phi * (1 - S) - AD * S
        return dV, dS

    def simulate(self, duration_s: float, dt: float = 0.01, drive=None, record_every_s: float = 0.05,
                 seed: int = 0, v0=None, s0=None, cg_tol: float = 1e-8, cg_max: int = 50):
        """Integrate and return (t, V - Vth), sampled every `record_every_s` seconds.

        Linearly implicit Euler: each step solves
            (I + dt/C (Gc I + L_gap + diag(Gs s))) V' = V + dt/C (Gc Ec + Gs (s * E) + I(t))
        with conjugate gradients (the matrix is symmetric positive definite), warm-started
        from the previous voltage. Synaptic gating uses the exact exponential update for
        fixed voltage. drive(t) -> current vector (length n), or None.
        """
        rng = np.random.default_rng(seed)
        n = self.n
        V = self.Vth + rng.uniform(-1, 1, n) if v0 is None else np.array(v0, float)
        S = rng.uniform(0, 0.1, n) if s0 is None else np.array(s0, float)
        G = self.Gg - np.diag(np.diag(self.Gg))
        G = 0.5 * (G + G.T)                                   # gap junctions are symmetric
        deg = G.sum(1)
        k = dt / CAP
        steps = int(round(duration_s / dt))
        every = max(1, int(round(record_every_s / dt)))
        out_t, out_v = [], []
        for step in range(steps):
            t = step * dt
            I = 0.0 if drive is None else drive(t)
            g = self.Gs @ S
            diag = 1.0 + k * (GC + deg + g)
            rhs = V + k * (GC * EC + self.Gs @ (S * self.E) + I)
            # matrix-free CG on A x = rhs, A x = diag * x - k * G x, Jacobi preconditioner
            x = V.copy()
            r = rhs - (diag * x - k * (G @ x))
            z = r / diag
            p = z.copy()
            rz = r @ z
            bnorm = np.linalg.norm(rhs)
            for _ in range(cg_max):
                Ap = diag * p - k * (G @ p)
                alpha = rz / (p @ Ap)
                x += alpha * p
                r -= alpha * Ap
                if np.linalg.norm(r) <= cg_tol * bnorm:
                    break
                z = r / diag
                rz_new = r @ z
                p = z + (rz_new / rz) * p
                rz = rz_new
            V = x
            phi = 1.0 / (1.0 + np.exp(-BETA * (V - self.Vth)))
            rate = AR * phi + AD
            s_inf = AR * phi / rate
            S = s_inf + (S - s_inf) * np.exp(-rate * dt)
            if step % every == 0:
                out_t.append(t)
                out_v.append(V - self.Vth)
        return np.array(out_t), np.array(out_v).T


def coloured_noise_drive(n: int, amplitude: float, tau_s: float, duration_s: float,
                         grid_s: float = 0.01, seed: int = 0):
    """Independent Ornstein-Uhlenbeck current into every neuron (driving condition D1),
    precomputed on a grid and linearly interpolated."""
    rng = np.random.default_rng(seed)
    steps = int(np.ceil(duration_s / grid_s)) + 2
    a = np.exp(-grid_s / tau_s)
    x = np.empty((steps, n))
    x[0] = rng.standard_normal(n)
    noise = rng.standard_normal((steps, n)) * np.sqrt(1 - a * a)
    for k in range(1, steps):
        x[k] = a * x[k - 1] + noise[k]
    x *= amplitude

    def drive(t):
        f = t / grid_s
        i = min(int(f), steps - 2)
        w = f - i
        return (1 - w) * x[i] + w * x[i + 1]
    return drive
