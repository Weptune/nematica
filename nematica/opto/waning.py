"""Study W (docs/OPTO_WANING.md): asked again and again, does a mouse neuron's answer to light fade?

The worm atlas shows a neuron answering a second poke, 0.6 to 2 minutes later, at about half its first
answer. Here the same question is put to the light-driven cells of mouse cortex (Allen Visual Behavior
Neuropixels, the Study V mice), where each cell is driven about 300 times, 2 s apart, over 10 minutes.
For each mouse: the driven units' summed answer in the last third of the trials over the first third."""
from __future__ import annotations

import numpy as np

from . import real


def _thirds(order, level):
    """Indices of the first and last third of the trials, taken within each light level so both ends hold
    the same mix of levels."""
    early, late = [], []
    for v in np.unique(level):
        ix = order[level[order] == v]
        k = len(ix) // 3
        early.extend(ix[:k]); late.extend(ix[len(ix) - k:])
    return np.array(early, int), np.array(late, int)


def pulse_answers(d, tagged):
    """Driven units x trials: extra spikes 2 to 9 ms after a 10 ms pulse, over the 7 ms before (the tagging
    window), on the even-numbered pulses only: the tagging rule chose units on the odd-numbered ones."""
    tr = real.square_pulses(d)
    tr = tr[np.isclose(d["opto_duration"][tr], 0.01)]
    tr = tr[np.argsort(d["opto_start"][tr])][1::2]
    on = d["opto_start"][tr]
    out = np.zeros((int(tagged.sum()), len(on)))
    for a, i in enumerate(np.flatnonzero(tagged)):
        s = d["trains"][i]
        out[a] = (np.searchsorted(s, on + 0.009) - np.searchsorted(s, on + 0.002)) - (np.searchsorted(s, on) - np.searchsorted(s, on - 0.007))
    return out, d["opto_level"][tr]


def slow_answers(d, tagged):
    """Driven units x trials: spikes in the 1 s of the half-cosine minus the rate in the 0.24 s before it."""
    tr = real.half_cosine(d)
    tr = tr[np.argsort(d["opto_start"][tr])]
    on = d["opto_start"][tr]
    out = np.zeros((int(tagged.sum()), len(on)))
    for a, i in enumerate(np.flatnonzero(tagged)):
        s = d["trains"][i]
        out[a] = (np.searchsorted(s, on + 1.0) - np.searchsorted(s, on)) - (np.searchsorted(s, on) - np.searchsorted(s, on - 0.24)) / 0.24
    return out, d["opto_level"][tr]


def fade(resp, level):
    """Late over early: the driven units' summed answer in the last third of trials over the first third."""
    early, late = _thirds(np.arange(resp.shape[1]), level)
    e, l = resp[:, early].sum(), resp[:, late].sum()
    return {"early": float(e / max(len(early), 1)), "late": float(l / max(len(late), 1)), "ratio": float(l / e) if e > 0 else float("nan")}


def sign_p(x):
    """One-sided sign test that the values lie above 0; ties dropped."""
    from math import comb
    x = [v for v in x if np.isfinite(v) and v != 0]
    n, k = len(x), sum(v > 0 for v in x)
    return sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n if n else float("nan")


# ------------------------------------------------------------------ the split: driven cells against their neighbours
def thirds3(level):
    """Early, middle and late third of time-ordered trials, within each light level."""
    order = np.arange(len(level))
    early, late = _thirds(order, level)
    mid = np.setdiff1d(order, np.r_[early, late])
    return early, mid, late


def live(rec):
    """Study P's rule: drop units with no spread in their 1 s spontaneous counts (they cannot be put in SD
    units). None if a class is left empty or no driven unit remains."""
    ok = real.spont_sd(rec["spont"]) > 0
    if not ok.all():
        rec = {**rec, "spont": [x[:, ok] for x in rec["spont"]], "block": rec["block"][:, ok], "cls": rec["cls"][ok]}
    if (rec["cls"] == -1).sum() < 1 or any((rec["cls"] == k).sum() == 0 for k in range(rec["n_classes"])):
        return None
    return rec


def split(block, onsets, level, cls, n, sd):
    """onsets: bin indices of the 1 s half-cosine trials in time order; level: their light levels.
    Driven units: summed spikes in the 1 s minus the 0.24 s baseline rate, late third over early third.
    Neighbours: the class profile of the early and of the late third, each projected on the profile of the
    middle third, which neither of them shares; late over early. Two versions of the profile (review, item 1):
      net       Study V's: per class, the median over its units of the mean response in spontaneous SD units.
                A steady fractional push on a resting rate that drifts down reads here as a fade.
      net_frac  per class, the summed change as a fraction of the class's own summed rate just before the
                trials of that third. A steady push of a fixed number of spikes on a drifting rate reads here
                as a change.
    `beyond` and `beyond_frac` are the neighbours' ratios over the driven ratio: below 1 when the neighbours'
    answer fades faster than the recorded driven units' own. A late answer that has reversed gives a ratio at
    or below 0, which counts as below 1. `rest` is the neighbours' summed rate before the trials, late third
    over early third."""
    from . import core
    early, mid, late = thirds3(level)
    resp = real.unit_responses(block, onsets, sd)                      # trials x units, SD units
    drv = block[:, cls == -1]
    own = np.array([drv[o:o + core.TEST_BINS].sum() - drv[o - real.BASE_BINS:o].sum() / real.BASE_BINS * core.TEST_BINS for o in onsets])
    keep, classes = cls >= 0, np.arange(n)
    prof = lambda ix: core.profile(resp[ix][:, keep], cls[keep], classes)   # noqa: E731
    one = (cls[:, None] == classes[None, :]).astype(float)                                                   # units x classes
    post = np.array([block[o:o + core.TEST_BINS].sum(0) for o in onsets]) @ one                              # trials x classes
    pre = np.array([block[o - real.BASE_BINS:o].sum(0) for o in onsets]) @ one / real.BASE_BINS * core.TEST_BINS

    def frac(ix):
        b = pre[ix].sum(0)
        return np.where(b > 0, (post[ix].sum(0) - b) / np.where(b > 0, b, 1), np.nan)

    def ratio(T, E, L):
        ok = np.isfinite(T) & np.isfinite(E) & np.isfinite(L)
        tt = float(T[ok] @ T[ok]) if ok.sum() >= 4 else 0.0
        if tt <= 0:
            return np.nan, np.nan, np.nan
        ne, nl = float(E[ok] @ T[ok]) / tt, float(L[ok] @ T[ok]) / tt
        return ne, nl, (nl / ne if ne > 0 else np.nan)

    ne, nl, net = ratio(prof(mid), prof(early), prof(late))
    fe, fl, netf = ratio(frac(mid), frac(early), frac(late))
    de, dl = float(own[early].mean()), float(own[late].mean())
    driven = dl / de if de > 0 else np.nan
    over = lambda r: r / driven if np.isfinite(r) and np.isfinite(driven) and driven > 0 else np.nan   # noqa: E731
    return {"driven_early": de, "driven_late": dl, "driven": driven, "net_early": ne, "net_late": nl, "net": net,
            "frac_early": fe, "frac_late": fl, "net_frac": netf, "beyond": over(net), "beyond_frac": over(netf),
            "rest": float(pre[late].sum() / pre[early].sum()) if pre[early].sum() > 0 else np.nan,
            "half": core.agree(prof(np.arange(len(onsets))[0::2]), prof(np.arange(len(onsets))[1::2]))}


def split_mouse(d):
    """The split for one real mouse: Study V's tagging, classes and recording, silent units dropped."""
    t = real.tag(d)
    cls, names = real.classes(d, t)
    rec = live(real.recording(d, cls, len(names)))
    if rec is None:
        return None
    hc = real.half_cosine(d)
    o = np.argsort(d["opto_start"][hc])
    return split(rec["block"], rec["on_test"][o], d["opto_level"][hc][o], rec["cls"], rec["n_classes"], real.spont_sd(rec["spont"]))


def boot(x, f=np.median, n=4000, seed=0):
    """95% interval of f over mice, by resampling mice."""
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    if len(x) < 3:
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    b = [f(x[rng.integers(0, len(x), len(x))]) for _ in range(n)]
    return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]


# ------------------------------------------------------------------ reported without a claim
def first_pulses(resp, level):
    """The thirds are blind to a drop that is over within a few trials. The driven units' summed answer on
    the first two even-numbered pulses, and what the next thirteen (pulses 6 to 30 of the 150) say to expect
    at the same light levels (review, item 4: the first pulses do not hold the same mix of levels as the
    rest). Returns (seen, expected), summed over the first two pulses that have a same-level pulse among the
    thirteen. The very first answer to light is not here: the first pulse of the block is odd-numbered and
    spent on choosing the units, and 1 to 9 other light trials come before the first even-numbered one."""
    per = resp.sum(0)
    seen = exp = 0.0
    for k in (0, 1):
        same = per[2:15][level[2:15] == level[k]]
        if len(same):
            seen += float(per[k]); exp += float(same.mean())
    return seen, exp


def by_level(resp, level):
    """Saturation check, no trial order involved: the driven units' summed answer per trial at the lowest
    light level over that at the highest. Near 1 means the recorded driven units are at their ceiling, where
    a weakening of the light's effect would not show in their spikes."""
    lv = np.unique(level)
    lo, hi = resp[:, level == lv[0]].sum() / (level == lv[0]).sum(), resp[:, level == lv[-1]].sum() / (level == lv[-1]).sum()
    return {"answer": float(lo / hi) if hi > 0 else float("nan"), "light": float(lv[0] / lv[-1])}


def resting(d, tagged):
    """Driven units' summed rate in the 0.24 s before each trial of the block, late third over early third
    of all 300 trials: a drift in the animal's state or in the recording would show here. Not free of light:
    the window starts 0.44 s or more after the light before it."""
    on = np.sort(d["opto_start"])
    k = len(on) // 3
    tot = np.zeros(len(on))
    for i in np.flatnonzero(tagged):
        s = d["trains"][i]
        tot += np.searchsorted(s, on) - np.searchsorted(s, on - 0.24)
    return float(tot[-k:].mean() / tot[:k].mean()) if tot[:k].mean() > 0 else float("nan")
