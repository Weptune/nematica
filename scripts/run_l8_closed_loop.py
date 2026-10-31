"""Level 8 (classifier two-sample test) for the closed-loop copper model, on the frozen split.

Does running the brain in closed loop (copper input, discrete reversals, a body) change how
easily a classifier tells its neural activity from real held-out worms, compared with the
open-loop calcium model (AUC 0.94)? Same features and settings as scripts/run_l8.py.

Usage:
  python scripts/run_l8_closed_loop.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \\
      --split configs/splits/copper2026.yaml [--out results/l8_closed_loop]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import from_recording  # noqa: E402
from nematica.bench.discriminability import core_classes, discriminability  # noqa: E402
from nematica.data import load_copper_dir, load_split  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.export.virtual_worm import MotionLibrary  # noqa: E402
from nematica.systems.closed_loop import SensoryVAR  # noqa: E402
from nematica.systems.forecasters import CalciumStateSpace, Debounced, Forecaster, IndividualVAR, LagFeatures  # noqa: E402

V6 = dict(senses=True, hazard_from="command_fixed", directional=True, speed_map=True,
          sense_scales=(0.25, 0.5, 1, 2, 4), per_worm_rates=True, steer=True, copper_limit=True,
          steer_scales=(0.5, 1, 2, 4, 8), stage_speed=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--out", default="results/l8_closed_loop")
    ap.add_argument("--perm", type=int, default=100)
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()
    recs = load_copper_dir(Path(args.data))
    split = load_split(args.split)
    classes = tuple(canonical_classes(recs, 0.25))
    by = {r.uid: r for r in recs}
    S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
    train, val, test = S(split["train"]), S(split["val"]), S(split["test"])
    core = core_classes(test + train + val, 12)
    lib = MotionLibrary.from_recordings([by[u] for u in split["train"]])

    cl = SensoryVAR(**V6).fit(train, val)
    cl.calibrate_steering(train, [(by[u].meta["arena"]["radius_mm"], float(by[u].behaviour["dist_from_center_mm"][0]),
                                   by[u].t) for u in split["train"]], lib)
    cs = CalciumStateSpace.from_train(train, gamma=0.5)
    ol = Debounced(IndividualVAR(Forecaster("var3", cs, LagFeatures(cs.k, 3, False)), fixed_lam=300)).fit(train, val)

    systems = {"real_other_worms": train + val, "open_loop_calcium_hyst": [], "closed_loop_v6": []}
    for seed in range(args.seeds):
        for i, (s, u) in enumerate(zip(test, split["test"])):
            r = by[u]
            rng = np.random.default_rng(1000 * seed + i)
            systems["open_loop_calcium_hyst"].append(ol.generate(s, rng, which=seed * len(test) + i))
            smp, _, _, _ = cl.simulate(s, r.meta["arena"]["radius_mm"], float(r.behaviour["dist_from_center_mm"][0]),
                                       lib, rng, seed * len(test) + i, r.t)
            systems["closed_loop_v6"].append(smp)
    rows = []
    for name, samples in systems.items():
        res = discriminability(test, samples, core, n_perm=args.perm, seed=0)
        rows.append({"system": name, **{k: v for k, v in res.items() if not isinstance(v, (list, dict, np.ndarray))}})
        print(name, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items() if k != "system"})
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (out / "l8_closed_loop.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
