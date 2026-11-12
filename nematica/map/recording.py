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


def _err(prep, got):
    """Largest error relative to tolerance (<= 1 means reached)."""
    e = [abs(got[x] - prep[x]) / (0.05 if x == "noise" else 0.1 * abs(prep[x])) for x in got]
    return max(e) if all(np.isfinite(e)) else np.inf


MATCH_MIN_UNITS = 200          # amendment 4: matching uses up to this many units (all if fewer) and
MATCH_MIN_TAU = 400            # at least this many recorded timescales; the timescale estimate on sparse
                               # counts at real noise levels varies by about 10% at this size (40% at 60
                               # units and 100 timescales)


def _reached(target, got, tol=0.1, key=None):
    """Within 10% of the target; the white-noise share (a proportion) within 0.05 absolute."""
    if not np.isfinite(got):
        return False
    return bool(abs(got - target) <= (0.05 if key == "noise" else tol * abs(target)))


def hold_factor(t0, target_per_tau=0.0):
    """Amendment 4 (F6): hold so the native tau_med spans at least HOLD_TARGET sub-steps and at least twice the
    target samples per tau, for fast and slow networks alike, so any target finer than a native step is
    reachable. Returns 1 when no hold is needed."""
    if not np.isfinite(t0) or t0 <= 0:
        return 1
    need = max(HOLD_TARGET, 2.0 * target_per_tau)
    return max(int(np.ceil(need / t0)), 1)


def _segments_record(fn, A, segments, rng, **kw):
    """Amendment 4 (F11): record each segment separately (kernels, interpolation and bins never cross a
    segment boundary). `segments` are start indices in native steps (0 implied). Returns the concatenated
    recording and the start indices of each recorded segment."""
    if not segments:
        return fn(A, rng=rng, **kw), []
    cuts = sorted(set([0] + [int(x) for x in segments if 0 < x < len(A)] + [len(A)]))
    parts, starts, n = [], [], 0
    for a, b in zip(cuts[:-1], cuts[1:]):
        Y = fn(A[a:b], rng=rng, **kw)
        if len(Y):
            if n:
                starts.append(n)
            parts.append(Y)
            n += len(Y)
    return np.vstack(parts), starts


def match_calcium(A, prep, rng=None, n_iter=14, rounds=8, seed=0):
    """Registered rule (amendments 2 to 4). `prep`: `decay_over_tau` (indicator decay as the 1/e constant over
    the recorded tau_med; half-decay times from papers are divided by ln 2), `frames_per_tau`, `noise` (median
    white-noise share). The network is held (hold_factor); decay is found by bisection on the noiseless trace;
    then up to `rounds` rounds of: SNR bisection to the noise target, multiplicative frame and decay updates
    from the achieved values, stopping once all three are reached. If the frame would fall below one sub-step
    the hold factor is raised. Every evaluation uses the same noise seed (common random numbers), so the
    search is deterministic; the best round is returned. `reached`: all three within tolerance (10%; noise
    0.05 absolute). Callers pass at most MATCH_MIN_UNITS units and at least MATCH_MIN_TAU timescales."""
    from .measures import noise_fraction, tau_med
    R_ = lambda: np.random.default_rng(seed)
    t0 = tau_med(_std(A))
    k = hold_factor(t0, prep["frames_per_tau"])
    H = hold(A, k)
    rec = lambda d, f, s_: calcium(H, decay=d, frame=f, snr=s_, rng=R_())
    lo, hi = 0.05, 4000.0
    for _ in range(n_iter):
        d = np.sqrt(lo * hi)
        lo, hi = (d, hi) if d / tau_med(rec(d, 1, 1e6)) < prep["decay_over_tau"] else (lo, d)
    d = np.sqrt(lo * hi)
    frame = max(tau_med(rec(d, 1, 1e6)) / prep["frames_per_tau"], 1.0)
    snr, got, ok, best = 4.0, {}, False, None
    for _ in range(rounds):
        lo, hi = 0.2, 200.0
        for _ in range(n_iter):
            s_ = np.sqrt(lo * hi)
            nf = np.median(noise_fraction(rec(d, frame, s_)))
            lo, hi = (s_, hi) if nf > prep["noise"] else (lo, s_)
        snr = float(np.sqrt(lo * hi))
        Y = rec(d, frame, snr)
        t_y = tau_med(Y)
        got = {"decay_over_tau": d / frame / t_y, "frames_per_tau": t_y, "noise": float(np.median(noise_fraction(Y)))}
        state = {"decay": float(d), "frame": float(frame), "snr": snr, "hold": k, "achieved": got}
        if best is None or _err(prep, got) < _err(prep, best["achieved"]):
            best = state
        if _err(prep, got) <= 1:
            break
        d = d * prep["decay_over_tau"] / got["decay_over_tau"]
        frame = frame * t_y / prep["frames_per_tau"]
        if frame < 1.0:                                  # the recorded timescale is too short: hold more
            f = int(np.ceil(1.5 / frame))
            k, H, d, frame = k * f, hold(A, k * f), d * f, frame * f
            rec = lambda d, f_, s_, H=H: calcium(H, decay=d, frame=f_, snr=s_, rng=R_())
    return {**best, "native_tau": float(t0), "reached": bool(_err(prep, best["achieved"]) <= 1)}


def match_spikes(A, prep, rng=None, n_iter=14, rounds=8, seed=0):
    """Registered rule (amendments 2 to 4). `prep` (real data binned at 20 ms): `bins_per_tau`,
    `count_per_bin`, `noise`. The network is held (hold_factor). Up to `rounds` rounds of: gain bisection to
    the noise target at the current bin, then a multiplicative bin update from the achieved bins per tau of the
    recorded counts (F6), with the mean count per sub-step set so the expected count per bin is the target;
    stopping once all three are reached. If the bin would fall below one sub-step the hold factor is raised.
    Common random numbers and best round as in match_calcium. `reached`: all three within tolerance."""
    from .measures import noise_fraction, tau_med
    R_ = lambda: np.random.default_rng(seed)
    t0 = tau_med(_std(A))
    k = hold_factor(t0, prep["bins_per_tau"])
    H = hold(A, k)
    g = 3.0
    b = max(tau_med(spikes(H, mean_count=1.0, bin_steps=1.0, gain=g, rng=R_())) / prep["bins_per_tau"], 1.0)
    got, best = {}, None
    for _ in range(rounds):
        mc = prep["count_per_bin"] / b
        lo, hi = 0.05, 40.0
        for _ in range(n_iter):
            g = np.sqrt(lo * hi)
            nf = np.median(noise_fraction(spikes(H, mean_count=mc, bin_steps=b, gain=g, rng=R_())))
            lo, hi = (g, hi) if nf > prep["noise"] else (lo, g)
        g = float(np.sqrt(lo * hi))
        Y = spikes(H, mean_count=mc, bin_steps=b, gain=g, rng=R_())
        t_y = tau_med(Y)
        got = {"bins_per_tau": t_y, "count_per_bin": float(Y.mean()), "noise": float(np.median(noise_fraction(Y)))}
        state = {"bin_steps": float(b), "mean_count": float(mc), "gain": g, "hold": k, "achieved": got}
        if best is None or _err(prep, got) < _err(prep, best["achieved"]):
            best = state
        if _err(prep, got) <= 1 or not np.isfinite(t_y):
            break
        b = b * t_y / prep["bins_per_tau"]
        if b < 1.0:                                      # the recorded timescale is too short: hold more
            f = int(np.ceil(1.5 / b))
            k, H, b = k * f, hold(A, k * f), b * f
    return {**best, "native_tau": float(t0), "reached": bool(_err(prep, best["achieved"]) <= 1)}


def record_matched(A, rtype, knobs, rng=None, segments=None, interp=False):
    """Record A with matched knobs (including the hold factor), segment by segment (F11). Returns the recording
    and its segment starts. `interp=True` replaces the hold by linear interpolation (F15 sensitivity)."""
    k = knobs.get("hold", 1)
    A = np.asarray(A, float)
    if k > 1 and interp:
        t = np.arange(len(A) * k) / k
        H = np.column_stack([np.interp(t, np.arange(len(A)), A[:, j]) for j in range(A.shape[1])])
    else:
        H = hold(A, k)
    seg = [int(x) * k for x in (segments or [])]
    if rtype == "calcium":
        return _segments_record(calcium, H, seg, rng, decay=knobs["decay"], frame=knobs["frame"], snr=knobs["snr"])
    if rtype == "spikes":
        return _segments_record(spikes, H, seg, rng, mean_count=knobs["mean_count"], bin_steps=knobs["bin_steps"],
                                gain=knobs["gain"])
    return native(H), seg
