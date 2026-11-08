"""Exploratory: what are the worm's slow brain-wide states? SlowLatent (6 factors, dynamics) fitted on
all wild-type atlas worms; for each factor, its timescale, share of slow variance, and the classes with
the largest loadings (sign included). Also: which classes lead and which follow in the slow band
(antisymmetric part of the lag-20 covariance, summed per class)."""
import sys, numpy as np
from collections import Counter
sys.path.insert(0, ".")
from nematica.data.pumpprobe import load_pumpprobe_dir
from nematica.systems.causal_models import SlowLatent, lagged_cov
recs = [r for r in load_pumpprobe_dir("data/raw/randi2023_wt_npz") if any(r.classes)]
cnt = Counter(c for r in recs for c in set(r.classes) if c)
classes = sorted(c for c, n in cnt.items() if n >= 0.3 * len(recs))
sm = SlowLatent(6).fit(recs, classes)          # factor AR(1) version: clean directions and timescales
V, c0, rho = sm.V, sm.c0, sm.rho
order = np.argsort(c0)[::-1]
tot = c0.sum()
lines = [f"{len(recs)} worms, {len(classes)} classes"]
for j in order:
    v = V[:, j] * np.sign(V[np.argmax(np.abs(V[:, j])), j])
    top = np.argsort(-np.abs(v))[:10]
    lines.append(f"factor: share {c0[j] / tot:.2f}, timescale {-0.5 / np.log(rho[j]):.0f} s: " +
                 ", ".join(f"{classes[i]} {v[i]:+.2f}" for i in top))
G = lagged_cov(recs, classes, 20, sym=False)     # G[i, j] = cov(x_i(t + 20), x_j(t))
A = np.nan_to_num(G - G.T)                        # > 0: j leads i
lead = A.sum(0) - A.sum(1)                        # positive: the class tends to lead
idx = np.argsort(lead)
lines.append("slow-band leaders (10 s ahead): " + ", ".join(f"{classes[i]} {lead[i]:+.2f}" for i in idx[::-1][:8]))
lines.append("slow-band followers: " + ", ".join(f"{classes[i]} {lead[i]:+.2f}" for i in idx[:8]))
open("docs/figures/slow_states.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
