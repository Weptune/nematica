"""Study W calibration of the split (docs/OPTO_WANING.md). A known effect is planted into each real mouse's
own spontaneous recording, where no light was shown: 150 pretend 1 s trials, 1.9 s apart, with the mouse's
own sequence of light levels. Driven units gain spikes; each class of neighbours is pushed down or up by its
own link; the driven answer falls over the block to `fd` times its start and the links to `fn` times theirs.
Then waning.split, unchanged. Nothing recorded under light is read.

Rows added by the review before the freeze: the neighbours' resting rate drifting over the block with nothing
fading (`drift`: rate at the end over rate at the start), links that push by a fixed number of spikes instead
of a fixed fraction (`additive`), and the background played backwards (`reversed`).

python -I scripts/opto_waning_cal2.py --part 0 &  python -I scripts/opto_waning_cal2.py --part 1   (half the mice each)
python -I scripts/opto_waning_cal2.py --merge  -> docs/figures/opto/waning_cal2.json"""
import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from nematica.opto import core, real, waning  # noqa: E402

V = json.loads((ROOT / "docs/figures/opto/vbn_result.json").read_text())
CACHE = ROOT / "data/cache/opto_waning"
REPS = 6
HC = np.sin(np.pi * (np.arange(core.TEST_BINS) + 0.5) / core.TEST_BINS)
# (fd, fn, link, drift, additive, reversed)
SCEN = [(fd, fn, lk, 1.0, False, False) for lk in (0.12, 0.25, 0.5) for fd, fn in ((1.0, 1.0), (0.6, 1.0), (1.0, 0.8), (1.0, 0.6), (0.6, 0.6))]
SCEN += [(1.0, 1.0, 0.25, 0.8, False, False), (1.0, 1.0, 0.25, 1.2, False, False), (1.0, 0.8, 0.25, 1.2, False, False),
         (1.0, 1.0, 0.25, 0.8, True, False), (1.0, 1.0, 0.25, 1.2, True, False), (1.0, 0.8, 0.25, 1.0, True, False),
         (1.0, 1.0, 0.25, 1.0, False, True)]


def plant(rng, base, on, level, cls, n, rate, fd, fn, link, drift=1.0, additive=False):
    Y = base.copy()
    nb = cls >= 0
    if drift != 1.0:                                                   # the neighbours' resting rate drifts; nothing else changes
        a, b = on[0] - 20, on[-1] + core.TEST_BINS                     # (thinned only where a trial reads it: its baseline and its 1 s)
        p = np.linspace(1.0, drift, b - a) if drift < 1 else np.linspace(1 / drift, 1.0, b - a)
        for o in on:
            w = Y[o - real.BASE_BINS:o + core.TEST_BINS]
            w[:, nb] = rng.binomial(w[:, nb].astype(np.int64), p[o - real.BASE_BINS - a:o + core.TEST_BINS - a, None]).astype(np.float32)
    place = np.linspace(0, 1, len(on))
    c = np.clip(rng.normal(-0.6 * link, link, n), -0.95, 2.0)          # most classes fall, some rise
    per = np.where(nb, c[np.clip(cls, 0, None)], 0.0)
    drv = cls == -1
    for o, lv, p in zip(on, level, place):
        a = lv * (1 - (1 - fd) * p)                                    # the driven units' answer on this trial
        g = 1 - (1 - fn) * p                                           # what is left of the links
        e = per[None, :] * a * g * HC[:, None]
        w = Y[o:o + core.TEST_BINS]
        if additive:                                                   # a fixed number of spikes, whatever the rate is now
            k = rng.poisson(np.abs(e) * rate[None, :] * real.BIN)
            w = np.where(e >= 0, w + k, np.maximum(w - k, 0)).astype(np.float32)
        else:                                                          # a fixed fraction of the spikes there are now
            w = rng.binomial(w.astype(np.int64), np.broadcast_to(np.clip(1 + e, 0, 1), w.shape)).astype(np.float32)
            w += rng.poisson(np.clip(e, 0, None) * rate[None, :] * real.BIN)
        w[:, drv] += rng.poisson(np.broadcast_to(8 * a * HC[:, None] * real.BIN, (core.TEST_BINS, int(drv.sum()))))
        Y[o:o + core.TEST_BINS] = w
    return Y


def part(k):
    CACHE.mkdir(parents=True, exist_ok=True)
    for j, m in enumerate(V["mice"]):
        if j % 2 != k or (CACHE / f"cal2_{m}.pkl").exists():           # one file per mouse, so a stopped run picks up where it was
            continue
        rng = np.random.default_rng([20261121, j])
        rows = {}
        d = real.load(m)
        t = real.tag(d)
        cls, names = real.classes(d, t)
        rec = real.recording(d, cls, len(names))
        ok = real.spont_sd(rec["spont"]) > 0
        rate = np.maximum(d["firing_rate"][cls != -2][ok], 0.05)
        rec = waning.live(rec)
        if rec is None:
            print(m, "left out", flush=True); continue
        sd = real.spont_sd(rec["spont"])
        base = max(rec["spont"], key=len)
        hc = real.half_cosine(d)
        level = d["opto_level"][hc][np.argsort(d["opto_start"][hc])]
        on = 20 + 95 * np.arange(len(level))
        if on[-1] + core.TEST_BINS > len(base):
            print(m, "spontaneous block too short", flush=True); continue
        for sc in SCEN:
            fd, fn, lk, drift, add, rev = sc
            for r in range(REPS):
                Y = plant(rng, base[::-1].copy() if rev else base, on, level, rec["cls"], rec["n_classes"], rate, fd, fn, lk, drift, add)
                rows[(m, sc, r)] = waning.split(Y, on, level, rec["cls"], rec["n_classes"], sd)
        pickle.dump(rows, open(CACHE / f"cal2_{m}.pkl", "wb"))
        print(j + 1, m, flush=True)


def merge():
    rows = {}
    for m in V["mice"]:
        rows.update(pickle.load(open(CACHE / f"cal2_{m}.pkl", "rb")))
    mice = sorted({m for m, _, _ in rows})
    inside = lambda iv, lo, hi: iv[0] >= lo and iv[1] <= hi          # noqa: E731
    out = []
    for sc in SCEN:
        for r in range(REPS):
            S = [rows[(m, sc, r)] for m in mice]
            col = lambda key: np.array([s[key] for s in S], float)   # noqa: E731
            by, bf, rest = col("beyond"), col("beyond_frac"), col("rest")
            pa, pf = waning.sign_p(1 - by), waning.sign_p(1 - bf)
            ia, if_, ir = waning.boot(by, seed=r), waning.boot(bf, seed=r), waning.boot(rest, seed=r)
            faster = pa < 0.05 and pf < 0.05
            out.append({"fd": sc[0], "fn": sc[1], "link": sc[2], "drift": sc[3], "additive": sc[4], "reversed": sc[5], "mice": len(S),
                        "undefined": int((~np.isfinite(by)).sum()), "undefined_frac": int((~np.isfinite(bf)).sum()), "half": float(np.nanmedian(col("half"))),
                        "driven": float(np.nanmedian(col("driven"))), "net": float(np.nanmedian(col("net"))), "net_frac": float(np.nanmedian(col("net_frac"))),
                        "beyond": float(np.nanmedian(by)), "beyond_frac": float(np.nanmedian(bf)), "rest": float(np.nanmedian(rest)),
                        "p_beyond": pa, "p_beyond_frac": pf, "faster": bool(faster), "one_only": bool((pa < 0.05) != (pf < 0.05)),
                        "follows": bool(not (pa < 0.05 or pf < 0.05) and inside(ia, 0.8, 1.25) and inside(if_, 0.8, 1.25) and inside(ir, 0.9, 1.1))})
    (ROOT / "docs/figures/opto/waning_cal2.json").write_text(json.dumps(out, indent=1))
    tl = lambda f: (f + (1 - f) / 6) / (1 - (1 - f) / 6)             # noqa: E731  late third over early third of a linear fall to f
    for sc in SCEN:
        g = [o for o in out if (o["fd"], o["fn"], o["link"], o["drift"], o["additive"], o["reversed"]) == sc]
        rng_ = lambda k: f"{np.median([o[k] for o in g]):.2f} [{min(o[k] for o in g):.2f}, {max(o[k] for o in g):.2f}]"   # noqa: E731
        print(f"driven {sc[0]} links {sc[1]} link {sc[2]} drift {sc[3]} {'add' if sc[4] else 'mul'}{' rev' if sc[5] else ''}: true beyond {tl(sc[1]):.2f} | half {np.median([o['half'] for o in g]):.2f}"
              f" | beyond {rng_('beyond')} frac {rng_('beyond_frac')} rest {np.median([o['rest'] for o in g]):.2f} | faster {sum(o['faster'] for o in g)} one only {sum(o['one_only'] for o in g)} follows {sum(o['follows'] for o in g)} of {len(g)}"
              f" | undefined {sum(o['undefined'] for o in g)}/{sum(o['undefined_frac'] for o in g)}")


if __name__ == "__main__":
    if "--merge" in sys.argv:
        merge()
    else:
        part(int(sys.argv[sys.argv.index("--part") + 1]))
