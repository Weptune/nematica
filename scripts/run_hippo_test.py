"""Mouse hippocampus test, pre-registered (README, "Beyond the worm: mouse hippocampus").

Question: a copy built only by WATCHING a session's untouched activity; does it predict how the
other recorded neurons respond when one interneuron is POKED (optogenetically stimulated)?

Per session (data/derived/hippo/<id>/, made by hippo_stream.py):
  traces   Fc = F - 0.7 Fneu, z-scored on the watching period, slow drift removed
           (minus a 501-frame moving average)
  watching frames 0 .. first stimulation - 50
  poke     each stimulation s with duration d frames: response = mean z over frames
           s+d+1 .. s+d+25 (about 3 s) minus mean over s-17 .. s-1 (2 s before)
  check    the stimulated index is read as an index into all ROIs, into the curated-cell
           list, or through old_cell_idx; the reading giving the largest response is used,
           and that ROI must be in the top 5% of all ROIs, or the session is excluded
  scored   curated cells (iscell; all ROIs if a session has no iscell file), minus the stimulated ROI and any ROI within 10 px of it
  ceiling  Spearman between responses from odd and even stimulations
  models   watching   VAR(1) fitted to the watching period (ridge 0.05 x mean variance),
                      stimulated cell driven +1 for d frames, response read in the same window
           corr       correlation of each cell with the stimulated cell while watching
           deconf     the VAR after regressing running speed (lags 0..8) out of every trace
                      (only sessions with a per-frame speed record)
           others     mean response by distance decile from the stimulated cell, learned
                      from all OTHER sessions (the generic, no-watching baseline)
  score    Spearman(model prediction, measured mean response) across scored cells
  include  >= 8 stimulations, >= 50 scored cells, ceiling >= 0.1
Summary: session-level bootstrap (2000 resamples) of means and paired differences.

Outputs: docs/figures/hippo_sessions.csv, docs/figures/hippo_summary.txt
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "derived" / "hippo"
FIG = ROOT / "docs" / "figures"

GAP_BEFORE_STIM = 50
DRIFT_WIN = 501
RESP_LEN = 25
BASE_LEN = 17
TOP_FRACTION = 0.05
NEAR_PX = 10.0
RIDGE = 0.05
SPEED_LAGS = 8
MIN_STIMS, MIN_CELLS, MIN_CEILING = 8, 50, 0.1
N_BOOT = 2000


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 5:
        return np.nan
    ra, rb = rankdata(a[ok]), rankdata(b[ok])
    if ra.std() == 0 or rb.std() == 0:
        return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])


def read_stims(path: Path):
    rows = []
    for line in path.read_text().split("\n"):
        parts = line.replace(",", " ").split()
        if len(parts) >= 1:
            try:
                s = int(float(parts[0]))
                d = int(float(parts[1])) if len(parts) > 1 else 4
                rows.append((s, max(1, d)))
            except ValueError:
                pass
    return rows


def read_int(path: Path):
    vals = [int(float(x)) for x in path.read_text().replace(",", " ").split()]
    return vals


def read_speed(sdir: Path, T: int):
    p = sdir / "additional_data.csv"
    if not p.exists():
        return None
    try:
        with open(p, newline="") as fh:
            rows = list(csv.DictReader(fh))
        sp = np.array([float(r["speed"]) for r in rows])
    except Exception:
        return None
    return sp if len(sp) == T else None


def preprocess(Fc, watch_end):
    X = Fc.astype(np.float32)
    X = X - uniform_filter1d(X, DRIFT_WIN, axis=1, mode="nearest")
    mu = X[:, :watch_end].mean(1, keepdims=True)
    sd = X[:, :watch_end].std(1, keepdims=True)
    sd[sd == 0] = 1
    return (X - mu) / sd


def poke_responses(Z, stims):
    T = Z.shape[1]
    per = []
    for s, d in stims:
        a, b = s + d + 1, s + d + 1 + RESP_LEN
        if s - BASE_LEN < 0 or b > T:
            continue
        per.append(Z[:, a:b].mean(1) - Z[:, s - BASE_LEN:s].mean(1))
    return np.array(per)  # trials x rois


def fit_var(Zw, ridge=RIDGE):
    X, Y = Zw[:, :-1], Zw[:, 1:]
    XtX = X @ X.T
    lam = ridge * np.trace(XtX) / XtX.shape[0]
    A = np.linalg.solve(XtX + lam * np.eye(XtX.shape[0]), X @ Y.T).T
    rho = np.max(np.abs(np.linalg.eigvals(A)))
    if rho >= 0.99:
        A *= 0.99 / rho
    return A


def var_response(A, src, d):
    n = A.shape[0]
    x = np.zeros(n)
    u = np.zeros(n)
    u[src] = 1.0
    acc = np.zeros(n)
    for t in range(d + 1 + RESP_LEN):
        x = A @ x + (u if t < d else 0.0)
        if t >= d + 1:
            acc += x
    return acc / RESP_LEN


def regress_out(Z, sp, watch_end):
    s = (sp - sp[:watch_end].mean()) / (sp[:watch_end].std() or 1)
    lags = np.stack([np.roll(s, k) for k in range(SPEED_LAGS + 1)])
    lags[:, :SPEED_LAGS] = 0
    D = np.vstack([lags, np.ones(len(s))])[:, :watch_end]
    beta = np.linalg.lstsq(D.T, Z[:, :watch_end].T, rcond=None)[0]
    return Z[:, :watch_end] - (D.T @ beta).T


def find_stim_roi(idx, resp_all, iscell, sdir):
    """Pick the reading of the stimulated index under which that ROI is a top responder."""
    n = len(resp_all)
    cut = np.quantile(resp_all, 1 - TOP_FRACTION)
    cands = [("all", idx)]
    cells = np.flatnonzero(iscell)
    if idx < len(cells):
        cands.append(("cells", int(cells[idx])))
    old = sdir / "old_cell_idx.npy"
    if old.exists():
        o = np.load(old).astype(int).ravel()
        if idx < len(o):
            cands.append(("old->new", int(o[idx])))
        w = np.flatnonzero(o == idx)
        if len(w):
            cands.append(("new<-old", int(w[0])))
    cands = [(how, r) for how, r in cands if 0 <= r < n]
    if not cands:
        return None, "failed"
    how, r = max(cands, key=lambda c: resp_all[c[1]])
    if resp_all[r] >= cut:
        return r, how
    return None, "failed"


def load_session(sdir: Path):
    need = ["Fc.npy", "pos.npy", "stim_frames_true.txt", "suite2p_stim.txt"]
    if not all((sdir / f).exists() for f in need):
        return None
    stim_ids = read_int(sdir / "suite2p_stim.txt")
    if len(stim_ids) != 1:
        return {"id": sdir.name, "status": f"{len(stim_ids)} stimulated ROIs listed (need 1)"}
    Fc = np.load(sdir / "Fc.npy").astype(np.float32)
    pos = np.load(sdir / "pos.npy")
    if (sdir / "iscell.npy").exists():
        iscell = np.load(sdir / "iscell.npy")
        iscell = (iscell[:, 0] if iscell.ndim == 2 else iscell) > 0.5
    else:  # some sessions ship without a curation file: every ROI counts as a cell
        iscell = np.ones(len(pos), bool)
    stims = sorted(read_stims(sdir / "stim_frames_true.txt"))
    if Fc.shape[0] != len(pos) or Fc.shape[0] != len(iscell):
        return {"id": sdir.name, "status": "ROI counts disagree"}
    return dict(id=sdir.name, Fc=Fc, pos=pos, iscell=iscell, stims=stims, stim_idx=stim_ids[0],
                sdir=sdir, status="ok")


def analyse(S):
    Fc, stims = S["Fc"], S["stims"]
    T = Fc.shape[1]
    watch_end = stims[0][0] - GAP_BEFORE_STIM
    out = {"id": S["id"], "n_rois": Fc.shape[0], "frames": T, "watch_frames": watch_end,
           "n_stims": len(stims)}
    if watch_end < 2000:
        out["status"] = "watching period too short"
        return out
    Z = preprocess(Fc, watch_end)
    per = poke_responses(Z, stims)
    out["n_stims"] = len(per)
    if len(per) < MIN_STIMS:
        out["status"] = "too few stimulations"
        return out
    resp = per.mean(0)
    src, how = find_stim_roi(S["stim_idx"], resp, S["iscell"], S["sdir"])
    out["index_reading"] = how
    if src is None:
        out["status"] = "stimulated ROI not a top responder"
        return out
    out["stim_response"] = float(resp[src])
    d_stim = int(np.median([d for _, d in stims]))
    dist = np.linalg.norm(S["pos"] - S["pos"][src], axis=1)
    scored = S["iscell"].copy()
    scored[src] = False
    scored &= ~(dist < NEAR_PX)
    scored &= np.isfinite(dist)
    out["n_scored"] = int(scored.sum())
    if scored.sum() < MIN_CELLS:
        out["status"] = "too few cells"
        return out
    use = np.flatnonzero(scored | (np.arange(len(scored)) == src))
    s_local = int(np.flatnonzero(use == src)[0])
    sc_local = np.flatnonzero(scored[use])

    odd, even = per[0::2].mean(0), per[1::2].mean(0)
    out["ceiling"] = spearman(odd[scored], even[scored])
    measured = resp[scored]

    Zw = Z[use][:, :watch_end]
    A = fit_var(Zw)
    out["watching"] = spearman(var_response(A, s_local, d_stim)[sc_local], measured)
    C = np.corrcoef(Zw)[s_local]
    out["corr"] = spearman(C[sc_local], measured)
    sp = read_speed(S["sdir"], T)
    if sp is not None:
        Zd = regress_out(Z[use], sp, watch_end)
        Ad = fit_var(Zd)
        out["deconf"] = spearman(var_response(Ad, s_local, d_stim)[sc_local], measured)
    # distance deciles for the cross-session model
    dd = dist[scored]
    edges = np.quantile(dd, np.linspace(0, 1, 11))
    bins = np.clip(np.searchsorted(edges, dd, side="right") - 1, 0, 9)
    out["_bins"] = bins
    out["_measured"] = measured
    out["_bin_means"] = np.array([measured[bins == k].mean() if (bins == k).any() else np.nan
                                  for k in range(10)])
    out["status"] = "ok"
    return out


def boot(vals, rng):
    v = np.asarray(vals, float)
    v = v[np.isfinite(v)]
    if len(v) < 2:
        return np.nan, np.nan, np.nan, len(v)
    bs = rng.choice(v, (N_BOOT, len(v))).mean(1)
    return float(v.mean()), float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975)), len(v)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--out", default=str(FIG))
    args = ap.parse_args()
    data, out_dir = Path(args.data), Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for sdir in sorted(p for p in data.iterdir() if p.is_dir()):
        S = load_session(sdir)
        if S is None:
            continue
        if S["status"] != "ok":
            rows.append(S)
            continue
        r = analyse(S)
        rows.append(r)
        print(f"{r['id']}: {r['status']}" + (f"  ceiling {r['ceiling']:.2f} watching {r['watching']:.2f}"
                                               f" corr {r['corr']:.2f}" if r["status"] == "ok" else ""),
              flush=True)
    ok = [r for r in rows if r.get("status") == "ok"]
    for r in ok:  # cross-session generic model, leaving the session out
        others = np.array([o["_bin_means"] for o in ok if o is not r])
        if len(others) == 0:
            r["others"] = np.nan
            continue
        prof = np.nanmean(others, 0)
        r["others"] = spearman(prof[r["_bins"]], r["_measured"])
    keys = ["id", "status", "index_reading", "n_rois", "frames", "watch_frames", "n_stims", "n_scored",
            "stim_response", "ceiling", "watching", "corr", "deconf", "others"]
    with open(out_dir / "hippo_sessions.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(keys)
        for r in rows:
            w.writerow([("" if r.get(k) is None else (f"{r[k]:.4f}" if isinstance(r.get(k), float) else r.get(k)))
                        for k in keys])
    inc = [r for r in ok if r["n_stims"] >= MIN_STIMS and r["n_scored"] >= MIN_CELLS
           and np.isfinite(r["ceiling"]) and r["ceiling"] >= MIN_CEILING]
    rng = np.random.default_rng(0)
    lines = ["Mouse hippocampus: watching versus poking (pre-registered)", "",
             f"sessions found {len(rows)}, analysable {len(ok)}, included (ceiling >= {MIN_CEILING}) {len(inc)}",
             "status counts: " + ", ".join(f"{s}: {sum(1 for r in rows if r.get('status') == s)}"
                                           for s in sorted({r.get('status') for r in rows})), ""]

    def block(title, sel):
        lines.append(title)
        for k in ["ceiling", "watching", "corr", "deconf", "others"]:
            m, lo, hi, n = boot([r.get(k, np.nan) for r in sel], rng)
            lines.append(f"  {k:9s} mean {m:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]  n={n}")
        for a, b in [("watching", "others"), ("corr", "others"), ("watching", "corr"),
                     ("deconf", "watching")]:
            d = [r.get(a, np.nan) - r.get(b, np.nan) for r in sel]
            m, lo, hi, n = boot(d, rng)
            lines.append(f"  {a} - {b}: {m:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]  n={n}")
        cm = np.nanmean([r["ceiling"] for r in sel]) if sel else np.nan
        wm = np.nanmean([r["watching"] for r in sel]) if sel else np.nan
        lines.append(f"  watching as a fraction of ceiling: {wm / cm:.2f}" if sel else "  (none)")
        lines.append("")

    block("INCLUDED sessions (primary)", inc)
    block("ALL analysable sessions (secondary)", ok)
    text = "\n".join(lines)
    (out_dir / "hippo_summary.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
