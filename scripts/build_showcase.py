"""Build the one-page NEMATICA showcase (8 Nov 2026) from the site's regenerated data and the result figures.

Inputs: web/data/local.js and web/data/echo.js (written by scripts/export_site.py --local from the local atlas
copy; derived third-party data, CC BY 4.0, never committed) and the figure PNGs from plot_showcase.py and
plot_post_figures.py. Output: OUT/index.html (not committed, because it embeds the derived data).

Usage:  python scripts/build_showcase.py FIGDIR OUT
"""
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def js_obj(path):
    s = path.read_text(encoding="utf-8")
    return s[s.index("{"):s.rstrip().rstrip(";").rindex("}") + 1]


def main():
    figdir, out = Path(sys.argv[1]), Path(sys.argv[2])
    html = (ROOT / "scripts" / "showcase_template.html").read_text(encoding="utf-8")
    local = json.loads(js_obj(ROOT / "web/data/local.js"))
    keep = {k: local[k] for k in ("worm", "dt", "frames", "classes", "real", "stims")}
    keep["brains"] = {"var3_spontaneous": local["brains"]["var3_spontaneous"]}
    echo = json.loads(js_obj(ROOT / "web/data/echo.js"))
    html = html.replace("__LOCAL__", json.dumps(keep, separators=(",", ":")))
    html = html.replace("__ECHO__", json.dumps(echo, separators=(",", ":")))
    for key, name in (("RVP", "fig-rest-vs-poke.png"), ("FP", "fig-fingerprints.png"),
                      ("CLS", "fig-classifier.png"), ("REC", "fig-repeat-recovery.png")):
        b = base64.b64encode((figdir / name).read_bytes()).decode()
        html = html.replace(f"__IMG_{key}__", "data:image/png;base64," + b)
    assert "__" not in html.replace("__proto__", ""), "unfilled placeholder"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    print("wrote", out / "index.html", len(html) // 1024, "KiB")


if __name__ == "__main__":
    main()
