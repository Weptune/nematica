import sys, numpy as np, time; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import inputs as I, measures as M
Z=I.movie_features()
spf=float(sys.argv[2]) if len(sys.argv)>2 else 17.41
for gain in [float(x) for x in sys.argv[1].split(',')]:
    t=time.time()
    A,st,_=I.driven_random_rnn(Z,R=10,n=480,gain=gain,spf=spf,seed=0)
    L=st[1]; Y=np.stack([A[s:s+L] for s in st])          # raw native activity, no instrument
    Y=Y[:,::max(int(spf//3),1)]                            # thin to ~3 samples per frame for speed
    r=M.internal_measures(Y)
    print(f"gain {gain}: M1 {r['M1']:.2f} M2_int {r['M2_int']:.2f} ti {r['ti_int']:.1f} tl {r['tl_int']:.1f} ({time.time()-t:.0f}s)",flush=True)
