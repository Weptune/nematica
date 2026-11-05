"""Is the worm's individuality about cause and effect? Pre-registered 6 Nov 2026 (README, after
ladder round 5). (a) remove each half's per-responder mean over targets; (b) shuffle target labels.

Usage: python scripts/run_individuality_check.py  ->  docs/figures/individuality_check.txt
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_ladder as LD  # noqa: E402
import run_week1 as W1  # noqa: E402


def halves(worms):
    out = []
    for w in worms:
        st = sorted(w.stims, key=lambda s: s[1])
        out.append((LD.class_resp_subset(w, st[0::2]), LD.class_resp_subset(w, st[1::2])))
    return out


def degeneric(d):
    by = defaultdict(list)
    for (t, r), v in d.items():
        by[r].append(v)
    m = {r: np.mean(v) for r, v in by.items()}
    return {(t, r): v - m[r] for (t, r), v in d.items()}


def shuffled(d, rng):
    ts = sorted({t for t, _ in d})
    perm = dict(zip(ts, rng.permutation(ts)))
    return {(perm[t], r): v for (t, r), v in d.items()}


def excess(H):
    ex = []
    for i, (a, b) in enumerate(H):
        same = W1.agree(a, b)
        if not np.isfinite(same):
            continue
        other = [W1.agree(a, H[j][1]) for j in range(len(H)) if j != i]
        other = [o for o in other if np.isfinite(o)]
        if other:
            ex.append(same - float(np.median(other)))
    return float(np.median(ex)), len(ex)


def excess_shuffled(H, n=100, seed=0):
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        Hs = [(a, shuffled(b, rng)) for a, b in H]
        vals.append(excess(Hs)[0])
    return float(np.mean(vals))


def report(label, worms):
    H = halves(worms)
    e0, n = excess(H)
    ea, _ = excess([(degeneric(a), degeneric(b)) for a, b in H])
    eb = excess_shuffled(H, n=30)
    return [f"{label}: recordings {n}; excess {e0:+.4f}; (a) generic profile removed {ea:+.4f} "
            f"({ea / e0:.0%} kept); (b) targets shuffled {eb:+.4f} ({eb / e0:.0%} kept)"], e0, ea, eb


def main():
    lines = []
    worms = W1.load_worms()
    l, e0, ea, eb = report("worms", worms)
    lines += l
    if ea / e0 < 0.5 and eb / e0 > 0.5:
        v = "mostly generic"
    elif ea / e0 > 0.75 and eb / e0 < 0.25:
        v = "mostly causal"
    else:
        v = "mixed"
    lines.append(f"verdict (worms): {v}")
    for code in ("", "G"):
        recs = LD.variant_recs(code, 0)
        l, *_ = report(f"lab {code or 'base'} (brain 0)", [W1.Worm(r, valid_fn=lambda c: True) for r in recs])
        lines += l
    (ROOT / "docs" / "figures" / "individuality_check.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
