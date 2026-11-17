import sys, json, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import inputs as I, measures as M, record as Rc
from nematica.map import zoo
P=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']
prof={k:P['median'][k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
Z=I.movie_features(); spf=I.steps_per_frame(27.15,prof['bins_per_tau'])
A0,st,_=I.driven_random_rnn(Z,R=20,n=480,gain=0.86,spf=spf,seed=0); L=st[1]-st[0]
for share in [float(x) for x in sys.argv[1].split(',')]:
    A=I.add_slow_drive(A0,share,tau_steps=float(sys.argv[2])*30*spf,seed=0) if share>0 else A0
    Y,k=Rc.record_repeats(A,st,L,prof,seed=0); r=M.internal_measures(Y)
    print('slow share',share,'tau_s',sys.argv[2],'bins',Y.shape[1],'M1_lag1',round(r['M1_lag1'],3),'M2_lag1',round(r['M2_lag1'],2),'ceiling',r['M2_ceiling'],flush=True)
