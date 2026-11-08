"""Exploratory: where does the lead-lag that real worms share come from? Between-worm agreement
(mean pairwise r of the antisymmetric lagged correlations, lags 1.8 and 6 s) for the raw signal,
its slow part (40 s moving average) and the rest, and for frames away from stimulation."""
import sys, numpy as np, itertools
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
from run_same_worms import bench_sample
from nematica.systems.causal_models import ClassVAR, spontaneous_mask
from nematica.data.pumpprobe import load_pumpprobe_dir
from nematica.bench.levels import _lagged_antisym
recs = load_pumpprobe_dir("data/raw/randi2023_wt_npz")
classes = ClassVAR(3, "all").fit(recs[:80], recs[80:]).classes
bs = [bench_sample(r, classes, "r", r.uid) for r in recs]
def smooth(x, w):
    k = np.ones(w) / w
    return np.array([np.convolve(r, k, mode="same") for r in x])
def agree(trans, pairs=400, seed=0):
    rng = np.random.default_rng(seed); rs = []
    feats = {}
    for i, b in enumerate(bs):
        ok = np.isfinite(b.x).all(1)
        feats[i] = (ok, trans(b.x))
    for _ in range(pairs):
        i, j = rng.choice(len(bs), 2, replace=False)
        idx = np.flatnonzero(feats[i][0] & feats[j][0])
        if idx.size < 15: continue
        la = _lagged_antisym(feats[i][1][idx], 0.5); lb = _lagged_antisym(feats[j][1][idx], 0.5)
        rs.append(np.corrcoef(la, lb)[0, 1])
    return np.mean(rs), np.std(rs) / np.sqrt(len(rs))
print("raw          r=%.4f +- %.4f" % agree(lambda x: np.nan_to_num(x)))
print("slow (40s)   r=%.4f +- %.4f" % agree(lambda x: smooth(np.nan_to_num(x), 80)))
print("fast (rest)  r=%.4f +- %.4f" % agree(lambda x: np.nan_to_num(x) - smooth(np.nan_to_num(x), 80)))
print("fast (8s)    r=%.4f +- %.4f" % agree(lambda x: np.nan_to_num(x) - smooth(np.nan_to_num(x), 16)))
