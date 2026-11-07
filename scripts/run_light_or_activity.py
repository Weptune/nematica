"""Light or activity: what tires a worm neuron? (pre-registered 8 Nov 2026, README section of that name).

Usage:
  python scripts/run_light_or_activity.py calibrate   # tune synthetic truths to the worm's known direct drop
  python scripts/run_light_or_activity.py validate    # 10 synthetic atlases per truth (must pass first)
  python scripts/run_light_or_activity.py t1          # light share on the worms
  python scripts/run_light_or_activity.py t2          # does the drop pass downstream?
  python scripts/run_light_or_activity.py t3          # recovery clocks
  python scripts/run_light_or_activity.py t4          # unc-31
Output: docs/figures/light_or_activity.txt (appended)
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_tiring_source as TS  # noqa: E402
import run_week1 as W  # noqa: E402
from nematica import tiring_sim as TM  # noqa: E402

OUT = ROOT / "docs" / "figures" / "light_or_activity.txt"
UNC = ROOT / "data" / "raw" / "randi2023_unc31_npz"


def log(line):
    print(line, flush=True)
    with OUT.open("a") as fh:
        fh.write(line + "\n")


def wrap(w):
    fp = TS.POS / f"{w.r.uid}.npz"
    near = [None] * w.N
    if fp.exists():
        pos = np.load(fp)["pos"]
        if pos.shape[0] == w.N:
            near = TS.nearest3(pos)
    X = w.r.x

    def pre(k, f):
        with np.errstate(all="ignore"):
            return (np.nanmean(X[k, f - W.PRE:f]) - w.mu_u[k]) / w.sd[k]
    return dict(stims=sorted(w.stims, key=lambda t: t[1]), pre=pre, near=near, classes=list(w.r.classes),
                T=w.T, uid=w.r.uid, N=w.N, has_pos=near[0] is not None or any(n is not None for n in near))


def keyed(ws, bins=None, amended=False):
    per = []
    for wi, w in enumerate(ws):
        rs = TM.rows_amended(w) if amended else TM.rows(w, bins=bins)
        for r in rs:
            r["key"] = f"{wi}_{r['unit']}"
        if rs:
            per.append(rs)
    return per


def schedules():
    out = []
    for w in W.load_worms():
        out.append(([(k, f) for k, f, _ in w.stims], w.N, list(w.r.classes), w.T))
    return out


def synth_atlas(scheds, truth, seed, **kw):
    rng = np.random.default_rng(seed)
    return [TM.synth_worm(s, N, cl, T, truth, rng, **kw) for s, N, cl, T in scheds]


def fmt(res):
    C = res["C"]
    parts = [f"{c} {res['b'][i]:+.3f} [{res['lo'][i]:+.3f}, {res['hi'][i]:+.3f}]" for i, c in enumerate(C)]
    return (f"n {res['n']} (L=1: {res['n_L']}); " + "; ".join(parts)
            + f"; A_dir {res['A_dir']:.2f}; total direct effect {res['total']:+.3f}; light share S {res['S']:.2f}"
            + f" [90%: {res['S_lo']:.2f}, {res['S_hi']:.2f}]; p(L) {res['p_L']:.4f}")


def validate_amended():
    sc = schedules()
    log("VALIDATION, amendment 1 (pass: >= 8/10 in each of six conditions, tool and neuron truths x recovery 5/10/20 min)")
    allok = True
    for tau_min in (5, 10, 20):
        for truth, kw in [("tool", dict(h=0.35)), ("neuron", dict(kappa=0.5))]:
            ok = 0
            Ss = []
            for s in range(10):
                res = TM.t1(keyed(synth_atlas(sc, truth, 1000 + 37 * tau_min + s, tau=tau_min * 120, **kw), amended=True),
                            n_boot=1000, n_shuf=0, seed=s, share=TM.light_share_amended)
                good = res["S_lo"] > 0.5 if truth == "tool" else res["S_hi"] < 0.5
                ok += int(good)
                Ss.append(f"{res['S']:.2f}[{res['S_lo']:.2f},{res['S_hi']:.2f}]")
            allok &= ok >= 8
            log(f"  tau {tau_min} min, {truth}: {ok}/10; S: " + " ".join(Ss))
    for s in range(5):
        res = TM.t1(keyed(synth_atlas(sc, "mixed", 2000 + s, h=0.6, kappa=0.25), amended=True),
                    n_boot=500, n_shuf=0, seed=s, share=TM.light_share_amended)
        log(f"  mixed truth atlas {s} (reported only): S {res['S']:.2f} [{res['S_lo']:.2f}, {res['S_hi']:.2f}]; total {res['total']:+.3f}")
    log(f"VALIDATION amendment 1 result: {'PASS' if allok else 'FAIL'}")
    return allok


def calibrate():
    sc = schedules()
    for truth, kw in [("tool", dict(h=0.5)), ("tool", dict(h=0.35)), ("neuron", dict(kappa=0.25)),
                      ("neuron", dict(kappa=0.5)), ("neuron", dict(kappa=1.0))]:
        res = TM.t1(keyed(synth_atlas(sc, truth, 1, **kw)), n_boot=200, n_shuf=0)
        log(f"CALIBRATE {truth} {kw}: " + fmt(res))


def validate(tool_kw, neuron_kw):
    sc = schedules()
    log(f"VALIDATION (pre-registered pass rule: S interval above 0.5 in >= 8/10 tool atlases, below 0.5 in >= 8/10 neuron atlases); tool {tool_kw}, neuron {neuron_kw}")
    passes = {}
    for truth, kw in [("tool", tool_kw), ("neuron", neuron_kw)]:
        ok = 0
        for s in range(10):
            res = TM.t1(keyed(synth_atlas(sc, truth, 100 + s, **kw)), n_boot=1000, n_shuf=0, seed=s)
            good = res["S_lo"] > 0.5 if truth == "tool" else res["S_hi"] < 0.5
            ok += int(good)
            log(f"  {truth} atlas {s}: S {res['S']:.2f} [{res['S_lo']:.2f}, {res['S_hi']:.2f}]; total {res['total']:+.3f}; "
                f"bL {res['b'][0]:+.3f}; bA {res['b'][1]:+.3f}; {'ok' if good else 'MISS'}")
        passes[truth] = ok
    verdict = passes["tool"] >= 8 and passes["neuron"] >= 8
    log(f"VALIDATION result: tool {passes['tool']}/10, neuron {passes['neuron']}/10 -> {'PASS' if verdict else 'FAIL'}")
    return verdict


def t1(folder=None, label="worms (wild type)"):
    ws = [wrap(w) for w in W.load_worms(folder)]
    per = keyed(ws)
    res = TM.t1(per)
    log(f"T1 {label}: worms with rows {len(per)}; " + fmt(res))
    S_lo, S_hi = res["S_lo"], res["S_hi"]
    iL, iA = 0, 1
    if S_lo > 0.5 and res["hi"][iL] < 0 and res["p_L"] < 0.05:
        v = "mostly light"
    elif S_hi < 0.5 and res["hi"][iA] < 0:
        v = "mostly activity"
    else:
        v = "inconclusive"
    log(f"T1 {label} verdict: {v}")
    return res


def t1a(folder=None, label="worms (wild type)"):
    ws = [wrap(w) for w in W.load_worms(folder)]
    per = keyed(ws, amended=True)
    res = TM.t1(per, share=TM.light_share_amended)
    log(f"T1 (amendment 1) {label}: worms with rows {len(per)}; " + fmt(res))
    if res["S_lo"] > 0.5 and res["hi"][0] < 0 and res["p_L"] < 0.05:
        v = "mostly light"
    elif res["S_hi"] < 0.5 and res["hi"][1] < 0:
        v = "mostly activity"
    else:
        v = "inconclusive"
    log(f"T1 (amendment 1) {label} verdict: {v}")
    return res


def t3():
    ws = [wrap(w) for w in W.load_worms()]
    per = keyed(ws, bins=TM.BINS)
    C = TM.cols(TM.BINS)
    allr = [r for p in per for r in p]
    b = TM.fit(allr, C)
    rng = np.random.default_rng(3)
    bs = np.array([TM.fit([r for i in rng.integers(0, len(per), len(per)) for r in per[i]], C) for _ in range(2000)])
    lo, hi = np.percentile(bs, [5, 95], axis=0)
    names = ["0-2", "2-5", "5-10", "10-20"]
    log("T3 recovery curves (log response; light beyond activity, and per SD of activity), n %d:" % len(allr))
    for kind in ("L", "A"):
        log("  " + kind + ": " + "; ".join(f"{names[i]} min {b[C.index(f'{kind}_{i}')]:+.3f} "
                                           f"[{lo[C.index(f'{kind}_{i}')]:+.3f}, {hi[C.index(f'{kind}_{i}')]:+.3f}]"
                                           for i in range(4)))
    Lb = C.index("L_3")
    Aa, Ab = C.index("A_2"), C.index("A_3")
    Lc, La, Lbb = C.index("L_2"), C.index("A_2"), C.index("A_3")
    diff = ((hi[Lb] < 0 and lo[Aa] <= 0 <= hi[Aa] and lo[Ab] <= 0 <= hi[Ab])
            or (hi[Ab] < 0 and lo[Lc] <= 0 <= hi[Lc] and lo[Lb] <= 0 <= hi[Lb]))
    del La, Lbb
    log(f"T3 verdict: {'different clocks' if diff else 'not distinguished'}")


def t2():
    worms = W.load_worms()
    ws = [wrap(w) for w in worms]
    # class-level response tables per worm (target class -> responding class -> list of responses)
    tabs = []
    for w in ws:
        cl = w["classes"]
        t = defaultdict(lambda: defaultdict(list))
        for k, f, v in w["stims"]:
            for j in range(len(v)):
                if cl[j] and cl[k] and cl[j] != cl[k] and np.isfinite(v[j]):
                    t[cl[k]][cl[j]].append(v[j])
        tabs.append({a: {c: np.mean(x) for c, x in d.items()} for a, d in t.items()})

    def down_set(wi, ck):
        acc = defaultdict(list)
        for oi, tb in enumerate(tabs):
            if oi == wi or ck not in tb:
                continue
            for c, m in tb[ck].items():
                acc[c].append(m)
        cand = [(abs(np.mean(v)), c, np.sign(np.mean(v))) for c, v in acc.items() if len(v) >= 5 and c != ck]
        cand.sort(reverse=True)
        return [(c, s) for _, c, s in cand[:5]]

    per = []
    for wi, (w, wo) in enumerate(zip(ws, worms)):
        cl = w["classes"]
        by = defaultdict(list)
        for k, f, v in w["stims"]:
            by[k].append((f, v))
        first = sorted((s[0][0], k, s[0][1]) for k, s in by.items())

        def down(k, v):
            ds = down_set(wi, cl[k])
            nk = w["near"][k] or set()
            vals = [s * v[j] for c, s in ds for j in range(len(v)) if cl[j] == c and j not in nk and np.isfinite(v[j])]
            return np.mean(vals) if vals else np.nan

        rep_t, rep_d, ctl_t, ctl_d = [], [], [], []
        for k, s in by.items():
            if len(s) < 2 or not cl[k]:
                continue
            s = sorted(s, key=lambda t: t[0])
            (f1, v1), (f2, v2) = s[0], s[1]
            gap = f2 - f1
            tol = max(0.2 * gap, 60)
            cand = []
            for a in range(len(first)):
                for b in range(a + 1, len(first)):
                    fx, kx, vx = first[a]
                    fy, ky, vy = first[b]
                    if kx == ky or abs((fy - fx) - gap) > tol or not cl[kx] or not cl[ky]:
                        continue
                    cand.append((abs(fx - f1), kx, vx, ky, vy))
            cand.sort(key=lambda t: t[0])
            if not cand:
                continue
            rep_t.append((v1[k], v2[k]))
            rep_d.append((down(k, v1), down(k, v2)))
            for _, kx, vx, ky, vy in cand[:5]:
                ctl_t.append((vx[kx], vy[ky]))
                ctl_d.append((down(kx, vx), down(ky, vy)))

        def lr(pairs):
            a = np.array(pairs, float)
            a = a[np.isfinite(a).all(1)]
            if len(a) == 0:
                return np.nan
            m1, m2 = a[:, 0].mean(), a[:, 1].mean()
            return np.log(m2 / m1) if m1 > 0 and m2 > 0 else np.nan
        Dt = lr(rep_t) - lr(ctl_t)
        Dd = lr(rep_d) - lr(ctl_d)
        if np.isfinite(Dt) and np.isfinite(Dd):
            per.append((Dt, Dd, len(rep_t)))
    per = np.array(per)
    rng = np.random.default_rng(2)
    n = len(per)
    bs = np.array([per[rng.integers(0, n, n), :2].mean(0) for _ in range(2000)])
    bd = bs[:, 1] - bs[:, 0]
    m = per[:, :2].mean(0)
    lt, ht = np.percentile(bs[:, 0], [5, 95])
    ld, hd = np.percentile(bs[:, 1], [5, 95])
    lx, hx = np.percentile(bd, [5, 95])
    log(f"T2 worms {n}, repeat pairs {int(per[:, 2].sum())}: D_target {m[0]:+.3f} [{lt:+.3f}, {ht:+.3f}]; "
        f"D_down {m[1]:+.3f} [{ld:+.3f}, {hd:+.3f}]; D_down - D_target {m[1] - m[0]:+.3f} [{lx:+.3f}, {hx:+.3f}]")
    if -0.2 <= lx and hx <= 0.2 and hd < 0:
        v = "passed on"
    elif ld <= 0 <= hd and ld > -0.15 and ht < -0.3:
        v = "not passed on"
    elif hx < -0.2:
        v = "extra downstream loss"
    else:
        v = "inconclusive"
    log(f"T2 verdict: {v}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "calibrate":
        calibrate()
    elif cmd == "validate":
        import json
        validate(json.loads(sys.argv[2]), json.loads(sys.argv[3]))
    elif cmd == "validate1":
        validate_amended()
    elif cmd == "t1":
        t1()
    elif cmd == "t1a":
        t1a()
    elif cmd == "t2":
        t2()
    elif cmd == "t3":
        t3()
    elif cmd == "t4":
        t1a(UNC, "unc-31")
