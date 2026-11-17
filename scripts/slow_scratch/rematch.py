import sys, json, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import synthetic as S, record as Rc, measures as M
P=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']
prof={k:P['median'][k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
for s in range(5):
    A,st=S.continuous(np.random.default_rng(s),R=20,T=1600,N=480,share=0.5,tau_locked=6,tau_internal=24)
    res=[]
    for ms in (s,s+100,s+200):
        k=Rc.recording.match(A[:,:200],'spikes',prof,seed=ms)
        Y,_=Rc.record_repeats(A,st,1600,prof,seed=s,k=k)
        r=M.internal_measures(Y); res.append((k['gain'],k['bin_steps'],r['M1_lag1'],r['M2_lag1']))
    print(s,np.round(res,3).tolist(),flush=True)
