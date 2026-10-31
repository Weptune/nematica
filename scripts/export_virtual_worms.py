"""Export "Which one is real?" rounds with full worms: body, path and glowing brain.

For each held-out test worm (frozen split):
  real   its recorded body, path and activity; activity shown per neuron class
  model  a sample from the most realistic model so far (per-worm linear VAR(3) on the
         calcium drive, gamma 0.5, lambda 300, fitted on the training worms). Its
         velocity and reversal state come from the model; body shapes and steering are
         motion-matched from real TRAINING worms (nematica/export/virtual_worm.py)
Both show the template worm's labelled neurons at atlas positions, class by class with the
same scaling; neither shows the copper ring (the model cannot sense copper yet). Which
side is real is random per round.

Usage:
  python scripts/fetch_atlas.py
  python scripts/export_virtual_worms.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --split configs/splits/copper2026.yaml [--out lab/public/data/which2]
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
from nematica.export.replay import _resample_posture  # noqa: E402
from nematica.export.virtual_worm import MotionLibrary, class_levels, write_bundle  # noqa: E402
from nematica.systems.forecasters import CalciumStateSpace, Forecaster, IndividualVAR, LagFeatures  # noqa: E402

MODEL_LABEL = "per-worm linear dynamics on the calcium drive"
METRIC_NAMES = {
    "L1.distribution": "activity values", "L1.timescale": "timescales",
    "L2.correlation": "which neurons move together", "L2.dimension": "dimensionality",
    "L4.leadlag": "who leads, who follows", "L4.dwell": "reversal-state durations",
    "L5.encoding": "tracking velocity", "L5.reversal": "activity during reversals",
}
KEY_NEURONS = ["AVA", "AVE", "AIB", "RIM", "AVB", "RIB", "SMDV", "ASH"]


def unwrap_angles(a: np.ndarray) -> np.ndarray:
    return np.unwrap(np.unwrap(a, axis=1), axis=0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--out", default="lab/public/data/which2")
    ap.add_argument("--start-s", type=float, default=120.0)
    ap.add_argument("--duration-s", type=float, default=420.0)
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
    library = MotionLibrary.from_recordings([by[u] for u in split["train"]])

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
    notes_common = {"positions": "atlas average (Skuhersky et al. 2022) [I]",
                    "activity": "shown per neuron class, scaled 5th-99th percentile within this worm [A]"}
    for i, (real, sim, uid) in enumerate(zip(test, sims, split["test"])):
        rec = by[uid]
        dt = real.dt
        a = int(args.start_s / dt)
        n = min(int(args.duration_s / dt), real.x.shape[1] - a)
        t = rec.t[a:a + n]
        shown = {classes[ci] for ci in range(len(classes)) if real.observed[ci] and np.isfinite(sim.x[ci]).all()}
        neurons = []
        for lab in sorted(rec.labelled(2.0).values(), key=lambda x: x.name):
            if lab.neuron_class not in shown:
                continue
            pos = position_for(lab.name, lab.neuron_class, lab.side, atlas)
            if pos is not None:
                neurons.append({"name": lab.name, "cls": lab.neuron_class, "pos_um": [round(q, 2) for q in pos]})

        # real worm: recorded body and path, class-level activity
        ang, length, _ = _resample_posture(rec.posture["segment_angle"])
        path = -rec.posture["stage_xy_mm"][a:a + n]
        path = path - path[0]
        real_file = f"round_{i + 1}_real.json"
        write_bundle(out / real_file, f"real:{uid}", "real recording (held-out test worm)", t,
                     unwrap_angles(ang[a:a + n]), length, path, rec.behaviour["velocity"][a:a + n],
                     rec.behaviour["reversing"][a:a + n], neurons, class_levels(real.x, classes, neurons, a, n),
                     {**notes_common, "body": "tracked posture and stage path [M]"})

        # model worm: generated brain and behaviour, motion-matched body
        vel, rev = sim.behaviour["velocity"][a:a + n], sim.behaviour["reversing"][a:a + n]
        orient0 = float(np.angle(np.mean(np.exp(1j * ang[a]))))
        m_ang, m_path, cont = library.synthesize(vel, rev, t, heading0=orient0, seed=i)
        model_file = f"round_{i + 1}_model.json"
        write_bundle(out / model_file, f"model:{uid}", f"model: {MODEL_LABEL}", t, unwrap_angles(m_ang),
                     library.length_mm, m_path, vel, rev, neurons, class_levels(sim.x, classes, neurons, a, n),
                     {**notes_common, "body": "velocity and reversal state generated by the model [L]; body shapes "
                      "and steering motion-matched from real training worms [borrowed M]"})

        real_side = "left" if rng.random() < 0.5 else "right"
        rounds.append({"round": i + 1, "left": real_file if real_side == "left" else model_file,
                       "right": model_file if real_side == "left" else real_file,
                       "answer": real_side, "real_uid": uid, "neurons": len(neurons),
                       "clip_continuation": round(cont, 3),
                       "reversal_fraction": {"real": round(float((rec.behaviour['reversing'][a:a + n] > 0.5).mean()), 3),
                                             "model": round(float((rev > 0.5).mean()), 3)}})
        print(f"round {i + 1}: {uid}, {len(neurons)} neurons, {n} frames, real on the {real_side}, "
              f"model body continued its clip {100 * cont:.0f}% of frames")
    index = {"version": "nematica-which/2", "rounds": rounds, "model": MODEL_LABEL, "scorecard": card,
             "key_neurons": KEY_NEURONS,
             "l8": {"model_auc": l8_model.get("auc"), "real_auc": l8_real.get("auc")},
             "note": "Neither worm shows the copper ring: the model cannot sense copper yet. Both brains use the "
                     "same neurons, shown class by class. The model's body shapes and steering are borrowed "
                     "from real training worms; its speed and reversals come from its own brain."}
    (out / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"Level 8: model AUC {l8_model.get('auc')}, other real worms {l8_real.get('auc')}. Wrote {out}/index.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
