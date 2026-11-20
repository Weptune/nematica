"""Study P (docs/OPTO_SECOND.md): does a copy taught by light pulses answer like a second mouse?

One code path for real mice and for synthetic mice recorded through real instruments. A mouse's answer to the
slow drive is its class profile (Study O and V's measure). Three things are compared with it on the classes
two mice share: another mouse's profile (the yardstick), the pulse-taught copy P's prediction, and the
watching copy W's prediction. Agreement is the correlation across classes (core.agree)."""
from __future__ import annotations

import numpy as np
from scipy.stats import wilcoxon

from . import core, real

MIN_SHARED = 8      # classes two mice must share for the pair to count
MIN_PARTNERS = 5    # pairs a mouse needs to enter
MARGIN = 0.75       # "like a second mouse": at least three quarters of a second mouse's agreement
ALPHA = 0.05        # the sign tests and the margin test against a second mouse (size checked in calibration)
ALPHA_WORSE = 0.01  # "worse than a second mouse": at 0.05 a literal second mouse was called worse in up to 14.5% of draws
ALPHA_AVERAGE = 0.01  # the margin test against the average of the other mice: at 0.05 it fired in up to 13% on the margin


def answers(rec, drop_silent=True):
    """As real.analyse, but returning the profile and the two copies' predictions themselves (same units).
    drop_silent: units with no spread in their 1 s spontaneous counts cannot be put in SD units; the earlier
    pipeline floored their SD at 1e-9, which lets one such unit swamp its class's mean rate (found by the
    review before the freeze). They are left out here. Returns None if fewer than 3 driven units remain or a
    class is left empty."""
    if drop_silent:
        live = real.spont_sd(rec["spont"]) > 0
        if not live.all():
            rec = {**rec, "spont": [x[:, live] for x in rec["spont"]], "block": rec["block"][:, live], "cls": rec["cls"][live]}
            if (rec["cls"] == -1).sum() < 3 or any((rec["cls"] == k).sum() == 0 for k in range(rec["n_classes"])):
                return None
    cls, n = rec["cls"], rec["n_classes"]
    sd = np.maximum(real.spont_sd(rec["spont"]), 1e-9)
    resp = real.unit_responses(rec["block"], rec["on_test"], sd)
    keep = cls >= 0
    classes = np.arange(n)
    prof = core.profile(resp[:, keep], cls[keep], classes)
    c = core.agree(core.profile(resp[0::2][:, keep], cls[keep], classes), core.profile(resp[1::2][:, keep], cls[keep], classes))
    spont = [x / sd for x in rec["spont"]]
    block = rec["block"] / sd
    W = real.fit_watch(spont, cls, n)
    scale = W[2][1:] * core.TEST_BINS
    te = real.courses(block, cls, n, rec["on_test"], W[2])
    trs = [real.courses(block, cls, n, rec["on_train"], W[2])]
    if len(rec["on_train2"]):
        trs.append(real.courses(block, cls, n, rec["on_train2"], W[2]))
    H = real.fit_poke2(trs)
    return {"prof": prof, "c": c, "pw": core.predict_watch(W, te[:, 0], 0)[1:] * scale, "pp": core.predict_poke(H, te[:, 0]) * scale,
            "H": H * scale, "tag": te[:, 0]}


def _from_others(M, m):
    """A copy that never saw this mouse's stimulation: for each class, the median over the other mice of the
    line of their pulse-taught kernel, driven by this mouse's driven-class course."""
    a = M[m]
    T, L = len(a["tag"]), a["H"].shape[0]
    D = np.zeros((T, L))
    for j in range(L):
        D[j:, j] = a["tag"][:T - j]
    out = np.full(len(a["names"]), np.nan)
    for i, k in enumerate(a["names"]):
        hs = [b["H"][:, b["names"].index(k)] for o, b in M.items() if o != m and b["line"] == a["line"] and k in b["names"]]
        if len(hs) >= 3:
            out[i] = (D @ np.median(hs, 0)).mean()
    return out


def consensus(M, m):
    """What the other mice of the line did, class by class: the median of their profiles (at least 3 mice)."""
    a = M[m]
    out = np.full(len(a["names"]), np.nan)
    for i, k in enumerate(a["names"]):
        v = [b["prof"][b["names"].index(k)] for o, b in M.items() if o != m and b["line"] == a["line"] and k in b["names"]]
        if len(v) >= 3:
            out[i] = np.median(v)
    return out


def pairwise(M, rng=None):
    """Per mouse: B, the median agreement of its profile with another mouse's; P, W and X, the median agreement
    of each copy's prediction with its profile on the same shared classes; N, the agreement with one other
    mouse drawn at random and held out of B (a literal second mouse, scored as if it were a copy)."""
    rng = rng or np.random.default_rng(0)
    out = {}
    for m, a in M.items():
        ia = {k: i for i, k in enumerate(a["names"])}
        px = _from_others(M, m)
        rows = []
        for o, b in M.items():
            if o == m or b["line"] != a["line"]:
                continue
            S = [k for k in b["names"] if k in ia]
            if len(S) < MIN_SHARED:
                continue
            i = [ia[k] for k in S]; j = [b["names"].index(k) for k in S]
            rows.append([core.agree(a["prof"][i], b["prof"][j]), core.agree(a["pp"][i], a["prof"][i]),
                         core.agree(a["pw"][i], a["prof"][i]), core.agree(px[i], a["prof"][i])])
        rows = np.array([r for r in rows if np.isfinite(r[0])])
        if len(rows) < MIN_PARTNERS:
            continue
        cons = consensus(M, m); ok = np.isfinite(cons)
        A, PA = (core.agree(cons[ok], a["prof"][ok]), core.agree(a["pp"][ok], a["prof"][ok])) if ok.sum() >= MIN_SHARED else (np.nan, np.nan)
        up = lambda x: float(np.mean(x[np.isfinite(x)] > 0)) if np.isfinite(x).any() else np.nan  # noqa: E731
        h = int(rng.integers(len(rows)))
        rest = np.delete(rows, h, 0)
        out[m] = {"line": a["line"], "partners": len(rows), "B": float(np.median(rows[:, 0])), "P": float(np.nanmedian(rows[:, 1])),
                  "W": float(np.nanmedian(rows[:, 2])), "X": float(np.nanmedian(rows[:, 3])) if np.isfinite(rows[:, 3]).any() else np.nan,
                  "N": float(rows[h, 0]), "B_rest": float(np.median(rest[:, 0])), "A": A, "PA": PA,
                  "real_up": up(a["prof"]), "p_up": up(a["pp"]), "w_up": up(a["pw"]), "x_up": up(px), "c": a["c"]}
    return out


def _sign_p(x):
    from math import comb
    x = [v for v in x if np.isfinite(v) and v != 0]
    n, k = len(x), sum(v > 0 for v in x)
    return sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n if n else np.nan


def _w(x, alt):
    x = np.asarray([v for v in x if np.isfinite(v)])
    return float(wilcoxon(x, alternative=alt).pvalue) if len(x) >= 8 and np.any(x != 0) else np.nan


def claims(S, line):
    """The registered tests on one line's mice. Each is one-sided at p < 0.05."""
    v = [x for x in S.values() if x["line"] == line]
    if len(v) < 8:
        return {"n": len(v), "undecided": True}
    B = np.array([x["B"] for x in v])
    o = {"n": len(v), "median": {k: float(np.nanmedian([x[k] for x in v])) for k in ("B", "P", "W", "X", "N", "A", "PA", "c", "real_up", "p_up", "w_up", "x_up")}}
    o["mice_agree"] = _sign_p(B)
    way = np.sign(0.5 - np.median([y["real_up"] for y in v]))            # which way most regions really went
    for key, up in (("P", "p_up"), ("W", "w_up"), ("X", "x_up")):
        s = np.array([x[key] for x in v])
        o[key + "_direction"] = _sign_p([(0.5 - x[up]) * way for x in v])
        o[key + "_direction_wrong"] = _sign_p([(x[up] - 0.5) * way for x in v])
        o[key + "_like"] = _w(s - MARGIN * B, "greater")
        o[key + "_worse"] = _w(s - B, "less")
    A, PA = np.array([x["A"] for x in v]), np.array([x["PA"] for x in v])                # the stricter bar: the average of the other mice
    o["P_like_average"] = _w(PA - MARGIN * A, "greater")
    o["P_worse_average"] = _w(PA - A, "less")
    n, br = np.array([x["N"] for x in v]), np.array([x["B_rest"] for x in v])
    o["null_like"] = _w(n - MARGIN * br, "greater")
    o["null_worse"] = _w(n - br, "less")
    return o


def verdict(o, key="P"):
    """For one copy (P pulse-taught, W watching, X taught by other mice's pulses).
    like a second mouse: the mice agree with each other, the copy gets the direction right, and its pattern is
      within a quarter of a second mouse's.
    not like one: the mice agree, and the copy gets the direction wrong or its pattern is worse than a second
      mouse's (the direction counts as wrong when the opposite direction is significant).
    Otherwise undecided."""
    if o.get("undecided") or not o["mice_agree"] < ALPHA:
        return "undecided"
    if o[key + "_like"] < ALPHA and o[key + "_direction"] < ALPHA:
        return "like a second mouse"
    if o[key + "_worse"] < ALPHA_WORSE or o[key + "_direction_wrong"] < ALPHA:
        return "not like a second mouse"
    return "undecided"


def beats_average(o):
    """The stricter bar, for P only: within a quarter of what the average of the other mice achieves."""
    return bool(not o.get("undecided") and o["mice_agree"] < ALPHA and o["P_like_average"] < ALPHA_AVERAGE)
