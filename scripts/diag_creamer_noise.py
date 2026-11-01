import warnings, copy
warnings.filterwarnings("ignore")
import numpy as np
exec(open("scripts/diag_creamer_reliability.py").read().split("real = [")[0])
real = [response_set(r) for r in pool]
def agree(A, B):
    v = [1 - c_pattern(a, b) for i, a in enumerate(A) for j, b in enumerate(B) if i != j]
    v = [x for x in v if np.isfinite(x)]
    return np.median(v)
for f in (1.0, 0.5, 0.3, 0.2, 0.1):
    mm = copy.copy(m); mm.Lq = f * m.Lq; mm.sr = f * m.sr
    sims = [response_set(mm.simulate(r, np.random.default_rng(i))) for i, r in enumerate(pool)]
    print(f"noise x{f:<4}  model vs real {agree(sims, real):.3f}   model vs model {agree(sims, sims):.3f}   (real vs real {agree(real, real):.3f})", flush=True)
