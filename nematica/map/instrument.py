"""Instrument numbers (docs/MAP.md, amendment 4, F2): the frozen function that turns one real individual's
recording into the summary numbers the matching rule uses. Step 1 of the map runs only this function on the
real data, before any activity measure is computed, and it outputs only these aggregates: never per-unit
timescales or any of the seven measures.

Rules (registered):
- Unit inclusion. Calcium: units with non-constant traces and a white-noise share below 0.99. Spikes: binned
  at SPIKE_BIN_S (20 ms) by the loader, units with at least MIN_SPIKES spikes and MIN_RATE_HZ mean rate.
- Rest segments. If the individual carries `segments` marking spontaneous (no-stimulus) stretches, only
  those are used (`rest`), and lags never cross a boundary; otherwise the whole recording.
- Indicator decay. The 1/e decay constant is the indicator's half-decay time divided by ln 2, from
  INDICATOR_HALF_DECAY_S (each entry cites its source: the indicator's characterisation paper, in vivo
  single-spike value where reported, else the dataset paper). Worm neurons mostly do not spike and are
  imaged at room temperature, so for R1 and R2 the indicator value is a convention; a sensitivity at twice
  the half-decay is reported.
- Aggregation. Median over individuals within a preparation; then median over preparations within a
  recording group (`group_numbers`). Each individual's numbers are kept so the per-preparation matching of
  amendment 4 (F5, AIs recorded at each preparation's own instrument) can use the preparation medians.
"""
from __future__ import annotations

import numpy as np

import hashlib
from pathlib import Path

from .measures import detrend, noise_fraction, tau_med

SPIKE_BIN_S = 0.02
MIN_SPIKES = 200
MIN_RATE_HZ = 0.05
MAX_NOISE_CALCIUM = 0.99

# indicator -> (half-decay time in seconds, source). Registered in amendment 4, before step 1. Which indicator
# each dataset used is read from its metadata or paper at step 1; an indicator not listed here is added with
# a citation by the same rule before any matching.
INDICATOR_HALF_DECAY_S: dict[str, tuple[float, str]] = {
    "GCaMP6f": (0.10, "Chen et al. 2013 Nature 499:295, mouse V1 in vivo, 1 AP (about 100 ms)"),
    "GCaMP6m": (0.20, "Chen et al. 2013, mouse V1 in vivo, 1 AP (about 200 ms)"),
    "GCaMP6s": (0.50, "Chen et al. 2013, mouse V1 in vivo, 1 AP (about 500 ms)"),
    "jGCaMP7f": (0.265, "Dana et al. 2019 Nat Methods, cultured neurons, 1 AP (265 ms); no in vivo 1-AP value"),
}


def include_units(X, rtype, dt):
    X = np.asarray(X, float)
    keep = X.std(0) > 1e-9
    if rtype == "spikes":
        n = X.sum(0)
        keep &= (n >= MIN_SPIKES) & (n / (len(X) * dt) >= MIN_RATE_HZ)
    out = X[:, keep]
    if rtype == "calcium" and out.shape[1]:
        out = out[:, noise_fraction(out) < MAX_NOISE_CALCIUM]
    return out


def _rest(ind):
    """Rest stretches: (activity, segment starts within it). `ind['rest']` is a list of (start, stop) sample
    ranges of spontaneous activity; absent means the whole recording, with `ind['segments']` as boundaries."""
    X = np.asarray(ind["activity"], float)
    if ind.get("rest"):
        parts, starts, n = [], [], 0
        for a, b in ind["rest"]:
            if b - a > 0:
                if n:
                    starts.append(n)
                parts.append(X[a:b])
                n += b - a
        return np.vstack(parts), starts
    return X, list(ind.get("segments") or [])


def instrument_numbers(ind, rtype):
    """One individual's instrument numbers. `ind`: activity (time x units), dt (s), recording type and, for
    calcium, `indicator` (a key of INDICATOR_HALF_DECAY_S) or `half_decay_s`. Returns only aggregates."""
    X, seg = _rest(ind)
    dt = float(ind["dt"])
    if rtype == "calcium":
        X = detrend(X, seg)                              # amendment 5: per unit, per stretch
    X = include_units(X, rtype, dt)
    out = {"n_units": int(X.shape[1]), "duration_s": float(len(X) * dt)}
    if X.shape[1] < 2:
        return {**out, "error": "fewer than 2 units"}
    t = tau_med(X, segments=seg)
    out["tau_med_s"] = float(t * dt)
    out["noise"] = float(np.median(noise_fraction(X, segments=seg)))
    out["duration_tau"] = float(len(X) / t) if np.isfinite(t) else np.nan
    if rtype == "calcium":
        hd = ind.get("half_decay_s")
        if hd is None:
            hd = INDICATOR_HALF_DECAY_S[ind["indicator"]][0]
        out["frames_per_tau"] = float(t)
        out["decay_over_tau"] = float(hd / np.log(2) / dt / t)
        out["decay_over_tau_x2"] = float(2 * hd / np.log(2) / dt / t)      # sensitivity (amendment 5)
    elif rtype == "spikes":
        if abs(dt - SPIKE_BIN_S) > 1e-9:
            return {**out, "error": f"spikes must be binned at {SPIKE_BIN_S} s"}
        out["bins_per_tau"] = float(t)
        out["count_per_bin"] = float(np.median(X.mean(0)))
    return out


KEYS = {"calcium": ("decay_over_tau", "frames_per_tau", "noise"),
        "spikes": ("bins_per_tau", "count_per_bin", "noise")}


def preparation_numbers(individuals, rtype):
    """Median over individuals (those without an error)."""
    rows = [r for r in individuals if "error" not in r]
    return {k: float(np.median([r[k] for r in rows])) for k in KEYS[rtype]} | {"n_individuals": len(rows)}


def group_numbers(preps, rtype):
    """Median over preparations within a recording group."""
    return {k: float(np.median([p[k] for p in preps])) for k in KEYS[rtype]}


STEP1_CODE = ["nematica/map/instrument.py", "nematica/map/measures.py", "nematica/map/data.py"]


def code_hash(extra=()):
    """Hash of the code step 1 runs (this module, the estimators, the loaders and any loader script), stored
    with step 1's output (amendment 5)."""
    root = Path(__file__).resolve().parents[2]
    h = hashlib.sha256()
    for f in list(STEP1_CODE) + list(extra):
        h.update((root / f).read_bytes())
    return h.hexdigest()[:16]
