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

    def __init__(self, train, val, pool, pci: bool = True):
        from ..systems.causal_models import ClassVAR
        self.train, self.val, self.pool, self.pci = train, val, pool, pci
        self.classes = ClassVAR(3, "all").fit(train, val).classes        # one class index per fold
        self.real_b = [bench_sample(r, self.classes, f"real:{r.uid}", r.uid) for r in pool]
        self.ref = build_reference(self.real_b, metrics=ACTIVITY_LEVELS)
        self.real_c = [response_set(r) for r in pool]
        self.real_p = [pci_set(r) for r in pool] if pci else None

    def score(self, name: str, model, seed_base: int = 0, progress: Callable[[str], None] | None = None) -> list[dict]:
        """Fit `model` (fit(train, val) -> self; simulate(rec, rng) -> PumpProbe) and score it."""
        m = model.fit(self.train, self.val)
        sims = []
        for i, r in enumerate(self.pool):
            sims.append(m.simulate(r, np.random.default_rng(seed_base + i)))
            if progress:
                progress(f"simulated {i + 1}/{len(self.pool)}")
        rows: list[dict] = []
        sim_b = [bench_sample(s, self.classes, f"{name}:{r.uid}", r.uid) for s, r in zip(sims, self.pool)]
        for row in score_system(name, sim_b, self.real_b, self.ref):
            if row["metric"] in ACTIVITY_LEVELS:
                rows.append({"kind": "activity", **row})
        sim_c = []
        for s, r in zip(sims, self.pool):
            rs = response_set(s, f"{name}:{r.uid}")
            rs.group = r.uid
            sim_c.append(rs)
        rows += [{"kind": "causal", **row} for row in score_sets(name, sim_c, self.real_c)]
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
        return rows


def set_norm(norm: str) -> None:
    causal.NORM = norm
