import sys, json, time, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import inputs as I, measures as M, record as Rc
P=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']
prof={k:P['median'][k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
Z=I.movie_features(); spf=I.steps_per_frame(27.15,prof['bins_per_tau'])
for gain in [float(x) for x in sys.argv[1].split(',')]:
    t=time.time()
    A,st,_=I.driven_random_rnn(Z,R=20,n=480,gain=gain,spf=spf,seed=0)
    L=st[1]-st[0]
    Y,k=Rc.record_repeats(A,st,L,prof,seed=0); del A
    r=M.internal_measures(Y)
    print(f"gain {gain}: bins {Y.shape[1]} bin_steps {k['bin_steps']:.1f} M1_lag1 {r['M1_lag1']:.3f} M2_lag1 {r['M2_lag1']:.2f} (M1 {r['M1']:.2f}) {time.time()-t:.0f}s",flush=True)
