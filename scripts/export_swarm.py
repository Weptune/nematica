"""Export one simulated swarm (arc 6) for the lab's swarm view (lab ?mode=swarm).

Fits the v11 closed-loop model on rotation 0's training worms (as scripts/run_swarm.py),
runs one twin swarm (each training worm's own model, twice) with interactions on, and
writes lab/public/data/swarm1/swarm.json: per worm, head positions, body posture reduced
to `--points` segment angles, reversal state and touch, every `--every` frames.

Usage:
  python scripts/export_swarm.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --folds configs/splits/copper2026_cv3.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import from_recording  # noqa: E402
from nematica.data import load_copper_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.export.virtual_worm import MotionLibrary  # noqa: E402
from nematica.swarm import run_swarm, swarm_summary  # noqa: E402
from nematica.systems.closed_loop import SensoryVAR  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_swarm import V11  # noqa: E402


def reduce_angles(a: np.ndarray, n: int) -> np.ndarray:
    """(..., K) segment angles -> (..., n) by circular means over equal groups."""
    K = a.shape[-1]
    edges = np.linspace(0, K, n + 1).round().astype(int)
    return np.stack([np.angle(np.mean(np.exp(1j * a[..., lo:hi]), axis=-1)) for lo, hi in zip(edges[:-1], edges[1:])],
                    axis=-1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--folds", required=True)
    ap.add_argument("--out", default="lab/public/data/swarm1")
    ap.add_argument("--n", type=int, default=32)
    ap.add_argument("--every", type=int, default=2)
    ap.add_argument("--points", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    recs = load_copper_dir(Path(args.data))
    classes = tuple(canonical_classes(recs, 0.25))
    by = {r.uid: r for r in recs}
    folds = load_folds(args.folds)["folds"]
    radius = float(np.median([r.meta["arena"]["radius_mm"] for r in recs]))
    pool_uids = folds[0]
    rest = sorted(u for f in folds[1:] for u in f)
    val_uids = [rest[len(rest) // 3], rest[2 * len(rest) // 3]]
    train_uids = [u for u in rest if u not in val_uids]
    S = lambda uids: [from_recording(by[u], classes) for u in uids]  # noqa: E731
    train, val, pool = S(train_uids), S(val_uids), S(pool_uids)
    lib = MotionLibrary.from_recordings([by[u] for u in train_uids])
    m = SensoryVAR(**V11).fit(train, val)
    m.calibrate_steering(train, [(by[u].meta["arena"]["radius_mm"], float(by[u].behaviour["dist_from_center_mm"][0]),
                                  by[u].t) for u in train_uids], lib, target="drift", mults=(1, 2, 3, 4, 5, 6, 8, 12))
    origins = [m.names[j % len(m.names)] for j in range(args.n)]
    t = by[pool_uids[0]].t
    run = run_swarm(m, origins, pool[0], lib, radius, t, np.random.default_rng(100 * args.seed + 7), interact=True)
    summ = swarm_summary(run)
    sl = slice(None, None, args.every)
    ang = reduce_angles(run.angles[:, sl], args.points)
    T = ang.shape[1]
    worms = []
    for j in range(args.n):
        worms.append({
            "origin": origins[j],
            "head": np.round(run.heads[j, sl], 3).ravel().tolist(),
            "angles": np.round(ang[j], 2).ravel().tolist(),
            "reversing": run.states[j, sl].astype(int).tolist(),
            "touch": run.touched[j, sl].astype(int).tolist(),
        })
    bundle = {"format": "nematica-swarm/1", "radius_mm": radius, "length_mm": run.length_mm,
              "dt": run.dt * args.every, "frames": T, "points": args.points,
              "notes": {"model": "v11 closed loop (each worm its own model, twins)", "rotation": 0,
                        "interactions": "touch reversal p 0.3, exclusion at 0.1 mm [assumptions]",
                        "summary": {k: round(float(v), 3) for k, v in summ.items()}},
              "worms": worms}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "swarm.json").write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out / 'swarm.json'} ({(out / 'swarm.json').stat().st_size / 1e6:.1f} MB), {summ}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
