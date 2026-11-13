"""One AI recorded at one preparation's instrument (docs/MAP.md, amendments 4 and 10), the same code for the
fake-brain controls and the real AIs.

`ai_at_prep(instances, rtype, inst, ...)`: `instances` is a list of activity arrays (time x units), one per
network instance (a seed, a checkpoint or a set of text segments). The network is matched once, on the
first instance (registered call `recording.match`), and the same knobs record every instance; each
instance gives `recs_per_instance` recordings with different noise seeds. Returns the mean values, the
replicates (each tagged with its instance, for the hierarchical bootstrap), whether matching reached its
targets, and the mismatch budget:
  for each matched knob swept x/÷1.5, the change of each measure with common random numbers (the same
  recording seed and unit draws as the base recording), mean over 2 seeds, minus the seed floor (half the
  mean absolute difference between the base recordings of two seeds, a conservative estimate of how much
  noise alone moves a value; amendment 10, review 13 item 6), floored at 0.
"""
from __future__ import annotations

import numpy as np

from . import measures, recording

KNOBS = {"calcium": ("decay", "frame", "snr"), "spikes": ("bin_steps", "mean_count", "gain")}


def _meas(Y, seed, seg, n_draws, tau_floor):
    r = measures.measure_matched(Y, seed=seed, n_draws=n_draws, segments=seg, tau_floor=tau_floor)
    return {m: r.get(m, np.nan) for m in measures.MEASURES} | {"tau_med": r.get("tau_med", np.nan),
                                                             "resolution_limited": r.get("resolution_limited")}


def ai_at_prep(instances, rtype, inst, segments=None, recs_per_instance=4, n_draws=20, seed=0,
               hold_mult=1, interp=False, tau_floor=measures.TAU_FLOOR, budget=True):
    k = recording.match(instances[0], rtype, inst, seed=seed, segments=segments, hold_mult=hold_mult,
                        interp=interp)
    rec = lambda A, kk, s: recording.record_matched(A, rtype, kk, rng=np.random.default_rng(s),
                                                    segments=segments, interp=interp)
    reps = []
    for i, A in enumerate(instances):
        for r in range(recs_per_instance):
            s = 1000 * i + 50 + r
            Y, seg = rec(A, k, s)
            reps.append({**_meas(Y, s, seg, n_draws, tau_floor), "instance": i})
    names = measures.MEASURES
    vals = {m: (float(np.nanmean(v)) if np.isfinite(v).sum() >= 0.8 * len(v) else np.nan)
            for m in names for v in [np.array([r[m] for r in reps], float)]}
    out = {"values": vals, "replicates": reps, "reached": bool(k["reached"]), "knobs": k,
           "achieved": k["achieved"]}
    if budget:
        A = instances[0]
        base = {s: reps[s - 50] for s in (50, 51)}               # instance 0, recordings 0 and 1
        floor = {m: abs(base[50][m] - base[51][m]) / 2 for m in names}
        ch = {m: [] for m in names}
        for s in (50, 51):
            c = {m: 0.0 for m in names}
            for knob in KNOBS[rtype]:
                for f in (1 / 1.5, 1.5):
                    kk = dict(k)
                    kk[knob] = max(k[knob] * f, 1.0) if knob in ("frame", "bin_steps") else k[knob] * f
                    Y, seg = rec(A, kk, s)
                    v = _meas(Y, s, seg, n_draws, tau_floor)
                    for m in names:
                        d = abs(v[m] - base[s][m])
                        c[m] = max(c[m], d) if np.isfinite(d) else np.nan
            for m in names:
                ch[m].append(c[m])
        out["budget"] = {m: float(max(np.mean(ch[m]) - floor[m], 0.0)) if np.isfinite(ch[m]).all()
                         and np.isfinite(floor[m]) else np.nan for m in names}
    return out
