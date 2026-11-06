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

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ccep_extract as E  # noqa: E402

BLANK_PRE_S, BLANK_POST_S = 0.002, 0.009
RESP = (0.010, 0.100)
PRE_RMS = (-0.050, -0.010)


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
    stem = vhdr.name.replace("_ieeg.vhdr", "")
    folder = vhdr.parent
    h = E.read_vhdr(vhdr)
    ev = E.read_tsv(folder / f"{stem}_events.tsv")
    onsets = [float(e["onset"]) for e in ev if e["trial_type"] == "electrical_stimulation"
              and e["electrical_stimulation_site"] not in ("", "n/a")]
    data, layout = E.open_data(h)
    blanked = Blanked(data, layout, onsets, h["fs"])
    orig, orig_ds = E.open_data, E.downsample
    cache = {}
    E.open_data = lambda h_: (blanked, layout)                     # reuse the v1 pipeline on blanked data
    E.downsample = lambda *a, **k: cache["x"] if "x" in cache else cache.setdefault("x", orig_ds(*a, **k))
    try:
        res = E.process(vhdr)
        res.update(per_pulse(vhdr, h, blanked, layout))
    finally:
        E.open_data, E.downsample = orig, orig_ds
    res["blank_s"] = np.array([-BLANK_PRE_S, BLANK_POST_S])
    return res


def per_pulse(vhdr, h, data, layout) -> dict:
    stem = vhdr.name.replace("_ieeg.vhdr", "")
    folder = vhdr.parent
    ch = E.read_tsv(folder / f"{stem}_channels.tsv")
    ev = E.read_tsv(folder / f"{stem}_events.tsv")
    good = [r["name"] for r in ch if r["type"].upper() == "ECOG" and r["status"] == "good" and r["name"] in h["names"]]
    cols = [h["names"].index(g) for g in good]
    x = E.notch(E.downsample(data, layout, cols, h["res"], h["fs"]))
    T, C = x.shape
    FS = E.FS
    bad = E.bad_mask(T, ev)
    stims = sorted((float(e["onset"]), e["electrical_stimulation_site"]) for e in ev
                   if e["trial_type"] == "electrical_stimulation" and e["electrical_stimulation_site"] not in ("", "n/a"))
    sites = sorted({s for _, s in stims})
    pre, post, base_end = int(E.EP_PRE_S * FS), int(E.EP_POST_S * FS), int(E.BASE_END_S * FS)
    r0, r1 = int(RESP[0] * FS), int(RESP[1] * FS)
    p0, p1 = int(PRE_RMS[0] * FS), int(PRE_RMS[1] * FS)
    t_on, site_i, resp, prer, ok = [], [], [], [], []
    for t0, s in stims:
        k = int(t0 * FS)
        valid = not (k - pre < 0 or k + post > T or bad[k - pre: k + post].any())
        t_on.append(t0)
        site_i.append(sites.index(s))
        if not valid:
            resp.append(np.full(C, np.nan, np.float32))
            prer.append(np.full(C, np.nan, np.float32))
            ok.append(False)
            continue
        pair = [p.strip() for p in s.split("-")]
        idx = [good.index(p) for p in pair if p in good]
        use = np.ones(C, bool)
        use[idx] = False
        ep = x[k - pre: k + post].astype(np.float64)
        ep = ep - ep[:, use].mean(1, keepdims=True)
        ep = ep - ep[: pre - base_end].mean(0)
        r = np.sqrt(np.mean(ep[pre + r0: pre + r1] ** 2, axis=0))
        q = np.sqrt(np.mean(ep[pre + p0: pre + p1] ** 2, axis=0))
        r[idx], q[idx] = np.nan, np.nan
        resp.append(r.astype(np.float32))
        prer.append(q.astype(np.float32))
        ok.append(True)
    return {"pulse_onset_s": np.array(t_on), "pulse_site": np.array(site_i), "pulse_ok": np.array(ok),
            "pulse_resp_rms": np.array(resp, np.float32).reshape(len(t_on), C),
            "pulse_pre_rms": np.array(prer, np.float32).reshape(len(t_on), C)}


def main() -> int:
    vhdr, out = Path(sys.argv[1]), Path(sys.argv[2])
    res = process(vhdr)
    np.savez_compressed(out, **res)
    print(f"{vhdr.name}: {len(res['names'])} channels, {len(res['sites'])} sites, {int(res['pulse_ok'].sum())} pulses kept")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
