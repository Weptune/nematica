"""Closed loop in the copper arena (arc 5): does a model worm that senses copper respond to it
like real worms? Scored at Level 6 (population test, held-out pools) and on the pairwise
levels, against the identical model that is blind to copper.

For each frozen rotation (configs/splits/copper2026_cv3.yaml): models and the motion library
are fitted on the other worms; each held-out worm's arena (radius, starting distance) hosts
`--seeds` simulated worms; Level 6 partitions are drawn within the held-out pool.

Usage:
  python scripts/run_closed_loop.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --folds configs/splits/copper2026_cv3.yaml [--out results/closed_loop]
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import build_reference, combine_folds, from_recording, score_system  # noqa: E402
from nematica.bench.cv import print_table  # noqa: E402
from nematica.bench.environment import environment_test_folds  # noqa: E402
from nematica.data import load_copper_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.export.virtual_worm import MotionLibrary  # noqa: E402
from nematica.systems.closed_loop import SensoryVAR  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="results/closed_loop")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--seed-offset", type=int, default=0, help="shifts every simulation seed (replicates)")
    ap.add_argument("--variants", default="v2", choices=("v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10"))
    args = ap.parse_args()
    recs = load_copper_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    by = {r.uid: r for r in recs}
    folds = load_folds(args.folds)["folds"]
    # v2: directional sense (proximity x facing the copper), sensing distance chosen on
    # validation worms, speed per state from real speed quantiles, motion matching aware of
    # reversal ends and recent turning. The blind control is identical apart from the senses.
    v2 = dict(hazard_from="none", directional=True, speed_map=True, sense_scales=(0.25, 0.5, 1, 2, 4))
    variants = {"senses": dict(senses=True, **v2), "blind": dict(senses=False, **v2)}
    if args.variants == "v3":
        # v3: each model worm gets its own reversal rates (calibrated in open loop on its
        # training worm), with reversals either independent of the brain or driven by the
        # command interneurons
        variants = {"senses_rates": dict(senses=True, **v2, per_worm_rates=True),
                    "senses_command": dict(senses=True, **{**v2, "hazard_from": "command"}, per_worm_rates=True),
                    "blind_rates": dict(senses=False, **v2, per_worm_rates=True)}
    if args.variants == "v5":
        # v5: as v4, plus the brain's own predicted reversal drive in the hazard
        variants = {"senses_drive_fixed": dict(senses=True, **{**v2, "hazard_from": "drive_fixed"},
                                               per_worm_rates=True)}
    if args.variants == "v6":
        # v6: v4 plus slow steering away from copper (gain fitted on training worms, checked
        # by indirect inference; length scale chosen on validation worms) and impassable
        # copper beyond the deepest crossing seen in training worms
        variants = {"senses_steer": dict(senses=True, **{**v2, "hazard_from": "command_fixed"}, per_worm_rates=True,
                                         steer=True, copper_limit=True, steer_scales=(0.5, 1, 2, 4, 8),
                                         stage_speed=True),
                    "blind_limit": dict(senses=False, **v2, per_worm_rates=True)}
    if args.variants == "v7":
        # v7: v6 with the steering gain set so simulated training worms drift away from
        # copper (0.5 to 2 mm) as fast as the real training worms do
        variants = {"senses_steer_drift": dict(senses=True, **{**v2, "hazard_from": "command_fixed"},
                                               per_worm_rates=True, steer=True, copper_limit=True,
                                               steer_scales=(0.5, 1, 2, 4, 8), stage_speed=True,
                                               steer_target="drift")}
    if args.variants == "v8":
        # v8: v7 with 10 frames of brain memory (the open-loop model that passes Level 8)
        variants = {"senses_steer_drift_lags10": dict(senses=True, **{**v2, "hazard_from": "command_fixed"},
                                                      per_worm_rates=True, steer=True, copper_limit=True,
                                                      steer_scales=(0.5, 1, 2, 4, 8), stage_speed=True,
                                                      steer_target="drift", lags=10)}
    if args.variants == "v9":
        # v9: copper reaches reversals only through the brain (hazard = command neurons + ASH,
        # no direct copper term; copper input to the brain unpenalised if validation prefers)
        variants = {"senses_ash": dict(senses=True, **{**v2, "hazard_from": "command_ash"}, per_worm_rates=True,
                                       steer=True, copper_limit=True, steer_scales=(0.5, 1, 2, 4, 8),
                                       stage_speed=True, steer_target="drift", sense_ridge_mults=(1.0, 0.1, 0.01, 0.0))}
    if args.variants == "v10":
        # v10: v9 plus a tonic copper input (time constant chosen on validation worms);
        # v9_pen: v9 with the copper weights penalised like the rest (is the distribution miss
        # from the unpenalised weights?)
        base9 = dict(senses=True, **{**v2, "hazard_from": "command_ash"}, per_worm_rates=True, steer=True,
                     copper_limit=True, steer_scales=(0.5, 1, 2, 4, 8), stage_speed=True, steer_target="drift")
        variants = {"senses_ash_tonic": dict(**base9, sense_ridge_mults=(1.0, 0.1, 0.01, 0.0),
                                             slow_taus=(8.0, 25.0, 50.0)),
                    "senses_ash_pen": dict(**base9, sense_ridge_mults=(1.0,))}
    if args.variants == "v4":
        # v4: command neurons set reversal timing around a copper effect fitted first, alone
        variants = {"senses_command_fixed": dict(senses=True, **{**v2, "hazard_from": "command_fixed"},
                                                 per_worm_rates=True)}
    pools = {v: [] for v in variants}
    pair_rows = {v: [] for v in variants}
    stats = {v: [] for v in variants}
    for fi, pool_uids in enumerate(folds):
        t0 = time.time()
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        val_uids = [rest[len(rest) // 3], rest[2 * len(rest) // 3]]
        train_uids = [u for u in rest if u not in val_uids]
        S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
        pool, train, val = S(pool_uids), S(train_uids), S(val_uids)
        lib = MotionLibrary.from_recordings([by[u] for u in train_uids])
        ref = build_reference(pool)
        for vname, kw in variants.items():
            kw = dict(kw)
            target = kw.pop("steer_target", "slope")
            m = SensoryVAR(**kw).fit(train, val)
            if kw.get("steer"):
                m.calibrate_steering(train, [(by[u].meta["arena"]["radius_mm"],
                                              float(by[u].behaviour["dist_from_center_mm"][0]), by[u].t)
                                             for u in train_uids], lib, target=target,
                                     mults=(1, 2, 4, 8, 16) if target == "slope" else (1, 2, 3, 4, 5, 6, 8, 12))
            print(f"  fold {fi} {vname}: {m.info}", flush=True)
            built = {}
            for i, (s, uid) in enumerate(zip(pool, pool_uids)):
                r = by[uid]
                sims = []
                for seed in range(args.seeds):
                    smp, _, _, _ = m.simulate(s, r.meta["arena"]["radius_mm"], float(r.behaviour["dist_from_center_mm"][0]),
                                              lib, np.random.default_rng(1000 * (seed + args.seed_offset) + 31 * fi + i), seed * len(pool) + i, r.t)
                    sims.append(smp)
                    d = smp.behaviour["dist_to_boundary"]
                    stats[vname].append({"near_or_beyond_0.5mm": float(np.mean(d < 0.5)), "beyond": float(np.mean(d < 0))})
                built[uid] = sims
            pools[vname].append((pool, lambda A, _rng, built=built: [x for s in A for x in built[s.origin]]))
            all_sims = [x for v in built.values() for x in v]
            rows = score_system(m.name, all_sims, pool, ref, return_boot=True)
            pair_rows[vname].append(rows)
        print(f"fold {fi} done ({time.time() - t0:.0f} s)", flush=True)

    real_near = [float(np.mean(by[u].behaviour["dist_to_boundary_mm"] < 0.5)) for u in by]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows_all = []
    print(f"\nTime within 0.5 mm of copper or beyond it: real worms {100 * np.median(real_near):.1f}% (median)")
    for vname in variants:
        st = stats[vname]
        print(f"  {vname}: {100 * np.median([x['near_or_beyond_0.5mm'] for x in st]):.1f}% "
              f"(beyond the boundary {100 * np.median([x['beyond'] for x in st]):.1f}%)")
    print("\nLevel 6 (environment, held-out pools combined):")
    for vname in variants:
        rows = environment_test_folds(pools[vname], f"closed_loop_{vname}", n_partitions=150)
        rows_all += rows
        print("  " + vname.ljust(8) + "  ".join(f"{r['metric']}: {r['verdict']} (share further {r.get('percentile_of_bio', '-')})" for r in rows))
    print("\nPairwise levels (held-out pools combined):")
    comb = []
    for vname in variants:
        comb += combine_folds(pair_rows[vname])
    print_table(comb)
    rows_all += comb
    keys = list(dict.fromkeys(k for r in rows_all for k in r))
    suffix = f"_rep{args.seed_offset}" if args.seed_offset else ""
    with (out / f"closed_loop_{args.variants}{suffix}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows_all)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
