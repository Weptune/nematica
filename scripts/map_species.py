"""Cross-species rule (docs/MAP.md, amendments 15, 17 and 18). RUN ONLY AFTER the worm and pooled-mouse
measurements, the AI recordings at both instruments, and the independent review.

Species 1: worms (R2, 14 baseline worms; measurements passing worm step 2 and C3). Species 2: mouse, R4 with
units pooled in groups of 8 ("R4g", 3 mice; measurements passing step 2 under amendment 17, C3 and budget).
For each usable measurement: the real envelope (min to max over individuals), each AI's median over crops
with a hierarchical bootstrap 90% interval, and the separating side over the standard AI families.
Writes docs/figures/map_species.json."""
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

STANDARD = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]


def reals(pid):
    b = json.loads((ROOT / "docs/figures/map_brains.json").read_text())["preparations"][pid]["individuals"]
    return [r for r in b if not r.get("error")]


def ais(pid):
    out = {}
    for aid, (fam, role, _) in AIS.SPECS.items():
        f = AIS.CACHE / f"{aid}_{pid}.pkl"
        if not f.exists():
            continue
        r = pickle.loads(f.read_bytes())
        if r.get("code_sha256_16") != AIS.code_hash() or r.get("crop_len") != AIS.CROP_LEN[pid]:
            out[aid] = {"family": fam, "role": role, "mapped": False, "why": "stale or other crop length"}
            continue
        ok = bool(r.get("reached")) and len(r.get("replicates", [])) > 0 and not r.get("error")
        out[aid] = {"family": fam, "role": role, "mapped": ok, "why": None if ok else (r.get("error") or "not reached"),
                    "r": r}
    return out


def ai_value(r, m, rng, n=1000):
    reps = [x for x in r["replicates"] if np.isfinite(x.get(m, np.nan))]
    if len(reps) < 0.5 * len(r["replicates"]) or not reps:
        return np.nan, [np.nan, np.nan]
    g = {}
    for x in reps:
        g.setdefault(x["instance"], []).append(x[m])
    keys = list(g)
    boot = []
    for _ in range(n):
        d = []
        for k in rng.choice(len(keys), len(keys)):
            v = g[keys[k]]
            d += [v[j] for j in rng.integers(len(v), size=len(v))]
        boot.append(np.median(d))
    return float(np.median([x[m] for x in reps])), [float(np.percentile(boot, 5)), float(np.percentile(boot, 95))]


def species(pid, usable_rule):
    R = reals(pid)
    A = ais(pid)
    cal, gates = usable_rule(R, A)
    rng = np.random.default_rng(0)
    out = {"individuals": len(R), "gates": gates, "usable": cal, "measures": {}, "ais": {
        a: {k: v for k, v in x.items() if k != "r"} for a, x in A.items()}}
    for m in gates:
        vals = np.array([r["values"][m] for r in R], float)
        lo, hi = float(np.nanmin(vals)), float(np.nanmax(vals))
        row = {"real": vals.tolist(), "envelope": [lo, hi], "ai": {}}
        for a, x in A.items():
            if not x["mapped"]:
                continue
            v, ci = ai_value(x["r"], m, rng)
            row["ai"][a] = {"value": v, "ci90": ci, "family": x["family"], "role": x["role"],
                            "side": "below" if v < lo else "above" if v > hi else "inside",
                            "strict_side": "below" if ci[1] < lo else "above" if ci[0] > hi else "overlap"}
        std = {a: y for a, y in row["ai"].items() if y["role"] == "standard" and np.isfinite(y["value"])}
        fams = sorted({y["family"] for y in std.values()})
        sides = {y["side"] for y in std.values()}
        strict = {y["strict_side"] for y in std.values()}
        row["separating_side"] = next(iter(sides)) if len(sides) == 1 and "inside" not in sides else None
        row["strict_separating_side"] = next(iter(strict)) if len(strict) == 1 and "overlap" not in strict else None
        row["families_present"] = fams
        row["families_missing"] = [f for f in STANDARD if f not in fams]
        row["usable"] = m in cal
        out["measures"][m] = row
    return out


def worm_rule(R, A):
    cal = json.loads((ROOT / "docs/figures/map_step2_worm.json").read_text())["worm_set"]
    se = {m: float(np.sqrt(np.mean(np.square([r["se"].get(m, np.nan) for r in R])))) for m in cal}
    sd = {m: float(np.std([r["values"][m] for r in R], ddof=1)) for m in cal}
    gates = {m: {"c3_se_over_bvu": se[m] / sd[m]} for m in cal}
    return [m for m in cal if gates[m]["c3_se_over_bvu"] < 0.5], gates


def mouse_rule(R, A):
    cal = json.loads((ROOT / "docs/figures/map_step2_r4g.json").read_text())["r4g_set"]
    se = {m: float(np.sqrt(np.mean(np.square([r["se"].get(m, np.nan) for r in R])))) for m in cal}
    sd = {m: float(np.std([r["values"][m] for r in R], ddof=1)) for m in cal}
    mapped = [{"at": {"R4g": x["r"]}} for x in A.values() if x["mapped"]]
    gates = {m: {"c3_se_over_bvu": se[m] / sd[m],
                 "budget_over_bvu": An.group_budget([{"id": "R4g"}], mapped, m) / sd[m]} for m in cal}
    use = [m for m in cal if gates[m]["c3_se_over_bvu"] < 0.5 and np.isfinite(gates[m]["budget_over_bvu"])
           and gates[m]["budget_over_bvu"] <= 1]
    return use, gates


def main():
    S = {"worm (R2)": species("R2", worm_rule), "mouse, pooled units (R4g)": species("R4g", mouse_rule)}
    ms = sorted({m for s in S.values() for m in s["measures"]})
    verdict = {}
    for m in ms:
        sides = {k: s["measures"][m]["separating_side"] for k, s in S.items() if m in s["usable"]}
        uniq = set(sides.values())
        verdict[m] = {"usable_in": list(sides), "sides": sides,
                      "candidate": bool(sides) and len(uniq) == 1 and None not in uniq,
                      "general_two_species": len(sides) == 2 and len(uniq) == 1 and None not in uniq,
                      "incomplete": any(S[k]["measures"][m]["families_missing"] for k in sides)}
    out = {"species": S, "verdict": verdict}
    (ROOT / "docs/figures/map_species.json").write_text(json.dumps(out, indent=1, default=float))
    for m, v in verdict.items():
        print(m, v)


if __name__ == "__main__":
    main()
