"""Exploratory: what sets echo magnitude (median |mean response|, fluct units) in a model:
background alone (kernels off) vs full; real for reference; also the kernels' own size."""
import sys, numpy as np
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
from run_same_worms import make_model
from nematica.systems.causal_models import ClassVAR
from nematica.data.pumpprobe import load_pumpprobe_dir
from nematica.data.splits import load_folds
import nematica.bench.causal as causal
from nematica.bench.causal import response_set
from nematica.bench.perturbational import pci_set
causal.NORM = "fluct"
fi = int(sys.argv[1]); name = sys.argv[2]
recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
folds = load_folds("configs/splits/pumpprobe_cv3.yaml")["folds"]
pool = [recs[u] for u in folds[fi]]
rest = sorted(u for f in folds if f is not folds[fi] for u in f); val_uids = rest[::5]
train = [recs[u] for u in rest if u not in val_uids]; val = [recs[u] for u in val_uids]
def mag(rs):
    out = []
    for r in rs:
        a = [abs(r.amp(k)) for k in r.traces]; a = [v for v in a if np.isfinite(v)]
        out.append(np.median(a))
    return np.median(out)
def spread(recs_):
    return np.median(np.concatenate([pci_set(r).spread for r in recs_]))
print("real          |amp| %.3f  spread %.3f" % (mag([response_set(r) for r in pool]), spread(pool)))
m = make_model(name).fit(train, val)
print("info", {k: v for k, v in m.info.items() if k in ("obs_share", "random_spread_target", "random_spread_model")})
sims = [m.simulate(r, np.random.default_rng(i)) for i, r in enumerate(pool)]
print("model         |amp| %.3f  spread %.3f" % (mag([response_set(s) for s in sims]), spread(sims)))
k = m.kernels; m.kernels = {}
sims0 = [m.simulate(r, np.random.default_rng(i)) for i, r in enumerate(pool)]
print("no kernels    |amp| %.3f  spread %.3f" % (mag([response_set(s) for s in sims0]), spread(sims0)))
m.kernels = k
amps = [abs(np.mean(h[:31])) for h in k.values()]
print("kernel |mean 0-15s| median %.3f" % np.median(amps))
from dataclasses import replace as _r
from nematica.bench.causal import window
rng = np.random.default_rng(5)
npre, npost = window(0.5)
def at_random(rec):
    fr = rng.integers(npre, rec.n_frames - npost, len(rec.stims))
    return _r(rec, stims=[(k, int(f)) for (k, _), f in zip(rec.stims, fr)])
rr = [at_random(r) for r in pool]
print("real random   |amp| %.3f  spread %.3f" % (mag([response_set(r) for r in rr]), spread(rr)))
m.kernels = {}
ss = [at_random(s) for s in sims0]
print("bg random     |amp| %.3f  spread %.3f" % (mag([response_set(s) for s in ss]), spread(ss)))
# within-window fluctuation vs total SD, real vs model
def ratio(recs_):
    out = []
    for r in recs_:
        for i in range(r.x.shape[0]):
            v = r.x[i]; v = v[np.isfinite(v)]
            if v.size < 500: continue
            n = v.size // 10 * 10
            w = v[:n].reshape(-1, 10)
            out.append(np.std(w - w.mean(1, keepdims=True)) / np.std(v))
    return np.percentile(out, [10, 50, 90])
print("fluct/SD real", np.round(ratio(pool), 3), " model bg", np.round(ratio(sims0), 3))
def kurt(recs_):
    out = []
    for r in recs_:
        for i in range(r.x.shape[0]):
            v = r.x[i]; v = v[np.isfinite(v)]
            if v.size < 500: continue
            d = np.diff(v); out.append(np.mean((d - d.mean()) ** 4) / np.var(d) ** 2)
    return np.percentile(out, [10, 50, 90])
print("kurtosis of increments real", np.round(kurt(pool), 1), " model bg", np.round(kurt(sims0), 1))
