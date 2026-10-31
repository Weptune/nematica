"""Generalisation: copper-trained models scored against Atanas et al. 2023 worms.
Design and expectations: README, "Generalisation".

Usage:
  python scripts/run_cross_dataset.py --copper data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 \\
      --atanas data/raw/atanas2023_wwweb [--out results/cross_dataset]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench import build_reference, from_recording, score_system  # noqa: E402
from nematica.bench.discriminability import core_classes, discriminability  # noqa: E402
from nematica.data import load_copper_dir, load_wormwideweb_dir  # noqa: E402
from nematica.data.canonical import canonical_classes  # noqa: E402
from nematica.systems.forecasters import CalciumStateSpace, Debounced, Forecaster, IndividualVAR, LagFeatures  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--copper", required=True)
    ap.add_argument("--atanas", required=True)
    ap.add_argument("--out", default="results/cross_dataset")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--perm", type=int, default=60)
    args = ap.parse_args()
    crecs = load_copper_dir(Path(args.copper))
    arecs = load_wormwideweb_dir(Path(args.atanas))
    classes = tuple(canonical_classes(crecs, 0.25))
    copper = [from_recording(r, classes) for r in crecs]
    base = [from_recording(r, classes) for r in arecs if "baseline" in r.conditions]
    heat = [from_recording(r, classes) for r in arecs if "heat" in r.conditions]
    uids = sorted(r.uid for r in crecs)
    val_uids = [uids[len(uids) // 3], uids[2 * len(uids) // 3]]
    by = {s.origin: s for s in copper}
    train = [by[u] for u in uids if u not in val_uids]
    val = [by[u] for u in val_uids]
    ref = build_reference(base)
    core = core_classes(base + copper, 12)
    print(f"copper train {len(train)}, val {len(val)}; Atanas baseline {len(base)}, heat {len(heat)}")

    systems = {"copper_real_worms": copper, "atanas_heat_worms": heat}
    for lags in (3, 10):
        cs = CalciumStateSpace.from_train(train, gamma=0.5)
        m = Debounced(IndividualVAR(Forecaster(f"var{lags}", cs, LagFeatures(cs.k, lags, False)), fixed_lam=300))
        m.fit(train, val)
        systems[f"calcium_var{lags}_hyst"] = [m.generate(t, np.random.default_rng(1000 * sd + i), which=sd * len(base) + i)
                                              for sd in range(args.seeds) for i, t in enumerate(base)]
    rows = []
    for name, samples in systems.items():
        scored = score_system(name, samples, base, ref)
        l8 = discriminability(base, samples, core, n_perm=args.perm, seed=0)
        for r in scored:
            ratio = r["system_median"] / r["bio_median"] if r.get("bio_median") else np.nan
            rows.append({**{k: v for k, v in r.items() if k != "_boot"}, "distance_ratio": round(float(ratio), 3),
                         "l8_auc": l8.get("auc"), "l8_p": l8.get("p")})
        inside = sum(r["verdict"] == "inside" for r in scored)
        scoredn = sum(r["verdict"] != "not scored" for r in scored)
        print(f"{name:24s} inside {inside}/{scoredn}  L8 AUC {l8.get('auc')} (p {l8.get('p')})  " +
              "  ".join(f"{r['metric'].split('.')[1][:8]} {r['verdict'][:3]} {r['system_median'] / r['bio_median']:.2f}"
                        for r in scored if r.get("bio_median")), flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (out / "cross_dataset.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
