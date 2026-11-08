"""Exploratory (8 Nov 2026, after the individuality calibration failed): where do fingerprints come from in lab
networks with identical wiring? Lab only; no worm data. Varies the network's gain (rho) and the split."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
import run_individuality as RI  # noqa: E402
from nematica import annlab as L  # noqa: E402

orig = L.make_brain


def with_rho(rho):
    def mk(*a, **k):
        k["rho"] = rho
        return orig(*a, **k)
    return mk


if __name__ == "__main__":
    for rho in (0.5, 0.9, 1.3, 1.8):
        L.make_brain = with_rho(rho)
        try:
            recs, nears = RI.lab_recs(0.0, n_ind=60)
        finally:
            L.make_brain = orig
        for split in ("alternate", "time"):
            A, B = RI.build(recs, nears, split=split)
            S = RI.IV.agreement_matrix(A, B, "routing")
            ex = RI.IV.excess(S); ex = ex[np.isfinite(ex)]
            rng = np.random.default_rng(0)
            bs = [np.median(ex[rng.integers(0, len(ex), len(ex))]) for _ in range(1000)]
            lo, hi = np.percentile(bs, [2.5, 97.5])
            sat = np.mean([np.nanmean(np.abs(r.x) > 0.9) for r in recs])
            RI.log(f"EXPLORATORY fingerprint source, identical wiring, rho {rho}, {split}: routing excess {np.median(ex):+.4f} "
                   f"[{lo:+.4f}, {hi:+.4f}]; within {np.nanmedian(np.diag(S)):.3f}; share of |activity| > 0.9: {sat:.3f}")


def fixed_obs_run(spread=0.3, label="fixed obs and schedule"):
    """Same as lab_recs(0.0) but every individual records the same units and gets the same poke schedule."""
    import run_ladder as LD
    br0 = L.make_brain(rho=1.3, share=0.0, tau=90.0, seed=0, q=0.2)
    hidden = L.design(br0.n, np.random.default_rng(200))
    g = np.random.default_rng(7)
    obs = (g.random(br0.n) < 0.5) & ~hidden
    targets = np.flatnonzero(obs)
    kicks = {f: int(g.choice(targets)) for f in range(LD.LEAD, L.FRAMES - L.WIN, L.EVERY)}
    out = {}
    for label, same_noise_seed in ((label, False),):
        recs, nears = [], []
        saved = LD.NEIGH
        try:
            for i in range(60):
                gg = np.random.default_rng(5000 + i)
                neigh = np.array([gg.choice([u for u in range(br0.n) if u != v], size=2, replace=False) for v in range(br0.n)])
                LD.NEIGH = neigh
                ind = L.individual(br0, 0.0, 1000 + i)
                y = LD.record(ind, np.random.default_rng(900 + i), obs, kicks, {f: 1.0 for f in kicks}, spread)
                rec = L.as_pumpprobe(y, obs, kicks, f"ind{i:03d}")
                units = [int(nm[1:]) for nm in rec.names]
                p_of = {u: p for p, u in enumerate(units)}
                nears.append([{p_of[v] for v in neigh[u] if v in p_of} | {p for p, w in enumerate(units) if u in neigh[w]} for u in units])
                recs.append(rec)
        finally:
            LD.NEIGH = saved
        for split in ("alternate", "time"):
            A, B = RI.build(recs, nears, split=split)
            for part in ("raw", "routing"):
                S = RI.IV.agreement_matrix(A, B, part)
                ex = RI.IV.excess(S); ex = ex[np.isfinite(ex)]
                rng = np.random.default_rng(0)
                bs = [np.median(ex[rng.integers(0, len(ex), len(ex))]) for _ in range(1000)]
                lo, hi = np.percentile(bs, [2.5, 97.5])
                RI.log(f"EXPLORATORY fingerprint source, identical wiring rho 1.3, {label}, {split}, {part}: excess {np.median(ex):+.4f} "
                       f"[{lo:+.4f}, {hi:+.4f}]; within {np.nanmedian(np.diag(S)):.3f}")
