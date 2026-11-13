"""The map's analysis, frozen before any brain data is read (docs/MAP.md, amendment 4).

Systems are dicts:
  preparation: {"id", "kind": "real", "group", "dataset", "species_type",
                "individuals": [{measure: value}], "se": {measure: pooled split-half SE}}
  AI:          {"id", "kind": "ai", "family", "role": "standard" | "augmented", "base": family id (augmented),
                "fitted_on": [preparation ids],
                "at": {preparation id: {"values": {measure: value}, "replicates": [{measure: value}, ...],
                                        "reached": bool, "budget": {measure: change over the sweep}}}}
Amendment 4 (F5): every AI is recorded at each preparation's own instrument numbers. An AI-to-preparation
distance uses the AI recorded at that preparation's instrument; an AI-to-AI distance is the mean over the
group's preparations of the distance between the two AIs recorded at the same instrument; the AI's position
for centroids is the mean over the group's preparations.
Every function returns plain numbers, so the decisions can be re-run and checked.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

CAP = 10.0                      # largest contribution of one measurement to a distance, in BVU
MIN_MEASURES = 3
MIN_TYPES = 4                   # distinct species-or-preparation types for a powered group
MIN_INDIVIDUALS = 3             # finite individuals for a preparation centroid (and for mapping)
MIN_REPLICATES = 20             # recording replicates per AI per preparation for H4 to H6 (F8)
SLOW_SET = ("slow_fraction", "timescale_spread", "drift")
C3_LIMIT = 0.5
BUDGET_LIMIT = 1.0


# ---------------------------------------------------------------- values
def _ind_values(p, m):
    v = np.array([ind.get(m, np.nan) for ind in p["individuals"]], float)
    return v[np.isfinite(v)]


def centroid(p, m):
    """Mean of the finite individuals; nan with fewer than MIN_INDIVIDUALS (the same rule as mapping)."""
    v = _ind_values(p, m)
    return float(v.mean()) if len(v) >= MIN_INDIVIDUALS else np.nan


def ai_value(a, m, prep_id):
    return a["at"].get(prep_id, {}).get("values", {}).get(m, np.nan)


def ai_position(a, m, preps):
    """An AI's position for centroids: mean over the group's preparations of its value at each instrument."""
    v = [ai_value(a, m, p["id"]) for p in preps]
    return float(np.mean(v)) if v and np.all(np.isfinite(v)) else np.nan


# ---------------------------------------------------------------- ruler
def bvu(preps, measures):
    """Biological variation unit per measurement: pooled within-preparation SD across individuals
    (preparations with at least MIN_INDIVIDUALS finite values), df = sum(n_i - 1), 90% chi-square interval."""
    out = {}
    for m in measures:
        ss, df = 0.0, 0
        for p in preps:
            v = _ind_values(p, m)
            if len(v) >= MIN_INDIVIDUALS:
                ss += ((v - v.mean()) ** 2).sum()
                df += len(v) - 1
        if df == 0 or ss <= 0:
            out[m] = {"sd": np.nan, "df": df, "lo": np.nan, "hi": np.nan}
            continue
        out[m] = {"sd": float(np.sqrt(ss / df)), "df": int(df),
                  "lo": float(np.sqrt(ss / stats.chi2.ppf(0.95, df))),
                  "hi": float(np.sqrt(ss / stats.chi2.ppf(0.05, df)))}
    return out


def mapped(preps, ais):
    """Preparations with at least MIN_INDIVIDUALS individuals; AIs whose matching was reached at every
    preparation's instrument (the others are reported, not mapped)."""
    P = [p for p in preps if len(p["individuals"]) >= MIN_INDIVIDUALS]
    A = [a for a in ais if all(a["at"].get(p["id"], {}).get("reached", False) for p in P)]
    return P, A


def group_budget(preps, ais, m):
    """Amendment 10 (review 13, item 6): each AI's mismatch-budget change at a preparation (computed by the
    pipeline with common random numbers and its seed-to-seed floor subtracted); the group's budget is the
    **largest** change over AIs and preparations. Missing anywhere: nan (fails the gate)."""
    c = [a["at"].get(p["id"], {}).get("budget", {}).get(m, np.nan) for a in ais for p in preps]
    return float(max(c)) if c and np.all(np.isfinite(c)) else np.nan


TRANSFER_LIMIT = 0.5


def transfer_range(preps, ais, m):
    """Amendment 10 (review 13, item 4), the instrument-transfer gate: how far one AI's value moves when it
    is recorded at the different preparations' instruments of the group; the largest range over AIs. A large
    range means instrument differences, not systems, would set real-to-real distances."""
    r = []
    for a in ais:
        v = [ai_value(a, m, p["id"]) for p in preps]
        if not np.all(np.isfinite(v)):
            return np.nan
        r.append(max(v) - min(v))
    return float(max(r)) if r else np.nan


def usable_measures(preps, ais, calibrated, B, budget_limit=BUDGET_LIMIT, c3_limit=C3_LIMIT):
    """Measurements used in a group: calibrated at the group's instrument numbers (step 2); a finite BVU;
    finite in every mapped system (a nan anywhere drops the measurement for the group, so nan never shrinks a
    distance); every preparation's pooled split-half SE below c3_limit BVU (C3; missing fails); the group's
    budget (group_budget) at most budget_limit BVU (missing fails); every AI's range across the group's
    instruments below TRANSFER_LIMIT BVU (amendment 10)."""
    use, why = [], {}
    for m in calibrated:
        sd = B.get(m, {}).get("sd", np.nan)
        if not np.isfinite(sd) or sd <= 0:
            why[m] = "no between-individual spread"; continue
        if any(not np.isfinite(centroid(p, m)) for p in preps) or \
                any(not np.isfinite(ai_value(a, m, p["id"])) for a in ais for p in preps):
            why[m] = "nan in some system"; continue
        se = [p.get("se", {}).get(m, np.nan) for p in preps]
        if not np.all(np.isfinite(se)) or max(se) >= c3_limit * sd:
            why[m] = "C3: missing or unstable in a preparation"; continue
        b = group_budget(preps, ais, m)
        if not np.isfinite(b) or b > budget_limit * sd:
            why[m] = "mismatch budget: missing or too large"; continue
        tr = transfer_range(preps, ais, m)
        if len(preps) > 1 and (not np.isfinite(tr) or tr >= TRANSFER_LIMIT * sd):
            why[m] = "instrument transfer: an AI moves too much across the group's instruments"; continue
        use.append(m)
    return use, why


# ---------------------------------------------------------------- distances
def _rms(diffs, measures, B, scale):
    d = [min(abs(x) / B[m][scale], CAP) for x, m in zip(diffs, measures)]
    return float(np.sqrt(np.mean(np.square(d)))) if d else np.nan


def distance(a, b, measures, B, preps, scale="sd"):
    """Real-real: centroids. AI-real: the AI recorded at that preparation's instrument. AI-AI: mean over the
    group's preparations of the distance at the same instrument. A dict with kind 'point' (e.g. the brain
    centroid) is compared with an AI's position (mean over instruments) or a preparation's centroid."""
    ka, kb = a["kind"], b["kind"]
    if ka == "ai" and kb == "real":
        a, b, ka, kb = b, a, kb, ka
    if ka == "real" and kb == "real":
        return _rms([centroid(a, m) - centroid(b, m) for m in measures], measures, B, scale)
    if ka == "real" and kb == "ai":
        return _rms([centroid(a, m) - ai_value(b, m, a["id"]) for m in measures], measures, B, scale)
    if ka == "ai" and kb == "ai":
        return float(np.mean([_rms([ai_value(a, m, p["id"]) - ai_value(b, m, p["id"]) for m in measures],
                                   measures, B, scale) for p in preps]))
    pt, o = (a, b) if ka == "point" else (b, a)
    pos = (lambda m: centroid(o, m)) if o["kind"] == "real" else (lambda m: ai_position(o, m, preps))
    return _rms([pt["values"][m] - pos(m) for m in measures], measures, B, scale)


def siblings(a, b):
    """Left out as neighbours: the system itself; same dataset or same species in the same kind of
    preparation; two AIs of the same family and role (F14: an augmented AI is not a sibling of its base)."""
    if a["id"] == b["id"]:
        return True
    if a["kind"] == "real" and b["kind"] == "real":
        return a.get("dataset") == b.get("dataset") or a.get("species_type") == b.get("species_type")
    if a["kind"] == "ai" and b["kind"] == "ai":
        return a.get("family") == b.get("family") and a.get("role") == b.get("role")
    return False


def nearest(s, pool, measures, B, preps, scale="sd"):
    cands = [o for o in pool if not siblings(s, o)]
    if not cands:
        return None, np.nan
    d = [distance(s, o, measures, B, preps, scale) for o in cands]
    i = int(np.argmin(d))
    return cands[i], d[i]


def brain_centroid(preps, measures):
    return {"id": "_brains", "kind": "point", "values": {m: float(np.mean([centroid(p, m) for p in preps]))
                                                        for m in measures}}


# ---------------------------------------------------------------- hypotheses
def powered(preps, measures):
    return len({p["species_type"] for p in preps}) >= MIN_TYPES and len(measures) >= MIN_MEASURES


def h1(preps, ais, measures, B):
    """Brains resemble brains more than AIs: nearest neighbour real for >= 80% of preparations and artificial
    for >= 80% of standard AI families (augmented AIs are never neighbours). Undecided unless powered, at
    least 2 standard AIs, and every system has a candidate neighbour."""
    std = [a for a in ais if a["role"] == "standard"]
    pool = preps + std
    nb_p = [nearest(p, pool, measures, B, preps)[0] for p in preps]
    nb_a = [nearest(a, pool, measures, B, preps)[0] for a in std]
    ok = powered(preps, measures) and len(std) >= 2 and all(x is not None for x in nb_p + nb_a)
    fp = float(np.mean([x["kind"] == "real" for x in nb_p if x is not None])) if nb_p else np.nan
    fa = float(np.mean([x["kind"] == "ai" for x in nb_a if x is not None])) if nb_a else np.nan
    return {"powered": bool(ok), "types": len({p["species_type"] for p in preps}), "real_share": fp,
            "ai_share": fa, "holds": bool(fp >= 0.8 and fa >= 0.8) if ok else None}


def real_nn_median(preps, measures, B):
    d = [nearest(p, preps, measures, B, preps)[1] for p in preps]
    d = [x for x in d if np.isfinite(x)]
    return float(np.median(d)) if d else np.nan


def h2(preps, ais, measures, B):
    """Some augmented AI lands among the brains (F14): undecided unless H1's AI half holds in the group
    (standard AIs keep to themselves, so the rule is not loose). An augmented AI passes if its nearest
    neighbour among the preparations (those it was fitted on left out) and the standard AIs (its base
    included) is a real preparation *and* that distance is at most the median real-to-real nearest-neighbour
    distance. Undecided for a candidate with fewer than MIN_TYPES preparation types left."""
    r1 = h1(preps, ais, measures, B)
    if not r1["powered"] or not r1["ai_share"] >= 0.8:
        return {"decided": False, "why": "H1's AI half does not hold or the group is not powered"}
    std = [a for a in ais if a["role"] == "standard"]
    res = {}
    for a in [x for x in ais if x["role"] == "augmented"]:
        pool = [p for p in preps if p["id"] not in a.get("fitted_on", [])]
        if len({p["species_type"] for p in pool}) < MIN_TYPES:
            res[a["id"]] = {"decided": False, "why": "too few preparation types left"}; continue
        lim = real_nn_median(pool, measures, B)
        nb, d = nearest(a, pool + std, measures, B, preps)
        if nb is None:
            res[a["id"]] = {"decided": False, "why": "no candidate neighbour"}; continue
        res[a["id"]] = {"decided": True, "nearest": nb["id"], "distance": d, "limit": lim,
                        "passes": bool(nb["kind"] == "real" and d <= lim)}
    if not any(v["decided"] for v in res.values()):
        return {"decided": False, "why": "no candidate could be decided", "candidates": res}
    return {"decided": True, "candidates": res, "holds": any(v.get("passes") for v in res.values())}


def gaps(preps, ais, measures, B):
    """H3(a), descriptive: |brain centroid - standard-AI centroid| per measurement, in BVU (capped)."""
    std = [a for a in ais if a["role"] == "standard"]
    out = {}
    for m in measures:
        bc = np.mean([centroid(p, m) for p in preps])
        ac = np.mean([ai_position(a, m, preps) for a in std])
        out[m] = float(min(abs(bc - ac) / B[m]["sd"], CAP))
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def h3b(preps, pairs, measures, B):
    """H3(b): adding slow state cuts distance to the brain centroid by >= 30% for every (augmented, base)
    pair. Undecided when the group's slow set is empty."""
    if not [m for m in measures if m in SLOW_SET]:
        return {"decided": False, "why": "no slow measurement in use"}
    c = brain_centroid(preps, measures)
    red = {aug["id"]: 1 - distance(aug, c, measures, B, preps) / distance(base, c, measures, B, preps)
           for aug, base in pairs}
    return {"decided": True, "reductions": red, "holds": all(r >= 0.3 for r in red.values())}


# ---------------------------------------------------------------- bootstrap (F8)
def _resample_prep(p, rng):
    idx = rng.integers(len(p["individuals"]), size=len(p["individuals"]))
    return {**p, "individuals": [p["individuals"][i] for i in idx]}


def _resample_ai(a, preps, measures, rng):
    """Amendment 10 (review 13, item 7): hierarchical. Replicates carry an `instance` key (a network seed, a
    model checkpoint or text segment set); instances are drawn with replacement, then each drawn instance's
    recordings with replacement, and everything drawn is averaged. Replicates without the key count as one
    instance each."""
    at = {}
    for p in preps:
        reps = a["at"][p["id"]]["replicates"]
        groups = {}
        for i, r in enumerate(reps):
            groups.setdefault(r.get("instance", i), []).append(r)
        keys = list(groups)
        drawn = []
        for k in rng.choice(len(keys), size=len(keys)):
            g = groups[keys[k]]
            drawn += [g[j] for j in rng.integers(len(g), size=len(g))]
        at[p["id"]] = {"values": {m: float(np.mean([r.get(m, np.nan) for r in drawn])) for m in measures}}
    return {**a, "at": at}


MIN_INSTANCES = 3


def enough_replicates(a, preps):
    """At least MIN_REPLICATES recordings from at least MIN_INSTANCES instances at every instrument."""
    for p in preps:
        reps = a["at"].get(p["id"], {}).get("replicates", [])
        if len(reps) < MIN_REPLICATES or len({r.get("instance", i) for i, r in enumerate(reps)}) < MIN_INSTANCES:
            return False
    return True


def boot_diff(a, b, preps, measures, B, n=200, seed=0):
    """90% interval of d(a, brains) - d(b, brains) at both ends of the BVU interval. Each resample draws each
    AI's replicates (as many as it has, with replacement) at every instrument and averages them, and draws
    each preparation's individuals (with replacement) for the brain centroid. BVU is held fixed (its own
    uncertainty is covered by evaluating at both ends of its interval)."""
    rng = np.random.default_rng(seed)
    ds = {"lo": [], "hi": []}
    for _ in range(n):
        P = [_resample_prep(p, rng) for p in preps]
        c = brain_centroid(P, measures)
        xa, xb = _resample_ai(a, preps, measures, rng), _resample_ai(b, preps, measures, rng)
        for scale in ds:
            ds[scale].append(distance(xa, c, measures, B, P, scale) - distance(xb, c, measures, B, P, scale))
    return {s: (float(np.nanpercentile(v, 5)), float(np.nanpercentile(v, 95))) for s, v in ds.items()}


def _paired(name, a, b, preps, measures, B, rule):
    if not powered(preps, measures):
        return {"decided": False, "why": "group not powered"}
    if not (enough_replicates(a, preps) and enough_replicates(b, preps)):
        return {"decided": False, "why": f"fewer than {MIN_REPLICATES} replicates or {MIN_INSTANCES} instances"}
    ci = boot_diff(a, b, preps, measures, B)
    return {"decided": True, "ci": ci, "holds": all(rule(lo, hi) for lo, hi in ci.values())}


def h4(preps, big, small, measures, B):
    """Bigger is not >= 1 BVU closer: the interval of d(big) - d(small) lies above -1 at both BVU ends."""
    return _paired("h4", big, small, preps, measures, B, lambda lo, hi: lo > -1)


def h5(preps, mamba, transformer, measures, B):
    """Mamba closer than the transformer on the slow set in use (RMS over it, like every distance), interval
    excluding 0 at both BVU ends. Undecided when the slow set is empty."""
    slow = [m for m in measures if m in SLOW_SET]
    if not slow:
        return {"decided": False, "why": "no slow measurement in use"}
    return _paired("h5", mamba, transformer, preps, slow, B, lambda lo, hi: hi < 0)


def h6(preps, cfc, gru, measures, B):
    """Equivalence: CfC minus GRU distance to the brain centroid within +-1 BVU at both interval ends."""
    return _paired("h6", cfc, gru, preps, measures, B, lambda lo, hi: lo > -1 and hi < 1)


def h8(preps, ais, ids, measures, B):
    """Cultures and organoids have a real nearest neighbour under H1's rule. Undecided (None) for each if the
    group is not powered, or the system is missing or has no candidate neighbour."""
    std = [a for a in ais if a["role"] == "standard"]
    pool = preps + std
    out = {}
    for i in ids:
        p = next((x for x in preps if x["id"] == i), None)
        if p is None or not powered(preps, measures):
            out[i] = None; continue
        nb = nearest(p, pool, measures, B, preps)[0]
        out[i] = None if nb is None else bool(nb["kind"] == "real")
    return out


# ---------------------------------------------------------------- robustness (F12, F15, F16)
VARIANTS = ("floor 2", "floor 4", "floor 8", "hold", "linear interpolation", "hold 2k")


def robust(verdicts):
    """A verdict holds only if it is the same under every registered variant (timescale floors 2, 4 and 8;
    hold, linear interpolation and a hold of 2k): {variant: True | False | None}. Any None, or a change across
    variants, is undecided (None), reported with each variant's verdict."""
    v = list(verdicts.values())
    if any(x is None for x in v) or len(set(v)) != 1:
        return None
    return v[0]
