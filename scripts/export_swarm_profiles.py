"""Reduce a fitted swarm run to per-worm motion priors for the live web sandbox.

The web sandbox is a behavioral model. These priors carry individual speed and
reversal variation from the fitted closed-loop worms; contact and boundary rules
are simulated afresh in the browser and are explicitly labeled assumptions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def profile(worm: dict, dt: float) -> dict:
    head = np.asarray(worm["head"], dtype=float).reshape(-1, 2)
    reversing = np.asarray(worm["reversing"], dtype=bool)
    delta = np.diff(head, axis=0)
    speed = np.linalg.norm(delta, axis=1) / dt
    moving = speed > 0.015

    def median_speed(mask: np.ndarray, fallback: float) -> float:
        values = speed[mask & moving]
        return float(np.median(values)) if len(values) else fallback

    forward = median_speed(~reversing[:-1], 0.09)
    reverse = median_speed(reversing[:-1], 0.07)
    onsets = int(np.count_nonzero(reversing[1:] & ~reversing[:-1]))
    rate = onsets * 60 / (len(reversing) * dt)
    # Head displacement is noisy near reversals. Use the exported first body
    # segment's orientation instead to estimate typical forward turning.
    angle = np.asarray(worm["angles"], dtype=float).reshape(len(reversing), -1)[:, 0]
    turn = np.abs(np.arctan2(np.sin(np.diff(angle)), np.cos(np.diff(angle))))
    steady = ~reversing[:-1] & ~reversing[1:]
    turn_median = float(np.quantile(turn[steady], 0.25)) if np.any(steady) else 0.12
    return {
        "origin": worm["origin"],
        "forward_mm_s": round(float(np.clip(forward, 0.045, 0.18)), 3),
        "reverse_mm_s": round(float(np.clip(reverse, 0.035, 0.16)), 3),
        "reversals_per_min": round(float(np.clip(rate, 1.0, 7.0)), 2),
        "turn_rad_step": round(float(np.clip(turn_median * 0.5, 0.015, 0.16)), 3),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=Path("lab/public/data/swarm1/swarm.json"))
    ap.add_argument("--out", type=Path, default=Path("web/data/sim/swarm-profiles.js"))
    args = ap.parse_args()
    data = json.loads(args.source.read_text(encoding="utf-8"))
    bundle = {
        "source": "v11 closed-loop individual model run, rotation 0",
        "radius_mm": data["radius_mm"],
        "length_mm": data["length_mm"],
        "profiles": [profile(worm, data["dt"]) for worm in data["worms"]],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("window.NEMATICA_SWARM_PROFILES = " + json.dumps(bundle, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"wrote {args.out}: {len(bundle['profiles'])} profiles")


if __name__ == "__main__":
    main()
