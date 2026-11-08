"""Exploratory: why the emulator recipe fails on Atanas worms. Directional summaries, real vs recipe vs
VAR(3), pool 0: participation ratio, mean |r|, half-decay time, autocorrelation profile, skewness,
member (left/right) correlation."""
import sys, numpy as np
from collections import defaultdict
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
from run_same_worms import make_model, bench_sample
from nematica.systems.causal_models import ClassVAR
from nematica.data.atanas_pp import load_atanas_pp_dir
from nematica.data.splits import load_folds
from nematica.bench.levels import participation_ratio, half_decay_time
from scipy.stats import skew
recs = {r.uid: r for r in load_atanas_pp_dir("data/raw/atanas2023_wwweb")}
folds = load_folds("configs/splits/atanas2023_cv3.yaml")["folds"]
fi = 0
pool = [recs[u] for u in folds[fi]]
rest = sorted(u for f in folds if f is not folds[fi] for u in f); vu = rest[::5]
train = [recs[u] for u in rest if u not in vu]; val = [recs[u] for u in vu]
classes = ClassVAR(3, "all").fit(train, val).classes
print("frames per worm", [r.n_frames for r in pool][:5], "dt", pool[0].dt)
def memcorr(rs):
    out = []
    for r in rs:
        by = defaultdict(list)
        for j, c in enumerate(r.classes):
            if c: by[c].append(j)
        for js in by.values():
            if len(js) >= 2:
                a, b = r.x[js[0]], r.x[js[1]]; ok = np.isfinite(a) & np.isfinite(b)
                if ok.sum() > 200: out.append(np.corrcoef(a[ok], b[ok])[0, 1])
    return np.median(out) if out else np.nan
def summ(bs):
    pr, rr, tau, sk, acf = [], [], [], [], []
    for b in bs:
        ok = np.isfinite(b.x).all(1); x = b.x[ok]
        pr.append(participation_ratio(x)); c = np.corrcoef(x); rr.append(np.abs(c[np.triu_indices_from(c, 1)]).mean())
        tau.append(np.nanmedian([half_decay_time(v, b.dt) for v in x])); sk.append(np.median(skew(x, axis=1)))
        acf.append([np.median([(v[L:] * v[:-L]).mean() / v.var() for v in x - x.mean(1, keepdims=True)]) for L in (1, 4, 16, 64)])
    return "PR %.1f  |r| %.3f  tau %.1fs  skew %.2f  acf(1,4,16,64) %s" % (np.median(pr), np.median(rr), np.median(tau), np.median(sk), np.round(np.median(acf, 0), 2))
print("real".ljust(12), summ([bench_sample(r, classes, "r", r.uid) for r in pool]), " member r %.2f" % memcorr(pool))
for n in ("var3_spontaneous", "hybrid_kernels_slow6d_indivslow1_hp_mem_diag_hsd1"):
    m = make_model(n).fit(train, val)
    sims = [m.simulate(r, np.random.default_rng(i)) for i, r in enumerate(pool)]
    print(n[:12].ljust(12), summ([bench_sample(s, classes, "s", r.uid) for s, r in zip(sims, pool)]), " member r %.2f" % memcorr(sims))
    if hasattr(m, "slow_model") and m.slow_model is not None:
        print("   slow info", m.slow_model.info)
