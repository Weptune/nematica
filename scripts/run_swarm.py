"""Arc 6, first experiment: does individuality change collective behaviour?

For each frozen rotation (configs/splits/copper2026_cv3.yaml) the v11 closed-loop model is
fitted on the training worms (as in run_closed_loop.py). Swarms of 32 worms, 16 minutes, in
an arena of the median real radius:

    twins     each training worm's own model, twice
    average   32 copies of the pooled model (nematica.swarm.engine.average_worm)

each with interactions on and off (pass-through), `--seeds` seeds per rotation. Expectations
were written in the README (Arc 6) before the first run.

Usage:
  python scripts/run_swarm.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --folds configs/splits/copper2026_cv3.yaml [--out docs/figures]
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import from_recording  # noqa: E402
from nematica.data import load_copper_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.export.virtual_worm import MotionLibrary  # noqa: E402
from nematica.swarm import average_worm, run_swarm, swarm_summary  # noqa: E402
from nematica.swarm.metrics import per_worm  # noqa: E402
from nematica.systems.closed_loop import SensoryVAR  # noqa: E402

V11 = dict(senses=True, hazard_from="command_ash", directional=True, speed_map=True,
           sense_scales=(0.25, 0.5, 1, 2, 4), per_worm_rates=True, steer=True, copper_limit=True,
           steer_scales=(0.5, 1, 2, 4, 8), stage_speed=True, sense_ridge_mults=(1.0, 0.1, 0.01, 0.0),
           slow_taus=(0.0, 8.0, 25.0, 50.0), sense_targets=("ASH",))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="docs/figures")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--n", type=int, default=32)
    ap.add_argument("--seed-start", type=int, default=0, help="first seed (clone mode runs one seed from here)")
    ap.add_argument("--p-touch", type=float, default=None)
    ap.add_argument("--contact-mm", type=float, default=None)
    ap.add_argument("--fold", type=int, default=None, help="run only this rotation")
    ap.add_argument("--tag", default="", help="suffix for output files")
    ap.add_argument("--clones", action="store_true",
                    help="also run one homogeneous swarm per training worm (32 copies of it), seed 0 only")
    args = ap.parse_args()
    recs = load_copper_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    by = {r.uid: r for r in recs}
    folds = load_folds(args.folds)["folds"]
    radius = float(np.median([r.meta["arena"]["radius_mm"] for r in recs]))
    rows, worm_rows = [], []
    kw = {}
    if args.p_touch is not None:
        kw["p_touch"] = args.p_touch
    if args.contact_mm is not None:
        kw["contact_mm"] = args.contact_mm
    for fi, pool_uids in enumerate(folds):
        if args.fold is not None and fi != args.fold:
            continue
        t0 = time.time()
        rest = sorted(u for f in folds if f is not pool_uids for u in f)
        val_uids = [rest[len(rest) // 3], rest[2 * len(rest) // 3]]
        train_uids = [u for u in rest if u not in val_uids]
        S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
        train, val, pool = S(train_uids), S(val_uids), S(pool_uids)
        lib = MotionLibrary.from_recordings([by[u] for u in train_uids])
        m = SensoryVAR(**V11).fit(train, val)
        m.calibrate_steering(train, [(by[u].meta["arena"]["radius_mm"], float(by[u].behaviour["dist_from_center_mm"][0]),
                                      by[u].t) for u in train_uids], lib, target="drift", mults=(1, 2, 3, 4, 5, 6, 8, 12))
        avg = average_worm(m)
        template, t = pool[0], by[pool_uids[0]].t
        swarms = {"twins": [m.names[j % len(m.names)] for j in range(args.n)], "average": [avg] * args.n}
        if args.clones:
            swarms = {"twins": swarms["twins"], **{f"clone:{o}": [o] * args.n for o in m.names}}
        print(f"fold {fi}: {len(m.names)} training worms, fitted in {time.time() - t0:.0f} s", flush=True)
        for seed in range(args.seed_start, args.seed_start + (1 if args.clones else args.seeds)):
            for kind, origins in swarms.items():
                for interact in (True, False):
                    rng = np.random.default_rng(10_000 * fi + 100 * seed + 7)   # same starts across conditions
                    run = run_swarm(m, origins, template, lib, radius, t, rng, interact=interact, **kw)
                    row = {"fold": fi, "seed": seed, "swarm": kind, "interact": interact, **swarm_summary(run)}
                    rows.append(row)
                    pw = per_worm(run)
                    for j, o in enumerate(origins):
                        worm_rows.append({"fold": fi, "seed": seed, "swarm": kind, "interact": interact, "worm": j,
                                          "origin": o, **{k: float(v[j]) for k, v in pw.items()}})
                    print(f"  seed {seed} {kind:7s} interact={interact!s:5s} contact {row['contact']:.3f} "
                          f"clusters {row['frac_in_cluster']:.3f} nn {row['nn_dist_mm']:.2f} "
                          f"rev {row['rev_rate']:.2f} (sd {row['sd_rev_rate']:.2f}) near Cu {row['near_copper']:.3f}",
                          flush=True)
        print(f"fold {fi} done ({time.time() - t0:.0f} s)", flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = ("swarm_clones" if args.clones else "swarm_twins_vs_average") + args.tag
    for name, data in ((f"{stem}.csv", rows), (f"{stem}_worms.csv", worm_rows)):
        with (out / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    # summary: mean and seed-to-seed SD per condition
    keys = [k for k in rows[0] if k not in ("fold", "seed", "swarm", "interact")]
    print("\ncondition            " + "  ".join(f"{k[:14]:>14s}" for k in keys))
    for kind in ("twins", "average") if not args.clones else ("twins",):
        for interact in (True, False):
            sel = [r for r in rows if r["swarm"] == kind and r["interact"] == interact]
            print(f"{kind:8s} interact={interact!s:5s} " + "  ".join(
                f"{np.nanmean([r[k] for r in sel]):7.3f}±{np.nanstd([r[k] for r in sel]):5.3f}" for k in keys))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
