"""Export rounds for the "Which one is real?" showcase (lab, ?mode=which).

Each round pairs one held-out test worm (frozen split) with a sample from the most
realistic model so far: per-worm linear VAR(3) on the deconvolved calcium drive
(CalciumStateSpace, gamma 0.5, IndividualVAR lambda 300), fitted on the training worms.

Fairness rules for the display:
  * both brains use the SAME neurons: the template worm's labelled neurons whose class the
    model simulates, at atlas positions [I] (Skuhersky et al. 2022)
  * both are shown class by class (the model has one trace per class; showing the real
    worm's left and right neurons separately would give it away)
  * each brain is display-scaled the same way: 5th to 99th percentile per class [A]
  * which side is real is random per round (seeded)
Brains only: the model has no body yet, so no body is drawn for either.

The reveal carries the model's scorecard: rotating-pool verdicts from
docs/figures/calcium_combined.csv and a fresh Level 8 classifier test on the frozen split.

Usage:
  python scripts/fetch_atlas.py
  python scripts/export_which_real.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --split configs/splits/copper2026.yaml [--out lab/public/data/which]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import from_recording  # noqa: E402
from nematica.bench.discriminability import core_classes, discriminability  # noqa: E402
from nematica.data import load_copper_dir, load_split  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.export.atlas import load_atlas, position_for  # noqa: E402
from nematica.systems.forecasters import CalciumStateSpace, Forecaster, IndividualVAR, LagFeatures  # noqa: E402

MODEL_LABEL = "per-worm linear dynamics on the calcium drive"
METRIC_NAMES = {
    "L1.distribution": "activity values", "L1.timescale": "timescales",
    "L2.correlation": "which neurons move together", "L2.dimension": "dimensionality",
    "L4.leadlag": "who leads, who follows", "L4.dwell": "reversal-state durations",
    "L5.encoding": "tracking velocity", "L5.reversal": "activity during reversals",
}


def scaled(x: np.ndarray) -> np.ndarray:
    lo, hi = np.nanpercentile(x, 5), np.nanpercentile(x, 99)
    return np.clip((x - lo) / max(hi - lo, 1e-9), 0, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--out", default="lab/public/data/which")
    ap.add_argument("--start-s", type=float, default=180.0)
    ap.add_argument("--duration-s", type=float, default=360.0)
    ap.add_argument("--max-ap-um", type=float, default=140.0, help="head region only")
    ap.add_argument("--scorecard", default="docs/figures/calcium_combined.csv")
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    recs = load_copper_dir(Path(args.data))
    split = load_split(args.split)
    classes = tuple(canonical_classes(recs, 0.25))
    by = {r.uid: r for r in recs}
    S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
    train, val, test = S(split["train"]), S(split["val"]), S(split["test"])
    cs = CalciumStateSpace.from_train(train, gamma=0.5)
    model = IndividualVAR(Forecaster("var3", cs, LagFeatures(cs.k, 3, False)), fixed_lam=300).fit(train, val)
    sims = [model.generate(s, np.random.default_rng(100 + i), which=i) for i, s in enumerate(test)]

    # scorecard
    card = []
    p = Path(args.scorecard)
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            if r["system"] == "calcium_g0.5_indiv_lam300":
                card.append({"metric": r["metric"], "what": METRIC_NAMES.get(r["metric"], r["metric"]),
                             "verdict": r["verdict"], "ratio": float(r["distance_ratio"])})
    core = core_classes(test + train + val, 12)
    l8_model = discriminability(test, sims, core, n_perm=60, seed=0)
    l8_real = discriminability(test, train + val, core, n_perm=60, seed=0)

    atlas = load_atlas()
    rng = np.random.default_rng(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rounds = []
    for i, (real, sim, rec) in enumerate(zip(test, sims, [by[u] for u in split["test"]])):
        dt = real.dt
        a = int(args.start_s / dt)
        n = min(int(args.duration_s / dt), real.x.shape[1] - a)
        shown = [ci for ci, c in enumerate(classes)
                 if real.observed[ci] and np.isfinite(sim.x[ci]).all()]
        neurons, rows_for = [], []
        for ci in shown:
            for lab in rec.labels.values():
                if lab.neuron_class != classes[ci] or lab.confidence < 2.0:
                    continue
                pos = position_for(lab.name, lab.neuron_class, lab.side, atlas)   # atlas includes the nose offset
                if pos is None or pos[0] > args.max_ap_um:
                    continue
                if any(nr["name"] == lab.name for nr in neurons):
                    continue
                neurons.append({"name": lab.name, "cls": classes[ci],
                                "pos_um": [round(pos[0], 2), round(pos[1], 2), round(pos[2], 2)]})
                rows_for.append(ci)
        levels = {}
        for key, smp in (("real", real), ("model", sim)):
            sc = {ci: scaled(smp.x[ci, a:a + n]) for ci in set(rows_for)}
            levels[key] = [[int(round(255 * sc[ci][t])) for ci in rows_for] for t in range(n)]
        real_side = "left" if rng.random() < 0.5 else "right"
        doc = {
            "version": "nematica-which/1",
            "round": i + 1,
            "dt": round(dt, 4),
            "n_frames": n,
            "neurons": neurons,
            "left": levels["real"] if real_side == "left" else levels["model"],
            "right": levels["model"] if real_side == "left" else levels["real"],
            "answer": real_side,
            "real_uid": real.origin,
            "model": MODEL_LABEL,
            "provenance": {"real": "M recorded activity, class-averaged", "model": "L generated",
                           "positions": "I atlas average", "display": "A percentile scaling, glow"},
        }
        fname = f"round_{i + 1}.json"
        (out / fname).write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
        rounds.append({"file": fname, "round": i + 1, "neurons": len(neurons)})
        print(f"round {i + 1}: {real.origin}, {len(neurons)} neurons, {n} frames, real on the {real_side}")
    index = {
        "version": "nematica-which/1",
        "rounds": rounds,
        "model": MODEL_LABEL,
        "scorecard": card,
        "l8": {"model_auc": l8_model.get("auc"), "real_auc": l8_real.get("auc")},
        "note": "Brains only: the model has no body yet. Both brains use the same neurons, shown "
                "class by class at atlas positions.",
    }
    (out / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"Level 8: model AUC {l8_model.get('auc')}, other real worms {l8_real.get('auc')}. Wrote {out}/index.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
