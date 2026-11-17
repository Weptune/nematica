import sys, time, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import inputs as I, measures as M
from nematica.map import measures as MM
Z=I.movie_features(); spf=(1000/30)/5
for gain in [float(x) for x in sys.argv[1].split(',')]:
    t=time.time(); A,st=I.driven_lif(Z,R=20,spf=spf,gain=gain,seed=0)
    L=st[1]-st[0]; nb=L//4
    Y=np.stack([A[s:s+nb*4].reshape(nb,4,-1).sum(1) for s in st])      # 20 ms bins, like the mice
    Y=Y[:,:,np.sort(np.random.default_rng(0).choice(1000,480,replace=False))]
    r=M.internal_measures(Y)
    print(f"gain {gain}: 20 ms bins {nb}, count/bin {Y.mean():.3f}, tau_med(bins) {MM.tau_med(Y.reshape(-1,480))}, noise share {r['noise_share']:.3f}, M1_lag1 {r['M1_lag1']:.3f} M2_lag1 {r['M2_lag1']:.2f} M1 {r['M1']:.2f} ({time.time()-t:.0f}s)",flush=True)
