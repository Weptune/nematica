"""Formal C1 for the lag-1 measures at four real instruments, with the clip at the Allen length (1,500 bins)."""
import sys, json, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from multiprocessing import Pool
from nematica.slow import synthetic as S, record as Rc, measures as M
P=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']
ind=P['individuals']; K=('bins_per_tau','count_per_bin','noise','rate_log_sd')
pick=lambda r:{k:r[k] for k in K}
INST={"median":{k:P['median'][k] for k in K},
      "fastest":pick(min(ind,key=lambda r:r['bins_per_tau'])),
      "slowest":pick(max(ind,key=lambda r:r['bins_per_tau'])),
      "noisiest":pick(max(ind,key=lambda r:r['noise']))}
TL=6.0; BINS=1500; R=20; N=480
SHARE=[0.05,0.1,0.2,0.4,0.8]; RATIO=[1,2,4,8,16]; GAINMOD=[0.0,0.1,0.2,0.4,0.8]
OUT='/tmp/s7/c1v4.jsonl'
def job(a):
    inst,sweep,level,seed=a; prof=INST[inst]
    share,ratio=(level,4) if sweep=="share" else ((0.5,level) if sweep=="ratio" else (0.0,4))
    # pilot: match the instrument on a short run of the same system, then size the clip to BINS bins
    T0=int(round(BINS*TL*3/prof['bins_per_tau']))+50
    A,st=S.continuous(np.random.default_rng(seed),R=3,T=T0,N=N,share=share,tau_locked=TL,tau_internal=ratio*TL)
    k=Rc.recording.match(A[:,:Rc.recording.MATCH_MIN_UNITS],'spikes',prof,seed=seed); del A
    per=Rc.recording.per_sample(k,'spikes')
    T=int(np.ceil((BINS+2)*per))
    A,st=S.continuous(np.random.default_rng(seed),R=R,T=T,N=N,share=share,tau_locked=TL,tau_internal=ratio*TL)
    if sweep=="gain":      # S-R2 finding 1: multiplicative internal state (a slow per-unit gain)
        from nematica.map.synthetic import ou
        g_=ou(len(A),np.full(10,4*TL),np.random.default_rng(seed+500),10)@(np.random.default_rng(seed+501).standard_normal((10,N))/np.sqrt(10))
        A=A*np.exp(level*g_/g_.std(0)).astype(np.float32)
    Y,k=Rc.record_repeats(A,st,T,prof,seed=seed,k=k); del A
    r=M.lag_measures(Y,k0=2)
    row=dict(inst=inst,sweep=sweep,level=level,seed=seed,T_native=T,bins=Y.shape[1],
             **{m:r[m] for m in ("M1","M2","int_ceiling","lock_ceiling")})
    with open(OUT,'a') as f: f.write(json.dumps(row)+"\n")
    return row
if __name__=="__main__":
    done=set()
    try: done={(d['inst'],d['sweep'],d['level'],d['seed']) for d in map(json.loads,open(OUT))}
    except FileNotFoundError: pass
    jobs=[(i,s,l,sd) for i in INST for s,L in (("share",SHARE),("ratio",RATIO),("gain",GAINMOD)) for l in L for sd in (0,1) if (i,s,l,sd) not in done]
    print(len(jobs),"jobs;",{k:{x:round(v[x],3) for x in K} for k,v in INST.items()},flush=True)
    with Pool(int(sys.argv[1]) if len(sys.argv)>1 else 1) as p:
        for r in p.imap_unordered(job,jobs): pass
    print("done",flush=True)
