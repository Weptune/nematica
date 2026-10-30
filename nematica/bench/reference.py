"""The ruler: distances between real worms, and where a system falls relative to them.

For each metric:
    ceiling      d(first half, second half) within each real test worm
    biological   d(worm a, worm b) for every pair of real test worms
    system       d(system sample, real worm b) for every real test worm b that the sample
                 was not derived from

Verdicts at each metric:
    outside       distances larger than real worm-to-worm distances: worm-level bootstrap
                  interval for the shift above 0, OR median above the biological 95th percentile
    too typical   distances smaller than real worm-to-worm distances: worm-level bootstrap
                  interval for the shift below 0, OR median below the biological 5th
                  percentile (the mirror image of "outside"). A real worm compared with other real worms sits near the 50th
                  percentile, because both carry their own individuality and sampling noise. A
                  system that sits systematically closer to every real worm than real worms sit
                  to each other is reproducing the population average, not a worm.
    inside        neither: indistinguishable from another real worm at this metric
Distances are not independent (they share worms), so the tests are done at the worm level:
a hierarchical bootstrap resamples real worms and system templates with replacement,
recomputes every pairwise distance median, and gives an interval for
    shift = median(system distances) - median(real worm-to-worm distances).
"outside" needs the lower end of the one-sided (1 - alpha) interval above 0, or the median
above the biological 95th percentile; "too typical" is the mirror image. The pair-level
Mann-Whitney p-values are still reported (p_greater, p_less) for reference only; they treat
pairs as independent and are overconfident.

Individuality: `self_spread_ratio` = median distance between the system's own samples divided
by the median real worm-to-worm distance. Real worms differ from each other; a system whose
samples are all alike (ratio well below 1) reproduces an "average worm", which can sit
inside the range while missing individual variability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Sequence

import numpy as np
from scipy.stats import mannwhitneyu

from .levels import LEVELS
from .sample import BenchSample


@dataclass
class Reference:
    worms: list[str]
    biological: dict[str, np.ndarray] = field(default_factory=dict)
    ceiling: dict[str, np.ndarray] = field(default_factory=dict)


def build_reference(real: Sequence[BenchSample], metrics: Sequence[str] = tuple(LEVELS)) -> Reference:
    ref = Reference(worms=[s.origin or s.name for s in real])
    for m in metrics:
        fn = LEVELS[m]["fn"]
        ref.biological[m] = np.array([fn(a, b) for a, b in combinations(real, 2)])
        ref.ceiling[m] = np.array([fn(s.half(0), s.half(1)) for s in real])
    return ref


def _group(s: BenchSample) -> str:
    """The unit of resampling: the source worm, or the template worm a generated sample used."""
    return s.origin or s.name.split(":")[-1]


def worm_bootstrap(d_sys: np.ndarray, sys_groups: np.ndarray, d_bio: np.ndarray,
                   n_boot: int = 2000, seed: int = 0) -> np.ndarray:
    """Bootstrap distribution of median(system) - median(biological), resampling worms.

    d_sys[k, j]  distance from system sample k to real worm j (NaN where not to be compared)
    sys_groups   template group index of each system sample
    d_bio[i, j]  symmetric real worm-to-worm distances (NaN diagonal)
    """
    rng = np.random.default_rng(seed)
    n_real = d_bio.shape[0]
    groups = np.unique(sys_groups)
    members = [np.flatnonzero(sys_groups == g) for g in groups]
    out = np.full(n_boot, np.nan)
    iu = np.triu_indices(n_real, 1)
    for b in range(n_boot):
        r = rng.integers(0, n_real, n_real)
        # biological pairs among resampled worms; a worm is never paired with its own copy
        sub = d_bio[np.ix_(r, r)]
        same = r[:, None] == r[None, :]
        bio = sub[iu][~same[iu]]
        g = rng.integers(0, len(groups), len(groups))
        rows = np.concatenate([members[k] for k in g])
        sy = d_sys[np.ix_(rows, r)]
        bio = bio[np.isfinite(bio)]
        sy = sy[np.isfinite(sy)]
        if bio.size and sy.size:
            out[b] = np.median(sy) - np.median(bio)
    return out[np.isfinite(out)]


def score_system(name: str, samples: Sequence[BenchSample], real: Sequence[BenchSample],
                 ref: Reference, alpha: float = 0.05, n_boot: int = 2000) -> list[dict]:
    rows = []
    groups = np.array([_group(s) for s in samples])
    _, gidx = np.unique(groups, return_inverse=True)
    for m, spec in LEVELS.items():
        if m not in ref.biological:
            continue
        fn = spec["fn"]
        d_sys = np.array([[fn(s, r) if (s.origin is None or s.origin != r.origin) else np.nan
                           for r in real] for s in samples], dtype=float)
        d = d_sys[np.isfinite(d_sys)]
        bio = ref.biological[m][np.isfinite(ref.biological[m])]
        ceil = ref.ceiling[m][np.isfinite(ref.ceiling[m])]
        if d.size == 0 or bio.size == 0:
            rows.append({"system": name, "metric": m, "verdict": "not scored"})
            continue
        n_real = len(real)
        d_bio = np.full((n_real, n_real), np.nan)
        d_bio[np.triu_indices(n_real, 1)] = ref.biological[m]
        d_bio = np.fmin(d_bio, d_bio.T)
        boot = worm_bootstrap(d_sys, gidx, d_bio, n_boot=n_boot, seed=0)
        lo, hi = (np.percentile(boot, [100 * alpha, 100 * (1 - alpha)]) if boot.size
                  else (np.nan, np.nan))
        p = float(mannwhitneyu(d, bio, alternative="greater").pvalue)
        p_less = float(mannwhitneyu(d, bio, alternative="less").pvalue)
        med = float(np.median(d))
        p95 = float(np.percentile(bio, 95))
        p05 = float(np.percentile(bio, 5))
        if lo > 0 or med > p95:
            verdict = "outside"
        elif hi < 0 or med < p05:
            verdict = "too typical"
        else:
            verdict = "inside"
        # individuality: are the system's own samples as different from each other as real
        # worms are? Pairs of samples from different templates only, so masks match real use.
        own = np.array([fn(a, b) for i, a in enumerate(samples) for b in samples[i + 1:]
                        if a.name.split(":")[-1] != b.name.split(":")[-1]])
        own = own[np.isfinite(own)]
        spread = float(np.median(own) / np.median(bio)) if own.size and np.median(bio) > 0 else None
        rows.append({
            "system": name,
            "metric": m,
            "level": spec["level"],
            "primary": spec["primary"],
            "system_median": round(med, 4),
            "bio_median": round(float(np.median(bio)), 4),
            "bio_p05": round(p05, 4),
            "bio_p95": round(p95, 4),
            "ceiling_median": round(float(np.median(ceil)), 4) if ceil.size else None,
            "percentile_of_bio": round(float(np.mean(bio <= med)), 3),
            "shift": round(med - float(np.median(bio)), 4),
            "shift_lo": round(float(lo), 4),
            "shift_hi": round(float(hi), 4),
            "p_greater": round(p, 4),
            "p_less": round(p_less, 4),
            "n_pairs": int(d.size),
            "n_templates": int(len(np.unique(groups))),
            "self_spread_ratio": round(spread, 3) if spread is not None else None,
            "verdict": verdict,
        })
    return rows
