"""Study P calibration (docs/OPTO_SECOND.md). Synthetic mice with known truth, recorded through the real Sst
instruments (classes, units, firing rates, spontaneous time, each mouse's own light schedule), then the
registered analysis, unchanged. No real response is read. Scenarios:
  right    links visible and linear; the pulse-taught copy is the right model
  shared   the same, plus a slow drive that moves every class with the driven cells at rest (watching misleads)
  wrong    every class also has a second set of links that open only when the driven cells are driven hard, with
           their own pattern; pulses mostly teach that pattern, which the slow drive never produces
Each population also gives the size of the decision rule itself: a literal second mouse, its profile blurred
until it agrees with the mouse f times as well as an unblurred one (f = 1, 0.75, 0.5), is scored as a copy.
  nopat    no pattern shared between mice (each mouse has its own links): there is no yardstick
python -I scripts/opto_second_cal.py SCENARIO SEED [SEED ...] [--cs 1.0] [--j 0.5] -> docs/figures/opto/second_cal.jsonl"""
import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from nematica.opto import core, second  # noqa: E402

BIN, TB = core.BIN, core.TEST_BINS
INST = pickle.loads((ROOT / "data/cache/opto_second/instruments.pkl").read_bytes())
OUT = ROOT / ("docs/figures/opto/second_cal2.jsonl" if "--second" in sys.argv else "docs/figures/opto/second_cal.jsonl")


def synth(rng, inst, coupling, A, coupling2, shared, pulse=8.0, cos=0.3, gain=0.5, k2=30.0):
    """As real.synthetic (links visible), with three additions: a second set of links, `coupling2`, that act
    only on the part of the driven cells' activity above 4 resting SDs; a slow shared drive of strength
    `shared`; and a slow drive weak enough (peak about 3 resting SDs) to stay under that threshold while a
    square pulse (8 SDs) does not."""
    cls, K = inst["cls"], inst["n_classes"]
    A = A * (0.85 / max(abs(np.linalg.eigvals(A))))
    rho, sig = 0.9, 0.3
    tag_sd = sig / np.sqrt(1 - rho ** 2)
    thr = 4 * tag_sd
    seg = [int(s / BIN) for s in inst["spont_s"]]
    T_sp = sum(seg)
    t_on, kinds = inst["schedule"]
    onsets = T_sp + 75 + np.round(t_on / BIN).astype(int)
    T = onsets[-1] + 2 * TB
    stim = np.zeros(T)
    hc = np.sin(np.pi * np.arange(TB) / TB)
    for o, k in zip(onsets, kinds):
        if k == 0:
            stim[o] += pulse * tag_sd
        elif k == 1:
            stim[o:o + TB] += cos * tag_sd * hc
    z = np.zeros((T, K)); tau = np.zeros(T); g = np.zeros(T)
    e = rng.normal(0, sig, (T, K)); et = rng.normal(0, sig, T); eg = rng.normal(0, 0.06, T)
    wg = 1 + 0.3 * rng.normal(0, 1, K)
    for t in range(1, T):
        g[t] = 0.995 * g[t - 1] + eg[t]
        tau[t] = rho * tau[t - 1] + et[t] + stim[t] + 0.5 * shared * g[t]
        d = tau[t - 1]
        z[t] = A @ z[t - 1] + e[t] + 0.25 * (coupling * d + coupling2 * (max(0.0, d - thr) * k2)) + 0.5 * shared * wg * g[t]
    zs = z / z[:T_sp].std(0)
    taus = tau / tau[:T_sp].std()
    lat = np.minimum(np.where(cls[None, :] == -1, taus[:, None], zs[:, np.clip(cls, 0, None)]), 6.0)
    base = np.maximum(inst["rate_hz"], 0.05) * BIN
    counts = rng.poisson(base * np.exp(gain * lat - gain ** 2 / 2)).astype(np.float32)
    edges = np.r_[0, np.cumsum(seg)]
    return {"spont": [counts[a:b] for a, b in zip(edges[:-1], edges[1:])], "block": counts[T_sp:],
            "on_train": onsets[kinds == 0] - T_sp, "on_test": onsets[kinds == 1] - T_sp,
            "on_train2": onsets[kinds == 2] - T_sp, "cls": cls, "n_classes": K}


def rule_size(M, rng, draws=200):
    """How often the two tests fire when the 'copy' is a second mouse's own profile, blurred to agree f times
    as well: f = 1 is a literal second mouse, 0.75 sits exactly on the margin, 0.5 is clearly worse."""
    ms = list(M); pair = {}
    for a in ms:
        for b in ms:
            if a != b:
                S = [k for k in M[b]["names"] if k in M[a]["names"]]
                if len(S) >= second.MIN_SHARED:
                    pair[a, b] = ([M[a]["names"].index(k) for k in S], [M[b]["names"].index(k) for k in S])
    Bm = {k: core.agree(M[k[0]]["prof"][v[0]], M[k[1]]["prof"][v[1]]) for k, v in pair.items()}
    out = {}
    cons = {a: second.consensus(M, a) for a in ms}
    for f in (1.0, 0.75, 0.5):
        like = worse = worse02 = worse01 = alike = alike02 = alike01 = 0
        for _ in range(draws):
            dl, dw, da = [], [], []
            for a in ms:
                part = [b for b in ms if (a, b) in pair and np.isfinite(Bm[a, b])]
                if len(part) < second.MIN_PARTNERS:
                    continue
                h = part[int(rng.integers(len(part)))]
                ia, ib = pair[a, h]
                x = M[h]["prof"][ib]
                n = core.agree(x + rng.normal(0, np.sqrt(1 / f ** 2 - 1) * x.std(), len(x)), M[a]["prof"][ia])
                br = np.median([Bm[a, b] for b in part if b != h])
                dl.append(n - second.MARGIN * br); dw.append(n - br)
                ok = np.isfinite(cons[a])                    # the same for the average of the other mice, blurred
                if ok.sum() >= second.MIN_SHARED:
                    y = cons[a][ok]
                    da.append(core.agree(y + rng.normal(0, np.sqrt(1 / f ** 2 - 1) * y.std(), len(y)), M[a]["prof"][ok]) - second.MARGIN * core.agree(y, M[a]["prof"][ok]))
            pw = second._w(dw, "less")
            like += second._w(dl, "greater") < 0.05; worse += pw < 0.05; worse02 += pw < 0.02; worse01 += pw < 0.01
            pa = second._w(da, "greater")
            alike += pa < 0.05; alike02 += pa < 0.02; alike01 += pa < 0.01
        out[str(f)] = {"like": like / draws, "worse": worse / draws, "worse_p02": worse02 / draws, "worse_p01": worse01 / draws, "like_average": alike / draws, "like_average_p02": alike02 / draws,
                       "like_average_p01": alike01 / draws}
    return out


def population(scenario, seed, cs, j, line="Sst"):
    rng = np.random.default_rng([20261121, seed, {"right": 1, "shared": 2, "wrong": 3, "nopat": 4}[scenario]])
    mice = [m for m in INST if INST[m]["line"] == line]
    U = sorted({k for m in mice for k in INST[m]["names"]})
    ix = {k: i for i, k in enumerate(U)}
    gc = rng.normal(-1.0, 0.7, len(U))                     # the species' links from the driven cells: most lower activity
    GA = rng.normal(0, 1, (len(U), len(U)))
    gc2 = rng.normal(-1.0, 0.7, len(U))                    # for `wrong`: the links that open only under a hard drive
    M = {}
    for m in mice:
        inst = INST[m]
        i = [ix[k] for k in inst["names"]]
        K = len(i)
        c = rng.normal(-1.0, 0.7, K) if scenario == "nopat" else gc[i] + j * 0.7 * rng.normal(0, 1, K)
        A = GA[np.ix_(i, i)] + j * rng.normal(0, 1, (K, K))
        c2 = cs * (gc2[i] + j * 0.7 * rng.normal(0, 1, K)) if scenario == "wrong" else np.zeros(K)
        rec = synth(rng, inst, cs * c, A, c2, 1.0 if scenario == "shared" else 0.0)
        M[m] = {"line": line, "names": inst["names"], **second.answers(rec)}
    S = second.pairwise(M, np.random.default_rng(seed))
    o = second.claims(S, line)
    return {"scenario": scenario, "seed": seed, "cs": cs, "j": j, **o, "rule_size": rule_size(M, np.random.default_rng(seed + 7)), "verdict_P": second.verdict(o, "P"), "verdict_W": second.verdict(o, "W"),
            "verdict_X": second.verdict(o, "X")}


if __name__ == "__main__":
    a = sys.argv[1:]
    cs = float(a[a.index("--cs") + 1]) if "--cs" in a else 1.0
    j = float(a[a.index("--j") + 1]) if "--j" in a else 0.5
    seeds = [int(x) for x in a[1:] if x.lstrip("-").isdigit() and a[a.index(x) - 1] not in ("--cs", "--j")]
    for s in seeds:
        r = population(a[0], s, cs, j)
        with OUT.open("a") as f:
            f.write(json.dumps(r, default=float) + "\n")
        print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k not in ("median", "rule_size")}, default=float), flush=True)
        print("  medians", {k: round(v, 3) for k, v in r["median"].items()}, "rule size", r["rule_size"], flush=True)
