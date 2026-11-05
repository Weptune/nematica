"""Do worms have links that are silent at rest? Pre-registered 5 Nov 2026 (README section of the
same name; the definitions there are the specification, this is their implementation).

  T1  do pokes push their targets beyond the range those neurons visit at rest?
  T2  is a unit of drive more effective beyond the resting range than within it (gain jump)?

Lab brains recorded like atlas worms, with and without the silent links of lab G, are the
positive and negative controls; each poke's strength is scaled by a factor drawn log-uniformly
from [a, 1] so that some pokes stay within the resting range, as in worms.

Usage:
  python scripts/run_silent_links_test.py worms-t1
  python scripts/run_silent_links_test.py calibrate                 # choose a (baseline brain, seed 0)
  python scripts/run_silent_links_test.py lab --a 0.1               # both brains, seeds 0 and 1
  python scripts/run_silent_links_test.py worms-t2
Outputs: docs/figures/silent_links_*.txt and .csv
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica import annlab as L  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402

FIG = ROOT / "docs" / "figures"
EXCL, MIN_UNPOKED, RUN, POST, PRE = 60, 100, 4, 30, 20
MIN_TRIALS, TMIN, BOOT = 6, 3.0, 2000
GATE_TH, GATED, KICK, KICK_FRAMES = 0.98, 1.5, 6.0, 4


# ---------------------------------------------------------------- measures (worms and lab alike)
def unpoked_mask(r) -> np.ndarray:
    m = np.ones(r.n_frames, bool)
    for f in r.all_stim_frames:
        m[f:f + EXCL] = False
    return m


def runmean(v: np.ndarray, k=RUN) -> np.ndarray:
    c = np.convolve(v, np.ones(k) / k, mode="valid")
    return c


def worm_trials(r):
    """Per stimulation of a named target: E, the target's resting p95 and p99, D, and R for every
    other named neuron. Returns None if the worm has too few unpoked frames."""
    m = unpoked_mask(r)
    if m.sum() < MIN_UNPOKED:
        return None
    X = r.x
    mu = np.nanmean(np.where(m, X, np.nan), axis=1)
    sd = np.nanstd(np.where(m, X, np.nan), axis=1)
    ok4 = runmean(m.astype(float)) > 1 - 1e-9          # runs of 4 consecutive unpoked frames
    rest = {}
    trials = []
    T = r.n_frames
    for k, f in r.stims:
        cj = r.classes[k]
        if not cj or f - PRE < 0 or f + POST > T or not (sd[k] > 0):
            continue
        if k not in rest:
            z = (X[k] - mu[k]) / sd[k]
            rm = runmean(np.nan_to_num(z, nan=np.nan))
            vals = rm[ok4 & np.isfinite(rm)]
            rest[k] = (np.percentile(vals, 95), np.percentile(vals, 99)) if len(vals) >= 20 else None
        if rest[k] is None:
            continue
        zk = (X[k, f:f + POST] - mu[k]) / sd[k]
        rm = runmean(zk)
        if not np.isfinite(rm).any():
            continue
        E = float(np.nanmax(rm))
        base = X[:, f - PRE:f]
        post = X[:, f:f + POST]
        chg = (np.nanmean(post, axis=1) - np.nanmean(base, axis=1)) / np.where(sd > 0, sd, np.nan)
        D = float(chg[k])
        if not np.isfinite(D):
            continue
        resp = {r.classes[i]: float(chg[i]) for i in range(len(chg))
                if i != k and r.classes[i] and r.classes[i] != cj and np.isfinite(chg[i])}
        trials.append(dict(cj=cj, E=E, p95=rest[k][0], p99=rest[k][1], D=D, R=resp))
    return trials


def all_trials(recs):
    out = []
    for r in recs:
        t = worm_trials(r)
        if t is not None and len(t):
            out.append((r.uid, t))
    return out


# ---------------------------------------------------------------- T1
def wmedian(v, w):
    o = np.argsort(v)
    v, w = np.asarray(v)[o], np.asarray(w)[o]
    c = np.cumsum(w) / w.sum()
    return float(v[np.searchsorted(c, 0.5)])


def t1(data, seed=0):
    def stat(sel):
        v95, v99, w, beyond, within = [], [], [], [], []
        for uid, tr in sel:
            for t in tr:
                v95.append(t["E"] - t["p95"])
                v99.append(t["E"] - t["p99"])
                w.append(1.0 / len(tr))
                beyond.append((t["E"] > t["p99"]) / len(tr))
                within.append((t["E"] <= t["p95"]) / len(tr))
        W = sum(w)
        return wmedian(v95, w), wmedian(v99, w), sum(beyond) / W, sum(within) / W
    est = stat(data)
    rng = np.random.default_rng(seed)
    bs = np.array([stat([data[i] for i in rng.integers(0, len(data), len(data))]) for _ in range(500)])
    lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
    return est, lo, hi


# ---------------------------------------------------------------- T2
def choose_pairs(half):
    acc = defaultdict(list)
    for uid, tr in half:
        for t in tr:
            for ci, v in t["R"].items():
                acc[(t["cj"], ci)].append(v)
    pairs = {}
    for p, v in acc.items():
        v = np.array(v)
        if len(v) < MIN_TRIALS:
            continue
        se = v.std(ddof=1) / np.sqrt(len(v))
        if se > 0 and abs(v.mean() / se) > TMIN:
            pairs[p] = (np.sign(v.mean()), np.mean(np.abs(v)))
    return pairs


def worm_sums(tr, pairs):
    """Per worm: summed normalised response and summed drive, beyond and within."""
    s = np.zeros(4)            # Rb, Db, Rw, Dw
    for t in tr:
        cat = 0 if t["E"] > t["p99"] else (2 if t["E"] <= t["p95"] else None)
        if cat is None:
            continue
        for ci, v in t["R"].items():
            p = pairs.get((t["cj"], ci))
            if p is None:
                continue
            s[cat] += v * p[0] / p[1]
            s[cat + 1] += t["D"]
    return s


def Q_of(S):
    Rb, Db, Rw, Dw = S.sum(axis=0)
    if Db <= 0 or Dw <= 0:
        return np.nan, np.nan, np.nan
    gb, gw = Rb / Db, Rw / Dw
    if gb <= 0 or gw <= 0:
        return np.nan, gb, gw
    return float(np.log(gb / gw)), gb, gw


def t2(data, seed=0):
    halves = [data[0::2], data[1::2]]
    S, npairs = [], []
    for h in (0, 1):
        pairs = choose_pairs(halves[h])
        npairs.append(len(pairs))
        S += [worm_sums(tr, pairs) for uid, tr in halves[1 - h]]
    S = np.array(S)
    q, gb, gw = Q_of(S)
    rng = np.random.default_rng(seed)
    bq = np.array([Q_of(S[rng.integers(0, len(S), len(S))])[0] for _ in range(BOOT)])
    return dict(Q=q, gain_beyond=gb, gain_within=gw, pairs=npairs, worms=len(S),
                lo=float(np.nanpercentile(bq, 2.5)), hi=float(np.nanpercentile(bq, 97.5)),
                undefined_share=float(np.isnan(bq).mean()), boot=bq)


# ---------------------------------------------------------------- lab brains
def lab_record(br, rng, obs, kicks, scale, frames=L.FRAMES, burn=400):
    n = br.n
    k = 0 if br.D is None else br.D.shape[1]
    x, s = np.zeros(n), np.zeros(k)
    y = np.full((frames, n), np.nan)
    active = {f + d: (j, scale[f]) for f, j in kicks.items() for d in range(KICK_FRAMES)}
    Wg = getattr(br, "Wg", None)
    for t in range(-burn, frames):
        s = br.drive_step(s, rng)
        inp = br.W @ np.tanh(x) + br.b + (br.D @ s if k else 0.0)
        if Wg is not None:
            inp = inp + Wg @ (np.maximum(np.tanh(x) - GATE_TH, 0.0) / (1 - GATE_TH))
        x = (1 - L.LEAK) * x + L.LEAK * inp + br.q * rng.standard_normal(n)
        if t in active:
            j, a = active[t]
            x[j] += KICK * a
        if t >= 0:
            v = np.tanh(x) + br.r * rng.standard_normal(n)
            y[t, obs] = v[obs]
    return y


def lab_recs(gated: bool, seed: int, a: float, n=113, sigma=0.3):
    br0 = L.make_brain(rho=1.3, share=0.05, tau=90.0, seed=seed, q=0.2)
    if gated:
        g = np.random.default_rng(12 + 100 * seed)
        Wg = GATED * g.standard_normal((br0.n, br0.n)) * (g.random((br0.n, br0.n)) < 0.05)
        np.fill_diagonal(Wg, 0.0)
        br0.Wg = Wg
    hidden = L.design(br0.n, np.random.default_rng(200))
    rng = np.random.default_rng(7)
    recs = []
    for i in range(n):
        ind = L.individual(br0, sigma, 1000 + i)
        if gated:
            ind.Wg = br0.Wg * (1 + sigma * np.random.default_rng(1000 + i + 777).standard_normal(br0.Wg.shape))
        obs = (rng.random(br0.n) < 0.5) & ~hidden
        targets = np.flatnonzero(obs)
        kicks = {f: int(rng.choice(targets)) for f in range(230, L.FRAMES - L.WIN, L.EVERY)}
        scale = {f: float(np.exp(rng.uniform(np.log(a), 0.0))) for f in kicks}
        y = lab_record(ind, rng, obs, kicks, scale)
        recs.append(L.as_pumpprobe(y, obs, kicks, f"ind{i:03d}"))
    return recs


# ---------------------------------------------------------------- commands
def fmt_t1(name, res):
    (m95, m99, fb, fw), lo, hi = res
    return (f"{name}: share beyond resting p99 {fb:.3f} [{lo[2]:.3f}, {hi[2]:.3f}]; share within p95 {fw:.3f} "
            f"[{lo[3]:.3f}, {hi[3]:.3f}]; median E - p95 {m95:+.2f} [{lo[0]:+.2f}, {hi[0]:+.2f}]; "
            f"median E - p99 {m99:+.2f} [{lo[1]:+.2f}, {hi[1]:+.2f}] (resting-SD units, worm-weighted)")


def fmt_t2(name, r):
    return (f"{name}: Q {r['Q']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}]; gain beyond {r['gain_beyond']:.3f}, "
            f"within {r['gain_within']:.3f}; pairs chosen {r['pairs']}; worms scored {r['worms']}; "
            f"bootstrap undefined {r['undefined_share']:.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["worms-t1", "calibrate", "lab", "worms-t2"])
    ap.add_argument("--a", type=float, default=None)
    ap.add_argument("--atlas", default=str(ROOT / "data" / "raw" / "randi2023_wt_npz"))
    args = ap.parse_args()
    if args.cmd == "worms-t1":
        data = all_trials(load_pumpprobe_dir(args.atlas))
        res = t1(data)
        n = sum(len(t) for _, t in data)
        txt = f"T1 on atlas worms ({len(data)} worms with >= {MIN_UNPOKED} unpoked frames, {n} stimulations)\n" + fmt_t1("worms", res)
        txt += "\nH's necessary condition fails if median E - p95 <= 0: " + ("FAILS" if res[0][0] <= 0 else "holds")
        print(txt)
        (FIG / "silent_links_t1_worms.txt").write_text(txt + "\n")
        json.dump({"share_beyond": res[0][2], "share_within": res[0][3]}, open(FIG / "silent_links_t1_worms.json", "w"))
    elif args.cmd == "calibrate":
        target = json.load(open(FIG / "silent_links_t1_worms.json"))["share_beyond"]
        lines = [f"worm share beyond: {target:.3f}"]
        best = None
        for a in (0.02, 0.05, 0.1, 0.2, 0.3):
            res = t1(all_trials(lab_recs(False, 0, a)))
            lines.append(fmt_t1(f"baseline seed 0, a={a}", res))
            print(lines[-1], flush=True)
            d = abs(res[0][2] - target)
            if best is None or d < best[0]:
                best = (d, a)
        lines.append(f"chosen a = {best[1]}")
        print(lines[-1])
        (FIG / "silent_links_calibration.txt").write_text("\n".join(lines) + "\n")
    elif args.cmd == "lab":
        lines, Q = [], {}
        for seed in (0, 1):
            for gated in (False, True):
                data = all_trials(lab_recs(gated, seed, args.a))
                nm = f"{'silent links' if gated else 'baseline'} seed {seed}"
                lines.append(fmt_t1(nm, t1(data)))
                r = t2(data)
                Q[(seed, gated)] = r
                lines.append(fmt_t2(nm, r))
                print(lines[-2] + "\n" + lines[-1], flush=True)
            d = Q[(seed, True)]["boot"] - Q[(seed, False)]["boot"]
            lo, hi = np.nanpercentile(d, [2.5, 97.5])
            lines.append(f"seed {seed}: Q(silent) - Q(baseline) {Q[(seed, True)]['Q'] - Q[(seed, False)]['Q']:+.3f} "
                         f"[{lo:+.3f}, {hi:+.3f}] (independent bootstraps)")
            print(lines[-1], flush=True)
        valid = all(np.nanpercentile(Q[(s, True)]["boot"] - Q[(s, False)]["boot"], 2.5) > 0 for s in (0, 1))
        line = float(np.mean([(Q[(s, True)]["Q"] + Q[(s, False)]["Q"]) / 2 for s in (0, 1)]))
        base = [Q[(s, False)]["Q"] for s in (0, 1)]
        lines.append(f"valid: {valid}; decision line {line:+.3f}; baseline Q {base[0]:+.3f}, {base[1]:+.3f}; a = {args.a}")
        print(lines[-1])
        (FIG / "silent_links_lab.txt").write_text("\n".join(lines) + "\n")
        json.dump({"valid": bool(valid), "line": line, "baseline": base, "a": args.a},
                  open(FIG / "silent_links_lab.json", "w"))
    else:
        lab = json.load(open(FIG / "silent_links_lab.json"))
        data = all_trials(load_pumpprobe_dir(args.atlas))
        r = t2(data)
        txt = fmt_t2("worms", r)
        if not lab["valid"]:
            verdict = "test not valid on lab brains: uninformative"
        elif r["lo"] > lab["line"]:
            verdict = "supports H"
        elif r["hi"] < min(lab["baseline"]):
            verdict = "counts against H"
        else:
            verdict = "inconclusive"
        txt += f"\nlab: valid {lab['valid']}, decision line {lab['line']:+.3f}, baseline Q {lab['baseline']}\nverdict: {verdict}"
        print(txt)
        (FIG / "silent_links_t2_worms.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
