import sys, json, resource, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import synthetic as S, record as Rc, measures as M
from nematica.map import recording
def pk(tag): print(tag, round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6,2),'GB',flush=True)
med=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']['median']
prof={k:med[k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
R=int(sys.argv[1])
A,st=S.continuous(np.random.default_rng(0),R=R,T=4000,N=480,share=0.5,tau_locked=6,tau_internal=24); pk('synthetic')
k=recording.match(A[:,:200],'spikes',prof,seed=0); pk('match'); print({x:k[x] for x in ('hold','bin_steps','gain') if x in k})
Y,_=Rc.record_repeats(A,st,4000,prof,seed=0); pk("record")
r=M.internal_measures(Y); pk('measures')
