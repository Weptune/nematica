"""The map's analysis, frozen before any brain data is read (docs/MAP.md, amendment 3).

Systems are dicts:
  preparation: {"id", "kind": "real", "group", "dataset", "species_type", "individuals": [{measure: value}],
                "se": {measure: split-half SE (mean over individuals)}}
  AI:          {"id", "kind": "ai", "family", "role": "standard" | "augmented", "fitted_on": [preparation ids],
                "values": {group: {measure: value}}, "replicates": {group: [{measure: value}, ...]},
                "reached": {group: bool}, "budget": {group: {measure: change over the mismatch sweep}}}
Every function takes the group's systems and returns plain numbers, so the decisions can be re-run and checked.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

CAP = 10.0                      # largest contribution of one measurement to a distance, in BVU
MIN_MEASURES = 3
MIN_TYPES = 4                   # distinct species-or-preparation types for a powered group
SLOW_SET = ("slow_fraction", "timescale_spread", "drift")


# ---------------------------------------------------------------- ruler
def bvu(preps, measures):
    """Biological variation unit per measurement: pooled within-preparation SD across individuals,
    df = sum(n_i - 1), with a 90% interval from the chi-square distribution."""
    out = {}
    for m in measures:
        ss, df = 0.0, 0
        for p in preps:
            v = np.array([ind.get(m, np.nan) for ind in p["individuals"]], float)
            v = v[np.isfinite(v)]
            if len(v) >= 2:
                ss += ((v - v.mean()) ** 2).sum()
                df += len(v) - 1
        if df == 0 or ss <= 0:
            out[m] = {"sd": np.nan, "df": df, "lo": np.nan, "hi": np.nan}
            continue
        sd = np.sqrt(ss / df)
        lo = np.sqrt(ss / stats.chi2.ppf(0.95, df))
        hi = np.sqrt(ss / stats.chi2.ppf(0.05, df))
        out[m] = {"sd": float(sd), "df": int(df), "lo": float(lo), "hi": float(hi)}
    return out


def centroid(p, m):
    v = np.array([ind.get(m, np.nan) for ind in p["individuals"]], float)
    return float(np.nanmean(v)) if np.isfinite(v).sum() >= max(1, (len(v) + 1) // 2) else np.nan


def value(s, m, group):
    return centroid(s, m) if s["kind"] == "real" else s["values"].get(group, {}).get(m, np.nan)


def usable_measures(group, systems, calibrated, B, budget_limit=1.0, c3_limit=0.5):
    """Measurements used in a group: calibrated in its recording type; every system finite (a nan anywhere
    drops the measurement for the whole group, so nan never shrinks a distance); each preparation's
    mean split-half SE over its individuals below c3_limit BVU (C3, amendment 3); every mapped AI's mismatch-budget change at most budget_limit BVU."""
    use, why = [], {}
    for m in calibrated:
        sd = B.get(m, {}).get("sd", np.nan)
        if not np.isfinite(sd) or sd <= 0:
            why[m] = "no between-individual spread"; continue
        if any(not np.isfinite(value(s, m, group)) for s in systems):
            why[m] = "nan in some system"; continue
        if any(s["kind"] == "real" and s.get("se", {}).get(m, 0) > c3_limit * sd for s in systems):
            why[m] = "C3: unstable in a preparation"; continue
        if any(s["kind"] == "ai" and s.get("budget", {}).get(group, {}).get(m, 0) > budget_limit * sd for s in systems):
            why[m] = "mismatch budget"; continue
        use.append(m)
    return use, why


def mapped(systems, group):
    """Systems that can be placed: preparations with at least 3 individuals; AIs whose matching was reached."""
    return [s for s in systems if (s["kind"] == "real" and len(s["individuals"]) >= 3)
            or (s["kind"] == "ai" and s.get("reached", {}).get(group, False))]


def distance(a, b, measures, B, group, scale="sd"):
    d = []
    for m in measures:
        x, y = value(a, m, group), value(b, m, group)
        d.append(min(abs(x - y) / B[m][scale], CAP))
    return float(np.sqrt(np.mean(np.square(d)))) if d else np.nan


def siblings(a, b):
    if a["id"] == b["id"]:
        return True
    if a["kind"] == "real" and b["kind"] == "real":
        return a.get("dataset") == b.get("dataset") or a.get("species_type") == b.get("species_type")
    if a["kind"] == "ai" and b["kind"] == "ai":
        return a.get("family") == b.get("family")
    return False


def nearest(s, pool, measures, B, group, scale="sd"):
    cands = [o for o in pool if not siblings(s, o)]
    if not cands:
        return None, np.nan
    d = [distance(s, o, measures, B, group, scale) for o in cands]
    i = int(np.argmin(d))
    return cands[i], d[i]


# ---------------------------------------------------------------- hypotheses
def h1(group, preps, ais, measures, B):
    """Brains resemble brains more than AIs: nearest neighbour real for >= 80% of preparations and artificial
    for >= 80% of standard AI families (augmented AIs are never neighbours). Powered if >= MIN_TYPES types."""
    std = [a for a in ais if a["role"] == "standard"]
    pool = preps + std
    types = {p["species_type"] for p in preps}
    rp = [nearest(p, pool, measures, B, group)[0]["kind"] == "real" for p in preps]
    ra = [nearest(a, pool, measures, B, group)[0]["kind"] == "ai" for a in std]
    fp, fa = (float(np.mean(rp)) if rp else np.nan), (float(np.mean(ra)) if ra else np.nan)
    powered = len(types) >= MIN_TYPES and len(measures) >= MIN_MEASURES and len(std) >= 2
    return {"powered": powered, "types": len(types), "real_share": fp, "ai_share": fa,
            "holds": bool(powered and fp >= 0.8 and fa >= 0.8) if powered else None}


def h2(group, preps, ais, measures, B):
    """Some augmented AI lands among the brains (amendment 3): its nearest neighbour among the preparations
    and the standard AI families is a real preparation, leaving out the preparations it was fitted on. With
    fewer than MIN_TYPES preparation types left, undecided."""
    res = {}
    std = [a for a in ais if a["role"] == "standard"]
    for a in [x for x in ais if x["role"] == "augmented"]:
        pool = [p for p in preps if p["id"] not in a.get("fitted_on", [])]
        if len({p["species_type"] for p in pool}) < MIN_TYPES:
            res[a["id"]] = {"decided": False, "why": "too few preparation types left"}; continue
        nb, d = nearest(a, pool + std, measures, B, group)
        res[a["id"]] = {"decided": True, "nearest": nb["id"], "distance": d, "passes": nb["kind"] == "real"}
    return res


def gaps(group, preps, ais, measures, B):
    """H3(a), descriptive: |brain centroid - standard-AI centroid| per measurement, in BVU (capped)."""
    std = [a for a in ais if a["role"] == "standard"]
    out = {}
    for m in measures:
        bc = np.mean([value(p, m, group) for p in preps])
        ac = np.mean([value(a, m, group) for a in std])
        out[m] = float(min(abs(bc - ac) / B[m]["sd"], CAP))
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def brain_centroid(preps, measures, group):
    return {"id": "_brains", "kind": "ai", "family": "_brains", "values": {group: {m: float(np.mean([value(p, m, group) for p in preps])) for m in measures}}}


def h3b(group, preps, pairs, measures, B):
    """H3(b): adding slow state cuts distance to the brain centroid by >= 30% for every (augmented, base)
    pair. Undecided when the group's slow set is empty."""
    if not [m for m in measures if m in SLOW_SET]:
        return {"decided": False, "why": "no slow measurement in use"}
    c = brain_centroid(preps, measures, group)
    red = {aug["id"]: 1 - distance(aug, c, measures, B, group) / distance(base, c, measures, B, group) for aug, base in pairs}
    return {"decided": True, "reductions": red, "holds": all(r >= 0.3 for r in red.values())}


def _boot_diff(a, b, preps, measures, B, group, fn, n=200, seed=0):
    """Bootstrap the difference fn(a_rep) - fn(b_rep) over the systems' replicates, at both ends of the BVU
    interval. Returns {scale: (lo5, hi95)}."""
    rng = np.random.default_rng(seed)
    out = {}
    for scale in ("lo", "hi"):
        ds = []
        ra, rb = a["replicates"][group], b["replicates"][group]
        for _ in range(n):
            xa = {"kind": "ai", "id": "x", "values": {group: ra[rng.integers(len(ra))]}}
            xb = {"kind": "ai", "id": "y", "values": {group: rb[rng.integers(len(rb))]}}
            ds.append(fn(xa, scale) - fn(xb, scale))
        out[scale] = (float(np.percentile(ds, 5)), float(np.percentile(ds, 95)))
    return out


def h4(group, preps, big, small, measures, B):
    """Bigger is not >= 1 BVU closer: the 90% interval of d(big) - d(small) to the brain centroid lies above
    -1 at both ends of the BVU interval."""
    c = brain_centroid(preps, measures, group)
    fn = lambda s, scale: distance(s, c, measures, B, group, scale)
    ci = _boot_diff(big, small, preps, measures, B, group, fn)
    return {"ci": ci, "holds": all(lo > -1 for lo, hi in ci.values())}


def h5(group, preps, mamba, transformer, measures, B):
    """Mamba closer than the transformer on the slow set in use, interval excluding 0 at both BVU ends."""
    slow = [m for m in measures if m in SLOW_SET]
    if not slow:
        return {"decided": False, "why": "no slow measurement in use"}
    c = brain_centroid(preps, slow, group)
    fn = lambda s, scale: distance(s, c, slow, B, group, scale)
    ci = _boot_diff(mamba, transformer, preps, slow, B, group, fn)
    return {"decided": True, "ci": ci, "holds": all(hi < 0 for lo, hi in ci.values())}


def h6(group, preps, cfc, gru, measures, B):
    """Equivalence: CfC minus GRU distance to the brain centroid within +-1 BVU at both interval ends."""
    c = brain_centroid(preps, measures, group)
    fn = lambda s, scale: distance(s, c, measures, B, group, scale)
    ci = _boot_diff(cfc, gru, preps, measures, B, group, fn)
    return {"ci": ci, "holds": all(lo > -1 and hi < 1 for lo, hi in ci.values())}


def h8(group, preps, ais, ids, measures, B):
    """Cultures and organoids have a real nearest neighbour (H1's rule). Undecided if the group is not mapped."""
    std = [a for a in ais if a["role"] == "standard"]
    pool = preps + std
    out = {}
    for i in ids:
        p = next((x for x in preps if x["id"] == i), None)
        if p is None or len(measures) < MIN_MEASURES:
            out[i] = None
        else:
            out[i] = nearest(p, pool, measures, B, group)[0]["kind"] == "real"
    return out
