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

KNOBS = {"calcium": ("decay", "frame", "snr"), "deconv": ("frame", "snr"), "spikes": ("bin_steps", "mean_count", "gain")}


def _meas(Y, seed, seg, n_draws, tau_floor, rtype=None):
    if len(Y) == 0:                                      # no recording (e.g. no crop): every value undefined
        return {m: np.nan for m in measures.MEASURES} | {"tau_med": np.nan, "resolution_limited": None}
    if rtype == "calcium":                               # amendment 5: per-segment detrending in the calcium group
        Y = measures.detrend(Y, seg)
    r = measures.measure_matched(Y, seed=seed, n_draws=n_draws, segments=seg, tau_floor=tau_floor)
    return {m: r.get(m, np.nan) for m in measures.MEASURES} | {"tau_med": r.get("tau_med", np.nan),
                                                             "resolution_limited": r.get("resolution_limited")}


def crops(Y, seg, length, max_crops):
    """Amendment 13 (review 14, items 3 and 4): non-overlapping crops of `length` recorded samples, never
    crossing a segment boundary, so an AI is measured on stretches as long as one brain recording."""
    out = []
    for a, b in measures._spans(len(Y), seg):
        for s in range(a, b - length + 1, length):
            out.append(Y[s:s + length])
            if len(out) >= max_crops:
                return out
    return out


def ai_at_prep(instances, rtype, inst, segments=None, recs_per_instance=4, n_draws=20, seed=0,
               hold_mult=1, interp=False, tau_floor=measures.TAU_FLOOR, budget=True, crop_len=None,
               max_crops=4):
    k = recording.match(instances[0], rtype, inst, seed=seed, segments=segments, hold_mult=hold_mult,
                        interp=interp)
    def stretch(A, kk, r):
        """Amendment 13 (memory): with crops, a recording needs only enough native steps for max_crops crops
        (plus 20%); recording r of an instance uses the r-th such stretch of its activity (wrapping), so
        recordings differ in activity, not only in noise. Segment starts are shifted accordingly."""
        if not crop_len:
            return A, segments
        need = int(np.ceil(max_crops * crop_len * 1.2 * kk[recording.SAMPLE_KNOB[rtype]]
                           / kk["hold"])) + 1
        if need >= len(A):
            return A, segments
        a = (r * need) % max(len(A) - need, 1)
        seg = [x - a for x in (segments or []) if a < x < a + need]
        return A[a:a + need], seg

    def _rec(A, kk, s, r=0):
        As, seg = stretch(A, kk, r)
        Y, seg = recording.record_matched(As, rtype, kk, rng=np.random.default_rng(s), segments=seg, interp=interp)
        if inst.get("group"):                            # amendment 17: pooled units
            Y = recording.pool(Y, int(inst["group"]))
        return Y, seg

    def rec(A, kk, s):
        """A recording, or (amendment 13) its first crop of crop_len samples (one 'individual')."""
        Y, seg = _rec(A, kk, s)
        if crop_len:
            c = crops(Y, seg, crop_len, 1)
            return (c[0], []) if c else (Y[:0], [])
        return Y, seg
    reps = []
    ks = [k] + [recording.match(A, rtype, inst, seed=seed, segments=segments, hold_mult=hold_mult, interp=interp)
                for A in instances[1:]]                  # amendment 13: every instance matched on its own
    for i, A in enumerate(instances):
        ki = ks[i]
        for r in range(recs_per_instance):
            s = 1000 * i + 50 + r
            if crop_len:                                 # every crop of one recording is an AI individual
                Yf, segf = _rec(A, ki, s, r)
                for j, Y in enumerate(crops(Yf, segf, crop_len, max_crops)):
                    reps.append({**_meas(Y, s + 100 * j, [], n_draws, tau_floor, rtype), "instance": i, "crop": j})
            else:
                Y, seg = rec(A, ki, s)
                reps.append({**_meas(Y, s, seg, n_draws, tau_floor, rtype), "instance": i})
    names = measures.MEASURES
    if crop_len and not reps:                            # amendment 13: too slow for one brain-length crop
        return {"values": {m: np.nan for m in names}, "replicates": [], "reached": bool(k["reached"]), "knobs": k,
                "knobs_per_instance": ks,
                "achieved": k["achieved"], "native_tau": k.get("native_tau"), "crop_len": crop_len,
                "budget": {m: np.nan for m in names},
                "error": "no crop: a recording is shorter than one brain recording (network too slow)"}
    vals = {m: (float(np.nanmean(v)) if np.isfinite(v).sum() >= 0.8 * len(v) else np.nan)
            for m in names for v in [np.array([r[m] for r in reps], float)]}
    out = {"values": vals, "replicates": reps, "reached": bool(all(x["reached"] for x in ks)), "knobs": k,
           "knobs_per_instance": ks,
           "achieved": k["achieved"], "native_tau": k.get("native_tau"), "crop_len": crop_len}
    if budget:                                           # on the first instance that yields a crop
        bi = min(r["instance"] for r in reps) if reps else 0
        A, k = instances[bi], ks[bi]
        base = {}
        for s in (50, 51):                                       # instance 0, recordings 0 and 1 (first crop)
            Y, seg = rec(A, k, s)
            base[s] = _meas(Y, s, seg, n_draws, tau_floor, rtype)
        floor = {m: abs(base[50][m] - base[51][m]) / 2 for m in names}
        ch = {m: [] for m in names}
        for s in (50, 51):
            c = {m: 0.0 for m in names}
            for knob in KNOBS[rtype]:
                for f in (1 / 1.5, 1.5):
                    kk = dict(k)
                    kk[knob] = max(k[knob] * f, 1.0) if knob in ("frame", "bin_steps") else k[knob] * f
                    Y, seg = rec(A, kk, s)
                    v = _meas(Y, s, seg, n_draws, tau_floor, rtype)
                    for m in names:
                        d = abs(v[m] - base[s][m])
                        c[m] = max(c[m], d) if np.isfinite(d) else np.nan
            for m in names:
                ch[m].append(c[m])
        out["budget"] = {m: float(max(np.mean(ch[m]) - floor[m], 0.0)) if np.isfinite(ch[m]).all()
                         and np.isfinite(floor[m]) else np.nan for m in names}
    return out
