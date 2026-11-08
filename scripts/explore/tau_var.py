"""Exploratory: structure of half-decay-time variation, real vs a model (one cv3 pool):
worm effect (median log tau per worm), class effect, residual; and the L1.timescale distance."""
import sys, numpy as np, itertools
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
from run_same_worms import make_model, bench_sample
from nematica.systems.causal_models import ClassVAR
from nematica.data.pumpprobe import load_pumpprobe_dir
from nematica.data.splits import load_folds
from nematica.bench.levels import half_decay_time, l1_timescale
import nematica.bench.causal as causal
causal.NORM = "fluct"
fi = int(sys.argv[1]); models = [m for m in sys.argv[2].split(",") if m]
recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
folds = load_folds("configs/splits/pumpprobe_cv3.yaml")["folds"]
pool = [recs[u] for u in folds[fi]]
rest = sorted(u for f in folds if f is not folds[fi] for u in f); val_uids = rest[::5]
train = [recs[u] for u in rest if u not in val_uids]; val = [recs[u] for u in val_uids]
classes = ClassVAR(3, "all").fit(train, val).classes
def table(bs):
    T = np.full((len(bs), len(classes)), np.nan)
    for w, b in enumerate(bs):
        for i in range(len(classes)):
            if b.observed[i]:
                T[w, i] = np.log(half_decay_time(b.x[i], b.dt))
    return T
def describe(name, bs, real_b):
    T = table(bs)
    wm = np.nanmedian(T, 1)
    resid = T - wm[:, None] - (np.nanmedian(T - wm[:, None], 0))[None, :]
    d = [l1_timescale(a, r) for a in bs for r in real_b if a is not r]
    print("%-58s worm-effect SD %.2f  class-effect SD %.2f  resid SD %.2f  median logtau %.2f  dist to real %.3f" % (
        name, np.nanstd(wm), np.nanstd(np.nanmedian(T - wm[:, None], 0)), np.nanstd(resid), np.nanmedian(T), np.nanmedian(d)))
real_b = [bench_sample(r, classes, "r", r.uid) for r in pool]
describe("real", real_b, real_b)
for n in models:
    m = make_model(n).fit(train, val)
    sims = [m.simulate(r, np.random.default_rng(1000 * fi + i)) for i, r in enumerate(pool)]
    describe(n, [bench_sample(s, classes, "s", r.uid) for s, r in zip(sims, pool)], real_b)
print("percentiles of tau (s): 5,10,25,50,75,90,95")
Tr = np.exp(table(real_b)); print("real ", np.round(np.nanpercentile(Tr, [5, 10, 25, 50, 75, 90, 95]), 1))
Ts = np.exp(table([bench_sample(s, classes, "s", r.uid) for s, r in zip(sims, pool)])); print("model", np.round(np.nanpercentile(Ts, [5, 10, 25, 50, 75, 90, 95]), 1))
print("share at max lag (120 s): real %.3f model %.3f" % (np.nanmean(Tr >= 119), np.nanmean(Ts >= 119)))
def acfL(bs, L):
    out = []
    for b in bs:
        for i in range(len(classes)):
            if b.observed[i]:
                x = b.x[i] - b.x[i].mean(); out.append((x[L:] * x[:-L]).mean() / x.var())
    return np.percentile(out, [50, 75, 90, 95])
sb = [bench_sample(s, classes, "s", r.uid) for s, r in zip(sims, pool)]
for L in (60, 120, 240, 480):
    print("acf lag %d frames pct 50/75/90/95  real" % L, np.round(acfL(real_b, L), 2), " model", np.round(acfL(sb, L), 2))
