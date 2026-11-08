"""HTML for a brain-likeness result: the score, one row per signature showing the real-worm range and
where the system falls, and how to read it. Self-contained (no scripts, no external files)."""
from __future__ import annotations

import html

from .signatures import ABOUT, LABELS, SIGNATURES

INK, MUTED, RULE = "#1f2328", "#5b636b", "#d6d9dc"
IN_C, OUT_C, BAND = "#2e7d4f", "#b8443f", "#dcefe2"

CSS = f"""
:root{{color-scheme:light}} *{{box-sizing:border-box}}
body{{margin:0;background:#fff;color:{INK};font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:860px;margin:0 auto;padding:44px 22px 80px}}
h1{{font:600 30px/1.2 Georgia,"Iowan Old Style",serif;margin:0 0 6px}}
h2{{font:600 21px/1.3 Georgia,"Iowan Old Style",serif;margin:40px 0 10px}}
p{{margin:0 0 12px;max-width:68ch}} .meta{{color:{MUTED};font-size:14px;margin-bottom:22px}}
.big{{font:600 44px/1 Georgia,serif;margin:6px 0 2px}} .big small{{font-size:20px;color:{MUTED};font-weight:400}}
.note{{background:#f6f7f8;border-left:3px solid {RULE};padding:8px 12px;font-size:15px}}
.warn{{background:#fbefee;border-left:3px solid {OUT_C};padding:8px 12px}}
table{{border-collapse:collapse;font-variant-numeric:tabular-nums}} th,td{{padding:6px 14px 6px 0;text-align:left;border-bottom:1px solid #eceef0}}
th{{font-weight:600}} td.num{{text-align:right}} .in{{color:{IN_C};font-weight:600}} .out{{color:{OUT_C};font-weight:600}}
ul{{padding-left:20px;max-width:68ch}} li{{margin-bottom:6px}}
code{{font:14px ui-monospace,SFMono-Regular,Menlo,monospace;background:#f3f4f5;padding:1px 5px;border-radius:4px}}
footer{{margin-top:50px;color:{MUTED};font-size:13px;border-top:1px solid {RULE};padding-top:12px}}
"""


def _e(s) -> str:
    return html.escape(str(s), quote=True)


def _fmt(v, k):
    if v is None:
        return "not measured"
    v = float(v)
    return f"{v:.1f} s" if k == "timescale" else f"{v:+.2f}" if k == "tiring" else f"{v:.3f}"


def profile_svg(sig: dict) -> str:
    """One row per signature on a common scale: distance from the worm median in units of the worm range
    (the green band, -1 to +1). The dot is the system; values beyond +-6 are drawn at the edge."""
    W, left, width, row = 760, 210, 500, 34
    H = 50 + row * len(SIGNATURES) + 30
    lo, hi = -6.0, 6.0

    def X(d):
        return left + (max(min(d, hi), lo) - lo) / (hi - lo) * width
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;font:13px system-ui,sans-serif" role="img" '
           f'aria-label="Each signature against the real worm range">',
           f'<rect x="{X(-1):.1f}" y="30" width="{X(1) - X(-1):.1f}" height="{row * len(SIGNATURES)}" fill="{BAND}"/>',
           f'<line x1="{X(0):.1f}" x2="{X(0):.1f}" y1="26" y2="{30 + row * len(SIGNATURES)}" stroke="{IN_C}" stroke-width="1.5"/>',
           f'<text x="{X(0):.1f}" y="20" text-anchor="middle" fill="{IN_C}">real worms</text>',
           f'<text x="{left}" y="20" fill="{MUTED}">lower</text>',
           f'<text x="{left + width}" y="20" text-anchor="end" fill="{MUTED}">higher</text>']
    for t in (-6, -3, 3, 6):
        out.append(f'<text x="{X(t):.1f}" y="{H - 8}" text-anchor="middle" fill="{MUTED}">{t:+d}</text>')
    for i, k in enumerate(SIGNATURES):
        s = sig.get(k, {})
        cy = 30 + row * i + row / 2
        out.append(f'<text x="0" y="{cy + 4:.1f}" fill="{INK}">{_e(LABELS[k])}<title>{_e(ABOUT[k])}</title></text>')
        out.append(f'<line x1="{left}" x2="{left + width}" y1="{cy:.1f}" y2="{cy:.1f}" stroke="#eceef0"/>')
        d = s.get("distance")
        if d is None:
            out.append(f'<text x="{left + width / 2:.1f}" y="{cy + 4:.1f}" fill="{MUTED}" text-anchor="middle">not measured</text>')
            continue
        c = IN_C if s.get("inside") else OUT_C
        cx = X(d)
        tip = (f'{LABELS[k]}: {_fmt(s.get("value"), k)}; real worms {_fmt(s.get("worm_low"), k)} to '
               f'{_fmt(s.get("worm_high"), k)} (median {_fmt(s.get("worm_median"), k)})')
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6.5" fill="{c}" stroke="#fff" stroke-width="1.5"><title>{_e(tip)}</title></circle>')
        if abs(d) > hi:
            out.append(f'<text x="{cx + (12 if d > 0 else -12):.1f}" y="{cy + 4:.1f}" text-anchor="{"start" if d > 0 else "end"}" '
                       f'fill="{MUTED}" font-size="11">{d:+.0f}</text>')
    out.append("</svg>")
    return "\n".join(out)


def render(res: dict, name: str, meta: dict | None = None) -> str:
    meta = meta or {}
    sig = res["signatures"]
    rows = "".join(
        f"<tr><th scope='row' title='{_e(ABOUT[k])}'>{_e(LABELS[k])}</th><td class='num' title='{_e(sig[k].get('missing', ''))}'>"
        f"{_fmt(sig[k].get('value'), k) if not sig[k].get('missing') else 'not read'}</td>"
        f"<td class='num'>{_fmt(sig[k].get('worm_low'), k)} to {_fmt(sig[k].get('worm_high'), k)}</td>"
        f"<td class='{'in' if sig[k].get('inside') else 'out'}'>{'inside' if sig[k].get('inside') else 'outside'}</td></tr>"
        for k in SIGNATURES)
    m = res.get("measured", {})
    sub = ""
    if res["valid"] and res.get("score_step_free") is not None:
        dsf = res.get("distance_step_free")
        sub = (f"<p class='meta'>{int(res['score_step_free'])} of {int(res['out_of_step_free'])} on the six signatures that "
               "do not depend on the declared step length (all but slow activity and timescale)"
               + (f", distance {float(dsf):.2f}" if dsf is not None else "") + ".</p>")
    checks = res.get("noise_check") or []
    if checks:
        cells = "".join(f"<td class='num'>{int(c['score']) if c['valid'] else 'not scored'}</td>" for c in checks)
        heads = "".join(f"<th>{float(c['factor']):g} x noise ({float(c['noise_sd']):.3g})</th>" for c in checks)
        sub += ("<p class='meta'>The same model at other noise levels (push recalibrated each time):</p>"
                f"<table><thead><tr><th>declared noise ({res.get('noise_sd', float('nan')):.3g})</th>{heads}</tr></thead>"
                f"<tbody><tr><td class='num'>{int(res['score']) if res['valid'] else 'not scored'}</td>{cells}</tr></tbody></table>")
    flags = []
    if meta.get("tuned"):
        flags.append("The submitter says this system was tuned against this test.")
    if meta.get("mode") == "recordings":
        flags.append("Recordings supplied by the system's owner: the test checks that pushes visibly moved the pushed "
                     "units, but cannot check how the recordings were made.")
    desc_flags = "".join(f"<p class='note'>{_e(f)}</p>" for f in flags)
    dist = res.get("mean_abs_distance")
    dline = (f"<p class='meta'>Distance from real worms: <b>{float(dist):.2f}</b>. For comparison: groups of real worms the "
             "reference never saw 0.36 to 0.65; a worm emulator fitted to the atlas 0.86 to 1.08; untrained recurrent, "
             "spiking, gated and transformer networks 3.8 to 5.4.</p>") if dist is not None else ""
    head = (f"<p class='big'>{int(res['score']) if res['valid'] else ''}<small> of {int(res['out_of'])} signatures inside the real-worm range</small></p>"
            + dline + sub + desc_flags if res["valid"] else
            "<p class='warn'><b>Not scored.</b> " + _e("; ".join(res["problems"])) + ". The signatures below are shown for "
            "information only.</p>" + desc_flags)
    def _num(v, f="{:.0f}"):
        try:
            return f.format(float(v))
        except (TypeError, ValueError):
            return "?"
    bits = [f"{_num(m.get('n_runs'))} runs", f"{_num(m.get('units_per_run'))} units recorded per run",
            f"{_num(m.get('n_pushes'))} pushes", f"pushed units moved {_num(m.get('poked_response'), '{:.2f}')} SD (worms 1.6)",
            _e(res.get("how", "")), f"schedule {_e(res.get('schedule', ''))}"]
    desc = f"<p>{_e(meta['description'])}</p>" if meta.get("description") else ""
    desc += "".join(f"<p class='note'>{_e(n)}</p>" for n in res.get("notes", []))
    by = f" by {_e(meta['author'])}" if meta.get("author") else ""
    body = [f"<h1>{_e(name)}</h1>", f"<p class='meta'>Brain-likeness test{by} · {' · '.join(b for b in bits if b)}</p>", desc,
            head,
            "<p>Each signature is measured on this system and on real <i>C. elegans</i> worms the same way: 30 runs of "
            "about 32 minutes, 45 recorded units each, a 2 s push to one unit every 31 s with two slots left empty, as in "
            "the signal propagation atlas (Randi et al. 2023). The green band is the range spanned by groups of 30 real worms; a dot inside it means a real worm group "
            "could have produced this value. Distances are in units of that range.</p>",
            profile_svg(sig),
            "<h2>Values</h2><table><thead><tr><th>Signature</th><th>This system</th><th>Real worm groups (95%)</th><th></th></tr></thead>"
            f"<tbody>{rows}</tbody></table>",
            "<h2>What each signature means</h2><ul>" + "".join(f"<li><b>{_e(LABELS[k])}.</b> {_e(ABOUT[k])}</li>" for k in SIGNATURES) + "</ul>",
            "<h2>Limits</h2><ul>"
            "<li>One reference animal: immobilised <i>C. elegans</i> under light pushes every 30 s. A system that matches it is "
            "worm-like in these conditions, not brain-like in general.</li>"
            "<li>Ranges are for groups of 30 runs. With 30 runs of your system, being inside means no difference from real "
            "worm groups was detected, not that the system is the same.</li>"
            "<li>Two signatures depend on the time scale you declared (step_seconds): slow activity and timescale.</li>"
            "<li>The noise you run with shapes ongoing activity; a system with no ongoing activity cannot match a brain at rest.</li>"
            "</ul>",
            "<footer>Brain-likeness test, protocol version 2 (9 Nov 2026). Reference: Randi et al. 2023 signal propagation atlas "
            "(CC BY 4.0), summary numbers only.</footer>"]
    return ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{_e(name)}: brain-likeness</title><style>{CSS}</style></head><body><main>" + "\n".join(body) + "</main></body></html>")
