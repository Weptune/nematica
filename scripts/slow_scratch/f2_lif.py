import sys, json, time, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import inputs as I, measures as M, record as Rc
P=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']
prof={k:P['median'][k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
Z=I.movie_features(); spf=(1000/30)/5
for gain in [float(x) for x in sys.argv[1].split(',')]:
    t=time.time(); A,st=I.driven_lif(Z,R=20,spf=spf,gain=gain,seed=0)
    A=A[:, np.sort(np.random.default_rng(0).choice(1000,480,replace=False))]
    L=st[1]-st[0]; Yraw=np.stack([A[s:s+L] for s in st]); sm,cr=M.repeat_autocov(Yraw,3)
    raw=(sm[1]-cr[1])/sm[1] if sm[1]>0 else float('nan')
    from nematica.map import measures as MM
    tau=MM.tau_med(A)
    try:
        Y,k=Rc.record_repeats(A,st,L,prof,seed=0); r=M.internal_measures(Y)
        inst=f"bins {Y.shape[1]} M1_lag1 {r['M1_lag1']:.3f} M2_lag1 {r['M2_lag1']:.2f}"
    except Exception as e: inst=f"instrument failed: {type(e).__name__} {e}"
    print(f"gain {gain}: rate {A.mean()/0.005:.1f} Hz, tau_med {tau}, raw lag-1 (5 ms) internal share {raw:.3f}; {inst} ({time.time()-t:.0f}s)",flush=True)
