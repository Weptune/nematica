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
from nematica.systems.closed_loop import SensoryVAR  # noqa: E402
from nematica.systems.forecasters import (CalciumStateSpace, Debounced, Forecaster,  # noqa: E402
                                          IndividualVAR, LagFeatures)

V11 = dict(senses=True, hazard_from="command_ash", directional=True, speed_map=True,
           sense_scales=(0.25, 0.5, 1, 2, 4), per_worm_rates=True, steer=True, copper_limit=True,
           steer_scales=(0.5, 1, 2, 4, 8), stage_speed=True, sense_ridge_mults=(1.0, 0.1, 0.01, 0.0),
           slow_taus=(0.0, 8.0, 25.0, 50.0), sense_targets=("ASH",))
CL_LABEL = ("closed loop v11: copper reaches the brain only through ASH; the brain decides reversals "
            "and steers its own body")

MODEL_LABEL = "per-worm linear dynamics on the calcium drive (10 frames of memory), reversals read with hysteresis"
METRIC_NAMES = {
    "L1.distribution": "activity values", "L1.timescale": "timescales",
    "L2.correlation": "which neurons move together", "L2.dimension": "dimensionality",
    "L4.leadlag": "who leads, who follows", "L4.dwell": "reversal-state durations",
    "L5.encoding": "tracking velocity", "L5.reversal": "activity during reversals",
    "B.rev_rate": "how often it reverses", "B.rev_duration": "how long reversals last",
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
    ap.add_argument("--scorecard", default="docs/figures/lags_combined.csv")
    ap.add_argument("--lags", type=int, default=10, help="memory of the open-loop brain, frames")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--closed-loop", action="store_true",
                    help="model worm = closed-loop v7 in the real worm's own arena, copper ring shown")
    args = ap.parse_args()
    if args.closed_loop and args.out == "lab/public/data/which2":
        args.out = "lab/public/data/which3"
    if args.closed_loop and args.scorecard == "docs/figures/lags_combined.csv":
        args.scorecard = "docs/figures/closed_loop_v11.csv"

    recs = load_copper_dir(Path(args.data))
    split = load_split(args.split)
    classes = tuple(canonical_classes(recs, 0.25))
    by = {r.uid: r for r in recs}
    S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
    train, val, test = S(split["train"]), S(split["val"]), S(split["test"])
    cs = CalciumStateSpace.from_train(train, gamma=0.5)
    model = Debounced(IndividualVAR(Forecaster(f"var{args.lags}", cs, LagFeatures(cs.k, args.lags, False)),
                                    fixed_lam=300)).fit(train, val)
    library = MotionLibrary.from_recordings([by[u] for u in split["train"]])
    cl_runs = {}
    if args.closed_loop:
        model = SensoryVAR(**V11).fit(train, val)
        model.calibrate_steering(train, [(by[u].meta["arena"]["radius_mm"], float(by[u].behaviour["dist_from_center_mm"][0]),
                                          by[u].t) for u in split["train"]], library,
                                 mults=(1, 2, 3, 4, 5, 6, 8, 12), target="drift")
        sims = []
        for i, (s, u) in enumerate(zip(test, split["test"])):
            r = by[u]
            smp, ang_cl, path_cl, _ = model.simulate(s, r.meta["arena"]["radius_mm"],
                                                     float(r.behaviour["dist_from_center_mm"][0]), library,
                                                     np.random.default_rng(100 + i), i, r.t)
            sims.append(smp)
            cl_runs[u] = (ang_cl, path_cl)
        print("closed loop:", {k: v for k, v in model.info.items() if k in ("sense_scale_mm", "steer_scale_mm", "k_steer", "steer_mult")})
    else:
        sims = [model.generate(s, np.random.default_rng(100 + i), which=i) for i, s in enumerate(test)]

    card = []
    p = Path(args.scorecard)
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            if r["system"] in ("calcium_g0.5_indiv_lam300_hyst", f"calcium_var{args.lags}_hyst") or (
                    args.closed_loop and r["system"].startswith("closed_loop_senses") and "metric" in r
                    and r["metric"] in METRIC_NAMES):
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
        arena_real = arena_model = None
        if args.closed_loop:
            R = float(rec.meta["arena"]["radius_mm"])
            # lab world frame = minus the stage frame, starting at the origin (export/replay.py)
            arena_real = {"centre_mm": np.round(-np.asarray(rec.meta["arena"]["center_mm"])
                                                + rec.posture["stage_xy_mm"][a], 4).tolist(), "radius_mm": R}
        real_file = f"round_{i + 1}_real.json"
        write_bundle(out / real_file, f"real:{uid}", "real recording (held-out test worm)", t,
                     unwrap_angles(ang[a:a + n]), length, path, rec.behaviour["velocity"][a:a + n],
                     rec.behaviour["reversing"][a:a + n], neurons, class_levels(real.x, classes, neurons, a, n),
                     {**notes_common, "body": "tracked posture and stage path [M]"}, arena=arena_real)

        # model worm: generated brain and behaviour, motion-matched body
        vel, rev = sim.behaviour["velocity"][a:a + n], sim.behaviour["reversing"][a:a + n]
        if args.closed_loop:
            ang_cl, path_cl = cl_runs[uid]
            m_ang, m_path, cont = ang_cl[a:a + n], path_cl[a:a + n] - path_cl[a], float("nan")
            arena_model = {"centre_mm": np.round(-path_cl[a], 4).tolist(), "radius_mm": R}
        else:
            orient0 = float(np.angle(np.mean(np.exp(1j * ang[a]))))
            m_ang, m_path, cont = library.synthesize(vel, rev, t, heading0=orient0, seed=i)
        model_file = f"round_{i + 1}_model.json"
        write_bundle(out / model_file, f"model:{uid}", f"model: {CL_LABEL if args.closed_loop else MODEL_LABEL}", t,
                     unwrap_angles(m_ang), library.length_mm, m_path, vel, rev, neurons,
                     class_levels(sim.x, classes, neurons, a, n),
                     {**notes_common, "body": "velocity and reversal state generated by the model [L]; body shapes "
                      "motion-matched from real training worms [borrowed M]" + (
                          "; steering, copper sensing and the path are the model's own, in this worm's arena [L]"
                          if args.closed_loop else "; steering motion-matched [borrowed M]")}, arena=arena_model)

        real_side = "left" if rng.random() < 0.5 else "right"
        rounds.append({"round": i + 1, "left": real_file if real_side == "left" else model_file,
                       "right": model_file if real_side == "left" else real_file,
                       "answer": real_side, "real_uid": uid, "neurons": len(neurons),
                       "clip_continuation": None if cont != cont else round(cont, 3),
                       "reversal_fraction": {"real": round(float((rec.behaviour['reversing'][a:a + n] > 0.5).mean()), 3),
                                             "model": round(float((rev > 0.5).mean()), 3)}})
        print(f"round {i + 1}: {uid}, {len(neurons)} neurons, {n} frames, real on the {real_side}, "
              f"model body continued its clip {100 * cont:.0f}% of frames")
    note = ("Both worms crawl in the real worm's own copper arena (ring). The model worm's brain senses the copper, "
            "decides when to reverse and steers its body; only its body shapes are borrowed from real training "
            "worms." if args.closed_loop else
            "Neither worm shows the copper ring: this model does not sense copper. Both brains use the "
            "same neurons, shown class by class. The model's body shapes and steering are borrowed "
            "from real training worms; its speed and reversals come from its own brain.")
    index = {"version": "nematica-which/2", "rounds": rounds,
             "model": CL_LABEL if args.closed_loop else MODEL_LABEL, "scorecard": card,
             "key_neurons": KEY_NEURONS,
             "l8": {"model_auc": l8_model.get("auc"), "real_auc": l8_real.get("auc")},
             "note": note}
    (out / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"Level 8: model AUC {l8_model.get('auc')}, other real worms {l8_real.get('auc')}. Wrote {out}/index.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
