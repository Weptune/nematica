"""Exploratory: directional summaries (real vs simulated pool worms, one cv3 fold): participation
ratio, mean |correlation|, AVA high-bout durations, half-decay time, echo magnitude."""
import sys, time, numpy as np
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
from run_same_worms import make_model, bench_sample
from nematica.systems.causal_models import ClassVAR
from nematica.data.pumpprobe import load_pumpprobe_dir
from nematica.data.splits import load_folds
from nematica.bench.levels import participation_ratio, ava_bouts, half_decay_time
import nematica.bench.causal as causal
from nematica.bench.causal import response_set
causal.NORM = "fluct"
fi = int(sys.argv[1]); models = sys.argv[2].split(",")
split = sys.argv[3] if len(sys.argv) > 3 else "configs/splits/pumpprobe_cv3.yaml"
recs = {r.uid: r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz")}
folds = load_folds(split)["folds"]
pool_uids = folds[fi]
rest = sorted(u for f in folds if f is not pool_uids for u in f)
val_uids = rest[::5]
train = [recs[u] for u in rest if u not in val_uids]; val = [recs[u] for u in val_uids]
pool = [recs[u] for u in pool_uids]
classes = ClassVAR(3, "all").fit(train, val).classes
def summ(bs, rsets):
    prs, cs, bouts, taus, amps = [], [], [], [], []
    for b in bs:
        ok = np.isfinite(b.x).all(1); x = b.x[ok]
        prs.append(participation_ratio(x))
        c = np.corrcoef(x); cs.append(np.abs(c[np.triu_indices_from(c, 1)]).mean())
        bouts.append(ava_bouts(b))
        taus.append(np.nanmedian([half_decay_time(r, b.dt) for r in x]))
    for rs in rsets:
        a = [abs(rs.amp(k)) for k in rs.traces]; a = [v for v in a if np.isfinite(v)]
        if a: amps.append(np.median(a))
    bb = np.concatenate([x for x in bouts if x.size])
    return "PR %.1f [%.1f-%.1f]  |r| %.3f [%.3f-%.3f]  AVA bouts n/worm %.1f dur med %.1fs p90 %.1fs  tau %.1fs [%.1f-%.1f]  |amp| %.3f" % (
        np.median(prs), *np.percentile(prs, [10, 90]), np.median(cs), *np.percentile(cs, [10, 90]),
        np.mean([x.size for x in bouts]), np.median(bb), np.percentile(bb, 90), np.median(taus), *np.percentile(taus, [10, 90]), np.median(amps))
real_b = [bench_sample(r, classes, "r", r.uid) for r in pool]
print("real".ljust(48), summ(real_b, [response_set(r) for r in pool]), flush=True)
for name in models:
    t = time.time(); m = make_model(name).fit(train, val)
    sims = [m.simulate(r, np.random.default_rng(1000 * fi + i)) for i, r in enumerate(pool)]
    sb = [bench_sample(x, classes, "s", r.uid) for x, r in zip(sims, pool)]
    print(name.ljust(48), summ(sb, [response_set(s) for s in sims]), "(%.0fs)" % (time.time() - t), flush=True)
