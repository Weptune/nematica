"""The worm map (docs/MAP.md, amendments 12 and 13): descriptive, one preparation (R2, the 14 baseline
worms), every AI recorded through the worm instrument in worm-length crops. RUN ONLY AFTER the worm
measurements (scripts/map_brains.py), the AI recordings (scripts/map_ais.py) and step 2 for worms
(scripts/map_step2_worm.py) exist.

- Ruler: the between-worm SD per measurement (BVU, 13 df).
- Measurements: those passing step 2 at the worm numbers; an AI with a nan in any of them is reported as
  unmapped (the measurement is kept); then the C3 gate (pooled worm SE below 0.5 BVU) and the budget gate
  (largest AI change at most 1 BVU); at least 3 measurements, else no map.
- Envelope: each worm's distance to the centroid of the other 13 (RMS over measurements, BVU, capped at 10);
  the envelope is their maximum, with a bootstrap interval over worms.
- Each AI: every crop is an individual; its summary is the median crop distance to the centroid of all
  worms, with a hierarchical bootstrap interval (instances, then crops). "Worm-like" if the median is at
  most the envelope; its percentile among the worms' leave-one-out distances is reported.
- Pairs (descriptive, the rules of H3(b), H4, H5 and H6): difference of median crop distances, bootstrap.
Writes docs/figures/map_worm.json.
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import map_ais as AIS  # noqa: E402
from nematica.map import analysis as An  # noqa: E402

PAIRS = {"H3b slow drives (A1-slow vs A1)": ("A1-slow", "A1", "reduction"),
         "H3b OU latent (Pythia-410M + OU vs Pythia-410M)": ("A6-410m-ou", "A6-410m", "reduction"),
         "H4 Pythia-1B vs Pythia-14M": ("A6-1b", "A6-14m", "h4"),
         "H5 Mamba-370M vs Pythia-410M (slow set)": ("A7-370m", "A6-410m", "h5"),
         "H6 CfC vs GRU": ("A5", "A3", "h6")}
MIN_MEASURES = 3


def rms(v, c, use, B):
    return An._rms([v[m] - c[m] for m in use], use, B, "sd")


def worms():
    b = json.loads((ROOT / "docs/figures/map_brains.json").read_text())["preparations"]["R2"]
    rows = [r for r in b["individuals"] if not r.get("error")]
    se = {m: float(np.sqrt(np.mean(np.square([r["se"].get(m, np.nan) for r in rows])))) for m in rows[0]["values"]}
    return {"id": "R2", "kind": "real", "dataset": "Atanas 2023", "species_type": "worm",
            "individuals": [r["values"] for r in rows], "se": se, "ids": [r["id"] for r in rows]}


def load_ais(variant=""):
    suf = f"_{variant}" if variant else ""
    out = []
    for aid, (fam, role, _) in AIS.SPECS.items():
        f = AIS.CACHE / f"{aid}_R2{suf}.pkl"
        if f.exists():
            out.append({"id": aid, "kind": "ai", "family": fam, "role": role, "fitted": aid in AIS.FITTED_ON,
                        "at": {"R2": pickle.loads(f.read_bytes())}})
    return out


def centroid(inds, use):
    return {m: float(np.mean([x[m] for x in inds])) for m in use}


def crop_distances(a, c, use, B):
    return [rms(r, c, use, B) for r in a["at"]["R2"]["replicates"]]


def boot_median(a, c, use, B, rng, n=500):
    reps = a["at"]["R2"]["replicates"]
    groups = {}
    for r in reps:
        groups.setdefault(r["instance"], []).append(rms(r, c, use, B))
    keys = list(groups)
    out = []
    for _ in range(n):
        d = []
        for k in rng.choice(len(keys), len(keys)):
            g = groups[keys[k]]
            d += [g[j] for j in rng.integers(len(g), size=len(g))]
        out.append(np.median(d))
    return np.array(out)


def analyse(W, A_all, cal, variant=""):
    inds = W["individuals"]
    finite = lambda a: all(np.isfinite(a["at"]["R2"]["values"].get(m, np.nan)) for m in cal)
    A = [a for a in A_all if a["at"]["R2"]["reached"] and finite(a)]
    B = An.bvu([W], cal)
    use, why = [], {}
    for m in cal:
        sd = B[m]["sd"]
        if not np.isfinite(sd) or sd <= 0:
            why[m] = "no between-worm spread"; continue
        if not np.isfinite(W["se"].get(m, np.nan)) or W["se"][m] >= 0.5 * sd:
            why[m] = "C3"; continue
        if not variant:
            b = An.group_budget([W], A, m)
            if not np.isfinite(b) or b > sd:
                why[m] = "budget"; continue
        use.append(m)
    out = {"variant": variant or "primary", "measures": use, "dropped": why, "bvu": B,
           "mapped_ais": [a["id"] for a in A],
           "unmapped_ais": {a["id"]: ("not reached" if not a["at"]["R2"]["reached"] else "nan in a measurement")
                            for a in A_all if a not in A}}
    if len(use) < MIN_MEASURES:
        out["note"] = f"fewer than {MIN_MEASURES} usable measurements: no map"
        return out
    rng = np.random.default_rng(0)
    loo = [rms(x, centroid([y for j, y in enumerate(inds) if j != i], use), use, B) for i, x in enumerate(inds)]
    env = float(max(loo))
    env_boot = []
    for _ in range(500):
        s = [inds[i] for i in rng.integers(len(inds), size=len(inds))]
        env_boot.append(max(rms(x, centroid([y for j, y in enumerate(s) if j != i], use), use, B) for i, x in enumerate(s)))
    c = centroid(inds, use)
    res = {}
    for a in A:
        d = crop_distances(a, c, use, B)
        med = float(np.median(d))
        bm = boot_median(a, c, use, B, rng)
        res[a["id"]] = {"median_crop_distance": med, "ci90": [float(np.percentile(bm, 5)), float(np.percentile(bm, 95))],
                        "crops": len(d), "worm_like": bool(med <= env),
                        "percentile_among_worms": float(np.mean(np.array(loo) <= med) * 100),
                        "role": a["role"], "family": a["family"], "fitted_on_worms": a["fitted"],
                        "native_tau": a["at"]["R2"].get("native_tau"),
                        "below_calibrated_speed": bool((a["at"]["R2"].get("native_tau") or 99) < 1.5)}
    g = {a["id"]: a for a in A}
    pairs = {}
    for name, (x, y, rule) in PAIRS.items():
        if x not in g or y not in g:
            pairs[name] = {"decided": False, "why": "AI missing or unmapped"}; continue
        ms = [m for m in use if m in An.SLOW_SET] if rule == "h5" else use
        if not ms:
            pairs[name] = {"decided": False, "why": "no slow measurement in use"}; continue
        cx = centroid(inds, ms)
        bx, by = boot_median(g[x], cx, ms, B, rng), boot_median(g[y], cx, ms, B, rng)
        diff = bx - by
        mx = float(np.median(crop_distances(g[x], cx, ms, B)))
        my = float(np.median(crop_distances(g[y], cx, ms, B)))
        ci = [float(np.percentile(diff, 5)), float(np.percentile(diff, 95))]
        verdict = {"reduction": 1 - mx / my >= 0.3, "h4": ci[0] > -1, "h5": ci[1] < 0,
                   "h6": ci[0] > -1 and ci[1] < 1}[rule]
        pairs[name] = {"first": mx, "second": my, "diff_ci90": ci, "rule_holds": bool(verdict),
                       "reduction": 1 - mx / my}
    out.update({"envelope": env, "envelope_ci90": [float(np.percentile(env_boot, 5)), float(np.percentile(env_boot, 95))],
                "worm_loo": dict(zip(W["ids"], loo)), "ais": res, "pairs": pairs,
                "positions": {"worms": {i: {m: x[m] for m in use} for i, x in zip(W["ids"], inds)},
                              "ai_crops": {a["id"]: [{m: r[m] for m in use} for r in a["at"]["R2"]["replicates"]] for a in A}}})
    return out


def main():
    W = worms()
    cal = json.loads((ROOT / "docs/figures/map_step2_worm.json").read_text())["worm_set"]
    res = {"worms": len(W["individuals"]), "calibrated": cal, "primary": analyse(W, load_ais(), cal)}
    for v in ("interp", "noise05", "noise10"):
        A = load_ais(v)
        if A:
            res[v] = analyse(W, A, res["primary"]["measures"] or cal, v)
    (ROOT / "docs/figures/map_worm.json").write_text(json.dumps(res, indent=1, default=float))
    p = res["primary"]
    print("measures", p["measures"], "dropped", p["dropped"], "envelope", p.get("envelope"), p.get("envelope_ci90"))
    for k, v in sorted(p.get("ais", {}).items(), key=lambda kv: kv[1]["median_crop_distance"]):
        print(f"{k:12s} {v['median_crop_distance']:.2f} [{v['ci90'][0]:.2f}, {v['ci90'][1]:.2f}] "
              f"worm-like={v['worm_like']} pct={v['percentile_among_worms']:.0f}")
    for k, v in p.get("pairs", {}).items():
        print(k, v)


if __name__ == "__main__":
    main()
