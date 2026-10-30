"""Level 8 discriminability: can a classifier tell each system from real held-out worms?

Usage:
  python scripts/run_l8.py --dataset copper --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --split configs/splits/copper2026.yaml [--out results/bench] [--perm 100]

Real reference: the test worms (never seen by any system). Systems:
  real_other_worms   real non-test worms (control: should be indistinguishable)
  calibration        independent_shift, frame_shuffle, phase_randomised, gaussian_noise
  independent_ar, joint_var   fitted on training worms
  kunert_noise       Kunert 2014 model at --kunert-amplitude (the benchmark's choice on
                     training worms; uses the simulation cache, so run run_benchmark.py first)
Writes l8_<dataset>.csv.
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
from nematica.bench.calib import CALIBRATIONS  # noqa: E402
from nematica.bench.discriminability import core_classes, discriminability  # noqa: E402
from nematica.data import load_copper_dir, load_split, load_wormwideweb_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.forward.imaging import ImagingParams, estimate_noise_fraction  # noqa: E402
from nematica.systems.baselines import IndependentAR, JointVAR  # noqa: E402
from nematica.systems.kunert import KunertModel  # noqa: E402
from nematica.systems.kunert_system import class_members, simulate_kunert_sample  # noqa: E402


def load_any(folder: Path):
    if any(folder.glob("*-cudata.h5")):
        return load_copper_dir(folder)
    return load_wormwideweb_dir(folder)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--out", default="results/bench")
    ap.add_argument("--min-class-fraction", type=float, default=0.25)
    ap.add_argument("--n-core", type=int, default=12)
    ap.add_argument("--window", type=int, default=50)
    ap.add_argument("--perm", type=int, default=100)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--kunert-amplitude", type=float, default=0.5)
    ap.add_argument("--no-kunert", action="store_true")
    ap.add_argument("--cache", default="results/cache/kunert")
    ap.add_argument("--null-splits", type=int, default=40,
                    help="random real-vs-real splits used to measure the false-alarm rate")
    args = ap.parse_args()

    recs = load_any(Path(args.data))
    split = load_split(args.split)
    classes = tuple(canonical_classes(recs, args.min_class_fraction))
    by_uid = {r.uid: r for r in recs}
    test_recs = [by_uid[u] for u in split["test"]]
    train_recs = [by_uid[u] for u in split["train"]]
    test = [from_recording(r, classes) for r in test_recs]
    train = [from_recording(r, classes) for r in train_recs]
    others = [from_recording(by_uid[u], classes) for u in split["train"] + split["val"]]
    core = core_classes(test + others, args.n_core)
    print(f"{args.dataset}: core classes {', '.join(core)}; window {args.window} frames; "
          f"{args.perm} permutations")

    systems: dict[str, list] = {"real_other_worms": others}
    for name, fn in CALIBRATIONS.items():
        rng = np.random.default_rng(2000)
        systems[name] = [fn(s, rng) for s in test]
    ar, var = IndependentAR.fit(train), JointVAR.fit(train)
    systems["independent_ar"], systems["joint_var"] = [], []
    for seed in range(args.seeds):
        rng = np.random.default_rng(seed)
        systems["independent_ar"] += [ar.generate(s, rng) for s in test]
        systems["joint_var"] += [var.generate(s, rng) for s in test]
    if not args.no_kunert:
        known: dict[str, set] = {}
        for r in recs:
            for lab in r.labels.values():
                known.setdefault(lab.neuron_class, set()).add(lab.name)
        model = KunertModel.load()
        members = class_members(model, classes, known)
        params = ImagingParams(noise_fraction=estimate_noise_fraction(train))
        missing = [c for c in core if c not in members]
        if missing:
            print(f"  note: Kunert model has no neurons for core classes {missing} (scored as 0)")
        systems["kunert_noise"] = [
            simulate_kunert_sample(model, classes, members, s, r.t, args.kunert_amplitude,
                                   seed=100 * seed + i, params=params, cache_dir=args.cache)
            for seed in range(args.seeds) for i, (s, r) in enumerate(zip(test, test_recs))]

    # calibration of the test itself: random splits of ALL real worms into a reference pool of
    # the test-set size and the rest. A calibrated test raises a false alarm ~alpha of the time.
    allw = test + others
    rng = np.random.default_rng(11)
    null_p, null_auc = [], []
    for k in range(args.null_splits):
        idx = rng.permutation(len(allw))
        r = discriminability([allw[i] for i in idx[:len(test)]], [allw[i] for i in idx[len(test):]],
                             core, window=args.window, n_perm=60, seed=k)
        null_p.append(r["p"])
        null_auc.append(r["auc"])
    if null_p:
        fa = float(np.mean(np.array(null_p) < 0.05))
        print(f"test calibration on {args.null_splits} random real-vs-real splits: false-alarm rate "
              f"{fa:.3f} at alpha 0.05, AUC median {np.median(null_auc):.2f}, max {np.max(null_auc):.2f}")

    rows = []
    print(f"\n{'system':22s}{'AUC':>7s}{'null p95':>10s}{'p':>8s}  verdict")
    for name, samples in systems.items():
        t0 = time.time()
        r = discriminability(test, samples, core, window=args.window, n_perm=args.perm, seed=0)
        r = {"system": name, **r}
        rows.append(r)
        print(f"{name:22s}{r.get('auc', float('nan')):7.3f}{r.get('null_p95', float('nan')):10.3f}"
              f"{r.get('p', float('nan')):8.3f}  {r['verdict']}  ({time.time() - t0:.0f} s)")

    if null_p:
        rows.append({"system": "_calibration_random_real_splits", "auc": round(float(np.median(null_auc)), 3),
                     "null_p95": round(float(np.percentile(null_auc, 95)), 3), "p": round(fa, 3),
                     "verdict": f"false-alarm rate {fa:.3f} over {len(null_p)} splits"})
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (out / f"l8_{args.dataset}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {out / f'l8_{args.dataset}.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
