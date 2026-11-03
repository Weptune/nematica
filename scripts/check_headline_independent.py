"""Independent recomputation of the headline worm result (3 Nov 2026).

Uses only numpy and the raw atlas files (data/raw/randi2023_wt_npz/*.npz: x frames x neurons,
ids, stim_cell, stim_frame, t). None of NEMATICA's loader, ruler, copies or splits are used, and
every analysis choice below was made independently and kept simple, so the numbers are not
expected to equal the pipeline's; the question is whether the ORDER holds:
    watching copy  <<  poke average  ~  worm-to-worm agreement

Definitions:
  class        neuron name with a trailing L/R removed (left and right averaged)
  response     for each stimulation: mean over 0-15 s after onset minus mean over the 10 s
               before, in units of that neuron's SD over unpoked frames; averaged over trials
               and over neurons of a class, per worm and (stimulated class, responding class)
  agreement    Pearson correlation of two response vectors over shared pairs (at least 30)
  split        worms sorted by file name, every third worm held out (3 pools)
  worm-to-worm median agreement between held-out worms
  poke average each held-out worm against the mean response of the training worms
  watching     a ridge VAR(1) on class activity in unpoked frames of the training worms
               (frames more than 30 s after any stimulation), classes a worm did not record
               set to zero (the zero-filling used by NEMATICA's watching copy); poked by holding
               the stimulated class at +1 for 15 s; prediction = mean of each other class
Usage: python scripts/check_headline_independent.py [atlas folder]
"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

DT = 0.5
POST, PRE, GAP = int(15 / DT), int(10 / DT), int(30 / DT)


def cls(name):
    name = str(name)
    if not name:
        return None
    return name[:-1] if len(name) > 2 and name[-1] in "LR" else name


def load(path):
    z = np.load(path, allow_pickle=False)
    x, ids = z["x"].astype(float), z["ids"]
    T, N = x.shape
    unpoked = np.ones(T, bool)
    for f in z["stim_frame"]:
        unpoked[max(f, 0):f + GAP] = False
    sd = np.nanstd(np.where(unpoked[:, None], x, np.nan), axis=0)
    sd[~(sd > 0)] = np.nan
    classes = [cls(i) for i in ids]
    resp = defaultdict(list)
    for k, f in zip(z["stim_cell"], z["stim_frame"]):
        if k < 0 or k >= N or classes[k] is None or f - PRE < 0 or f + POST > T:
            continue
        r = (np.nanmean(x[f:f + POST], axis=0) - np.nanmean(x[f - PRE:f], axis=0)) / sd
        for j in range(N):
            if j != k and classes[j] is not None and np.isfinite(r[j]):
                resp[(classes[k], classes[j])].append(r[j])
    R = {p: float(np.mean(v)) for p, v in resp.items()}
    # class activity for watching: mean of z-scored neurons per class
    zx = (x - np.nanmean(x, axis=0)) / np.nanstd(x, axis=0)
    act = defaultdict(list)
    for j, c in enumerate(classes):
        if c is not None:
            act[c].append(zx[:, j])
    act = {c: np.nanmean(v, axis=0) for c, v in act.items()}
    return {"R": R, "act": act, "unpoked": unpoked}


def agree(a, b, min_pairs=30):
    keys = [k for k in a if k in b]
    if len(keys) < min_pairs:
        return np.nan
    u, v = np.array([a[k] for k in keys]), np.array([b[k] for k in keys])
    if u.std() == 0 or v.std() == 0:
        return np.nan
    return float(np.corrcoef(u, v)[0, 1])


def fit_watching(train, ridge=1.0):
    C = sorted({c for w in train for c in w["act"]})
    ix = {c: i for i, c in enumerate(C)}
    XtX, XtY = np.zeros((len(C), len(C))), np.zeros((len(C), len(C)))
    for w in train:
        T = len(w["unpoked"])
        Z = np.zeros((T, len(C)))
        seen = np.zeros(len(C), bool)
        for c, a in w["act"].items():
            Z[:, ix[c]] = np.nan_to_num(a)
            seen[ix[c]] = True
        ok = w["unpoked"][:-1] & w["unpoked"][1:]
        X, Y = Z[:-1][ok], Z[1:][ok]
        XtX += X.T @ X
        XtY += X.T @ (Y * seen)          # only recorded classes are targets
    A = np.linalg.solve(XtX + ridge * np.eye(len(C)), XtY).T
    r = np.abs(np.linalg.eigvals(A)).max()
    if r >= 0.99:
        A *= 0.99 / r
    pred = {}
    for i, ci in enumerate(C):
        z, acc = np.zeros(len(C)), np.zeros(len(C))
        for _ in range(POST):
            z = A @ z
            z[i] = 1.0
            acc += z
        for j, cj in enumerate(C):
            if j != i:
                pred[(ci, cj)] = acc[j] / POST
    return pred


def main():
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/randi2023_wt_npz")
    files = sorted(folder.glob("*.npz"))
    worms = [load(f) for f in files]
    print(f"{len(worms)} worms")
    for fold in range(3):
        pool = [w for i, w in enumerate(worms) if i % 3 == fold]
        train = [w for i, w in enumerate(worms) if i % 3 != fold]
        real = [agree(a["R"], b["R"]) for k, a in enumerate(pool) for b in pool[k + 1:]]
        mean = defaultdict(list)
        for w in train:
            for p, v in w["R"].items():
                mean[p].append(v)
        mean = {p: float(np.mean(v)) for p, v in mean.items()}
        poke = [agree(mean, w["R"]) for w in pool]
        watch_pred = fit_watching(train)
        watch = [agree(watch_pred, w["R"]) for w in pool]
        med = lambda v: float(np.nanmedian(v))  # noqa: E731
        print(f"pool {fold}: worm-to-worm {med(real):.3f}   poke average {med(poke):.3f}   "
              f"watching {med(watch):.3f}   (watching / worm-to-worm {med(watch) / med(real):.2f}, "
              f"poke / worm-to-worm {med(poke) / med(real):.2f})")


if __name__ == "__main__":
    main()
