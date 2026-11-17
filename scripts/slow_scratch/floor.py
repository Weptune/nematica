import sys, json, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import synthetic as S, record as Rc, measures as M
med=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']['median']
prof={k:med[k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
for tl in (0.7,1.5,6):
  for share in (0.0,0.5):
    o=[]
    for seed in (0,1):
        A,st=S.continuous(np.random.default_rng(seed),R=20,T=int(600*max(tl,1)),N=480,share=share,tau_locked=tl,tau_internal=4*tl)
        Y,k=Rc.record_repeats(A,st,int(600*max(tl,1)),prof,seed=seed)
        r=M.internal_measures(Y); o.append((r['M1'],r['M1_lag1'],r['M2_int']))
    o=np.nanmean(o,0); print(f"tau_locked {tl} share {share}: M1 {o[0]:.2f} M1_lag1 {o[1]:.2f} M2_int {o[2]:.2f}",flush=True)
