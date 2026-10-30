"""Validate the benchmark ruler with systems whose answers are known.

Usage:
  python scripts/run_ruler.py --dataset copper --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \
      --split configs/splits/copper2026.yaml [--other-data data/raw/atanas2023_wwweb] [--out results/bench]

Reference pool = the dataset's frozen TEST worms. Systems scored against it:
  real_other_worms     the same dataset's non-test worms (real, never in the pool): must be inside everywhere
  real_other_<cond>    worms of the other dataset, if given, scored separately by condition:
                       unstimulated must be inside; heat-pulse sessions are reported as a finding
  calibration systems  derived from each test worm (see nematica/bench/calib.py), 3 seeds each

Level 6 (environment, population level; nematica/bench/environment.py) uses ALL worms of
an arena dataset, because each worm meets the copper only a few times. Calibrations there
are built from partition-A worms only and compared against partition-B worms.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import LEVELS, build_reference, from_recording, score_system  # noqa: E402
from nematica.bench.calib import CALIBRATIONS, EXPECTED, EXPECTED_ENV  # noqa: E402
from nematica.bench.environment import ENV_METRICS, environment_test  # noqa: E402
from nematica.data import load_copper_dir, load_split, load_wormwideweb_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402


def load_any(folder: Path):
    if any(folder.glob("*-cudata.h5")):
        return load_copper_dir(folder)
    return load_wormwideweb_dir(folder)



def run_environment(recs, classes, args, out: Path) -> None:
    """Level 6: environment test at the population level (all worms of an arena dataset)."""
    allw = [from_recording(r, classes) for r in recs]
    if any("dist_to_boundary" in w.behaviour for w in allw):
        env_rows = []
        for name, fn in CALIBRATIONS.items():
            rng = np.random.default_rng(3000)
            built = {w.origin: fn(w, rng) for w in allw}       # one calibrated copy per worm
            env_rows += environment_test(allw, lambda A, _rng, built=built: [built[s.origin] for s in A],
                                         name, n_partitions=args.env_partitions)
        epath = out / f"ruler_env_{args.dataset}.csv"
        ekeys = list(dict.fromkeys(k for r in env_rows for k in r))
        with epath.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=ekeys)
            w.writeheader()
            w.writerows(env_rows)
        print(f"\nLevel 6 (environment, population level, {args.env_partitions} worm partitions; "
              f"number = share of partitions where the system was further from held-out worms than real worms were):")
        print(f"{'system':22s}" + "".join(f"{m:>22s}" for m in ENV_METRICS))
        e_checked = e_ok = 0
        for name in CALIBRATIONS:
            line = f"{name:22s}"
            for m in ENV_METRICS:
                r = next(x for x in env_rows if x["system"] == name and x["metric"] == m)
                exp = EXPECTED_ENV.get(name, {}).get(m)
                mark = ""
                if exp in ("inside", "outside") and r["verdict"] != "not scored":
                    e_checked += 1
                    e_ok += exp == r["verdict"]
                    mark = " ok" if exp == r["verdict"] else " !!"
                line += f"{r['verdict'] + ' (' + str(r.get('percentile_of_bio', '')) + ')' + mark:>22s}"
            print(line)
        print(f"{e_ok} of {e_checked} designed Level 6 outcomes matched. Wrote {epath}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--other-data")
    ap.add_argument("--other-split")
    ap.add_argument("--min-class-fraction", type=float, default=0.25)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--out", default="results/bench")
    ap.add_argument("--env-partitions", type=int, default=150)
    ap.add_argument("--env-only", action="store_true", help="run only the Level 6 environment test")
    args = ap.parse_args()

    recs = load_any(Path(args.data))
    split = load_split(args.split)
    classes = canonical_classes(recs, args.min_class_fraction)
    by_uid = {r.uid: r for r in recs}
    test = [from_recording(by_uid[u], classes) for u in split["test"]]
    others = [from_recording(by_uid[u], classes) for u in split["train"] + split["val"]]
    print(f"{args.dataset}: {len(classes)} canonical classes (labelled in >= {args.min_class_fraction:.0%} "
          f"of worms), reference pool {len(test)} test worms ({len(test) * (len(test) - 1) // 2} pairs)")

    if args.env_only:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        run_environment(recs, classes, args, out)
        return 0

    ref = build_reference(test)
    rows = []
    rows += score_system("real_other_worms", others, test, ref)
    if args.other_data:
        orecs = load_any(Path(args.other_data))
        if args.other_split:
            keep = set(load_split(args.other_split)["test"])
            orecs = [r for r in orecs if r.uid in keep]
        # score other-dataset worms by condition: stimulated sessions are real but perturbed
        groups: dict[str, list] = {}
        for r in orecs:
            cond = "heat" if "heat" in r.conditions else "unstimulated"
            groups.setdefault(cond, []).append(from_recording(r, classes))
        for cond, samples in sorted(groups.items(), key=lambda x: x[0] != "unstimulated"):
            rows += score_system(f"real_other_{cond}", samples, test, ref)
    for name, fn in CALIBRATIONS.items():
        samples = []
        for seed in range(args.seeds):
            rng = np.random.default_rng(1000 + seed)
            samples += [fn(s, rng) for s in test]
        rows += score_system(name, samples, test, ref)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"ruler_{args.dataset}.csv"
    keys = [k for k in rows[0]]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    metrics = list(LEVELS)
    systems = list(dict.fromkeys(r["system"] for r in rows))
    print("\nVerdict per system and metric (percentile of real worm-to-worm distances in brackets):")
    print(f"{'system':22s}" + "".join(f"{m:>22s}" for m in metrics))
    n_checked = n_ok = 0
    for s in systems:
        line = f"{s:22s}"
        for m in metrics:
            r = next(x for x in rows if x["system"] == s and x["metric"] == m)
            v = r["verdict"]
            if s in EXPECTED:
                exp = EXPECTED[s].get(m)
            elif s == "real_other_heat":
                exp = None          # real but perturbed: no designed answer, reported as a finding
            else:
                exp = "inside" if s.startswith("real") else None
            mark = ""
            if exp in ("inside", "outside") and v != "not scored":
                n_checked += 1
                ok = exp == v
                n_ok += ok
                mark = " ok" if ok else " !!"
            line += f"{v + ' (' + str(r.get('percentile_of_bio', '')) + ')' + mark:>22s}"
        print(line)
    print(f"\n{n_ok} of {n_checked} designed outcomes matched. Wrote {path}")
    print("Ceilings (median within-worm half-vs-half distance) vs biological medians:")
    for m in metrics:
        print(f"  {m:18s} ceiling {np.nanmedian(ref.ceiling[m]):.3f}   worm-to-worm {np.nanmedian(ref.biological[m]):.3f}")
    run_environment(recs, classes, args, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
