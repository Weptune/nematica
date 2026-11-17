import sys, json, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import synthetic as S, record as Rc, measures as M
med=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']['median']
prof={k:med[k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
cases=[(6,1,0.05),(6,16,0.05),(6,4,0.0)]
for tl,ratio,share in cases:
    o=[]
    for seed in (0,1):
        T=int(600*max(tl,1)); A,st=S.continuous(np.random.default_rng(seed),R=20,T=T,N=480,share=share,tau_locked=tl,tau_internal=ratio*tl)
        Y,k=Rc.record_repeats(A,st,T,prof,seed=seed)
        r=M.internal_measures(Y); o.append((r['M1'],r['M1_lag1'],r['M2_int'],r['M2_lag1']))
    o=np.nanmean(o,0); print(f"tau_locked {tl} ratio {ratio} share {share}: M1 {o[0]:.2f} M1_lag1 {o[1]:.2f} M2_int {o[2]:.2f} M2_lag1 {o[3]:.2f}",flush=True)
