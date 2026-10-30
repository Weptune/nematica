"""First fidelity report: score systems under test against real test worms.

Usage:
  python scripts/run_benchmark.py --dataset copper --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --split configs/splits/copper2026.yaml [--out results/bench] [--seeds 2]

Systems (all fitted or tuned on TRAINING worms only):
  real_other_worms   real non-test worms (sanity: should be inside everywhere)
  independent_ar     one AR(4) process per neuron class
  joint_var          VAR(1) over core classes + velocity + reversal state
  kunert_noise       Kunert 2014 connectome model, coloured-noise drive, through the imaging model
  gaussian_noise     floor
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import LEVELS, build_reference, from_recording, score_system  # noqa: E402
from nematica.bench.calib import gaussian_noise  # noqa: E402
from nematica.bench.report import plot_profile  # noqa: E402
from nematica.data import load_copper_dir, load_split, load_wormwideweb_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.forward.imaging import ImagingParams, estimate_noise_fraction  # noqa: E402
from nematica.systems.baselines import IndependentAR, JointVAR  # noqa: E402
from nematica.systems.kunert import KunertModel  # noqa: E402
from nematica.systems.kunert_system import class_members, simulate_kunert_sample  # noqa: E402


SHORT = {"inside": "ins", "outside": "out", "too typical": "typ"}

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
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--min-class-fraction", type=float, default=0.25)
    ap.add_argument("--amplitudes", default="0.5,1,2,4,8")
    ap.add_argument("--no-kunert", action="store_true")
    ap.add_argument("--cache", default="results/cache/kunert")
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
    known_names: dict[str, set] = {}
    for r in recs:
        for lab in r.labels.values():
            known_names.setdefault(lab.neuron_class, set()).add(lab.name)

    ref = build_reference(test)
    rows = []
    rows += score_system("real_other_worms", others, test, ref)

    t0 = time.time()
    ar = IndependentAR.fit(train)
    var = JointVAR.fit(train)
    ar_s, var_s = [], []
    for seed in range(args.seeds):
        rng = np.random.default_rng(seed)
        ar_s += [ar.generate(s, rng) for s in test]
        var_s += [var.generate(s, rng) for s in test]
    rows += score_system("independent_ar", ar_s, test, ref)
    rows += score_system("joint_var", var_s, test, ref)
    print(f"baselines fitted on {len(train)} training worms and generated in {time.time() - t0:.1f} s "
          f"(joint_var models {var.core.size} core classes)")

    # Kunert: choose the drive amplitude on TRAINING worms only (median L2.correlation distance)
    if args.no_kunert:
        args.amplitudes = ""
    model = KunertModel.load()
    members = class_members(model, classes, known_names)
    params = ImagingParams(noise_fraction=estimate_noise_fraction(train))
    print(f"Kunert model covers {len(members)} of {len(classes)} canonical classes; "
          f"noise fraction from training worms {params.noise_fraction:.2f}")
    l2 = LEVELS["L2.correlation"]["fn"]
    best = None
    for amp in [float(a) for a in args.amplitudes.split(",") if a]:
        t1 = time.time()
        tpl = train[0]
        s = simulate_kunert_sample(model, classes, members, tpl, train_recs[0].t, amp, seed=99, params=params,
                                   cache_dir=args.cache)
        d = np.nanmedian([l2(s, r) for r in train[1:]])
        print(f"  amplitude {amp:g}: median L2.correlation distance to training worms {d:.3f} ({time.time() - t1:.0f} s)")
        if np.isfinite(d) and (best is None or d < best[1]):
            best = (amp, d)
    if best is not None:
        amp = best[0]
        print(f"  chosen amplitude {amp:g}")
        ku_s = []
        for seed in range(args.seeds):
            for i, (s, r) in enumerate(zip(test, test_recs)):
                ku_s.append(simulate_kunert_sample(model, classes, members, s, r.t, amp,
                                                   seed=100 * seed + i, params=params, cache_dir=args.cache))
        rows += score_system("kunert_noise", ku_s, test, ref)

    rng = np.random.default_rng(7)
    rows += score_system("gaussian_noise", [gaussian_noise(s, rng) for s in test], test, ref)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with (out / f"fidelity_{args.dataset}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    metrics = list(LEVELS)
    systems = list(dict.fromkeys(r["system"] for r in rows))
    print("\nFidelity profile (percentile of real worm-to-worm distances; inside = within the range):")
    print(f"{'system':18s}" + "".join(f"{m:>17s}" for m in metrics))
    for s in systems:
        line = f"{s:18s}"
        for m in metrics:
            r = next((x for x in rows if x["system"] == s and x["metric"] == m), None)
            if r is None or r["verdict"] == "not scored":
                line += f"{'n/a':>17s}"
            else:
                tag = SHORT[r["verdict"]] + " " + format(r["percentile_of_bio"], ".2f")
                line += f"{tag:>17s}"
        print(line)
    print("\nIndividuality (spread among the system's own samples / real worm-to-worm spread; real worms = 1):")
    for s in systems:
        vals = [r.get("self_spread_ratio") for r in rows if r["system"] == s and LEVELS.get(r["metric"], {}).get("primary")]
        vals = [v for v in vals if v is not None]
        if vals:
            print(f"  {s:18s} median over primary metrics {np.median(vals):.2f}")
    try:
        plot_profile(rows, metrics, systems, out / f"fidelity_{args.dataset}.png")
        print(f"\nWrote {out / f'fidelity_{args.dataset}.csv'} and .png")
    except ImportError:
        print(f"\nWrote {out / f'fidelity_{args.dataset}.csv'} (install matplotlib for the figure)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
