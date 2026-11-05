"""Follow-up to the pre-registered silent-links test (exploratory, 5 Nov 2026; written after T2
was found uninformative on lab brains and after the worm T2 output already existed, but before
this follow-up was run on worms). Review: it has the same near-zero-denominator problem as T2
(W / P with P near zero for within-range pokes), so its worm number is uninformative.

Why T2 failed: its statistic divides by the summed drive of within-range pokes, which is close
to zero, so the gain swings wildly. This follow-up asks a question that does not divide by
drive: does a watching copy predict WHICH neurons respond equally well for weak pokes (targets
kept within their resting range) and strong ones (pushed beyond it)?

If links are silent at rest and open only beyond the resting range (H), ongoing activity shows
the always-on links, which carry the response to within-range pokes, but not the silent ones,
which add to the response to beyond-range pokes: watching should predict within-range response
patterns relatively better than beyond-range ones. With ordinary links (or poke pathways that
do not depend on the target's activity level) there is no such asymmetry by construction.

Per category (within, beyond; the T1 definitions of run_silent_links_test.py), for each of 3
pools (every third worm by file order held out):
  P = Pearson correlation, over (stimulated class, responding class) pairs present in both,
      between the training worms' mean response and the held-out pool's mean response
      (the poke reference; it also absorbs how noisy each category is)
  W = the same correlation for the watching copy's prediction (ridge VAR(1) on class activity
      in unpoked frames of the training worms, unrecorded classes zero-filled, the stimulated
      class held at +1 for 15 s; as in scripts/check_headline_independent.py)
  share = W / P;  asymmetry = share(within) - share(beyond)
H predicts asymmetry > 0. Check on lab brains (seeds 0 and 1, a = 0.02, exactly as in the
pre-registered lab check): the follow-up is usable only if the silent-link brain's asymmetry
exceeds the baseline brain's in at least 5 of 6 (seed, pool) comparisons. Decision on worms,
fixed here before running them: support for H if the worm asymmetry is positive in all 3 pools
and its mean over pools exceeds the mean of the two baseline brains' means; against H if it is
at or below the baseline mean in all 3 pools; otherwise inconclusive.

Usage: python scripts/run_silent_links_followup.py lab | worms
Outputs: docs/figures/silent_links_followup_{lab,worms}.txt
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_silent_links_test as S  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402

POST = 30


def worm_summary(r):
    tr = S.worm_trials(r)
    if not tr:
        return None
    cat = {"within": defaultdict(list), "beyond": defaultdict(list)}
    for t in tr:
        c = "beyond" if t["E"] > t["p99"] else ("within" if t["E"] <= t["p95"] else None)
        if c is None:
            continue
        for ci, v in t["R"].items():
            cat[c][(t["cj"], ci)].append(v)
    m = S.unpoked_mask(r)
    X = r.x
    zx = (X - np.nanmean(X, axis=1, keepdims=True)) / np.nanstd(X, axis=1, keepdims=True)
    act = defaultdict(list)
    for j, c in enumerate(r.classes):
        if c:
            act[c].append(zx[j])
    act = {c: np.nanmean(v, axis=0) for c, v in act.items()}
    return {"cat": cat, "act": act, "unpoked": m}


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
        XtX += Z[:-1][ok].T @ Z[:-1][ok]
        XtY += Z[:-1][ok].T @ (Z[1:][ok] * seen)
    A = np.linalg.solve(XtX + ridge * np.eye(len(C)), XtY).T
    rad = np.abs(np.linalg.eigvals(A)).max()
    if rad >= 0.99:
        A *= 0.99 / rad
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


def mean_resp(worms, c):
    acc = defaultdict(list)
    for w in worms:
        for p, v in w["cat"][c].items():
            acc[p].extend(v)
    return {p: float(np.mean(v)) for p, v in acc.items()}


def corr(a, b):
    k = [p for p in a if p in b]
    if len(k) < 30:
        return np.nan
    u, v = np.array([a[p] for p in k]), np.array([b[p] for p in k])
    return float(np.corrcoef(u, v)[0, 1])


def analyse(recs):
    worms = [w for w in (worm_summary(r) for r in sorted(recs, key=lambda r: r.uid)) if w]
    rows = []
    for fold in range(3):
        pool = [w for i, w in enumerate(worms) if i % 3 == fold]
        train = [w for i, w in enumerate(worms) if i % 3 != fold]
        wp = fit_watching(train)
        row = {"pool": fold}
        for c in ("within", "beyond"):
            held, tm = mean_resp(pool, c), mean_resp(train, c)
            P, W = corr(tm, held), corr(wp, held)
            row.update({f"P_{c}": P, f"W_{c}": W, f"share_{c}": W / P})
        row["asym"] = row["share_within"] - row["share_beyond"]
        rows.append(row)
    return rows


def fmt(name, rows):
    out = []
    for r in rows:
        out.append(f"{name} pool {r['pool']}: within P {r['P_within']:.3f} W {r['W_within']:.3f} share {r['share_within']:.2f} | "
                   f"beyond P {r['P_beyond']:.3f} W {r['W_beyond']:.3f} share {r['share_beyond']:.2f} | asymmetry {r['asym']:+.2f}")
    out.append(f"{name}: mean asymmetry {np.mean([r['asym'] for r in rows]):+.3f}")
    return out


def main():
    cmd = sys.argv[1]
    if cmd == "lab":
        lines, A = [], {}
        for seed in (0, 1):
            for gated in (False, True):
                nm = f"{'silent links' if gated else 'baseline'} seed {seed}"
                rows = analyse(S.lab_recs(gated, seed, 0.02))
                A[(seed, gated)] = [r["asym"] for r in rows]
                lines += fmt(nm, rows)
                print("\n".join(lines[-4:]), flush=True)
        wins = sum(g > b for s in (0, 1) for g, b in zip(A[(s, True)], A[(s, False)]))
        base = float(np.mean([np.mean(A[(s, False)]) for s in (0, 1)]))
        usable = wins >= 5
        lines.append(f"silent-link asymmetry above baseline in {wins} of 6; usable: {usable}; baseline mean asymmetry {base:+.3f}")
        print(lines[-1])
        (S.FIG / "silent_links_followup_lab.txt").write_text("\n".join(lines) + "\n")
        json.dump({"usable": usable, "baseline": base}, open(S.FIG / "silent_links_followup_lab.json", "w"))
    else:
        lab = json.load(open(S.FIG / "silent_links_followup_lab.json"))
        rows = analyse(load_pumpprobe_dir(str(S.ROOT / "data" / "raw" / "randi2023_wt_npz")))
        lines = fmt("worms", rows)
        a = [r["asym"] for r in rows]
        if not lab["usable"]:
            v = "follow-up not usable on lab brains: uninformative"
        elif all(x > 0 for x in a) and np.mean(a) > lab["baseline"]:
            v = "supports H"
        elif all(x <= lab["baseline"] for x in a):
            v = "against H"
        else:
            v = "inconclusive"
        lines.append(f"lab usable {lab['usable']}, baseline mean asymmetry {lab['baseline']:+.3f}; verdict: {v}")
        print("\n".join(lines))
        (S.FIG / "silent_links_followup_worms.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
