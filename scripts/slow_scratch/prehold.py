import sys, json, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import inputs as I, measures as M, record as Rc
from nematica.map import zoo
P=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']
prof={k:P['median'][k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
m=I.load_char_net('/home/claude/nematica/data/derived/slow_nets/'+sys.argv[1]+'_seed0.pt'); data,V=zoo.chars(); split=len(data)-200_000
A,st=I.char_repeats(m,data,split,clip_len=1000,R=20)
for h in [int(x) for x in sys.argv[2].split(",")]:
    Y,k=Rc.record_repeats(A,st,1000,prof,seed=0,prehold=h); r=M.internal_measures(Y)
    print(sys.argv[1],'prehold',h,'bins',Y.shape[1],'M1_lag1',round(r['M1_lag1'],3),'M2_lag1',round(r['M2_lag1'],2),flush=True)
