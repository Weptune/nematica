"""One fold of the headline test as a function: a brain copy is fitted on the training worms,
then simulated on every held-out worm with that worm's own stimulation schedule, and scored
against the held-out real worms on the watching levels (activity statistics), the poking
levels (C1 pattern, C2 magnitude, C3 kinetics) and, optionally, perturbational complexity
(P1, P2).

This is the same procedure as scripts/run_same_worms.py, kept in the package so that
`nematica score` (nematica/score.py) can run it on any copy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from ..data.canonical import zscore_rows
from ..data.pumpprobe import PumpProbe
from . import causal
from .causal import response_set, score_sets
from .perturbational import PCI_LEVELS, pci_set
from .reference import build_reference, score_system
from .sample import BenchSample

ACTIVITY_LEVELS = ("L1.distribution", "L1.timescale", "L2.correlation", "L2.dimension", "L4.leadlag", "L4.dwell")
POKE_LEVELS = ("C1.pattern", "C2.magnitude", "C3.kinetics")
SPLITS_DIR = Path(__file__).resolve().parents[2] / "configs" / "splits"
SPLITS = {"cv3": "pumpprobe_cv3.yaml", "blocks1": "pumpprobe_cv3_blocks1.yaml"}


def bench_sample(rec: PumpProbe, classes, name: str, origin: str, max_gap_frac: float = 0.05) -> BenchSample:
    """Class-level z-scored activity on a fixed class index; short gaps interpolated, classes
    missing more than 5% of frames left out."""
    from ..systems.causal_models import class_matrix
    x = class_matrix(rec, classes)
    t = np.arange(x.shape[1])
    for i in range(len(x)):
        ok = np.isfinite(x[i])
        if ok.mean() < 1 - max_gap_frac:
            x[i] = np.nan
        elif not ok.all():
            x[i] = np.interp(t, t[ok], x[i, ok])
    return BenchSample(name, tuple(classes), zscore_rows(x), rec.dt, origin=origin)


def fold_parts(recs: dict, folds: Sequence[Sequence[str]], fi: int):
    """Training worms, validation worms and the held-out pool for fold `fi`: every fifth
    non-pool worm (sorted by uid) is validation."""
    pool_uids = folds[fi]
    rest = sorted(u for f in folds if f is not pool_uids for u in f)
    val_uids = rest[::5]
    train = [recs[u] for u in rest if u not in val_uids]
    val = [recs[u] for u in val_uids]
    pool = [recs[u] for u in pool_uids]
    return train, val, pool


class FoldRuler:
    """The real side of one fold, built once and reused for every copy scored on it."""

    def __init__(self, train, val, pool, pci: bool = True, equivalence: bool = False):
        from ..systems.causal_models import ClassVAR
        self.train, self.val, self.pool, self.pci = train, val, pool, pci
        self.with_equivalence = equivalence     # research scripts: poke-level equivalence columns (x3 rule)
        self.classes = ClassVAR(3, "all").fit(train, val).classes        # one class index per fold
        self.real_b = [bench_sample(r, self.classes, f"real:{r.uid}", r.uid) for r in pool]
        self.ref = build_reference(self.real_b, metrics=ACTIVITY_LEVELS)
        self.real_c = [response_set(r) for r in pool]
        self.real_p = [pci_set(r) for r in pool] if pci else None

    def score(self, name: str, model, seed_base: int = 0, progress: Callable[[str], None] | None = None,
              refit: bool = True) -> list[dict]:
        """Fit `model` (fit(train, val) -> self; simulate(rec, rng) -> PumpProbe) and score it.
        refit=False reuses the model fitted by the previous call (further noise seeds)."""
        fitted = getattr(self, "_fitted", {})
        if refit or id(model) not in fitted:
            fitted = {id(model): model.fit(self.train, self.val)}          # one copy's fit at a time
            self._fitted = fitted
        m = fitted[id(model)]
        sims = []
        for i, r in enumerate(self.pool):
            s_ = m.simulate(r, np.random.default_rng(seed_base + i))
            if np.isinf(np.asarray(s_.x, float)).any():
                raise ValueError(f"{name}: infinite values in the simulation of worm {r.uid}")
            sims.append(s_)
            if progress:
                progress(f"simulated {i + 1}/{len(self.pool)}")
        rows: list[dict] = []
        sim_b = [bench_sample(s, self.classes, f"{name}:{r.uid}", r.uid) for s, r in zip(sims, self.pool)]
        # coverage: of the classes scored in each real worm, the share the copy's worm also has scored
        # (a class with more than 5% missing frames is not scored, for real and simulated worms alike)
        coverage = []
        for sb, rb in zip(sim_b, self.real_b):
            want = rb.observed
            coverage.append(float((sb.observed & want).sum() / max(want.sum(), 1)))
        cov_med, cov_min = float(np.median(coverage)), float(np.min(coverage))
        for row in score_system(name, sim_b, self.real_b, self.ref):
            if row["metric"] in ACTIVITY_LEVELS:
                rows.append({"kind": "activity", **row})
        sim_c = []
        for s, r in zip(sims, self.pool):
            rs = response_set(s, f"{name}:{r.uid}")
            rs.group = r.uid
            sim_c.append(rs)
        if self.with_equivalence and not hasattr(self, "tolerances"):
            self.tolerances = poke_tolerances(self.pool, self.real_c)
        for row in score_sets(name, sim_c, self.real_c):
            if self.with_equivalence:
                tol = self.tolerances.get(row["metric"], {}).get("tolerance")
                row = {**row, "tolerance": tol, "equivalence": equivalence(row, tol)}
            rows.append({"kind": "causal", **row})
        if self.pci:
            sim_p = []
            for s, r in zip(sims, self.pool):
                ps = pci_set(s, f"{name}:{r.uid}")
                ps.group = r.uid
                sim_p.append(ps)
            for row in score_sets(name, sim_p, self.real_p, levels=PCI_LEVELS):
                med = np.concatenate([q.spread for q in sim_p if len(q.spread)])
                rows.append({"kind": "complexity", **row,
                             "median_spread": round(float(np.median(med)), 4) if med.size else None})
        for r in rows:
            r["system"] = name
            r["coverage"], r["coverage_min"] = round(cov_med, 3), round(cov_min, 3)
        return rows


# Equivalence on the poke levels (fixed 1 Nov 2026, before any copy was checked against it).
# "Inside" only says no difference was detected. A copy AGREES on a level when the whole 90%
# bootstrap interval of its shift (copy-to-real minus real-to-real median distance) lies
# within +/- tolerance, where tolerance = TOL_FRACTION x the shift of a copy known to be
# wrong on that level, built from the same held-out worms: targets permuted (pattern), all
# responses x3 (magnitude), time reversed (kinetics). Those controls are the calibrations
# already used to check the levels (nematica.bench.causal.CALIBRATIONS).
TOL_FRACTION = 0.5
TOL_CONTROL = {"C1.pattern": "permuted_targets", "C2.magnitude": "scaled_x3", "C3.kinetics": "time_reversed"}
# magnitude control from 1 Nov 2026 (README): responses x1.5; reported beside the x3 rule
TOL_CONTROL_V2 = {"C2.magnitude": "scaled_x1.5"}


def poke_tolerances(pool, real_c=None, frac: float = TOL_FRACTION, seed: int = 0, controls: dict | None = None) -> dict:
    """Per poke level: the known-wrong control's median shift, and the tolerance from it."""
    from .causal import CALIBRATIONS, CAUSAL_LEVELS, scaled
    real_c = real_c or [response_set(r) for r in pool]
    calib = dict(CALIBRATIONS)
    calib["scaled_x1.5"] = lambda r, rng: scaled(r, 1.5)
    out = {}
    for level, ctrl in (controls or TOL_CONTROL).items():
        rng = np.random.default_rng(seed)
        sets = []
        for r in pool:
            cs = calib[ctrl](r, rng)
            cs.group = r.uid
            sets.append(cs)
        row = score_sets(ctrl, sets, real_c, levels={level: CAUSAL_LEVELS[level]})[0]
        gap = row.get("system_median", np.nan) - row.get("bio_median", np.nan)
        out[level] = {"control": ctrl, "control_shift": round(float(gap), 4),
                      "tolerance": round(float(frac * gap), 4) if gap > 0 else None}
    return out


def equivalence(row: dict, tol: float | None) -> str:
    if row.get("verdict") == "not scored" or row.get("shift_lo") in (None, ""):
        return "not scored"
    if tol is None:
        return "no tolerance"
    lo, hi = float(row["shift_lo"]), float(row["shift_hi"])
    return "agrees" if (-tol < lo and hi < tol) else "not shown"


def set_norm(norm: str) -> None:
    causal.NORM = norm
