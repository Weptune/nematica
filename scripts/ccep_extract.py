"""Human test, step 1: reduce one CCEP ECoG recording (OpenNeuro ds004080, BrainVision
format) to what the pre-registered analysis needs, so the raw file can be deleted.

Per recording (one run of one patient), written to one .npz:
  names, xyz, label        good ECoG channels, MNI coordinates, Destrieux label text
  sites                    stimulated pairs, e.g. "F01-F02"
  ccep_odd, ccep_even      average response per (site, channel), odd and even pulses
                           separately, -50 to 500 ms at 256 Hz, baseline -200 to -10 ms
                           removed; the two stimulated channels are NaN
  n_odd, n_even            pulses in each average
  XtX, XtY, n_rows         sufficient statistics of a VAR(5) at 512 Hz on the activity
                           between pulses (1.0 s after a pulse to 20 ms before the next),
                           so watching copies can be refitted with any ridge without the
                           raw data; rows are [x(t-1) ... x(t-5), 1], targets x(t)
  seg_seconds              how much between-pulse activity went into them
Preprocessing: good ECoG channels only (status "good" in channels.tsv); to 512 Hz by block means
after a 120 Hz low-pass (recordings at 2048 Hz; the five at 512 Hz are only low-passed); 50, 100 and 150 Hz notches; common average
reference over good channels (for responses: excluding the stimulated pair); pulses and
segments touching an annotated artefact are dropped.

Usage:  python scripts/ccep_extract.py RUN_ieeg.vhdr OUT.npz
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import numpy as np

FS = 512                               # analysis rate; recordings are 2048 Hz (112) or 512 Hz (5)
LAGS = 5
SEG_START_S, SEG_END_GAP_S = 1.0, 0.02
EP_PRE_S, EP_POST_S, BASE_END_S = 0.2, 0.5, 0.01
OUT_FS = 256


def read_tsv(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def read_vhdr(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8", errors="replace")
    get = lambda k: (re.search(rf"^{k}=(.*)$", txt, re.M) or [None, None])[1]
    n = int(get("NumberOfChannels"))
    lines = {}
    for line in txt.splitlines():
        m = re.match(r"^Ch(\d+)=(.*)$", line.strip())
        if m:
            lines[int(m.group(1))] = m.group(2)
    names, res = [], []
    for i in range(1, n + 1):
        parts = [p.strip() for p in lines[i].split(",")]        # name, reference, resolution, unit
        names.append(parts[0].replace("\\1", ","))
        try:
            res.append(float(parts[2]) if len(parts) > 2 and parts[2] else 1.0)
        except ValueError:
            res.append(1.0)
    fmt = (get("BinaryFormat") or "IEEE_FLOAT_32").strip()
    orient = (get("DataOrientation") or "MULTIPLEXED").strip()
    fs = 1e6 / float(get("SamplingInterval"))
    return {"n": n, "names": names, "res": np.array(res), "fmt": fmt, "orient": orient, "fs": fs,
            "datafile": path.parent / get("DataFile").strip()}


def open_data(h):
    dt = {"IEEE_FLOAT_32": np.float32, "INT_16": np.int16, "INT_32": np.int32}[h["fmt"]]
    raw = np.memmap(h["datafile"], dtype=dt, mode="r")
    T = raw.size // h["n"]
    if h["orient"].startswith("MULTIPLEX"):
        return raw[: T * h["n"]].reshape(T, h["n"]), "TC"
    return raw[: T * h["n"]].reshape(h["n"], T), "CT"


def downsample(data, layout, cols, res, fs_in, chunk=2048 * 60):
    """Low-pass at 120 Hz, block-mean to 512 Hz, in chunks; returns (T512, C) float32."""
    from scipy.signal import butter, sosfiltfilt
    DS = int(round(fs_in / FS))
    sos = butter(4, 120, fs=fs_in, output="sos")
    T = data.shape[0] if layout == "TC" else data.shape[1]
    out = []
    pad = 2048
    for a in range(0, T, chunk):
        lo, hi = max(0, a - pad), min(T, a + chunk + pad)
        x = (data[lo:hi, cols] if layout == "TC" else data[cols, lo:hi].T).astype(np.float64) * res[cols]
        x = sosfiltfilt(sos, x, axis=0)
        x = x[a - lo: a - lo + min(chunk, T - a)]
        n = (x.shape[0] // DS) * DS
        out.append(x[:n].reshape(-1, DS, x.shape[1]).mean(1).astype(np.float32))
    return np.vstack(out)


def notch(x):
    from scipy.signal import iirnotch, filtfilt
    for f0 in (50.0, 100.0, 150.0):
        b, a = iirnotch(f0, 30.0, fs=FS)
        x = filtfilt(b, a, x, axis=0)
    return x.astype(np.float32)


def bad_mask(T, events):
    bad = np.zeros(T, bool)
    for e in events:
        if e["trial_type"] == "artefact":
            a = int(float(e["onset"]) * FS)
            b = int(float(e["offset"]) * FS) if e.get("offset", "n/a") != "n/a" else a + int(float(e["duration"]) * FS)
            bad[max(0, a - FS // 10): min(T, b + FS // 10)] = True
    return bad


def process(vhdr: Path) -> dict:
    stem = vhdr.name.replace("_ieeg.vhdr", "")
    folder = vhdr.parent
    h = read_vhdr(vhdr)
    ds = h["fs"] / FS
    if h["fs"] < FS - 1 or abs(ds - round(ds)) > 1e-6:
        raise ValueError(f"{vhdr.name}: sampling rate {h['fs']} is not a multiple of {FS} Hz")
    ch = read_tsv(folder / f"{stem}_channels.tsv")
    ev = read_tsv(folder / f"{stem}_events.tsv")
    ses = folder / next(p.name for p in folder.iterdir() if p.name.endswith("_electrodes.tsv"))
    el = {r["name"]: r for r in read_tsv(ses)}
    good = [r["name"] for r in ch if r["type"].upper() == "ECOG" and r["status"] == "good" and r["name"] in h["names"]]
    cols = [h["names"].index(g) for g in good]
    data, layout = open_data(h)
    x = notch(downsample(data, layout, cols, h["res"], h["fs"]))
    T, C = x.shape
    bad = bad_mask(T, ev)
    car = x - x.mean(1, keepdims=True)

    # watching: between pulses
    stims = sorted((float(e["onset"]), e["electrical_stimulation_site"]) for e in ev
                   if e["trial_type"] == "electrical_stimulation" and e["electrical_stimulation_site"] not in ("", "n/a"))
    d = LAGS * C + 1
    XtX, XtY, n_rows, seg = np.zeros((d, d)), np.zeros((d, C)), 0, 0.0
    for (t0, _), (t1, _) in zip(stims[:-1], stims[1:]):
        if t1 - t0 > 10:
            continue
        a, b = int((t0 + SEG_START_S) * FS), int((t1 - SEG_END_GAP_S) * FS)
        if b - a < FS or bad[a:b].any():
            continue
        z = car[a:b].astype(np.float64)
        X = np.hstack([z[LAGS - L: z.shape[0] - L] for L in range(1, LAGS + 1)] + [np.ones((z.shape[0] - LAGS, 1))])
        Y = z[LAGS:]
        XtX += X.T @ X
        XtY += X.T @ Y
        n_rows += Y.shape[0]
        seg += (b - a) / FS

    # poking: average responses per stimulated pair
    pre, post, base_end = int(EP_PRE_S * FS), int(EP_POST_S * FS), int(BASE_END_S * FS)
    keep = int(0.05 * FS)                                   # stored window starts at -50 ms
    sites = sorted({s for _, s in stims})
    W = (keep + post) // 2                                  # 512 -> 256 Hz
    odd = np.zeros((len(sites), C, W), np.float32)
    even = np.zeros_like(odd)
    n_odd = np.zeros(len(sites), int)
    n_even = np.zeros(len(sites), int)
    count = {s: 0 for s in sites}
    for t0, s in stims:
        k = int(t0 * FS)
        if k - pre < 0 or k + post > T or bad[k - pre: k + post].any():
            continue
        pair = [p.strip() for p in s.split("-")]
        idx = [good.index(p) for p in pair if p in good]
        use = np.ones(C, bool)
        use[idx] = False
        ep = x[k - pre: k + post]
        ep = ep - ep[:, use].mean(1, keepdims=True)
        ep = ep - ep[: pre - base_end].mean(0)
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
            "XtX": XtX, "XtY": XtY, "n_rows": n_rows, "seg_seconds": seg, "fs": FS, "out_fs": OUT_FS, "lags": LAGS,
            "window_start_s": -0.05}


def main() -> int:
    vhdr, out = Path(sys.argv[1]), Path(sys.argv[2])
    res = process(vhdr)
    np.savez_compressed(out, **res)
    print(f"{vhdr.name}: {len(res['names'])} channels, {len(res['sites'])} sites, "
          f"{int(res['n_odd'].sum() + res['n_even'].sum())} pulses, {res['seg_seconds']:.0f} s between pulses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
