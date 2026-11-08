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
MIN_PUSH_EXCESS = 0.5          # pushed unit must move this much more than the others (worms: median 1.54 SD)
MIN_MEASURED = 6               # signatures that must be measurable for a result to count
MISSING_DISTANCE = 10.0        # a signature that cannot be measured counts as this far from worms
MIN_STEP, MAX_STEP = 0.005, 2.0                  # seconds per step the test accepts
TARGET_PUSH = 1.6
STEP_DEPENDENT = ("slow_share", "timescale")         # read in seconds: depend on the declared step length


def _search_push(response: Callable[[float], float], base: float) -> tuple[float, float]:
    """The push strength for a system: a log grid from 1e-2 to 1e4 times `base`, then a finer grid. If some
    strength reaches the atlas median (1.6 SD), the one closest to it; if none does (saturating units), the
    smallest strength that reaches 90% of the best response, so the push is not a long clamp."""
    pts = []
    for a in base * np.logspace(-2, 4, 13):
        r = response(float(a))
        if np.isfinite(r):
            pts.append((float(a), float(r)))
    if not pts:
        return float(base), float("nan")
    best_r = max(r for _, r in pts)
    if best_r < 0.9 * TARGET_PUSH:
        a, r = min((a, r) for a, r in pts if r >= 0.9 * best_r)
        return a, r
    best = min(pts, key=lambda t: abs(t[1] - TARGET_PUSH))
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
    """Compare measured signatures with the real-worm reference. A signature that cannot be measured counts as
    outside, at distance MISSING_DISTANCE. `check_push` is kept for compatibility: pushes are checked always."""
    ref = ref or load_reference()
    rel_ref = ref["signatures"].get("reliability")
    out = {}
    for k in SIGNATURES:
        r = ref["signatures"][k]
        v = m.get(k)
        why = None
        if k == "watch_share" and rel_ref is not None:
            rel = m.get("reliability")
            if rel is None or not np.isfinite(rel) or rel < rel_ref["p2_5"]:
                why = ("its runs barely agree with each other about push responses (reliability "
                       f"{rel if rel is not None else float('nan'):.3f}; real worm groups at least {rel_ref['p2_5']:.3f}), "
                       "so how well watching predicts them cannot be read")
        if why is None and (v is None or not np.isfinite(v)):
            why = "not measurable from these recordings"
        if why is not None:
            out[k] = {"value": None if v is None or not np.isfinite(v) else float(v), "inside": False, "distance": None,
                      "missing": why, "label": LABELS[k], "about": ABOUT[k]}
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
    pr, px = m.get("poked_response", np.nan), m.get("push_excess", np.nan)
    if not (np.isfinite(pr) and pr >= MIN_PUSH):
        problems.append(f"the pushes barely moved the pushed units (median change {pr:.2f} SD over 15 s; at least "
                        f"{MIN_PUSH} needed, worms 1.6)")
    elif not (np.isfinite(px) and px >= MIN_PUSH_EXCESS):
        problems.append(f"a push moved the pushed unit hardly more than the others (median excess {px:.2f} SD; at "
                        f"least {MIN_PUSH_EXCESS} needed, worms 1.54): the push did not reach one unit")
    if m.get("n_pushes", 0) < MIN_PUSHES:
        problems.append(f"only {m.get('n_pushes', 0)} usable pushes (at least {MIN_PUSHES} needed)")
    if m.get("units_per_run", 0) < MIN_UNITS:
        problems.append(f"only {m.get('units_per_run', 0):.0f} units per run with resting activity (at least {MIN_UNITS})")
    measured = sum(v["distance"] is not None for v in out.values())
    if measured < MIN_MEASURED:
        problems.append(f"only {measured} of {len(SIGNATURES)} signatures could be measured (at least {MIN_MEASURED})")
    for k, v in out.items():
        if v.get("missing") and k == "watch_share":
            notes.append(f"Copyable by watching was not read: {v['missing']}. It counts as outside.")
    inside = sum(v["inside"] for v in out.values())
    free = sum(v["inside"] for k, v in out.items() if k not in STEP_DEPENDENT)

    def dist(keys):
        return float(np.mean([MISSING_DISTANCE if out[k]["distance"] is None else min(abs(out[k]["distance"]), MISSING_DISTANCE)
                              for k in keys]))
    return {"signatures": out, "valid": not problems, "problems": problems, "notes": notes,
            "score": inside if not problems else None, "out_of": len(SIGNATURES),
            "score_step_free": free if not problems else None, "out_of_step_free": len(SIGNATURES) - len(STEP_DEPENDENT),
            "mean_abs_distance": dist(SIGNATURES) if not problems else None,
            "distance_step_free": dist([k for k in SIGNATURES if k not in STEP_DEPENDENT]) if not problems else None}


def evaluate(activity: np.ndarray, sch: Schedule, how: str, extra: dict | None = None, seed: int = 0) -> dict:
    """Score recorded activity (runs, steps or 0.5 s frames, analysis units) that followed `sch`. A result
    counts only if the pushes visibly moved the pushed units, more than the others, whoever applied them."""
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    recs = to_recordings(activity, sch, np.random.default_rng(seed))
    m = measure(recs)
    res = score(m)
    res.update({"measured": {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in m.items()},
                "how": how, "schedule": sch.digest(), "n_units": sch.n_units, "step_seconds": sch.step_seconds,
                **(extra or {})})
    return res


def run_test(net: Network, protocol: Protocol | None = None, seed: int = 0, log: Callable[[str], None] = print,
             noise_check: bool = False, schedule_seed: int | None = None) -> dict:
    """The full test for a model the server (or you) can run: calibrate the push, record 30 runs, score.
    With noise_check, the model is also tested at half and double its declared noise (push recalibrated
    each time), so a score that rests on a knife-edge noise setting is visible. The server passes a secret
    schedule_seed, so a model cannot know which units are recorded or when pushes come."""
    check_settings(net)
    t0 = time.time()
    rng = np.random.default_rng(seed)
    amp = calibrate_push(net, rng, log)
    sch = make_schedule(net.n, net.step_seconds, protocol, seed=schedule_seed)
    log(f"recording {len(sch.runs)} runs of {sch.steps} steps")
    act = record_population(net, sch, amp, rng)
    res = evaluate(act, sch, "model run by the test",
                   {"push_strength": amp, "noise_sd": net.noise_sd, "seconds": round(time.time() - t0, 1)}, seed)
    if noise_check:
        base, checks = net.noise_sd, []
        try:
            for f in (0.5, 2.0):
                net.noise_sd = base * f
                log(f"noise check: noise_sd {net.noise_sd:.3g}")
                r2 = np.random.default_rng(seed + 1)
                a2 = calibrate_push(net, r2, lambda m: None)
                act2 = record_population(net, sch, a2, r2)
                e = evaluate(act2, sch, "model run by the test", seed=seed)
                checks.append({"factor": f, "noise_sd": net.noise_sd, "score": e["score"], "valid": e["valid"],
                               "score_step_free": e["score_step_free"], "distance": e["mean_abs_distance"]})
        finally:
            net.noise_sd = base
        res["noise_check"] = checks
        res["seconds"] = round(time.time() - t0, 1)
    return res


# ---------------------------------------------------------------- systems written in Python
class BrainLike:
    """Any system, in Python. Implement run(); the test calls it once per run.

        run(steps, record, pushes, push_steps, rng) -> array (steps, len(record))

    steps:       how many steps to run (31.7 minutes at your step length)
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
    """Run a Python system through the schedule; steps shorter than 0.5 s are averaged into frames run by run
    (sch.framed is then set), so memory stays small at fine steps."""
    from .protocol import FRAME_S, _resample
    units = np.asarray(sch.units)
    fine = sch.step_seconds < FRAME_S - 1e-9
    T = sch.frames if fine else sch.steps
    act = np.full((len(sch.runs), T, len(units)), np.nan, np.float32)
    for i, run in enumerate(sch.runs):
        rec = units[run["recorded"]].tolist()
        pushes = [(s, int(units[p])) for s, p in run["pushes"]]
        a = np.asarray(system.run(sch.steps, rec, pushes, sch.push_steps, np.random.default_rng(rng.integers(1 << 31))), float)
        if a.shape != (sch.steps, len(rec)):
            raise NetworkError(f"run() returned shape {a.shape}; expected ({sch.steps}, {len(rec)})")
        if not np.isfinite(a).all():
            raise NetworkError("run() returned NaN or infinite values")
        act[i][:, run["recorded"]] = _resample(a, sch.step_seconds) if fine else a
        if log:
            log(f"run {i + 1}/{len(sch.runs)}")
    sch.framed = fine
    return act


def python_activity(system: BrainLike, protocol: Protocol | None = None, seed: int = 0,
                    log: Callable[[str], None] = lambda m: None, schedule_seed: int | None = None):
    """Run a Python system through the schedule (and first find its push strength if it sets
    `calibrate_push = True` and reads `self.push_strength`). Returns (activity, schedule, extra)."""
    if not MIN_UNITS <= int(system.n_units) <= 1_000_000:
        raise NetworkError(f"set n_units to the number of units your system has ({MIN_UNITS} to 1,000,000)")
    if not MIN_STEP <= float(system.step_seconds) <= MAX_STEP:
        raise NetworkError(f"step_seconds must be {MIN_STEP} to {MAX_STEP}")
    rng = np.random.default_rng(seed)
    extra = {}
    if getattr(system, "calibrate_push", False):
        pilot = make_schedule(int(system.n_units), float(system.step_seconds), Protocol(runs=6, minutes=8.0))

        def response(a):
            system.push_strength = a
            act = _python_activity(system, pilot, np.random.default_rng(rng.integers(1 << 31)))
            return poked_response([Run(x) for x in to_recordings(act, pilot, np.random.default_rng(1))])
        system.push_strength, _ = _search_push(response, float(getattr(system, "push_strength", 1.0) or 1.0))
        extra["push_strength"] = float(system.push_strength)
        log(f"push strength {system.push_strength:.4g}")
    sch = make_schedule(int(system.n_units), float(system.step_seconds), protocol, seed=schedule_seed)
    act = _python_activity(system, sch, rng, log)
    return act, sch, extra


def run_python(system: BrainLike, protocol: Protocol | None = None, seed: int = 0, log: Callable[[str], None] = print,
               schedule_seed: int | None = None) -> dict:
    """Run a Python system through the test and score it."""
    t0 = time.time()
    act, sch, extra = python_activity(system, protocol, seed, log, schedule_seed)
    return evaluate(act, sch, "Python system run by the test", {"seconds": round(time.time() - t0, 1), **extra}, seed)


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
