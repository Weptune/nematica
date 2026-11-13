"""Assemble the map and run the registered decisions (docs/MAP.md, analysis.py), per recording group.
RUN ONLY AFTER brain measurements exist (scripts/map_brains.py) and the AIs are recorded (scripts/map_ais.py).

Measurement sets come from step 2 (docs/figures/map_step2.json, `group_sets`); the gates (C3, budget,
instrument transfer, nan) are applied at the primary variant; verdicts are recomputed with the AIs'
"hold2k" and "interp" recordings where present (`analysis.robust`). Writes docs/figures/map_result.json.
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
import map_step1 as s1  # noqa: E402
from nematica.map import analysis as An  # noqa: E402

H2_CANDIDATES = ["A1-slow", "A6-410m-ou", "A10"]
PAIRS_H3B = [("A1-slow", "A1"), ("A6-410m-ou", "A6-410m")]
H4 = ("A6-1b", "A6-14m")
H5 = ("A7-370m", "A6-410m")
H6 = ("A5", "A3")
H8 = ["R9", "R10b", "R10d", "R10c"]


def preps_of(group):
    b = json.loads((ROOT / "docs/figures/map_brains.json").read_text())["preparations"]
    out = []
    for pid in AIS.GROUPS[group]:
        rows = [r for r in b.get(pid, {}).get("individuals", []) if not r.get("error")]
        if not rows:
            continue
        se = {m: float(np.sqrt(np.mean(np.square([r["se"].get(m, np.nan) for r in rows])))) for m in rows[0]["values"]}
        out.append({"id": pid, "kind": "real", "dataset": s1.PREPS[pid]["source"], "species_type": s1.PREPS[pid]["type"],
                    "individuals": [r["values"] for r in rows], "se": se})
    return out


def ais_of(group, variant=""):
    suf = f"_{variant}" if variant else ""
    out = []
    for aid, (fam, role, _) in AIS.SPECS.items():
        at = {}
        for pid in AIS.GROUPS[group]:
            f = AIS.CACHE / f"{aid}_{pid}{suf}.pkl"
            if f.exists():
                at[pid] = pickle.loads(f.read_bytes())
        if at:
            out.append({"id": aid, "kind": "ai", "family": fam, "role": role,
                        "fitted_on": AIS.FITTED_ON.get(aid, []), "at": at})
    return out


def decide(P, A, use, B):
    g = lambda i: next((a for a in A if a["id"] == i), None)
    r = {"H1": An.h1(P, A, use, B), "H2": An.h2(P, [a for a in A if a["role"] == "standard" or a["id"] in H2_CANDIDATES], use, B),
         "gaps": An.gaps(P, A, use, B)}
    pairs = [(g(x), g(y)) for x, y in PAIRS_H3B if g(x) and g(y)]
    r["H3b"] = An.h3b(P, pairs, use, B) if pairs else {"decided": False, "why": "AIs missing"}
    for h, (x, y), fn in (("H4", H4, An.h4), ("H5", H5, An.h5), ("H6", H6, An.h6)):
        r[h] = fn(P, g(x), g(y), use, B) if g(x) and g(y) else {"decided": False, "why": "AIs missing"}
    r["H8"] = An.h8(P, A, H8, use, B)
    return r


def verdict(x):
    if isinstance(x, dict):
        return x.get("holds") if x.get("decided", x.get("powered", True)) else None
    return x


def main():
    step2 = json.loads((ROOT / "docs/figures/map_step2.json").read_text())
    res = {}
    for group in AIS.GROUPS:
        P0, A0 = preps_of(group), ais_of(group)
        P, A = An.mapped(P0, A0)
        calibrated = step2["group_sets"].get(group, [])
        B = An.bvu(P, calibrated)
        use, why = An.usable_measures(P, A, calibrated, B)
        out = {"preparations": [p["id"] for p in P], "ais": [a["id"] for a in A],
               "unmapped_ais": [a["id"] for a in A0 if a not in A], "calibrated": calibrated,
               "measures": use, "dropped": why, "bvu": B}
        if len(use) >= An.MIN_MEASURES:
            prim = decide(P, A, use, B)
            out["primary"] = prim
            variants = {"hold": {k: verdict(v) for k, v in prim.items() if k not in ("gaps",)}}
            for var in ("hold2k", "interp"):
                Av = [a for a in ais_of(group, var) if a["id"] in {x["id"] for x in A}]
                if len(Av) == len(A):
                    variants[var] = {k: verdict(v) for k, v in decide(P, Av, use, B).items() if k != "gaps"}
            out["variants"] = variants
            out["robust"] = {k: An.robust({v: variants[v][k] for v in variants}) if not isinstance(variants["hold"][k], dict)
                             else None for k in variants["hold"]}
        # the map itself: every system's position on the measures in use (AIs: mean over instruments)
        out["positions"] = {**{p["id"]: {m: An.centroid(p, m) for m in use} for p in P},
                            **{a["id"]: {m: An.ai_position(a, m, P) for m in use} for a in A}}
        res[group] = out
    (ROOT / "docs/figures/map_result.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({g: {k: v for k, v in r.items() if k in ("measures", "robust")} for g, r in res.items()}, indent=1, default=str))


if __name__ == "__main__":
    main()
