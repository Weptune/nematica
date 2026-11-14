"""Cross-species rule (docs/MAP.md, amendments 15, 17, 18 and 19). RUN ONLY AFTER the worm and pooled-mouse
measurements, the AI recordings at both instruments, and the independent review.

Amendment 19 (answering review 15):
- The worms are the DISCOVERY set (the candidate was found there, amendment 14); every worm verdict is
  exploratory. The pooled mouse ("R4g", 3 mice) is the only CONFIRMATORY test, of one hypothesis fixed in
  advance: on timescale spread, every counted standard AI lies below the mice.
- Native speed (review 15, item 2): for the temporal measurements (timescale spread, slow memory) an AI
  counts toward a separating side only if its native timescale is at least 1.5 native steps in every
  instance and it was not pre-held; others are reported as "outside calibrated speed".
- Margin (item 5a): an AI is "below" (or "above") only if it lies beyond the real envelope's edge by more
  than max(its own budget for that measurement, 2 x the pooled real SE). Strict version (5b): beyond the
  t(df) 90% prediction interval for a new individual, mean +/- t_0.95(df) sqrt(1 + 1/n) SD.
- C3 (5c) is judged against the lower 90% bound of the ruler (chi-square, df = n - 1).
- An AI is mapped at a measurement if at least 80% of its crops are finite there (the pipeline's rule); a
  mapped standard AI with an undefined value counts as not separating (8a).
- The confirmatory test needs both slow-enough standard families (A1 random RNN and A2 task RNN) mapped
  and counted; otherwise it is "incomplete".
Writes docs/figures/map_species.json."""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_ais as AIS  # noqa: E402
import map_ais_r4a as R4A  # noqa: E402
import map_worm  # noqa: E402
from nematica.map import analysis as An  # noqa: E402

STANDARD = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
TEMPORAL = {"timescale_spread", "slow_fraction"}
MIN_NATIVE_TAU = 1.5
CONFIRM = ("timescale_spread", "below")
CONFIRM_FAMILIES = {"A1", "A2"}


KEEP_INDIVIDUALS = False       # sensitivity (amendment 23): keep every individual, drop measures with a nan


def reals(pid, cal):
    if (KEEP_INDIVIDUALS and pid != "R2") or pid == "R4a":   # R4a: amendment 24, item 6 (per measurement)
        b = json.loads((ROOT / "docs/figures/map_brains.json").read_text())["preparations"][pid]["individuals"]
        return [r for r in b if not r.get("error")]
    if pid == "R2":                                    # review 15, item 8d: the worm map's own nan rule
        W = map_worm.worms(cal)
        b = json.loads((ROOT / "docs/figures/map_brains.json").read_text())["preparations"]["R2"]["individuals"]
        return [r for r in b if r["id"] in W["ids"]]
    b = json.loads((ROOT / "docs/figures/map_brains.json").read_text())["preparations"][pid]["individuals"]
    return [r for r in b if not r.get("error") and all(np.isfinite(r["values"].get(m, np.nan)) for m in cal)]


def ais(pid):
    out = {}
    for aid, (fam, role, _) in AIS.SPECS.items():
        f = AIS.CACHE / f"{aid}_{pid}.pkl"
        if not f.exists():
            continue
        r = pickle.loads(f.read_bytes())
        if (r.get("code_sha256_16") != AIS.code_hash() or r.get("crop_len") != AIS.CROP_LEN.get(pid)
                or (pid == "R4a" and r.get("r4a_wrapper_sha256_16") != R4A.WRAPPER)):
            out[aid] = {"family": fam, "role": role, "mapped": False, "why": "stale or other crop length"}
            continue
        ok = bool(r.get("reached")) and len(r.get("replicates", [])) > 0 and not r.get("error")
        taus = [k.get("native_tau", np.nan) for k in r.get("knobs_per_instance", [])] or [np.nan]
        speed = bool(np.all(np.isfinite(taus)) and min(taus) >= MIN_NATIVE_TAU and not r.get("pre_hold"))
        out[aid] = {"family": fam, "role": role, "mapped": ok, "why": None if ok else (r.get("error") or "not reached"),
                    "native_tau_min": float(np.nanmin(taus)) if np.isfinite(taus).any() else None,
                    "pre_hold": r.get("pre_hold"), "within_calibrated_speed": speed,
                    "stretches_overlap": r.get("stretches_overlap"), "r": r}
    return out


def ai_value(r, m, rng, n=1000):
    reps = r["replicates"]
    fin = [x for x in reps if np.isfinite(x.get(m, np.nan))]
    if not fin or len(fin) < 0.8 * len(reps):
        return np.nan, [np.nan, np.nan]
    g = {}
    for x in fin:
        g.setdefault(x["instance"], []).append(x[m])
    keys = list(g)
    boot = []
    for _ in range(n):
        d = []
        for k in rng.choice(len(keys), len(keys)):
            v = g[keys[k]]
            d += [v[j] for j in rng.integers(len(v), size=len(v))]
        boot.append(np.median(d))
    return float(np.median([x[m] for x in fin])), [float(np.percentile(boot, 5)), float(np.percentile(boot, 95))]


def ruler(vals):
    n = len(vals)
    sd = float(np.std(vals, ddof=1))
    lo = sd * np.sqrt((n - 1) / stats.chi2.ppf(0.95, n - 1))
    return sd, float(lo)


def species(pid, cal, budget_gate):
    R = reals(pid, cal)
    if KEEP_INDIVIDUALS and pid not in ("R2", "R4a"):
        cal = [m for m in cal if all(np.isfinite(r["values"].get(m, np.nan)) for r in R)]
    A = ais(pid)
    rng = np.random.default_rng(0)
    n = len(R)
    out = {"individuals": n, "ids": [r["id"] for r in R], "calibrated": cal, "measures": {},
           "ais": {a: {k: v for k, v in x.items() if k != "r"} for a, x in A.items()}}
    mapped = {a: x for a, x in A.items() if x["mapped"]}
    extra = [m for m in ("shared_fraction", "slow_fraction", "timescale_spread", "coupling_spread") if m not in cal]
    for m in cal + extra:                                 # extra: not calibrated here; descriptive only
        vals = np.array([r["values"].get(m, np.nan) for r in R], float)
        if not np.isfinite(vals).all():
            if m in extra:
                continue
            vals = vals[np.isfinite(vals)]
        sd, sd_lo = ruler(vals)
        se = float(np.sqrt(np.mean(np.square([r["se"].get(m, np.nan) for r in R]))))
        lo, hi = float(vals.min()), float(vals.max())
        tq = stats.t.ppf(0.95, n - 1) * np.sqrt(1 + 1 / n)
        pi = [float(vals.mean() - tq * sd), float(vals.mean() + tq * sd)]
        cnt_ai = [x for x in mapped.values() if x["role"] == "standard"     # review 15 follow-up, item 9: the
                  and (m not in TEMPORAL or x["within_calibrated_speed"])]  # budget over counted AIs only
        budget = An.group_budget([{"id": pid}], [{"at": {pid: x["r"]}} for x in cnt_ai], m)
        gates = {"c3_se_over_ruler": se / sd, "c3_se_over_ruler_lower90": se / sd_lo,
                 "budget_over_ruler": budget / sd if np.isfinite(budget) else np.nan}
        usable = m in cal and gates["c3_se_over_ruler_lower90"] < 0.5 and (
            not budget_gate or (np.isfinite(gates["budget_over_ruler"]) and gates["budget_over_ruler"] <= 1))
        row = {"calibrated": m in cal, "real": vals.tolist(), "envelope": [lo, hi], "prediction_interval90": pi, "ruler_sd": sd,
               "ruler_sd_lower90": sd_lo, "pooled_se": se, "gates": gates, "usable": bool(usable), "ai": {}}
        for a, x in mapped.items():
            v, ci = ai_value(x["r"], m, rng)
            b = x["r"].get("budget", {}).get(m, np.nan)
            margin = float(np.nanmax([b if np.isfinite(b) else np.nan, 2 * se]))
            side = ("undefined" if not np.isfinite(v) else "below" if v < lo - margin
                    else "above" if v > hi + margin else "inside")
            strict = ("undefined" if not np.isfinite(v) else "below" if ci[1] < pi[0]
                      else "above" if ci[0] > pi[1] else "overlap")
            counted = x["role"] == "standard" and (m not in TEMPORAL or x["within_calibrated_speed"])
            raw = "undefined" if not np.isfinite(v) else "below" if v < lo else "above" if v > hi else "inside"
            row["ai"][a] = {"value": v, "ci90": ci, "family": x["family"], "role": x["role"], "margin": margin,
                            "raw_side": raw,
                            "side": side, "strict_side": strict, "counted": counted,
                            "within_calibrated_speed": x["within_calibrated_speed"]}
        cnt = {a: y for a, y in row["ai"].items() if y["counted"]}
        sides, strict = {y["side"] for y in cnt.values()}, {y["strict_side"] for y in cnt.values()}
        row["separating_side"] = next(iter(sides)) if len(sides) == 1 and sides <= {"below", "above"} else None
        row["strict_separating_side"] = (next(iter(strict)) if len(strict) == 1 and strict <= {"below", "above"}
                                         else None)
        row["families_counted"] = sorted({y["family"] for y in cnt.values()})
        row["families_not_counted"] = [f for f in STANDARD if f not in row["families_counted"]]
        out["measures"][m] = row
    return out


def new_mouse_quantile(n, k, q=0.95, sims=40000, seed=7):
    """Amendment 21 (review 15 follow-up, item 7): the q-quantile of a NEW individual's distance (RMS over k
    independent measurements of (value - mean of n) / SD of n) under a normal model, by simulation."""
    rng = np.random.default_rng(seed)
    Z = rng.standard_normal((sims, n + 1, k))
    ref, new = Z[:, :n], Z[:, n]
    d = np.sqrt(np.mean(((new - ref.mean(1)) / ref.std(1, ddof=1)) ** 2, axis=1))
    return float(np.quantile(d, q))


def distance_test(pid, S, cal, cap=10.0, min_measures=2, min_families=5):
    cal = [m for m in cal if m in S["measures"]]
    """Amendments 20 and 21: every counted standard AI farther from the mice than a new mouse would be.
    Threshold: the 95% quantile of a new individual's distance for the AI's number of measurements (the
    leave-one-out envelope is reported only descriptively). AI value: the mean over all its crops (all
    instances), so it is no noisier than a mouse's crop mean; 90% interval by hierarchical bootstrap of that
    mean. An AI counts with at least 1 measurement within calibrated speed."""
    use = [m for m in cal if S["measures"][m]["usable"]]
    if len(use) < min_measures:
        return {"result": "not testable", "why": f"{len(use)} usable measurements", "measures": use}
    R = reals(pid, cal)
    A = {a: x for a, x in ais(pid).items() if x["mapped"]}
    sd = {m: S["measures"][m]["ruler_sd"] for m in use}
    def dist(v, c, ms):
        z = [((v[m] - c[m]) / sd[m]) ** 2 for m in ms]
        return float(min(np.sqrt(np.mean(z)), cap)) if np.all(np.isfinite(z)) else np.nan
    def loo(ms):
        vals = [r["values"] for r in R]
        return max(dist(v, {m: np.mean([w[m] for j, w in enumerate(vals) if j != i]) for m in ms}, ms)
                   for i, v in enumerate(vals))
    rng = np.random.default_rng(1)
    res = {}
    for a, x in A.items():
        ms = [m for m in use if m not in TEMPORAL or x["within_calibrated_speed"]]
        if not ms:
            res[a] = {"counted": False, "why": "no usable measurement within calibrated speed"}
            continue
        reps = x["r"]["replicates"]
        ok = [r for r in reps if all(np.isfinite(r.get(m, np.nan)) for m in ms)]
        if len(ok) < 0.8 * len(reps):
            res[a] = {"counted": x["role"] == "standard", "median": np.nan, "why": "undefined values"}
            continue
        c = {m: float(np.nanmean([r["values"][m] for r in R])) for m in ms}
        g = {}
        for r in ok:
            g.setdefault(r["instance"], []).append(r)
        def mean_of(rs):
            return {m: float(np.mean([r[m] for r in rs])) for m in ms}
        keys, boot = list(g), []
        for _ in range(1000):
            rs = []
            for kk in rng.choice(len(keys), len(keys)):
                v = g[keys[kk]]
                rs += [v[j] for j in rng.integers(len(v), size=len(v))]
            boot.append(dist(mean_of(rs), c, ms))
        thr = new_mouse_quantile(len(R), len(ms))
        res[a] = {"counted": x["role"] == "standard", "family": x["family"], "role": x["role"], "measures": ms,
                  "distance": dist(mean_of(ok), c, ms), "median": dist(mean_of(ok), c, ms),
                  "ci90": [float(np.percentile(boot, 5)), float(np.percentile(boot, 95))],
                  "threshold_new_mouse_q95": thr, "loo_envelope": loo(ms), "crops": len(ok)}
    cnt = {a: r for a, r in res.items() if r.get("counted")}
    fams = sorted({r["family"] for r in cnt.values() if "family" in r})
    if len(fams) < min_families:
        verdict = "incomplete"
    elif any(not np.isfinite(r.get("median", np.nan)) or r["median"] <= r["threshold_new_mouse_q95"]
             for r in cnt.values()):
        verdict = "not confirmed"
    elif all(r["ci90"][0] > r["threshold_new_mouse_q95"] for r in cnt.values()):
        verdict = "confirmed"
    else:
        verdict = "unclear"
    return {"result": verdict, "measures": use, "families_counted": fams, "ais": res}


def allen_tests(pid="R4a"):
    """Amendment 24's five registered tests in the Allen mice."""
    cal = json.loads((ROOT / "docs/figures/map_step2_r4a.json").read_text())["r4a_set"]
    S = species(pid, cal, budget_gate=True)
    def directional(m, required=()):
        row = S["measures"].get(m)
        if row is None or not row.get("calibrated", True):
            return {"result": "not testable", "why": "not calibrated at R4a"}
        if not row["usable"]:
            return {"result": "not testable", "why": "fails C3 or budget", "gates": row["gates"]}
        cnt = {a: y for a, y in row["ai"].items() if y["counted"]}
        miss = [f for f in required if f not in {y["family"] for y in cnt.values()}]
        if miss:
            return {"result": "not testable", "why": f"required family not counted: {miss}"}
        sides = {a: y["side"] for a, y in cnt.items()}
        raws = {a: y["raw_side"] for a, y in cnt.items()}
        if all(v == "below" for v in sides.values()):
            res = "confirmed"
        elif any(v in ("inside", "above") for v in raws.values()):
            res = "refuted"
        else:
            res = "unclear"
        return {"result": res, "sides": sides, "raw_sides": raws, "strict_side": row["strict_separating_side"],
                "families_counted": row["families_counted"]}
    T = {"A coupling spread": directional("coupling_spread"),
         "B slow memory": directional("slow_fraction", ("A1",)),
         "C timescale spread": directional("timescale_spread", ("A1",))}
    row = S["measures"].get("slow_fraction")
    y = (row or {}).get("ai", {}).get("A1-slow")
    if T["B slow memory"]["result"] == "not testable" or y is None:
        T["D slow drives"] = {"result": "not testable", "why": "test B not testable or A1-slow missing"}
    elif y["side"] in ("below", "above"):
        T["D slow drives"] = {"result": "refuted", "side": y["side"], "value": y["value"]}
    else:
        T["D slow drives"] = {"result": "confirmed" if T["B slow memory"]["result"] == "confirmed" else "unclear",
                              "side": y["side"], "value": y["value"], "envelope": row["envelope"]}
    T["E distance"] = distance_test(pid, S, cal)
    return S, T


def main():
    worm_cal = json.loads((ROOT / "docs/figures/map_step2_worm.json").read_text())["worm_set"]
    mouse_cal = json.loads((ROOT / "docs/figures/map_step2_r4g.json").read_text())["r4g_set"]
    # The worm budget is not applied (amendment 19: a stated deviation from amendment 15; with 1,600-frame
    # crops the budget is undefined, see the note under amendment 18). The worms are discovery only.
    W = species("R2", worm_cal, budget_gate=False)
    M = species("R4g", mouse_cal, budget_gate=True)
    m, side = CONFIRM
    row = M["measures"].get(m)
    if row is None or not row.get("calibrated", True):
        conf = {"result": "not testable", "why": f"{m} did not pass step 2 under amendment 17"}
    else:
        fams = set(row["families_counted"])
        complete = CONFIRM_FAMILIES <= fams
        conf = {"measure": m, "predicted_side": side, "usable": row["usable"], "complete": complete,
                "families_counted": row["families_counted"], "separating_side": row["separating_side"],
                "strict_separating_side": row["strict_separating_side"],
                "result": ("not testable (gates)" if not row["usable"] else "incomplete" if not complete
                           else "confirmed" if row["separating_side"] == side else "not confirmed")}
    out = {"discovery_worm": W, "confirmatory_mouse": M, "confirmatory_test": conf,
           "confirmatory_distance_test": distance_test("R4g", M, mouse_cal),
           "exploratory": {k: {"worm": W["measures"].get(k, {}).get("separating_side"),
                               "mouse": M["measures"].get(k, {}).get("separating_side")}
                           for k in sorted(set(W["measures"]) | set(M["measures"]))}}
    global KEEP_INDIVIDUALS
    KEEP_INDIVIDUALS = True
    M2 = species("R4g", mouse_cal, budget_gate=True)
    out["sensitivity_keep_all_mice"] = {"mouse": M2, "distance_test": distance_test("R4g", M2, mouse_cal),
                                        "sides": {k: v["separating_side"] for k, v in M2["measures"].items()}}
    KEEP_INDIVIDUALS = False
    if (ROOT / "docs/figures/map_step2_r4a.json").exists() and any(AIS.CACHE.glob("*_R4a.pkl")):
        AIS.CROP_LEN["R4a"] = R4A.r4a_profile(True)["crop_len"]
        S4, T4 = allen_tests()
        out["confirmatory_allen"] = {"mice": S4, "tests": T4}
        for k, v in T4.items():
            print("ALLEN", k, v["result"], v.get("why", ""))
    (ROOT / "docs/figures/map_species.json").write_text(json.dumps(out, indent=1, default=float))
    print("confirmatory:", conf)
    print("exploratory sides:", out["exploratory"])


if __name__ == "__main__":
    main()
