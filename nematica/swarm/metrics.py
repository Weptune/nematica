"""Swarm statistics (arc 6). All take a SwarmRun (nematica.swarm.engine)."""

from __future__ import annotations

import numpy as np


def _onsets(states: np.ndarray) -> np.ndarray:
    """(N, T) boolean: a reversal starts at this frame."""
    s = states > 0.5
    on = np.zeros_like(s)
    on[:, 1:] = s[:, 1:] & ~s[:, :-1]
    return on


def _components(n: int, pairs: list) -> list:
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for j, k in pairs:
        parent[find(j)] = find(k)
    groups = {}
    for j in range(n):
        groups.setdefault(find(j), []).append(j)
    return [len(g) for g in groups.values()]


def cluster_stats(run) -> dict:
    n = run.heads.shape[0]
    in_cluster, sizes = [], []
    for pairs in run.links:
        comp = _components(n, pairs)
        in_cluster.append(sum(c for c in comp if c >= 2) / n)
        sizes += [c for c in comp if c >= 2]
    sizes = np.array(sizes) if sizes else np.array([0])
    return {"frac_in_cluster": float(np.mean(in_cluster)),
            "mean_cluster_size": float(np.mean(sizes)) if sizes.any() else 0.0,
            "max_cluster_size": int(sizes.max())}


def nearest_neighbour(run) -> float:
    """Median over worms and frames of the distance from each head to the nearest other head."""
    H = run.heads                                                     # (N, T, 2)
    d = np.hypot(H[:, None, :, 0] - H[None, :, :, 0], H[:, None, :, 1] - H[None, :, :, 1])
    n = H.shape[0]
    d[np.arange(n), np.arange(n)] = np.inf
    return float(np.median(d.min(axis=1)))


def rate_by_density(run, bins=((0, 0), (1, 1), (2, 99))) -> dict:
    """Reversal onsets per minute of forward crawling, by local density (other heads within
    one body length at the frame before the onset)."""
    on = _onsets(run.states)
    fwd = run.states < 0.5
    out = {}
    for lo, hi in bins:
        sel = np.zeros_like(fwd)
        sel[:, 1:] = (run.density[:, :-1] >= lo) & (run.density[:, :-1] <= hi) & fwd[:, :-1]
        minutes = sel.sum() * run.dt / 60
        key = f"rev_per_min_density_{lo}" + ("" if hi == lo else "+")
        out[key] = float(on[sel].sum() / minutes) if minutes > 0.5 else float("nan")
    return out


def per_worm(run) -> dict:
    """Each worm's own statistics (arrays over worms)."""
    minutes = run.states.shape[1] * run.dt / 60
    return {"rev_rate": _onsets(run.states).sum(axis=1) / minutes,
            "contact": run.touched.mean(axis=1),
            "near_copper": (run.dist < 0.5).mean(axis=1)}


def swarm_summary(run) -> dict:
    pw = per_worm(run)
    out = {"contact": float(run.touched.mean()),
           "blocked": float(run.blocked.mean()),
           "near_copper": float((run.dist < 0.5).mean()),
           "nn_dist_mm": nearest_neighbour(run),
           "rev_rate": float(pw["rev_rate"].mean()),
           "sd_rev_rate": float(pw["rev_rate"].std()),
           "sd_contact": float(pw["contact"].std()),
           "sd_near_copper": float(pw["near_copper"].std())}
    out.update(cluster_stats(run))
    out.update(rate_by_density(run))
    return out
