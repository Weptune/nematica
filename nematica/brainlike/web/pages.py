"""HTML for the website. Plain server-rendered pages, one small script (the submission form), no external files."""
from __future__ import annotations

import html
import json
import os
import time

from .. import report as R
from ..signatures import ABOUT, LABELS, SIGNATURES

# Where the test is served: "" at the root of its own site, "/test" when it sits inside the NEMATICA site.
BASE = os.environ.get("BRAINLIKE_BASE", "").rstrip("/")

INK, MUTED, RULE, IN_C, OUT_C, BAND = R.INK, R.MUTED, R.RULE, R.IN_C, R.OUT_C, R.BAND

CSS = R.CSS + f"""
nav{{display:flex;flex-wrap:wrap;gap:6px 22px;align-items:baseline;border-bottom:1px solid {RULE};padding-bottom:12px;margin-bottom:34px;font-size:15px}}
nav a{{color:{INK};text-decoration:none}} nav a:hover,nav a:focus-visible{{text-decoration:underline}}
nav .home{{font:600 17px Georgia,serif;margin-right:auto}} nav .site{{color:{MUTED}}}
a{{color:#1d5c8f}} a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible{{outline:2px solid #1d5c8f;outline-offset:2px}}
.lede{{font-size:18px;max-width:62ch}}
h1.hero{{font-size:38px;max-width:20ch;margin-bottom:14px}}
figure{{margin:26px 0 8px}} figcaption{{color:{MUTED};font-size:14px;max-width:68ch;margin-top:6px}}
.ways{{display:grid;gap:10px;margin:8px 0 18px}}
.way{{display:grid;grid-template-columns:22px 1fr;gap:4px 10px;border:1px solid {RULE};border-radius:6px;padding:12px 14px;cursor:pointer}}
.way:has(input:checked){{border-color:{IN_C};background:#f4faf6}}
.way input{{margin-top:5px}} .way b{{font-weight:600}} .way span{{grid-column:2;color:{MUTED};font-size:15px}}
.way.off{{opacity:.55;cursor:not-allowed}}
label.f{{display:block;font-weight:600;margin:14px 0 4px}} label.f small{{font-weight:400;color:{MUTED}}}
input[type=text],input[type=number],textarea{{font:inherit;width:100%;max-width:520px;padding:7px 9px;border:1px solid #b9bec3;border-radius:5px}}
textarea{{min-height:70px}} input[type=file]{{font:inherit}}
.check{{display:flex;gap:8px;align-items:baseline;margin-top:14px}}
button{{font:600 16px system-ui,sans-serif;background:{IN_C};color:#fff;border:0;border-radius:6px;padding:10px 20px;margin-top:20px;cursor:pointer}}
button:hover{{background:#256841}}
.inline{{display:flex;flex-wrap:wrap;gap:10px;align-items:end}} .inline label{{font-size:14px;color:{MUTED}}}
.inline input{{width:130px}} .inline button{{margin:0;padding:8px 14px;font-size:14px}}
.board td a{{color:{INK}}} .ref{{color:{MUTED};font-size:13px}}
.score{{font:600 18px Georgia,serif}} .score small{{font:13px system-ui;color:{MUTED}}}
pre{{background:#f3f4f5;border-radius:6px;padding:12px 14px;overflow-x:auto;font:13.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;max-width:100%}}
pre code{{background:none;padding:0}}
.status{{font:600 24px Georgia,serif;margin:20px 0 8px}}
@media (max-width:600px){{h1.hero{{font-size:29px}} main{{padding-top:24px}}}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
"""


def _e(s) -> str:
    return html.escape(str(s), quote=True)


def nav() -> str:
    back = "<a class='site' href='@site/'>NEMATICA site</a>" if BASE else ""
    return ("<nav aria-label='Site'><a class='home' href='/'>Brain-likeness test</a><a href='/#submit'>Submit a system</a>"
            "<a href='/how'>How it works</a><a href='/leaderboard'>Leaderboard</a>" + back + "</nav>")


def _based(doc: str) -> str:
    """Prefix the test's own links with BASE; '@site/' is the front page of the site around it."""
    if BASE:
        doc = doc.replace("href='/", f"href='{BASE}/").replace("action='/", f"action='{BASE}/").replace(">/r/", f">{BASE}/r/")
    return doc.replace("href='@site/'", "href='/'")


def page(title: str, body: str, refresh: int | None = None) -> str:
    meta = f"<meta http-equiv='refresh' content='{refresh}'>" if refresh else ""
    return _based("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>" + meta +
            f"<title>{_e(title)}</title><style>{CSS}</style></head><body><main>{nav()}{body}"
            "<footer>Reference data: Randi et al. 2023, signal propagation atlas of <i>C. elegans</i> (CC BY 4.0), "
            "summary numbers only. Protocol version 3 (9 Nov 2026).</footer></main></body></html>")


def with_nav(report_html: str) -> str:
    """A report page from report.render, with the site's navigation and styles."""
    return _based(report_html.replace("<main>", "<main>" + nav(), 1).replace("</style>", CSS[len(R.CSS):] + "</style>", 1))


# ---------------------------------------------------------------- the comparison figure
def compare_svg(systems: list[tuple[str, dict, str]]) -> str:
    """Several systems on the common scale: one row per signature, one dot per system."""
    W, left, width, row = 760, 210, 500, 34
    n = len(SIGNATURES)
    H = 50 + row * n + 30 + 22 * len(systems)
    lo, hi = -6.0, 6.0

    def X(d):
        return left + (max(min(d, hi), lo) - lo) / (hi - lo) * width
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;font:13px system-ui,sans-serif" role="img" '
           f'aria-label="Signatures of example systems against the real worm range">',
           f'<rect x="{X(-1):.1f}" y="30" width="{X(1) - X(-1):.1f}" height="{row * n}" fill="{BAND}"/>',
           f'<line x1="{X(0):.1f}" x2="{X(0):.1f}" y1="26" y2="{30 + row * n}" stroke="{IN_C}" stroke-width="1.5"/>',
           f'<text x="{X(0):.1f}" y="20" text-anchor="middle" fill="{IN_C}">real worms</text>',
           f'<text x="{left}" y="20" fill="{MUTED}">lower</text>',
           f'<text x="{left + width}" y="20" text-anchor="end" fill="{MUTED}">higher</text>']
    for t in (-6, -3, 3, 6):
        out.append(f'<text x="{X(t):.1f}" y="{30 + row * n + 18}" text-anchor="middle" fill="{MUTED}">{t:+d}</text>')
    off = [(j - (len(systems) - 1) / 2) * 7 for j in range(len(systems))]
    for i, k in enumerate(SIGNATURES):
        cy = 30 + row * i + row / 2
        out.append(f'<text x="0" y="{cy + 4:.1f}" fill="{INK}">{_e(LABELS[k])}<title>{_e(ABOUT[k])}</title></text>')
        out.append(f'<line x1="{left}" x2="{left + width}" y1="{cy:.1f}" y2="{cy:.1f}" stroke="#eceef0"/>')
        for j, (label, sig, color) in enumerate(systems):
            d = (sig.get(k) or {}).get("distance")
            if d is None:
                continue
            shape = (f'<circle cx="{X(d):.1f}" cy="{cy + off[j]:.1f}" r="6" fill="{color}" stroke="#fff" stroke-width="1.5">'
                     if j % 2 == 0 else
                     f'<rect x="{X(d) - 5.5:.1f}" y="{cy + off[j] - 5.5:.1f}" width="11" height="11" fill="{color}" '
                     f'stroke="#fff" stroke-width="1.5">')
            out.append(shape + f'<title>{_e(label)}: {d:+.1f}</title>' + ("</circle>" if j % 2 == 0 else "</rect>"))
    y = 30 + row * n + 44
    for j, (label, _, color) in enumerate(systems):
        mark = (f'<circle cx="{left + 6}" cy="{y - 4}" r="6" fill="{color}"/>' if j % 2 == 0 else
                f'<rect x="{left}" y="{y - 10}" width="11" height="11" fill="{color}"/>')
        out.append(mark + f'<text x="{left + 18}" y="{y}" fill="{INK}">{_e(label)}</text>')
        y += 22
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- pages
WAYS = [
    ("recordings", "Upload recordings",
     "Run your system anywhere, in any language, on any hardware: spiking chips, simulators, wet-lab organoids. "
     "Download the schedule, record the listed units and give the listed pushes, upload the recordings (.npz)."),
    ("model", "Upload a model",
     "A rate network as weights (.npz) or any recurrent model exported to ONNX, one step at a time. The server runs "
     "it, sets the push strength and records it."),
    ("python", "Upload Python code",
     "A class with one method, run(), that does whatever your system does. Runs here only if this server has "
     "a sandbox; you can always run it on your own machine with the nematica package."),
]


def _board_rows(rows) -> str:
    if not rows:
        return "<p>No public results yet. Submit the first one.</p>"
    out = ["<table class='board'><thead><tr><th>#</th><th>System</th>"
           "<th title='Average distance from the real-worm median over the eight signatures, in units of the real-worm "
           "range (each capped at 10). Real worm groups: 0.29 to 0.60.'>Distance from real worms</th>"
           "<th>Signatures inside</th></tr></thead><tbody>"]
    for i, r in enumerate(rows, 1):
        tags = [r["author"]] if r.get("author") else []
        if r.get("mode") == "recordings":
            tags.append("recordings supplied by the owner")
        if r.get("tuned"):
            tags.append("tuned against this test")
        who = f"<br><span class='ref'>{_e('; '.join(tags))}</span>" if tags else ""
        out.append(f"<tr><td>{i}</td><td><a href='/r/{_e(r['id'])}'>{_e(r['name'])}</a>{who}</td>"
                   f"<td class='score'>{float(r['distance']):.2f}</td>"
                   f"<td class='num'>{int(r['score'])} of {int(r['out_of'])}</td></tr>")
    out.append("</tbody></table>")
    return "".join(out)


def home(board: list[dict], allow_code: bool, limits: dict, examples: list[tuple[str, dict, str]] | None = None) -> str:
    ways = []
    for key, title, text in WAYS:
        off = key == "python" and not allow_code
        ways.append(f"<label class='way{' off' if off else ''}'><input type='radio' name='mode' value='{key}' "
                    f"{'disabled' if off else ''} {'checked' if key == 'model' else ''} required>"
                    f"<b>{_e(title)}</b><span>{_e(text)}"
                    f"{' Not accepted on this server.' if off else ''} Up to {limits[key]} MB.</span></label>")
    fig = ""
    if examples:
        fig = ("<figure>" + compare_svg(examples) + "<figcaption>Each row is one signature of activity. The green band is "
               "the range real worm groups span. A group of real worms the test never saw lands inside on most rows; a "
               "worm emulator fitted to the atlas lands close; a random recurrent network lands far outside on almost "
               "all of them.</figcaption></figure>")
    body = f"""
<h1 class='hero'>How close is your network to a living nervous system?</h1>
<p class='lede'>Submit any artificial network: a rate RNN, a transformer run step by step, a spiking simulation,
neuromorphic hardware, a brain emulation. The test records it at rest and while briefly pushing single units, measures
eight signatures of its activity, and checks each one against recordings of 113 real <i>C. elegans</i> nervous systems
probed the same way.</p>
{fig}
<h2 id='submit'>Submit a system</h2>
<p>Three ways in. All of them run the same test and give the same score.</p>
<form method='post' action='/submit' enctype='multipart/form-data'>
<fieldset style='border:0;padding:0;margin:0'><legend class='sr' style='font-weight:600;margin-bottom:6px'>What are you uploading?</legend>
<div class='ways'>{''.join(ways)}</div></fieldset>
<label class='f' for='file'>File <small id='hint'>(.npz weights or .onnx model)</small></label>
<input id='file' type='file' name='file' required accept='.npz,.onnx'>
<div id='classbox' hidden><label class='f' for='class_name'>Class name <small>(the BrainLike class in your file)</small></label>
<input id='class_name' type='text' name='class_name' value='System' maxlength='60'></div>
<label class='f' for='name'>Name of your system</label>
<input id='name' type='text' name='name' required maxlength='80' placeholder='e.g. Leaky RNN, 300 units, trained on navigation'>
<label class='f' for='author'>Your name or lab <small>(optional)</small></label>
<input id='author' type='text' name='author' maxlength='80'>
<label class='f' for='description'>What it is <small>(optional; shown on the result page)</small></label>
<textarea id='description' name='description' maxlength='600'></textarea>
<label class='check'><input type='checkbox' name='public' value='1' checked> List the result on the public leaderboard</label>
<label class='check'><input type='checkbox' name='tuned' value='1'> I tuned this system against this test (shown with the result)</label>
<button type='submit'>Run the test</button>
</form>
<h3 style='margin-top:30px'>Schedule for recordings</h3>
<p>If you run your system yourself, the schedule says which units to record and when to push which unit. It depends
only on how many units your system has and how long one step is.</p>
<form class='inline' method='get' action='/schedule'>
<div><label for='nu'>Units in your system</label><br><input id='nu' type='number' name='n_units' min='10' max='1000000' value='300' required></div>
<div><label for='dt'>Seconds per step</label><br><input id='dt' type='number' name='step_seconds' min='0.005' max='2' step='any' value='0.5' required></div>
<button type='submit'>Download schedule</button></form>
<p style='margin-top:10px'>Details for every format are on <a href='/how'>How it works</a>.</p>
<h2>Leaderboard</h2>
{_board_rows(board)}
<p><a href='/leaderboard'>Full leaderboard</a></p>
<script>
(function(){{
  var hints={{model:['.npz,.onnx','(.npz weights or .onnx model)'],recordings:['.npz','(.npz with activity, n_units, step_seconds)'],
             python:['.py','(.py file with your BrainLike class)']}};
  var f=document.getElementById('file'),h=document.getElementById('hint'),c=document.getElementById('classbox');
  document.querySelectorAll('input[name=mode]').forEach(function(r){{r.addEventListener('change',function(){{
    f.accept=hints[r.value][0];h.textContent=hints[r.value][1];c.hidden=r.value!=='python';}});}});
}})();
</script>"""
    return page("Brain-likeness test", body)


def leaderboard(board: list[dict]) -> str:
    body = ("<h1>Leaderboard</h1><p>Valid public results, ranked by distance from real worms: the average, over the "
            "eight signatures, of how far the system sits from the real-worm median in units of the real-worm range. "
            "Groups of real worms the reference never saw sit at 0.29 to 0.60. The number of signatures inside "
            "the range is shown too; it is coarser, and a score of 1 can happen by chance. Entries marked as NEMATICA "
            "references are calibration systems: real worm groups held out of the reference, and baseline networks."
            "</p>" + _board_rows(board) +
            "<p style='margin-top:18px'>The same list as JSON: <a href='/api/leaderboard'><code>/api/leaderboard</code></a>.</p>")
    return page("Leaderboard: brain-likeness test", body)


def status(j: dict, ahead: int) -> str:
    if j["status"] == "failed":
        body = (f"<h1>{_e(j['name'])}</h1><p class='status'>The test could not run</p>"
                f"<p class='warn'>{_e(j['error'] or 'unknown error')}</p>"
                "<p>Fix the file and <a href='/#submit'>submit it again</a>. The formats are on <a href='/how'>How it works</a>.</p>")
        return page(f"{j['name']}: test failed", body)
    waited = int(time.time() - j["created"])
    if j["status"] == "queued":
        msg = ("Next in line." if ahead == 0 else f"Waiting: {ahead} test{'s' if ahead != 1 else ''} ahead.")
    else:
        msg = "Running."
    body = (f"<h1>{_e(j['name'])}</h1><p class='status' role='status'>{msg}</p>"
            f"<p>A model of a few hundred units takes about 2 to 10 minutes; recordings take about a minute. This page "
            f"refreshes itself. Keep the address to come back later: <a href='/r/{_e(j['id'])}'>/r/{_e(j['id'])}</a>.</p>"
            f"<p class='meta'>Submitted {waited // 60} min {waited % 60} s ago.</p>")
    return page(f"{j['name']}: waiting", body, refresh=10)


HOW = """
<h1>How it works</h1>
<p class='lede'>The test asks two things of a system: that its units can be recorded over time, and that one unit can
be given a brief push. Everything else about the system is free.</p>

<h2>What the test does</h2>
<p>It picks up to 120 of your units. In each of 30 runs of about 32 minutes it records 45 of them and, every 31
seconds, gives one recorded unit a 2 second push, leaving 2 slots per run empty so there is as much undisturbed
activity as in the atlas, the way the signal propagation atlas probed real worms with light (Randi et al. 2023). It adds the same small measurement noise to every recording (0.1 SD) and measures eight signatures:</p>
{about}
<p>For each signature the reference is the range spanned by 60 random groups of 30 real worms, widened for the
finite atlas. Your score is the number of signatures inside that range. The profile on the result page shows how far
outside each one is, in units of the real-worm range.</p>
<p>A result counts only if the pushes are visible in the recordings: across at least 300 pushes, the pushed units must
move on average at least 0.75 SD (real worms: 1.6), and at least 0.5 SD more than the other recorded units (real
worms: 1.54). When the server runs your model it finds the push strength that
moves a pushed unit about 1.6 SD itself.</p>
<p>Two signatures, slow activity and timescale, are read in seconds, so they depend on the step length you
declare. Every result also shows the score on the other six. For models the server runs, the result also shows
the score at half and double your declared noise, so a score that rests on one exact noise setting is visible.
If you tuned your system against this test, say so when you submit; it is shown with the result. Results from
uploaded recordings are marked as recordings supplied by the owner.</p>

<h2>Way 1: upload recordings (any system)</h2>
<p>Download the schedule for your system's size and step length (on the <a href='/#submit'>front page</a>, or
<code>/schedule?n_units=300&amp;step_seconds=0.5</code>). It lists the analysis units, and for each of the 30 runs the
units to record and the pushes as <code>[step, unit]</code>. Positions refer to the <code>units</code> list. Then:</p>
<pre><code>import json, numpy as np
s = json.load(open("schedule_300u_0.5s.json"))
units = np.array(s["units"])
activity = np.full((len(s["runs"]), s["steps_per_run"], len(units)), np.nan, np.float32)
for i, run in enumerate(s["runs"]):
    rec = units[run["recorded"]]                              # your unit indices to record
    pushes = [(step, units[p]) for step, p in run["pushes"]]  # push this unit for s["push_steps"] steps
    a = my_system_run(s["steps_per_run"], rec, pushes, s["push_steps"])   # (steps, len(rec))
    activity[i][:, run["recorded"]] = a
np.savez_compressed("recordings.npz", activity=activity, n_units=300, step_seconds=0.5)</code></pre>
<p>Each run should start from a different state, with whatever ongoing input or noise your system normally has.
For fast systems you may average each run into 0.5 s frames first and upload shape
<code>(runs, frames_per_run, units)</code>. Push strength is yours to choose; the test checks that pushed units
visibly respond. Upload limit 400 MB.</p>

<h2>Way 2: upload a model</h2>
<p><b>Rate network (.npz).</b> Arrays <code>W</code> (N by N, <code>W[i, j]</code> from unit j to unit i), optional
<code>b</code>, <code>leak</code> (0 to 1, default 1), <code>nonlinearity</code> (tanh, relu, sigmoid or linear),
<code>noise_sd</code> (default 0.1) and <code>step_seconds</code> (default 0.5). One step:
<code>x = (1 - leak) x + leak (W phi(x) + b + u)</code>; the recorded activity is <code>phi(x)</code>.</p>
<pre><code>np.savez("my_rnn.npz", W=W, b=b, leak=0.2, nonlinearity="tanh", noise_sd=0.3, step_seconds=0.1)</code></pre>
<p><b>Any recurrent model (.onnx).</b> Export one step with inputs <code>state</code> (batch, S) and
<code>input</code> (batch, N), and outputs <code>next_state</code> (batch, S) and optionally <code>activity</code>
(batch, N). The state can hold anything; the N units are what <code>activity</code> reports (without it, the state
itself). The test feeds noise and pushes through <code>input</code>, one value per unit, and checks that a push to unit i
moves unit i more than the others, so route <code>input[:, i]</code> to unit i alone. From PyTorch:</p>
<pre><code>class Step(torch.nn.Module):
    def __init__(self, H):
        super().__init__()
        self.H, self.cell = H, torch.nn.LSTMCell(1, H)
    def forward(self, state, input):
        h, c = self.cell(torch.zeros(len(state), 1), (state[:, :self.H], state[:, self.H:]))
        h = h + input                        # input[:, i] reaches hidden unit i, and only it
        return torch.cat([h, c], 1), h       # next_state, activity: the H hidden units

torch.onnx.export(Step(H), (torch.zeros(1, 2 * H), torch.zeros(1, H)), "model.onnx",
                  input_names=["state", "input"], output_names=["next_state", "activity"],
                  dynamic_axes={{"state": {{0: "b"}}, "input": {{0: "b"}}, "next_state": {{0: "b"}}, "activity": {{0: "b"}}}})</code></pre>
<p>Set <code>noise_sd</code> and <code>step_seconds</code> as ONNX metadata to choose them. Models of up to 4,096
units, 100 MB. Neither format runs Python on the server; ONNX files are parsed by onnxruntime, loaded from
memory so they cannot reach other files.</p>

<h2>Way 3: Python</h2>
<pre><code>from nematica.brainlike import BrainLike, run_python

class System(BrainLike):
    n_units, step_seconds = 300, 0.5
    def run(self, steps, record, pushes, push_steps, rng):
        # simulate `steps` steps from a fresh state; at each (step, unit) in pushes, drive that unit
        # for push_steps steps; return activity of the units in `record`, shape (steps, len(record))
        ...

print(run_python(System()))</code></pre>
<p>Set <code>calibrate_push = True</code> and read <code>self.push_strength</code> to let the test choose the push
strength. On your own machine, <code>python -m nematica brainlike my_system.py</code> writes the same report page.
{code_note}</p>

<h2>What the score means, and what it does not</h2>
<ul>
<li>The reference is one animal, immobilised <i>C. elegans</i>, probed with light every 30 seconds. A system inside
on all eight signatures is worm-like under these conditions. It is not shown to be brain-like in general.</li>
<li>Calibration: groups of real worms held out of the reference sit at a distance of 0.29 to 0.60 (6 to 8 signatures
inside); a worm emulator fitted to the atlas at 0.84 to 1.04; a network with hidden slow drives at the worm's
timescale at 2.32 and a small trained transformer at 3.25; untrained recurrent, spiking, gated and transformer
networks at 4.4 to 6.6. The count of signatures inside is coarse: untrained networks often reach 1 by chance.</li>
<li>Being inside means no difference from real worm groups was detected with 30 runs, not that the system is the same.</li>
<li>Your choices of noise and step length shape the result. Report them with your score.</li>
</ul>
"""


def how(allow_code: bool) -> str:
    about = "<ul>" + "".join(f"<li><b>{_e(LABELS[k])}.</b> {_e(ABOUT[k])}</li>" for k in SIGNATURES) + "</ul>"
    note = ("This server accepts Python files and runs them in a sandbox with no network." if allow_code else
            "This server does not run uploaded Python; run it on your machine and upload the recordings instead.")
    return page("How the brain-likeness test works", HOW.format(about=about, code_note=note))
