"""A self-contained HTML report for one scored copy (no scripts, no external files, no recordings:
only the copy's scores and, optionally, reference copies' scores for comparison).

    python -m nematica report results/scores/my-copy.json [--compare results/scores/baselines/*.json]
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Sequence

import numpy as np

from .bench.verdicts import ALL_LEVELS, LABELS, OTHER_LEVELS, POKE_RULE_LEVELS, REST_LEVELS, answers, rule_text

INK, MUTED, RULE = "#1f2328", "#5b636b", "#d6d9dc"
COL = {"inside": "#2e7d4f", "outside": "#b8443f", "too typical": "#b7862b", "not scored": "#9aa0a6"}
FILL = {"inside": "#e3f1e7", "outside": "#f6e1df", "too typical": "#f5ead3", "not scored": "#eceef0"}
LETTER = {"I": "inside", "O": "outside", "T": "too typical", "-": "not scored"}
LO, HI = -0.6, 1.2                                  # excess axis; values beyond are drawn at the edge


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def _x(v: float, x0: float, w: float) -> float:
    return x0 + (min(max(v, LO), HI) - LO) / (HI - LO) * w


def excess_chart(a: dict, split: str, compare: dict[str, dict]) -> str:
    """One row per level: a dot per pool and seed (colour = that pool's verdict), a dark tick at the
    median; reference copies' medians as open diamonds. Zero = as different from real worms as real
    worms are from each other."""
    d = a[split]
    levels = [lv for lv in ALL_LEVELS if lv in d["levels"]]
    row_h, top, left, width, right = 30, 46, 190, 520, 24
    groups = [("At rest", [lv for lv in REST_LEVELS if lv in levels]),
              ("When poked", [lv for lv in POKE_RULE_LEVELS if lv in levels]),
              ("Reported, not in the rule", [lv for lv in OTHER_LEVELS if lv in levels])]
    n_rows = sum(len(g) for _, g in groups) + sum(1 for _, g in groups if g)
    H = top + n_rows * row_h + 40
    W = left + width + right
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-labelledby="t-{split}" '
           f'style="max-width:{W}px;font:13px/1.3 system-ui,-apple-system,Segoe UI,sans-serif">',
           f'<title id="t-{split}">Excess distance from real worms by level, split {_esc(split)}</title>']
    for t in (-0.5, 0, 0.5, 1.0):
        x = _x(t, left, width)
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 8}" y2="{H - 34}" stroke="{INK if t == 0 else RULE}" '
                   f'stroke-width="{1.5 if t == 0 else 1}"/>')
        out.append(f'<text x="{x:.1f}" y="{H - 18}" text-anchor="middle" fill="{MUTED}">{t:+.1f}</text>'.replace("+0.0", "0"))
    out.append(f'<text x="{_x(0, left, width):.1f}" y="{top - 14}" text-anchor="middle" fill="{INK}">like real worms</text>')
    out.append(f'<text x="{left}" y="{top - 14}" fill="{MUTED}">too typical</text>')
    out.append(f'<text x="{left + width}" y="{top - 14}" text-anchor="end" fill="{MUTED}">too different</text>')
    y = top
    for title, lv_list in groups:
        if not lv_list:
            continue
        out.append(f'<text x="0" y="{y + 18}" font-weight="600" fill="{INK}">{_esc(title)}</text>')
        y += row_h
        for lv in lv_list:
            L = d["levels"][lv]
            cy = y + row_h / 2
            out.append(f'<text x="12" y="{cy + 4:.1f}" fill="{INK}">{_esc(L["label"])}</text>')
            out.append(f'<line x1="{left}" x2="{left + width}" y1="{cy:.1f}" y2="{cy:.1f}" stroke="#f0f1f2"/>')
            runs = [r for r in L["per_run"] if r["excess"] is not None]
            for k, r in enumerate(runs):
                jitter = ((k % 5) - 2) * 2.2
                cx = _x(r["excess"], left, width)
                v = r["verdict"] if r["verdict"] in COL else "not scored"
                tip = (f'{L["label"]}, pool {r["fold"] + 1}, seed {r["seed"]}: {v}; excess {r["excess"]:+.3f}'
                       + (f' (interval {r["low"]:+.3f} to {r["high"]:+.3f})' if r["low"] is not None else ""))
                out.append(f'<circle cx="{cx:.1f}" cy="{cy + jitter:.1f}" r="4.2" fill="{COL[v]}" fill-opacity="0.85" '
                           f'stroke="#fff" stroke-width="1.2"><title>{_esc(tip)}</title></circle>')
            if L["excess_median"] is not None:
                mx = _x(L["excess_median"], left, width)
                out.append(f'<line x1="{mx:.1f}" x2="{mx:.1f}" y1="{cy - 10:.1f}" y2="{cy + 10:.1f}" stroke="{INK}" '
                           f'stroke-width="2.5"><title>{_esc(L["label"])}: median excess {L["excess_median"]:+.3f}</title></line>')
            for name, ca in compare.items():
                CL = ca.get(split, {}).get("levels", {}).get(lv)
                if CL and CL["excess_median"] is not None:
                    bx = _x(CL["excess_median"], left, width)
                    out.append(f'<path d="M{bx:.1f},{cy - 6:.1f} l5,6 l-5,6 l-5,-6 z" fill="none" stroke="{MUTED}" '
                               f'stroke-width="1.3"><title>{_esc(name)}: median excess {CL["excess_median"]:+.3f}</title></path>')
            y += row_h
    out.append("</svg>")
    return "\n".join(out)


def verdict_grid(a: dict, split: str) -> str:
    d = a[split]
    seeds = list(next(iter(d["levels"].values()))["letters"].keys()) if d["levels"] else []
    head = "".join(f"<th scope='col'>seed {s}</th>" for s in seeds)
    rows = []
    for title, lvls in (("At rest", REST_LEVELS), ("When poked", POKE_RULE_LEVELS), ("Not in the rule", OTHER_LEVELS)):
        rows.append(f"<tr class='grp'><th colspan='{len(seeds) + 2}' scope='colgroup'>{title}</th></tr>")
        for lv in lvls:
            L = d["levels"].get(lv)
            if not L:
                continue
            cells = []
            for s in seeds:
                letters = L["letters"].get(s, "")
                chips = "".join(f"<span class='chip' style='background:{FILL[LETTER.get(c, 'not scored')]};"
                                f"color:{COL[LETTER.get(c, 'not scored')]}' title='pool {i + 1}: {LETTER.get(c, 'not scored')}'>{c}</span>"
                                for i, c in enumerate(letters))
                ok = letters.count("I") >= 2 and len(letters) >= 3
                cells.append(f"<td class='{'pass' if ok else 'fail'}'>{chips}<span class='sr'>{'passes' if ok else 'fails'}</span></td>")
            rows.append(f"<tr><th scope='row'>{_esc(L['label'])}</th>{''.join(cells)}<td class='num'>{L['passes']}/{len(seeds)}</td></tr>")
    return (f"<table class='grid'><thead><tr><th scope='col'>Level</th>{head}<th scope='col'>Seeds passing</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


CSS = f"""
:root{{color-scheme:light}}
*{{box-sizing:border-box}}
body{{margin:0;background:#fff;color:{INK};font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:880px;margin:0 auto;padding:48px 24px 80px}}
h1{{font:600 30px/1.2 Georgia,"Iowan Old Style",serif;margin:0 0 6px;letter-spacing:-.01em}}
h2{{font:600 21px/1.3 Georgia,"Iowan Old Style",serif;margin:44px 0 10px}}
h3{{font-size:16px;margin:26px 0 6px}}
p{{margin:0 0 12px;max-width:68ch}}
.meta{{color:{MUTED};font-size:14px;margin-bottom:28px}}
.answer{{border-collapse:collapse;margin:8px 0 8px;font-variant-numeric:tabular-nums}}
.answer th,.answer td{{padding:8px 14px 8px 0;text-align:left;border-bottom:1px solid {RULE}}}
.answer td.yes{{color:{COL['inside']};font-weight:600}} .answer td.no{{color:{COL['outside']};font-weight:600}}
.grid{{border-collapse:collapse;font-variant-numeric:tabular-nums;margin:6px 0 4px}}
.grid th,.grid td{{padding:5px 12px 5px 0;text-align:left;font-weight:400}}
.grid thead th{{color:{MUTED};font-size:13px;border-bottom:1px solid {RULE}}}
.grid tr.grp th{{font-weight:600;padding-top:14px}}
.grid td.num{{color:{MUTED}}}
.chip{{display:inline-block;width:22px;height:22px;line-height:22px;text-align:center;border-radius:4px;margin-right:2px;font-weight:600;font-size:13px}}
td.fail .chip{{opacity:.95}} td.fail{{box-shadow:inset 0 -2px 0 {COL['outside']}33}}
.sr{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;color:{MUTED};font-size:14px;margin:6px 0 0}}
.legend span::before{{content:"";display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:-1px;background:var(--c)}}
.legend .med::before{{border-radius:0;width:3px;height:14px;vertical-align:-3px}}
.legend .ref::before{{background:none;border:1.3px solid {MUTED};transform:rotate(45deg);width:8px;height:8px;border-radius:0}}
ul{{padding-left:20px;max-width:68ch}} li{{margin-bottom:6px}}
code{{font:14px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;background:#f3f4f5;padding:1px 5px;border-radius:4px}}
footer{{margin-top:56px;color:{MUTED};font-size:13px;border-top:1px solid {RULE};padding-top:14px}}
@media (max-width:640px){{main{{padding:28px 16px}} h1{{font-size:24px}}}}
"""


def render(report: dict, compare: dict[str, dict] | None = None) -> str:
    name = report.get("copy", "copy")
    rows = report["rows"]
    a = answers(rows)
    comp = {k: answers(v["rows"]) for k, v in (compare or {}).items()}
    meta = report.get("meta", {})
    splits = list(a)
    ans_rows = []
    for s in splits:
        d = a[s]
        n = d["seeds"]
        def cell(k):
            v = d[k]
            return f"<td class='{'yes' if v == n else 'no' if v == 0 else ''}'>{v} of {n} seed{'s' if n > 1 else ''}</td>"
        ans_rows.append(f"<tr><th scope='row'>{_esc(s)}</th>{cell('rest_pass_seeds')}{cell('poke_pass_seeds')}{cell('all_nine_seeds')}</tr>")
    meta_bits = [f"{meta['worms']} real worms" if meta.get("worms") else None,
                 f"{len(splits)} split{'s' if len(splits) > 1 else ''} of 3 held-out pools",
                 f"{a[splits[0]]['seeds']} noise seed{'s' if a[splits[0]]['seeds'] > 1 else ''}" if splits else None,
                 f"scored {meta['date']}" if meta.get("date") else None,
                 f"code {meta['commit']}" if meta.get("commit") else None]
    legend = ("<div class='legend'>"
              f"<span style='--c:{COL['inside']}'>inside in that pool</span>"
              f"<span style='--c:{COL['outside']}'>outside</span>"
              f"<span style='--c:{COL['too typical']}'>too typical</span>"
              f"<span class='med' style='--c:{INK}'>median over pools and seeds</span>"
              + ("".join(f"<span class='ref'>{_esc(k)}</span>" for k in comp) if comp else "")
              + "</div>")
    body = [f"<h1>{_esc(name)} on the NEMATICA worm benchmark</h1>",
            f"<p class='meta'>{' · '.join(b for b in meta_bits if b)}</p>",
            "<h2>The answer</h2>",
            "<table class='answer'><thead><tr><th>Split</th><th>Passes at rest</th><th>Passes when poked</th>"
            "<th>Inside on every level</th></tr></thead><tbody>" + "".join(ans_rows) + "</tbody></table>",
            f"<p>{_esc(rule_text())} Each noise seed is judged on its own.</p>"]
    for s in splits:
        body += [f"<h2>How far from real worms, split {_esc(s)}</h2>",
                 "<p>For each level, the excess distance compares the copy's worms with real worms: 0 means they are as "
                 "different from real worms as real worms are from each other; +0.5 means 50% further; negative means "
                 "closer than real worms ever are to each other. Each dot is one held-out pool under one noise seed. "
                 "Hover a dot for its interval.</p>",
                 excess_chart(a, s, comp), legend,
                 f"<h3>Verdicts, split {_esc(s)}</h3>", verdict_grid(a, s)]
    body += ["<h2>How to read this</h2><ul>",
             "<li><b>Inside is not agreement.</b> It means no difference from real worm-to-worm variation was detected "
             "in that pool. With 3 held-out pools of about 37 worms, small but consistent differences can pass. Look at "
             "the dots: a level whose dots all sit on one side of zero is consistently off, even when it passes.</li>",
             "<li><b>Too typical</b> is a failure too: the copy's worms are closer to real worms than real worms are to "
             "each other, as an average worm would be. Real worms differ from each other, and a good copy should too.</li>",
             "<li><b>Lead and lag</b> has little power: real worms agree with each other on it only weakly (correlation "
             "about 0.03), so most copies sit near zero.</li>",
             "<li><b>Echo time course and echo complexity</b> are reported but are not part of the rule. Echo complexity "
             "mostly measures ongoing activity, not the poke (README, sham checks), and fails for every model tried.</li>",
             "<li>Both splits use the same 113 worms, arranged differently; noise seeds resample only the simulation, not "
             "the fit. Passing both splits under several seeds shows robustness, not confirmation on new animals.</li>",
             "</ul>",
             "<h2>Reproduce</h2>",
             f"<p><code>{_esc(meta.get('command', 'python -m nematica score path/to/copy.py:ClassName'))}</code></p>",
             "<p>Data: Randi et al. 2023 signal propagation atlas (CC BY 4.0), downloaded and converted locally; this "
             "report contains only scores.</p>",
             "<footer>NEMATICA benchmark report. Rule fixed 8 Nov 2026; levels and calibrations in the project README.</footer>"]
    return ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{_esc(name)}: NEMATICA benchmark</title><style>{CSS}</style></head><body><main>"
            + "\n".join(body) + "</main></body></html>")


def write_html(report_path: str | Path, out: str | Path | None = None, compare: Sequence[str | Path] = ()) -> Path:
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    comp = {}
    for p in compare:
        c = json.loads(Path(p).read_text(encoding="utf-8"))
        if c.get("copy") != report.get("copy"):
            comp[c.get("copy", Path(p).stem)] = c
    out = Path(out or Path(report_path).with_suffix(".html"))
    out.write_text(render(report, comp), encoding="utf-8")
    return out
