"""Rotating reference pools: refit every system per fold and combine the evidence.

    cv_score(recs, classes, folds, build_systems, seeds) -> (combined_rows, per_fold_rows)

`build_systems(train)` returns {name: model}; a model needs fit(train, val) and either
generate(template, rng) or, for per-worm models (attribute `names`), generate(template,
rng, which=i) so that each sample comes from a different training individual. Within each
rotation the pool is that fold's worms; 2 of the remaining worms are held out for any
model selection and the rest train.
"""

from __future__ import annotations

import time
from typing import Callable, Sequence

import numpy as np

from .reference import build_reference, combine_folds, score_system
from .sample import from_recording


def _per_worm(m) -> bool:
    return bool(getattr(m, "names", None)) or getattr(m, "lam", None) is not None and hasattr(m, "worm_A")


def cv_score(recs, classes, folds: Sequence[Sequence[str]], build_systems: Callable, seeds: int = 2,
             verbose: bool = True):
    by = {r.uid: r for r in recs}
    per: dict[str, list] = {}
    flat = []
    for fi, pool_uids in enumerate(folds):
        t0 = time.time()
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        val_uids = [rest[len(rest) // 3], rest[2 * len(rest) // 3]]
        train_uids = [u for u in rest if u not in val_uids]
        S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
        pool, train, val = S(pool_uids), S(train_uids), S(val_uids)
        ref = build_reference(pool)
        for name, m in build_systems(train).items():
            if m is None:                                   # real control: the training worms
                samples = train + val
            else:
                m.fit(train, val)
                samples = []
                for seed in range(seeds):
                    rng = np.random.default_rng(1000 * seed + 7 + fi)
                    if _per_worm(m):
                        samples += [m.generate(s, rng, which=seed * len(pool) + i) for i, s in enumerate(pool)]
                    else:
                        samples += [m.generate(s, rng) for s in pool]
            rows = score_system(name, samples, pool, ref, return_boot=True)
            per.setdefault(name, []).append(rows)
            flat += [{**{k: v for k, v in r.items() if k != "_boot"}, "fold": fi} for r in rows]
        if verbose:
            print(f"fold {fi} done ({time.time() - t0:.0f} s)", flush=True)
    combined = []
    for name, rows in per.items():
        combined += combine_folds(rows)
    return combined, flat


def print_table(combined) -> None:
    metrics = list(dict.fromkeys(r["metric"] for r in combined))
    systems = list(dict.fromkeys(r["system"] for r in combined))
    short = {"inside": "in", "outside": "OUT", "too typical": "typ", "not scored": "-"}
    print("system".ljust(28) + "".join(m.split(".")[1][:10].rjust(12) for m in metrics) + "  inside")
    for name in systems:
        line, n_in, n = name.ljust(28), 0, 0
        for m in metrics:
            r = next(x for x in combined if x["system"] == name and x["metric"] == m)
            if r["verdict"] == "not scored":
                line += "-".rjust(12)
                continue
            n += 1
            n_in += r["verdict"] == "inside"
            line += f"{short[r['verdict']]} {r['distance_ratio']:.2f}".rjust(12)
        print(line + f"  {n_in}/{n}")
