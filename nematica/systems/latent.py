"""The best watcher: a latent linear network fitted by maximum likelihood to rest activity.

Unlike the VAR watching copies, this copy has k hidden units with their own dynamics and
private noise (the model class for which watching is provably able to recover poke
responses, nematica/limits.py), and it handles partial recordings exactly: each stretch of
rest contributes the likelihood of the classes it saw, nothing is zero-filled.

Fitting (Whittle likelihood): unpoked frames (spontaneous_mask) are cut into stretches of
`seg` consecutive frames; per stretch, classes tracked in every frame are kept, demeaned,
and Fourier transformed; periodograms are averaged per (recording, class set). The number of
hidden units is chosen from `ks` by held-out Whittle likelihood on the fold's validation
worms; the final model is refitted on training plus validation worms.

Simulation: ClassVAR's clamp protocol with lags = 1, hidden units as extra classes that keep
running (they are never recorded, so never in a worm's class list).
"""

from __future__ import annotations

from collections import Counter

import numpy as np

from .causal_models import ClassVAR, class_matrix, spontaneous_mask


def segment_groups(recs, classes, seg=64, min_classes=3):
    """Grouped periodograms from rest stretches: list of (obs, freqs, weights, P)."""
    acc = {}
    m = seg // 2
    freqs = 2 * np.pi * np.arange(1, m) / seg
    for ri, r in enumerate(recs):
        z = class_matrix(r, classes)
        spont = spontaneous_mask(r)
        T = z.shape[1]
        t = 0
        while t + seg <= T:
            if not spont[t:t + seg].all():
                t += 1
                continue
            blk = z[:, t:t + seg]
            obs = np.flatnonzero(np.isfinite(blk).all(axis=1))
            if len(obs) >= min_classes:
                x = blk[obs] - blk[obs].mean(axis=1, keepdims=True)
                f = np.fft.fft(x, axis=1)[:, 1:m]                      # (o, m-1)
                P = np.einsum("if,jf->fij", f, f.conj()) / seg
                key = (ri, tuple(obs))
                if key in acc:
                    acc[key][0] += P
                    acc[key][1] += 1
                else:
                    acc[key] = [P, 1]
            t += seg
    groups = []
    for (ri, obs), (P, c) in acc.items():
        groups.append((np.array(obs), freqs, np.full(len(freqs), float(c)), P / c))
    return groups


class LatentCopy(ClassVAR):
    def __init__(self, ks=(0, 2, 4, 8), seg=64, steps=600, polish=200, min_fraction=0.3,
                 fixed_k=None, name=None):
        super().__init__(lags=1, frames="spontaneous", min_fraction=min_fraction)
        self.ks, self.seg, self.steps, self.polish, self.fixed_k = ks, seg, steps, polish, fixed_k
        self.run_unseen = True
        self.name = name or ("latent" if fixed_k is None else f"latent_k{fixed_k}")

    def _fit_k(self, groups, C, k, init):
        from ..limits import whittle_fit_groups
        return whittle_fit_groups(groups, C, k, steps=self.steps, polish=self.polish, init=init,
                                  lr=0.01, seed=k)

    def fit(self, train, val):
        from ..limits import whittle_loss
        cnt = Counter(c for r in train for c in set(r.classes) if c)
        classes = sorted(c for c, n in cnt.items() if n >= self.min_fraction * len(train))
        C = len(classes)
        gt = segment_groups(train, classes, self.seg)
        gv = segment_groups(val, classes, self.seg)
        # start from a VAR(1) on the same frames (the plain watcher), shrunk to be stable
        v1 = ClassVAR(1, "spontaneous", min_fraction=self.min_fraction)
        v1.fit(train, val)
        A = v1.W[:C, :C].T if v1.classes == classes else 0.5 * np.eye(C)
        rad = np.abs(np.linalg.eigvals(A)).max()
        A = A * min(1.0, 0.95 / rad)
        init0 = (A, np.log(np.clip(v1.noise_sd, 0.1, None) ** 2) if len(v1.noise_sd) == C else np.zeros(C),
                 np.log(0.05) * np.ones(C))
        ks = [self.fixed_k] if self.fixed_k is not None else list(self.ks)
        scores = {}
        if len(ks) > 1:
            for k in ks:
                F, lq, lr_, _ = self._fit_k(gt, C, k, init0)
                q = np.concatenate([np.exp(lq), np.ones(k)])
                scores[k] = whittle_loss(gv, F, q, np.exp(lr_), C)
            k = min(scores, key=scores.get)
        else:
            k = ks[0]
        F, lq, lr_, loss = self._fit_k(gt + gv, C, k, init0)
        self.k = k
        self.lr_ = lr_
        self.classes = classes + [f"_hidden{h}" for h in range(k)]
        d = C + k
        self.W = np.vstack([F.T, np.zeros((1, d))])          # A[from, to] = F^T, zero bias
        self.noise_sd = np.sqrt(np.concatenate([np.exp(lq), np.ones(k)]))
        self.nu = np.full(d, 30.0)
        self.radius = self.spectral_radius()
        self.info = {"radius": round(self.radius, 4), "k": k, "classes": C, "groups": len(gt) + len(gv),
                     "val_loss": {kk: round(v, 5) for kk, v in scores.items()}, "loss": round(loss, 5)}
        return self
