import sys, time, numpy as np; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import inputs as I, measures as M
from nematica.map import measures as MM
t=time.time(); net,acc=I.trained_task_rnn(seed=0); print('A2 trained, accuracy',round(acc,3),round(time.time()-t),'s',flush=True)
A,st=I.task_rnn_repeats(net,R=20,clip_trials=100)
L=100*60; Y=np.stack([A[s:s+L] for s in st])
print('tau_med',round(MM.tau_med(A),1))
sm,cr=M.repeat_autocov(Y[:,::10],3); print('raw lag-0 internal share',round((sm[0]-cr[0])/sm[0],3),'lag-1 (10 steps)',round((sm[1]-cr[1])/sm[1],3))
for lag in (60,600,3000):
    sm,cr=M.repeat_autocov(Y[:,::lag//3],4); print(f'share at lag {lag} steps',round((sm[3]-cr[3])/sm[3],3))
# internal share by position within the clip: does the carried-over state fade?
D=Y-Y.mean(0); share_t=(D**2).mean((0,2))/Y.var((0,2)).clip(1e-12)
print('internal share in trial 1, 2, 5, 20, 100 of the clip',[round(float(share_t[(i-1)*60:i*60].mean()),3) for i in (1,2,5,20,100)])
