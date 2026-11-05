"""Does stimulation in worms reach neighbouring neurons? Pre-registered 5 Nov 2026 (README section of
the same name, which is the specification). Positions from scripts/extract_positions.py.

Usage: python scripts/run_offtarget_worms.py   ->  docs/figures/offtarget_worms.txt
"""
from __future__ import annotations

import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402

POS = ROOT / "data" / "derived" / "positions"
EXCL, PRE, EARLY, LATE0, LATE1 = 60, 20, 4, 10, 30
BOOT = 2000


def entries(recs, s_z, sham=False, seed=0):
    rng = np.random.default_rng(seed)
    rows = []          # worm, cj, ci, early, late, dist, rank, target_early
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
        P = pos * np.array([s_z, 1.0, 1.0])
        for k, f in onsets:
            if not np.isfinite(P[k]).all():
                continue
            base = np.nanmean(X[:, f - PRE:f], axis=1)
            early = (np.nanmean(X[:, f:f + EARLY], axis=1) - base) / sd
            late = (np.nanmean(X[:, f + LATE0:f + LATE1], axis=1) - base) / sd
            d = np.linalg.norm(P - P[k], axis=1)
            ok_i = [i for i in range(len(d)) if i != k and np.isfinite(d[i]) and np.isfinite(early[i]) and np.isfinite(late[i])]
            if not ok_i:
                continue
            order = np.argsort(d[ok_i])
            rank = np.empty(len(ok_i), int)
            rank[order] = np.arange(1, len(ok_i) + 1)
            for i, rk in zip(ok_i, rank):
                rows.append((w, r.classes[k], r.classes[i], early[i], late[i], d[i], rk, early[k]))
    return rows


def residuals(rows, col):
    """Within-pair residual for named pairs seen in >= 2 worms."""
    acc, worms = defaultdict(list), defaultdict(set)
    for e in rows:
        if e[1] and e[2]:
            acc[(e[1], e[2])].append(e[col])
            worms[(e[1], e[2])].add(e[0])
    mean = {p: np.mean(v) for p, v in acc.items() if len(worms[p]) >= 2}
    out = []
    for e in rows:
        p = (e[1], e[2])
        if p in mean:
            out.append((e[0], e[col] - mean[p], e[5], e[6], e[7]))
    return np.array(out, dtype=float)


def S_boot(res, seed=0):
    w = res[:, 0].astype(int)
    ids = np.unique(w)
    idx = {i: np.flatnonzero(w == i) for i in ids}
    est = spearmanr(res[:, 1], np.log(res[:, 2])).statistic
    # bootstrap: Pearson correlation of the full-sample ranks within each resample (fast Spearman)
    from scipy.stats import rankdata
    ra, rb = rankdata(res[:, 1]), rankdata(res[:, 2])
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(BOOT):
        sel = np.concatenate([idx[i] for i in rng.choice(ids, len(ids))])
        bs.append(np.corrcoef(ra[sel], rb[sel])[0, 1])
    return est, np.array(bs)


def main():
    warnings.filterwarnings("ignore")
    recs = sorted(load_pumpprobe_dir(str(ROOT / "data" / "raw" / "randi2023_wt_npz")), key=lambda r: r.uid)
    lines = []
    have = sum((POS / f"{r.uid}.npz").exists() for r in recs)
    lines.append(f"worms with positions: {have} of {len(recs)}")
    verdict_ok = []
    for s_z in (2.0, 4.0, 8.0):
        real = entries(recs, s_z)
        sham = entries(recs, s_z, sham=True)
        re_e, sh_e = residuals(real, 3), residuals(sham, 3)
        re_l = residuals(real, 4)
        S, bs = S_boot(re_e)
        Ss, bss = S_boot(sh_e, seed=1)
        Sl, bsl = S_boot(re_l, seed=2)
        d = bs - bss[:len(bs)]
        lo, hi = np.nanpercentile(bs, [2.5, 97.5])
        dlo, dhi = np.nanpercentile(d, [2.5, 97.5])
        lines.append(f"s_z {s_z:g}: entries {len(re_e)} (worms {len(np.unique(re_e[:, 0]))}); "
                     f"S early {S:+.4f} [{lo:+.4f}, {hi:+.4f}]; sham S {Ss:+.4f} "
                     f"[{np.nanpercentile(bss, 2.5):+.4f}, {np.nanpercentile(bss, 97.5):+.4f}]; "
                     f"real minus sham {S - Ss:+.4f} [{dlo:+.4f}, {dhi:+.4f}]; S late {Sl:+.4f} "
                     f"[{np.nanpercentile(bsl, 2.5):+.4f}, {np.nanpercentile(bsl, 97.5):+.4f}]")
        bins = [(1, 1), (2, 3), (4, 10), (11, 10 ** 6)]
        parts = []
        for a, b in bins:
            sel = (re_e[:, 3] >= a) & (re_e[:, 3] <= b)
            ssel = (sh_e[:, 3] >= a) & (sh_e[:, 3] <= b)
            parts.append(f"rank {a}-{b if b < 10 ** 6 else 'end'}: {re_e[sel, 1].mean():+.3f} (n {sel.sum()}; sham {sh_e[ssel, 1].mean():+.3f})")
        lines.append("   mean residual early response by distance rank: " + "; ".join(parts))
        if s_z == 4.0:
            nn = re_e[re_e[:, 3] == 1]
            tgt = np.nanmean([e[7] for e in real])
            lines.append(f"   nearest neighbour residual early response {nn[:, 1].mean():+.3f} against the target's own early response {tgt:+.3f} (ratio {nn[:, 1].mean() / tgt:+.3f})")
            absent = (lo <= 0 <= hi) and lo > -0.02
        verdict_ok.append(hi < 0 and dhi < 0)
    if all(verdict_ok):
        v = "off-target signature present"
    elif absent:
        v = "off-target signature absent"
    else:
        v = "inconclusive"
    lines.append(f"verdict: {v}")
    txt = "\n".join(lines)
    print(txt)
    (ROOT / "docs" / "figures" / "offtarget_worms.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
