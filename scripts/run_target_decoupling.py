"""Does a poke's downstream effect need the poked neuron's measured activity to change?
(Exploratory, 5 Nov 2026. Written after the silent-links test, whose follow-up diagnostics showed
that in worms, pokes that leave the target within its resting range still evoke the same
downstream pattern as strong pokes, and after a binned look at the curve below; so this is not
pre-registered, and the numbers it reports were partly seen before it was written.)

In a brain where everything runs through measured activity, as in every lab brain, a poke can
only affect other neurons through the poked neuron's own activity: trials in which the target's
activity does not change should evoke nothing. Watching copies learn exactly these routes, from
measured activity. If, in worms, pokes evoke downstream responses even when the target's measured
activity does not change, then part of what a poke does travels by a route that measured activity
does not show, which would explain why watching cannot find it.

Per trial (definitions of scripts/run_silent_links_test.py: frames 0-29 after onset against the
20 before, resting-SD units): D = the target's change; r = mean over responding classes of the
response, signed and scaled per (stimulated class, responding class) pair from the other half of
the worms (pairs with >= 6 trials and |t| > 3, chosen on all trials). D is measured with noise,
so a plain regression of r on D understates the slope and inflates the intercept. The noise SD
s is measured directly: D computed at sham times (random unpoked frames, random named neuron,
the same windows). Errors-in-variables correction (method of moments, classical noise):
lambda = 1 - s^2 / var(D), slope g = b / lambda, intercept c = mean(r) - g * mean(D).
Reported: c (the response at zero target change) and c / g (the target change that would be
needed to produce it through the target), with 95% intervals from 2000 bootstrap resamples of
worms (sham times resampled with their worm); also the mean r at sham times (should be near 0).
Lab brains (the pre-registered lab check's settings, seeds 0 and 1, with and without silent
links) are the reference where the answer is known: c should be near zero.
Also reported for trials whose target trace is complete (no missing frames in the window). Added
after a first run: part of the intercept could be a generic response to any stimulation that
happens to share the pairs' signs, so every trial is also scored with the pairs of every other
stimulated class (averaged over them; a first version used one random other class, whose result
varied from draw to draw), and the target-specific intercept is the difference.

Timing disclosed: run_silent_links_followup.py was saved after the pre-registered worm T2 output
existed. Independent review (5 Nov): see README, "Do worms have links that are silent at rest?".

Usage: python scripts/run_target_decoupling.py   ->  docs/figures/target_decoupling.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_silent_links_test as S  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402


def per_worm(recs, rng):
    """Per worm: arrays of (D, r, complete) for trials and (D_sham, r_sham) at sham times."""
    recs = sorted(recs, key=lambda r: r.uid)
    data = []
    for r in recs:
        tr = S.worm_trials(r)
        if tr:
            data.append((r, tr))
    halves = [data[0::2], data[1::2]]
    out = []
    for h in (0, 1):
        pairs = S.choose_pairs([(r.uid, tr) for r, tr in halves[h]])
        stimcls = sorted({p[0] for p in pairs})
        for r, tr in halves[1 - h]:
            m = S.unpoked_mask(r)
            X = r.x
            sd = np.nanstd(np.where(m, X, np.nan), axis=1)
            T = r.n_frames
            Dt, Rt, Ut, Ct = [], [], [], []
            for t in tr:
                v = [val * pairs[(t["cj"], ci)][0] / pairs[(t["cj"], ci)][1] for ci, val in t["R"].items() if (t["cj"], ci) in pairs]
                u = []
                for cs in stimcls:
                    if cs != t["cj"]:
                        w = [val * pairs[(cs, ci)][0] / pairs[(cs, ci)][1] for ci, val in t["R"].items() if (cs, ci) in pairs]
                        if w:
                            u.append(np.mean(w))
                if v and u:
                    Dt.append(t["D"])
                    Rt.append(np.mean(v))
                    Ut.append(np.mean(u))
                    Ct.append(t["complete"])
            # sham times: windows entirely in unpoked frames
            ok = [f for f in range(S.PRE, T - S.POST) if m[f - S.PRE:f + S.POST].all()]
            named = [k for k, c in enumerate(r.classes) if c and sd[k] > 0]
            Ds, Rs = [], []
            if ok and named:
                for f in rng.choice(ok, min(len(ok), 10), replace=False):
                    k = int(rng.choice(named))
                    chg = (np.nanmean(X[:, f:f + S.POST], axis=1) - np.nanmean(X[:, f - S.PRE:f], axis=1)) / np.where(sd > 0, sd, np.nan)
                    if not np.isfinite(chg[k]):
                        continue
                    cj = r.classes[k]
                    v = [chg[i] * pairs[(cj, r.classes[i])][0] / pairs[(cj, r.classes[i])][1]
                         for i in range(len(chg)) if i != k and r.classes[i] and (cj, r.classes[i]) in pairs and np.isfinite(chg[i])]
                    Ds.append(chg[k])
                    if v:
                        Rs.append(np.mean(v))
            out.append(dict(D=np.array(Dt), R=np.array(Rt), U=np.array(Ut), C=np.array(Ct, bool), Ds=np.array(Ds), Rs=np.array(Rs)))
    return out


def estimate(W, complete_only=False, key="R"):
    D = np.concatenate([w["D"][w["C"]] if complete_only else w["D"] for w in W])
    R = np.concatenate([w[key][w["C"]] if complete_only else w[key] for w in W])
    Ds = np.concatenate([w["Ds"] for w in W])
    Rs = np.concatenate([w["Rs"] for w in W])
    s2 = Ds.var()
    b = np.cov(D, R)[0, 1] / D.var()
    lam = 1 - s2 / D.var()
    g = b / lam
    c = R.mean() - g * D.mean()
    return c, g, c / g, Rs.mean() if len(Rs) else np.nan, np.sqrt(s2), lam, len(D)


def report(name, W, complete_only=False, B=2000, seed=0):
    est = estimate(W, complete_only)
    gen = estimate(W, complete_only, "U")
    rng = np.random.default_rng(seed)
    bs, bg = [], []
    for _ in range(B):
        sel = [W[i] for i in rng.integers(0, len(W), len(W))]
        bs.append(estimate(sel, complete_only))
        bg.append(estimate(sel, complete_only, "U"))
    bs, bg = np.array(bs), np.array(bg)
    lo, hi = np.nanpercentile(bs, [2.5, 97.5], axis=0)
    glo, ghi = np.nanpercentile(bg[:, 0], [2.5, 97.5])
    dlo, dhi = np.nanpercentile(bs[:, 0] - bg[:, 0], [2.5, 97.5])
    tag = " (complete target traces)" if complete_only else ""
    return (f"{name}{tag}: intercept c {est[0]:+.3f} [{lo[0]:+.3f}, {hi[0]:+.3f}]; slope g {est[1]:.3f} "
            f"[{lo[1]:.3f}, {hi[1]:.3f}]; c/g {est[2]:+.2f} [{lo[2]:+.2f}, {hi[2]:+.2f}] resting SD; "
            f"sham response {est[3]:+.3f} [{lo[3]:+.3f}, {hi[3]:+.3f}]; noise SD of D {est[4]:.2f}; "
            f"lambda {est[5]:.2f}; trials {est[6]}; worms {len(W)}\n"
            f"    scored with every other target's pairs (generic part): intercept {gen[0]:+.3f} [{glo:+.3f}, {ghi:+.3f}]; "
            f"target-specific intercept (true minus others) {est[0] - gen[0]:+.3f} [{dlo:+.3f}, {dhi:+.3f}]")


def main():
    import warnings
    warnings.filterwarnings("ignore")
    lines = []
    rng = np.random.default_rng(0)
    W = per_worm(load_pumpprobe_dir(str(S.ROOT / "data" / "raw" / "randi2023_wt_npz")), rng)
    lines += [report("worms", W), report("worms", W, True)]
    print("\n".join(lines[-2:]), flush=True)
    for seed in (0, 1):
        for gated in (False, True):
            nm = f"lab {'silent links' if gated else 'baseline'} seed {seed}"
            lines.append(report(nm, per_worm(S.lab_recs(gated, seed, 0.02), np.random.default_rng(seed))))
            print(lines[-1], flush=True)
    (S.FIG / "target_decoupling.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
