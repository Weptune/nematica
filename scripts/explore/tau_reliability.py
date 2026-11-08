"""Exploratory: is a neuron class's timescale a property of the class, of the individual worm-neuron,
or noise? Half-decay time in the first and second half of each recording (same worm): within-worm
test-retest agreement vs agreement of the same class between different worms."""
import sys, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
from run_same_worms import bench_sample
from nematica.systems.causal_models import ClassVAR
from nematica.data.pumpprobe import load_pumpprobe_dir
from nematica.bench.levels import half_decay_time
from collections import Counter
recs = load_pumpprobe_dir("data/raw/randi2023_wt_npz")
cnt = Counter(c for r in recs for c in set(r.classes) if c)
classes = sorted(c for c, n in cnt.items() if n >= 0.3 * len(recs))
A, B = [], []                       # rows: worm, cols: class; log tau in halves
for r in recs:
    b = bench_sample(r, classes, "r", r.uid)
    T = b.x.shape[1] // 2
    a1 = np.full(len(classes), np.nan); a2 = a1.copy()
    for i in range(len(classes)):
        if b.observed[i]:
            for arr, seg in ((a1, b.x[i, :T]), (a2, b.x[i, T:])):
                seg = (seg - seg.mean()) / seg.std()
                arr[i] = np.log(half_decay_time(seg, b.dt, max_lag_s=60))
    A.append(a1); B.append(a2)
A, B = np.array(A), np.array(B)
ok = np.isfinite(A) & np.isfinite(B)
# remove class means (computed from the other half) so agreement is about worm-specific deviations
def dev(X):
    return X - np.nanmean(X, axis=0, keepdims=True)
dA, dB = dev(A), dev(B)
m = ok & np.isfinite(dA) & np.isfinite(dB)
within = np.corrcoef(dA[m], dB[m])[0, 1]
# same class, different worms: pair worm w's first half with worm w+1's second half
Bs = np.roll(dB, 1, axis=0); m2 = np.isfinite(dA) & np.isfinite(Bs)
between = np.corrcoef(dA[m2], Bs[m2])[0, 1]
raw_within = np.corrcoef(A[ok], B[ok])[0, 1]
Br = np.roll(B, 1, axis=0); m3 = np.isfinite(A) & np.isfinite(Br)
raw_between = np.corrcoef(A[m3], Br[m3])[0, 1]
# worm-level component: median per worm in each half
wa, wb = np.nanmedian(A, 1), np.nanmedian(B, 1)
print("rows", int(ok.sum()))
print("raw log tau: same worm-neuron, two halves r = %.2f ; same class, different worms r = %.2f" % (raw_within, raw_between))
print("after removing class means: same worm-neuron r = %.2f ; different worms r = %.2f" % (within, between))
print("worm median log tau, half 1 vs half 2: r = %.2f" % np.corrcoef(wa, wb)[0, 1])
# remove worm medians too: neuron-in-this-worm specific part
dA2 = dA - np.nanmedian(dA, 1, keepdims=True); dB2 = dB - np.nanmedian(dB, 1, keepdims=True)
m4 = np.isfinite(dA2) & np.isfinite(dB2)
print("after removing class and worm effects: same worm-neuron r = %.2f" % np.corrcoef(dA2[m4], dB2[m4])[0, 1])
okw = np.isfinite(wa) & np.isfinite(wb)
print("worm median log tau, half 1 vs half 2 (fixed): r = %.2f (n=%d)" % (np.corrcoef(wa[okw], wb[okw])[0, 1], okw.sum()))
rng = np.random.default_rng(0)
def stats(idx):
    a, b = A[idx], B[idx]
    da = a - np.nanmean(a, 0, keepdims=True); db = b - np.nanmean(b, 0, keepdims=True)
    da = da - np.nanmedian(da, 1, keepdims=True); db = db - np.nanmedian(db, 1, keepdims=True)
    m = np.isfinite(da) & np.isfinite(db)
    within = np.corrcoef(da[m], db[m])[0, 1]
    br = np.roll(b, 1, 0); m3 = np.isfinite(a) & np.isfinite(br)
    raw_b = np.corrcoef(a[m3], br[m3])[0, 1]
    m1 = np.isfinite(a) & np.isfinite(b)
    raw_w = np.corrcoef(a[m1], b[m1])[0, 1]
    return within, raw_w, raw_b
bs = np.array([stats(rng.integers(0, len(A), len(A))) for _ in range(500)])
for name, col in zip(("neuron-in-worm part, two halves", "raw, same worm two halves", "raw, same class other worm"), bs.T):
    print("%-34s 95%% CI %.2f to %.2f" % (name, *np.percentile(col, [2.5, 97.5])))
