"""Render a film shot frame by frame with a controlled clock, then optionally encode it.

    cd lab && npm run film            # serves film.html on http://localhost:8090
    python scripts/film/render.py hero out/hero --seconds 12 --fps 24 --size 1920x1080
    python scripts/film/render.py echo out/echo --seconds 12 --cpu      # no GPU: software WebGL

Shots: hero, brain, pair, path, swarm, echo (see lab/film/Film.jsx). The page sees a fake clock
that advances exactly 1/fps per captured frame, so output is smooth however slow rendering is.
Add --grade to write <out>.mp4 with the same glow, vignette and fades used for the blog clips.
Needs: pip install playwright && playwright install chromium; ffmpeg on PATH for --grade.
"""
import argparse
import base64
import shutil
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

CLOCK = """(() => {
  let t = 1000; const realRAF = window.requestAnimationFrame.bind(window); const t0 = Date.now();
  window.__adv = (ms) => { t += ms; };
  performance.now = () => t;
  Date.now = () => t0 + t;
  window.requestAnimationFrame = (cb) => realRAF(() => cb(t));
})();"""
NEXT = "() => new Promise(r => requestAnimationFrame(() => r()))"
CPU = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
GRADE = ("format=gbrp,split=3[base][g1][g2];[g1]curves=all='0/0 0.42/0 1/1',gblur=sigma=9[a];"
         "[g2]curves=all='0/0 0.5/0 1/1',gblur=sigma=42[b];[base][a]blend=all_mode=screen:all_opacity=0.75[c];"
         "[c][b]blend=all_mode=screen:all_opacity=0.55,vignette=angle=PI/7:mode=forward,"
         "colorbalance=bs=0.03:rs=0.012{fades},format=yuv420p")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shot"); ap.add_argument("out")
    ap.add_argument("--seconds", type=float, default=10); ap.add_argument("--fps", type=float, default=24)
    ap.add_argument("--size", default="1920x1080"); ap.add_argument("--url", default="http://localhost:8090/film.html")
    ap.add_argument("--query", default="&nopost=1", help="extra query; &nopost=1 leaves glow to --grade")
    ap.add_argument("--cpu", action="store_true", help="software WebGL (slow; for machines without a GPU)")
    ap.add_argument("--grade", action="store_true")
    a = ap.parse_args()
    W, H = map(int, a.size.split("x"))
    out = Path(a.out); frames = out.with_name(out.name + "_frames")
    shutil.rmtree(frames, ignore_errors=True); frames.mkdir(parents=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=CPU if a.cpu else ["--ignore-gpu-blocklist", "--enable-gpu"])
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.on("pageerror", lambda e: print("page error:", e))
        pg.add_init_script(CLOCK)
        pg.goto(f"{a.url}?shot={a.shot}{a.query}", wait_until="load")
        start = time.time()
        while not pg.evaluate("!!window.__filmReady"):
            pg.evaluate("__adv(16)"); pg.evaluate(NEXT)
            if time.time() - start > 120:
                raise SystemExit("the shot never became ready (is `npm run film` running, and the data exported?)")
        cdp = pg.context.new_cdp_session(pg)
        n = int(a.seconds * a.fps)
        for i in range(n):
            if i: pg.evaluate(f"__adv({1000 / a.fps})")
            pg.evaluate(NEXT)
            shot = cdp.send("Page.captureScreenshot", {"format": "png"})
            (frames / f"f{i:05d}.png").write_bytes(base64.b64decode(shot["data"]))
            if i % 24 == 0: print(f"{a.shot}: frame {i}/{n}", flush=True)
        b.close()
    if a.grade:
        fades = f",fade=t=in:st=0:d=0.5,fade=t=out:st={a.seconds - 0.6:.2f}:d=0.6" if a.seconds >= 2 else ""
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", str(frames / "f%05d.png"),
                        "-filter_complex", GRADE.format(fades=fades), "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                        "-movflags", "+faststart", str(out.with_suffix(".mp4"))], check=True)
        print("wrote", out.with_suffix(".mp4"))


if __name__ == "__main__":
    main()
