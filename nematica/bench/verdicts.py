"""Turning per-pool verdicts into the benchmark's answers.

The rule (fixed 8 Nov 2026 with the emulator pre-registration, README "A worm emulator"):

* a level PASSES on a split when its verdict is "inside" in at least 2 of the split's 3 held-out pools;
* a copy passes AT REST when at least 5 of the 6 activity levels pass;
* a copy passes WHEN POKED when echo pattern (C1), echo size (C2) and echo spread (P2) all pass;
* with several noise seeds, each seed is judged on its own and the report gives how many pass.

Verdicts are binary and can sit on a knife edge (review 8 found passes resting on bootstrap bounds a
hair below zero). So every level also gets a continuous EXCESS DISTANCE per pool:

    excess = (median copy-to-real distance - median real-to-real distance) / median real-to-real distance

0 means the copy's worms are as far from real worms as real worms are from each other; +0.5 means
50% further (too different); negative means closer than real worms ever are to each other (too
typical, an "average worm"). Its interval is the verdict's bootstrap interval on the same scale.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

import numpy as np

REST_LEVELS = ("L1.distribution", "L1.timescale", "L2.correlation", "L2.dimension", "L4.leadlag", "L4.dwell")
POKE_RULE_LEVELS = ("C1.pattern", "C2.magnitude", "P2.spread")
OTHER_LEVELS = ("C3.kinetics", "P1.complexity")
ALL_LEVELS = REST_LEVELS + POKE_RULE_LEVELS + OTHER_LEVELS
REST_NEEDED = 5

LABELS = {
    "L1.distribution": "activity distribution", "L1.timescale": "timescale", "L2.correlation": "correlation pattern",
    "L2.dimension": "dimensionality", "L4.leadlag": "lead and lag", "L4.dwell": "reversal-bout timing",
    "C1.pattern": "echo pattern", "C2.magnitude": "echo size", "P2.spread": "echo spread",
    "C3.kinetics": "echo time course", "P1.complexity": "echo complexity",
}
SHORT = {"inside": "I", "outside": "O", "too typical": "T"}


def _f(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return float("nan")
    return v


def excess(row: dict) -> tuple[float, float, float]:
    """(excess, low, high) for one pool's row; NaN when the level was not scored."""
    s, b = _f(row.get("system_median")), _f(row.get("bio_median"))
    if not (np.isfinite(s) and np.isfinite(b) and b > 0):
        return (np.nan, np.nan, np.nan)
    return ((s - b) / b, _f(row.get("shift_lo")) / b, _f(row.get("shift_hi")) / b)


def level_passes(letters: str) -> bool:
    return len(letters) >= 3 and letters.count("I") >= 2


def tables(rows: Sequence[dict]) -> dict:
    """{split: {seed: {level: letters over pools in fold order}}} and per-row excess."""
    acc: dict = defaultdict(lambda: defaultdict(dict))
    for r in sorted(rows, key=lambda r: (r["split"], r.get("seed", 0), r["fold"])):
        lv = r.get("metric")
        if lv not in ALL_LEVELS:
            continue
        d = acc[r["split"]][r.get("seed", 0)]
        d[lv] = d.get(lv, "") + SHORT.get(r.get("verdict"), "-")
    return {s: {sd: dict(v) for sd, v in d.items()} for s, d in acc.items()}


def judge(letters_by_level: dict) -> dict:
    rest = [lv for lv in REST_LEVELS if level_passes(letters_by_level.get(lv, ""))]
    poke = [lv for lv in POKE_RULE_LEVELS if level_passes(letters_by_level.get(lv, ""))]
    scored_poke = all(lv in letters_by_level for lv in POKE_RULE_LEVELS)
    return {"rest_levels_passing": len(rest), "rest_pass": len(rest) >= REST_NEEDED,
            "poke_levels_passing": len(poke), "poke_scored": scored_poke,
            "poke_pass": scored_poke and len(poke) == len(POKE_RULE_LEVELS),
            "all_nine": len(rest) == len(REST_LEVELS) and scored_poke and len(poke) == len(POKE_RULE_LEVELS)}


def answers(rows: Sequence[dict]) -> dict:
    """Per split: the rule applied seed by seed, and per level: letters, passes and excess."""
    t = tables(rows)
    order = list(dict.fromkeys(r["split"] for r in rows))
    out = {}
    for split in order:
        by_seed = t.get(split)
        if by_seed is None:
            continue
        seeds = sorted(by_seed)
        judged = {sd: judge(by_seed[sd]) for sd in seeds}
        levels = {}
        for lv in ALL_LEVELS:
            rr = [r for r in rows if r["split"] == split and r.get("metric") == lv]
            if not rr:
                continue
            ex = np.array([excess(r) for r in rr])
            ok = np.isfinite(ex[:, 0])
            levels[lv] = {
                "label": LABELS[lv],
                "letters": {sd: by_seed[sd].get(lv, "") for sd in seeds},
                "passes": sum(level_passes(by_seed[sd].get(lv, "")) for sd in seeds),
                "excess_median": float(np.median(ex[ok, 0])) if ok.any() else None,
                "excess_min": float(np.min(ex[ok, 0])) if ok.any() else None,
                "excess_max": float(np.max(ex[ok, 0])) if ok.any() else None,
                "runs_further": int(np.sum(ex[ok, 0] > 0)), "runs_closer": int(np.sum(ex[ok, 0] < 0)),
                "runs": int(ok.sum()),
                "per_run": [{"fold": r["fold"], "seed": r.get("seed", 0), "verdict": r.get("verdict"),
                             "excess": None if not np.isfinite(e[0]) else round(float(e[0]), 4),
                             "low": None if not np.isfinite(e[1]) else round(float(e[1]), 4),
                             "high": None if not np.isfinite(e[2]) else round(float(e[2]), 4)}
                            for r, e in zip(rr, ex)],
            }
        out[split] = {
            "seeds": len(seeds),
            "pools": max((len(v) for d in by_seed.values() for v in d.values()), default=0),
            "rest_pass_seeds": sum(j["rest_pass"] for j in judged.values()),
            "poke_pass_seeds": sum(j["poke_pass"] for j in judged.values()),
            "both_pass_seeds": sum(j["rest_pass"] and j["poke_pass"] for j in judged.values()),
            "all_nine_seeds": sum(j["all_nine"] for j in judged.values()),
            "by_seed": judged, "levels": levels,
        }
    return out


def rule_text() -> str:
    return ("A level passes when it is inside in at least 2 of 3 held-out pools. Rest: at least 5 of the 6 "
            "activity levels pass. Poked: echo pattern, echo size and echo spread all pass.")
