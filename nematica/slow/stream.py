"""Streaming recorder for the AI stage (amendment S4; SLOW_LOG, "The AI stage is paused" and after).

Some registered recordings are too large to hold in memory (tens of thousands of bins per clip x up to 60
repeats x hundreds of units). This module records and measures an AI run repeat by repeat and unit block by
unit block, never holding the whole recording:

- the spike model is `record.spikes_aligned`'s, unit by unit: each unit standardised and rate-normalised once
  over the whole native run; the hold applied analytically; bins laid out from each repeat's start;
- every (unit block, repeat) has its own seeded random stream, so a second pass regenerates identical spikes;
- pass 1 gives each unit's spike counts (for the inclusion rule), its within-repeat mean and pooled
  within-repeat SD, and the population sum over repeats (for the adaptation trend);
- the analysed units are then chosen as before (inclusion rule scaled to the clip, seeded subset of the
  mouse's size);
- pass 2 accumulates, per analysed unit, the FFT sums that `measures.repeat_autocov(center="repeat")` needs
  (sum over repeats of |F_r|^2 and the sum over repeats of F_r), for the whole clip and for each half;
- the instrument numbers come from a fixed subset of analysed units (at most 60) and at most 20 repeats,
  materialised in memory and passed to the map study's instrument function.

The measures are the same quantities as the in-memory path; `check_equivalence` below verifies it.
"""
from __future__ import annotations

import numpy as np

from ..map import recording
from . import measures as M
from . import record as Rc

BLOCK = 16                  # units per block
NUMBERS_UNITS = 60          # units used for the instrument numbers
NUMBERS_REPEATS = 20        # repeats used for the instrument numbers


class Recorder:
    """One AI run (native activity A, repeat starts, clip length in native steps) recorded with knobs k."""

    def __init__(self, A, starts, length, k, seed):
        self.A = np.asarray(A)
        self.T = len(self.A)
        self.hold = int(k.get("hold", 1))
        self.b = max(float(k["bin_steps"]), 1.0)
        self.n = int(np.floor(length * self.hold / self.b + 1e-9))
        assert self.n > 0, "the clip is shorter than one recorded bin"
        self.edges0 = np.arange(self.n + 1) * self.b
        self.starts = [s for s in starts if s * self.hold + self.edges0[-1] <= self.T * self.hold]
        assert self.starts, "no repeat fits in the recording"
        self.R = len(self.starts)
        self.k = k
        self.seed = int(seed)
        sd = self.A.std(0)
        self.cols = np.flatnonzero(sd > 1e-9)        # `recording._std` drops constant units
        self.sd = sd
        self.mult = recording.rate_multipliers(len(self.cols), k.get("rate_log_sd", 0.0))

    def _cum(self, idx):
        """Native cumulative rate for units `idx` (positions into self.cols)."""
        c = self.cols[idx]
        Z = (np.asarray(self.A[:, c], float) - self.A[:, c].mean(0)) / self.sd[c]
        if recording.SPIKE_NONLINEARITY == "exp":
            Rr = np.exp(np.minimum(self.k["gain"] * Z, 50.0))
        else:
            Rr = recording.softplus(self.k["gain"] * Z)
        del Z
        Rr *= (self.k["mean_count"] * self.mult[idx] / (Rr.mean(0) + 1e-12))[None]
        return np.vstack([np.zeros((1, Rr.shape[1])), np.cumsum(Rr, 0)])

    def _repeat(self, C, r, block_id):
        x = (self.starts[r] * self.hold + self.edges0) / self.hold
        i0 = np.minimum(x.astype(int), self.T - 1)
        w = (x - i0)[:, None]
        lam = np.diff(self.hold * (C[i0] * (1 - w) + C[i0 + 1] * w), axis=0)
        rng = np.random.default_rng([self.seed, block_id, r])
        return rng.poisson(np.clip(lam, 0, None)).astype(np.float64)

    def blocks(self, positions):
        """Unit blocks over the given positions into self.cols; block ids are fixed by position."""
        positions = np.asarray(positions)
        for bid in np.unique(positions // BLOCK):
            yield int(bid), positions[positions // BLOCK == bid]

    def counts(self, positions, repeats=None):
        """Materialise counts (repeats, n, units) for a small set of units (instrument numbers, checks)."""
        repeats = range(self.R) if repeats is None else repeats
        out = np.zeros((len(repeats), self.n, len(positions)))
        positions = np.asarray(positions)
        for bid, pos in self.blocks(positions):
            full = np.arange(bid * BLOCK, min((bid + 1) * BLOCK, len(self.cols)))
            C = self._cum(full)
            sel = np.searchsorted(full, pos)
            cols_out = np.searchsorted(positions, pos)
            for j, r in enumerate(repeats):
                out[j][:, cols_out] = self._repeat(C, r, bid)[:, sel]
        return out

    def pass1(self):
        """Per unit (all non-constant units): spikes over the first 17 repeats and over all, within-repeat
        means are implicit; pooled within-repeat SD; and the population sum over repeats (n x units)."""
        N = len(self.cols)
        first17, total, ss = np.zeros(N), np.zeros(N), np.zeros(N)
        tot = np.zeros((self.n, N), np.float32)
        for bid, pos in self.blocks(np.arange(N)):
            C = self._cum(pos)
            for r in range(self.R):
                y = self._repeat(C, r, bid)
                s = y.sum(0)
                total[pos] += s
                if r < 17:
                    first17[pos] += s
                ss[pos] += ((y - y.mean(0)) ** 2).sum(0)
                tot[:, pos] += y.astype(np.float32)
        return {"first17": first17, "total": total, "sd": np.sqrt(ss / (self.R * self.n)), "tot": tot}

    def pass2(self, positions, sd, tot, max_lag, halves=True):
        """FFT sums for the analysed units: whole clip and each half; and the adaptation-trend sums."""
        n, R = self.n, self.R
        h = n // 2
        spans = {"all": (0, n), "first": (0, h), "second": (h, n)} if halves else {"all": (0, n)}
        L = {"all": max_lag, "first": max(min(h // 4, 4000), 10), "second": max(min((n - h) // 4, 4000), 10)}
        L = {key: L[key] for key in spans}
        nfft = {key: 1 << int(np.ceil(np.log2(2 * (b - a)))) for key, (a, b) in spans.items()}
        acc = {key: {"same": np.zeros(L[key] + 1), "all": np.zeros(L[key] + 1), "units": 0} for key in spans}
        trend = np.zeros((R, 5))                      # sum y, sum y^2, sum o, sum o^2, sum y o
        for bid, pos in self.blocks(positions):
            full = np.arange(bid * BLOCK, min((bid + 1) * BLOCK, len(self.cols)))
            C = self._cum(full)
            sel = np.searchsorted(full, pos)
            G = {key: None for key in spans}
            S2 = {key: 0.0 for key in spans}
            for r in range(R):
                y = self._repeat(C, r, bid)[:, sel]
                o = (tot[:, pos].astype(float) - y) / max(R - 1, 1)
                trend[r] += [y.sum(), (y ** 2).sum(), o.sum(), (o ** 2).sum(), (y * o).sum()]
                for key, (a, b) in spans.items():
                    seg = y[a:b]
                    z = seg - seg.mean(0)
                    # pooled within-repeat SD over this span (as `repeat_autocov` computes it on the span)
                    F = np.fft.rfft(z, nfft[key], axis=0)
                    S2[key] = S2[key] + (F * F.conj()).real          # per unit, summed over repeats
                    G[key] = F if G[key] is None else G[key] + F
                    if r == 0:
                        acc[key].setdefault("ssq", {})
                    acc[key]["ssq"][bid] = acc[key]["ssq"].get(bid, 0.0) + (z ** 2).sum(0)
            for key, (a, b) in spans.items():
                m = b - a
                var = acc[key]["ssq"][bid] / (R * m)                   # pooled within-repeat variance
                keep = var > 1e-18
                s_same = np.fft.irfft(S2[key], nfft[key], axis=0)[: L[key] + 1]
                s_all = np.fft.irfft((G[key] * G[key].conj()).real, nfft[key], axis=0)[: L[key] + 1]
                nk = (m - np.arange(L[key] + 1)).astype(float)[:, None]
                acc[key]["same"] += (s_same[:, keep] / var[keep] / (R * nk)).sum(1)
                acc[key]["all"] += ((s_all[:, keep] - s_same[:, keep]) / var[keep] / (R * (R - 1) * nk)).sum(1)
                acc[key]["units"] += int(keep.sum())
        res = {}
        for key in spans:
            u = max(acc[key]["units"], 1)
            res[key] = (acc[key]["same"] / u, acc[key]["all"] / u, L[key])
        sy, syy, so, soo, syo = trend.T
        N_ = n * len(positions)
        cov = syo / N_ - (sy / N_) * (so / N_)
        sdv = np.sqrt(np.clip(syy / N_ - (sy / N_) ** 2, 0, None) * np.clip(soo / N_ - (so / N_) ** 2, 0, None))
        sim = np.where(sdv > 0, cov / np.where(sdv > 0, sdv, 1), np.nan)
        return res, sim


def measure_stream(rec, positions, tot, k0=2, halves=True):
    """The primary measures, the halves (unless halves=False) and the adaptation trend from a Recorder."""
    from scipy.stats import spearmanr
    L = int(max(min(rec.n // 4, 4000), k0 + 8))
    res, sim = rec.pass2(positions, None, tot, L, halves=halves)
    out = {}
    for key, (same, cross, Lk) in res.items():
        out[key] = M.measures_from_autocov(same, cross, k0, Lk)
    prim = {x: out["all"][x] for x in ("M1", "M2", "ti", "tl", "int_ceiling", "lock_ceiling", "no_shared", "no_locked")}
    trend = float(spearmanr(np.arange(rec.R), sim)[0]) if rec.R >= 4 and np.isfinite(sim).all() else None
    return {**prim, "max_lag": L, "M1_first_half": out["first"]["M1"] if halves else None,
            "M1_second_half": out["second"]["M1"] if halves else None, "adapt_trend": trend}


def check_equivalence(seed=0):
    """The streaming accumulation equals `measures.lag_measures` on the identical counts (materialised)."""
    from .synthetic import continuous
    A, starts = continuous(np.random.default_rng(seed), R=8, T=700, N=40, share=0.4, tau_locked=6, tau_internal=24)
    A[:, 3] = 2.0
    k = {"hold": 3, "bin_steps": 2.5, "gain": 1.0, "mean_count": 0.3, "rate_log_sd": 1.0}
    rec = Recorder(A, starts, 700, k, seed=7)
    pos = np.arange(len(rec.cols))
    p1 = rec.pass1()
    Y = rec.counts(pos)
    direct = M.lag_measures(Y, k0=2)
    T = Y.shape[1]
    h1, h2 = M.lag_measures(Y[:, : T // 2], k0=2), M.lag_measures(Y[:, T // 2:], k0=2)
    st = measure_stream(rec, pos, p1["tot"], k0=2)
    diffs = {x: abs(st[x] - direct[x]) for x in ("M1", "M2", "ti", "tl")}
    diffs["M1_first_half"] = abs(st["M1_first_half"] - h1["M1"])
    diffs["M1_second_half"] = abs(st["M1_second_half"] - h2["M1"])
    tot_direct = Y.sum(0)
    diffs["tot"] = float(np.abs(tot_direct - p1["tot"]).max())
    return diffs, direct, st


def renormalise_hold(k):
    """Keep at least one held step per bin when a correction makes the bin finer than a held step: the hold is
    raised and the mean count per held step lowered so that the expected spikes per bin are unchanged
    (Recorder clamps the bin at one held step, which had made finer-bin corrections ineffective)."""
    native_bin = k["bin_steps"] / k["hold"]
    hold = max(1, int(np.ceil(1.0 / native_bin))) if native_bin < 1 else 1
    if hold != k["hold"]:
        new_bin = native_bin * hold
        k["mean_count"] *= k["bin_steps"] / new_bin
        k["hold"], k["bin_steps"] = hold, new_bin
    return k


def record_stream(A, starts, length, prof, nb_mouse, R_mouse, n_units_mouse, seed, rounds=5, k_start=None,
                  halves=True, extra=None, max_bins=None):
    """Amendment S4: the AI recording for one mouse, streamed. Starting knobs: `record.analytic_knobs` (or
    `k_start`); then up to `rounds` corrections judged on the instrument numbers of a fixed subset of units
    and repeats (as `record.record_checked`, best round kept); then the full recording in two passes; the
    mouse's inclusion rule scaled to the clip; a seeded subset of the mouse's size; the measures.
    Returns a dict of results (measures, numbers on the analysed units, reached, knobs, sizes).
    `extra(rec, inc)`, if given (Study 3), returns a dict of further measures on the same recording and
    analysed units, stored under "extra"; it does not change anything else. `max_bins` (Study 3): a correction
    that would make the recording longer than this many bins is not made (the corrections stop there and the
    best round so far is kept); None (Study 2) means no limit."""
    from ..map import instrument as INS
    A = np.asarray(A)
    k = dict(k_start or Rc.analytic_knobs(A, prof, max_hold=0))
    pick = np.random.default_rng(seed + 1)

    def numbers(rec, positions):
        # all the given units (a 60-unit sample made the median spikes per bin too noisy for a 15% tolerance:
        # SLOW_LOG, "Instrument numbers from all units"); as many repeats as fit in about 400 MB, 2 to 20
        fit = int(4e8 / (8 * rec.n * max(len(positions), 1)))
        reps = list(range(max(2, min(NUMBERS_REPEATS, rec.R, fit))))
        Y = rec.counts(positions, reps)
        msp = Rc.scaled_min_spikes(rec.n, nb_mouse) * len(reps) / max(R_mouse, 1)
        return Rc.recorded_numbers(Y, min_spikes=msp)

    rec = Recorder(A, starts, length, k, seed)
    probe = np.arange(len(rec.cols))
    got = numbers(rec, probe)
    best = (Rc._err(got, prof), dict(k), got)
    too_long = lambda kk: max_bins is not None and np.floor(length * kk.get("hold", 1) / max(kk["bin_steps"], 1.0)) > max_bins
    for _ in range(rounds):
        if best[0] <= 1.0:
            break
        if not np.isfinite(got.get("bins_per_tau", np.nan)) or not np.isfinite(got.get("count_per_bin", np.nan)):
            k["bin_steps"] *= 0.5                      # no measurable timescale yet: finer bins, then retry
            k["mean_count"] *= 2.0
            k["corrected"] = k.get("corrected", 0) + 1
            k = renormalise_hold(k)
            if too_long(k):
                k = dict(best[1])
                k["stopped_at_max_bins"] = True
                best = (best[0], dict(k), best[2])
                break
            rec = Recorder(A, starts, length, k, seed)
            got = numbers(rec, probe)
            continue
        fb = got["bins_per_tau"] / prof["bins_per_tau"]
        k["bin_steps"] *= fb
        k["mean_count"] *= prof["count_per_bin"] / got["count_per_bin"] / fb
        k["rate_log_sd"] = k.get("rate_log_sd", 0.0) * prof["rate_log_sd"] / max(got["rate_log_sd"], 1e-6)
        k["gain"] *= float(np.exp(4.0 * (got["noise"] - prof["noise"])))
        k["corrected"] = k.get("corrected", 0) + 1
        k = renormalise_hold(k)
        if too_long(k):
            best[1]["stopped_at_max_bins"] = True
            break
        rec = Recorder(A, starts, length, k, seed)
        got = numbers(rec, probe)
        if Rc._err(got, prof) < best[0]:
            best = (Rc._err(got, prof), dict(k), got)
    k = best[1]
    rec = Recorder(A, starts, length, k, seed)
    p1 = rec.pass1()
    msp = Rc.scaled_min_spikes(rec.n, nb_mouse)
    rate_ok = p1["total"] / (rec.R * rec.n * INS.SPIKE_BIN_S) >= INS.MIN_RATE_HZ
    inc = np.flatnonzero((p1["sd"] > 1e-9) & (p1["first17"] >= msp) & rate_ok)
    if n_units_mouse < len(inc):
        inc = np.sort(np.random.default_rng(seed).choice(inc, n_units_mouse, replace=False))
    if len(inc) < 2:
        return {"error": "fewer than 2 units pass inclusion", "knobs": _plain(k), "reached": False}
    got = numbers(rec, inc)
    reached = Rc.within_tolerance(got, prof) and len(inc) >= n_units_mouse
    meas = measure_stream(rec, inc, p1["tot"], halves=halves)
    if extra is not None:
        meas["extra"] = extra(rec, inc)
    return {**meas, "recorded_bins": int(rec.n), "repeats_used": int(rec.R), "units_used": int(len(inc)),
            "bin_steps": float(k["bin_steps"] / k.get("hold", 1)), "knobs": _plain(k),
            "numbers_on_repeats": {x: got.get(x) for x in prof}, "reached": bool(reached)}


def _plain(k):
    return {a: (float(v) if isinstance(v, (int, float, np.floating, np.integer)) and not isinstance(v, bool) else v)
            for a, v in k.items() if isinstance(v, (int, float, bool, np.floating, np.integer))}
