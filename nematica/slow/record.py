"""Recording repeated-input activity through a matched instrument (docs/SLOW.md, section 5).

A system's native activity is one continuous run in which the clip occupies known native steps. It is
recorded continuously through the registered spike model (nematica.map.recording, matched with
recording.match), optionally pooled in groups, and then cut into equal-length repeat windows, so that the
instrument and its noise are applied exactly as for the map study's recordings."""
from __future__ import annotations

import numpy as np

from ..map import recording


def cut_repeats(Y, starts, length, per_sample):
    """Cut recorded samples into repeats. `starts` are native steps of each repeat's start; `length` is the
    repeat's native length; per_sample is native steps per recorded sample. Returns (R, T_rec, units)."""
    n = int(np.floor(length / per_sample)) - 1        # one sample short, so rounding never drops a repeat
    out = []
    for s in starts:
        a = int(np.ceil(s / per_sample))
        if a + n <= len(Y):
            out.append(Y[a:a + n])
    return np.stack(out)


UNIT_BLOCK = 100
PREHOLD = 4      # steps are repeated this many times when a system has no measurable timescale


def record_repeats(A, starts, length, prof, rtype="spikes", seed=0, group=None, k=None, prehold=None):
    """Match (unless knobs k are given) and record native activity A (time x units), cut into repeats.
    Returns (repeats, knobs)."""
    A = np.asarray(A)
    if prehold is None:                                  # SLOW_LOG 16:45: no measurable native timescale
        from ..map.measures import tau_med
        prehold = PREHOLD if not np.isfinite(tau_med(np.asarray(A[:20000, :recording.MATCH_MIN_UNITS], float))) else 1
    if prehold > 1:
        A = np.repeat(A, prehold, axis=0)
        starts = [s * prehold for s in starts]
        length = length * prehold
    if k is None:
        # match() reads only the first MATCH_MIN_UNITS columns; passing just those gives the same knobs
        # without a float64 copy of all of A (memory, SLOW_LOG 19:20)
        k = recording.match(A[:, :recording.MATCH_MIN_UNITS], rtype, prof, seed=seed)
    # memory (SLOW_LOG 19:40): units recorded 100 at a time with one shared generator; record_matched's
    # own blocks of 400 peak at about 3 GB per 100,000 native rows. Same model, different random draws
    # from the earlier single call.
    rng = np.random.default_rng(seed + 7)
    if rtype == "spikes":
        return spikes_aligned(A, starts, length, k, rng), k
    Y = np.hstack([recording.record_matched(A[:, a:a + UNIT_BLOCK], rtype, k, rng=rng)[0]
                   for a in range(0, A.shape[1], UNIT_BLOCK)])
    if group:
        Y = recording.pool(Y, int(group), seed=seed)
    per = recording.per_sample(k, rtype)
    return cut_repeats(Y, starts, length, per), k


def spikes_aligned(A, starts, length, k, rng, block_bytes=4e8):
    """The map study's spike model (`recording.spikes`, exponential nonlinearity), applied to the whole run at
    once, with bins laid out from each repeat's own start (review S-R1 finding 14) WITHOUT re-standardising
    per repeat (review S-R2 finding 1). Each unit is standardised and rate-normalised once over the whole run,
    exactly as `recording.spikes` does for a continuous recording; only the bin edges differ.
    Memory (amendment S2, operational): the hold is applied analytically. Holding repeats each native value
    `hold` times, so the cumulative rate over held steps at held position x equals hold x (the native
    cumulative rate, linearly interpolated at x / hold); bins are integrated from that without building the
    held array. Rate multipliers are drawn once for all non-constant units (`recording.rate_multipliers`, the
    same seeded set as a single call) and units are processed in blocks sized to `block_bytes`.
    Returns (R, n_bins, units)."""
    hold = int(k.get("hold", 1))
    b = max(float(k["bin_steps"]), 1.0)
    n = int(np.floor(length * hold / b + 1e-9))
    assert n > 0, "the clip is shorter than one recorded bin"      # S-R2 finding 16
    edges0 = np.arange(n + 1) * b                                  # in held steps, from a repeat's start
    A = np.asarray(A)
    sd = A.std(0)
    cols = np.flatnonzero(sd > 1e-9)                               # `recording._std` drops constant units
    mult = recording.rate_multipliers(len(cols), k.get("rate_log_sd", 0.0))
    T = len(A)
    reps_ok = [s_ for s_ in starts if s_ * hold + edges0[-1] <= T * hold]
    assert reps_ok, "no repeat fits in the recording"
    per = max(1, int(block_bytes / (8 * 3 * (T + 1))))
    out = []
    for a in range(0, len(cols), per):
        c = cols[a:a + per]
        Z = (np.asarray(A[:, c], float) - A[:, c].mean(0)) / sd[c]
        if recording.SPIKE_NONLINEARITY == "exp":
            Rr = np.exp(np.minimum(k["gain"] * Z, 50.0))
        else:
            Rr = recording.softplus(k["gain"] * Z)
        del Z
        Rr *= (k["mean_count"] * mult[a:a + per] / (Rr.mean(0) + 1e-12))[None]
        C = np.vstack([np.zeros((1, Rr.shape[1])), np.cumsum(Rr, 0)])   # native cumulative rate
        del Rr
        reps = []
        for s_ in reps_ok:
            x = (s_ * hold + edges0) / hold                         # native position of each edge
            i0 = np.minimum(x.astype(int), T - 1)
            w = (x - i0)[:, None]
            cum = hold * (C[i0] * (1 - w) + C[i0 + 1] * w)
            lam = np.diff(cum, axis=0)
            reps.append(rng.poisson(np.clip(lam, 0, None)).astype(np.float32))
        out.append(np.stack(reps))
    return np.concatenate(out, axis=2)


TOL = {"bins_per_tau": 0.15, "count_per_bin": 0.15, "rate_log_sd": 0.20}   # relative; noise: 0.05 absolute


def scaled_min_spikes(nb_ai, nb_mouse, min_spikes=200):
    """Amendment S1 (review S-R3 B1): the mouse's spike minimum applies to the same movie time. An AI clip
    recorded at nb_ai bins has the same repeats as its mouse, so the minimum is scaled by nb_ai / nb_mouse
    (the same number of spikes per bin of movie)."""
    return float(min_spikes) * nb_ai / float(nb_mouse)


def recorded_numbers(Y, rtype="spikes", min_spikes=None):
    """The mouse's instrument function (`instrument.instrument_numbers`) on recorded repeats (R, bins, units),
    repeats as segments (review S-R2 finding 5). `min_spikes` replaces the map study's absolute 200-spike
    inclusion minimum for this call (amendment S1), so the per-bin rule matches the mouse's."""
    from ..map import instrument as INS
    R, nb, N = Y.shape
    X = np.asarray(Y, float).reshape(R * nb, N)
    dt = INS.SPIKE_BIN_S if rtype == "spikes" else 1 / 30
    ind = {"activity": X, "dt": dt, "segments": [r * nb for r in range(1, R)]}
    if rtype == "calcium":
        ind["indicator"] = "GCaMP6f"
    old = INS.MIN_SPIKES
    try:
        if min_spikes is not None:
            INS.MIN_SPIKES = min_spikes
        return INS.instrument_numbers(ind, rtype)
    finally:
        INS.MIN_SPIKES = old


def _err(got, prof):
    """Largest relative error over the toleranced numbers (noise in units of its 0.05 tolerance); inf if any
    is not finite (amendment S1, review S-R3 N8: a NaN number is not within tolerance)."""
    e = []
    for x, t in TOL.items():
        if x in prof:
            g = got.get(x, np.nan)
            if not np.isfinite(g):
                return np.inf
            e.append(abs(g / prof[x] - 1) / t)
    g = got.get("noise", np.nan)
    if not np.isfinite(g):
        return np.inf
    e.append(abs(g - prof["noise"]) / 0.05)
    return max(e)


def within_tolerance(got, prof):
    return bool(_err(got, prof) <= 1.0)


MAX_HOLD = 0          # amendment S3: every AI recording starts from the analytic knobs


def analytic_knobs(A, prof, max_hold=MAX_HOLD):
    """Amendment S3 (operational). The map study's matcher builds the held activity (rows x hold x units); for
    mice with long movie timescales and AIs with short ones the hold reaches hundreds and the array no longer
    fits in memory (the AI stage was killed twice). When the estimated hold exceeds `max_hold`, the starting
    knobs are set directly instead: bin width = the AI's native timescale / the mouse's bins per timescale
    (fractional, via an integer hold and a bin of at least one held step), mean count from the mouse's spikes
    per bin, gain 1, the mouse's rate spread. The registered check on the recorded repeats (`record_checked`)
    then corrects them and decides "reached" exactly as for matched recordings. Returns None when the
    matcher can be used."""
    from ..map.measures import tau_med
    t0 = tau_med(np.asarray(A[:20000, :recording.MATCH_MIN_UNITS], float))
    if not np.isfinite(t0) or t0 <= 0:
        t0 = 1.0
    bin_native = t0 / prof["bins_per_tau"]
    hold = int(np.ceil(1.0 / bin_native)) if bin_native < 1 else 1
    if max_hold and hold <= max_hold:
        return None
    return {"hold": hold, "bin_steps": bin_native * hold, "mean_count": prof["count_per_bin"] / (bin_native * hold),
            "gain": 1.0, "rate_log_sd": prof["rate_log_sd"], "analytic": True, "native_tau": float(t0),
            "reached": False, "achieved": {}}


def record_checked(A, starts, length, prof, seed=0, rounds=3, nb_mouse=1501):
    """Spike recording with the matched knobs corrected on the recorded repeats themselves (review S-R2
    finding 5; amendment S1 for review S-R3 B1): after each recording the instrument numbers are measured on
    the repeats as for a mouse, with the mouse's per-bin inclusion rule; then the bin width is scaled by the
    timescale error, the mean count by the count error divided by the bin change (count per bin is mean count
    x bin width), the rate spread by its error, and the gain toward the white-share target. At most `rounds`
    corrections; the best round is kept. Returns (repeats, knobs, numbers on those repeats, reached)."""
    k0 = analytic_knobs(A, prof)
    ph = 1 if k0 is not None else None
    if k0 is not None:                                 # amendment S3: the matcher would need too much memory
        Y, k = record_repeats(A, starts, length, prof, seed=seed, k=k0, prehold=1)
    else:
        Y, k = record_repeats(A, starts, length, prof, seed=seed)
    ms = lambda Y_: scaled_min_spikes(Y_.shape[1], nb_mouse)
    got = recorded_numbers(Y, min_spikes=ms(Y))
    best = (_err(got, prof), Y, k, got)
    for _ in range(rounds):
        if best[0] <= 1.0 or not np.isfinite(_err(got, prof)):
            break
        k = dict(k)
        fb = got["bins_per_tau"] / prof["bins_per_tau"]
        k["bin_steps"] *= fb
        k["mean_count"] *= prof["count_per_bin"] / got["count_per_bin"] / fb
        k["rate_log_sd"] = k.get("rate_log_sd", 0.0) * prof["rate_log_sd"] / max(got["rate_log_sd"], 1e-6)
        k["gain"] *= float(np.exp(2.0 * (got["noise"] - prof["noise"])))   # more gain, less white share
        k["corrected"] = k.get("corrected", 0) + 1
        Y, k = record_repeats(A, starts, length, prof, seed=seed, k=k, prehold=ph)
        got = recorded_numbers(Y, min_spikes=ms(Y))
        if _err(got, prof) < best[0]:
            best = (_err(got, prof), Y, k, got)
    e, Y, k, got = best
    return Y, k, got, bool(e <= 1.0)
