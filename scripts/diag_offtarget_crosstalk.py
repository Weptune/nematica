"""Exploratory follow-up to the pre-registered worm off-target test (5 Nov 2026, written after it).

The pre-registered rank correlation was diluted by far neurons, but its pre-registered by-rank
summary showed nearest neighbours rising early after a poke. Two readings: light reaching
neighbours (poke-specific), or proximity effects present at rest too (optical crosstalk between
adjacent cells, or local coupling). Test: the same neighbour excess after SPONTANEOUS rises of a
neuron, in unpoked stretches. Per event: excess = (mean early change of the nearest 1 / 2-3
neighbours) minus (mean early change of neurons beyond rank 10), divided by the event neuron's own
early change. Events: stimulations (target early change > 1 resting SD) and spontaneous rises
(windows entirely unpoked; a named neuron whose early change is > 1 resting SD; at most the 20
largest per worm). Matched comparison: events with the source's early change between 1 and 4.
Bootstrap over worms. s_z = 4.
"""
import sys
from pathlib import Path
import warnings
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
POS = ROOT / "data" / "derived" / "positions"
EXCL, PRE, EARLY = 60, 20, 4


def events(r, pos, kind):
    X, T = r.x, r.n_frames
    m = np.ones(T, bool)
    for f in r.all_stim_frames:
        m[f:f + EXCL] = False
    sd = np.nanstd(np.where(m, X, np.nan), axis=1)
    sd = np.where(sd > 0, sd, np.nan)
    P = pos * np.array([4.0, 1, 1])
    out = []
    if kind == "stim":
        cand = [(k, f) for k, f in r.stims if f - PRE >= 0 and f + EARLY <= T]
    else:
        ok = [f for f in range(PRE, T - 30) if m[f - PRE:f + 30].all()]
        cand = []
        for f in ok[::2]:
            base = np.nanmean(X[:, f - PRE:f], axis=1)
            e = (np.nanmean(X[:, f:f + EARLY], axis=1) - base) / sd
            for k in np.flatnonzero(e > 1):
                if r.classes[k]:
                    cand.append((int(k), f, e[k]))
        cand = [c[:2] for c in sorted(cand, key=lambda c: -c[2])[:20]]
    for k, f in cand:
        if not np.isfinite(P[k]).all():
            continue
        base = np.nanmean(X[:, f - PRE:f], axis=1)
        e = (np.nanmean(X[:, f:f + EARLY], axis=1) - base) / sd
        if not (np.isfinite(e[k]) and 1 < e[k] < 4):
            continue
        d = np.linalg.norm(P - P[k], axis=1)
        ii = [i for i in range(len(d)) if i != k and np.isfinite(d[i]) and np.isfinite(e[i])]
        if len(ii) < 15:
            continue
        o = np.array(ii)[np.argsort(d[ii])]
        far = e[o[10:]].mean()
        out.append((e[k], e[o[0]] - far, e[o[1:3]].mean() - far))
    return out


def main():
    warnings.filterwarnings("ignore")
    recs = sorted(load_pumpprobe_dir(str(ROOT / "data" / "raw" / "randi2023_wt_npz")), key=lambda r: r.uid)
    per = {"stim": [], "spont": []}
    for r in recs:
        f = POS / f"{r.uid}.npz"
        if not f.exists():
            continue
        pos = np.load(f)["pos"]
        if pos.shape[0] != r.x.shape[0]:
            continue
        for kind in per:
            per[kind].append(np.array(events(r, pos, kind)).reshape(-1, 3))
    lines = []
    rng = np.random.default_rng(0)
    for kind, W in per.items():
        W = [w for w in W if len(w)]
        def stat(ws):
            a = np.concatenate(ws)
            return a[:, 1].mean() / a[:, 0].mean(), a[:, 2].mean() / a[:, 0].mean(), a[:, 0].mean(), len(a)
        est = stat(W)
        bs = np.array([stat([W[i] for i in rng.integers(0, len(W), len(W))])[:2] for _ in range(2000)])
        lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
        lines.append(f"{kind}: events {est[3]} in {len(W)} worms; source early change {est[2]:.2f}; nearest-neighbour excess / source "
                     f"{est[0]:+.3f} [{lo[0]:+.3f}, {hi[0]:+.3f}]; 2nd-3rd {est[1]:+.3f} [{lo[1]:+.3f}, {hi[1]:+.3f}]")
    txt = "\n".join(lines)
    print(txt)
    (ROOT / "docs" / "figures" / "offtarget_crosstalk.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
