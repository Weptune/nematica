"""Perturbational complexity (arc 4, "signatures of a mind").

The Perturbational Complexity Index (Casali et al. 2013, Sci Transl Med) is how consciousness
research judges, in people, whether a brain that cannot answer is conscious: perturb the
cortex with a magnetic pulse, mark where and when the response is significant, and measure
how compressible that spatiotemporal pattern is. Awake brains give echoes that are both
widespread and differentiated (hard to compress); deep sleep and anaesthesia give local or
stereotyped ones. Nothing here claims a worm is conscious; the question is whether
artificial brains have the same signature as real ones under the same pokes.

Worm version, per stimulation event:
    1. each named class's response from 0 to 30 s, in units of that neuron's fluctuation
       size before stimulation (SD of deviations within the 5 s pre-stimulus windows,
       pooled over the worm's events), members of a class averaged; the stimulated class
       left out
    2. significant where |response| > 3 [A]
    3. PCI = Lempel-Ziv (1976) complexity of the binary matrix read time point by time
       point, normalised by L log2 L / (L H(p)), with H the binary entropy of the fraction
       p of significant entries (0 when nothing responds)

Levels (distances between two worms' sets of events):
    P1.complexity   Kolmogorov-Smirnov distance between event PCI distributions
    P2.spread       Kolmogorov-Smirnov distance between event fractions significant (p)
"""

from __future__ import annotations

import numpy as np
from scipy.stats import ks_2samp

from ..data.pumpprobe import PumpProbe
from .causal import window

THRESHOLD = 3.0


def lz76(s: np.ndarray) -> int:
    """Number of phrases in the Lempel-Ziv (1976) parsing (Kaspar and Schuster 1987)."""
    s = np.asarray(s, dtype=np.uint8)
    n = len(s)
    if n == 0:
        return 0
    c, l, i, k, k_max = 1, 1, 0, 1, 1
    while True:
        if s[i + k - 1] == s[l + k - 1]:
            k += 1
            if l + k > n:
                c += 1
                break
        else:
            k_max = max(k, k_max)
            i += 1
            if i == l:
                c += 1
                l += k_max
                if l + 1 > n:
                    break
                i, k, k_max = 0, 1, 1
            else:
                k = 1
    return c


def pci(binary: np.ndarray) -> float:
    """binary (sources, time): normalised Lempel-Ziv complexity, columns read in time order."""
    s = np.asarray(binary, dtype=np.uint8).T.ravel()
    L = s.size
    p = s.mean() if L else 0.0
    if L < 2 or p == 0 or p == 1:
        return 0.0
    H = -(p * np.log2(p) + (1 - p) * np.log2(1 - p))
    return float(lz76(s) * np.log2(L) / (L * H))


def event_matrices(rec: PumpProbe, threshold: float = THRESHOLD, transform=None) -> list[dict]:
    """Per stimulation: the class-level significance matrix and its PCI and spread."""
    npre, npost = window(rec.dt)
    x = rec.x
    T = x.shape[1]
    named = [j for j, c in enumerate(rec.classes) if c]
    stims = [(k, f) for k, f in rec.stims if rec.classes[k] and f - npre >= 0 and f + npost <= T]
    if not stims:
        return []
    # fluctuation size before stimulation, pooled over this worm's pre-stimulus windows
    dev = {j: [] for j in named}
    for _, f in stims:
        for j in named:
            pre = x[j, f - npre:f]
            dev[j].append(pre - np.nanmean(pre))
    noise = {j: np.nanstd(np.concatenate(d)) for j, d in dev.items()}
    out = []
    for k, f in stims:
        ci = rec.classes[k]
        rows: dict = {}
        for j in named:
            cj = rec.classes[j]
            if cj == ci or not noise[j] > 0:
                continue
            pre, post = x[j, f - npre:f], x[j, f:f + npost]
            if np.isfinite(pre).sum() < 5 or np.isfinite(post).mean() < 0.8:
                continue
            rows.setdefault(cj, []).append((post - np.nanmean(pre)) / noise[j])
        if len(rows) < 10:
            continue
        R = np.vstack([np.nanmean(np.vstack(v), axis=0) for _, v in sorted(rows.items())])
        if transform is not None:
            R = transform(R)
        B = np.abs(np.nan_to_num(R)) > threshold
        out.append({"stim_class": ci, "frame": f, "n_classes": len(rows), "pci": pci(B), "spread": float(B.mean())})
    return out


class PciSet:
    """One worm's (or one simulated worm's) events, for the ruler."""

    def __init__(self, name: str, group: str, events: list[dict]):
        self.name, self.group, self.events = name, group, events
        self.pci = np.array([e["pci"] for e in events])
        self.spread = np.array([e["spread"] for e in events])


def pci_set(rec: PumpProbe, name: str | None = None, transform=None) -> PciSet:
    return PciSet(name or rec.uid, rec.uid, event_matrices(rec, transform=transform))


def p_complexity(a: PciSet, b: PciSet) -> float:
    if len(a.pci) < 5 or len(b.pci) < 5:
        return np.nan
    return float(ks_2samp(a.pci, b.pci).statistic)


def p_spread(a: PciSet, b: PciSet) -> float:
    if len(a.spread) < 5 or len(b.spread) < 5:
        return np.nan
    return float(ks_2samp(a.spread, b.spread).statistic)


PCI_LEVELS = {"P1.complexity": p_complexity, "P2.spread": p_spread}


def desynchronised(R: np.ndarray, rng=np.random.default_rng(0)) -> np.ndarray:
    """Each class's response circularly shifted by its own random offset within the window:
    keeps how much each class responds, breaks when (calibration)."""
    return np.vstack([np.roll(r, int(rng.integers(len(r)))) for r in R])
