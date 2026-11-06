"""Transformer phase 1: the worm test in token time (pre-registered; README "Phase 1").

Usage: python scripts/run_tlab_phase1.py trained|untrained [--ruler]
Output: docs/figures/tlab_phase1.csv (six axes), tlab_phase1_ruler.csv (pool 0)
"""
from __future__ import annotations

import csv
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica import annlab as L  # noqa: E402
from nematica import tlab as T  # noqa: E402
import run_ladder as LD  # noqa: E402
import run_week1 as W1  # noqa: E402

torch.set_num_threads(1)
FIG = ROOT / "docs" / "figures"
N_IND, FRAMES, LEAD, EVERY, KICK_SD, HOLD = 113, 4440, 230, 60, 10.0, 30


def recordings(cond):
    cache = T.CACHE / f"phase1_{cond}.pkl"
    if cache.exists():
        return pickle.load(cache.open("rb"))
    base, _ = T.base_model(steps=3000 if cond == "trained" else 0)
    Tm, E = T.hmm()
    D, Lr = base.cfg["D"], base.cfg["L"]
    n = D * Lr
    hidden = L.design(n, np.random.default_rng(200))
    rng = np.random.default_rng(7)
    recs, t0 = [], time.time()
    for i in range(N_IND):
        net = T.Net(**base.cfg)
        net.load_state_dict(base.state_dict())
        g = torch.Generator().manual_seed(1000 + i)
        with torch.no_grad():
            for p in net.parameters():
                p.mul_(1 + 0.1 * torch.randn(p.shape, generator=g))
        if cond == "trained":
            T.train(net, Tm, E, 50, seed=1000 + i, lr=3e-4)
        with torch.no_grad():
            tok0 = torch.tensor(T.sample(Tm, E, 2000, np.random.default_rng(99)))[None]
            r0 = net(tok0)[1]
        sd = torch.cat([r0[("resid", l)][0] for l in range(Lr)], -1).std(0).numpy() + 1e-6
        obs = (rng.random(n) < 0.5) & ~hidden
        targets = np.flatnonzero(obs)
        kicks = {f: int(rng.choice(targets)) for f in range(LEAD, FRAMES - L.WIN, EVERY)}
        patches = {("resid", l): torch.zeros(1, FRAMES, D) for l in range(Lr)}
        for f, j in kicks.items():
            l, d = divmod(j, D)
            patches[("resid", l)][0, f:f + HOLD, d] += KICK_SD * float(sd[j])
        tok = torch.tensor(T.sample(Tm, E, FRAMES, rng))[None]
        with torch.no_grad():
            r = net(tok, patches)[1]
        y = torch.cat([r[("resid", l)][0] for l in range(Lr)], -1).numpy()
        y = y + 0.1 * sd[None, :] * rng.standard_normal(y.shape)
        out = np.full((FRAMES, n), np.nan)
        out[:, obs] = y[:, obs]
        recs.append(L.as_pumpprobe(out, obs, kicks, f"ind{i:03d}"))
        if i % 20 == 0:
            print(f"{cond}: individual {i} ({(time.time() - t0) / 60:.1f} min)", flush=True)
    pickle.dump(recs, cache.open("wb"))
    return recs


def run_axes(cond):
    recs = recordings(cond)
    ws = [W1.Worm(r, valid_fn=lambda c: True) for r in recs]
    fp = LD.fingerprint(ws)
    fp["evoked_share"] = LD.evoked_share(ws)
    out = FIG / "tlab_phase1.csv"
    rows = [r for r in (csv.DictReader(out.open()) if out.exists() else []) if r["condition"] != cond]
    rows.append({"condition": cond, **{k: round(v, 4) for k, v in fp.items()}})
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[-1]))
        w.writeheader()
        w.writerows(rows)
    print(rows[-1], flush=True)


def run_ruler(cond):
    import warnings
    import run_ann_ruler as R
    from run_worm_stitch import StitchedVAR
    from nematica.bench.scorecard import FoldRuler, fold_parts, set_norm
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    recs = {r.uid: r for r in recordings(cond)}
    uids = sorted(recs)
    perm = np.random.default_rng(1).permutation(uids)
    folds = [sorted(perm[i::3]) for i in range(3)]
    out = FIG / "tlab_phase1_ruler.csv"
    rows = [r for r in (csv.DictReader(out.open()) if out.exists() else []) if r["condition"] != cond]
    ruler = FoldRuler(*fold_parts(recs, folds, 0), pci=False)
    for c in ("var3_spontaneous", "stitch3_hp", "hybrid_kernels"):
        m = StitchedVAR(True, True) if c == "stitch3_hp" else R.make_model(c)
        res = ruler.score(c, m, seed_base=0)
        c1 = next(x for x in res if x["metric"] == "C1.pattern")
        rows.append({"condition": cond, "fold": 0, "copy": c, "echo_agreement": round(1 - c1["system_median"], 4),
                     "real_agreement": round(1 - c1["bio_median"], 4), "verdict": c1["verdict"]})
        print(rows[-1], flush=True)
        with out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[-1]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    cond = sys.argv[1]
    if "--ruler" in sys.argv:
        run_ruler(cond)
    else:
        run_axes(cond)
