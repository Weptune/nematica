import sys, resource, numpy as np
sys.path.insert(0, "/home/claude/nematica")
from nematica.slow import inputs as I
def anon():
    return [l.strip() for l in open("/proc/self/status") if l.startswith(("RssAnon","VmHWM"))]
rng = np.random.default_rng(0)
A, st, meta = I.lm_repeats("EleutherAI/pythia-1b", rng.integers(0, 50000, 400), [rng.integers(0, 50000, 256) for _ in range(3)])
print(A.shape, meta, anon(), "maxrss GB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6)
