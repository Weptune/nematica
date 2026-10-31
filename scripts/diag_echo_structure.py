"""Diagnostic for the echo-complexity failure: how long significant responses last, how often
the set of responding classes changes, and what share of classes ever responds, real against
model (pool 1). Usage: python scripts/diag_echo_structure.py"""
import numpy as np, sys
sys.path.insert(0,'scripts')
from run_same_worms import make_model
from nematica.data.pumpprobe import load_pumpprobe_dir
from nematica.data.splits import load_folds
from nematica.bench.perturbational import event_matrices
import nematica.bench.causal as causal; causal.NORM='fluct'
recs={r.uid:r for r in load_pumpprobe_dir('data/raw/randi2023_wt_npz')}
folds=load_folds('configs/splits/pumpprobe_cv3.yaml')['folds']
pool=[recs[u] for u in folds[0]][:10]
rest=sorted(u for f in folds[1:] for u in f); val=rest[::5]
def stats(events):
    runs=[]; change=[]; frac_rows=[]
    for e in events:
        B=np.abs(np.nan_to_num(e['R']))>3
        for row in B:
            r=0
            for v in row:
                if v: r+=1
                elif r: runs.append(r); r=0
            if r: runs.append(r)
        change.append(np.mean(np.any(B[:,1:]!=B[:,:-1],axis=0)))
        frac_rows.append(np.mean(B.any(axis=1)))
    return np.median(runs), np.mean(runs), np.median(change), np.median(frac_rows)
print("real  (median run, mean run, share of steps where the active set changes, share of classes ever responding)", np.round(stats([e for r in pool for e in event_matrices(r,keep=True)]),3))
for spec in ['hybrid_kernels_regimes_obsfit','var3_spontaneous']:
    m=make_model(spec).fit([recs[u] for u in rest if u not in val],[recs[u] for u in val])
    print(spec, np.round(stats([e for i,r in enumerate(pool) for e in event_matrices(m.simulate(r,np.random.default_rng(i)),keep=True)]),3))
