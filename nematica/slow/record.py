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


def spikes_aligned(A, starts, length, k, rng):
    """The map study's spike model (`recording.spikes`, exponential nonlinearity), applied to the whole run at
    once, with bins laid out from each repeat's own start (review S-R1 finding 14) WITHOUT re-standardising
    per repeat (review S-R2 finding 1: per-repeat recording had erased between-repeat gain changes). Each
    unit is standardised and rate-normalised once over the whole run, exactly as `recording.spikes` does for
    a continuous recording; only the bin edges differ. Units are processed UNIT_BLOCK at a time with one
    generator. Returns (R, n_bins, units)."""
    hold = int(k.get("hold", 1))
    b = max(float(k["bin_steps"]), 1.0)
    L = length * hold
    n = int(np.floor(L / b + 1e-9))
    assert n > 0, "the clip is shorter than one recorded bin"      # S-R2 finding 16
    edges0 = np.arange(n + 1) * b
    out = []
    for a in range(0, A.shape[1], UNIT_BLOCK):
        H = recording.upsample(A[:, a:a + UNIT_BLOCK], hold)
        Z = recording._std(H)
        if recording.SPIKE_NONLINEARITY == "exp":
            Rr = np.exp(np.minimum(k["gain"] * Z, 50.0))
        else:
            Rr = recording.softplus(k["gain"] * Z)
        Rr = Rr / (Rr.mean(0) + 1e-12) * k["mean_count"] * recording.rate_multipliers(Rr.shape[1],
                                                                                        k.get("rate_log_sd", 0.0))
        C = np.vstack([np.zeros((1, Rr.shape[1])), np.cumsum(Rr, 0)])
        reps = []
        for s_ in starts:
            e = s_ * hold + edges0
            if e[-1] > len(Rr):
                break
            i0 = np.minimum(e.astype(int), len(Rr) - 1)
            w = (e - i0)[:, None]
            lam = np.diff(C[i0] * (1 - w) + C[i0 + 1] * w, axis=0)
            reps.append(rng.poisson(np.clip(lam, 0, None)).astype(np.float32))
        assert reps, "no repeat fits in the recording"
        out.append(np.stack(reps))
    m = min(len(o) for o in out)
    assert m == len(starts) or m > 0
    return np.concatenate([o[:m] for o in out], axis=2)


TOL = {"bins_per_tau": 0.15, "count_per_bin": 0.15, "rate_log_sd": 0.20}   # relative; noise: 0.05 absolute


def recorded_numbers(Y, rtype="spikes"):
    """The mouse's instrument function (`instrument.instrument_numbers`) on recorded repeats (R, bins, units),
    repeats as segments: what the AI recording actually looks like (review S-R2 finding 5)."""
    from ..map import instrument as INS
    R, nb, N = Y.shape
    X = np.asarray(Y, float).reshape(R * nb, N)
    dt = INS.SPIKE_BIN_S if rtype == "spikes" else 1 / 30
    ind = {"activity": X, "dt": dt, "segments": [r * nb for r in range(1, R)]}
    if rtype == "calcium":
        ind["indicator"] = "GCaMP6f"
    return INS.instrument_numbers(ind, rtype)


def within_tolerance(got, prof):
    ok = all(abs(got[x] / prof[x] - 1) <= t for x, t in TOL.items() if x in prof and np.isfinite(got.get(x, np.nan)))
    return bool(ok and abs(got["noise"] - prof["noise"]) <= 0.05)


def record_checked(A, starts, length, prof, seed=0, rounds=2):
    """Spike recording with the matched knobs corrected on the recorded repeats themselves (review S-R2
    finding 5): after each recording, the instrument numbers are measured on the repeats as for a mouse, and
    mean count, bin width and rate spread are scaled toward the mouse's values (at most `rounds` times).
    Returns (repeats, knobs, numbers measured on the final repeats, reached on the repeats)."""
    Y, k = record_repeats(A, starts, length, prof, seed=seed)
    got = recorded_numbers(Y)
    for _ in range(rounds):
        if within_tolerance(got, prof):
            break
        k = dict(k)
        k["mean_count"] *= prof["count_per_bin"] / got["count_per_bin"]
        k["bin_steps"] *= got["bins_per_tau"] / prof["bins_per_tau"]
        k["rate_log_sd"] = k.get("rate_log_sd", 0.0) * prof["rate_log_sd"] / max(got["rate_log_sd"], 1e-6)
        k["corrected"] = k.get("corrected", 0) + 1
        Y, k = record_repeats(A, starts, length, prof, seed=seed, k=k)
        got = recorded_numbers(Y)
    return Y, k, got, within_tolerance(got, prof)
