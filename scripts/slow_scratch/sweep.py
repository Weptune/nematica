import sys, numpy as np, json, time; sys.path.insert(0,'/home/claude/nematica')
from scipy.stats import spearmanr
from multiprocessing import Pool
from nematica.slow import synthetic as S, record as Rc, measures as M
med=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']['median']
prof={k:med[k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
G=int(sys.argv[1]) if len(sys.argv)>1 else 8
def job(a):
    kind, lv, seed = a
    share, tl, ti = (lv, 6, 24) if kind=='M1' else (0.5, 6, 6*lv)
    A,st=S.continuous(np.random.default_rng(seed),R=20,T=4000,N=480,share=share,tau_locked=tl,tau_internal=ti)
    Y,k=Rc.record_repeats(A,st,4000,prof,group=G if G>1 else None, seed=seed)
    r=M.internal_measures(Y)
    return kind, lv, seed, r['M1'], r['M2'], r['M2_int'], r['t_locked'], r['tl_int']
jobs=[('M1',lv,s) for lv in (0.1,0.25,0.4,0.6,0.8) for s in (0,1)]+[('M2',lv,s) for lv in (1,2,4,8,16) for s in (0,1)]
with Pool(2) as p: res=p.map(job, jobs)
for kind in ('M1','M2'):
    rows=[r for r in res if r[0]==kind]; x=[r[1] for r in rows]
    for j,name in ((3,'M1'),(4,'M2 half-life'),(5,'M2 integral')):
        y=np.array([r[j] for r in rows]); ok=np.isfinite(y)
        print('G',G,'sweep',kind, name, 'rho', round(spearmanr(np.array(x)[ok],y[ok])[0],2), np.round(y,2))
    print('   t_locked', np.round([r[6] for r in rows],2), 'tl_int', np.round([r[7] for r in rows],2))
