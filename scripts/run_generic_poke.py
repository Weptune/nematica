"""Validity check (3 Nov 2026, exploratory): does the worm poke test measure neuron-to-neuron
cause and effect, or mostly a stereotyped response to ANY poke?

The poke-trained copy (hybrid_kernels) answers a poke of class i by adding, to every other
class j, the average response of j to pokes of i in the training worms. The generic copy is the
same in every respect except that the response of j is its average response to pokes of ALL
stimulated classes: it knows that something was poked, not what. If the generic copy passes
the test about as well as the poke-trained copy, the test mostly measures a generic response
to stimulation (for example a state change or a side effect of the light), and the gap between
watching and poking says little about specific causal structure. If it fails while the
poke-trained copy passes, the test measures stimulus-specific cause and effect.

Scored exactly like every copy: split cv3, all 3 pools, fluctuation norm, unchanged ruler.
Output: docs/figures/generic_poke.csv
"""
import csv
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nematica.bench.scorecard import SPLITS, SPLITS_DIR, FoldRuler, fold_parts, set_norm  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from run_same_worms import make_model  # noqa: E402

OUT = Path("docs/figures/generic_poke.csv")


def make_generic():
    m = make_model("hybrid_kernels")
    fit0 = m.fit

    def fit(train, val):
        fit0(train, val)
        by_resp = defaultdict(list)
        for (ci, cj), h in m.kernels.items():
            if ci != cj:
                by_resp[cj].append(h)
        L = min(len(h) for hs in by_resp.values() for h in hs)
        generic = {cj: np.mean([h[:L] for h in hs], axis=0) for cj, hs in by_resp.items()}
        m.kernels = {(ci, cj): (h if ci == cj else generic[cj]) for (ci, cj), h in m.kernels.items()}
        return m

    m.fit = fit
    m.name = "generic_kernels"
    return m


def main() -> int:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
    folds = load_folds(SPLITS_DIR / SPLITS["cv3"])["folds"]
    rows = []
    for fi in range(len(folds)):
        ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=False)
        for name, m in (("hybrid_kernels", make_model("hybrid_kernels")), ("generic_kernels", make_generic())):
            res = ruler.score(name, m, seed_base=1000 * fi)
            c1 = next(r for r in res if r["metric"] == "C1.pattern")
            rows.append({"fold": fi, "copy": name, "echo_agreement": round(1 - c1["system_median"], 4),
                         "real_agreement": round(1 - c1["bio_median"], 4), "verdict": c1["verdict"],
                         "equivalence": c1.get("equivalence", "")})
            print(rows[-1], flush=True)
            with OUT.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
