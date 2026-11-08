"""Turning per-pool verdicts into the benchmark's answers.

The rule (fixed 8 Nov 2026 with the emulator pre-registration, README "A worm emulator"):

* a level PASSES on a split when its verdict is "inside" in at least 2 of the split's 3 held-out pools;
* a copy passes AT REST when at least 5 of the 6 activity levels pass;
* a copy passes WHEN POKED when echo pattern (C1), echo size (C2) and echo spread (P2) all pass;
* with several noise seeds, each seed is judged on its own and the report gives how many pass.

A split is JUDGED only when every one of its pools was scored, each exactly once per seed, and the copy
covered enough of the neurons scored (COVERAGE_FLOOR). Otherwise its letters and distances are shown
but no pass or fail is given: a quick look at one pool is not a verdict.

Verdicts are binary and can sit on a knife edge (review 8 found passes resting on bootstrap bounds a
hair below zero). So every level also gets a continuous EXCESS DISTANCE per pool:

    excess = (median copy-to-real distance - median real-to-real distance) / median real-to-real distance

0 means the copy's worms are as far from real worms (by that pool's median) as real worms are from
each other; +0.5 means 50% further. A negative excess means closer on median; the verdict "too typical"
needs the whole bootstrap interval below zero. Distances are on different scales on different levels
(lead and lag is 1 minus a correlation near 0.03, so real-to-real is about 0.97 and every copy sits
near 0), so compare a level's excess across copies, not across levels.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Sequence

import numpy as np

REST_LEVELS = ("L1.distribution", "L1.timescale", "L2.correlation", "L2.dimension", "L4.leadlag", "L4.dwell")
POKE_RULE_LEVELS = ("C1.pattern", "C2.magnitude", "P2.spread")
OTHER_LEVELS = ("C3.kinetics", "P1.complexity")
ALL_LEVELS = REST_LEVELS + POKE_RULE_LEVELS + OTHER_LEVELS
REST_NEEDED = 5
POOLS_NEEDED = 2                      # of the split's pools (3 in both frozen splits)
COVERAGE_FLOOR = 0.8                  # median share of the scored neuron classes a copy must model

LABELS = {
    "L1.distribution": "activity distribution", "L1.timescale": "timescale", "L2.correlation": "correlation pattern",
    "L2.dimension": "dimensionality", "L4.leadlag": "lead and lag", "L4.dwell": "reversal-bout timing",
    "C1.pattern": "echo pattern", "C2.magnitude": "echo size", "P2.spread": "echo spread",
    "C3.kinetics": "echo time course", "P1.complexity": "echo complexity",
}
SHORT = {"inside": "I", "outside": "O", "too typical": "T"}


class RowsError(ValueError):
    """Rows that cannot be judged as they stand (duplicates, unknown structure)."""


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def excess(row: dict) -> tuple[float, float, float]:
    """(excess, low, high) for one pool's row; NaN when the level was not scored."""
    s, b = _f(row.get("system_median")), _f(row.get("bio_median"))
    if not (np.isfinite(s) and np.isfinite(b) and b > 0):
        return (np.nan, np.nan, np.nan)
    return ((s - b) / b, _f(row.get("shift_lo")) / b, _f(row.get("shift_hi")) / b)


def pools_needed(n_pools: int) -> int:
    """2 of 3 in the frozen splits; two thirds, rounded up, for other numbers of pools."""
    return -(-2 * n_pools // 3)


def level_passes(letters: str, n_pools: int = 3) -> bool:
    return len(letters) == n_pools and "." not in letters and letters.count("I") >= pools_needed(n_pools)


def _letters(rows_by_fold: dict, folds: list) -> str:
    return "".join(SHORT.get(rows_by_fold[f].get("verdict"), "-") if f in rows_by_fold else "." for f in folds)


def judge(letters_by_level: dict, n_pools: int = 3) -> dict:
    rest = [lv for lv in REST_LEVELS if level_passes(letters_by_level.get(lv, ""), n_pools)]
    poke = [lv for lv in POKE_RULE_LEVELS if level_passes(letters_by_level.get(lv, ""), n_pools)]
    scored_poke = all(lv in letters_by_level for lv in POKE_RULE_LEVELS)
    return {"rest_levels_passing": len(rest), "rest_pass": len(rest) >= REST_NEEDED,
            "poke_levels_passing": len(poke), "poke_scored": scored_poke,
            "poke_pass": scored_poke and len(poke) == len(POKE_RULE_LEVELS),
            "all_nine": len(rest) == len(REST_LEVELS) and scored_poke and len(poke) == len(POKE_RULE_LEVELS)}


def answers(rows: Sequence[dict]) -> dict:
    """Per split: whether it can be judged, the rule applied seed by seed, and per level: letters
    (one per pool, in fold order; '.' = pool not scored), passes and excess distances."""
    order = list(dict.fromkeys(r["split"] for r in rows))
    idx: dict = defaultdict(dict)                         # (split, seed, level) -> {fold: row}
    for r in rows:
        lv = r.get("metric")
        if lv not in ALL_LEVELS:
            continue
        key = (r["split"], int(r.get("seed", 0)), lv)
        f = int(r["fold"])
        if f in idx[key]:
            raise RowsError(f"two rows for split {r['split']}, seed {key[1]}, fold {f}, level {lv}: "
                            "merged or duplicated results cannot be judged")
        idx[key][f] = r
    out = {}
    for split in order:
        srows = [r for r in rows if r["split"] == split]
        nf = {int(_f(r.get("n_folds"))) for r in srows if np.isfinite(_f(r.get("n_folds")))}
        n_folds = max(nf) if nf else 0
        seen_folds = sorted({int(r["fold"]) for r in srows})
        folds = list(range(n_folds)) if n_folds else seen_folds
        seeds = sorted({int(r.get("seed", 0)) for r in srows})
        sizes = {int(r["fold"]): int(r["pool_size"]) for r in srows if r.get("pool_size") not in (None, "")
                 and np.isfinite(_f(r.get("pool_size")))}
        cov = [_f(r.get("coverage")) for r in srows if np.isfinite(_f(r.get("coverage")))]
        coverage = float(np.median(cov)) if cov else None
        problems = []
        if not nf:
            problems.append("the number of pools in the split was not recorded")
        elif len(nf) > 1 or any(f not in range(n_folds) for f in seen_folds):
            problems.append("inconsistent pool numbering")
        elif set(seen_folds) != set(folds):
            problems.append(f"{len(seen_folds)} of {len(folds)} pools scored")
        if any((split, sd, "P2.spread") not in idx for sd in seeds) and \
                not any((split, sd, lv) in idx for sd in seeds for lv in ("C1.pattern", "C2.magnitude")):
            problems.append("poke levels not scored")
        elif any((split, sd, "P2.spread") not in idx for sd in seeds):
            problems.append("echo spread not scored (run with the complexity levels on)")
        incomplete = sorted({(sd, LABELS[lv]) for sd in seeds for lv in REST_LEVELS + POKE_RULE_LEVELS
                             if (split, sd, lv) in idx and set(idx[(split, sd, lv)]) != set(folds)
                             or (split, sd, lv) not in idx})
        if incomplete and not problems:
            problems.append(f"seed {incomplete[0][0]}: {incomplete[0][1]} not scored in every pool")
        cmin = [_f(r.get("coverage_min")) for r in srows if np.isfinite(_f(r.get("coverage_min")))]
        if coverage is not None and coverage < COVERAGE_FLOOR:
            problems.append(f"the copy models a median {coverage:.0%} of the scored neuron classes "
                            f"(at least {COVERAGE_FLOOR:.0%} needed)")
        elif cmin and min(cmin) < 0.5:
            problems.append(f"in one held-out worm the copy models only {min(cmin):.0%} of the scored neuron classes")
        judged_ok = not problems
        letters = {sd: {lv: _letters(idx[(split, sd, lv)], folds) for lv in ALL_LEVELS if (split, sd, lv) in idx}
                   for sd in seeds}
        judged = {sd: judge(letters[sd], len(folds)) for sd in seeds} if judged_ok else {}
        levels = {}
        for lv in ALL_LEVELS:
            rr = [r for r in srows if r.get("metric") == lv]
            if not rr:
                continue
            ex = np.array([excess(r) for r in rr])
            ok = np.isfinite(ex[:, 0])
            levels[lv] = {
                "label": LABELS[lv],
                "letters": {sd: letters[sd].get(lv, "") for sd in seeds},
                "passes": sum(level_passes(letters[sd].get(lv, ""), len(folds)) for sd in seeds) if judged_ok else None,
                "excess_median": float(np.median(ex[ok, 0])) if ok.any() else None,
                "excess_min": float(np.min(ex[ok, 0])) if ok.any() else None,
                "excess_max": float(np.max(ex[ok, 0])) if ok.any() else None,
                "runs_further": int(np.sum(ex[ok, 0] > 0)), "runs_closer": int(np.sum(ex[ok, 0] < 0)),
                "runs": int(ok.sum()),
                "per_run": [{"fold": int(r["fold"]), "seed": int(r.get("seed", 0)), "verdict": r.get("verdict"),
                             "self_spread_ratio": None if not np.isfinite(_f(r.get("self_spread_ratio"))) else round(_f(r.get("self_spread_ratio")), 3),
                             "excess": None if not np.isfinite(e[0]) else round(float(e[0]), 4),
                             "low": None if not np.isfinite(e[1]) else round(float(e[1]), 4),
                             "high": None if not np.isfinite(e[2]) else round(float(e[2]), 4)}
                            for r, e in zip(rr, ex)],
            }
        out[split] = {
            "judged": judged_ok, "not_judged_because": problems,
            "seeds": len(seeds), "pools": len(folds), "pools_scored": len(seen_folds), "coverage": coverage,
            "held_out_worms": sum(sizes.values()) if sizes else None,
            "coverage_note": None if coverage is not None else "coverage not recorded (results converted from research runs)",
            "rest_pass_seeds": sum(j["rest_pass"] for j in judged.values()) if judged_ok else None,
            "poke_pass_seeds": sum(j["poke_pass"] for j in judged.values()) if judged_ok else None,
            "both_pass_seeds": sum(j["rest_pass"] and j["poke_pass"] for j in judged.values()) if judged_ok else None,
            "all_nine_seeds": sum(j["all_nine"] for j in judged.values()) if judged_ok else None,
            "by_seed": judged, "levels": levels,
        }
    return out


def rule_text() -> str:
    return ("A level passes when it is inside in at least 2 of a split's 3 held-out pools (two thirds when a split has "
            "another number of pools). At rest: at least 5 of "
            "the 6 activity levels pass. When poked: echo pattern, echo size and echo spread all pass.")


FOLD_DIR = re.compile(r"fold(\d+)$")
SEED_DIR = re.compile(r"seed(\d+)$")
