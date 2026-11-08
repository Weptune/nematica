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
shown but no score is given. Exception: when the test applies the pushes itself with a calibrated strength
(uploaded models, or Python systems that let it calibrate), a weak pushed-unit response is a property of
the system: it is noted and the system is still scored.
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
MIN_STEP, MAX_STEP = 0.001, 2.0                  # seconds per step the test accepts
TARGET_PUSH = 1.6


def _search_push(response: Callable[[float], float], base: float) -> tuple[float, float]:
    """The strength whose pilot response is closest to the atlas median (1.6 SD): a log grid from 1e-2 to
    1e4 times `base` (robust when the response is not monotonic, e.g. gated units that shut at large
    inputs), then a finer grid around the best point."""
    grid = base * np.logspace(-2, 4, 13)
    best = None
    for a in grid:
        r = response(float(a))
        if np.isfinite(r) and (best is None or abs(r - TARGET_PUSH) < abs(best[1] - TARGET_PUSH)):
            best = (float(a), r)
    if best is None:
        return float(base), float("nan")
    for a in best[0] * np.logspace(-0.5, 0.5, 7):
        r = response(float(a))
        if np.isfinite(r) and abs(r - TARGET_PUSH) < abs(best[1] - TARGET_PUSH):
            best = (float(a), r)
    return best


def calibrate_push(net: Network, rng: np.random.Generator, log: Callable[[str], None] = print) -> float:
    """The push strength (added to the pushed unit's input each step of the push) that moves a pushed unit
    by about 1.6 of its resting SD over 15 s, like the atlas's median: bisection in log scale on short runs."""
    pilot = Protocol(runs=6, minutes=8.0)
    sch = make_schedule(net.n, net.step_seconds, pilot)

    def response(a):
        act = record_population(net, sch, a, np.random.default_rng(rng.integers(1 << 31)), burn=200)
        return poked_response([Run(r) for r in to_recordings(act, sch, np.random.default_rng(1))])
    a, r = _search_push(response, net.noise_sd)
    log(f"push strength {a:.4g} (pilot pushed-unit change {r:.2f} SD)")
    return a


def score(m: dict, ref: dict | None = None, check_push: bool = True) -> dict:
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
    problems, notes = [], []
    weak = not (np.isfinite(m.get("poked_response", np.nan)) and m["poked_response"] >= MIN_PUSH)
    if weak and not check_push:
        notes.append(f"The test pushed as hard as was useful, but pushed units moved only {m.get('poked_response', float('nan')):.2f} "
                     "SD over the next 15 s (worms about 1.6): this system lets go of a push quickly.")
    if weak and check_push:
        problems.append(f"the pushes barely moved the pushed units (median change {m.get('poked_response', float('nan')):.2f} "
                        f"SD; at least {MIN_PUSH} needed)")
    if m.get("n_pushes", 0) < MIN_PUSHES:
        problems.append(f"only {m.get('n_pushes', 0)} usable pushes (at least {MIN_PUSHES} needed)")
    if m.get("units_per_run", 0) < MIN_UNITS:
        problems.append(f"only {m.get('units_per_run', 0):.0f} units per run with resting activity (at least {MIN_UNITS})")
    inside = sum(v["inside"] for v in out.values())
    return {"signatures": out, "valid": not problems, "problems": problems, "notes": notes,
            "score": inside if not problems else None, "out_of": len(SIGNATURES),
            "mean_abs_distance": float(np.mean([min(abs(v["distance"]), 10) for v in out.values() if v["distance"] is not None]))
            if any(v["distance"] is not None for v in out.values()) else None}


def evaluate(activity: np.ndarray, sch: Schedule, how: str, extra: dict | None = None, seed: int = 0,
             pushed_by_test: bool = False) -> dict:
    """Score recorded activity (runs, steps, analysis units) that followed `sch`. When the test itself
    applied calibrated pushes, weak pushed-unit responses are a property of the system (noted, still
    scored); otherwise they mean the pushes cannot be verified (not scored)."""
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    recs = to_recordings(activity, sch, np.random.default_rng(seed))
    m = measure(recs)
    res = score(m, check_push=not pushed_by_test)
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
                   {"push_strength": amp, "noise_sd": net.noise_sd, "seconds": round(time.time() - t0, 1)}, seed,
                   pushed_by_test=True)
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


def _python_activity(system, sch, rng, log=None):
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
        if log:
            log(f"run {i + 1}/{len(sch.runs)}")
    return act


def run_python(system: BrainLike, protocol: Protocol | None = None, seed: int = 0, log: Callable[[str], None] = print) -> dict:
    """Run a Python system through the test. If the system sets `calibrate_push = True` and reads its push
    strength from `self.push_strength`, the test first finds the strength that moves a pushed unit by
    about 1.6 SD, as for uploaded models."""
    if not MIN_UNITS <= int(system.n_units) <= 1_000_000:
        raise NetworkError(f"set n_units to the number of units your system has ({MIN_UNITS} to 1,000,000)")
    if not MIN_STEP <= float(system.step_seconds) <= MAX_STEP:
        raise NetworkError(f"step_seconds must be {MIN_STEP} to {MAX_STEP}")
    t0 = time.time()
    rng = np.random.default_rng(seed)
    extra = {}
    if getattr(system, "calibrate_push", False):
        pilot = make_schedule(int(system.n_units), float(system.step_seconds), Protocol(runs=6, minutes=8.0))

        def response(a):
            system.push_strength = a
            act = _python_activity(system, pilot, np.random.default_rng(rng.integers(1 << 31)))
            return poked_response([Run(x) for x in to_recordings(act, pilot, np.random.default_rng(1))])
        system.push_strength, _ = _search_push(response, float(getattr(system, "push_strength", 1.0) or 1.0))
        extra["push_strength"] = system.push_strength
        log(f"push strength {system.push_strength:.4g}")
    sch = make_schedule(int(system.n_units), float(system.step_seconds), protocol)
    act = _python_activity(system, sch, rng, log)
    return evaluate(act, sch, "Python system run by the test", {"seconds": round(time.time() - t0, 1), **extra}, seed,
                    pushed_by_test=bool(extra))


# ---------------------------------------------------------------- uploaded recordings
def recordings_from_upload(z) -> tuple[np.ndarray, Schedule]:
    """An uploaded npz (already opened): `activity`, `n_units`, optional `step_seconds` (default 0.5).
    `activity` is (runs, steps_per_run, analysis units) at your step, or (runs, frames_per_run, analysis
    units) averaged into 0.5 s frames (smaller files for fast systems). Checked against the schedule the
    test gives that system."""
    if "activity" not in z.files or "n_units" not in z.files:
        raise NetworkError("the npz needs arrays `activity` (runs, steps, units) and `n_units`")
    try:
        n = int(np.asarray(z["n_units"]).item())
        dt = float(np.asarray(z["step_seconds"]).item()) if "step_seconds" in z.files else 0.5
    except (TypeError, ValueError):
        raise NetworkError("`n_units` and `step_seconds` must be single numbers") from None
    if not MIN_UNITS <= n <= 1_000_000 or not MIN_STEP <= dt <= MAX_STEP:
        raise NetworkError(f"n_units must be {MIN_UNITS} to 1,000,000 and step_seconds {MIN_STEP} to {MAX_STEP}")
    sch = make_schedule(n, dt)
    a = z["activity"]
    full = (len(sch.runs), sch.steps, len(sch.units))
    framed = (len(sch.runs), sch.frames, len(sch.units))
    if a.shape == framed and a.shape != full:
        sch.framed = True
    elif a.shape != full:
        alt = f" or {framed} in 0.5 s frames" if framed != full else ""
        raise NetworkError(f"activity has shape {a.shape}; the schedule for n_units={n}, step_seconds={dt:g} needs "
                           f"{full}{alt}")
    if a.dtype.kind not in "fiu":
        raise NetworkError("activity must hold numbers")
    a = np.asarray(a, np.float32)
    if np.isinf(a).any():
        raise NetworkError("activity contains infinite values")
    for i, run in enumerate(sch.runs):
        if not np.isfinite(a[i][:, run["recorded"]]).all():
            raise NetworkError(f"run {i}: the units this run records must have a value at every step")
    return a, sch
