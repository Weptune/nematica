"""Test N (pre-registered 8 Nov 2026, README "Testing the emulator recipe on data it was not built on"):
do unc-31 worms (no dense-core-vesicle neuropeptide release) have less slow activity than wild type?

Per worm and class: slow share = autocovariance of the z-scored class activity at 20, 40, 80 frames,
log-linear fit extrapolated to lag 0, clipped to [0, 0.95]; slow timescale from the fitted slope.
Primary: class-matched difference (median over classes seen in >= 5 worms of each strain of
unc-31 median minus wild-type median); permutation of strain labels (10,000), worm bootstrap.
Secondary: timescale; shared slow variance (top 6 eigenvalues of the lag-40 correlation matrix over
the worm's classes, divided by its class count)."""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.systems.causal_models import class_matrix  # noqa: E402

LAGS = (20, 40, 80)


def worm_table(rec, classes):
    z = class_matrix(rec, classes)
    share = np.full(len(classes), np.nan); tau = share.copy()
    for i in range(len(classes)):
        v = z[i]
        if not np.isfinite(v).sum() > 0.95 * v.size:
            continue
        v = np.where(np.isfinite(v), v, np.nanmean(v)); v = (v - v.mean()) / v.std()
        d = np.array([np.mean(v[L:] * v[:-L]) for L in LAGS])
        if (d <= 1e-3).any():
            share[i] = 0.0
            continue
        sl, ic = np.polyfit(LAGS, np.log(d), 1)
        share[i] = float(np.clip(np.exp(ic), 0, 0.95))
        tau[i] = float(-0.5 / sl) if sl < 0 else np.nan
    ok = np.isfinite(share) & np.isfinite(z).all(1)
    x = np.nan_to_num(z[ok]); x = (x - x.mean(1, keepdims=True)) / x.std(1, keepdims=True)
    C = (x[:, 40:] @ x[:, :-40].T) / (x.shape[1] - 40); C = (C + C.T) / 2
    ev = np.sort(np.linalg.eigvalsh(C))[::-1]
    shared = float(np.clip(ev[:6], 0, None).sum() / max(ok.sum(), 1))
    return share, tau, shared


def load(path):
    return [r for r in load_pumpprobe_dir(path) if any(r.classes) and r.n_frames >= 1000]


def main():
    wt, mu = load("data/raw/randi2023_wt_npz"), load("data/raw/randi2023_unc31_npz")
    cnt = Counter(c for r in wt + mu for c in set(r.classes) if c)
    classes = sorted(c for c, n in cnt.items() if n >= 10)
    tabs = [worm_table(r, classes) for r in wt + mu]
    S = np.array([t[0] for t in tabs]); TAU = np.array([t[1] for t in tabs]); SH = np.array([t[2] for t in tabs])
    lab = np.array([0] * len(wt) + [1] * len(mu))

    def stat(M, lab):
        a, b = M[lab == 1], M[lab == 0]
        keep = (np.isfinite(a).sum(0) >= 5) & (np.isfinite(b).sum(0) >= 5)
        return float(np.median(np.nanmedian(a[:, keep], 0) - np.nanmedian(b[:, keep], 0))), int(keep.sum())

    rng = np.random.default_rng(0)
    out = []
    for name, M in (("slow share", S), ("slow timescale (s)", TAU)):
        obs, k = stat(M, lab)
        perm = np.array([stat(M, rng.permutation(lab))[0] for _ in range(10000)])
        boot = []
        for _ in range(2000):
            i0 = rng.choice(np.flatnonzero(lab == 0), (lab == 0).sum()); i1 = rng.choice(np.flatnonzero(lab == 1), (lab == 1).sum())
            idx = np.r_[i0, i1]; boot.append(stat(M[idx], lab[idx])[0])
        p = float((np.abs(perm) >= abs(obs)).mean())
        out.append(f"{name}: unc-31 minus wild type, class-matched median {obs:+.4f} "
                   f"[95% {np.percentile(boot, 2.5):+.4f}, {np.percentile(boot, 97.5):+.4f}], "
                   f"permutation p = {p:.4f}, {k} classes; medians wt {np.nanmedian(M[lab == 0]):.3f}, unc-31 {np.nanmedian(M[lab == 1]):.3f}")
    a, b = SH[lab == 1], SH[lab == 0]
    obs = float(np.median(a) - np.median(b))
    perm = []
    for _ in range(10000):
        l = rng.permutation(lab); perm.append(np.median(SH[l == 1]) - np.median(SH[l == 0]))
    out.append(f"shared slow variance: unc-31 {np.median(a):.3f} vs wild type {np.median(b):.3f}, difference {obs:+.4f}, "
               f"permutation p = {float((np.abs(perm) >= abs(obs)).mean()):.4f}")
    out.insert(0, f"worms: wild type {len(wt)}, unc-31 {len(mu)}; classes {len(classes)}")
    Path("docs/figures/neuropeptide_slow.txt").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
