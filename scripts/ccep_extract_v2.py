"""Human data, second extraction (pre-registered 6 Nov 2026; README "Do human cortical responses tire?").

Two changes from ccep_extract.py, both fixed before any recording was re-extracted:
1. The stimulation artefact is blanked before any filtering: in the raw recording, every channel is
   replaced by a straight line from 2 ms before to 9 ms after each pulse onset (the response window
   starts at 10 ms), so filtering can no longer smear the pulse into the response or the baseline.
2. Per-pulse responses are kept, not only odd and even averages: for every pulse and every good
   channel, the response strength (root mean square from 10 to 100 ms of the epoch after the same
   common average and baseline as before) and the pre-pulse strength (root mean square from -50 to
   -10 ms), with the pulse's onset time and stimulated pair.

Everything else (channels, 512 Hz, notches, common average, artefact annotations, the VAR statistics,
odd/even averages) is as in ccep_extract.py, so the original human test can be rescored on clean data.

Usage:  python scripts/ccep_extract_v2.py RUN_ieeg.vhdr OUT.npz
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ccep_extract as E  # noqa: E402

BLANK_PRE_S, BLANK_POST_S = 0.002, 0.009
RESP = (0.010, 0.100)
PRE_RMS = (-0.050, -0.010)


def lean_notch(x, block=16):
    """The same 50, 100 and 150 Hz notches as ccep_extract.notch, a few channels at a time, in place."""
    from scipy.signal import iirnotch, filtfilt
    coefs = [iirnotch(f0, 30.0, fs=E.FS) for f0 in (50.0, 100.0, 150.0)]
    for c in range(0, x.shape[1], block):
        y = x[:, c:c + block].astype(np.float64)
        for b, a in coefs:
            y = filtfilt(b, a, y, axis=0)
        x[:, c:c + block] = y
    return x


def lean_downsample_range(data, layout, cols, res, fs_in, a0, a1):
    """Low-pass at 120 Hz (4th-order Butterworth, forward and back, 2,048 raw samples of padding as
    ccep_extract.downsample) and block-mean to 512 Hz, for raw samples [a0, a1)."""
    from scipy.signal import butter, sosfiltfilt
    DS = int(round(fs_in / E.FS))
    sos = butter(4, 120, fs=fs_in, output="sos")
    T = data.shape[0] if layout == "TC" else data.shape[1]
    lo, hi = max(0, a0 - 2048), min(T, a1 + 2048)
    x = (data[lo:hi, cols] if layout == "TC" else data[cols, lo:hi].T).astype(np.float64) * res[cols]
    x = sosfiltfilt(sos, x, axis=0)[a0 - lo: a1 - lo]
    n = (x.shape[0] // DS) * DS
    return x[:n].reshape(-1, DS, x.shape[1]).mean(1).astype(np.float32)


def lean_downsample(data, layout, cols, res, fs_in, chunk=2048 * 60):
    """ccep_extract.downsample (120 Hz low-pass, block means to 512 Hz, in chunks) written into one
    preallocated array instead of a list joined at the end (half the memory)."""
    from scipy.signal import butter, sosfiltfilt
    DS = int(round(fs_in / E.FS))
    sos = butter(4, 120, fs=fs_in, output="sos")
    T = data.shape[0] if layout == "TC" else data.shape[1]
    total = sum(((min(chunk, T - a)) // DS) for a in range(0, T, chunk))
    out = np.empty((total, len(cols)), np.float32)
    pad, o = 2048, 0
    for a in range(0, T, chunk):
        lo, hi = max(0, a - pad), min(T, a + chunk + pad)
        x = (data[lo:hi, cols] if layout == "TC" else data[cols, lo:hi].T).astype(np.float64) * res[cols]
        x = sosfiltfilt(sos, x, axis=0)
        x = x[a - lo: a - lo + min(chunk, T - a)]
        n = (x.shape[0] // DS) * DS
        out[o:o + n // DS] = x[:n].reshape(-1, DS, x.shape[1]).mean(1)
        o += n // DS
    return out


class Blanked:
    """Wraps the raw memmap; returns copies with each pulse's samples replaced by a straight line."""

    def __init__(self, data, layout, onsets_s, fs):
        self.data, self.layout, self.fs = data, layout, fs
        self.shape = data.shape
        self.win = [(int(round((t - BLANK_PRE_S) * fs)), int(round((t + BLANK_POST_S) * fs))) for t in onsets_s]

    def __getitem__(self, key):
        x = np.array(self.data[key], dtype=np.float64)
        if self.layout == "TC":
            rows, _ = key
            lo = rows.start or 0
            tax = 0
        else:
            _, rows = key
            lo = rows.start or 0
            tax = 1
        n = x.shape[tax]
        for a, b in self.win:
            a0, b0 = a - lo, b - lo
            if b0 < 1 or a0 > n - 2:
                continue
            a0, b0 = max(a0, 0), min(b0, n - 1)
            if tax == 0:
                x[a0:b0 + 1] = np.linspace(x[a0], x[b0], b0 - a0 + 1)
            else:
                x[:, a0:b0 + 1] = np.linspace(x[:, a0], x[:, b0], b0 - a0 + 1).T
        return x


def process(vhdr: Path) -> dict:
    """ccep_extract.process step for step (same channels, filters, segments, epochs, odd/even averages,
    VAR statistics), on the blanked signal, with the common average computed per segment instead of
    held as a second full copy (recordings run up to 2 h), plus the per-pulse strengths."""
    stem = vhdr.name.replace("_ieeg.vhdr", "")
    folder = vhdr.parent
    h = E.read_vhdr(vhdr)
    FS = E.FS
    ds = h["fs"] / FS
    if h["fs"] < FS - 1 or abs(ds - round(ds)) > 1e-6:
        raise ValueError(f"{vhdr.name}: sampling rate {h['fs']} is not a multiple of {FS} Hz")
    ch = E.read_tsv(folder / f"{stem}_channels.tsv")
    ev = E.read_tsv(folder / f"{stem}_events.tsv")
    ses = folder / next(p.name for p in folder.iterdir() if p.name.endswith("_electrodes.tsv"))
    el = {r["name"]: r for r in E.read_tsv(ses)}
    good = [r["name"] for r in ch if r["type"].upper() == "ECOG" and r["status"] == "good" and r["name"] in h["names"]]
    cols = [h["names"].index(g) for g in good]
    onsets = [float(e["onset"]) for e in ev if e["trial_type"] == "electrical_stimulation"
              and e["electrical_stimulation_site"] not in ("", "n/a")]
    data, layout = E.open_data(h)
    src = Blanked(data, layout, onsets, h["fs"])
    DSr = int(round(h["fs"] / FS))
    T = (data.shape[0] if layout == "TC" else data.shape[1]) // DSr
    C = len(cols)
    NPAD, CORE, EXT = 10 * FS, 120 * FS, 12 * FS

    def piece(lo, hi):
        """The 512 Hz, low-passed, notched signal for samples [lo, hi), computed from a padded stretch
        (10 s beyond each end for the notches, 1 s of raw signal beyond that for the low-pass), so the
        whole recording never sits in memory (amended before any human response was computed)."""
        elo, ehi = max(0, lo - NPAD), min(T, hi + NPAD)
        z = lean_downsample_range(src, layout, cols, h["res"], h["fs"], elo * DSr, ehi * DSr)
        z = lean_notch(z)
        return z[lo - elo: lo - elo + (hi - lo)]

    cache = {}

    def get(a, b):
        """Samples [a, b) from the 120 s piece holding a, computed once per piece with 12 s of margin."""
        c = a // CORE
        if cache.get("c") != c:
            lo, hi = max(0, c * CORE - EXT), min(T, (c + 1) * CORE + EXT)
            cache.clear()
            cache.update(c=c, lo=lo, x=piece(lo, hi))
        lo = cache["lo"]
        return cache["x"][a - lo: b - lo]

    bad = E.bad_mask(T, ev)
    LAGS = E.LAGS
    stims = sorted((float(e["onset"]), e["electrical_stimulation_site"]) for e in ev
                   if e["trial_type"] == "electrical_stimulation" and e["electrical_stimulation_site"] not in ("", "n/a"))
    d = LAGS * C + 1
    XtX, XtY, n_rows, seg = np.zeros((d, d)), np.zeros((d, C)), 0, 0.0
    QUART = os.environ.get("NEMATICA_CCEP_QUARTERS") == "1"   # watching-limit part E: statistics per quarter
    if QUART:
        XtXq, XtYq, nq = np.zeros((4, d, d)), np.zeros((4, d, C)), np.zeros(4, int)
        span = (stims[0][0], stims[-1][0]) if stims else (0.0, 1.0)
    for (t0, _), (t1, _) in zip(stims[:-1], stims[1:]):
        if t1 - t0 > 10:
            continue
        a, b = int((t0 + E.SEG_START_S) * FS), int((t1 - E.SEG_END_GAP_S) * FS)
        if b - a < FS or b > T or bad[a:b].any():
            continue
        z = get(a, b).astype(np.float64)
        z = z - z.mean(1, keepdims=True)                         # common average, per segment
        X = np.hstack([z[LAGS - L: z.shape[0] - L] for L in range(1, LAGS + 1)] + [np.ones((z.shape[0] - LAGS, 1))])
        Y = z[LAGS:]
        XtX += X.T @ X
        XtY += X.T @ Y
        n_rows += Y.shape[0]
        seg += (b - a) / FS
        if QUART:
            qi = min(3, int(4 * (t0 - span[0]) / max(span[1] - span[0], 1e-9)))
            XtXq[qi] += X.T @ X
            XtYq[qi] += X.T @ Y
            nq[qi] += Y.shape[0]
    pre, post, base_end = int(E.EP_PRE_S * FS), int(E.EP_POST_S * FS), int(E.BASE_END_S * FS)
    keep = int(0.05 * FS)
    sites = sorted({s for _, s in stims})
    W = (keep + post) // 2
    odd = np.zeros((len(sites), C, W), np.float32)
    even = np.zeros_like(odd)
    n_odd = np.zeros(len(sites), int)
    n_even = np.zeros(len(sites), int)
    count = {s: 0 for s in sites}
    r0, r1 = int(RESP[0] * FS), int(RESP[1] * FS)
    p0, p1 = int(PRE_RMS[0] * FS), int(PRE_RMS[1] * FS)
    t_on, site_i, resp, prer, ok = [], [], [], [], []
    V3 = os.environ.get("NEMATICA_CCEP_V3") == "1"          # third extraction: waveforms and state too
    wave, state = [], []
    Ww = (r1 - r0) // 2
    for t0, s in stims:
        k = int(t0 * FS)
        t_on.append(t0)
        site_i.append(sites.index(s))
        if k - pre < 0 or k + post > T or bad[k - pre: k + post].any():
            resp.append(np.full(C, np.nan, np.float32))
            prer.append(np.full(C, np.nan, np.float32))
            ok.append(False)
            if V3:
                wave.append(np.full((C, Ww), np.nan, np.float16)); state.append(np.full(C, np.nan, np.float16))
            continue
        pair = [p.strip() for p in s.split("-")]
        idx = [good.index(p) for p in pair if p in good]
        use = np.ones(C, bool)
        use[idx] = False
        ep = get(k - pre, k + post)
        ep = ep - ep[:, use].mean(1, keepdims=True)
        ep = ep - ep[: pre - base_end].mean(0)
        r = np.sqrt(np.mean(ep[pre + r0: pre + r1].astype(np.float64) ** 2, axis=0))
        q = np.sqrt(np.mean(ep[pre + p0: pre + p1].astype(np.float64) ** 2, axis=0))
        r[idx], q[idx] = np.nan, np.nan
        resp.append(r.astype(np.float32))
        prer.append(q.astype(np.float32))
        ok.append(True)
        if V3:   # the response waveform from 10 to 100 ms at 256 Hz, and the state: log variance from -1 s to -50 ms
            wv = ep[pre + r0: pre + r0 + 2 * Ww].reshape(Ww, 2, C).mean(1).T.copy()
            wv[idx] = np.nan
            wave.append(wv.astype(np.float16))
            if k - FS >= 0 and not bad[k - FS: k].any():
                z0 = get(k - FS, k - int(0.05 * FS)).astype(np.float64)
                z0 = z0 - z0.mean(1, keepdims=True)
                st = np.log(z0.var(0) + 1e-12)
                st[idx] = np.nan
            else:
                st = np.full(C, np.nan)
            state.append(st.astype(np.float16))
        ep = ep[pre - keep:]
        ep = ep[: (ep.shape[0] // 2) * 2].reshape(-1, 2, C).mean(1).T[:, :W]
        ep[idx] = np.nan
        i = sites.index(s)
        if count[s] % 2 == 0:
            odd[i] += np.nan_to_num(ep)
            n_odd[i] += 1
        else:
            even[i] += np.nan_to_num(ep)
            n_even[i] += 1
        count[s] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        odd /= np.maximum(n_odd, 1)[:, None, None]
        even /= np.maximum(n_even, 1)[:, None, None]
    for i, s in enumerate(sites):
        for p in s.split("-"):
            if p.strip() in good:
                odd[i, good.index(p.strip())] = np.nan
                even[i, good.index(p.strip())] = np.nan
    xyz = np.array([[float(el[g][k]) if g in el and el[g][k] not in ("n/a", "") else np.nan for k in ("x", "y", "z")] for g in good])
    label = [el[g].get("Destrieux_label_text", "n/a") if g in el else "n/a" for g in good]
    return {"names": np.array(good), "xyz": xyz, "label": np.array(label), "sites": np.array(sites),
            "ccep_odd": odd.astype(np.float16), "ccep_even": even.astype(np.float16), "n_odd": n_odd, "n_even": n_even,
            "XtX": XtX, "XtY": XtY, "n_rows": n_rows, "seg_seconds": seg, "fs": FS, "out_fs": E.OUT_FS, "lags": LAGS,
            "window_start_s": -0.05, "blank_s": np.array([-BLANK_PRE_S, BLANK_POST_S]),
            "pulse_onset_s": np.array(t_on), "pulse_site": np.array(site_i), "pulse_ok": np.array(ok),
            "pulse_resp_rms": np.array(resp, np.float32).reshape(len(t_on), C),
            "pulse_pre_rms": np.array(prer, np.float32).reshape(len(t_on), C),
            **({"pulse_wave": np.array(wave, np.float16).reshape(len(t_on), C, Ww),
                "pulse_state": np.array(state, np.float16).reshape(len(t_on), C)} if V3 else {}),
            **({"XtX_q": XtXq, "XtY_q": XtYq, "n_rows_q": nq} if QUART else {})}


def main() -> int:
    vhdr, out = Path(sys.argv[1]), Path(sys.argv[2])
    res = process(vhdr)
    np.savez_compressed(out, **res)
    print(f"{vhdr.name}: {len(res['names'])} channels, {len(res['sites'])} sites, {int(res['pulse_ok'].sum())} pulses kept")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
