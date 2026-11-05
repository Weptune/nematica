"""Is the neighbour effect real activation? Pre-registered 6 Nov 2026 (README section of the same
name, which is the specification). A truly activated neighbour drives its own synaptic partners;
a leak in the recording does not.

Usage: python scripts/run_neighbour_partners.py  ->  docs/figures/neighbour_partners.txt
"""
from __future__ import annotations

import ast
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.data.pumpprobe import load_pumpprobe_dir, neuron_class  # noqa: E402

POS = ROOT / "data" / "derived" / "positions"
KUNERT = ROOT / "data_assets" / "kunert2014"
EXCL, PRE, EARLY, LATE0, LATE1 = 60, 20, 4, 10, 30
S_Z, BOOT, N_CTRL = 4.0, 2000, 3


def partners():
    names = [str(n) for n in ast.literal_eval((KUNERT / "neuron_names.txt").read_text())]
    Gs, Gg = np.load(KUNERT / "Gs.npy"), np.load(KUNERT / "Gg.npy")      # [post, pre]
    cls = [neuron_class(n) for n in names]
    out = defaultdict(set)
    for post in range(len(names)):
        for pre in range(len(names)):
            if cls[pre] == cls[post]:
                continue
            if Gs[post, pre] > 0 or Gg[post, pre] > 0 or Gg[pre, post] > 0:
                out[cls[pre]].add(cls[post])
    return out, set(cls)


def pokes(recs, sham=False, seed=0):
    """Per onset: (worm, target class, list of (neuron class, early, late, rank))."""
    rng = np.random.default_rng(seed)
    res = []
    for w, r in enumerate(recs):
        f_pos = POS / f"{r.uid}.npz"
        if not f_pos.exists():
            continue
        pos = np.load(f_pos)["pos"]
        if pos.shape[0] != r.x.shape[0]:
            continue
        X, T = r.x, r.n_frames
        m = np.ones(T, bool)
        for f in r.all_stim_frames:
            m[f:f + EXCL] = False
        sd = np.nanstd(np.where(m, X, np.nan), axis=1)
        sd = np.where(sd > 0, sd, np.nan)
        if sham:
            ok = [f for f in range(PRE, T - LATE1) if m[f - PRE:f + LATE1].all()]
            named = [k for k, c in enumerate(r.classes) if c and np.isfinite(pos[k]).all()]
            if not ok or not named:
                continue
            onsets = [(int(rng.choice(named)), int(f)) for f in rng.choice(ok, min(len(ok), 10), replace=False)]
        else:
            onsets = [(k, f) for k, f in r.stims if f - PRE >= 0 and f + LATE1 <= T]
        P = pos * np.array([S_Z, 1.0, 1.0])
        for k, f in onsets:
            if not np.isfinite(P[k]).all() or not r.classes[k]:
                continue
            base = np.nanmean(X[:, f - PRE:f], axis=1)
            early = (np.nanmean(X[:, f:f + EARLY], axis=1) - base) / sd
            late = (np.nanmean(X[:, f + LATE0:f + LATE1], axis=1) - base) / sd
            d = np.linalg.norm(P - P[k], axis=1)
            ok_i = [i for i in range(len(d)) if i != k and np.isfinite(d[i]) and np.isfinite(early[i])
                    and np.isfinite(late[i]) and r.classes[i]]
            if len(ok_i) < 15:
                continue
            order = np.argsort(d[ok_i])
            rank = np.empty(len(ok_i), int)
            rank[order] = np.arange(1, len(ok_i) + 1)
            res.append((w, r.classes[k], [(r.classes[i], early[i], late[i], int(rk)) for i, rk in zip(ok_i, rank)]))
    return res


def residualise(ps):
    acc, worms = defaultdict(list), defaultdict(set)
    for w, ck, lst in ps:
        for ci, e, l, _ in lst:
            acc[(ck, ci)].append((e, l))
            worms[(ck, ci)].add(w)
    mean = {p: np.mean(v, axis=0) for p, v in acc.items() if len(worms[p]) >= 2}
    out = []
    for w, ck, lst in ps:
        out.append((w, ck, [(ci, e - mean[(ck, ci)][0], l - mean[(ck, ci)][1], rk) for ci, e, l, rk in lst
                            if (ck, ci) in mean]))
    return out


def diffs(ps, part, known, seed=0):
    rng = np.random.default_rng(seed)
    per = defaultdict(list)       # worm -> list of (early diff, late diff)
    n_used = 0
    for w, ck, lst in ps:
        if len(lst) < 15:
            continue
        lst = sorted(lst, key=lambda t: t[3])
        nb = lst[0][0]
        if nb not in known or ck not in known:
            continue
        excl = {ck, nb} | part[ck] | {c for c, _, _, rk in lst if rk <= 3}
        npart = part[nb] - excl
        NP = [(e, l) for c, e, l, rk in lst if c in npart and rk > 3]
        cands = [c for c, _, _, rk in lst if rk >= 11 and c in known and c not in excl]
        if not NP or not cands:
            continue
        ctrl_classes = set()
        for c in rng.choice(cands, min(N_CTRL, len(cands)), replace=False):
            ctrl_classes |= part[c]
        ctrl_classes -= excl | npart
        CP = [(e, l) for c, e, l, rk in lst if c in ctrl_classes and rk > 3]
        if not CP:
            continue
        a, b = np.mean(NP, axis=0), np.mean(CP, axis=0)
        per[w].append(a - b)
        n_used += 1
    wm = {w: np.mean(v, axis=0) for w, v in per.items()}
    return wm, n_used


def boot(wm, seed=0):
    ids = sorted(wm)
    arr = np.array([wm[i] for i in ids])
    rng = np.random.default_rng(seed)
    bs = np.array([arr[rng.integers(0, len(ids), len(ids))].mean(0) for _ in range(BOOT)])
    return arr.mean(0), bs


def main():
    warnings.filterwarnings("ignore")
    part, known = partners()
    recs = sorted(load_pumpprobe_dir(str(ROOT / "data" / "raw" / "randi2023_wt_npz")), key=lambda r: r.uid)
    real = residualise(pokes(recs))
    sham = residualise(pokes(recs, sham=True))
    wr, nr = diffs(real, part, known)
    ws, ns = diffs(sham, part, known, seed=1)
    mr, br = boot(wr)
    ms, bsh = boot(ws, seed=1)
    lines = [f"real: {nr} stimulations in {len(wr)} worms; sham: {ns} onsets in {len(ws)} worms"]
    for j, name in ((0, "early (0-2 s)"), (1, "late (5-15 s)")):
        lo, hi = np.percentile(br[:, j], [2.5, 97.5])
        slo, shi = np.percentile(bsh[:, j], [2.5, 97.5])
        d = br[:, j] - bsh[:, j]
        dlo, dhi = np.percentile(d, [2.5, 97.5])
        lines.append(f"{name}: neighbour-partners minus control partners {mr[j]:+.4f} [{lo:+.4f}, {hi:+.4f}]; "
                     f"sham {ms[j]:+.4f} [{slo:+.4f}, {shi:+.4f}]; real minus sham {mr[j] - ms[j]:+.4f} [{dlo:+.4f}, {dhi:+.4f}]")
        if j == 1:
            lo1, hi1, dlo1 = lo, hi, dlo
    if lo1 > 0 and dlo1 > 0:
        v = "real activation supported"
    elif lo1 <= 0 <= hi1 and hi1 < 0.02:
        v = "downstream silence (consistent with a leak)"
    else:
        v = "inconclusive"
    lines.append(f"verdict: {v}")
    (ROOT / "docs" / "figures" / "neighbour_partners.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
