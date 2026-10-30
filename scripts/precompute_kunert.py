"""Precompute Kunert simulations into the cache, a few at a time.

Usage:  python scripts/precompute_kunert.py --amplitudes 0.5,1,2,4 --seeds 99 [--max 4]
        python scripts/precompute_kunert.py --amplitudes 1 --seeds 0,1,2,3,4,5,100,101,102,103,104,105

Each 16-minute simulation takes roughly half a minute. Already-cached runs are skipped, so
the command can simply be repeated until it reports nothing left to do.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.systems.kunert import KunertModel  # noqa: E402
from nematica.systems.kunert_system import kunert_activation  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--amplitudes", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--cache", default="results/cache/kunert")
    ap.add_argument("--max", type=int, default=4, help="simulations to run in this call")
    args = ap.parse_args()
    model = KunertModel.load()
    todo = [(float(a), int(s)) for a in args.amplitudes.split(",") for s in args.seeds.split(",")]
    done = 0
    for amp, seed in todo:
        t0 = time.time()
        before = len(list(Path(args.cache).glob("*.npz"))) if Path(args.cache).exists() else 0
        kunert_activation(model, amp, seed, args.cache)
        after = len(list(Path(args.cache).glob("*.npz")))
        if after > before:
            done += 1
            print(f"simulated amplitude {amp:g} seed {seed} in {time.time() - t0:.0f} s", flush=True)
            if done >= args.max:
                break
    remaining = sum(1 for _ in todo) - len(list(Path(args.cache).glob("*.npz")))
    print(f"ran {done}; cache now holds {len(list(Path(args.cache).glob('*.npz')))} simulations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
