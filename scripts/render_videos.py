"""Two short videos for the write-up (8 Nov 2026), drawn from the site's regenerated data (web/data/local.js and
echo.js, derived from the CC BY 4.0 atlas; outputs are not committed).

  06-poke-echo.mp4      one neuron class switched on: average echo in held-out real worms, in a brain that only
                        watched, and in a brain that also learned from pokes
  03-real-vs-model.mp4  eight minutes of a held-out real worm and of the watching model, scrolled, then labelled

Usage:  python scripts/render_videos.py OUTDIR [--frames-only]
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
W, H, FPS = 1280, 720, 30
BG, INK, MUTED = "#0b1514", "#eef5f1", "#8fa6a0"
GLOW, COOL = (124 / 255, 240 / 255, 168 / 255), (211 / 255, 111 / 255, 208 / 255)
FLUO = LinearSegmentedColormap.from_list("fluo", [(0, "#000000"), (0.3, "#0d3b26"), (0.65, "#2fae66"), (0.85, "#7cf0a8"), (1, "#effff4")])


def js_obj(p):
    s = p.read_text(encoding="utf-8")
    return json.loads(s[s.index("{"):s.rstrip().rstrip(";").rindex("}") + 1])


class Writer:
    def __init__(self, path):
        self.path, self.tmp = path, path.with_name(path.stem + ".part.mp4")
        self.p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                   "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                                   "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(self.tmp)], stdin=subprocess.PIPE)

    def add(self, fig):
        fig.canvas.draw()
        self.p.stdin.write(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].tobytes())

    def close(self):
        self.p.stdin.close()
        if self.p.wait() == 0:
            os.replace(self.tmp, self.path)


def new_fig():
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
    return fig


# ---------------------------------------------------------------- poke echo
def echo_video(out, frames_only=False):
    E = js_obj(ROOT / "web/data/echo.js")
    S, R, NT, SC = E["stims"], E["resp"], E["nt"], E["scale"]

    def arr(k):
        a = np.frombuffer(base64.b64decode(E["sets"][k]), dtype=np.int8).reshape(len(S), len(R), NT).astype(float)
        a[a == -128] = np.nan
        return a / 127 * SC
    sets = [("Real worms", f"average of {E['nWorms']} held-out worms", arr("real")),
            ("Learned by watching", "fitted to other worms at rest", arr("var3_spontaneous")),
            ("Learned from pokes too", "causal links from other worms' pokes", arr("hybrid_kernels_regimes_obsfit"))]
    pos = np.array([E["pos"][c] for c in R])
    x0, x1, y0, y1 = pos[:, 0].min(), pos[:, 0].max(), pos[:, 1].min(), pos[:, 1].max()

    def agree(i, k):
        a, b = np.nanmean(sets[0][2][i, :, :16], 1), np.nanmean(sets[k][2][i, :, :16], 1)
        m = np.isfinite(a) & np.isfinite(b)
        return np.corrcoef(a[m], b[m])[0, 1] if m.sum() >= 5 else np.nan

    scenes = ["ASH", "MI"]
    secs_per = 10.0
    w = Writer(out / "06-poke-echo.mp4") if not frames_only else None
    stills = []
    for sc_i, name in enumerate(scenes):
        i = S.index(name)
        nfr = int(secs_per * FPS)
        for f in range(nfr):
            tt = f / nfr * 30.0                      # echo seconds shown
            fig = new_fig()
            fig.text(0.04, 0.92, f"Switch on {name}. Where does the signal go?", color=INK, fontsize=24, family="serif")
            fig.text(0.04, 0.875, "Each dot is a neuron type in the worm's head, nose to the left. Green rises, pink falls.",
                     color=MUTED, fontsize=13)
            for k, (title, sub, a) in enumerate(sets):
                ax = fig.add_axes([0.03 + k * 0.325, 0.2, 0.3, 0.55])
                ax.set_facecolor(BG)
                ax.set_xlim(x0 - 8, x1 + 8)
                ax.set_ylim(y0 - 8, y1 + 8)
                ax.axis("off")
                ax.add_patch(matplotlib.patches.Ellipse(((x0 + x1) / 2, (y0 + y1) / 2), x1 - x0 + 14, y1 - y0 + 12,
                                                        fill=False, ec=(0.84, 0.89, 0.87, 0.18), lw=1.5))
                t0 = int(np.floor(tt)); t1 = min(NT - 1, t0 + 1); fr = tt - t0
                v = (1 - fr) * a[i, :, t0] + fr * a[i, :, t1]
                ok = np.isfinite(v)
                m = np.clip(np.abs(v) / 1.5, 0, 1)
                cols = [(*(GLOW if vv >= 0 else COOL), 0.18 + 0.82 * mm) for vv, mm in zip(np.nan_to_num(v), m)]
                ax.scatter(pos[ok, 0], pos[ok, 1], s=(3 + 9 * m[ok]) ** 2, c=[c for c, o in zip(cols, ok) if o], lw=0)
                ax.scatter(pos[~ok, 0], pos[~ok, 1], s=10, c=[(0.84, 0.89, 0.87, 0.12)], lw=0)
                if name in E["pos"]:
                    px, py = E["pos"][name]
                    flash = max(0.0, 1 - tt / 2.0)
                    if flash > 0:
                        ax.scatter([px], [py], s=(40 * flash + 10) ** 2, c=[(1, 1, 1, 0.35 * flash)], lw=0)
                    ax.scatter([px], [py], s=260, facecolors="none", edgecolors="white", lw=2)
                fig.text(0.03 + k * 0.325 + 0.01, 0.78, title, color=INK, fontsize=17, family="serif")
                fig.text(0.03 + k * 0.325 + 0.01, 0.755, sub, color=MUTED, fontsize=11)
                if k:
                    r = agree(i, k)
                    fig.text(0.03 + k * 0.325 + 0.01, 0.16, f"Agreement with real worms: {r:.2f}", color=INK, fontsize=13)
                else:
                    fig.text(0.04, 0.16, "The reference", color=MUTED, fontsize=13)
            fig.text(0.04, 0.07, f"{tt:4.1f} s after the poke", color=INK, fontsize=15, family="monospace")
            fig.text(0.96, 0.07, "Data: Randi et al. 2023 (CC BY 4.0). NEMATICA", color=MUTED, fontsize=10, ha="right")
            if frames_only and f in (int(0.1 * nfr), int(0.3 * nfr)):
                p = out / f"frame_echo_{name}_{f}.png"
                fig.savefig(p, facecolor=BG)
                stills.append(p)
            if w:
                w.add(fig)
            plt.close(fig)
            if frames_only and f > int(0.3 * nfr):
                break
    if w:
        w.close()
    return stills


# ---------------------------------------------------------------- real vs model
def raster_video(out, frames_only=False):
    L = js_obj(ROOT / "web/data/local.js")
    n, T = len(L["classes"]), L["frames"]

    def unpack(b):
        q = np.frombuffer(base64.b64decode(b), dtype=np.uint8).reshape(n, T).astype(float)
        return np.where(q == 0, 0, (q - 1) / 254 * 1.25)
    real, model = unpack(L["real"]), unpack(L["brains"]["var3_spontaneous"]["data"])
    win = 240                                         # 2 minutes visible
    total = 16.0
    nfr = int(total * FPS)
    w = Writer(out / "03-real-vs-model.mp4") if not frames_only else None
    stills = []
    for f in range(nfr):
        s = f / nfr
        start = int(min(T - win, s / 0.8 * (T - win)))
        labelled = s > 0.62
        fig = new_fig()
        fig.text(0.04, 0.91, "One is a real worm's brain. One is a model. Which is which?" if not labelled
                 else "Right: the real worm. Left: a model learned only by watching.", color=INK, fontsize=22, family="serif")
        fig.text(0.04, 0.865, "Each row is a neuron type; brightness is its activity. Two minutes are shown at a time.",
                 color=MUTED, fontsize=13)
        for k, (data, lab) in enumerate(((model, "Model"), (real, "Real worm"))):
            ax = fig.add_axes([0.04 + k * 0.48, 0.14, 0.44, 0.66])
            ax.imshow(data[:, start:start + win], aspect="auto", cmap=FLUO, vmin=0, vmax=1, interpolation="nearest")
            ax.axis("off")
            for st in L["stims"]:
                if start <= st["frame"] < start + win:
                    ax.plot([st["frame"] - start] * 2, [-2.5, -0.7], color="#7cf0a8", lw=2, clip_on=False)
            name = lab if labelled else ("Brain A" if k == 0 else "Brain B")
            fig.text(0.04 + k * 0.48, 0.815, name, color=INK, fontsize=16)
        if labelled:
            fig.text(0.04, 0.07, "The model passes five of six statistical tests of real activity. It answers pokes almost at random.",
                     color=INK, fontsize=14)
        else:
            fig.text(0.04, 0.07, f"{start * 0.5 / 60:4.1f} min into the recording", color=MUTED, fontsize=13, family="monospace")
        fig.text(0.96, 0.03, "Data: Randi et al. 2023 (CC BY 4.0). NEMATICA", color=MUTED, fontsize=10, ha="right")
        if frames_only and f in (int(0.3 * nfr), int(0.8 * nfr)):
            p = out / f"frame_raster_{f}.png"
            fig.savefig(p, facecolor=BG)
            stills.append(p)
        if w:
            w.add(fig)
        plt.close(fig)
        if frames_only and f > int(0.8 * nfr):
            break
    if w:
        w.close()
    return stills


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    fo = "--frames-only" in sys.argv
    print(echo_video(out, fo))
    print(raster_video(out, fo))
