"""A spiking network recorded like the atlas (pre-registered 7 Nov 2026, README "A spiking network on the
same tests, and what makes neurons tire").

120 leaky integrate-and-fire neurons (96 excitatory, 24 inhibitory, Dale's law), 5 ms steps, simulated
for many individuals at once. Variants add slow (10 min) processes:
  S0  plain
  S1  spike-frequency adaptation: every spike adds a hyperpolarising current (decays over 10 min)
  S2  use-dependent fatigue: rate above 30 Hz builds a hyperpolarising current (decays over 10 min)
  S3  use-dependent synaptic depletion: rate above 30 Hz depletes outgoing synapses (recover over 10 min)
  S4  use-dependent gain fatigue: as S2, but it divides the neuron's synaptic, poke and noise input by
      (1 + f) instead of subtracting a current (added 8 Nov after S2x4 gave the opposite sign)
  S5  use-dependent refractoriness: the S2 build-up adds floor(20 f) steps of refractoriness
  S6  calibration: only the poke's own input weakens with use (channel desensitisation)
Readout per 0.5 s frame: firing rate through a 1.5 s calcium-like decay, scaled, plus measurement noise.
"""
from __future__ import annotations

import numpy as np

from . import annlab as L

N, NE = 120, 96
DT, TM, TS, REF = 0.005, 0.02, 0.01, 2
MU, SIG, J, G, P = 0.8, 0.3, 0.15, 4.0, 0.1
STEPS_PER_FRAME = 100                      # 0.5 s frames
SLOW = 600.0                               # 10 min recovery
TAU_R, THETA = 1.0, 30.0                   # rate estimate (s) and the gate (Hz)
POKE = 1.5                                 # current, in thresholds
HOLD = 4                                   # frames (2 s)
CA = 1.5                                   # calcium-like decay of the readout (s)
DA = 1.4e-5                                # S1: per-spike adaptation increment
KF = 0.005                                 # S2: fatigue gain per Hz above the gate per second
KD = 0.008                                 # S3: depletion rate per Hz above the gate per second
LEAD, EVERY = 230, L.EVERY


def base_weights(seed=0):
    rng = np.random.default_rng(seed)
    W = (rng.random((N, N)) < P) * rng.lognormal(0.0, 0.5, (N, N))
    np.fill_diagonal(W, 0.0)
    W[:, :NE] *= J
    W[:, NE:] *= -G * J
    return W


def individuals(W0, n_ind, sigma=0.3, seed=1000):
    out = np.empty((n_ind, N, N))
    for i in range(n_ind):
        g = np.random.default_rng(seed + i)
        out[i] = W0 * np.maximum(0.0, 1.0 + sigma * g.standard_normal(W0.shape))
    return out


def simulate(Wb, kick_targets, variant="S0", frames=L.FRAMES, burn=400, seed=0):
    """Wb: (B, N, N); kick_targets: (B, frames) int, -1 where no poke. Returns y (B, frames, N)."""
    rng = np.random.default_rng(seed)
    B = Wb.shape[0]
    v = rng.random((B, N))
    s = np.zeros((B, N))
    ref = np.zeros((B, N))
    r = np.zeros((B, N))                       # rate estimate, Hz
    a = np.zeros((B, N))                       # S1 adaptation / S2 fatigue current
    x = np.ones((B, N))                        # S3 synaptic resources
    ca = np.zeros((B, N))
    d = np.zeros((B, N))                       # S6 channel desensitisation
    y = np.empty((B, frames, N))
    dec_s, dec_r, dec_slow = np.exp(-DT / TS), np.exp(-DT / TAU_R), np.exp(-DT / SLOW)
    a_ca = np.exp(-0.5 / CA)
    noise_scale = SIG * np.sqrt(TM / DT)
    bi = np.arange(B)
    for fr in range(-burn, frames):
        poke = np.zeros((B, N))
        if fr >= 0:
            tg = kick_targets[:, fr]
            on = tg >= 0
            poke[bi[on], tg[on]] = POKE
        count = np.zeros((B, N))
        for _ in range(STEPS_PER_FRAME):
            if variant == "S6":
                d = d * dec_slow + 0.15 * DT * (poke > 0)
                I = MU + s + poke * np.clip(1.0 - d, 0.0, 1.0) + noise_scale * rng.standard_normal((B, N))
            elif variant == "S4":
                I = MU + (s + poke + noise_scale * rng.standard_normal((B, N))) / (1.0 + a)
            else:
                I = MU + s + poke - a + noise_scale * rng.standard_normal((B, N))
            v = v + DT / TM * (-v + I)
            v[ref > 0] = 0.0
            ref -= 1
            sp = v > 1.0
            v[sp] = 0.0
            ref[sp] = REF + (np.floor(20.0 * a[sp]) if variant == "S5" else 0)
            spf = sp.astype(float)
            count += spf
            r = r * dec_r + spf / TAU_R
            if variant == "S1":
                a = a * dec_slow + DA * spf
            elif variant in ("S2", "S4", "S5"):
                a = a * dec_slow + KF * np.maximum(r - THETA, 0.0) * DT
            out = spf
            if variant == "S3":
                x = x + (1.0 - x) * (1.0 - dec_slow) - KD * np.maximum(r - THETA, 0.0) * DT * x
                x = np.clip(x, 0.0, 1.0)
                out = spf * x
            s = s * dec_s + np.einsum("bij,bj->bi", Wb, out)
        rate = count / 0.5
        ca = a_ca * ca + (1.0 - a_ca) * rate
        if fr >= 0:
            y[:, fr] = ca / 20.0 + 0.1 * rng.standard_normal((B, N))
    return y


def recordings(variant, n_ind=113, seed=0, sigma=0.3, batch=40, poke=True, burn=400):
    """Atlas-style recordings (PumpProbe) of n_ind individuals, poked as the lab brains are."""
    W0 = base_weights(seed)
    Wall = individuals(W0, n_ind, sigma)
    hidden = L.design(N, np.random.default_rng(200))
    rng = np.random.default_rng(7)
    obs_all, kicks_all = [], []
    for _ in range(n_ind):
        obs = (rng.random(N) < 0.5) & ~hidden
        targets = np.flatnonzero(obs)
        kicks = {f: int(rng.choice(targets)) for f in range(LEAD, L.FRAMES - L.WIN, EVERY)}
        if not poke:
            kicks = {}
        obs_all.append(obs)
        kicks_all.append(kicks)
    recs = []
    for b0 in range(0, n_ind, batch):
        idx = list(range(b0, min(n_ind, b0 + batch)))
        kt = -np.ones((len(idx), L.FRAMES), int)
        for row, i in enumerate(idx):
            for f, j in kicks_all[i].items():
                kt[row, f:f + HOLD] = j
        y = simulate(Wall[idx], kt, variant, seed=seed + b0, burn=burn)
        for row, i in enumerate(idx):
            recs.append(L.as_pumpprobe(y[row], obs_all[i], kicks_all[i], f"spk{variant}_{i:03d}"))
    return recs
