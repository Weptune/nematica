"""The ingredient ladder (pre-registered 6 Nov 2026; README "The ingredient ladder: what does an
artificial network need to look like a worm?"). Five ingredients in every combination, two
brains, six axes measured identically on lab networks and on the 113 atlas worms.

Usage:
  python scripts/run_ladder.py worms                 # the worms' fingerprint
  python scripts/run_ladder.py lab --seed 0          # all 32 variants of brain 0
  python scripts/run_ladder.py summary               # distances and Shapley values
Outputs: docs/figures/ladder_worms.csv, ladder_lab_seed<k>.csv, ladder_summary.txt
"""
from __future__ import annotations

import argparse
import csv
import itertools
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica import annlab as L  # noqa: E402
import run_week1 as W1  # noqa: E402

FIG = ROOT / "docs" / "figures"
ING = "DGSHM"
AXES = ["watch_share", "echo_breadth", "tiring", "rest_dim", "individuality", "reliability"]
KICK, KICK_FRAMES, LEAD = 6.0, 4, 230
GATE_TH, GATED = 0.98, 1.5
_g = np.random.default_rng(4242)
NEIGH = np.array([_g.choice([u for u in range(120) if u != i], size=2, replace=False) for i in range(120)])


# ---------------------------------------------------------------- the six axes
def class_resp_subset(w, stims):
    acc = defaultdict(list)
    cl = w.r.classes
    for k, f, v in stims:
        for j in range(w.N):
            if j != k and w.valid[j] and cl[j] != cl[k] and np.isfinite(v[j]):
                acc[(cl[k], cl[j])].append(v[j])
    return {p: float(np.mean(v)) for p, v in acc.items()}


def echo_breadth(worms):
    vals = []
    for w in worms:
        cl = w.r.classes
        for k, f, v in w.stims:
            per = defaultdict(list)
            for j in range(w.N):
                if j != k and w.valid[j] and cl[j] != cl[k] and np.isfinite(v[j]):
                    per[cl[j]].append(v[j])
            if len(per) >= 10:
                m = np.array([np.mean(x) for x in per.values()])
                vals.append(float(np.mean(np.abs(m) > 1.0)))
    return float(np.median(vals))


def rest_dim(worms):
    vals = []
    for w in worms:
        act = w.class_activity()
        if len(act) < 10:
            continue
        Z = np.array([a[w.unpoked] for a in act.values()])
        Z = Z[:, np.isfinite(Z).mean(0) > 0.5] if Z.shape[1] else Z
        if Z.shape[1] < 60:
            continue
        with np.errstate(all="ignore"):
            Z = (Z - np.nanmean(Z, 1, keepdims=True)) / np.nanstd(Z, 1, keepdims=True)
        Z = np.nan_to_num(Z)
        ev = np.linalg.svd(Z - Z.mean(1, keepdims=True), compute_uv=False) ** 2
        vals.append(float(ev[:3].sum() / ev.sum()))
    return float(np.median(vals))


def individuality(worms):
    halves = []
    for w in worms:
        st = sorted(w.stims, key=lambda s: s[1])
        halves.append((class_resp_subset(w, st[0::2]), class_resp_subset(w, st[1::2])))
    ex = []
    for i, (a, b) in enumerate(halves):
        same = W1.agree(a, b)
        if not np.isfinite(same):
            continue
        other = [W1.agree(a, halves[j][1]) for j in range(len(halves)) if j != i]
        other = [o for o in other if np.isfinite(o)]
        if other:
            ex.append(same - float(np.median(other)))
    return float(np.median(ex))


def fingerprint(worms):
    R = [w.class_resp() for w in worms]
    shares, w2w_all = [], []
    for fold in range(3):
        pool = [i for i in range(len(worms)) if i % 3 == fold]
        train = [worms[i] for i in range(len(worms)) if i % 3 != fold]
        pred = W1.fit_watching(train)
        w2w = [W1.agree(R[a], R[b]) for x, a in enumerate(pool) for b in pool[x + 1:]]
        wat = [W1.agree(pred, R[i]) for i in pool]
        shares.append(np.nanmedian(wat) / np.nanmedian(w2w))
        w2w_all += w2w
    lines, per = W1.b1_stats(worms, all_valid=not hasattr(worms[0], "is_worm"))
    tiring = float(np.nanmean(per[:, 1]))
    return {"watch_share": float(np.mean(shares)), "echo_breadth": echo_breadth(worms), "tiring": tiring,
            "rest_dim": rest_dim(worms), "individuality": individuality(worms),
            "reliability": float(np.nanmedian(w2w_all))}


# ---------------------------------------------------------------- lab variants
def modular_W(n, rho, rng, k=4, inside=0.9, density=0.1):
    mod = np.arange(n) * k // n
    same = mod[:, None] == mod[None, :]
    np.fill_diagonal(same, False)
    n_in, n_out = same.sum(), (~same).sum() - n
    edges = density * n * (n - 1)
    p_in, p_out = inside * edges / n_in, (1 - inside) * edges / n_out
    P = np.where(same, p_in, p_out)
    np.fill_diagonal(P, 0.0)
    Wm = rng.standard_normal((n, n)) * (rng.random((n, n)) < P)
    return Wm * rho / np.abs(np.linalg.eigvals(Wm)).max()


KICK_HOLD = {"frames": KICK_FRAMES}      # round 6 sets this to 16


def record(br, rng, obs, kicks, scale, spread):
    n = br.n
    Dm = getattr(br, "Dm", None)            # round 5: drives that scale the recurrent input
    k = (0 if br.D is None else br.D.shape[1]) or (0 if Dm is None else Dm.shape[1])
    x, s = np.zeros(n), np.zeros(k)
    y = np.full((L.FRAMES, n), np.nan)
    active = {f + d: (j, scale[f]) for f, j in kicks.items() for d in range(KICK_HOLD["frames"])}
    Wg = getattr(br, "Wg", None)
    for t in range(-400, L.FRAMES):
        if k:
            a_ = np.exp(-0.5 / br.tau)
            s = a_ * s + np.sqrt(1 - a_ * a_) * rng.standard_normal(k)
        rec = br.W @ np.tanh(x)
        if Dm is not None:
            rec = rec * (1.0 + br.gain * (Dm @ s))
        inp = rec + br.b + (br.D @ s if br.D is not None else 0.0)
        if Wg is not None:
            inp = inp + Wg @ (np.maximum(np.tanh(x) - GATE_TH, 0.0) / (1 - GATE_TH))
        x = (1 - L.LEAK) * x + L.LEAK * inp + br.q * rng.standard_normal(n)
        if t in active:
            j, a = active[t]
            x[j] += KICK * a
            if spread:
                x[NEIGH[j]] += spread * KICK * a
        if t >= 0:
            v = np.tanh(x) + br.r * rng.standard_normal(n)
            y[t, obs] = v[obs]
    return y


def variant_recs(code, seed, n_ind=113, sigma=0.3):
    on = set(code)
    W = modular_W(120, 1.3, np.random.default_rng(seed + 500)) if "M" in on else None
    br0 = L.make_brain(rho=1.3, share=0.25 if "D" in on else 0.0, tau=90.0, seed=seed, q=0.2, W=W)
    if "Q" in on:          # round 2: half the units sit near the flat bottom of their range
        quiet = np.random.default_rng(seed + 900).random(br0.n) < 0.5
        br0.b = br0.b.copy()
        br0.b[quiet] = -2.5
    if "G" in on:
        g = np.random.default_rng(12 + 100 * seed)
        Wg = GATED * g.standard_normal((br0.n, br0.n)) * (g.random((br0.n, br0.n)) < 0.05)
        np.fill_diagonal(Wg, 0.0)
        br0.Wg = Wg
    hidden = L.design(br0.n, np.random.default_rng(200))
    rng = np.random.default_rng(7)
    recs = []
    for i in range(n_ind):
        ind = L.individual(br0, sigma, 1000 + i)
        if "G" in on:
            ind.Wg = br0.Wg * (1 + sigma * np.random.default_rng(1000 + i + 777).standard_normal(br0.Wg.shape))
        obs = (rng.random(br0.n) < 0.5) & ~hidden
        targets = np.flatnonzero(obs)
        kicks = {f: int(rng.choice(targets)) for f in range(LEAD, L.FRAMES - L.WIN, L.EVERY)}
        count = defaultdict(int)
        scale = {}
        for f in sorted(kicks):
            count[kicks[f]] += 1
            scale[f] = 0.65 ** (count[kicks[f]] - 1) if "H" in on else 1.0
        y = record(ind, rng, obs, kicks, scale, 0.15 if "S" in on else 0.0)
        recs.append(L.as_pumpprobe(y, obs, kicks, f"ind{i:03d}"))
    return recs


def param_recs(pr, seed, n_ind=113, sigma=0.3):
    """Continuous ingredient strengths (joint fit, pre-registered 6 Nov): share (drives), g
    (silent-link strength, 0 = none), spread, quiet (fraction of quiet units), mod (0/1)."""
    W = modular_W(120, 1.3, np.random.default_rng(seed + 500)) if pr["mod"] else None
    br0 = L.make_brain(rho=1.3, share=pr["share"], tau=90.0, seed=seed, q=0.2, W=W)
    if pr["quiet"] > 0:
        quiet = np.random.default_rng(seed + 900).random(br0.n) < pr["quiet"]
        br0.b = br0.b.copy()
        br0.b[quiet] = -2.5
    if pr["g"] > 0:
        g = np.random.default_rng(12 + 100 * seed)
        Wg = pr["g"] * g.standard_normal((br0.n, br0.n)) * (g.random((br0.n, br0.n)) < 0.05)
        np.fill_diagonal(Wg, 0.0)
        br0.Wg = Wg
    hidden = L.design(br0.n, np.random.default_rng(200))
    rng = np.random.default_rng(7)
    recs = []
    for i in range(n_ind):
        ind = L.individual(br0, sigma, 1000 + i)
        if pr.get("gain"):
            ind.Dm = np.random.default_rng(seed + 4000).standard_normal((br0.n, 3)) / np.sqrt(3)
            ind.gain = pr["gain"]
        if pr.get("private") and br0.D is not None:     # round 4: each individual its own drive loadings
            gd = np.random.default_rng(5000 + i)
            ind.D = gd.standard_normal(br0.D.shape) * br0.D.std()
        if pr["g"] > 0:
            ind.Wg = br0.Wg * (1 + sigma * np.random.default_rng(1000 + i + 777).standard_normal(br0.Wg.shape))
        obs = (rng.random(br0.n) < 0.5) & ~hidden
        targets = np.flatnonzero(obs)
        kicks = {f: int(rng.choice(targets)) for f in range(LEAD, L.FRAMES - L.WIN, L.EVERY)}
        y = record(ind, rng, obs, kicks, {f: 1.0 for f in kicks}, pr["spread"])
        recs.append(L.as_pumpprobe(y, obs, kicks, f"ind{i:03d}"))
    return recs


GRID = {"share": [0.0, 0.1, 0.25, 0.4], "g": [0.0, 0.75, 1.5, 3.0], "spread": [0.0, 0.15, 0.3],
        "quiet": [0.0, 0.1, 0.2, 0.3], "mod": [0, 1]}
FIT_AXES = ["watch_share", "echo_breadth", "rest_dim", "individuality", "reliability"]


# restored 6 Nov: run_fit9 and GRID9 were deleted by mistake in ee526e2 (the CLI still called them)
GRID9 = {"share": [0.0, 0.1, 0.25, 0.4], "g": [0.0, 0.75, 1.5], "spread": [0.0, 0.15],
         "quiet": [0.0, 0.1, 0.2, 0.3], "sigma": [0.3, 0.5, 0.65, 0.8], "hold": [4, 6, 8, 10]}


def run_fit9(seed, part=None, top=None, leak=None):
    """Round 9. part = (i, k): this process measures draws i, i+k, i+2k, ... (two processes share
    the work on brain 0; each writes its own file)."""
    worm = {k: float(v) for k, v in next(csv.DictReader((FIG / "ladder_worms.csv").open())).items()}
    if top:
        rows0 = []
        for f in sorted(FIG.glob("ladder_fit9_seed0_part*.csv")):
            rows0 += list(csv.DictReader(f.open()))
        rows0.sort(key=lambda r: float(r["rel_err"]))
        settings = [{k: (int(r[k]) if k == "hold" else float(r[k])) for k in GRID9} for r in rows0[:top]]
        out = FIG / f"ladder_fit9_seed{seed}.csv"
    else:
        g = np.random.default_rng(909)
        settings = [{k: v[g.integers(len(v))] for k, v in GRID9.items()} for _ in range(60)]
        i, k = part
        settings = settings[i::k]
        out = FIG / f"ladder_fit9_seed{seed}_part{i}.csv"
    rows = list(csv.DictReader(out.open())) if out.exists() else []
    done = {tuple(str(r[x]) for x in GRID9) for r in rows}
    for pr in settings:
        key = tuple(str(pr[x]) for x in GRID9)
        if key in done:
            continue
        done.add(key)
        KICK_HOLD["frames"] = int(pr["hold"])
        if leak is not None:
            L.LEAK = leak
        full = {"share": pr["share"], "g": pr["g"], "spread": pr["spread"], "quiet": pr["quiet"], "mod": 0}
        ws = [W1.Worm(r, valid_fn=lambda c: True) for r in param_recs(full, seed, sigma=pr["sigma"])]
        fp = fingerprint(ws)
        L.LEAK = 0.5
        rel = [abs(fp[a] - worm[a]) / abs(worm[a]) for a in FIT_AXES]
        rows.append({**pr, **{a: round(fp[a], 4) for a in AXES},
                     "rel_err": round(float(np.sqrt(np.mean(np.square(rel)))), 4),
                     "within25": int(sum(r <= 0.25 for r in rel))})
        print(seed, rows[-1], flush=True)
        with out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    KICK_HOLD["frames"] = KICK_FRAMES


def run_private(seed):
    worm = {k: float(v) for k, v in next(csv.DictReader((FIG / "ladder_worms.csv").open())).items()}
    out = FIG / "ladder_private.csv"
    rows = list(csv.DictReader(out.open())) if out.exists() else []
    for base in ({"share": 0.25, "g": 0.75, "spread": 0.15, "quiet": 0.2, "mod": 0},
                 {"share": 0.4, "g": 1.5, "spread": 0.0, "quiet": 0.1, "mod": 0}):
        pr = {**base, "private": 1}
        fp = fingerprint([W1.Worm(r, valid_fn=lambda c: True) for r in param_recs(pr, seed)])
        rel = [abs(fp[a] - worm[a]) / abs(worm[a]) for a in FIT_AXES]
        rows.append({"seed": seed, **pr, **{a: round(fp[a], 4) for a in AXES},
                     "rel_err": round(float(np.sqrt(np.mean(np.square(rel)))), 4),
                     "within25": int(sum(r <= 0.25 for r in rel))})
        print(rows[-1], flush=True)
        with out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def run_gain(seed):
    worm = {k: float(v) for k, v in next(csv.DictReader((FIG / "ladder_worms.csv").open())).items()}
    out = FIG / "ladder_gain.csv"
    rows = list(csv.DictReader(out.open())) if out.exists() else []
    for gval in (0.0, 0.3, 0.6):
        pr = {"share": 0.0, "g": 0.75, "spread": 0.15, "quiet": 0.2, "mod": 0, "gain": gval}
        fp = fingerprint([W1.Worm(r, valid_fn=lambda c: True) for r in param_recs(pr, seed)])
        rel = [abs(fp[a] - worm[a]) / abs(worm[a]) for a in FIT_AXES]
        rows.append({"seed": seed, **pr, **{a: round(fp[a], 4) for a in AXES},
                     "rel_err": round(float(np.sqrt(np.mean(np.square(rel)))), 4),
                     "within25": int(sum(r <= 0.25 for r in rel))})
        print(rows[-1], flush=True)
        with out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def evoked_share(worms):
    """Share of the mean-square post-minus-pre change after pokes that is evoked. Reference onsets
    (corrected after the second review): the whole 25 s window must lie outside the 30 s after any
    poke (the `unpoked` mask), so held pokes and earlier echoes cannot enter it. In worms and in the
    lab this leaves the rest period before the first poke."""
    fl, ev = [], []
    for w in worms:
        for t in range(W1.PRE, w.T - W1.POST, 5):
            if not w.unpoked[t - W1.PRE:t + W1.POST].all():
                continue
            v = w.change(t)[w.valid]
            v = v[np.isfinite(v)]
            if len(v) >= 10:
                fl.append(np.mean(v ** 2))
        for k, f, v in w.stims:
            m = w.valid.copy()
            m[k] = False
            vv = v[m]
            vv = vv[np.isfinite(vv)]
            if len(vv) >= 10:
                ev.append(np.mean(vv ** 2))
    if not fl:
        return float("nan")
    return float((np.mean(ev) - np.mean(fl)) / np.mean(ev))


def run_evoked():
    out = ["Evoked share of the post-minus-pre change (reference windows entirely outside the 30 s after any poke)"]
    out.append(f"worms: {evoked_share(W1.load_worms()):.3f}")
    for code in ("", "D", "G", "DG", "DGSM"):
        out.append(f"lab {code or 'base'} (brain 0, hold 4): {evoked_share([W1.Worm(r, valid_fn=lambda c: True) for r in variant_recs(code, 0)]):.3f}")
    for hold in (16,):
        KICK_HOLD["frames"] = hold
        out.append(f"lab DGSM (brain 0, hold {hold}): {evoked_share([W1.Worm(r, valid_fn=lambda c: True) for r in variant_recs('DGSM', 0)]):.3f}")
    KICK_HOLD["frames"] = 6
    out.append(f"lab round 9 setting (brain 0, hold 6, sigma 0.8): {evoked_share([W1.Worm(r, valid_fn=lambda c: True) for r in param_recs({'share': 0.4, 'g': 0.75, 'spread': 0.15, 'quiet': 0.3, 'mod': 0}, 0, sigma=0.8)]):.3f}")
    KICK_HOLD["frames"] = KICK_FRAMES
    (FIG / "echo_noise_share.txt").write_text("\n".join(out) + "\n")
    print("\n".join(out))


def run_long(seed, holds=(4, 16), out_name="ladder_long.csv"):
    worm = {k: float(v) for k, v in next(csv.DictReader((FIG / "ladder_worms.csv").open())).items()}
    out = FIG / out_name
    rows = list(csv.DictReader(out.open())) if out.exists() else []
    best = {"share": 0.25, "g": 0.75, "spread": 0.15, "quiet": 0.0 + 0.2, "mod": 0}
    for hold in holds:
        KICK_HOLD["frames"] = hold
        for name in ("best", "DGSM"):
            recs = param_recs(best, seed) if name == "best" else variant_recs("DGSM", seed)
            ws = [W1.Worm(r, valid_fn=lambda c: True) for r in recs]
            fp = fingerprint(ws)
            rel = [abs(fp[a] - worm[a]) / abs(worm[a]) for a in FIT_AXES]
            rows.append({"seed": seed, "setting": name, "hold": hold, "evoked_share": round(evoked_share(ws), 4),
                         **{a: round(fp[a], 4) for a in AXES},
                         "rel_err": round(float(np.sqrt(np.mean(np.square(rel)))), 4),
                         "within25": int(sum(r <= 0.25 for r in rel))})
            print(rows[-1], flush=True)
            with out.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    KICK_HOLD["frames"] = KICK_FRAMES


def run_fit(seed, n=48, top=None):
    worm = {k: float(v) for k, v in next(csv.DictReader((FIG / "ladder_worms.csv").open())).items()}
    out = FIG / f"ladder_fit_seed{seed}.csv"
    rows = list(csv.DictReader(out.open())) if out.exists() else []
    if top is None:
        g = np.random.default_rng(2026)
        settings = [{k: v[g.integers(len(v))] for k, v in GRID.items()} for _ in range(n)]
    else:          # the best settings found on brain 0, re-measured on another brain
        b0 = list(csv.DictReader((FIG / "ladder_fit_seed0.csv").open()))
        b0.sort(key=lambda r: float(r["rel_err"]))
        settings = [{k: (int(r[k]) if k == "mod" else float(r[k])) for k in GRID} for r in b0[:top]]
    done = {tuple(r[k] for k in GRID) for r in rows}
    for pr in settings:
        key = tuple(str(pr[k]) for k in GRID)
        if key in done:
            continue
        done.add(key)
        fp = fingerprint([W1.Worm(r, valid_fn=lambda c: True) for r in param_recs(pr, seed)])
        rel = [abs(fp[a] - worm[a]) / abs(worm[a]) for a in FIT_AXES]
        rows.append({**{k: pr[k] for k in GRID}, **{a: round(fp[a], 4) for a in AXES},
                     "rel_err": round(float(np.sqrt(np.mean(np.square(rel)))), 4),
                     "within25": int(sum(r <= 0.25 for r in rel))})
        print(seed, rows[-1], flush=True)
        with out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def run_lab(seed, codes=None):
    out = FIG / f"ladder_lab_seed{seed}.csv"
    rows = list(csv.DictReader(out.open())) if out.exists() else []
    done = {r["variant"] for r in rows}
    codes = codes or ["".join(c for c, b in zip(ING, bits) if b) for bits in itertools.product([0, 1], repeat=5)]
    for code in codes:
        name = code or "base"
        if name in done:
            continue
        recs = variant_recs(code, seed)
        worms = [W1.Worm(r, valid_fn=lambda c: True) for r in recs]
        fp = fingerprint(worms)
        rows.append({"variant": name, **{k: round(v, 4) for k, v in fp.items()}})
        print(seed, rows[-1], flush=True)
        with out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["variant"] + AXES)
            w.writeheader()
            w.writerows(rows)


def run_worms():
    worms = W1.load_worms()
    for w in worms:
        w.is_worm = True
    fp = fingerprint(worms)
    with (FIG / "ladder_worms.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=AXES)
        w.writeheader()
        w.writerow({k: round(v, 4) for k, v in fp.items()})
    print(fp)


def shapley(f, i):
    """f: dict frozenset(ingredients) -> value; Shapley value of ingredient i."""
    others = [c for c in ING if c != i]
    n = len(ING)
    tot = 0.0
    for r in range(len(others) + 1):
        for S in itertools.combinations(others, r):
            wgt = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
            tot += wgt * (f[frozenset(S) | {i}] - f[frozenset(S)])
    return tot


def run_summary():
    worm = {k: float(v) for k, v in next(csv.DictReader((FIG / "ladder_worms.csv").open())).items()}
    labs = {}
    for seed in (0, 1):
        p = FIG / f"ladder_lab_seed{seed}.csv"
        # the pre-registered summary uses the 32 round-1 variants only (round 2 rows are summarised separately)
        labs[seed] = {r["variant"]: {k: float(r[k]) for k in AXES} for r in csv.DictReader(p.open())
                      if "Q" not in r["variant"]}
    allv = np.array([[v[a] for a in AXES] for s in labs for v in labs[s].values()])
    scale = allv.std(0)
    out = ["worms: " + ", ".join(f"{a} {worm[a]:.3f}" for a in AXES),
           "axis scales (SD over lab runs): " + ", ".join(f"{a} {s:.3f}" for a, s in zip(AXES, scale)), ""]
    key = lambda name: frozenset("" if name == "base" else name)  # noqa: E731
    dist = {}
    for seed, vs in labs.items():
        for name, v in vs.items():
            z = np.array([(v[a] - worm[a]) / s for a, s in zip(AXES, scale)])
            dist[(seed, name)] = float(np.sqrt(np.mean(z ** 2)))
    names = sorted(labs[0], key=lambda n: (len(n) if n != "base" else 0, n))
    out.append("variant  " + "  ".join(f"{a[:12]:>12s}" for a in AXES) + "   distance (brain 0 / 1)")
    for nme in names:
        v0, v1 = labs[0][nme], labs[1].get(nme)
        cells = "  ".join(f"{v0[a]:6.3f}/{v1[a]:6.3f}" if v1 else f"{v0[a]:6.3f}" for a in AXES)
        out.append(f"{nme:7s}  {cells}   {dist[(0, nme)]:.2f} / {dist.get((1, nme), float('nan')):.2f}")
    out.append("")
    for target in ["watch_share", "echo_breadth", "tiring", "distance"]:
        cells = []
        for i in ING:
            vals = []
            for seed in (0, 1):
                f = {key(n): (dist[(seed, n)] if target == "distance" else labs[seed][n][target]) for n in labs[seed]}
                vals.append(shapley(f, i))
            cells.append(f"{i} {np.mean(vals):+.3f} ({vals[0]:+.3f}, {vals[1]:+.3f})")
        out.append(f"Shapley on {target}: " + "; ".join(cells))
    best = sorted(((d, s, n) for (s, n), d in dist.items()))[:6]
    out.append("closest variants: " + "; ".join(f"brain {s} {n} {d:.2f}" for d, s, n in best))
    mean_d = defaultdict(list)
    for (s, n), d in dist.items():
        mean_d[n].append(d)
    bestm = sorted((np.mean(v), n) for n, v in mean_d.items())[:5]
    out.append("closest by mean of both brains: " + "; ".join(f"{n} {d:.2f}" for d, n in bestm))
    out += [""] + extras(worm, labs, scale, key)
    (FIG / "ladder_summary.txt").write_text("\n".join(out) + "\n")
    print("\n".join(out))


def extras(worm, labs, scale, key):
    """Exploratory additions (labelled as such in the README): distance without the tiring axis,
    implied watching agreement (share x reliability), and round 2 (quiet units)."""
    out = ["Exploratory (not pre-registered): distance without the tiring axis, which no variant approaches"]
    use = [a for a in AXES if a != "tiring"]
    d = {(s, n): float(np.sqrt(np.mean([((v[a] - worm[a]) / scale[AXES.index(a)]) ** 2 for a in use])))
         for s in labs for n, v in labs[s].items()}
    m = {n: np.mean([d[(0, n)], d[(1, n)]]) for n in labs[0]}
    srt = sorted(m.items(), key=lambda t: t[1])
    out.append("closest by mean of both brains: " + "; ".join(f"{n} {v:.2f}" for n, v in srt[:6])
               + f"; range {min(d.values()):.2f} to {max(d.values()):.2f}")
    out.append("Exploratory: implied watching agreement (watching share x reliability); worms "
               f"{worm['watch_share'] * worm['reliability']:.3f}")
    for n in sorted(labs[0], key=lambda n: (len(n) if n != "base" else 0, n)):
        out.append(f"  {n:6s} " + " / ".join(f"{labs[s][n]['watch_share'] * labs[s][n]['reliability']:.3f}" for s in (0, 1)))
    cells = []
    for i in ING:
        vals = [shapley({key(n): labs[s][n]["watch_share"] * labs[s][n]["reliability"] for n in labs[s]}, i) for s in (0, 1)]
        cells.append(f"{i} {np.mean(vals):+.3f} ({vals[0]:+.3f}, {vals[1]:+.3f})")
    out.append("Shapley on implied watching agreement: " + "; ".join(cells))
    # round 2
    r2 = {}
    for seed in (0, 1):
        p = FIG / f"ladder_lab_seed{seed}.csv"
        r2[seed] = {r["variant"]: {k: float(r[k]) for k in AXES} for r in csv.DictReader(p.open())}
    pairs = [("base", "Q"), ("D", "DQ"), ("G", "GQ"), ("DG", "DGQ"), ("DGS", "DGSQ"), ("GSM", "GSMQ"), ("DGSM", "DGSMQ")]
    if all(b in r2[0] and b in r2[1] for _, b in pairs):
        out.append("")
        out.append("Round 2 (quiet units), without -> with Q, brain 0 / brain 1: echo breadth; watching share; rest dimensionality")
        nb = nw = 0
        for a, b in pairs:
            for s in (0, 1):
                nb += r2[s][b]["echo_breadth"] < r2[s][a]["echo_breadth"]
                nw += r2[s][b]["watch_share"] - r2[s][a]["watch_share"] <= 0.1
            out.append(f"  {a:5s}-> {b:6s} " + "; ".join(
                " / ".join(f"{r2[s][a][x]:.3f}->{r2[s][b][x]:.3f}" for s in (0, 1)) for x in ("echo_breadth", "watch_share", "rest_dim")))
        out.append(f"prediction 1 (Q narrows echoes): {nb} of 14; prediction 2 (Q raises watching share by at most 0.1): {nw} of 14")
        res = []
        for n in r2[0]:
            if n not in r2[1]:
                continue
            c = [sum(abs(r2[s][n][a] - worm[a]) <= 0.25 * abs(worm[a]) for a in AXES) for s in (0, 1)]
            both = [a for a in AXES if all(abs(r2[s][n][a] - worm[a]) <= 0.25 * abs(worm[a]) for s in (0, 1))]
            res.append((sum(c) / 2, n, c, both))
        res.sort(key=lambda t: (-t[0], t[1]))
        out.append(f"axes within 25% of the worm value (brain 0/1; axes in both), top 6 of {len(res)} variants:")
        out += [f"  {n:6s} {c[0]}/{c[1]}  {', '.join(a)}" for _, n, c, a in res[:6]]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["worms", "lab", "summary", "fit", "fit9", "evoked"])
    ap.add_argument("--part", default=None)
    ap.add_argument("--top", type=int, default=None)
    ap.add_argument("--private", action="store_true")
    ap.add_argument("--gain", action="store_true")
    ap.add_argument("--long", action="store_true")
    ap.add_argument("--hold-sweep", action="store_true")
    ap.add_argument("--sigma-sweep", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--codes", default=None)
    a = ap.parse_args()
    if a.cmd == "worms":
        run_worms()
    elif a.cmd == "evoked":
        run_evoked()
    elif a.cmd == "fit9":
        run_fit9(a.seed, part=tuple(int(x) for x in a.part.split("/")) if a.part else None, top=a.top)
    elif a.cmd == "fit" and a.sigma_sweep:
        run_sigma(a.seed)
    elif a.cmd == "fit" and a.hold_sweep:
        run_long(a.seed, holds=(6, 8, 10), out_name=f"ladder_holds_seed{a.seed}.csv")
    elif a.cmd == "fit" and a.long:
        run_long(a.seed)
    elif a.cmd == "fit" and a.gain:
        run_gain(a.seed)
    elif a.cmd == "fit" and a.private:
        run_private(a.seed)
    elif a.cmd == "fit":
        run_fit(a.seed, top=a.top)
    elif a.cmd == "lab":
        run_lab(a.seed, a.codes.split(",") if a.codes else None)
    else:
        run_summary()
