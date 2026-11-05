"""Three tests on the worm atlas, pre-registered 6 Nov 2026 (README section "Three new tests on
the worm atlas: neuron role, repeat pokes, behavioural state"; the definitions there are the
specification, this is their implementation).

  a2   does watching fail more for some kinds of neuron (sensory, inter, motor)?
  b1   does a worm give the same answer twice (habituation across repeat pokes)?
  b2   does the same poke spread differently in different behavioural states (AVA)?

Usage:  python scripts/run_week1.py a2|b1|b2|b1-lab
Outputs: docs/figures/week1_<test>.txt (and .csv where useful)
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.roles import role  # noqa: E402

FIG = ROOT / "docs" / "figures"
ATLAS = ROOT / "data" / "raw" / "randi2023_wt_npz"
POST, PRE, EXCL = 30, 20, 60          # 15 s, 10 s, 30 s at 0.5 s per frame
BOOT = 2000
ROLES = ["sensory", "inter", "motor", "pharynx"]


# ---------------------------------------------------------------- shared per-worm preparation
class Worm:
    def __init__(self, r, valid_fn=None):
        self.r = r
        X = r.x
        N, T = X.shape
        self.N, self.T = N, T
        valid_fn = valid_fn or (lambda c: role(c) is not None)
        self.valid = np.array([bool(c) and valid_fn(c) for c in r.classes])
        unp = np.ones(T, bool)
        for f in r.all_stim_frames:
            unp[max(f, 0):f + EXCL] = False
        self.unpoked = unp
        with np.errstate(all="ignore"):
            self.mu_u = np.nanmean(np.where(unp, X, np.nan), axis=1)
            sd = np.nanstd(np.where(unp, X, np.nan), axis=1)
        sd[~(sd > 0)] = np.nan
        self.sd = sd
        self.stims = []                                   # (neuron, frame, response vector)
        for k, f in r.stims:
            if not self.valid[k] or f - PRE < 0 or f + POST > T:
                continue
            self.stims.append((k, f, self.change(f)))

    def change(self, f):
        X = self.r.x
        with np.errstate(all="ignore"):
            return (np.nanmean(X[:, f:f + POST], axis=1) - np.nanmean(X[:, f - PRE:f], axis=1)) / self.sd

    def class_resp(self):
        """(stimulated class, responding class) -> mean response over trials and class members."""
        acc = defaultdict(list)
        cl = self.r.classes
        for k, f, v in self.stims:
            for j in range(self.N):
                if j != k and self.valid[j] and cl[j] != cl[k] and np.isfinite(v[j]):
                    acc[(cl[k], cl[j])].append(v[j])
        return {p: float(np.mean(v)) for p, v in acc.items()}

    def class_activity(self):
        X = self.r.x
        with np.errstate(all="ignore"):
            z = (X - np.nanmean(X, axis=1, keepdims=True)) / np.nanstd(X, axis=1, keepdims=True)
        act = defaultdict(list)
        for j, c in enumerate(self.r.classes):
            if self.valid[j]:
                act[c].append(z[j])
        with np.errstate(all="ignore"):
            return {c: np.nanmean(v, axis=0) for c, v in act.items()}


def load_worms():
    rs = sorted(load_pumpprobe_dir(ATLAS), key=lambda r: r.uid)
    return [Worm(r) for r in rs]


def agree(a, b, keys=None, min_pairs=20):
    ks = [k for k in (keys if keys is not None else a) if k in a and k in b]
    if len(ks) < min_pairs:
        return np.nan
    u, v = np.array([a[k] for k in ks]), np.array([b[k] for k in ks])
    if u.std() == 0 or v.std() == 0:
        return np.nan
    return float(np.corrcoef(u, v)[0, 1])


# ---------------------------------------------------------------- A2
def fit_watching(train, ridge=1.0):
    acts = [w.class_activity() for w in train]
    C = sorted({c for a in acts for c in a})
    ix = {c: i for i, c in enumerate(C)}
    XtX, XtY = np.zeros((len(C), len(C))), np.zeros((len(C), len(C)))
    for w, act in zip(train, acts):
        Z = np.zeros((w.T, len(C)))
        seen = np.zeros(len(C), bool)
        for c, a in act.items():
            Z[:, ix[c]] = np.nan_to_num(a)
            seen[ix[c]] = True
        ok = w.unpoked[:-1] & w.unpoked[1:]
        X, Y = Z[:-1][ok], Z[1:][ok]
        XtX += X.T @ X
        XtY += X.T @ (Y * seen)
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


def run_a2(mixed_as_first=False):
    worms = load_worms()
    R = [w.class_resp() for w in worms]
    rl = lambda c: role(c, mixed_as_first)  # noqa: E731
    out, rows = [], []
    shares = {}           # (pool, role) -> bootstrap array of watching share
    point = {}
    rng = np.random.default_rng(6)
    for fold in range(3):
        pool = [i for i in range(len(worms)) if i % 3 == fold]
        train = [worms[i] for i in range(len(worms)) if i % 3 != fold]
        pred = fit_watching(train)
        mean = defaultdict(list)
        for i in range(len(worms)):
            if i % 3 != fold:
                for p, v in R[i].items():
                    mean[p].append(v)
        mean = {p: float(np.mean(v)) for p, v in mean.items()}
        n = len(pool)
        for ro in ROLES:
            keysets = [[p for p in R[i] if rl(p[0]) == ro] for i in pool]
            W = np.full((n, n), np.nan)
            for a in range(n):
                for b in range(a + 1, n):
                    W[a, b] = W[b, a] = agree(R[pool[a]], R[pool[b]], keysets[a])
            wa = np.array([agree(pred, R[i], keysets[k]) for k, i in enumerate(pool)])
            pa = np.array([agree(mean, R[i], keysets[k]) for k, i in enumerate(pool)])
            iu = np.triu_indices(n, 1)
            m_w2w = np.nanmedian(W[iu])
            point[(fold, ro)] = dict(w2w=m_w2w, watch=np.nanmedian(wa), poke=np.nanmedian(pa),
                                     n_pairs=int(np.isfinite(W[iu]).sum()), n_watch=int(np.isfinite(wa).sum()))
            bs = np.empty(BOOT)
            for b in range(BOOT):
                s = rng.integers(0, n, n)
                sub = W[np.ix_(s, s)]
                same = s[:, None] == s[None, :]
                vals = sub[np.triu_indices(n, 1)][~same[np.triu_indices(n, 1)]]
                bs[b] = np.nanmedian(wa[s]) / np.nanmedian(vals)
            shares[(fold, ro)] = bs
            pt = point[(fold, ro)]
            rows.append((fold, ro, pt["w2w"], pt["watch"], pt["poke"], pt["watch"] / pt["w2w"],
                         pt["poke"] / pt["w2w"], pt["n_pairs"], pt["n_watch"]))
    out.append("pool role worm-to-worm watching poke-average watch-share poke-share pairs worms")
    for r in rows:
        out.append(f"{r[0]} {r[1]:8s} {r[2]:.3f} {r[3]:.3f} {r[4]:.3f} {r[5]:.2f} {r[6]:.2f} {r[7]} {r[8]}")
    # decision
    below = 0
    for fold in range(3):
        s = {ro: point[(fold, ro)]["watch"] / point[(fold, ro)]["w2w"] for ro in ROLES}
        below += int(s["sensory"] < s["inter"] and s["sensory"] < s["motor"])
    diff = np.mean([shares[(f, "sensory")] - (shares[(f, "inter")] + shares[(f, "motor")]) / 2 for f in range(3)], axis=0)
    dpt = np.mean([point[(f, "sensory")]["watch"] / point[(f, "sensory")]["w2w"]
                   - (point[(f, "inter")]["watch"] / point[(f, "inter")]["w2w"]
                      + point[(f, "motor")]["watch"] / point[(f, "motor")]["w2w"]) / 2 for f in range(3)])
    lo, hi = np.nanpercentile(diff, [5, 95])
    for ro in ROLES:
        m = np.mean([point[(f, ro)]["watch"] / point[(f, ro)]["w2w"] for f in range(3)])
        b = np.mean([shares[(f, ro)] for f in range(3)], axis=0)
        l2, h2 = np.nanpercentile(b, [5, 95])
        out.append(f"mean watching share, {ro}: {m:.2f} [{l2:.2f}, {h2:.2f}]")
    verdict = ("supported" if below >= 2 and hi < 0 else "refuted" if lo > 0 else "inconclusive")
    out.append(f"pools with sensory share below both inter and motor: {below} of 3")
    out.append(f"sensory share minus mean(inter, motor): {dpt:+.3f} [90%: {lo:+.3f}, {hi:+.3f}]")
    out.append(f"verdict: {verdict}")
    tag = "a2_mixed" if mixed_as_first else "a2"
    (FIG / f"week1_{tag}.txt").write_text("\n".join(out) + "\n")
    print("\n".join(out))


# ---------------------------------------------------------------- B1
def b1_pairs(w, all_valid=False):
    """Repeat pairs and matched control pairs for one worm. Returns lists of (L_echo, L_target)."""
    cl = w.r.classes
    by = defaultdict(list)
    for k, f, v in w.stims:
        by[k].append((f, v))
    first = sorted((s[0][0], k, s[0][1]) for k, s in by.items())        # (frame, neuron, resp)

    def echo(k, v):
        m = w.valid.copy()
        m[k] = False
        if not all_valid:
            m &= np.array([c != cl[k] for c in cl])
        vv = v[m]
        vv = vv[np.isfinite(vv)]
        return np.sqrt(np.mean(vv ** 2)) if len(vv) >= 10 else np.nan

    def ratio(k1, v1, k2, v2):
        e1, e2 = echo(k1, v1), echo(k2, v2)
        le = np.log(e2 / e1) if e1 > 0 and e2 > 0 else np.nan
        a1, a2 = v1[k1], v2[k2]
        la = np.log(a2 / a1) if (np.isfinite(a1) and np.isfinite(a2) and a1 > 0 and a2 > 0) else np.nan
        return le, la

    reps, ctls = [], []
    for k, s in by.items():
        if len(s) < 2:
            continue
        s = sorted(s, key=lambda t: t[0])
        (f1, v1), (f2, v2) = s[0], s[1]
        rep = ratio(k, v1, k, v2)
        gap = f2 - f1
        tol = max(0.2 * gap, 60)
        cand = []
        for a in range(len(first)):
            for b in range(a + 1, len(first)):
                fx, kx, vx = first[a]
                fy, ky, vy = first[b]
                if kx == ky or abs((fy - fx) - gap) > tol:
                    continue
                cand.append((abs(fx - f1), kx, vx, ky, vy))
        cand.sort(key=lambda t: t[0])
        cs = [ratio(kx, vx, ky, vy) for _, kx, vx, ky, vy in cand[:5]]
        if np.isfinite(rep[0]) and any(np.isfinite(c[0]) for c in cs):
            reps.append(rep)
            ctls.append(cs)
    return reps, ctls


def b1_stats(worms, all_valid=False, label="worms"):
    per = []                                  # per worm: (D_echo, D_target or nan, n_rep)
    for w in worms:
        reps, ctls = b1_pairs(w, all_valid)
        if not reps:
            continue
        le_r = np.array([r[0] for r in reps])
        le_c = np.array([c[0] for cs in ctls for c in cs])
        la_r = np.array([r[1] for r in reps])
        la_c = np.array([c[1] for cs in ctls for c in cs])
        de = np.nanmean(le_r) - np.nanmean(le_c)
        da = (np.nanmean(la_r) - np.nanmean(la_c)) if (np.isfinite(la_r).any() and np.isfinite(la_c).any()) else np.nan
        per.append((de, da, len(reps), np.nanmean(le_r), np.nanmean(le_c)))
    per = np.array(per)
    rng = np.random.default_rng(61)
    n = len(per)
    bs = np.array([np.nanmean(per[rng.integers(0, n, n), 0]) for _ in range(BOOT)])
    ba = np.array([np.nanmean(per[rng.integers(0, n, n), 1]) for _ in range(BOOT)])
    D, Da = np.nanmean(per[:, 0]), np.nanmean(per[:, 1])
    lo, hi = np.percentile(bs, [5, 95])
    la, ha = np.nanpercentile(ba, [5, 95])
    verdict = ("habituation" if hi < 0 else "sensitisation" if lo > 0 else
               "no detectable change" if (lo >= -0.10 and hi <= 0.10) else "inconclusive")
    lines = [f"{label}: worms {n}, repeat pairs {int(per[:, 2].sum())}",
             f"  echo: mean L repeats {np.nanmean(per[:, 3]):+.3f}, mean L controls {np.nanmean(per[:, 4]):+.3f}",
             f"  D (echo) {D:+.3f} [90%: {lo:+.3f}, {hi:+.3f}]  -> {verdict}",
             f"  D (target's own response) {Da:+.3f} [90%: {la:+.3f}, {ha:+.3f}]"]
    return lines, per


def run_b1():
    lines, per = b1_stats(load_worms())
    (FIG / "week1_b1.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def run_b1_lab():
    import run_silent_links_test as S
    recs = S.lab_recs(False, 0, 1.0)
    worms = [Worm(r, valid_fn=lambda c: True) for r in recs]
    lines, _ = b1_stats(worms, all_valid=True, label="lab brains (ordinary links, fixed poke strength)")
    with (FIG / "week1_b1.txt").open("a") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


# ---------------------------------------------------------------- B2
def run_b2():
    worms = load_worms()
    pokes = defaultdict(list)              # stimulated class -> list of (state, {resp class: value})
    n_worms = 0
    for w in worms:
        cl = w.r.classes
        ava = [j for j, c in enumerate(cl) if c == "AVA"]
        if not ava:
            continue
        X = w.r.x
        with np.errstate(all="ignore"):
            z = np.nanmean((X[ava] - w.mu_u[ava, None]) / w.sd[ava, None], axis=0)
        if not np.isfinite(z).any():
            continue
        T = w.T
        s10 = np.full(T, np.nan)
        for t in range(PRE, T):
            seg = z[t - PRE:t]
            if np.isfinite(seg).sum() >= PRE // 2:
                s10[t] = np.nanmean(seg)
        # thresholds from unpoked 10 s windows
        okpre = np.array([t >= PRE and w.unpoked[t - PRE:t].all() for t in range(T)])
        ref = s10[okpre & np.isfinite(s10)]
        if len(ref) < 50:
            continue
        q33, q67 = np.percentile(ref, [33, 67])
        state = lambda v: "high" if v > q67 else "low" if v < q33 else None  # noqa: E731
        # pseudo-responses at onsets with no stimulation in the whole window
        pseudo = {"high": [], "low": []}
        for t in range(PRE, T - POST, 5):
            if not w.unpoked[t - PRE:t + POST].all() or not np.isfinite(s10[t]):
                continue
            st = state(s10[t])
            if st:
                pseudo[st].append(w.change(t))
        if len(pseudo["high"]) < 5 or len(pseudo["low"]) < 5:
            continue
        with np.errstate(all="ignore"):
            pm = {k: np.nanmean(np.array(v), axis=0) for k, v in pseudo.items()}
        used = False
        for k, f, v in w.stims:
            if not np.isfinite(s10[f]):
                continue
            st = state(s10[f])
            if not st:
                continue
            corr = v - pm[st]
            acc = defaultdict(list)
            for j in range(w.N):
                if j != k and w.valid[j] and cl[j] not in (cl[k], "AVA") and np.isfinite(corr[j]):
                    acc[cl[j]].append(corr[j])
            pokes[cl[k]].append((st, {c: float(np.mean(vals)) for c, vals in acc.items()}))
            used = True
        n_worms += used
    rng = np.random.default_rng(62)

    def S_of(entries, labels, resp):
        hi = defaultdict(list)
        lo = defaultdict(list)
        for (_, d), lab in zip(entries, labels):
            for c in resp:
                if c in d:
                    (hi if lab == "high" else lo)[c].append(d[c])
        cs = [c for c in resp if hi[c] and lo[c]]
        if len(cs) < 15:
            return np.nan, np.nan
        a = np.array([np.mean(hi[c]) for c in cs])
        b = np.array([np.mean(lo[c]) for c in cs])
        return float(np.corrcoef(a, b)[0, 1]), float(np.mean(np.abs(a)) / np.mean(np.abs(b)))

    rows = []
    for c, entries in sorted(pokes.items()):
        labels = [e[0] for e in entries]
        if labels.count("high") < 3 or labels.count("low") < 3:
            continue
        cnt = defaultdict(lambda: [0, 0])
        for st, d in entries:
            for rc in d:
                cnt[rc][0 if st == "high" else 1] += 1
        resp = [rc for rc, (h, lw) in cnt.items() if h >= 2 and lw >= 2]
        if len(resp) < 15:
            continue
        S, size = S_of(entries, labels, resp)
        if not np.isfinite(S):
            continue
        null = []
        for _ in range(500):
            perm = list(rng.permutation(labels))
            s, _ = S_of(entries, perm, resp)
            null.append(s)
        null = np.array(null)
        rows.append((c, S, np.nanmean(null), S - np.nanmean(null), size, labels.count("high"),
                     labels.count("low"), len(resp)))
    d = np.array([r[3] for r in rows])
    med = float(np.median(d))
    bs = np.array([np.median(d[rng.integers(0, len(d), len(d))]) for _ in range(BOOT)])
    lo, hi = np.percentile(bs, [5, 95])
    flips = np.array([np.median(d * rng.choice([-1, 1], len(d))) for _ in range(10000)])
    p = float((flips <= med).mean())
    verdict = ("supported" if p < 0.05 and med < 0 else
               "refuted (no detectable state dependence)" if (lo <= 0 <= hi and lo > -0.05) else "inconclusive")
    sizes = np.array([r[4] for r in rows])
    lines = [f"worms with AVA used: {n_worms}; stimulated classes scored: {len(rows)}",
             "class S(high,low) mean-null S-minus-null size(high/low) n_high n_low responders"]
    lines += [f"{r[0]:7s} {r[1]:+.3f} {r[2]:+.3f} {r[3]:+.3f} {r[4]:.2f} {r[5]} {r[6]} {r[7]}" for r in rows]
    lines += [f"median S minus null: {med:+.3f} [90%: {lo:+.3f}, {hi:+.3f}], sign-flip p (one-sided) = {p:.4f}",
              f"echo size high/low: median {np.median(sizes):.2f}",
              f"verdict: {verdict}"]
    (FIG / "week1_b2.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"a2": run_a2, "a2-mixed": lambda: run_a2(True), "b1": run_b1, "b1-lab": run_b1_lab, "b2": run_b2}[cmd]()
