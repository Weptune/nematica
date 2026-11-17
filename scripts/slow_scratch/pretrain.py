import sys, time; sys.path.insert(0,'/home/claude/nematica')
from pathlib import Path
from nematica.slow import inputs as I
NETS=Path('/home/claude/nematica/data/derived/slow_nets')
for kind in ("gru","cfc"):
    for seed in (1,2):
        f=NETS/f"{kind}_seed{seed}.pt"
        if f.exists(): continue
        t=time.time(); m,_,_=I.trained_char_net(kind,seed=seed); I.save_char_net(m,f,kind); print(kind,seed,'trained',round(time.time()-t),'s',flush=True)
for seed in (1,2):
    f=NETS/f"a2_seed{seed}.pt"
    if f.exists(): continue
    t=time.time(); net,acc=I.trained_task_rnn(seed=seed); print('a2',seed,'accuracy',round(acc,3),round(time.time()-t),'s',flush=True)
    if acc>=0.7: I.save_task_rnn(net,f)
