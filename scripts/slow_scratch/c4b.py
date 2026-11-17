import sys, numpy as np, json; sys.path.insert(0,'/home/claude/nematica')
from multiprocessing import Pool
from nematica.slow import synthetic as S, record as Rc, measures as M
med=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']['median']
prof={k:med[k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
BASE=dict(R=20,T=4000,N=480,share=0.5,tau_locked=6,tau_internal=24)
KN={"native_tau":[dict(tau_locked=2,tau_internal=8,T=1400),dict(tau_locked=6,tau_internal=24),dict(tau_locked=18,tau_internal=72,T=12000)],
    "population":[dict(N=200),dict(N=480),dict(N=1200)],
    "repeats":[dict(R=20),dict(R=60)],
    "clip_length":[dict(T=450),dict(T=2000),dict(T=4000),dict(T=8000)]}
OUT='/tmp/s7/c4v3.jsonl'
def job(a):
    knob,i,seed=a; p={**BASE,**KN[knob][i]}
    A,st=S.continuous(np.random.default_rng(seed),**p)
    Y,k=Rc.record_repeats(A,st,p["T"],prof,seed=seed); del A
    r=M.lag_measures(Y,k0=2)
    row=dict(knob=knob,level=i,seed=seed,bins=int(Y.shape[1]),**{m:r[m] for m in ("M1","M2","int_ceiling")})
    with open(OUT,'a') as f: f.write(json.dumps(row)+"\n")
    return row
done=set()
try: done={(d['knob'],d['level'],d['seed']) for d in map(json.loads,open(OUT))}
except FileNotFoundError: pass
jobs=[(k,i,s) for k in KN for i in range(len(KN[k])) for s in (0,1) if (k,i,s) not in done]
# heavy jobs first, one at a time alongside light ones
jobs.sort(key=lambda j: -(KN[j[0]][j[1]].get("T",4000)*KN[j[0]][j[1]].get("R",20)*KN[j[0]][j[1]].get("N",480)))
[print(job(j),flush=True) for j in jobs]
print("done")
