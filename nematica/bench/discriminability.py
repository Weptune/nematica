"""Level 8: discriminability. Can a classifier tell a system's traces from real ones?

A classifier two-sample test (Lopez-Paz & Oquab 2017), done at the worm level:

    windows      each sample is cut into non-overlapping windows (default 50 frames, 30 s at
                 1.67 Hz); each window becomes one feature vector
    features     for a fixed set of core classes (the most often labelled ones): window mean,
                 standard deviation and lag-1 autocorrelation of every class, plus every
                 pairwise correlation. Classes a sample does not have are set to 0.
    classifier   L2-regularised logistic regression on standardised features
    validation   grouped K-fold: every window of a worm (or of a system template) sits in the
                 same fold, so the classifier must generalise to unseen animals rather than
                 recognise individuals. Score = out-of-fold AUC.
    null         the group labels are permuted (which worms count as "system" is reshuffled,
                 counts kept) and the whole procedure repeated; p = (1 + #null >= observed) /
                 (1 + n_perm).

Verdict: "indistinguishable" when p >= alpha, else "distinguishable". Held-out real worms
are run through the same test as a control and must come out indistinguishable.

The test sees only 30 s windows, so it complements the levels rather than replacing them:
it catches any local difference the eight metrics were not designed for. It is linear in
the features, so a pass means "not linearly separable on these statistics", not proof of
realism.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy.optimize import minimize

from .sample import BenchSample


def core_classes(real: Sequence[BenchSample], n: int = 12) -> tuple[str, ...]:
    """The n classes observed in the most real worms (ties broken by canonical order)."""
    classes = real[0].classes
    freq = np.mean([s.observed for s in real], axis=0)
    order = sorted(range(len(classes)), key=lambda i: (-freq[i], i))
    return tuple(classes[i] for i in order[:n])


def window_features(s: BenchSample, core: Sequence[str], window: int = 50) -> np.ndarray:
    idx = [s.classes.index(c) for c in core]
    x = s.x[idx]
    n_win = x.shape[1] // window
    iu = np.triu_indices(len(idx), 1)
    feats = []
    for w in range(n_win):
        seg = x[:, w * window:(w + 1) * window]
        mean = seg.mean(axis=1)
        sd = seg.std(axis=1)
        a, b = seg[:, :-1] - seg[:, :-1].mean(1, keepdims=True), seg[:, 1:] - seg[:, 1:].mean(1, keepdims=True)
        with np.errstate(invalid="ignore", divide="ignore"):
            ac1 = (a * b).sum(1) / np.sqrt((a * a).sum(1) * (b * b).sum(1))
            c = np.corrcoef(seg)
        feats.append(np.concatenate([mean, sd, ac1, c[iu]]))
    f = np.array(feats)
    return np.nan_to_num(f, nan=0.0, posinf=0.0, neginf=0.0)


def _fit_logistic(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    n, d = X.shape
    Xb = np.hstack([X, np.ones((n, 1))])
    w_pos = 0.5 / max(y.mean(), 1e-9)
    w_neg = 0.5 / max(1 - y.mean(), 1e-9)
    sw = np.where(y == 1, w_pos, w_neg) / n          # balanced classes

    def loss(w):
        z = Xb @ w
        ll = np.logaddexp(0, z) - y * z
        reg = 0.5 * lam * np.sum(w[:-1] ** 2)
        p = 1 / (1 + np.exp(-z))
        g = Xb.T @ (sw * (p - y))
        g[:-1] += lam * w[:-1]
        return float(np.sum(sw * ll) + reg), g

    res = minimize(loss, np.zeros(d + 1), jac=True, method="L-BFGS-B", options={"maxiter": 200})
    return res.x


def auc(score: np.ndarray, y: np.ndarray) -> float:
    from scipy.stats import rankdata
    r = rankdata(score)
    n1 = int(y.sum())
    n0 = y.size - n1
    if n0 == 0 or n1 == 0:
        return float("nan")
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n0 * n1))


def _grouped_auc(X, y_group, groups, n_folds, lam, rng) -> float:
    """Out-of-fold AUC with folds made of whole groups, each fold holding both labels."""
    ug = np.unique(groups)
    glabel = np.array([y_group[g] for g in ug])
    fold_of = {}
    for lab in (0, 1):
        gs = rng.permutation(ug[glabel == lab])
        for i, g in enumerate(gs):
            fold_of[g] = i % n_folds
    fold = np.array([fold_of[g] for g in groups])
    y = np.array([y_group[g] for g in groups], dtype=float)
    score = np.full(y.size, np.nan)
    for k in range(n_folds):
        te = fold == k
        tr = ~te
        if not te.any() or len(np.unique(y[tr])) < 2:
            continue
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-6
        w = _fit_logistic((X[tr] - mu) / sd, y[tr], lam)
        Xt = (X[te] - mu) / sd
        score[te] = Xt @ w[:-1] + w[-1]
    ok = np.isfinite(score)
    return auc(score[ok], y[ok])


def discriminability(real: Sequence[BenchSample], system: Sequence[BenchSample],
                     core: Sequence[str], window: int = 50, n_folds: int = 5, lam: float = 1.0,
                     n_perm: int = 100, alpha: float = 0.05, seed: int = 0) -> dict:
    """Worm-level classifier two-sample test of `system` samples against `real` worms."""
    rng = np.random.default_rng(seed)
    feats, groups, y_group = [], [], {}
    for s in real:
        g = "real:" + (s.origin or s.name)
        f = window_features(s, core, window)
        feats.append(f)
        groups += [g] * len(f)
        y_group[g] = 0
    for s in system:
        g = "sys:" + (s.origin or s.name.split(":")[-1])
        f = window_features(s, core, window)
        feats.append(f)
        groups += [g] * len(f)
        y_group[g] = 1
    X = np.vstack(feats)
    groups = np.array(groups)
    n_sys_groups = sum(y_group.values())
    n_folds = min(n_folds, n_sys_groups)
    if n_folds < 2:
        return {"verdict": "not scored"}
    observed = _grouped_auc(X, y_group, groups, n_folds, lam, rng)
    ug = list(y_group)
    labels = np.array([y_group[g] for g in ug])
    null = []
    for _ in range(n_perm):
        perm = dict(zip(ug, rng.permutation(labels)))
        null.append(_grouped_auc(X, perm, groups, n_folds, lam, rng))
    null = np.array(null)
    null = null[np.isfinite(null)]
    p = float((1 + np.sum(null >= observed)) / (1 + null.size))
    return {
        "auc": round(observed, 3),
        "null_median": round(float(np.median(null)), 3),
        "null_p95": round(float(np.percentile(null, 95)), 3),
        "p": round(p, 4),
        "n_windows_real": int(sum(y_group[g] == 0 for g in groups)),
        "n_windows_system": int(sum(y_group[g] == 1 for g in groups)),
        "n_groups_system": int(n_sys_groups),
        "verdict": "indistinguishable" if p >= alpha else "distinguishable",
    }
