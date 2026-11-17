import sys, json, time, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import inputs as I, measures as M, record as Rc
from nematica.map import measures as MM
P=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']
prof={k:P['median'][k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
kind=sys.argv[1]
import torch, os
NET=f'/home/claude/nematica/data/derived/slow_nets/{kind}_seed0.pt'; os.makedirs(os.path.dirname(NET),exist_ok=True)
from nematica.map import zoo
if os.path.exists(NET):
    model=I.load_char_net(NET); data,V=zoo.chars(); split=len(data)-200_000; print('loaded',NET,flush=True)
else:
    t=time.time(); model,data,split=I.trained_char_net(kind,seed=0); print(kind,'trained',round(time.time()-t),'s',flush=True); I.save_char_net(model,NET,kind)
A,st=I.char_repeats(model,data,split,clip_len=3000,R=20)
tau=MM.tau_med(A[:st[0]+3000]); print('tau_med (chars)',round(tau,2),flush=True)
Y=np.stack([A[s:s+3000] for s in st]); sm,cr=M.repeat_autocov(Y,4)
print('raw internal share lag0',round((sm[0]-cr[0])/sm[0],3),'lag1',round((sm[1]-cr[1])/sm[1],3),flush=True)
D=Y-Y.mean(0); sh=(D**2).mean((0,2))/Y.var((0,2)).clip(1e-12)
print('internal share by position 0-10,10-50,50-200,200-1000,1000-3000 chars',[round(float(sh[a:b].mean()),3) for a,b in ((0,10),(10,50),(50,200),(200,1000),(1000,3000))],flush=True)
import resource; print('peak before recording GB',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6,flush=True)
Yr,k=Rc.record_repeats(A,st,3000,prof,seed=0); r=M.internal_measures(Yr)
print('instrument: bins',Yr.shape[1],'M1_lag1',round(r['M1_lag1'],3),'M2_lag1',round(r['M2_lag1'],3),'M1',round(r['M1'],3),flush=True)
