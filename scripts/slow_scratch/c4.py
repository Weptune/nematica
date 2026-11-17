import sys, numpy as np, json; sys.path.insert(0,'/home/claude/nematica')
from multiprocessing import Pool
from nematica.slow import synthetic as S, record as Rc, measures as M
med=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']['median']
prof={k:med[k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
BASE=dict(R=20,T=4000,N=480,share=0.5,tau_locked=6,tau_internal=24)
KN={"native_tau":[dict(tau_locked=2,tau_internal=8,T=1400),dict(tau_locked=6,tau_internal=24),dict(tau_locked=18,tau_internal=72,T=12000)],
    "population":[dict(N=200),dict(N=480),dict(N=1200)],
    "repeats":[dict(R=20),dict(R=60)],
    "clip_length":[dict(T=2000),dict(T=4000),dict(T=8000)]}
def job(a):
    knob,i,seed=a; p={**BASE,**KN[knob][i]}
    A,st=S.continuous(np.random.default_rng(seed),**p)
    Y,k=Rc.record_repeats(A,st,p["T"],prof,seed=seed)
    r=M.internal_measures(Y)
    return knob,i,seed,r['M1'],r['M2_int'],r['M2']
jobs=[(k,i,s) for k in KN for i in range(len(KN[k])) for s in (0,1)]
with Pool(2) as p: res=p.map(job,jobs)
RANGE={"M1":0.66,"M2_int":6.4,"M2":2.3}
for k in KN:
    for j,name in ((3,"M1"),(4,"M2_int"),(5,"M2")):
        means=[np.nanmean([r[j] for r in res if r[0]==k and r[1]==i]) for i in range(len(KN[k]))]
        print(k, name, np.round(means,3), "C4 ratio", round((max(means)-min(means))/RANGE[name],2))
