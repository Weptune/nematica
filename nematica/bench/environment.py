"""Level 6: responses to the environment, tested at the population level.

Why population level: in the copper arena each worm meets the boundary only a few times
(70 encounters across 24 of 27 worms), so one worm's encounter response does not even
agree with itself across the two halves of its recording (within-worm ceiling = the
worm-to-worm distance, about 0.81). Pooled over worms the response is reproducible:
two random halves of the worms agree at r = 0.62 (split-half, 300 splits). So Level 6 asks
whether a system's POOLED response matches the pooled real response, using real
split-half disagreement as the yardstick.

Encounter definition (FROZEN, v1): the head comes within 1.0 mm of the copper boundary
after having been more than 1.5 mm away. Chosen among five candidate definitions by the
split-half reliability of the real pooled response alone (no system was scored when
choosing); see the progress log.

Metrics on pools of worms:
    encounter   per class: mean activity in (0, +10 s] after an encounter minus [-10 s, 0)
                before, averaged over every encounter in the pool. Distance = normalised
                squared difference |a - b|^2 / (|a|^2 + |b|^2) over classes seen in >= 3 worms
                on both sides: 0 identical, 1 unrelated or one side flat, 2 opposite. It is
                sensitive to response SIZE as well as pattern (v1.0 used 1 - Pearson r, which
                let a time-shuffled worm with a tiny but correctly signed response pass; the
                frame_shuffle calibration caught it).
    approach    reversal-onset rate in distance bands from the copper (0-0.5, 0.5-1, 1-2,
                > 2 mm), as log ratio to the pool's overall rate. Distance = mean |difference|.
    occupancy   pooled distribution of head distance to the copper; Wasserstein-1 in mm.
                Added after encounter and approach failed to reject a copper-blind simulated
                worm in held-out pools of 9 (too few encounters per pool to have power).

Test (paired partitions): repeat many times: split the real worms at random into halves A
and B; d_real = d(pool(real A), pool(real B)); d_sys = d(pool(system built on A), pool(real
B)). shift = d_sys - d_real. "outside" if the 5th percentile of shift > 0, "too typical" if
the 95th percentile < 0, else "inside".

Leakage note: a system trained on real worms must only be compared against held-out worms
(B must exclude its training worms). The calibration systems below are derived from the
partition-A worms themselves and never see B, so pooling all 27 worms is safe for them.
Trained systems need the rotating cross-validated pools planned next.
"""

from __future__ import annotations

from typing import Callable, Sequence

import numpy as np

from .sample import BenchSample

NEAR_MM, FAR_MM, WINDOW_S = 1.0, 1.5, 10.0
APPROACH_BINS_MM = (0.0, 0.5, 1.0, 2.0, np.inf)
MIN_WORMS_PER_CLASS = 3


def encounters(s: BenchSample, near: float = NEAR_MM, far: float = FAR_MM) -> list[int]:
    d = s.behaviour.get("dist_to_boundary")
    if d is None or len(d) != s.x.shape[1]:
        return []
    onsets, armed = [], False
    for t, v in enumerate(d):
        if not np.isfinite(v):
            continue
        if v > far:
            armed = True
        elif armed and v < near:
            onsets.append(t)
            armed = False
    return onsets


_CACHE: dict[int, tuple[BenchSample, np.ndarray]] = {}


def encounter_responses(s: BenchSample) -> np.ndarray:
    """(n_encounters, C) responses; NaN for classes the worm does not have. Cached per object."""
    hit = _CACHE.get(id(s))
    if hit is not None and hit[0] is s:
        return hit[1]
    out = _encounter_responses(s)
    if len(_CACHE) > 5000:
        _CACHE.clear()
    _CACHE[id(s)] = (s, out)
    return out


def _encounter_responses(s: BenchSample) -> np.ndarray:
    w = int(round(WINDOW_S / s.dt))
    T = s.x.shape[1]
    r = [s.x[:, t:t + w].mean(axis=1) - s.x[:, t - w:t].mean(axis=1)
         for t in encounters(s) if t - w >= 0 and t + w <= T]
    return np.array(r) if r else np.empty((0, s.x.shape[0]))


def pooled_encounter(pool: Sequence[BenchSample]) -> tuple[np.ndarray, np.ndarray]:
    rows, worm_has = [], []
    for s in pool:
        r = encounter_responses(s)
        if len(r):
            rows.append(r)
            worm_has.append(np.isfinite(r).any(axis=0))
    if not rows:
        return np.full(pool[0].x.shape[0], np.nan), np.zeros(pool[0].x.shape[0], int)
    with np.errstate(invalid="ignore"):
        mean = np.nanmean(np.vstack(rows), axis=0)
    return mean, np.sum(worm_has, axis=0)


def d_encounter(pa: Sequence[BenchSample], pb: Sequence[BenchSample]) -> float:
    ma, na = pooled_encounter(pa)
    mb, nb = pooled_encounter(pb)
    ok = np.isfinite(ma) & np.isfinite(mb) & (na >= MIN_WORMS_PER_CLASS) & (nb >= MIN_WORMS_PER_CLASS)
    if ok.sum() < 8:
        return np.nan
    a, b = ma[ok], mb[ok]
    den = float(np.sum(a * a) + np.sum(b * b))
    return float(np.sum((a - b) ** 2) / den) if den > 0 else np.nan


def pooled_approach(pool: Sequence[BenchSample]) -> np.ndarray:
    n_on = np.zeros(len(APPROACH_BINS_MM) - 1)
    n_fr = np.zeros_like(n_on)
    for s in pool:
        d, rv = s.behaviour.get("dist_to_boundary"), s.behaviour.get("reversing")
        if d is None or rv is None:
            continue
        on = np.zeros(len(rv), bool)
        on[np.flatnonzero(np.diff((rv > 0.5).astype(int)) == 1) + 1] = True
        band = np.digitize(d, APPROACH_BINS_MM) - 1
        for k in range(n_on.size):
            m = band == k
            n_on[k] += on[m].sum()
            n_fr[k] += m.sum()
    overall = n_on.sum() / max(n_fr.sum(), 1)
    if overall == 0:
        return np.full(n_on.size, np.nan)
    return np.where(n_fr > 0, np.log((n_on + 0.5) / (n_fr * overall + 0.5)), np.nan)


def d_approach(pa: Sequence[BenchSample], pb: Sequence[BenchSample]) -> float:
    a, b = pooled_approach(pa), pooled_approach(pb)
    ok = np.isfinite(a) & np.isfinite(b)
    return float(np.mean(np.abs(a[ok] - b[ok]))) if ok.sum() >= 2 else np.nan


def d_occupancy(pa: Sequence[BenchSample], pb: Sequence[BenchSample]) -> float:
    """Where the worms spend their time: Wasserstein-1 distance (mm) between the pooled
    distributions of head distance to the copper (clipped to -2..6 mm)."""
    from scipy.stats import wasserstein_distance
    da = [np.clip(s.behaviour["dist_to_boundary"], -2, 6) for s in pa if "dist_to_boundary" in s.behaviour]
    db = [np.clip(s.behaviour["dist_to_boundary"], -2, 6) for s in pb if "dist_to_boundary" in s.behaviour]
    if not da or not db:
        return np.nan
    return float(wasserstein_distance(np.concatenate(da), np.concatenate(db)))


ENV_METRICS = {
    "L6.encounter": {"fn": d_encounter, "primary": True,
                     "what": "pooled neural response when the head meets the copper boundary"},
    "L6.approach": {"fn": d_approach, "primary": False,
                    "what": "how the reversal rate rises near the copper (pooled)"},
    "L6.occupancy": {"fn": d_occupancy, "primary": True,
                     "what": "where in the arena the worms spend their time (pooled distance to copper)"},
}


def environment_shifts(real: Sequence[BenchSample],
                       system_for: Callable[[Sequence[BenchSample], np.random.Generator], Sequence[BenchSample]],
                       n_partitions: int = 300, seed: int = 0):
    """Per-partition (d_sys - d_real, d_real) for every Level 6 metric."""
    rng = np.random.default_rng(seed)
    real = [s for s in real if "dist_to_boundary" in s.behaviour]
    shifts = {m: [] for m in ENV_METRICS}
    d_real_all = {m: [] for m in ENV_METRICS}
    if len(real) < 6:
        return shifts, d_real_all
    for _ in range(n_partitions):
        perm = rng.permutation(len(real))
        A = [real[i] for i in perm[:len(real) // 2]]
        B = [real[i] for i in perm[len(real) // 2:]]
        sysA = system_for(A, rng)
        for m, spec in ENV_METRICS.items():
            dr, ds = spec["fn"](A, B), spec["fn"](sysA, B)
            if np.isfinite(dr) and np.isfinite(ds):
                shifts[m].append(ds - dr)
                d_real_all[m].append(dr)
    return shifts, d_real_all


def environment_rows(name: str, shifts: dict, d_real_all: dict) -> list[dict]:
    rows = []
    for m, spec in ENV_METRICS.items():
        sh = np.array(shifts[m])
        if sh.size < 20:
            rows.append({"system": name, "metric": m, "verdict": "not scored"})
            continue
        lo, hi = np.percentile(sh, [5, 95])
        verdict = "outside" if lo > 0 else ("too typical" if hi < 0 else "inside")
        dr = np.array(d_real_all[m])
        rows.append({
            "system": name, "metric": m, "level": 6, "primary": spec["primary"],
            "system_median": round(float(np.median(dr + sh)), 4),
            "bio_median": round(float(np.median(dr)), 4),
            "shift": round(float(np.median(sh)), 4),
            "shift_lo": round(float(lo), 4), "shift_hi": round(float(hi), 4),
            # share of partitions where the system was further from B than real A was
            "percentile_of_bio": round(float(np.mean(sh > 0)), 3),
            "n_partitions": int(sh.size),
            "verdict": verdict,
        })
    return rows


def environment_test(real: Sequence[BenchSample],
                     system_for: Callable[[Sequence[BenchSample], np.random.Generator], Sequence[BenchSample]],
                     name: str, n_partitions: int = 300, seed: int = 0) -> list[dict]:
    """Paired-partition test of a system against real worms at every Level 6 metric.

    system_for(real_half_A, rng) must return the system's samples built on those worms'
    arenas (for a calibration: transformed copies; for a simulator: runs in those arenas).
    """
    return environment_rows(name, *environment_shifts(real, system_for, n_partitions, seed))


def environment_test_folds(pools, name: str, n_partitions: int = 200, seed: int = 0) -> list[dict]:
    """Level 6 for TRAINED systems: `pools` is a list of (held-out real worms, system_for),
    one per rotation, where the system was fitted without those worms. Partitions are drawn
    within each held-out pool and the shifts pooled across rotations."""
    shifts = {m: [] for m in ENV_METRICS}
    d_real_all = {m: [] for m in ENV_METRICS}
    for k, (real, system_for) in enumerate(pools):
        sh, dr = environment_shifts(real, system_for, n_partitions, seed + k)
        for m in ENV_METRICS:
            shifts[m] += sh[m]
            d_real_all[m] += dr[m]
    return environment_rows(name, shifts, d_real_all)
