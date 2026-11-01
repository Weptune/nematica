"""The reverse test: unc-31 worms (no neuropeptide release) scored as a copy against each
wild-type held-out pool, on every level, with the poke-level equivalence check. Each unc-31
worm counts once, as its own group, compared with every wild-type pool worm (activity and
pokes as recorded).

Usage:
  python scripts/run_reverse_unc31.py --split cv3
"""

from __future__ import annotations

import argparse
import csv
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.scorecard import SPLITS, SPLITS_DIR, FoldRuler, fold_parts, set_norm  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402


def score_recorded(name, worms, ruler):
    """FoldRuler.score, for recorded worms instead of a model: one sample per worm."""
    import numpy as np
    from nematica.bench.causal import response_set, score_sets
    from nematica.bench.perturbational import PCI_LEVELS, pci_set
    from nematica.bench.reference import score_system
    from nematica.bench.scorecard import ACTIVITY_LEVELS, bench_sample, equivalence, poke_tolerances
    rows = []
    samples = [bench_sample(w, ruler.classes, f"{name}:{w.uid}", w.uid) for w in worms]
    rows += [{"kind": "activity", **r} for r in score_system(name, samples, ruler.real_b, ruler.ref)
             if r["metric"] in ACTIVITY_LEVELS]
    tol = poke_tolerances(ruler.pool, ruler.real_c)
    sets = []
    for w in worms:
        rs = response_set(w, f"{name}:{w.uid}")
        rs.group = w.uid
        sets.append(rs)
    for r in score_sets(name, sets, ruler.real_c):
        t = tol.get(r["metric"], {}).get("tolerance")
        rows.append({"kind": "causal", **r, "tolerance": t, "equivalence": equivalence(r, t)})
    ps = []
    for w in worms:
        p = pci_set(w, f"{name}:{w.uid}")
        p.group = w.uid
        ps.append(p)
    rows += [{"kind": "complexity", **r} for r in score_sets(name, ps, ruler.real_p, levels=PCI_LEVELS)]
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw/randi2023_wt_npz")
    ap.add_argument("--unc31", default="data/raw/randi2023_unc31_npz")
    ap.add_argument("--split", choices=tuple(SPLITS), default="cv3")
    ap.add_argument("--out", default="results/reverse_unc31")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    recs = {r.uid: r for r in load_pumpprobe_dir(args.data)}
    unc = [r for r in load_pumpprobe_dir(args.unc31) if sum(1 for c in r.classes if c) >= 20]
    print(f"{len(unc)} unc-31 worms with identities", flush=True)
    folds = load_folds(SPLITS_DIR / SPLITS[args.split])["folds"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for fi in range(len(folds)):
        f = out / f"{args.split}_f{fi}.csv"
        if f.exists():
            continue
        ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=True)
        rows = score_recorded("unc31", unc, ruler)
        with f.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
            w.writeheader()
            w.writerows(rows)
        print(f"{args.split} fold {fi} " + "  ".join(f"{r['metric']}={r['verdict']}" + (f"/{r['equivalence']}" if 'equivalence' in r else "")
                                               for r in rows), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
