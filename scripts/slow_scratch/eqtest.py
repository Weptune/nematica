import sys,numpy as np,json; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import synthetic as S, record as Rc, measures as M
from nematica.map import recording
med=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']['median']
prof={k:med[k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
A,st=S.continuous(np.random.default_rng(3),R=6,T=1500,N=300,share=0.4,tau_locked=6,tau_internal=24)
for B in (A, A.astype(np.float64), A.astype(np.float32)):
    k1=recording.match(B,'spikes',prof,seed=3); k2=recording.match(B[:,:200],'spikes',prof,seed=3)
    print(B.dtype,'full',round(k1['gain'],4),'200 cols',round(k2['gain'],4))
