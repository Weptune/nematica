"""Individual routing (pre-registered 8 Nov 2026, README "Do worms with the same wiring route signals
differently, and do neuropeptides carry it?").

Usage:  python scripts/run_individuality.py calib|q1|q2|q3
Output: docs/figures/individuality.txt (appended), docs/figures/individuality_q3.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica import individuality as IV  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402

OUT = ROOT / "docs" / "figures" / "individuality.txt"
WT = ROOT / "data" / "raw" / "randi2023_wt_npz"
UNC = ROOT / "data" / "raw" / "randi2023_unc31_npz"
POS = ROOT / "data" / "derived" / "positions"


def log(s):
    print(s, flush=True)
    with OUT.open("a") as fh:
        fh.write(s + "\n")


def near_of(rec):
    import run_tiring_source as TS
    fp = POS / f"{rec.uid}.npz"
    pos = np.load(fp)["pos"]
    if pos.shape[0] != rec.x.shape[0]:
        return None
    return TS.nearest3(pos)


def halves(stims, split):
    if split == "alternate":
        return stims[0::2], stims[1::2]
    h = len(stims) // 2
    return stims[:h], stims[h:]


def build(recs, nears, split="alternate", exclude=True):
    A, B = [], []
    for r, nr in zip(recs, nears):
        a, b = halves(r.stims, split)
        A.append(IV.parts(IV.half_map(r, a, nr if exclude else None)))
        B.append(IV.parts(IV.half_map(r, b, nr if exclude else None)))
    return A, B


def summarise(label, A, B, seed=0, boot=2000):
    rng = np.random.default_rng(seed)
    res = {}
    for part in IV.PARTS:
        S = IV.agreement_matrix(A, B, part)
        ex = IV.excess(S)
        ex = ex[np.isfinite(ex)]
        bs = [np.median(ex[rng.integers(0, len(ex), len(ex))]) for _ in range(boot)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        w = np.nanmedian(np.diag(S))
        b = np.nanmedian(S[~np.eye(len(S), dtype=bool)])
        res[part] = (float(np.median(ex)), lo, hi, len(ex), w, b, float(np.mean(ex > 0)))
        log(f"  {label} {part:9s}: excess {np.median(ex):+.4f} [95%: {lo:+.4f}, {hi:+.4f}]; within {w:.3f}, between {b:.3f}; "
            f"worms {len(ex)}, share > 0: {np.mean(ex > 0):.2f}")
    return res


# ---------------------------------------------------------------- calibration on lab networks
def lab_recs(sigma, n_ind=60, spread=0.3, seed=0):
    import run_ladder as LD
    from nematica import annlab as L
    br0 = L.make_brain(rho=1.3, share=0.0, tau=90.0, seed=seed, q=0.2)
    hidden = L.design(br0.n, np.random.default_rng(200))
    rng = np.random.default_rng(7)
    recs, nears = [], []
    saved = LD.NEIGH
    try:
        for i in range(n_ind):
            g = np.random.default_rng(5000 + i)
            neigh = np.array([g.choice([u for u in range(br0.n) if u != v], size=2, replace=False) for v in range(br0.n)])
            LD.NEIGH = neigh
            ind = L.individual(br0, sigma, 1000 + i)
            obs = (rng.random(br0.n) < 0.5) & ~hidden
            targets = np.flatnonzero(obs)
            kicks = {f: int(rng.choice(targets)) for f in range(LD.LEAD, L.FRAMES - L.WIN, L.EVERY)}
            scale = {f: 1.0 for f in kicks}
            y = LD.record(ind, rng, obs, kicks, scale, spread)
            rec = L.as_pumpprobe(y, obs, kicks, f"ind{i:03d}")
            units = [int(nm[1:]) for nm in rec.names]
            p_of = {u: p for p, u in enumerate(units)}
            nears.append([{p_of[v] for v in neigh[u] if v in p_of} | {p for p, w in enumerate(units) if u in neigh[w]}
                          for u in units])
            recs.append(rec)
    finally:
        LD.NEIGH = saved
    return recs, nears


def calib():
    log("CALIBRATION (pre-registered: (i) identical individuals with per-individual spillover, excluded: routing interval includes 0; "
        "(ii) connections varying 30%: routing interval above 0)")
    r0, n0 = lab_recs(0.0)
    A, B = build(r0, n0, exclude=True)
    i_res = summarise("(i) sigma 0, spillover excluded", A, B)
    A, B = build(r0, n0, exclude=False)
    summarise("(iii) sigma 0, spillover NOT excluded", A, B)
    r1, n1 = lab_recs(0.3)
    A, B = build(r1, n1, exclude=True)
    ii_res = summarise("(ii) sigma 0.3, spillover excluded", A, B)
    ok_i = i_res["routing"][1] <= 0 <= i_res["routing"][2]
    ok_ii = ii_res["routing"][1] > 0
    log(f"CALIBRATION result: (i) {'pass' if ok_i else 'FAIL'}, (ii) {'pass' if ok_ii else 'FAIL'} -> {'PASS' if ok_i and ok_ii else 'FAIL'}")


# ---------------------------------------------------------------- worms
def worm_set(folder, min_stims=20):
    recs = [r for r in sorted(load_pumpprobe_dir(folder), key=lambda r: r.uid) if len(r.stims) >= min_stims]
    pairs = [(r, near_of(r)) for r in recs]
    pairs = [(r, n) for r, n in pairs if n is not None]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def q1():
    recs, nears = worm_set(WT)
    log(f"Q1 wild type, {len(recs)} worms with >= 20 pokes and positions")
    for split in ("alternate", "time"):
        A, B = build(recs, nears, split=split, exclude=True)
        res = summarise(f"WT {split} (excluded)", A, B)
        if split == "alternate":
            r = res["routing"]
            raw = res["raw"]
            if r[1] > 0:
                v = "individual routing"
            elif raw[1] > 0 and r[1] <= 0 <= r[2] and r[2] < 0.02:
                v = "individuality only in per-neuron sensitivity or drive"
            else:
                v = "inconclusive"
            log(f"Q1 verdict (alternate, routing): {v}")
    A, B = build(recs, nears, split="alternate", exclude=False)
    summarise("WT alternate, NOT excluded (for comparison)", A, B)


def subsample_stims(r, n, rng):
    idx = np.sort(rng.choice(len(r.stims), n, replace=False))
    import dataclasses
    return dataclasses.replace(r, stims=[r.stims[i] for i in idx])


def index_for(recs, nears, rng, draws=20, n_pokes=40):
    vals = []
    for _ in range(draws):
        rs = [subsample_stims(r, n_pokes, rng) for r in recs]
        A, B = build(rs, nears)
        vals.append(IV.index_I(IV.agreement_matrix(A, B, "routing")))
    return float(np.nanmean(vals))


def q2(n_sub=1000, draws=20):
    wt, wn = worm_set(WT, 40)
    un, nn = worm_set(UNC, 40)
    rng = np.random.default_rng(11)
    I_unc = index_for(un, nn, rng, draws)
    log(f"Q2: unc-31 worms {len(un)} (>= 40 pokes), I (routing) = {I_unc:.4f}")
    # Wild-type distribution: precompute each worm's 20 half-map draws once, then subset worms.
    pre = []
    for d in range(draws):
        rs = [subsample_stims(r, 40, rng) for r in wt]
        pre.append(build(rs, wn))
    k = len(un)
    Is = []
    for s in range(n_sub):
        pick = rng.choice(len(wt), k, replace=False)
        v = []
        for A, B in pre:
            v.append(IV.index_I(IV.agreement_matrix([A[i] for i in pick], [B[i] for i in pick], "routing")))
        Is.append(np.nanmean(v))
        if s % 100 == 99:
            print("  subsets", s + 1, flush=True)
    Is = np.array(Is)
    p5, p25, p50 = np.nanpercentile(Is, [5, 25, 50])
    pct = float(np.mean(Is <= I_unc))
    log(f"Q2: wild-type subsets of {k} worms ({n_sub}): median I {p50:.4f}, 5th pct {p5:.4f}, 25th pct {p25:.4f}; unc-31 at percentile {pct:.3f}")
    v = "peptide-dependent" if I_unc < p5 else ("not detectably peptide-dependent" if I_unc > p25 else "inconclusive")
    log(f"Q2 verdict: {v}")


def q3(min_worms=8, boot=2000):
    from nematica.systems.wiring import class_wiring
    recs, nears = worm_set(WT)
    A, B = build(recs, nears)
    per_pair = {}
    for a, b in zip(A, B):
        for k in set(a["routing"]) & set(b["routing"]):
            per_pair.setdefault(k, []).append((a["routing"][k], b["routing"][k]))
    rows = []
    classes = sorted({c for k in per_pair for c in k})
    W = class_wiring(classes)
    idx = {c: i for i, c in enumerate(classes)}
    for (i, j), v in per_pair.items():
        if len(v) < min_worms:
            continue
        v = np.array(v)
        m = v.mean(1)
        within = np.mean((v[:, 0] - v[:, 1]) ** 2) / 2
        total = np.var(np.concatenate([v[:, 0], v[:, 1]]), ddof=1)
        between = np.var(m, ddof=1) - within / 2          # worm variance component (can be < 0 by noise)
        if total > 0 and within + between != 0:
            wired = bool(W[idx[j], idx[i]] or W[idx[i], idx[j]])
            rows.append({"source": i, "responder": j, "worms": len(v), "wired": wired,
                         "individual_share": round(float(between / (between + within)), 4)})
    with (ROOT / "docs" / "figures" / "individuality_q3.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    x = np.array([r["individual_share"] for r in rows if not r["wired"]])
    y = np.array([r["individual_share"] for r in rows if r["wired"]])
    rng = np.random.default_rng(3)
    bs = [np.median(x[rng.integers(0, len(x), len(x))]) - np.median(y[rng.integers(0, len(y), len(y))]) for _ in range(boot)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    log(f"Q3: pairs measured in >= {min_worms} worms: unwired {len(x)} (median individual share {np.median(x):+.4f}), "
        f"wired {len(y)} ({np.median(y):+.4f}); unwired minus wired {np.median(x) - np.median(y):+.4f} [95%: {lo:+.4f}, {hi:+.4f}]")
    log(f"Q3 verdict: {'supported' if lo > 0 else 'not supported'}")




# ---------------------------------------------------------------- amendment 1: Q0, does spillover shape echoes?
def rows_and_neighbours(recs, nears, nbr_classes):
    """Per worm: {stim class: {resp class: amp}} from all pokes, and {stim class: set of neighbour classes}."""
    out = []
    for r, nr, nc in zip(recs, nears, nbr_classes):
        m = IV.half_map(r, r.stims, nr)
        rows = {}
        for (ci, cj), a in m.items():
            rows.setdefault(ci, {})[cj] = a
        out.append((rows, nc))
    return out


def triples(data, min_resp=8):
    T = []
    n = len(data)
    for a in range(n):
        ra, na = data[a]
        for b in range(a + 1, n):
            rb, nb = data[b]
            for ci in set(ra) & set(rb):
                if ci not in na or ci not in nb or not (na[ci] or nb[ci]):
                    continue
                x, y = ra[ci], rb[ci]
                ks = [k for k in x if k in y]
                if len(ks) < min_resp:
                    continue
                u, v = np.array([x[k] for k in ks]), np.array([y[k] for k in ks])
                if u.std() == 0 or v.std() == 0:
                    continue
                ov = len(na[ci] & nb[ci]) / len(na[ci] | nb[ci])
                T.append((a, b, ci, float(np.corrcoef(u, v)[0, 1]), ov))
    return T


def slope_fe(T, w=None):
    cls = {}
    for t_i, t in enumerate(T):
        cls.setdefault(t[2], []).append(t_i)
    r = np.array([t[3] for t in T]); o = np.array([t[4] for t in T])
    w = np.ones(len(T)) if w is None else w
    rd, od = r.copy(), o.copy()
    for idx in cls.values():
        idx = np.array(idx)
        ww = w[idx]
        if ww.sum() == 0:
            continue
        rd[idx] -= np.average(r[idx], weights=ww); od[idx] -= np.average(o[idx], weights=ww)
    den = np.sum(w * od * od)
    return float(np.sum(w * od * rd) / den) if den > 0 else np.nan


def q0_stats(T, n_worms, perm=2000, boot=1000, seed=0):
    rng = np.random.default_rng(seed)
    s0 = slope_fe(T)
    cls = {}
    for t_i, t in enumerate(T):
        cls.setdefault(t[2], []).append(t_i)
    cnt = 0
    for _ in range(perm):
        Tp = list(T)
        for idx in cls.values():
            ovs = [T[i][4] for i in idx]
            sh = rng.permutation(ovs)
            for i, o in zip(idx, sh):
                Tp[i] = T[i][:4] + (o,)
        if slope_fe(Tp) >= s0:
            cnt += 1
    p = (cnt + 1) / (perm + 1)
    bs = []
    A = np.array([t[0] for t in T]); B = np.array([t[1] for t in T])
    for _ in range(boot):
        c = np.bincount(rng.integers(0, n_worms, n_worms), minlength=n_worms)
        bs.append(slope_fe(T, w=(c[A] * c[B]).astype(float)))
    lo, hi = np.nanpercentile(bs, [2.5, 97.5])
    r = np.array([t[3] for t in T]); o = np.array([t[4] for t in T])
    return s0, p, lo, hi, len(T), float(np.mean(o > 0)), float(np.mean(r[o > 0]) - np.mean(r[o == 0])) if (o > 0).any() and (o == 0).any() else np.nan


def lab_ring(spread, n_ind=60, seed=0):
    import run_ladder as LD
    br0 = __import__("nematica.annlab", fromlist=["x"]).make_brain(rho=1.3, share=0.0, tau=90.0, seed=seed, q=0.2)
    from nematica import annlab as L
    n = br0.n
    hidden = L.design(n, np.random.default_rng(200))
    rng = np.random.default_rng(7)
    recs, nears, nbrc = [], [], []
    saved = LD.NEIGH
    try:
        for i in range(n_ind):
            g = np.random.default_rng(5000 + i)
            neigh = np.array([g.choice([(v + d) % n for d in (-3, -2, -1, 1, 2, 3)], size=2, replace=False) for v in range(n)])
            LD.NEIGH = neigh
            ind = L.individual(br0, 0.0, 1000 + i)
            obs = (rng.random(n) < 0.5) & ~hidden
            targets = np.flatnonzero(obs)
            kicks = {f: int(rng.choice(targets)) for f in range(LD.LEAD, L.FRAMES - L.WIN, L.EVERY)}
            y = LD.record(ind, rng, obs, kicks, {f: 1.0 for f in kicks}, spread)
            rec = L.as_pumpprobe(y, obs, kicks, f"ind{i:03d}")
            units = [int(nm[1:]) for nm in rec.names]
            p_of = {u: p for p, u in enumerate(units)}
            nears.append([{p_of[v] for v in neigh[u] if v in p_of} | {p for p, w in enumerate(units) if u in neigh[w]} for u in units])
            nbrc.append({f"U{u:03d}": {f"U{v:03d}" for v in neigh[u]} for u in units})
            recs.append(rec)
    finally:
        LD.NEIGH = saved
    return recs, nears, nbrc


def calib0():
    log("Q0 CALIBRATION (amendment 1: ring neighbours, identical wiring; with spillover slope > 0 and p < 0.01; without, p > 0.1)")
    res = {}
    for spread in (0.3, 0.0):
        recs, nears, nbrc = lab_ring(spread)
        T = triples(rows_and_neighbours(recs, nears, nbrc))
        s, p, lo, hi, n, frac, diff = q0_stats(T, len(recs), perm=1000, boot=300)
        res[spread] = (s, p)
        log(f"  lab spillover {spread}: slope {s:+.4f} [95%: {lo:+.4f}, {hi:+.4f}], p {p:.4f}; triples {n}, share with overlap {frac:.3f}; "
            f"agreement with overlap minus without {diff:+.4f}")
    ok = res[0.3][0] > 0 and res[0.3][1] < 0.01 and res[0.0][1] > 0.1
    log(f"Q0 CALIBRATION result: {'PASS' if ok else 'FAIL'} (lab spillover slope {res[0.3][0]:+.4f})")


def q0(lab_slope):
    import run_tiring_source as TS
    recs, nears = worm_set(WT)
    nbrc = []
    for r, nr in zip(recs, nears):
        d = {}
        for k, _ in r.stims:
            ci = r.classes[k]
            if not ci or nr[k] is None:
                continue
            d.setdefault(ci, set()).update(r.classes[j] for j in nr[k] if r.classes[j])
        nbrc.append(d)
    T = triples(rows_and_neighbours(recs, nears, nbrc))
    s, p, lo, hi, n, frac, diff = q0_stats(T, len(recs))
    log(f"Q0 worms ({len(recs)}): slope {s:+.4f} [95%: {lo:+.4f}, {hi:+.4f}], p {p:.4f}; triples {n}, share with overlap {frac:.3f}; "
        f"agreement with overlap minus without {diff:+.4f}")
    if s > 0 and p < 0.01:
        v = "spillover shapes echoes"
    elif p > 0.1 and hi < lab_slope / 3:
        v = "no detectable effect"
    else:
        v = "inconclusive"
    log(f"Q0 verdict: {v}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "q0":
        q0(float(sys.argv[2]))
    else:
        {"calib": calib, "q1": q1, "q2": q2, "q3": q3, "calib0": calib0}[cmd]()
