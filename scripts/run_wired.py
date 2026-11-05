"""Real wiring diagrams through the worm measurements (pre-registered 6 Nov 2026; README "Real
wiring diagrams through the worm measurements"). Worm: Kunert et al. 2014 connectome. Fly: the
fib25/fib19 visual-system connectome bundled with flyvis, expanded over 19 columns.

Usage: python scripts/run_wired.py fingerprints | ruler
Output: docs/figures/wired_fingerprints.csv, wired_ruler.csv
"""
from __future__ import annotations

import ast
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica import annlab as L  # noqa: E402
from nematica.data.pumpprobe import PumpProbe, neuron_class  # noqa: E402
import run_ladder as LD  # noqa: E402
import run_week1 as W1  # noqa: E402

FIG = ROOT / "docs" / "figures"
KUNERT = ROOT / "data_assets" / "kunert2014"


def worm_wiring():
    names = [str(n) for n in ast.literal_eval((KUNERT / "neuron_names.txt").read_text())]
    Gs, Gg, em = np.load(KUNERT / "Gs.npy"), np.load(KUNERT / "Gg.npy"), np.load(KUNERT / "emask.npy")
    sign = np.where(np.asarray(em).ravel() > 0, -1.0, 1.0)            # 1 = inhibitory presynaptic neuron
    W = Gs * sign[None, :] + 0.5 * (Gg + Gg.T)                         # [post, pre]
    np.fill_diagonal(W, 0.0)
    return W, [neuron_class(n) or n for n in names]


def fly_wiring(radius=2):
    import flyvis
    d = json.load(open(Path(flyvis.__file__).parent / "connectome" / "fib25-fib19_v2.2.json"))
    cols = [(u, v) for u in range(-radius, radius + 1) for v in range(-radius, radius + 1) if abs(u + v) <= radius]
    units, idx = [], {}
    for nd in d["nodes"]:
        su, sv = nd["pattern"][1] if nd["pattern"][0] == "stride" else (1, 1)
        for (u, v) in cols:
            if u % su == 0 and v % sv == 0:
                idx[(nd["name"], u, v)] = len(units)
                units.append(nd["name"])
    W = np.zeros((len(units), len(units)))
    for e in d["edges"]:
        a = float(e["alpha"])
        for off, cnt in e["offsets"]:
            for (u, v) in cols:
                t = idx.get((e["tar"], u, v))
                s_ = idx.get((e["src"], u + off[0], v + off[1]))
                if t is not None and s_ is not None:
                    W[t, s_] += a * cnt
    np.fill_diagonal(W, 0.0)
    return W, units


def shuffled(W, seed=1):
    g = np.random.default_rng(seed)
    vals = W[W != 0]
    off = ~np.eye(len(W), dtype=bool)
    pos = np.flatnonzero(off.ravel())
    Ws = np.zeros(W.size)
    Ws[g.choice(pos, len(vals), replace=False)] = g.permutation(vals)
    return Ws.reshape(W.shape)


def scaled(W, rho=1.3):
    return W * rho / np.abs(np.linalg.eigvals(W)).max()


def recs_for(W, classes, share, seed=0, n_ind=113, sigma=0.3):
    n = len(W)
    br0 = L.make_brain(n=n, rho=1.3, share=share, tau=90.0, seed=seed, q=0.2, W=scaled(W))
    hidden = L.design(n, np.random.default_rng(200))
    rng = np.random.default_rng(7)
    out = []
    for i in range(n_ind):
        ind = L.individual(br0, sigma, 1000 + i)
        obs = (rng.random(n) < 0.5) & ~hidden
        targets = np.flatnonzero(obs)
        kicks = {f: int(rng.choice(targets)) for f in range(LD.LEAD, L.FRAMES - L.WIN, L.EVERY)}
        y = LD.record(ind, rng, obs, kicks, {f: 1.0 for f in kicks}, 0.0)
        rows = np.flatnonzero(obs)
        pos = {u: k for k, u in enumerate(rows)}
        stims = [(pos[j], f) for f, j in sorted(kicks.items()) if j in pos]
        out.append(PumpProbe(uid=f"ind{i:03d}", x=y[:, rows].T.copy(), names=[f"U{u}" for u in rows],
                             classes=[classes[u] for u in rows], stims=stims, dt=0.5,
                             all_stim_frames=sorted(kicks)))
    return out


NETS = {"worm-wired": worm_wiring, "fly-wired": fly_wiring}


def run_fingerprints():
    out = FIG / "wired_fingerprints.csv"
    rows = list(csv.DictReader(out.open())) if out.exists() else []
    done = {(r["network"], r["wiring"], r["drives"]) for r in rows}
    for net, fn in NETS.items():
        W, classes = fn()
        for wiring, Wx in (("real", W), ("shuffled", shuffled(W))):
            for share in (0.0, 0.25):
                key = (net, wiring, str(share))
                if key in done:
                    continue
                ws = [W1.Worm(r, valid_fn=lambda c: True) for r in recs_for(Wx, classes, share)]
                fp = LD.fingerprint(ws)
                rows.append({"network": net, "wiring": wiring, "drives": share, "units": len(W),
                             "classes": len(set(classes)), **{k: round(v, 4) for k, v in fp.items()}})
                print(rows[-1], flush=True)
                with out.open("w", newline="") as fh:
                    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                    w.writeheader()
                    w.writerows(rows)


def run_ruler(net):
    import warnings
    import run_ann_ruler as R
    from run_worm_stitch import StitchedVAR
    from nematica.bench.scorecard import FoldRuler, fold_parts, set_norm
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    W, classes = NETS[net]()
    recs = {r.uid: r for r in recs_for(W, classes, 0.0)}
    uids = sorted(recs)
    perm = np.random.default_rng(1).permutation(uids)
    folds = [sorted(perm[i::3]) for i in range(3)]
    out = FIG / f"wired_ruler_{net}.csv"
    rows = []
    ruler = FoldRuler(*fold_parts(recs, folds, 0), pci=False)
    for c in ("var3_spontaneous", "stitch3_hp", "hybrid_kernels"):
        m = StitchedVAR(True, True) if c == "stitch3_hp" else R.make_model(c)
        res = ruler.score(c, m, seed_base=0)
        c1 = next(r for r in res if r["metric"] == "C1.pattern")
        rows.append({"network": net, "fold": 0, "copy": c, "echo_agreement": round(1 - c1["system_median"], 4),
                     "real_agreement": round(1 - c1["bio_median"], 4), "verdict": c1["verdict"]})
        print(rows[-1], flush=True)
        with out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    if sys.argv[1] == "fingerprints":
        run_fingerprints()
    else:
        run_ruler(sys.argv[2])
