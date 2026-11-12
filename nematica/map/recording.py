"""Recording models (docs/MAP.md, amendment 2): an artificial network (or a synthetic system) recorded the way
a brain preparation was. Units are standardised and multiplied by a registered gain before rectification, so
the share of signal that survives does not depend on a network's native activation scale.

`match_calcium` and `match_spikes` set the knobs from a preparation's own summary numbers (the registered
matching rule); the knobs are then swept around the matched values for the mismatch budget.
"""
from __future__ import annotations

import numpy as np

GAIN = 1.0


def softplus(x):
    return np.logaddexp(0, x)


def _std(A):
    """Standardise units; units that are constant in native activity are dropped (amendment 3: they would
    otherwise become pure Poisson units)."""
    A = np.asarray(A, float)
    sd = A.std(0)
    A = A[:, sd > 1e-9]
    return (A - A.mean(0)) / sd[sd > 1e-9]


def hold(A, k):
    """Amendment 3: an AI's native steps held for k sub-steps each (piecewise constant), so recording knobs
    finer than one native step can be reached; k = ceil(HOLD_TARGET / native tau_med) for fast networks."""
    k = max(int(k), 1)
    return np.repeat(np.asarray(A, float), k, axis=0) if k > 1 else np.asarray(A, float)


HOLD_TARGET = 8.0


def native(A, rng=None):
    return np.asarray(A, float)


def calcium(A, decay=8.0, frame=2, snr=4.0, gain=None, rng=None):
    """Standardise, rectify (softplus of gain x), convolve with an exponential indicator kernel (decay in
    native steps), keep every `frame`-th step, add white noise at the given signal-to-noise ratio (SD of
    signal / SD of noise, per unit)."""
    rng = rng or np.random.default_rng(0)
    gain = GAIN if gain is None else gain
    R = softplus(gain * _std(A))
    k = np.exp(-np.arange(int(6 * max(decay, 0.2)) + 1) / max(decay, 1e-3))
    k /= k.sum()
    T = len(R)
    F = np.fft.irfft(np.fft.rfft(R, n=2 * T, axis=0) * np.fft.rfft(k, n=2 * T)[:, None], axis=0)[:T]
    if frame > 1:                                       # fractional frames: sample by linear interpolation
        pos = np.arange(0, T - 1, frame)
        i0 = pos.astype(int)
        w = (pos - i0)[:, None]
        F = F[i0] * (1 - w) + F[np.minimum(i0 + 1, T - 1)] * w
    sd = F.std(0) + 1e-12
    return F + rng.standard_normal(F.shape) * sd / snr


def spikes(A, mean_count=0.5, bin_steps=1, gain=None, rng=None):
    """Standardise, rectify (softplus of gain x), scale each unit to a mean Poisson count per native step,
    integrate the rate over bins of `bin_steps` native steps (fractional allowed: the cumulative rate is
    interpolated at bin edges) and draw each bin's count from a Poisson distribution."""
    rng = rng or np.random.default_rng(0)
    gain = GAIN if gain is None else gain
    R = softplus(gain * _std(A))
    R = R / (R.mean(0) + 1e-12) * mean_count
    b = max(float(bin_steps), 1.0)
    C = np.vstack([np.zeros((1, R.shape[1])), np.cumsum(R, 0)])
    edges = np.arange(0, len(R) + 1e-9, b)
    i0 = np.minimum(edges.astype(int), len(R) - 1)
    w = (edges - i0)[:, None]
    lam = np.diff(C[i0] * (1 - w) + C[i0 + 1] * w, axis=0)
    return rng.poisson(np.clip(lam, 0, None)).astype(float)


RECORDINGS = {"native": native, "calcium": calcium, "spikes": spikes}


def _reached(target, got, tol=0.1, key=None):
    """Within 10% of the target; the white-noise share (a proportion) within 0.05 absolute."""
    if not np.isfinite(got):
        return False
    return bool(abs(got - target) <= (0.05 if key == "noise" else tol * abs(target)))


def match_calcium(A, prep, rng=None, n_iter=14):
    """Registered rule (amendments 2 and 3). `prep`: `decay_over_tau` (indicator decay, the 1/e constant of
    exp(-n/decay); half-decay times from papers are divided by ln 2, over the recorded tau_med),
    `frames_per_tau`, `noise` (median white-noise share). Fast networks are first held (hold) so that their
    native tau_med spans HOLD_TARGET sub-steps. Returns the knobs, the hold factor, what was reached and a
    `reached` flag (all three within 10%). A network that cannot reach them is reported, not mapped."""
    from .measures import noise_fraction, tau_med
    rng = rng or np.random.default_rng(0)
    t0 = tau_med(_std(A))
    k = int(np.ceil(HOLD_TARGET / t0)) if np.isfinite(t0) and t0 < HOLD_TARGET else 1
    H = hold(A, k)
    lo, hi = 0.05, 2000.0
    for _ in range(n_iter):
        d = np.sqrt(lo * hi)
        if d / tau_med(calcium(H, decay=d, frame=1, snr=1e6, rng=rng)) < prep["decay_over_tau"]:
            lo = d
        else:
            hi = d
    d = np.sqrt(lo * hi)
    t_rec = tau_med(calcium(H, decay=d, frame=1, snr=1e6, rng=rng))
    frame = max(t_rec / prep["frames_per_tau"], 1.0)
    lo, hi = 0.3, 100.0
    for _ in range(n_iter):
        s_ = np.sqrt(lo * hi)
        nf = np.median(noise_fraction(calcium(H, decay=d, frame=frame, snr=s_, rng=rng)))
        if nf > prep["noise"]:
            lo = s_
        else:
            hi = s_
    snr = float(np.sqrt(lo * hi))
    for _ in range(3):                                   # refine decay and frame on the noisy recording
        Y = calcium(H, decay=d, frame=frame, snr=snr, rng=rng)
        t_y = tau_med(Y)
        frame = max(frame * t_y / prep["frames_per_tau"], 1.0)
        d = d * prep["decay_over_tau"] / (d / frame / max(tau_med(calcium(H, decay=d, frame=frame, snr=snr, rng=rng)), 1e-9))
    Y = calcium(H, decay=d, frame=frame, snr=snr, rng=rng)
    t_y = tau_med(Y)
    got = {"decay_over_tau": d / frame / t_y, "frames_per_tau": t_y, "noise": float(np.median(noise_fraction(Y)))}
    ok = all(_reached(prep[x], got[x], key=x) for x in got)
    return {"decay": float(d), "frame": float(frame), "snr": snr, "hold": k, "native_tau": float(t0),
            "achieved": got, "reached": ok}


def match_spikes(A, prep, rng=None, n_iter=12, rounds=3):
    """Registered rule (amendments 2 and 3). `prep` (real data binned at 20 ms): `bins_per_tau`,
    `count_per_bin`, `noise`. Fast networks are held first. Bin and gain are iterated jointly, measuring the
    timescale on the recorded counts. Returns knobs, hold, achieved numbers and `reached` (within 10%)."""
    from .measures import noise_fraction, tau_med
    rng = rng or np.random.default_rng(0)
    t0 = tau_med(_std(A))
    k = int(np.ceil(HOLD_TARGET / t0)) if np.isfinite(t0) and t0 < HOLD_TARGET else 1
    H = hold(A, k)
    g, b = 3.0, 1.0
    for _ in range(rounds):
        mc = prep["count_per_bin"] / b
        t_rec = tau_med(spikes(H, mean_count=mc, bin_steps=1.0, gain=g, rng=rng))   # in native sub-steps
        b = max(t_rec / prep["bins_per_tau"], 1.0)
        mc = prep["count_per_bin"] / b
        lo, hi = 0.1, 30.0
        for _ in range(n_iter):
            g = np.sqrt(lo * hi)
            nf = np.median(noise_fraction(spikes(H, mean_count=mc, bin_steps=b, gain=g, rng=rng)))
            if nf > prep["noise"]:
                lo = g
            else:
                hi = g
        g = float(np.sqrt(lo * hi))
    Y = spikes(H, mean_count=mc, bin_steps=b, gain=g, rng=rng)
    got = {"bins_per_tau": tau_med(Y), "count_per_bin": float(Y.mean()), "noise": float(np.median(noise_fraction(Y)))}
    ok = all(_reached(prep[x], got[x], key=x) for x in got)
    return {"bin_steps": float(b), "mean_count": float(mc), "gain": g, "hold": k, "native_tau": float(t0),
            "achieved": got, "reached": ok}


def record_matched(A, rtype, knobs, rng=None):
    """Record A with matched knobs (including the hold factor)."""
    H = hold(A, knobs.get("hold", 1))
    if rtype == "calcium":
        return calcium(H, decay=knobs["decay"], frame=knobs["frame"], snr=knobs["snr"], rng=rng)
    if rtype == "spikes":
        return spikes(H, mean_count=knobs["mean_count"], bin_steps=knobs["bin_steps"], gain=knobs["gain"], rng=rng)
    return native(H)
