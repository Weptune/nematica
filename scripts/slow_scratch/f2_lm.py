import sys, json, numpy as np, time; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import inputs as I, measures as M, record as Rc
from nematica.map import measures as MM
med=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']['median']
prof={k:med[k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
tok=np.load('/home/claude/nematica/data/external/books/tokens.npy')
model=sys.argv[1]; C=int(sys.argv[2]); ctx=int(sys.argv[3]); R=int(sys.argv[4]) if len(sys.argv)>4 else 20
t=time.time()
clip,ctxs=I.text_clip_and_contexts(tok,C,ctx,R,seed=0)
A,st,meta=I.lm_repeats(model,clip,ctxs)
sm,cr=M.repeat_autocov(np.stack([A[s:s+C] for s in st]),4)
Y,k=Rc.record_repeats(A,st,C,prof,seed=0)
r=M.internal_measures(Y)
print(f"{model} clip {C} ctx {ctx} R {R}: tau_med {MM.tau_med(A[:C]):.2f}; raw lag-0 internal var share {(sm[0]-cr[0])/sm[0]:.2f}; recorded Y {Y.shape} M1_lag1 {r['M1_lag1']:.3f} M2_lag1 {r['M2_lag1']:.2f} M1 {r['M1']:.2f} ({time.time()-t:.0f}s)",flush=True)
