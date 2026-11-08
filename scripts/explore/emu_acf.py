"""Exploratory: autocorrelation profile, real vs simulated (median over worms and classes)."""
import sys, numpy as np
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
from run_same_worms import make_model, bench_sample
from nematica.systems.causal_models import ClassVAR
from nematica.data.pumpprobe import load_pumpprobe_dir
from nematica.data.splits import load_folds
import nematica.bench.causal as causal
causal.NORM = "fluct"
LAGS = [1, 2, 4, 8, 16, 32, 64, 128]
fi = int(sys.argv[1]); models = [m for m in sys.argv[2].split(",") if m]
recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
folds = load_folds("configs/splits/pumpprobe_cv3.yaml")["folds"]
pool = [recs[u] for u in folds[fi]]
rest = sorted(u for f in folds if f is not folds[fi] for u in f); val_uids = rest[::5]
train = [recs[u] for u in rest if u not in val_uids]; val = [recs[u] for u in val_uids]
classes = ClassVAR(3, "all").fit(train, val).classes
def acf(x, L):
    x = x - x.mean(); return float((x[L:] * x[:-L]).mean() / x.var())
def prof(bs):
    out = []
    for b in bs:
        ok = np.isfinite(b.x).all(1)
        out.append([np.median([acf(r, L) for r in b.x[ok]]) for L in LAGS])
    return np.median(out, axis=0)
print("dt", pool[0].dt, "lags(frames)", LAGS)
print("real".ljust(44), np.round(prof([bench_sample(r, classes, "r", r.uid) for r in pool]), 3))
for name in models:
    m = make_model(name).fit(train, val)
    sims = [m.simulate(r, np.random.default_rng(1000 * fi + i)) for i, r in enumerate(pool)]
    print(name.ljust(44), np.round(prof([bench_sample(x, classes, "s", r.uid) for x, r in zip(sims, pool)]), 3), flush=True)
