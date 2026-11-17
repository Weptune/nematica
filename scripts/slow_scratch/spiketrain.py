"""Review S-R1 checks: zero internal state, locked rate identical on every repeat, non-Poisson spike trains,
and per-unit rate drift between two blocks."""
import sys, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import measures as M
from nematica.map.synthetic import ou
def gen(rng, R=20, nb=1500, N=200, kind="poisson", drift=0.0, share=0.0, tau_int=200, K=10):
    ms=nb*20
    lat=ou(nb, np.full(K,8.0), rng, K)@ (rng.standard_normal((K,N))/np.sqrt(K))      # locked, per 20 ms bin
    lat=lat/lat.std(0)
    base=np.log(3.0)+rng.normal(0,0.8,N)                                           # ~3 Hz, spread
    blk=np.stack([np.zeros(N), rng.normal(0,drift,N)])                             # per-unit block offset
    li=rng.standard_normal((K,N))/np.sqrt(K)
    eint=ou(R*nb, np.full(K,float(tau_int)), rng, K)@li; eint=(eint/eint.std(0)).reshape(R,nb,N)
    Y=np.zeros((R,nb,N),np.float32)
    for r in range(R):
        z=np.sqrt(1-share)*lat+np.sqrt(share)*eint[r]
        rate=np.exp(base+0.5*z+blk[int(r>=R//2)])                                  # Hz, per bin
        lam=np.repeat(rate,20,axis=0)/1000.0                                       # per ms
        if kind=="poisson":
            sp=rng.random((ms,N))<lam
        else:
            sp=np.zeros((ms,N),bool); last=np.full(N,-100)
            u=rng.random((ms,N))
            for t in range(ms):
                if kind=="dead":
                    s=(u[t]<lam[t]*1.0)&(t-last>=10)
                else:  # burst: a spike makes another spike likely within the next few ms
                    boost=np.where((t-last>=2)&(t-last<=10),0.03,0.0)
                    s=u[t]<lam[t]+boost
                sp[t]=s; last[s]=t
        Y[r]=sp.reshape(nb,20,N).sum(1)
    return Y
import json
out=open('/tmp/s7/spiketype.jsonl','a')
for seed in (1,2):
    for share in (0.0,0.1,0.3,0.6):
        for kind in ("poisson","dead","burst"):
            Y=gen(np.random.default_rng(seed*100+int(share*10)),kind=kind,share=share)
            r=M.lag_measures(Y,k0=2)
            out.write(json.dumps(dict(seed=seed,share=share,kind=kind,drift=0,M1=r["M1"],M2=r["M2"]))+"\n"); out.flush()
    for drift in (0.2,0.4):
        Y=gen(np.random.default_rng(seed*100+7),kind="poisson",drift=drift,share=0.0)
        r=M.lag_measures(Y,k0=2)
        out.write(json.dumps(dict(seed=seed,share=0.0,kind="poisson",drift=drift,M1=r["M1"],M2=r["M2"]))+"\n"); out.flush()
print("done",flush=True)
