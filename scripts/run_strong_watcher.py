"""The strongest watcher we can build: AtlasGRU, trained only on stimulation-free stretches,
poked with the standard clamp protocol and scored on the poke test like every copy.
Pre-registered 6 Nov 2026 (README "The strongest watcher we can build").

Usage:  python scripts/run_strong_watcher.py [--copies gru64_watch,gru128ss_watch] [--folds 0,1,2]
Output: docs/figures/strong_watcher.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.bench.causal import window  # noqa: E402
from nematica.bench.scorecard import SPLITS, SPLITS_DIR, FoldRuler, fold_parts, set_norm  # noqa: E402
from nematica.data.pumpprobe import PumpProbe, load_pumpprobe_dir  # noqa: E402
from nematica.data.splits import load_folds  # noqa: E402
from nematica.systems.causal_models import AtlasGRU  # noqa: E402

OUT = Path("docs/figures/strong_watcher.csv")


class GRUWatch(AtlasGRU):
    """AtlasGRU with the clamp protocol of ClassVAR.simulate: the stimulated class is held at its
    pre-pulse model value plus the stimulated neuron's measured response for the response window;
    the clamped value is what the network reads at the next step, so the poke spreads only
    through what the network learned by watching."""

    def simulate(self, rec: PumpProbe, rng: np.random.Generator, burn: int = 200,
                 noise_gain=None, quiet=None) -> PumpProbe:
        import torch
        C = len(self.classes)
        idx = {c: i for i, c in enumerate(self.classes)}
        own = [c for c in sorted(set(rec.classes)) if c in idx]
        row_of = {c: i for i, c in enumerate(own)}
        seen = np.zeros(C, bool)
        seen[[idx[c] for c in own]] = True
        T = rec.n_frames
        npre, npost = window(rec.dt)
        sd = np.nanstd(rec.x, axis=1)
        clamp, stims_out = {}, []
        for k, f in rec.stims:
            c = rec.classes[k]
            if c not in idx or f - npre < 0 or f + npost > T or not sd[k] > 0:
                continue
            tr = (rec.x[k, f:f + npost] - np.nanmean(rec.x[k, f - npre:f])) / sd[k]
            for t, v in enumerate(tr):
                if np.isfinite(v):
                    clamp[f + t] = (idx[c], f, float(v))
            stims_out.append((row_of[c], f))
        obs = torch.tensor(seen.astype(np.float32)).view(1, 1, C)
        z = np.zeros((C, T + burn), dtype=np.float32)
        h, x, base = None, torch.zeros(1, 1, C), {}
        with torch.no_grad():
            for t in range(1, T + burn):
                mu, lv, h = self.net(x, obs, h)
                sdv = np.exp(0.5 * lv.numpy().ravel())
                nxt = np.clip(mu.numpy().ravel() + sdv * rng.standard_normal(C), -8, 8)
                nxt[~seen] = 0.0
                tt = t - burn
                if tt in clamp:
                    ci, f0, v = clamp[tt]
                    if (ci, f0) not in base:
                        base[(ci, f0)] = z[ci, t - 1]
                    nxt[ci] = base[(ci, f0)] + v
                z[:, t] = nxt
                x = torch.tensor(nxt, dtype=torch.float32).view(1, 1, C)
        out = z[[idx[c] for c in own], burn:].astype(float)
        return PumpProbe(uid=rec.uid, x=out, names=own, classes=own, stims=stims_out, dt=rec.dt,
                         all_stim_frames=list(rec.all_stim_frames))


MAKE = {
    "gru64_watch": lambda: GRUWatch(hidden=64, steps=1500),
    "gru128ss_watch": lambda: GRUWatch(hidden=128, steps=4000, sampled=True),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="cv3")
    ap.add_argument("--copies", default="gru64_watch,gru128ss_watch")
    ap.add_argument("--folds", default="0,1,2")
    args = ap.parse_args()
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    import torch
    torch.set_num_threads(2)
    set_norm("fluct")
    recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
    folds = load_folds(SPLITS_DIR / SPLITS[args.split])["folds"]
    rows = list(csv.DictReader(OUT.open(encoding="utf-8"))) if OUT.exists() else []
    done = {(r["fold"], r["copy"]) for r in rows}
    for fi in [int(f) for f in args.folds.split(",")]:
        todo = [c for c in args.copies.split(",") if (str(fi), c) not in done]
        if not todo:
            continue
        ruler = FoldRuler(*fold_parts(recs, folds, fi), pci=False)
        for name in todo:
            t0 = time.time()
            m = MAKE[name]()
            m.name = name
            res = ruler.score(name, m, seed_base=1000 * fi)
            c1 = next(r for r in res if r["metric"] == "C1.pattern")
            rows.append({"fold": fi, "copy": name, "echo_agreement": round(1 - c1["system_median"], 4),
                         "real_agreement": round(1 - c1["bio_median"], 4), "verdict": c1["verdict"],
                         "equivalence": c1.get("equivalence", ""), "val_nll": m.info.get("val_nll"),
                         "minutes": round((time.time() - t0) / 60, 1)})
            print(rows[-1], flush=True)
            with OUT.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
                w.writeheader()
                w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
