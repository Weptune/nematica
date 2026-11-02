"""Is meeting copper like poking ASH?

Two datasets that never met: freely moving worms meeting a copper boundary (the copper set),
and immobilised worms whose neurons were poked one at a time (the atlas). If pokes reveal how
signals really flow, the brain-wide response to a natural sensory event should resemble the
echo of poking the neuron that senses it. ASH is the copper sensor.

  encounter    pooled copper-encounter response per neuron class (Level 6 definition:
               mean over (0, 10 s] minus [-10 s, 0), all encounters of all 27 worms)
  echo(T)      atlas echo of target T: mean over worms of each responder's 0-15 s response
  match(T)     Pearson r between encounter and echo(T) over classes seen on both sides
               (the target itself excluded)

Every target poked in >= 6 worms is ranked by match. Uncertainty: bootstrap over copper worms
and atlas worms together (2000 draws), reporting how often each target ranks first and in the
top 5. Copies: a VAR fitted by watching the copper worms and one fitted by watching the atlas's
unpoked frames are poked at ASH (clamped for 5 s) and their echoes matched to the encounter.

Usage:  python scripts/run_copper_vs_pokes.py
"""

from __future__ import annotations

import csv
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nematica.bench.environment import encounter_responses  # noqa: E402
from nematica.bench.sample import from_recording  # noqa: E402
from nematica.bench.scorecard import set_norm  # noqa: E402
from nematica.data.copper import load_copper_dir  # noqa: E402
from nematica.data.pumpprobe import load_pumpprobe_dir  # noqa: E402
from nematica.systems.causal_models import ClassVAR  # noqa: E402
from run_behaving_pokes import SOURCES, as_pumpprobe  # noqa: E402
from run_poke_budget import echoes  # noqa: E402

MIN_WORMS, MIN_CLASSES, N_BOOT = 6, 12, 2000


def encounter_matrix(samples):
    """per worm: (n_enc, C) responses."""
    return [encounter_responses(s) for s in samples]


def pooled(enc_list):
    rows = [e for e in enc_list if len(e)]
    if not rows:
        return None, None
    allr = np.vstack(rows)
    with np.errstate(invalid="ignore"):
        m = np.nanmean(allr, axis=0)
    n = np.sum([np.isfinite(e).any(axis=0) for e in rows], axis=0)
    return m, n


def echo_mean(worms, classes):
    v = np.array([[d.get(c, np.nan) for c in classes] for d in worms])
    with np.errstate(invalid="ignore"):
        m = np.nanmean(v, axis=0)
    n = np.sum(np.isfinite(v), axis=0)
    return m, n


def match(enc, n_enc, echo, n_echo, classes, target):
    ok = np.isfinite(enc) & np.isfinite(echo) & (n_enc >= 3) & (n_echo >= 3) & (np.array(classes) != target)
    if ok.sum() < MIN_CLASSES or np.std(echo[ok]) == 0:
        return np.nan, int(ok.sum())
    return float(np.corrcoef(enc[ok], echo[ok])[0, 1]), int(ok.sum())


def var_echo(m: ClassVAR, target: str, classes, hold=10, n=30):
    """Deterministic echo of a fitted ClassVAR: target clamped at +1 for `hold` frames."""
    C, p = len(m.classes), m.lags
    A = [m.W[L * C:(L + 1) * C] for L in range(p)]
    rad = m.spectral_radius()
    g = min(1.0, m.max_radius / rad) if rad > 0 else 1.0
    A = [a * g ** (L + 1) for L, a in enumerate(A)]
    i = m.classes.index(target)
    z = np.zeros((C, n + p))
    for t in range(p, n + p):
        z[:, t] = sum(z[:, t - L - 1] @ A[L] for L in range(p))
        if t - p < hold:
            z[i, t] = 1.0
    amp = z[:, p:p + n].mean(axis=1)
    idx = {c: k for k, c in enumerate(m.classes)}
    return np.array([amp[idx[c]] if c in idx else np.nan for c in classes])


def main() -> int:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    set_norm("fluct")
    rng = np.random.default_rng(0)
    cu = load_copper_dir(SOURCES["copper"])
    cnt = Counter(lab.neuron_class for r in cu for lab in r.labelled(2.0).values())
    classes = sorted(c for c, k in cnt.items() if k >= 3)
    samples = [from_recording(r, classes) for r in cu]
    enc = encounter_matrix(samples)
    m_enc, n_enc = pooled(enc)
    print(f"copper: {len(cu)} worms, {sum(len(e) for e in enc)} encounters, {len(classes)} classes", flush=True)

    atlas = load_pumpprobe_dir("data/raw/randi2023_wt_npz")
    ech = echoes(atlas)
    targets = sorted(t for t, w in ech.items() if len(w) >= MIN_WORMS)
    rows = []
    for t in targets:
        e, n = echo_mean(ech[t], classes)
        r, k = match(m_enc, n_enc, e, n, classes, t)
        rows.append({"target": t, "worms": len(ech[t]), "match": round(r, 4) if np.isfinite(r) else "", "classes": k})

    # bootstrap: resample copper worms and, per target, the atlas worms that poked it
    ranks = {t: [] for t in targets}
    vals = {t: [] for t in targets}
    for _ in range(N_BOOT):
        pick = rng.integers(0, len(enc), len(enc))
        mb, nb = pooled([enc[i] for i in pick])
        res = {}
        for t in targets:
            w = ech[t]
            e, n = echo_mean([w[i] for i in rng.integers(0, len(w), len(w))], classes)
            res[t] = match(mb, nb, e, n, classes, t)[0]
        order = sorted((v, t) for t, v in res.items() if np.isfinite(v))[::-1]
        for rank, (v, t) in enumerate(order, 1):
            ranks[t].append(rank)
        for t, v in res.items():
            vals[t].append(v)
    for row in rows:
        t = row["target"]
        rk = np.array(ranks[t])
        v = np.array(vals[t], float)
        row.update({"match_lo": round(float(np.nanpercentile(v, 5)), 4), "match_hi": round(float(np.nanpercentile(v, 95)), 4),
                    "p_rank1": round(float(np.mean(rk == 1)) if rk.size else 0.0, 4),
                    "p_top5": round(float(np.mean(rk <= 5)) if rk.size else 0.0, 4),
                    "median_rank": float(np.median(rk)) if rk.size else ""})
    rows.sort(key=lambda r: -(r["match"] if r["match"] != "" else -9))
    out = Path("docs/figures/copper_vs_pokes.csv")
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} targets ranked by how well their echo matches the copper encounter")
    for i, r in enumerate(rows[:10], 1):
        print(f"  {i:2d} {r['target']:6s} r={r['match']:+.3f} [{r['match_lo']:+.3f},{r['match_hi']:+.3f}] "
              f"rank1 {r['p_rank1']:.0%} top5 {r['p_top5']:.0%} (worms {r['worms']}, classes {r['classes']})")
    ash = next((i for i, r in enumerate(rows, 1) if r["target"] == "ASH"), None)
    print("ASH position:", ash, "of", len(rows))

    # null for the best match: shuffle the encounter vector across classes
    emat = {t: echo_mean(ech[t], classes) for t in targets}
    best_null = []
    for _ in range(2000):
        perm = rng.permutation(len(classes))
        me, ne = m_enc[perm], n_enc[perm]
        best_null.append(np.nanmax([match(me, ne, *emat[t], classes, t)[0] for t in targets]))
    top = rows[0]["match"]
    print(f"best match {top:+.3f}; shuffled-encounter null for the best of {len(targets)}: median "
          f"{np.median(best_null):+.3f}, 95th {np.percentile(best_null, 95):+.3f}, p={np.mean(np.array(best_null) >= top):.3f}")

    # copies poked at ASH
    copies = {}
    cu_pp = [as_pumpprobe(r) for r in cu]
    copies["watch_copper_var3"] = ClassVAR(3, "all").fit([r for i, r in enumerate(cu_pp) if i % 5], [r for i, r in enumerate(cu_pp) if not i % 5])
    copies["watch_atlas_var3"] = ClassVAR(3, "spontaneous").fit([r for i, r in enumerate(atlas) if i % 5], [r for i, r in enumerate(atlas) if not i % 5])
    crow = []
    for name, m in copies.items():
        if "ASH" not in m.classes:
            print(name, "has no ASH class")
            continue
        e = var_echo(m, "ASH", classes)
        r, k = match(m_enc, n_enc, e, np.full(len(classes), 99), classes, "ASH")
        crow.append({"copy": name, "match": round(r, 4), "classes": k})
        print(f"copy {name}: ASH echo vs copper encounter r={r:+.3f} over {k} classes")
    e, n = echo_mean(ech["ASH"], classes)
    real_ash = match(m_enc, n_enc, e, n, classes, "ASH")
    crow.append({"copy": "atlas_ASH_echo (what a poke-trained copy learns)", "match": round(real_ash[0], 4), "classes": real_ash[1]})
    with Path("docs/figures/copper_vs_pokes_copies.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(crow[0]))
        w.writeheader()
        w.writerows(crow)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
