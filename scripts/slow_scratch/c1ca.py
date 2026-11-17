"""Formal C1 for the lag-1 measures at four real instruments, with the clip at the Allen length (1,500 bins)."""
import sys, json, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from multiprocessing import Pool
from nematica.slow import synthetic as S, record as Rc, measures as M
P2=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']
pick=lambda r:{k:r[k] for k in K}
INST={'ca_R3':{k:P2['R3']['median'][k] for k in ('decay_over_tau','frames_per_tau','noise')},'ca_noisy':{'decay_over_tau':P2['R3']['median']['decay_over_tau'],'frames_per_tau':P2['R3']['median']['frames_per_tau'],'noise':0.8}}
TL=6.0; BINS=900; R=10; N=480
SHARE=[0.05,0.1,0.2,0.4,0.8]; RATIO=[1,2,4,8,16]
OUT='/tmp/s7/c1ca.jsonl'
def job(a):
    inst,sweep,level,seed=a; prof=INST[inst]
    share,ratio=(level,4) if sweep=="share" else (0.5,level)
    # pilot: match the instrument on a short run of the same system, then size the clip to BINS bins
    T0=int(round(BINS*TL*3/prof['frames_per_tau']))+50
    A,st=S.continuous(np.random.default_rng(seed),R=3,T=T0,N=N,share=share,tau_locked=TL,tau_internal=ratio*TL)
    k=Rc.recording.match(A[:,:Rc.recording.MATCH_MIN_UNITS],'calcium',prof,seed=seed); del A
    per=Rc.recording.per_sample(k,'calcium')
    T=int(np.ceil((BINS+2)*per))
    A,st=S.continuous(np.random.default_rng(seed),R=R,T=T,N=N,share=share,tau_locked=TL,tau_internal=ratio*TL)
    Y,k=Rc.record_repeats(A,st,T,prof,rtype='calcium',seed=seed,k=k); del A
    r=M.internal_measures(Y)
    row=dict(inst=inst,sweep=sweep,level=level,seed=seed,T_native=T,bins=Y.shape[1],
             **{m:r[m] for m in ("M1","M1_lag1","M2_int","M2_lag1","M2")})
    with open(OUT,'a') as f: f.write(json.dumps(row)+"\n")
    return row
if __name__=="__main__":
    done=set()
    try: done={(d['inst'],d['sweep'],d['level'],d['seed']) for d in map(json.loads,open(OUT))}
    except FileNotFoundError: pass
    jobs=[(i,s,l,sd) for i in INST for s,L in (("share",SHARE),("ratio",RATIO)) for l in L for sd in (0,1) if (i,s,l,sd) not in done]
    print(len(jobs),"jobs;",INST,flush=True)
    with Pool(int(sys.argv[1]) if len(sys.argv)>1 else 1) as p:
        for r in p.imap_unordered(job,jobs): pass
    print("done",flush=True)
