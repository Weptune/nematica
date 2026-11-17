import sys, os, json, time, numpy as np, torch; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import inputs as I, measures as M, record as Rc
P=json.load(open('/home/claude/nematica/docs/figures/map_step1.json'))['preparations']['R4a']
prof={k:P['median'][k] for k in ('bins_per_tau','count_per_bin','noise','rate_log_sd')}
NET='/home/claude/nematica/data/derived/slow_nets/a2_seed0.pt'
if os.path.exists(NET): net=I.load_task_rnn(NET); print('loaded',flush=True)
else:
    t=time.time(); net,acc=I.trained_task_rnn(seed=0); I.save_task_rnn(net,NET); print('trained, accuracy',round(acc,3),round(time.time()-t),'s',flush=True)
A,st=I.task_rnn_repeats(net,R=20,clip_trials=100)
L=6000
Y,k=Rc.record_repeats(A,st,L,prof,seed=0); r=M.internal_measures(Y)
print('A2 instrument: bins',Y.shape[1],'bin_steps',round(k['bin_steps'],2),'hold',k.get('hold'),'M1_lag1',round(r['M1_lag1'],3),'M2_lag1',round(r['M2_lag1'],2),'ti',round(r['ti_lag1'],1),'tl',round(r['tl_lag1'],1),flush=True)
