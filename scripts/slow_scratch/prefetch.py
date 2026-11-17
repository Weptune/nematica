"""Download and cache the 58 sessions' movie-repeat spikes, unit metadata and behaviour. No statistics are
computed or printed (the review of the frozen registration gates the first measurement)."""
import sys; sys.path.insert(0,'/home/claude/nematica')
from nematica.slow import data as D
for ds,a in D.sessions():
    uid=a["path"].split("/")[0]
    try:
        z=D.movie_cache(a); D.unit_meta(a,z["units"]); import numpy as np; nb=int(np.floor(np.min(z["stops"]-z["starts"])/D.BIN_S+1e-9)); D.behaviour(a,z["starts"],z["stops"],nb)
        if ds=="000022": D.movie_cache(a,shuffled=True)
        print(uid,"cached",flush=True)
    except Exception as e:
        print(uid,"ERROR",type(e).__name__,e,flush=True)
