"""Running the brain-likeness test and scoring it against real worms.

The score (fixed 8 Nov 2026, before any calibration system was scored; README "Brain-likeness test"):
for each of the 8 signatures, the system's value is compared with the range spanned by 60 random groups of
30 real worms (2.5th to 97.5th percentile, widened by the finite-population correction because the
groups are drawn from the same 113 worms). It is INSIDE when it falls in that range. The distance is the
value's offset from the worm median in units of that half of the range (|distance| <= 1 is inside).
The brain-likeness score is the number of signatures inside, out of 8.

The test is VALID only if the pushes were real and strong enough (median change of the pushed unit itself
at least 0.75 of its resting SD over 15 s: half the atlas median of about 1.6), there were at least 300
usable pushes, and each run recorded at least 10 units with resting activity. Otherwise the signatures are
shown but no score is given.
"""
from __future__ import annotations

import time
import warnings
from typing import Callable

import numpy as np

from .networks import Network, NetworkError, check_settings
from .protocol import Protocol, Schedule, make_schedule, record_population, to_recordings
from .reference import load as load_reference
from .signatures import ABOUT, LABELS, SIGNATURES, Run, measure, poked_response

MIN_PUSH, MIN_PUSHES, MIN_UNITS = 0.75, 300, 10
TARGET_PUSH = 1.6


def calibrate_push(net: Network, rng: np.random.Generator, log: Callable[[str], None] = print) -> float:
    """The push strength (added to the pushed unit's input each step of the push) that moves a pushed unit
    by about 1.6 of its resting SD over 15 s, like the atlas's median: bisection in log scale on short runs."""
    pilot = Protocol(runs=6, minutes=8.0)
    sch = make_schedule(net.n, net.step_seconds, pilot)
    lo, hi = np.log(1e-3 * net.noise_sd), np.log(1e4 * net.noise_sd)

    def response(a):
        act = record_population(net, sch, float(np.exp(a)), np.random.default_rng(rng.integers(1 << 31)), burn=200)
        return poked_response([Run(r) for r in to_recordings(act, sch, np.random.default_rng(1))])
    best = None
    for _ in range(14):
        mid = (lo + hi) / 2
        r = response(mid)
        if not np.isfinite(r):
            hi = mid
            continue
        if best is None or abs(r - TARGET_PUSH) < abs(best[1] - TARGET_PUSH):
            best = (mid, r)
        if r < TARGET_PUSH:
            lo = mid
        else:
            hi = mid
        if abs(r - TARGET_PUSH) < 0.1:
            break
    a = float(np.exp(best[0])) if best else float(np.exp(hi))
    log(f"push strength {a:.4g} (pilot pushed-unit change {best[1] if best else float('nan'):.2f} SD)")
    return a


def score(m: dict, ref: dict | None = None) -> dict:
    ref = ref or load_reference()
    out = {}
    for k in SIGNATURES:
        r = ref["signatures"][k]
        v = m.get(k)
        if v is None or not np.isfinite(v):
            out[k] = {"value": None, "inside": False, "distance": None}
            continue
        med = r["median"]
        # groups of 30 drawn from 113 worms overlap, which narrows their spread: widen by the finite-
        # population correction 1 / sqrt(1 - 30/113), so the range is that of independent groups
        fpc = 1.0 / np.sqrt(1.0 - ref["group_size"] / 113.0) if ref.get("group_size") else 1.0
        lo_, hi_ = med - (med - r["p2_5"]) * fpc, med + (r["p97_5"] - med) * fpc
        half = (hi_ - med) if v >= med else (med - lo_)
        d = (v - med) / half if half > 0 else (0.0 if v == med else np.sign(v - med) * np.inf)
        out[k] = {"value": float(v), "distance": float(d), "inside": bool(abs(d) <= 1),
                  "worm_median": med, "worm_low": lo_, "worm_high": hi_,
                  "label": LABELS[k], "about": ABOUT[k]}
    problems = []
    if not (np.isfinite(m.get("poked_response", np.nan)) and m["poked_response"] >= MIN_PUSH):
        problems.append(f"the pushes barely moved the pushed units (median change {m.get('poked_response', float('nan')):.2f} "
                        f"SD; at least {MIN_PUSH} needed)")
    if m.get("n_pushes", 0) < MIN_PUSHES:
        problems.append(f"only {m.get('n_pushes', 0)} usable pushes (at least {MIN_PUSHES} needed)")
    if m.get("units_per_run", 0) < MIN_UNITS:
        problems.append(f"only {m.get('units_per_run', 0):.0f} units per run with resting activity (at least {MIN_UNITS})")
    inside = sum(v["inside"] for v in out.values())
    return {"signatures": out, "valid": not problems, "problems": problems,
            "score": inside if not problems else None, "out_of": len(SIGNATURES),
            "mean_abs_distance": float(np.mean([min(abs(v["distance"]), 10) for v in out.values() if v["distance"] is not None]))
            if any(v["distance"] is not None for v in out.values()) else None}


def evaluate(activity: np.ndarray, sch: Schedule, how: str, extra: dict | None = None, seed: int = 0) -> dict:
    """Score recorded activity (runs, steps, analysis units) that followed `sch`."""
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    recs = to_recordings(activity, sch, np.random.default_rng(seed))
    m = measure(recs)
    res = score(m)
    res.update({"measured": {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in m.items()},
                "how": how, "schedule": sch.digest(), "n_units": sch.n_units, "step_seconds": sch.step_seconds,
                **(extra or {})})
    return res


def run_test(net: Network, protocol: Protocol | None = None, seed: int = 0, log: Callable[[str], None] = print) -> dict:
    """The full test for a model the server (or you) can run: calibrate the push, record 30 runs, score."""
    check_settings(net)
    t0 = time.time()
    rng = np.random.default_rng(seed)
    amp = calibrate_push(net, rng, log)
    sch = make_schedule(net.n, net.step_seconds, protocol)
    log(f"recording {len(sch.runs)} runs of {sch.steps} steps")
    act = record_population(net, sch, amp, rng)
    res = evaluate(act, sch, "model run by the test",
                   {"push_strength": amp, "noise_sd": net.noise_sd, "seconds": round(time.time() - t0, 1)}, seed)
    return res


# ---------------------------------------------------------------- systems written in Python
class BrainLike:
    """Any system, in Python. Implement run(); the test calls it once per run.

        run(steps, record, pushes, push_steps, rng) -> array (steps, len(record))

    steps:       how many steps to run (37 minutes at your step length)
    record:      indices of your units to record, in the order to return them
    pushes:      list of (step, unit): at that step give unit (an index of your units) a brief extra drive,
                 lasting push_steps steps, strong enough to move it clearly
    rng:         numpy Generator: use it for all randomness
    Set n_units (how many units your system has) and step_seconds (seconds per step; default 0.5).
    """
    n_units: int = 0
    step_seconds: float = 0.5
    name: str = "system"

    def run(self, steps, record, pushes, push_steps, rng):              # pragma: no cover
        raise NotImplementedError


def run_python(system: BrainLike, protocol: Protocol | None = None, seed: int = 0, log: Callable[[str], None] = print) -> dict:
    if not 2 <= int(system.n_units) <= 1_000_000:
        raise NetworkError("set n_units to the number of units your system has")
    t0 = time.time()
    sch = make_schedule(int(system.n_units), float(system.step_seconds), protocol)
    rng = np.random.default_rng(seed)
    units = np.asarray(sch.units)
    act = np.full((len(sch.runs), sch.steps, len(units)), np.nan, np.float32)
    for i, run in enumerate(sch.runs):
        rec = units[run["recorded"]].tolist()
        pushes = [(s, int(units[p])) for s, p in run["pushes"]]
        a = np.asarray(system.run(sch.steps, rec, pushes, sch.push_steps, np.random.default_rng(rng.integers(1 << 31))), float)
        if a.shape != (sch.steps, len(rec)):
            raise NetworkError(f"run() returned shape {a.shape}; expected ({sch.steps}, {len(rec)})")
        if not np.isfinite(a).all():
            raise NetworkError("run() returned NaN or infinite values")
        act[i][:, run["recorded"]] = a
        log(f"run {i + 1}/{len(sch.runs)}")
    return evaluate(act, sch, "Python system run by the test", {"seconds": round(time.time() - t0, 1)}, seed)


# ---------------------------------------------------------------- uploaded recordings
def recordings_from_upload(z) -> tuple[np.ndarray, Schedule]:
    """An uploaded npz (already opened): `activity` (runs, steps, analysis units), `n_units`, optional
    `step_seconds`. Checked against the schedule the test would give that system."""
    if "activity" not in z.files or "n_units" not in z.files:
        raise NetworkError("the npz needs arrays `activity` (runs, steps, units) and `n_units`")
    n = int(z["n_units"])
    dt = float(z["step_seconds"]) if "step_seconds" in z.files else 0.5
    if not 2 <= n <= 1_000_000 or not 0.001 <= dt <= 60:
        raise NetworkError("n_units must be 2 to 1,000,000 and step_seconds 0.001 to 60")
    sch = make_schedule(n, dt)
    a = z["activity"]
    want = (len(sch.runs), sch.steps, len(sch.units))
    if a.shape != want:
        raise NetworkError(f"activity has shape {a.shape}; the schedule for n_units={n}, step_seconds={dt} needs {want}")
    a = np.asarray(a, np.float32)
    if np.isinf(a).any():
        raise NetworkError("activity contains infinite values")
    for i, run in enumerate(sch.runs):
        if not np.isfinite(a[i][:, run["recorded"]]).all():
            raise NetworkError(f"run {i}: the units this run records must have a value at every step")
    return a, sch
