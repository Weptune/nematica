"""Exploratory check: does the slow-band order seen in the atlas (sensory neurons lead, pharyngeal and
head neurons follow, about 10 s) also hold in Atanas worms, which are freely moving and never
optogenetically stimulated? Lag 17 frames (about 10 s at 0.6 s)."""
import sys, numpy as np
from collections import Counter
from scipy.stats import spearmanr
sys.path.insert(0, ".")
from nematica.data.pumpprobe import load_pumpprobe_dir
from nematica.data.atanas_pp import load_atanas_pp_dir
from nematica.systems.causal_models import lagged_cov
def lead_scores(recs, L):
    cnt = Counter(c for r in recs for c in set(r.classes) if c)
    classes = sorted(c for c, n in cnt.items() if n >= 0.3 * len(recs) and c != "MERGE")
    G = lagged_cov(recs, classes, L, sym=False, min_n=200)
    A = np.nan_to_num(G - G.T)
    return dict(zip(classes, A.sum(0) - A.sum(1)))
wt = lead_scores([r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz") if any(r.classes)], 20)
at = lead_scores(load_atanas_pp_dir("data/raw/atanas2023_wwweb"), 17)
common = sorted(set(wt) & set(at))
a = np.array([wt[c] for c in common]); b = np.array([at[c] for c in common])
r, p = spearmanr(a, b)
print(f"{len(common)} shared classes; Spearman r between atlas and Atanas lead scores = {r:.2f} (p = {p:.3f})")
for name, d in (("atlas", wt), ("Atanas", at)):
    s = sorted(common, key=lambda c: -d[c])
    print(f"{name} leaders: {', '.join(s[:8])}; followers: {', '.join(s[-8:])}")
rng = np.random.default_rng(0)
perm = [spearmanr(a, rng.permutation(b))[0] for _ in range(5000)]
print("permutation p (two-sided) = %.4f" % np.mean(np.abs(perm) >= abs(r)))
