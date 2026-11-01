import warnings, copy, itertools
warnings.filterwarnings("ignore")
import numpy as np
from nematica.bench import causal
from nematica.bench.causal import response_set, c_pattern
from nematica.bench.scorecard import fold_parts
from nematica.data.pumpprobe import load_pumpprobe_dir
from nematica.data.splits import load_folds
from nematica.systems.causal_models import CreamerCausal
causal.NORM = "fluct"
recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
folds = load_folds("configs/splits/pumpprobe_cv3.yaml")["folds"]
_, _, pool = fold_parts(recs, folds, 0)
pool = pool[:14]
m = CreamerCausal("connectome_constrained", protocol="native")
quiet = copy.copy(m); quiet.Lq = 0 * m.Lq; quiet.sr = 0 * m.sr
real = [response_set(r) for r in pool]
noisy = [response_set(m.simulate(r, np.random.default_rng(i))) for i, r in enumerate(pool)]
clean = [response_set(quiet.simulate(r, np.random.default_rng(i))) for i, r in enumerate(pool)]
def agree(A, B, same_ok=False):
    v = [1 - c_pattern(a, b) for i, a in enumerate(A) for j, b in enumerate(B) if (same_ok or i != j)]
    v = [x for x in v if np.isfinite(x)]
    return np.median(v), len(v)
print("real vs real            %.3f (n=%d)" % agree(real, real))
print("noisy model vs real     %.3f (n=%d)" % agree(noisy, real))
print("noise-free model vs real %.3f (n=%d)" % agree(clean, real))
print("noisy model vs noisy model (different worms) %.3f (n=%d)" % agree(noisy, noisy))
# population average echo: mean amplitude per pair over real worms vs noise-free model
keys = set().union(*[set(r.traces) for r in real])
ra, ma = [], []
for k in keys:
    rv = [r.amp(k) for r in real if k in r.traces and np.isfinite(r.amp(k))]
    mv = [c.amp(k) for c in clean if k in c.traces and np.isfinite(c.amp(k))]
    if len(rv) >= 3 and mv:
        ra.append(np.mean(rv)); ma.append(np.mean(mv))
print("population-average echo, noise-free model vs real: r = %.3f over %d pairs" % (np.corrcoef(ra, ma)[0, 1], len(ra)))
# echo-to-noise: size of the response vs pre-stimulus fluctuation, model vs real
def snr(sets):
    return np.nanmedian([abs(s.amp(k)) for s in sets for k in s.traces])
print("median |response| in fluct units: real %.2f, noisy model %.2f, noise-free model %.2f" % (snr(real), snr(noisy), snr(clean)))
# per-trial reliability: one worm's echo against the average echo of the others (leave one out)
def loo(sets, ref=None):
    out = []
    for i, s in enumerate(sets):
        others = [o for j, o in enumerate(ref or sets) if j != i]
        ks = [k for k in s.traces if np.isfinite(s.amp(k))]
        a, b = [], []
        for k in ks:
            v = [o.amp(k) for o in others if k in o.traces and np.isfinite(o.amp(k))]
            if len(v) >= 3:
                a.append(s.amp(k)); b.append(np.mean(v))
        if len(a) >= 20:
            out.append(np.corrcoef(a, b)[0, 1])
    return np.median(out)
print("one real worm vs mean of other real worms:      r = %.3f" % loo(real))
print("one noisy model worm vs mean of real worms:     r = %.3f" % loo(noisy, real))
print("one noisy model worm vs its own noise-free echo: r = %.3f" %
      np.median([np.corrcoef(*zip(*[(n.amp(k), c.amp(k)) for k in n.traces if k in c.traces and np.isfinite(n.amp(k)) and np.isfinite(c.amp(k))]))[0, 1] for n, c in zip(noisy, clean)]))
