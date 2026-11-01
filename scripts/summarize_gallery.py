"""The fingerprint table: every gallery family (results/gallery) and the headline copies
(results/fixed_cv3, results/fixed_blocks1) across the six held-out pools. Per family: watching
tests inside, echo agreement with real worms against real worms with each other, and the
poke-level equivalence verdicts (magnitude under both the x3 and the x1.5 rule).

Usage:  python scripts/summarize_gallery.py   (writes docs/figures/gallery_fingerprint.csv)
"""

from __future__ import annotations

import csv
import json
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.scorecard import (ACTIVITY_LEVELS, SPLITS, SPLITS_DIR, TOL_CONTROL_V2,  # noqa: E402
                                      equivalence, fold_parts, poke_tolerances, set_norm)
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402

HEADLINE = {"hybrid_kernels_regimes_obsfit": "hybrid (pokes)", "var3_spontaneous": "linear VAR (watching)",
            "hybrid_kernels": "plain hybrid"}
LABEL = {"linear-rest": "linear, fitted to recordings", "random-wiring": "same, wiring randomised",
         "task-dense": "task-trained, dense", "task-wired": "task-trained, wiring-shaped",
         "kunert2014": "Kunert 2014 wiring model", "creamer-native": "Creamer et al. (own input)"}


def tolerances_v2() -> dict:
    path = Path("results/gallery/tolerance_v2.json")
    if path.exists():
        return json.loads(path.read_text())
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
    out = {}
    for split in SPLITS:
        folds = load_folds(SPLITS_DIR / SPLITS[split])["folds"]
        for fi in range(len(folds)):
            _, _, pool = fold_parts(recs, folds, fi)
            out[f"{split}_{fi}"] = poke_tolerances(pool, controls=TOL_CONTROL_V2)["C2.magnitude"]["tolerance"]
    path.write_text(json.dumps(out))
    return out


def load() -> dict:
    by = {}                                            # family -> pool -> metric -> row
    for f in Path("results/gallery").glob("*_f*_*.csv"):
        split, fold, fam = f.stem.split("_", 2)
        for r in csv.DictReader(f.open(encoding="utf-8")):
            by.setdefault(fam, {}).setdefault(f"{split}_{fold[1:]}", {})[r["metric"]] = r
    for split, cache in (("cv3", "results/fixed_cv3"), ("blocks1", "results/fixed_blocks1")):
        eqf = Path(cache) / "equivalence.csv"            # scripts/annotate_equivalence.py
        eqs = {(r["fold"], r["system"], r["metric"]): r for r in csv.DictReader(eqf.open(encoding="utf-8"))} if eqf.exists() else {}
        for name in HEADLINE:
            for fi in range(3):
                f = Path(cache) / f"fluct_f{fi}_{name}.csv"
                if f.exists():
                    for r in csv.DictReader(f.open(encoding="utf-8")):
                        e = eqs.get((str(fi), name, r["metric"]))
                        if e:
                            r["equivalence"] = e["equivalence"]
                        by.setdefault(name, {}).setdefault(f"{split}_{fi}", {})[r["metric"]] = r
    return by


def main() -> int:
    tol2 = tolerances_v2()
    by = load()
    rows = []
    for fam, pools in by.items():
        n = len(pools)
        watch = [sum(p[m]["verdict"] == "inside" for m in ACTIVITY_LEVELS if m in p) for p in pools.values()]
        agree = [1 - float(p["C1.pattern"]["system_median"]) for p in pools.values() if p.get("C1.pattern", {}).get("system_median")]
        real = [1 - float(p["C1.pattern"]["bio_median"]) for p in pools.values() if p.get("C1.pattern", {}).get("bio_median")]
        tol1 = {}
        eq = {"C1.pattern": 0, "C3.kinetics": 0, "C2.magnitude": 0, "C2.magnitude.v2": 0}
        for key, p in pools.items():
            for m in ("C1.pattern", "C3.kinetics", "C2.magnitude"):
                r = p.get(m)
                if not r:
                    continue
                eq[m] += r.get("equivalence") == "agrees"
            r = p.get("C2.magnitude")
            if r:
                eq["C2.magnitude.v2"] += equivalence(r, tol2.get(key)) == "agrees"
        rows.append({"family": fam, "label": LABEL.get(fam, HEADLINE.get(fam, fam)), "pools": n,
                     "watching_inside_min": min(watch), "watching_inside_max": max(watch),
                     "echo_agreement_median": round(float(np.median(agree)), 3) if agree else None,
                     "echo_agreement_min": round(min(agree), 3) if agree else None,
                     "echo_agreement_max": round(max(agree), 3) if agree else None,
                     "real_agreement_median": round(float(np.median(real)), 3) if real else None,
                     "pattern_agrees": eq["C1.pattern"], "kinetics_agrees": eq["C3.kinetics"],
                     "magnitude_agrees_x3": eq["C2.magnitude"], "magnitude_agrees_x1.5": eq["C2.magnitude.v2"]})
    rows.sort(key=lambda r: -(r["echo_agreement_median"] or 0))
    with Path("docs/figures/gallery_fingerprint.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['label']:32s} pools {r['pools']}  watching {r['watching_inside_min']}-{r['watching_inside_max']}  "
              f"echo {r['echo_agreement_median']} [{r['echo_agreement_min']}, {r['echo_agreement_max']}] (real {r['real_agreement_median']})  "
              f"pattern {r['pattern_agrees']}  kinetics {r['kinetics_agrees']}  magnitude x3 {r['magnitude_agrees_x3']} x1.5 {r['magnitude_agrees_x1.5']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
