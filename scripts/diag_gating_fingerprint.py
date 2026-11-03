"""Fingerprint of silent-at-rest links in the atlas (exploratory, 3 Nov 2026).

If some links carry signal only when the sending neuron is driven past a threshold, then across
trials of the same stimulation, downstream responses should rise more steeply than in
proportion to how hard the stimulated neuron was driven (convex), switching on in the
strongest trials. With always-on links they rise in proportion.

For every stimulation in the wild-type atlas: the stimulated neuron's evoked amplitude A (mean
over 0-30 s after onset minus the 10 s before, in units of its pre-stimulus SD) and every other
neuron's response in the same units. Per (stimulated class, responding class) pair with at
least 9 trials and a clear mean response (|t| > 3), each trial's response is signed by the
pair's mean response and divided by the pair's mean |response|. Trials are split into thirds
of A within the stimulated class. Reported: mean normalised response per third, beside mean A
per third; proportional rise gives response ratios equal to A ratios, a threshold gives a
response concentrated in the top third.
"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402


def trials(recs, pre=20, post=60):
    out = defaultdict(list)          # (stim class, resp class) -> list of (A, R)
    for r in recs:
        T = r.x.shape[1]
        for k, f in r.stims:
            c = r.classes[k]
            if not c or f - pre < 0 or f + post > T:
                continue
            base = r.x[:, f - pre:f]
            sd = np.nanstd(base, axis=1)
            resp = (np.nanmean(r.x[:, f:f + post], axis=1) - np.nanmean(base, axis=1)) / np.where(sd > 0, sd, np.nan)
            A = resp[k]
            if not np.isfinite(A):
                continue
            for j, cj in enumerate(r.classes):
                if cj and j != k and np.isfinite(resp[j]):
                    out[(c, cj)].append((A, resp[j]))
    return out


def fingerprint(out, min_trials=9, tmin=3.0):
    rows = []
    by_stim = defaultdict(list)
    for (c, cj), v in out.items():
        v = np.array(v)
        if len(v) < min_trials:
            continue
        m, s = v[:, 1].mean(), v[:, 1].std(ddof=1) / np.sqrt(len(v))
        if s == 0 or abs(m / s) < tmin:
            continue
        by_stim[c].append(v[:, 0])
        rows.append((c, v[:, 0], v[:, 1] * np.sign(m) / np.mean(np.abs(v[:, 1]))))
    Rt, At = [[], [], []], [[], [], []]
    for c, A, R in rows:
        q = np.quantile(np.concatenate(by_stim[c]), [1 / 3, 2 / 3])
        b = np.digitize(A, q)
        for t in range(3):
            if (b == t).any():
                Rt[t].append(R[b == t].mean())
                At[t].append(A[b == t].mean())
    return len(rows), [np.mean(x) for x in At], [np.mean(x) for x in Rt], [np.std(x) / np.sqrt(len(x)) for x in Rt]


if __name__ == "__main__":
    recs = load_pumpprobe_dir(sys.argv[1] if len(sys.argv) > 1 else "data/raw/randi2023_wt_npz")
    n, A, R, se = fingerprint(trials(recs))
    print(f"pairs {n}")
    print("third of stimulated-neuron drive:  low / mid / high")
    print("  mean drive A        " + " / ".join(f"{a:.2f}" for a in A))
    print("  mean response       " + " / ".join(f"{r:.2f} (se {e:.2f})" for r, e in zip(R, se)))
    print("  response / drive    " + " / ".join(f"{r / a:.2f}" for r, a in zip(R, A)))
