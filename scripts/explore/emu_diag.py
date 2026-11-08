"""Exploratory: where do emulator backgrounds miss on dimensionality? Per-worm participation ratio,
real vs simulated, on the pool worms of one cv3 fold."""
import sys, time, numpy as np
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
from run_same_worms import make_model, bench_sample
from nematica.systems.causal_models import ClassVAR, spontaneous_mask
from nematica.data.pumpprobe import load_pumpprobe_dir
from nematica.bench.levels import participation_ratio
from nematica.data.splits import load_folds
import nematica.bench.causal as causal
causal.NORM = "recording"
DATA = "data/raw/randi2023_wt_npz"
fi = int(sys.argv[1]); models = sys.argv[2].split(",")
recs = {r.uid: r for r in load_pumpprobe_dir(DATA)}
folds = load_folds("configs/splits/pumpprobe_cv3.yaml")["folds"]
pool_uids = folds[fi]
rest = sorted(u for f in folds if f is not pool_uids for u in f)
val_uids = rest[::5]
train = [recs[u] for u in rest if u not in val_uids]; val = [recs[u] for u in val_uids]
pool = [recs[u] for u in pool_uids]
classes = ClassVAR(3, "all").fit(train, val).classes
def pr(b):
    ok = np.isfinite(b.x).all(1)
    return participation_ratio(b.x[ok]), ok.sum()
real = [pr(bench_sample(r, classes, "r", r.uid)) for r in pool]
print("real PR median %.2f IQR %.2f-%.2f  n_classes median %d" % (np.median([p for p,_ in real]), *np.percentile([p for p,_ in real],[25,75]), np.median([n for _,n in real])))
# real spontaneous-only frames
import copy
sp=[]
for r in pool:
    b = bench_sample(r, classes, "r", r.uid); m = spontaneous_mask(r)
    ok = np.isfinite(b.x).all(1); x = b.x[ok][:, m[:b.x.shape[1]]] if m.size>=b.x.shape[1] else b.x[ok]
    sp.append(participation_ratio(x))
print("real PR spontaneous frames median %.2f" % np.median(sp))
for name in models:
    t=time.time(); m = make_model(name).fit(train, val)
    sims = [m.simulate(r, np.random.default_rng(1000*fi+i)) for i, r in enumerate(pool)]
    s = [pr(bench_sample(x, classes, "s", r.uid)) for x, r in zip(sims, pool)]
    ratio = [np.log(a[0]/b[0]) for a,b in zip(s, real)]
    print("%s PR median %.2f IQR %.2f-%.2f  log(sim/real) median %.2f  (%.0fs)" % (name, np.median([p for p,_ in s]), *np.percentile([p for p,_ in s],[25,75]), np.median(ratio), time.time()-t))
