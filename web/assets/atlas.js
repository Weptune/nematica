/* NEMATICA, the atlas: every drawing on the home page that carries data. Each is an engraved plate: hairline
   rules with graduated ticks, serif numerals, notes written on the figure where the thing they describe is,
   and marks that are lit. Brass is a real animal, a carmine ring is a plain artificial copy, a filled carmine
   mark is a copy given what it lacked, gold dust between two lines is how far real animals sit from each
   other. The scales, numerals and notes are SVG at the page's own pixel size; the marks and their light are
   painted on a canvas under each plate by lumen.js, and where that is missing they are drawn here instead.
   Everything is placed from window.NEMATICA_RESULTS (web/data/results.js, exported by scripts/export_site.py
   from committed result tables). The gradients and patterns live in the sprite at the top of index.html. */
(function () {
  "use strict";
  const R = window.NEMATICA_RESULTS || {};
  const NS = "http://www.w3.org/2000/svg", PI = Math.PI;
  const MO = window.NEMATICA_MOTION, REDUCED = MO ? !MO.on : matchMedia("(prefers-reduced-motion: reduce)").matches;   // as the page opened; the scene and plates follow the switch live
  const C = { bone: "#ece6d6", b2: "rgba(236,230,214,.74)", b3: "rgba(236,230,214,.64)", line: "rgba(236,230,214,.26)",
    hair: "rgba(236,230,214,.13)", ghost: "rgba(236,230,214,.06)", real: "#b68f1b", gilt: "#dcbc62", gold: "#f0cf78",
    copy: "#e03063", lit: "#ff5d88", paper: "#071230", deep: "#040a1c" };
  const HATCH = "url(#hatch)";   // without the canvas of light, real animals' spread is engraved
  const LUM = window.NEMATICA_LUMEN || null;
  const $ = (q, r) => (r || document).querySelector(q), $$ = (q, r) => Array.from((r || document).querySelectorAll(q));
  function el(tag, a, p) { const n = document.createElementNS(NS, tag); for (const k in a || {}) if (a[k] != null) n.setAttribute(k, a[k]); if (p) p.appendChild(n); return n; }
  function tx(p, x, y, s, a) { const t = el("text", Object.assign({ x, y }, a || {}), p); t.textContent = s; return t; }
  const lin = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0)) * (r1 - r0);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const px = (v) => Math.round(v) + 0.5;
  const f2 = (v, d = 2) => (+v).toFixed(d).replace("-", "−");
  const pc = (v) => Math.round(v * 100) + "%";
  const pol = (cx, cy, r, a) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  const med = (a) => { const s = a.slice().sort((x, y) => x - y), n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
  const qt = (a, q) => { const s = a.slice().sort((x, y) => x - y), i = (s.length - 1) * q, lo = Math.floor(i); return s[lo] + (s[Math.min(s.length - 1, lo + 1)] - s[lo]) * (i - lo); };
  function stage(host, h, label) {
    host.innerHTML = "";
    const w = Math.max(280, Math.floor(host.clientWidth));
    const s = el("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}`, class: "show", role: "img", "aria-label": label });
    const L = LUM ? LUM.layer(host, w, h) : null;
    host.appendChild(s);
    return { s, w, L };
  }
  let tipEl;
  function tip(html, e) {
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tip"; document.body.appendChild(tipEl); }
    if (!html) { tipEl.style.opacity = 0; return; }
    tipEl.innerHTML = html; const w = tipEl.offsetWidth, h = tipEl.offsetHeight;
    let x = e.clientX + 16, y = e.clientY + 16; if (x + w > innerWidth - 8) x = e.clientX - w - 16; if (y + h > innerHeight - 8) y = e.clientY - h - 16;
    tipEl.style.left = Math.max(8, x) + "px"; tipEl.style.top = Math.max(8, y) + "px"; tipEl.style.opacity = 1;
  }
  function hover(n, html) { n.addEventListener("pointermove", (e) => tip(typeof html === "function" ? html() : html, e)); n.addEventListener("pointerleave", () => tip(null)); return n; }
  const row = (a, b) => `<div class="row"><span>${a}</span><span>${b}</span></div>`;
  const rv = (n, i, step) => { n.classList.add("rv"); n.style.setProperty("--d", Math.round(i * (step || 18)) + "ms"); return n; };

  // ------------------------------------------------------------------ the plate's vocabulary
  // type: serif italics for what things are, serif numerals on the scales, small sans for the second line
  const it = (size, fill, more) => Object.assign({ "font-size": size, fill: fill || C.bone, class: "sf", "font-style": "italic", "font-weight": 500 }, more || {});
  const num = (more) => Object.assign({ "font-size": 15.5, fill: C.b3, class: "sf", "font-weight": 500 }, more || {});
  const small = (more) => Object.assign({ "font-size": 12.5, fill: C.b2 }, more || {});
  // marks: each is a small light
  const mark = {
    real(p, x, y, r) { const g = el("g", { class: "mk" }, p); el("circle", { cx: x, cy: y, r: r * 3, fill: "url(#gl-real)" }, g); el("circle", { cx: x, cy: y, r, fill: "url(#mk-real)" }, g); return g; },
    full(p, x, y, r) { const g = el("g", { class: "mk" }, p); el("circle", { cx: x, cy: y, r: r * 3, fill: "url(#gl-copy)" }, g); el("circle", { cx: x, cy: y, r, fill: "url(#mk-copy)" }, g); return g; },
    ring(p, x, y, r) { const g = el("g", { class: "mk" }, p); el("circle", { cx: x, cy: y, r, fill: C.paper, stroke: C.lit, "stroke-width": 1.7 }, g); return g; },
  };
  // a mark on a plate: a light on the canvas under it with something over it to rest the pointer on, or a drawn mark
  const KIND = { real: "real", full: "copy", ring: "ring", bone: "bone" };
  function dot(S, kind, x, y, r, i, step) {
    if (!S.L) return rv(kind === "bone" ? el("circle", { cx: x, cy: y, r, fill: C.bone, stroke: C.paper, "stroke-width": 2 }, S.s) : mark[kind](S.s, x, y, r), i, step);
    const st = S.L.star(KIND[kind], x, y, r, i * (step || 18)), c = el("circle", { cx: x, cy: y, r: r + 3, fill: "transparent", class: "mk" }, S.s);
    c.addEventListener("pointerenter", () => S.L.heat(st, 1)); c.addEventListener("pointerleave", () => S.L.heat(st, 0)); c.star = st; return c;
  }
  // a key: small marks and what they stand for, in a row that wraps when it must
  function key(s, x0, y, items, wmax) {
    let x = x0, yy = y;
    items.forEach(([k, t]) => { const g = el("g", {}, s);
      if (k === "band") { el("rect", { x: 0, y: -12, width: 16, height: 13, fill: LUM ? "url(#dust)" : HATCH }, g); el("path", { d: "M0 -12.5h16M0 1.5h16", stroke: C.gilt }, g); }
      else if (k === "light") el("rect", { x: 0, y: -12, width: 16, height: 13, fill: "rgba(236,230,214,.16)" }, g);
      else if (k === "ink") el("path", { d: "M0 -5h16", stroke: C.bone, "stroke-width": 2 }, g);
      else if (k === "tick") el("path", { d: "M8 -13v15", stroke: C.gold, "stroke-width": 1.6 }, g);
      else mark[k](g, 8, -5, k === "ring" ? 4.8 : 5.2);
      const wd = 25 + tx(g, 25, 0, t, it(17.5, C.b2)).getComputedTextLength();
      if (x + wd > wmax && x > x0) { x = x0; yy += 27; }
      g.setAttribute("transform", `translate(${x.toFixed(1)} ${yy})`); x += wd + 30; });
    return yy;
  }
  // a note written on the figure: a line of serif, a smaller line or two under it, and a fine leader to what it is about
  function note(s, x, y, head, sub, o) {
    o = o || {}; const anchor = o.anchor || "start", g = el("g", { class: "note" }, s), tg = el("g", {}, g);
    tx(tg, x, y, head, it(o.size || 20, o.fill || C.bone, { "text-anchor": anchor }));
    (sub || []).forEach((t, i) => tx(tg, x, y + 19 + i * 16, t, small({ "text-anchor": anchor })));
    if (o.plate) { const b = tg.getBBox(); g.insertBefore(el("rect", { x: b.x - 8, y: b.y - 4, width: b.width + 16, height: b.height + 8, fill: C.paper, "fill-opacity": 0.86, rx: 2 }), tg); }
    if (o.to) { const b = tg.getBBox(), tx0 = o.to[0], ty0 = o.to[1], sx = tx0 < b.x ? b.x - 7 : tx0 > b.x + b.width ? b.x + b.width + 7 : clamp(tx0, b.x + 8, b.x + b.width - 8), sy = ty0 < b.y ? b.y - 3 : ty0 > b.y + b.height ? b.y + b.height + 3 : y - 6;
      el("path", { d: `M${sx.toFixed(1)} ${sy.toFixed(1)}L${tx0.toFixed(1)} ${ty0.toFixed(1)}`, stroke: C.b3, "stroke-width": 0.8, fill: "none" }, g); el("circle", { cx: tx0, cy: ty0, r: 2.6, fill: "none", stroke: C.b3, "stroke-width": 0.9 }, g); }
    return g;
  }
  // the spread between real animals: gold dust (or, without the canvas, hatching) between two brass lines, lying along x (a level band) or along y (an upright one)
  function band(s, x, y, w, h, upright, L) {
    if (L) L.band(x, y, w, h, upright); else { el("rect", { x, y, width: w, height: h, fill: "rgba(240,207,120,.07)" }, s); el("rect", { x, y, width: w, height: h, fill: HATCH }, s); }
    el("path", { d: upright ? `M${px(x)} ${y}v${h}M${px(x + w)} ${y}v${h}` : `M${x} ${px(y)}h${w}M${x} ${px(y + h)}h${w}`, stroke: C.gilt, "stroke-opacity": 0.85 }, s);
  }
  // an engraved scale up the left: a rule, long ticks with numerals, short ticks between, and faint lines across at the long ones
  function ruleY(s, x, x1, y, ticks, fmt, sub) {
    el("path", { d: `M${px(x)} ${y(ticks[0])}V${y(ticks[ticks.length - 1])}`, stroke: C.line }, s);
    let long = "", short = "", grid = "";
    ticks.forEach((v, i) => { long += `M${x - 8} ${px(y(v))}H${x}`; if (i) grid += `M${x + 1} ${px(y(v))}H${x1}`; tx(s, x - 14, y(v) + 5, fmt(v), num({ "text-anchor": "end" }));
      if (i < ticks.length - 1) for (let q = 1; q < (sub || 4); q++) short += `M${x - 4} ${px(y(v + ((ticks[i + 1] - v) * q) / (sub || 4)))}H${x}`; });
    el("path", { d: long, stroke: C.b2 }, s); el("path", { d: short, stroke: C.line }, s); el("path", { d: grid, stroke: C.hair, "stroke-dasharray": "1 6" }, s);
    el("path", { d: `M${x} ${px(y(ticks[0]))}H${x1}`, stroke: C.line }, s);
  }
  const titleY = (s, x, y0, y1, t) => tx(s, 0, 0, t, it(17, C.b2, { "text-anchor": "middle", transform: `translate(${x} ${(y0 + y1) / 2}) rotate(-90)` }));
  // a line that glows: a soft wide stroke under a fine one
  function glowLine(s, d, col, w, lit) { if (!lit) el("path", { d, fill: "none", stroke: col, "stroke-width": (w || 2) * 4, "stroke-opacity": 0.12, "stroke-linejoin": "round", "stroke-linecap": "round" }, s);
    const p = el("path", { d, fill: "none", stroke: col, "stroke-width": w || 2, "stroke-linejoin": "round", "stroke-linecap": "round", class: "draw" }, s); p.style.setProperty("--len", Math.ceil(p.getTotalLength())); return p; }

  // ------------------------------------------------------------------ I. the echo
  function echo(host) {
    const pts = (R.restPoke || []).filter((d) => d.poke != null), G = (R.gaps || [])[0] || { band: [0.087, 0.121] };
    const nar = host.clientWidth < 720, H = nar ? 520 : Math.round(clamp(host.clientWidth * 0.46, 480, 560));
    const S = stage(host, H, "Each copy of the worm brain: how many resting-activity tests it passes, against how well its answers to a poke agree with real worms"), { s, w, L } = S;
    const ky = key(s, 2, 20, [["ring", "a copy that only watched"], ["full", "a copy that also learned from pokes"], ["band", "how well two real worms agree"]], w);
    const m = { l: nar ? 50 : 96, r: nar ? 8 : 26, t: ky + 30, b: 72 };
    const x = lin(0.45, nar ? 5.55 : 6.2, m.l, w - m.r), y = lin(-0.008, 0.135, H - m.b, m.t);
    band(s, m.l, y(G.band[1]), w - m.r - m.l, y(G.band[0]) - y(G.band[1]), false, L);
    ruleY(s, m.l, w - m.r, y, [0, 0.04, 0.08, 0.12], f2);
    el("path", { d: `M${m.l} ${px(H - m.b)}H${w - m.r}`, stroke: C.hair }, s);
    for (let k = 1; k <= (nar ? 5 : 6); k++) { el("path", { d: `M${px(x(k))} ${H - m.b}v7`, stroke: C.b2 }, s); tx(s, x(k), H - m.b + 27, String(k), num({ "text-anchor": "middle" })); }
    tx(s, (m.l + w - m.r) / 2, H - 12, nar ? "tests of resting activity passed, of 6" : "how real it looks at rest: tests of resting activity passed, of 6", it(17, C.b2, { "text-anchor": "middle" }));
    if (!nar) titleY(s, 26, m.t, H - m.b, "how real its answers to a poke are");
    const by = {}; pts.forEach((d) => (by[d.rest] = by[d.rest] || []).push(d));
    const r = nar ? 3.1 : 5.6, half = (x(2) - x(1)) * 0.44; let i = 0; const top = {};
    Object.keys(by).sort().forEach((k) => { const placed = [];
      by[k].sort((a, b) => a.poke - b.poke).forEach((d) => { const y0 = y(1 - d.poke); let off = 0, cy = y0, t = 0, lift = 0;
        const clash = () => placed.some((p) => Math.hypot(p.x - (x(+k) + off), p.y - cy) < 2 * r + 1.5);
        while (clash() && lift < 9) { t++; off = (t % 2 ? 1 : -1) * Math.ceil(t / 2) * r * 0.95; if (Math.abs(off) > half) { lift++; t = 0; off = 0; cy = y0 + (lift % 2 ? -1 : 1) * Math.ceil(lift / 2) * (r + 0.6); } }
        placed.push({ x: x(+k) + off, y: cy });
        const learned = d.brain.startsWith("hybrid"), c = dot(S, learned ? "full" : "ring", x(+k) + off, cy, learned ? r : r - 0.8, i++, 9);
        if (!learned) top[k] = Math.max(top[k] || 0, Math.abs(off));
        hover(c, `<b>${learned ? "Learned from pokes too" : "Learned by watching"}</b>${row("Resting tests passed", d.rest + " of 6")}${row("Agreement with real worms", f2(1 - d.poke))}`); }); });
    if (!nar) {
      note(s, w - m.r - 4, y(0.062), "Looks right, answers at random", ["these pass 5 of 6 tests of resting activity"], { anchor: "end", to: [x(5) + (top[5] || 0) + r + 5, y(0.018)] });
      note(s, x(4.5), y(0.1035), "Answers like a second worm", ["once it has learned from pokes"], { plate: true, to: [x(4) + 3 * r + 8, y(0.096)] });
    }
  }

  // ------------------------------------------------------------------ II. the push
  function push(host) {
    const O = R.optoSign; if (!O) return;
    const nar = host.clientWidth < 720, H = nar ? 470 : 540, order = ["Sst", "Vip"];
    const D = O.mice.filter((d) => order.includes(d.line)).sort((a, b) => order.indexOf(a.line) - order.indexOf(b.line) || a.real - b.real);
    const S = stage(host, H, `For ${D.length} mice: the share of brain regions a copy fitted at rest predicted would rise when one kind of inhibitory cell was driven, and the share that did`), { s, w, L } = S;
    const hasP = D.some((d) => d.p != null);
    const ky = key(s, 2, 20, [["ring", "what the copy fitted at rest predicted"], ["real", "what happened when the cells were driven"]].concat(hasP ? [["full", nar ? "a copy given brief pulses" : "what a copy given brief pulses predicted"]] : [], [["light", nar ? "what the light alone does" : `what the light alone does, in ${O.nWT || 27} mice whose cells cannot answer it`]]), w);
    const m = { l: nar ? 50 : 96, r: nar ? 8 : 26, t: ky + (nar ? 74 : 72), b: 84 }, gapG = nar ? 20 : 56, n = D.length;
    const step = (w - m.l - m.r - gapG) / n, y = lin(0, 1, H - m.b, m.t);
    if (L) L.band(m.l, y(O.wt[2]), w - m.l - m.r, y(O.wt[0]) - y(O.wt[2]), false, 0, true);      // what the light alone does: a pale mist, not the gold of the yardstick
    else el("rect", { x: m.l, y: y(O.wt[2]), width: w - m.l - m.r, height: y(O.wt[0]) - y(O.wt[2]), fill: "rgba(236,230,214,.085)" }, s);
    el("path", { d: `M${m.l} ${px(y(O.wt[2]))}H${w - m.r}M${m.l} ${px(y(O.wt[0]))}H${w - m.r}`, stroke: C.line, "stroke-dasharray": "2 4" }, s);
    ruleY(s, m.l, w - m.r, y, [0, 0.25, 0.5, 0.75, 1], pc, 5);
    if (!nar) titleY(s, 26, m.t, H - m.b, "share of brain regions that rise");
    const gid = "pg" + Math.random().toString(36).slice(2, 7), lg = el("linearGradient", { id: gid, gradientUnits: "userSpaceOnUse", x1: 0, y1: y(1), x2: 0, y2: y(0) }, el("defs", {}, s));
    el("stop", { offset: 0, "stop-color": C.lit, "stop-opacity": 0.75 }, lg); el("stop", { offset: 1, "stop-color": C.gold, "stop-opacity": 0.75 }, lg);
    let xi = m.l + (nar ? 4 : 10), g = null, gx0 = 0; const r = nar ? 3.4 : 5.2, groups = [];
    D.forEach((d, i) => { if (d.line !== g) { if (g) { groups.push([g, gx0, xi]); xi += gapG; } g = d.line; gx0 = xi; }
      const cx = xi + step / 2, col = el("g", {}, s);
      if (L) { const hit = L.star("real", cx, y(d.real), r, i * 14 + 260); L.star("ring", cx, y(d.w), r - 0.6, i * 14);      // what was predicted, then light running from it to what happened
        L.beam(cx, y(d.w), cx, y(d.real), "ring", "real", i * 14 + 120, { pulse: true, fall: true, to: hit, off: i * 0.085, per: 7.5, w: 1.3 });
        if (d.p != null) L.star("copy", cx, y(d.p), r - 1.3, i * 14 + 520); }
      else { rv(el("path", { d: `M${cx.toFixed(1)} ${y(d.w)}V${y(d.real)}`, stroke: `url(#${gid})`, "stroke-width": 1.3 }, col), i, 14);
        rv(mark.ring(col, cx, y(d.w), r - 0.6), i, 14); if (d.p != null) rv(mark.full(col, cx, y(d.p), r - 1.3), i, 14); rv(mark.real(col, cx, y(d.real), r), i, 14); }
      hover(el("rect", { x: xi, y: m.t, width: step, height: H - m.t - m.b, fill: "transparent" }, s), `<b>${d.line} mouse ${d.id.replace("sub-", "")}</b>${row("Copy fitted at rest predicted rising", pc(d.w))}${d.p != null ? row("Copy given brief pulses predicted rising", pc(d.p)) : ""}${row("Rose when the cells were driven", pc(d.real))}${row("Light alone, median", pc(O.wt[1]))}`);
      xi += step; });
    groups.push([g, gx0, xi]);
    const cnt = (l) => D.filter((d) => d.line === l).length, said = { Sst: ["The copy said rise. They fell.", "in 29 of 29 mice"], Vip: ["These did rise.", "in 10 of 10 mice"] };
    groups.forEach(([gn, a, b]) => { const mid = (a + b) / 2;
      el("path", { d: `M${a + 2} ${px(H - m.b + 16)}v-5H${b - 2}v5`, stroke: C.line, fill: "none" }, s);
      const edge = nar && b > w - 60, ax = edge ? w - 2 : nar ? a + 2 : mid, an = edge ? "end" : nar ? "start" : "middle";
      tx(s, ax, H - m.b + 42, nar ? `${gn}, ${cnt(gn)} mice` : `${gn} cells, ${cnt(gn)} mice`, it(nar ? 17 : 21, C.bone, { "text-anchor": an }));
      tx(s, ax, H - m.b + 62, gn === "Sst" ? (nar ? "quiet their neighbours" : "they quiet their neighbours") : (nar ? "quiet the quieters" : "they quiet the cells that quiet others"), small({ "text-anchor": an }));
      if (!nar || gn === "Sst") note(s, mid, m.t - 32, nar ? said[gn][0].replace("The copy said rise. ", "Predicted to rise. ") : said[gn][0], [said[gn][1]], { anchor: "middle", size: nar ? 17 : 21 }); });
  }

  // ------------------------------------------------------------------ III. the face
  function face(host) {
    const D = R.shrinkage || []; if (!D.length) return;
    const nar = host.clientWidth < 720, H = nar ? 500 : 560;
    const S = stage(host, H, "As each worm's model is pulled toward the average worm, forecasting skill barely changes while individuality collapses"), { s, w, L } = S;
    const m = { l: nar ? 50 : 96, r: nar ? 12 : 26, t: 62, b: 78 }, lx = (v) => Math.log10(+v);
    const x = lin(lx(D[0].lam), lx(D[D.length - 1].lam), m.l + 26, w - m.r - (nar ? 16 : 210));
    const gapY = 56, ph = (H - m.t - m.b - gapY) / 2;
    const yA = lin(0.69, 0.77, m.t + ph, m.t), yB = lin(0.4, 1.12, H - m.b, H - m.b - ph);
    const iBest = D.reduce((b, d, i) => (d.r2 > D[b].r2 ? i : b), 0), iTrue = D.findIndex((d) => +d.lam === 300);
    const xr = nar ? w - m.r : x(lx(D[D.length - 1].lam)) + 8;
    ruleY(s, m.l, xr, yA, [0.7, 0.73, 0.76], f2, 3); ruleY(s, m.l, xr, yB, [0.5, 0.75, 1], f2, 5);
    band(s, m.l, yB(1.04), xr - m.l, yB(0.96) - yB(1.04), false, L);
    [[iTrue, "the faithful copy"], [iBest, "the best forecaster"]].forEach(([k, t], j) => { const xx = x(lx(D[k].lam)), up = nar && !j ? 20 : 0;
      el("path", { d: `M${px(xx)} ${m.t - 14 - up}V${H - m.b + 8}`, stroke: C.b3, "stroke-dasharray": "2 5" }, s);
      tx(s, xx, m.t - 24 - up, t, it(nar ? 16.5 : 20, C.bone, { "text-anchor": nar ? (j ? "start" : "end") : "middle", dx: nar ? (j ? -30 : 30) : 0 })); });
    const P = (yy, k) => D.map((d) => [x(lx(d.lam)), yy(d[k])]), dOf = (p) => p.map((q, j) => (j ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join("");
    const pA = P(yA, "r2"), pB = P(yB, "ind");
    // what is lost: the space between real worms and the copy
    const lost = pB.filter((q) => q[1] >= yB(1) - 0.5), gid = "fl" + Math.random().toString(36).slice(2, 7), lg = el("linearGradient", { id: gid, x1: 0, y1: 0, x2: 0, y2: 1 }, el("defs", {}, s));
    el("stop", { offset: 0, "stop-color": C.copy, "stop-opacity": 0.03 }, lg); el("stop", { offset: 1, "stop-color": C.copy, "stop-opacity": 0.3 }, lg);
    if (lost.length > 1) rv(el("path", { d: `M${lost[0][0].toFixed(1)} ${yB(1)}` + lost.map((q) => `L${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join("") + `V${yB(1)}Z`, fill: `url(#${gid})` }, s), 40, 20);
    glowLine(s, dOf(pA), C.bone, 2, L); glowLine(s, dOf(pB), C.lit, 2, L);
    if (L) { L.ribbon(pA, "bone", 0, { off: 1.5 }); L.ribbon(pB, "copy", 0, { off: 2.4 }); L.shed(pB, yB(0.96), yB(0.5) - yB(0.96), 1500, nar ? 70 : 150); }      // individuality falling away: embers leave the curve once it sinks under the real worms
    const tipOf = (j) => `<b>Pull toward the average: ${Number(D[j].lam).toLocaleString()}</b>${row("Forecasting skill (R²)", f2(D[j].r2, 3))}${row("Individuality (real worms are 1)", f2(D[j].ind, 2))}`;
    pA.forEach((q, j) => hover(dot(S, "bone", q[0], q[1], 5, j, 190), tipOf(j)));
    pB.forEach((q, j) => hover(dot(S, "full", q[0], q[1], 5.4, j, 190), tipOf(j)));
    const xe = pA[pA.length - 1][0] + 24;
    if (!nar) { note(s, xe, pA[pA.length - 1][1] + 2, "Forecasting skill", ["barely moves"]); note(s, xe, yB(1) + 2, "Real worms", ["are this individual"], { fill: C.gold }); note(s, xe, pB[pB.length - 1][1] + 2, "Individuality", ["falls away"]); }
    else { tx(s, m.l + 8, yA(0.77) + 4, "forecasting skill", it(16.5)); tx(s, m.l + 8, yB(1.12) + 6, "individuality (real worms are 1)", it(16.5)); }
    const xa = pA[0][0], xb = pA[pA.length - 1][0], ya = H - m.b + 30;
    el("path", { d: `M${xa} ${px(ya)}H${xb}m-8 -4.5l8 4.5-8 4.5`, stroke: C.b3, fill: "none" }, s);
    tx(s, xa, ya + 22, nar ? "its own model" : "each worm its own model", small()); tx(s, xb, ya + 22, nar ? "the average one" : "one average model", small({ "text-anchor": "end" }));
    tx(s, (xa + xb) / 2, H - 10, nar ? "pull toward the average worm" : "how hard each worm's model is pulled toward the average worm", it(17, C.b2, { "text-anchor": "middle" }));
  }

  // ------------------------------------------------------------------ IV. the long memory
  function memory(host) {
    const PM = R.permouse; if (!PM) return;
    const D = PM.mice, n = D.length, nar = host.clientWidth < 720, H = nar ? 470 : 560;
    const S = stage(host, H, `Slow memory in ${n} mice, in a random network recorded through each mouse's own instrument, and in the same network with strong slow drives`), { s, w, L } = S;
    const ky = key(s, 2, 20, [["real", "a mouse"], ["ring", nar ? "a random network, recorded alike" : "a random network, recorded as that mouse was"], ["full", "the same network, with strong slow drives"]], w);
    const m = { l: nar ? 50 : 96, r: nar ? 8 : 26, t: ky + 30, b: 62 };
    const x = (i) => m.l + 22 + (i * (w - m.l - m.r - 44)) / (n - 1), y = lin(0, 0.34, H - m.b, m.t);
    ruleY(s, m.l, w - m.r, y, [0, 0.1, 0.2, 0.3], (v) => f2(v, 1), 5);
    if (!nar) titleY(s, 26, m.t, H - m.b, "slow memory");
    const r = nar ? 3.4 : 5.2;
    // the mice, lowest to highest, as one rising line of light
    if (L) L.ribbon(D.map((d, i) => [x(i), y(d.m)]), "real", 200, { w: 1.15, off: 2 });
    else el("path", { d: D.map((d, i) => (i ? "L" : "M") + x(i).toFixed(1) + " " + y(d.m).toFixed(1)).join(""), fill: "none", stroke: C.gold, "stroke-width": 9, "stroke-opacity": 0.1, "stroke-linejoin": "round", "stroke-linecap": "round" }, s);
    D.forEach((d, i) => { const xi = x(i), col = el("g", {}, s);
      if (L) { L.beam(xi, y(d.rnn), xi, y(d.m), "ring", "real", i * 22 + 100, { a: 0.42, w: 1, glow: false });
        if (d.slow != null) L.star("copy", xi, y(d.slow), r - 1.2, i * 22 + 420, 3.2); L.star("ring", xi, y(d.rnn), r - 0.6, i * 22); L.star("real", xi, y(d.m), r, i * 22 + 180); }      // the slow drive shows as a slow swell passing along its marks
      else { rv(el("path", { d: `M${px(xi)} ${y(d.m)}V${y(d.rnn)}`, stroke: C.line }, col), i, 22);
        if (d.slow != null) rv(mark.full(col, xi, y(d.slow), r - 1.2), i, 22);
        rv(mark.ring(col, xi, y(d.rnn), r - 0.6), i, 22); rv(mark.real(col, xi, y(d.m), r), i, 22); }
      hover(el("rect", { x: xi - (w - m.l - m.r) / (2 * n), y: m.t, width: (w - m.l - m.r) / n, height: H - m.t - m.b, fill: "transparent" }, s),
        `<b>Mouse ${i + 1} of ${n}</b>${row("Mouse", f2(d.m, 3))}${row("Random network, recorded like this mouse", f2(d.rnn, 3))}${row("Same network, strong slow drives", d.slow == null ? "not measured" : f2(d.slow, 3))}`); });
    tx(s, (m.l + w - m.r) / 2, H - 12, `${n} mice, in order of their own slow memory`, it(17, C.b2, { "text-anchor": "middle" }));
    if (!nar) { const k = Math.round(n * 0.3);
      note(s, x(k) + 26, y(0.008) - 4, "A random network holds less of the past", [`than the mouse it is recorded like, in ${PM.lower} of ${n}`], { to: [x(k) + 6, y(D[k].rnn) + 4] });
      note(s, x(Math.round(n * 0.52)), y(0.335), "Given strong slow drives, it holds more than any mouse", [], { anchor: "middle" }); }
  }

  // ------------------------------------------------------------------ V. the inner light: a sun on the horizon, one ray for each mouse
  function light(host) {
    const S = R.slowStudy; if (!S) return;
    const nets = [];
    S.families.filter((f) => f.counted).forEach((f) => f.members.forEach((mb) => nets.push({ v: mb.M1[1], t: f.members.length > 1 ? `${f.name} ${mb.label}` : f.name, fam: f.name, lab: mb.label, mb })));
    nets.sort((a, b) => a.v - b.v);
    const tipOf = (o) => `<b>${o.t}</b>${row("Internal share, median over mice", pc(o.v))}${row("Middle half", `${pc(o.mb.M1[0])} to ${pc(o.mb.M1[2])}`)}`;
    const q = S.mice.M1, all = S.mice.M1all, label = "Share of state that is internal, in 49 mice and in each kind of network";
    if (host.clientWidth < 760) return lightStrip(host, S, nets, tipOf, label);
    const H = Math.round(clamp(host.clientWidth * 0.53, 500, 640)), T = stage(host, H, label), { s, w, L } = T;
    const cx = w / 2, cy = H - 92, Rg = Math.min(w * 0.36, H - 196, w / 2 - 190), r0 = Rg * 0.15;
    const ang = (v) => PI - v * PI, at = (v, r) => [cx + r * Math.cos(ang(v)), cy - r * Math.sin(ang(v))];
    const arc = (r, v0, v1) => { const [x0, y0] = at(v0, r), [x1, y1] = at(v1, r); return `M${x0.toFixed(1)} ${y0.toFixed(1)}A${r} ${r} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`; };
    key(s, 2, 20, [["tick", "one mouse"], ["band", "the middle half of the mice"], ["ring", "a kind of network, at its median"]], w);
    const cid = "lc" + Math.random().toString(36).slice(2, 7); el("rect", { x: 0, y: 0, width: w, height: cy }, el("clipPath", { id: cid }, el("defs", {}, s)));
    const sky = el("g", { "clip-path": `url(#${cid})` }, s);
    el("circle", { cx, cy, r: Rg * 0.95, fill: "url(#gl-real)", opacity: 0.55 }, sky);
    // the rays
    all.forEach((v, i) => { const [x0, y0] = at(v, r0 + 12), [x1, y1] = at(v, Rg - 58);
      if (L) L.beam(x0, y0, x1, y1, "real", "real", i * 16 + 200, { pulse: true, a: 0.6, w: 1.25, per: 5 + ((i * 7) % 5), run: 1.5, glint: 0.7 });
      else rv(el("path", { d: `M${x0.toFixed(1)} ${y0.toFixed(1)}L${x1.toFixed(1)} ${y1.toFixed(1)}`, stroke: C.gold, "stroke-width": 1.3, "stroke-opacity": 0.62, "stroke-linecap": "round" }, sky), i, 14); });
    if (ORBS) orbImage(sky, "sun", cx, cy, r0 * 1.05, { spin: 0.8, time: 5 }, "fig", 520);
    else { el("circle", { cx, cy, r: r0 * 2.6, fill: "url(#gl-real)" }, sky); el("circle", { cx, cy, r: r0, fill: "url(#mk-real)" }, sky); }
    // the middle half of the mice, engraved outside the scale
    const [bx0, by0] = at(q[0], Rg + 8), [bx1, by1] = at(q[2], Rg + 8), [bx2, by2] = at(q[2], Rg + 26), [bx3, by3] = at(q[0], Rg + 26);
    const wedge = `M${bx0.toFixed(1)} ${by0.toFixed(1)}A${Rg + 8} ${Rg + 8} 0 0 1 ${bx1.toFixed(1)} ${by1.toFixed(1)}L${bx2.toFixed(1)} ${by2.toFixed(1)}A${Rg + 26} ${Rg + 26} 0 0 0 ${bx3.toFixed(1)} ${by3.toFixed(1)}Z`;
    if (L) { L.arcBand(cx, cy, Rg + 8, Rg + 26, -ang(q[0]), -ang(q[2])); el("path", { d: wedge, fill: "none", stroke: C.gilt, "stroke-opacity": 0.85 }, s); }
    else { el("path", { d: wedge, fill: "rgba(240,207,120,.07)" }, s); el("path", { d: wedge, fill: HATCH, stroke: C.gilt, "stroke-opacity": 0.85 }, s); }
    // the scale: an arc from none of it to all of it
    el("path", { d: arc(Rg, 0, 1), fill: "none", stroke: C.b2 }, s); el("path", { d: arc(Rg - 5, 0, 1), fill: "none", stroke: C.hair }, s);
    let long = "", short = ""; for (let k = 0; k <= 100; k += 1) { const v = k / 100, [x0, y0] = at(v, Rg), [x1, y1] = at(v, Rg - (k % 25 === 0 ? 16 : k % 5 === 0 ? 10 : 5)), seg = `M${x0.toFixed(1)} ${y0.toFixed(1)}L${x1.toFixed(1)} ${y1.toFixed(1)}`; if (k % 5 === 0) long += seg; else short += seg; }
    el("path", { d: long, stroke: C.b2 }, s); el("path", { d: short, stroke: C.line }, s);
    [0.25, 0.5, 0.75].forEach((v) => { const [x, y] = at(v, Rg - 36); tx(s, x, y + 5, pc(v), num({ "text-anchor": "middle" })); });
    el("path", { d: `M${cx - Rg - 70} ${px(cy)}H${cx + Rg + 70}`, stroke: C.line }, s);
    tx(s, cx - Rg, cy + 26, "none of it", num({ "text-anchor": "middle" })); tx(s, cx + Rg, cy + 26, "all of it", num({ "text-anchor": "middle" }));
    tx(s, cx, cy + 30, `${S.mice.n} mice`, it(21, C.gold, { "text-anchor": "middle" }));
    tx(s, cx, H - 12, "share of the brain's state that is its own, not locked to what it sees", it(17, C.b2, { "text-anchor": "middle" }));
    // the networks: rings on the scale, each named outside it; two that sit together share a name
    const groups = []; nets.forEach((o) => { const g = groups[groups.length - 1]; if (g && g.fam === o.fam && o.v - g.items[g.items.length - 1].v < 0.012) { g.items.push(o); g.t += " and " + o.lab; } else groups.push({ fam: o.fam, t: o.t, items: [o] }); });
    const boxes = [];
    groups.forEach((g, i) => { const v = g.items.reduce((a, o) => a + o.v, 0) / g.items.length, c = Math.cos(ang(v)), anchor = c > 0.28 ? "start" : c < -0.28 ? "end" : "middle", inBand = v > q[0] - 0.01 && v < q[2] + 0.01;
      const t = tx(s, 0, 0, g.t, it(19)), tw = t.getComputedTextLength(); let lane = 0, bx, by, box;
      do { const [lx, ly] = at(v, Rg + (inBand ? 50 : 40) + lane * 27); bx = anchor === "start" ? lx : anchor === "end" ? lx - tw : lx - tw / 2; by = ly; box = [bx - 8, by - 20, bx + tw + 8, by + 8]; lane++; }
      while (boxes.some((b) => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1]) && lane < 5);
      boxes.push(box); t.setAttribute("x", bx); t.setAttribute("y", by + (anchor === "middle" ? 0 : 6));
      const [l0x, l0y] = at(v, Rg + 9), [l1x, l1y] = at(v, Rg + (inBand ? 50 : 40) + (lane - 1) * 27 - (anchor === "middle" ? 22 : 6));
      el("path", { d: `M${l0x.toFixed(1)} ${l0y.toFixed(1)}L${l1x.toFixed(1)} ${l1y.toFixed(1)}`, stroke: C.lit, "stroke-opacity": 0.6 }, s);
      g.items.forEach((o, j) => { const [x, y] = at(o.v, Rg), c = hover(dot(T, "ring", x, y, 7, i + j, 70), tipOf(o)); hover(t, tipOf(o));
        if (c.star) { t.addEventListener("pointerenter", () => L.heat(c.star, 1)); t.addEventListener("pointerleave", () => L.heat(c.star, 0)); } }); });
  }
  // on a narrow screen the same thing is a straight scale
  function lightStrip(host, S, nets, tipOf, label) {
    const H = 470, T = stage(host, H, label), { s, w, L } = T, m = { l: 14, r: 14 }, x = lin(0, 1, m.l, w - m.r), q = S.mice.M1;
    const ky = key(s, 2, 20, [["tick", "one mouse"], ["band", "the middle half of the mice"], ["ring", "a kind of network"]], w), ya = Math.round((ky + 30 + H - 50) / 2);
    band(s, x(q[0]), ya - 62, x(q[2]) - x(q[0]), 124, true, L);
    S.mice.M1all.forEach((v, i) => rv(el("path", { d: `M${px(x(v))} ${ya - 14}V${ya + 14}`, stroke: C.gold, "stroke-width": 1.5, "stroke-opacity": 0.8 }, s), i, 12));
    el("path", { d: `M${m.l} ${px(ya)}H${w - m.r}`, stroke: C.b2 }, s);
    [0, 0.25, 0.5, 0.75, 1].forEach((v) => { el("path", { d: `M${px(x(v))} ${ya - 6}V${ya + 6}`, stroke: C.b2 }, s); tx(s, x(v), H - 34, v === 0 ? "none" : v === 1 ? "all" : pc(v), num({ "text-anchor": v === 0 ? "start" : v === 1 ? "end" : "middle" })); });
    tx(s, w / 2, H - 10, "share of state that is internal", it(16.5, C.b2, { "text-anchor": "middle" }));
    const up = [], dn = [];
    nets.forEach((o, i) => { const isUp = i % 2 === 0, lanes = isUp ? up : dn, t = tx(s, 0, 0, o.t, it(15.5)), tw = t.getComputedTextLength(), lx = clamp(x(o.v) - tw / 2, m.l, w - m.r - tw);
      let k = 0; while ((lanes[k] || []).some((b) => lx < b[1] + 12 && lx + tw > b[0] - 12)) k++; (lanes[k] = lanes[k] || []).push([lx, lx + tw]);
      const ly = isUp ? ya - 78 - k * 22 : ya + 88 + k * 22; t.setAttribute("x", lx); t.setAttribute("y", ly);
      el("path", { d: `M${px(x(o.v))} ${isUp ? ly + 6 : ya + 8}V${isUp ? ya - 8 : ly - 14}`, stroke: C.lit, "stroke-opacity": 0.55 }, s);
      hover(dot(T, "ring", x(o.v), ya, 5.5, i, 60), tipOf(o)); hover(t, tipOf(o)); });
  }

  // ------------------------------------------------------------------ VI. the waning: a moon for each answer
  const TINT = { real: [1.32, 1.05, 0.56], copy: [1.36, 0.45, 0.62] };
  function moon(s, cx, cy, r, f, kind) {
    if (ORBS) { const g = el("g", { class: "mk" }, s), lz = 2 * f - 1;
      el("circle", { cx, cy, r: r * 1.5, fill: `url(#gl-${kind})`, opacity: 0.3 + 0.45 * f }, g);
      orbImage(g, "moon", cx, cy, r, { light: f > 0.99 ? [-0.38, 0.32, 0.86] : [-Math.sqrt(1 - lz * lz), 0.1, lz], tint: TINT[kind], amb: 0.07, air: 0, spin: kind === "real" ? 0.5 : 2.6 }, kind + f.toFixed(2), 320);
      return g; }
    const g = el("g", { class: "mk" }, s), col = kind === "real" ? C.gold : C.lit;
    el("circle", { cx, cy, r: r * 1.5, fill: `url(#gl-${kind})`, opacity: 0.5 + 0.5 * f }, g);
    el("circle", { cx, cy, r, fill: C.paper, stroke: col, "stroke-width": 1.2, "stroke-opacity": 0.75 }, g);
    if (f >= 0.999) el("circle", { cx, cy, r, fill: `url(#mk-${kind})` }, g);
    else { const rx = r * Math.abs(1 - 2 * f); el("path", { d: `M${cx} ${cy - r}A${r} ${r} 0 0 0 ${cx} ${cy + r}A${rx.toFixed(2)} ${r} 0 0 ${f < 0.5 ? 1 : 0} ${cx} ${cy - r}Z`, fill: `url(#mk-${kind})` }, g); }
    return g;
  }
  function waning(host) {
    const G = (R.gaps || []).find((g) => /same poke/i.test(g.title)) || { band: [0.34, 0.64] }, M = R.waning && R.waning.mouse;
    const lo = G.band[0], hi = G.band[1], mid = (lo + hi) / 2, nar = host.clientWidth < 540;
    const rows = [{ kind: "real", f: mid, name: "A real worm", said: ["second answer: about half", `between ${f2(lo)} and ${f2(hi)} of the first`], short: ["about half", `${f2(lo)} to ${f2(hi)}`], under: ["first answer", "asked again"], band: [lo, hi] }];
    if (M && M.later) rows.push({ kind: "real", f: M.later, name: "A mouse's driven cells", said: ["later answers: about four fifths", `then steady: ${f2(M.fade)} over ten minutes`], short: ["four fifths,", "then steady"], under: ["first flash", "from the third on"] });
    rows.push({ kind: "copy", f: 1, name: "An artificial network", said: ["answers the same every time"], short: ["the same", "every time"], under: ["first answer", "asked again"] });
    const r = nar ? 30 : rows.length > 2 ? 42 : 50, step = nar ? 158 : rows.length > 2 ? 142 : 160, y0 = nar ? 74 : r + 46, H = y0 + step * (rows.length - 1) + r + 44;
    const { s } = stage(host, H, `A real worm's second answer to the same poke is about half its first (between ${lo} and ${hi})${M && M.later ? `; a mouse's driven cells answer later flashes at about four fifths of the first (${f2(M.later)}) and then hold, ${f2(M.fade)} from the start of ten minutes of light to the end` : ""}; an artificial network's second answer equals its first`);
    const x1 = r * 1.5 + 2, x2 = x1 + r * 2 + (nar ? 44 : 76);
    rows.forEach((o, k) => { const yy = y0 + k * step;
      rv(moon(s, x1, yy, r, 1, o.kind), k * 4, 120); rv(moon(s, x2, yy, r, o.f, o.kind), k * 4 + 2, 120);
      if (!k) moon(s, x2, yy, r, 1, o.kind).classList.add("wane");      // asked again, the real worm's answer is seen to fade: a full moon over the waned one, which then goes
      el("path", { d: `M${x1 + r + 10} ${px(yy)}H${x2 - r - 12}m-7 -4.5l7 4.5-7 4.5`, fill: "none", stroke: C.b3 }, s);
      if (o.band) o.band.forEach((v) => { const rx = r * Math.abs(1 - 2 * v);
        el("path", { d: `M${x2} ${yy - r}A${rx.toFixed(2)} ${r} 0 0 ${v < 0.5 ? 0 : 1} ${x2} ${yy + r}`, fill: "none", stroke: C.bone, "stroke-dasharray": "2 4", "stroke-opacity": 0.85 }, s); });
      const lx = x2 + r + (nar ? 14 : 30);
      if (nar) { tx(s, 0, yy - r - 16, o.name, it(20)); tx(s, lx, yy - 4, o.short[0], small()); tx(s, lx, yy + 14, o.short[1], small({ fill: C.b3 })); }
      else note(s, lx, yy - 6, o.name, o.said, { size: 25 });
      tx(s, x1, yy + r + 24, o.under[0], small({ "text-anchor": "middle", fill: C.b3 })); tx(s, x2, yy + r + 24, o.under[1], small({ "text-anchor": "middle", fill: C.b3 }));
    });
  }

  // ------------------------------------------------------------------ VII. the journey: six tests, three trials
  function journey(host) {
    const E = R.emulator, J = R.journey; if (!E || !J) return;
    const span = (v) => [Math.min(...v), Math.max(...v)];
    const rows = [["On the worms it was built on", "the recipe, held-still worms", span((E.atlas_cv3 || []).map((d) => d.rest))], ["On worms that move", "the same recipe, refitted, another lab", span(J.frozen)],
      ["On worms that move", "a plain copy fitted to rest alone", span(J.plain)], ["On worms that move", "the recipe, given what it lacked", span(J.given)]];
    const nar = host.clientWidth < 580, rowH = nar ? 118 : 100, H = rowH * rows.length + (nar ? 26 : 34);
    const said = (v) => (v[0] === v[1] ? `${v[0]}` : v[1] - v[0] === 1 ? `${v[0]} or ${v[1]}` : `${v[0]} to ${v[1]}`);
    const { s } = stage(host, H, `Of six tests of ongoing activity, the recipe passes ${said(rows[0][2])} on the worms it was built on and ${said(rows[1][2])} on freely moving worms, where a plain copy fitted to rest passes ${said(rows[2][2])}; given the coupling and the skew it lacked, it passes ${said(rows[3][2])}, short of the pass mark of five`);
    const r = nar ? 13 : 16, gap = nar ? 10 : 13, x0 = 6, y0 = nar ? 64 : 40;
    const px5 = x0 + 4 * (2 * r + gap) - gap / 2;
    el("path", { d: nar ? rows.map((_, k) => `M${px(px5)} ${y0 + k * rowH - r - 6}v${2 * r + 12}`).join("") : `M${px(px5)} 6V${rowH * rows.length - 14}`, stroke: C.gold, "stroke-dasharray": "2 5" }, s);
    tx(s, px5 + 9, rowH * rows.length + (nar ? 2 : 6), "the pass mark: 5 of 6", it(16, C.gold));
    rows.forEach(([a, b, v], k) => { const yy = y0 + k * rowH;
      for (let i = 0; i < 6; i++) { const cx = x0 + r + i * (2 * r + gap), on = i < v[0], maybe = i >= v[0] && i < v[1];
        rv(on ? (ORBS ? moon(s, cx, yy, r * 0.94, 1, "copy") : mark.full(s, cx, yy, r * 0.82)) : el("circle", { cx, cy: yy, r: r - 1, fill: C.paper, stroke: maybe ? C.lit : C.line, "stroke-width": 1.4, "stroke-dasharray": maybe ? "3 3" : null }, s), k * 6 + i, 40); }
      const cnt = v[0] === v[1] ? `${v[0]} of 6 in all five runs` : `${said(v)} of 6 across five runs`;
      if (nar) { tx(s, x0, yy - 40, a, it(19.5)); tx(s, x0, yy - 23, b, small({ "font-size": 11.5 })); tx(s, x0 + 6 * (2 * r + gap) + 4, yy + 4, cnt.replace(" in all five runs", "").replace(" across five runs", ""), small({ "font-size": 12 })); }
      else { note(s, x0 + 6 * (2 * r + gap) + 18, yy - 2, a, [b], { size: 23 }); tx(s, x0, yy + r + 23, cnt, small({ fill: C.b3 })); }
    });
  }

  // ------------------------------------------------------------------ seals: a ring of ticks, one per animal, round a planet's sign
  function seal(host) {
    const n = +host.dataset.n || 0, g = host.dataset.g, legend = !host.closest(".card") && host.dataset.legend;
    const s = el("svg", { viewBox: "0 0 200 200", "aria-hidden": "true" }); host.appendChild(s);
    el("circle", { cx: 100, cy: 100, r: 98.5, fill: "none", stroke: C.line }, s);
    el("circle", { cx: 100, cy: 100, r: 95, fill: "none", stroke: C.hair }, s);
    el("circle", { cx: 100, cy: 100, r: 77, fill: "none", stroke: C.hair }, s);
    el("circle", { cx: 100, cy: 100, r: 50, fill: "none", stroke: C.line }, s);
    if (legend) {
      const id = "sl" + Math.random().toString(36).slice(2, 8);
      el("path", { id, d: "M100 17.5a82.5 82.5 0 1 1-.01 0", fill: "none" }, s);
      const t = el("text", { class: "legend" }, s), tp = el("textPath", { href: "#" + id, textLength: 510, lengthAdjust: "spacing" }, t);
      tp.textContent = `${legend} ✦ ${legend} ✦ `.toUpperCase();
    } else {
      let st = ""; for (let i = 0; i < 28; i++) { const a = (i / 28) * 2 * Math.PI, [x, y] = pol(100, 100, 86, a); st += `M${x.toFixed(2)} ${(y - 1.2).toFixed(2)}v2.4m-1.2 -1.2h2.4`; }
      el("path", { d: st, stroke: C.b3, "stroke-width": .7, fill: "none" }, s);
    }
    const t = el("g", { class: "ticks" }, s);
    let d = "", dl = "";
    for (let i = 0; i < n; i++) { const a = -Math.PI / 2 + (i / n) * 2 * Math.PI, long = i % 5 === 0;
      const [x1, y1] = pol(100, 100, 56, a), [x2, y2] = pol(100, 100, long ? 72 : 67, a);
      const seg = `M${x1.toFixed(2)} ${y1.toFixed(2)}L${x2.toFixed(2)} ${y2.toFixed(2)}`; if (long) dl += seg; else d += seg; }
    el("path", { d, stroke: C.b2, "stroke-width": 1, fill: "none" }, t);
    el("path", { d: dl, stroke: C.gilt, "stroke-width": 1.3, fill: "none" }, t);
    if (host.closest(".card")) { planetArt(s, g); const nm = host.closest(".card").querySelector(".num span"); if (nm && !nm.querySelector("svg")) nm.insertAdjacentHTML("afterbegin", `<svg viewBox="0 0 48 48" aria-hidden="true"><use href="#g-${g}"/></svg>`); }
    else { const u = el("use", { href: "#g-" + g, x: 72, y: 72, width: 56, height: 56 }, s); u.style.color = C.gilt; }
  }
  // the seven planets in small: each a lit body, with the one thing that makes it itself
  const ORBS = window.NEMATICA_ORBS || null, PIC = {};
  // a rendered body as a picture an SVG can hold: painted once per kind of light, then reused
  function orbPic(name, size, o, key) { const k = name + (key || ""); if (!PIC[k]) { const c = ORBS.sprite(name, size, o); PIC[k] = { href: c.toDataURL("image/png"), R: c.R }; } return PIC[k]; }
  function orbImage(p, name, cx, cy, r, o, key, size) { const pic = orbPic(name, size || 360, o, key), half = r / pic.R; return el("image", { href: pic.href, x: cx - half, y: cy - half, width: 2 * half, height: 2 * half }, p); }
  function planetArt(s, name) {
    if (ORBS) { const g = el("g", { class: "planet p-" + name }, s), r = { mercury: 31, venus: 37, mars: 35, jupiter: 41, saturn: 23.5, sun: 25, moon: 37 }[name];
      orbImage(g, name, 100, 100, r, { light: name === "moon" ? [0.86, 0.3, 0.12] : [-0.6, 0.5, 0.62], roll: name === "saturn" ? 0.36 : name === "mars" ? 0.4 : 0.08, lean: name === "saturn" ? 0.42 : 0.12, spin: name === "jupiter" ? 0.25 : 0.9, time: 4 }, "card", 420); return; }
    const g = el("g", { transform: "translate(100 100) scale(1.17) translate(-100 -100)" }, el("g", { class: "planet p-" + name }, s)), id = "pc" + Math.random().toString(36).slice(2, 7), cx = 100, cy = 100;
    const body = (r, ry) => el("ellipse", { cx, cy, rx: r, ry: ry || r, fill: `url(#pl-${name})` }, g);
    const clip = (r, ry) => { el("ellipse", { cx, cy, rx: r, ry: ry || r }, el("clipPath", { id }, el("defs", {}, g))); return el("g", { "clip-path": `url(#${id})` }, g); };
    if (name === "mercury") { [[0, 0.7], [9, 0.45], [-9, 0.45], [17, 0.22], [-17, 0.22]].forEach(([dy, o]) => el("path", { d: `M${cx + 8} ${cy + dy * 0.9}Q${cx - 22} ${cy + dy * 1.1 + 6} ${cx - 44 + Math.abs(dy) * 0.9} ${cy + dy * 1.3 + 16}`, stroke: "#c4deff", "stroke-opacity": o, "stroke-width": 1.4, "stroke-linecap": "round", fill: "none" }, g));
      el("circle", { cx: cx + 10, cy: cy - 2, r: 21, fill: "url(#pl-mercury)" }, g); }
    else if (name === "mars") { el("ellipse", { cx, cy, rx: 46, ry: 11, fill: "none", stroke: "#ff7a5c", "stroke-opacity": 0.35, transform: `rotate(-20 ${cx} ${cy})` }, g); body(29);
      el("ellipse", { cx: cx - 3, cy: cy - 30, rx: 13, ry: 6, fill: "#fff6ee", "fill-opacity": 0.85 }, clip(29)); el("circle", { cx: cx + 42, cy: cy - 16, r: 2.4, fill: "#fff6ee" }, g); el("circle", { cx: cx - 40, cy: cy + 15, r: 1.7, fill: "#fff6ee", "fill-opacity": 0.8 }, g); }
    else if (name === "venus") { el("circle", { cx, cy, r: 44, fill: "url(#gl-venus)" }, g); body(29); const c = clip(29);
      [[-12, 0.3], [0, 0.22], [12, 0.26]].forEach(([dy, o]) => el("path", { d: `M${cx - 34} ${cy + dy + 6}Q${cx} ${cy + dy - 10} ${cx + 34} ${cy + dy + 4}`, stroke: "#fff6ee", "stroke-opacity": o, "stroke-width": 3.5, fill: "none" }, c)); }
    else if (name === "saturn") { const t = el("g", { transform: `rotate(-20 ${cx} ${cy})` }, g), ring = (p) => { el("ellipse", { cx, cy, rx: 46, ry: 12, fill: "none", stroke: "#e8dcc0", "stroke-width": 3.2, "stroke-opacity": 0.75 }, p); el("ellipse", { cx, cy, rx: 37.5, ry: 9.4, fill: "none", stroke: "#e8dcc0", "stroke-width": 1.3, "stroke-opacity": 0.5 }, p); };
      ring(t); el("ellipse", { cx, cy, rx: 23, ry: 21.5, fill: "url(#pl-saturn)" }, t);
      el("rect", { x: cx - 50, y: cy, width: 100, height: 20 }, el("clipPath", { id }, el("defs", {}, t))); ring(el("g", { "clip-path": `url(#${id})` }, t)); }
    else if (name === "sun") { el("circle", { cx, cy, r: 49, fill: "url(#gl-real)" }, g); let d = ""; for (let k = 0; k < 24; k++) { const a = (k / 24) * 2 * PI, [x0, y0] = pol(cx, cy, 29, a), [x1, y1] = pol(cx, cy, k % 2 ? 36 : 43, a); d += `M${x0.toFixed(1)} ${y0.toFixed(1)}L${x1.toFixed(1)} ${y1.toFixed(1)}`; }
      el("path", { d, stroke: C.gold, "stroke-width": 1.3, "stroke-linecap": "round", "stroke-opacity": 0.85 }, g); body(23); }
    else if (name === "moon") { el("circle", { cx, cy, r: 30, fill: "rgba(226,234,250,.07)", stroke: "#e2eafa", "stroke-opacity": 0.35 }, g);
      el("path", { d: `M${cx} ${cy - 30}A30 30 0 0 1 ${cx} ${cy + 30}A15 30 0 0 0 ${cx} ${cy - 30}Z`, fill: "url(#pl-moon)", transform: `rotate(14 ${cx} ${cy})` }, g); }
    else if (name === "jupiter") { body(31, 29); const c = clip(31, 29);
      [[-17, 4, 0.5], [-7, 6.5, 0.62], [8, 5.5, 0.6], [19, 3.5, 0.45]].forEach(([dy, h, o]) => el("rect", { x: cx - 32, y: cy + dy - h / 2, width: 64, height: h, fill: "#b9784e", "fill-opacity": o }, c));
      el("ellipse", { cx: cx + 11, cy: cy + 8, rx: 6, ry: 3.4, fill: "#ff7a5c", "fill-opacity": 0.9 }, c); el("ellipse", { cx, cy, rx: 31, ry: 29, fill: "url(#pl-shade)" }, g);
      [[-46, 0], [-40, 1], [41, -1], [47, 0]].forEach(([dx, dy]) => el("circle", { cx: cx + dx, cy: cy + dy, r: 1.7, fill: "#fff6ee" }, g)); }
  }
  // the dials of the big seals turn a little as the page scrolls past them
  function dials() {
    const D = $$(".chapter .seal .ticks"); if (!D.length || REDUCED) return;
    let queued = false;
    const turn = () => { queued = false; D.forEach((t) => { const r = t.ownerSVGElement.getBoundingClientRect(); if (r.bottom < -50 || r.top > innerHeight + 50) return;
      t.style.transform = `rotate(${(((r.top + r.height / 2) / innerHeight - 0.5) * 70).toFixed(2)}deg)`; }); };
    addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(turn); } }, { passive: true }); turn();
  }

  // ------------------------------------------------------------------ the answer: seven rows on one sheet
  function ledger(host) {
    const G = (R.gaps || []).slice(), O = R.optoSign; if (!G.length) return;
    if (O) { const sst = O.mice.filter((d) => d.line === "Sst"), re = sst.map((d) => d.real), wu = sst.map((d) => d.w);
      G.splice(1, 0, { title: "Which way a cell pushes", where: `Mouse cortex, ${O.mice.length} animals, written down in advance`, scale: "Share of regions that rise when Sst cells are switched on", domain: [0, 1], ticks: [0, 0.5, 1], pct: true,
        band: [qt(re, 0.25), qt(re, 0.75)], bandLabel: "real mice", plain: { value: med(wu), label: "copy fitted at rest" },
        fixed: sst.some((d) => d.p != null) ? { value: med(sst.filter((d) => d.p != null).map((d) => d.p)), label: "copy given brief pulses" } : null,
        status: { text: "Watching points the wrong way", sub: O.second ? `A copy given the mouse's own answers to brief pulses gets the direction right in ${O.second.Sst.right} of ${O.second.Sst.n}` : "A copy taught by light pulses does better" } }); }
    const names = [["mercury", "The Echo"], ["mars", "The Push"], ["venus", "The Face"], ["saturn", "The Long Memory"], ["sun", "The Inner Light"], ["moon", "The Waning"], ["jupiter", "The Journey"]];
    host.innerHTML = "";
    G.forEach((g, i) => {
      const rowEl = document.createElement("a"); rowEl.className = "row"; rowEl.href = "#q" + (i + 1); rowEl.style.textDecoration = "none"; rowEl.style.color = "inherit";
      rowEl.innerHTML = `<svg class="g" aria-hidden="true"><use href="#g-${names[i][0]}"/></svg><div class="t"><b>${names[i][1]}</b><span>${g.where}</span></div><div class="strip"></div>
        <div class="st"><div><b>${g.status.text}</b>${g.status.sub}</div></div>`;
      host.appendChild(rowEl);
      if (ORBS) { const ic = rowEl.querySelector("svg.g"), nm = names[i][0]; ic.innerHTML = ""; ic.setAttribute("viewBox", "0 0 100 100"); ic.classList.add("orb");      // the row's sign is its planet
        orbImage(ic, nm, 50, 50, { mercury: 40, venus: 42, mars: 40, jupiter: 45, saturn: 22, sun: 21, moon: 42 }[nm], { light: nm === "moon" ? [0.86, 0.3, 0.12] : [-0.6, 0.5, 0.62], roll: nm === "saturn" ? 0.36 : nm === "mars" ? 0.4 : 0.08, lean: nm === "saturn" ? 0.42 : 0.12, spin: nm === "jupiter" ? 0.25 : 0.9, time: 4 }, "card", 420); }
      const sh = rowEl.querySelector(".strip"), w = Math.max(240, Math.floor(sh.clientWidth)), H = 110;
      const s = el("svg", { viewBox: `0 0 ${w} ${H}`, width: w, height: H, role: "img", "aria-label": `${g.scale}. ${g.status.text}.` }), L = LUM ? LUM.layer(sh, w, H) : null, S = { s, L }; sh.appendChild(s);
      const x = lin(g.domain[0], g.domain[1], 10, w - 10), ya = 52, fmt = (v) => (g.pct ? pc(v) : g.tickFmt === "int" ? String(v) : f2(v, g.dp));
      const bw = Math.max(4, x(g.band[1]) - x(g.band[0]));
      band(s, x(g.band[0]), ya - 15, bw, 30, true, L);
      if (g.band2) {      // a second kind of real animal on the same scale: both spreads are named under the line
        band(s, x(g.band2.range[0]), ya - 15, Math.max(4, x(g.band2.range[1]) - x(g.band2.range[0])), 30, true, L);
        const la = tx(s, (x(g.band[0]) + x(g.band[1])) / 2, ya + 49, g.bandShort || g.bandLabel, it(15, C.b2, { "text-anchor": "middle" }));
        const lb = tx(s, (x(g.band2.range[0]) + x(g.band2.range[1])) / 2, ya + 49, g.band2.label, it(15, C.b2, { "text-anchor": "middle" }));
        const ba = la.getBBox(), bb = lb.getBBox();
        if (ba.x + ba.width + 14 > bb.x) {      // on a short strip the two names would run together: each then hangs from its band's outer side
          la.setAttribute("text-anchor", "end"); la.setAttribute("x", x(g.band[1])); lb.setAttribute("text-anchor", "start"); lb.setAttribute("x", x(g.band2.range[0])); } }
      el("path", { d: `M10 ${px(ya)}H${w - 10}`, stroke: C.b3 }, s);
      g.ticks.forEach((v) => { el("path", { d: `M${px(x(v))} ${ya}v6`, stroke: C.b2 }, s); tx(s, x(v), ya + 31, fmt(v), num({ "font-size": 13.5, "text-anchor": "middle" })); });
      const lab = tx(s, 10, 12, g.scale, small({ "font-size": 11.5, fill: C.b3 }));
      if (lab.getComputedTextLength() > w - 14) { const wd = g.scale.split(" "); let keep = "", k = 0;      // on a narrow strip the scale's name takes two lines
        for (; k < wd.length; k++) { lab.textContent = (keep ? keep + " " : "") + wd[k]; if (lab.getComputedTextLength() > w - 14) break; keep = lab.textContent; }
        lab.textContent = keep; lab.setAttribute("y", 3); tx(s, 10, 17, wd.slice(k).join(" "), small({ "font-size": 11.5, fill: C.b3 })); }
      const place = (o, filled) => { if (!o) return;
        if (o.range) el("path", { d: `M${x(o.range[0])} ${px(ya)}H${x(o.range[1])}`, stroke: C.lit, "stroke-width": 3, "stroke-linecap": "round" }, s);
        const vals = o.values || (o.value != null ? [o.value] : o.range ? [(o.range[0] + o.range[1]) / 2] : []);
        vals.forEach((v, j) => (L ? dot(S, filled ? "full" : "ring", x(v), ya, filled ? 6 : 5, i * 6 + j + (filled ? 4 : 0), 60) : filled ? mark.full(s, x(v), ya, 6) : mark.ring(s, x(v), ya, 5)));
        if (!vals.length) return;
        const cxm = vals.length > 1 ? (x(vals[0]) + x(vals[vals.length - 1])) / 2 : x(vals[0]);
        const anchor = vals.length > 1 ? "middle" : cxm > w * 0.6 ? "end" : cxm < w * 0.25 ? "start" : "middle", dx = anchor === "end" ? 8 : anchor === "start" ? -8 : 0;
        tx(s, cxm + dx, filled ? ya + 49 : ya - 24, o.label, it(15, C.b2, { "text-anchor": anchor })); };
      place(g.plain, false); place(g.fixed, true);
      hover(rowEl, () => `<b>${names[i][1]}</b>${(g.tip || [[g.plain.label, fmt(g.plain.value)], [g.bandLabel, `${fmt(g.band[0])} to ${fmt(g.band[1])}`]]).map((t) => row(t[0], t[1])).join("")}`);
    });
  }

  // ------------------------------------------------------------------ the great seal: the seven questions on the star of seven
  function greatSeal(host) {
    const cards = $$(".arcana .card"); if (!cards.length) return;
    const WEEK = ["saturn", "jupiter", "mars", "sun", "venus", "mercury", "moon"];      // round the circle as in the sky above; the star's lines then run in the order of the days
    const s = el("svg", { viewBox: "0 0 520 520", "aria-hidden": "true" }); host.appendChild(s);
    const cx = 260, cy = 260, RO = 250, RV = 172;
    el("circle", { cx, cy, r: 236, fill: "url(#gl-real)", opacity: 0.3 }, s);
    el("circle", { cx, cy, r: RO, fill: "none", stroke: C.b3 }, s); el("circle", { cx, cy, r: RO - 5, fill: "none", stroke: C.hair }, s);
    el("circle", { cx, cy, r: RO - 36, fill: "none", stroke: C.b3 }, s); el("circle", { cx, cy, r: RO - 41, fill: "none", stroke: C.hair }, s);
    let t = ""; for (let i = 0; i < 252; i++) { const a = (i / 252) * 2 * PI, [x1, y1] = pol(cx, cy, RO - 41, a), [x2, y2] = pol(cx, cy, RO - 41 - (i % 36 === 0 ? 13 : i % 6 === 0 ? 8 : 4), a); t += `M${x1.toFixed(1)} ${y1.toFixed(1)}L${x2.toFixed(1)} ${y2.toFixed(1)}`; }
    el("path", { d: t, stroke: C.b3, "stroke-width": .8, fill: "none" }, s);
    el("path", { id: "gs-arc", d: `M${cx} ${cy - (RO - 25)}a${RO - 25} ${RO - 25} 0 1 1-.01 0`, fill: "none" }, s);
    const lt = el("text", { class: "legend", style: "font-size:11px" }, s), tp = el("textPath", { href: "#gs-arc", textLength: Math.round(2 * PI * (RO - 25)) - 12, lengthAdjust: "spacing" }, lt);
    tp.textContent = "WHAT THEY WERE SHOWN ✦ WHAT THEY WERE BUILT TO CARRY ✦ NOT THAT THEY ARE ARTIFICIAL ✦ ";
    const V = WEEK.map((_, i) => pol(cx, cy, RV, -PI / 2 + (i / 7) * 2 * PI));
    let star = "", inner = ""; for (let i = 0, k = 0; i < 7; i++, k = (k + 3) % 7) star += (i ? "L" : "M") + V[k][0].toFixed(1) + " " + V[k][1].toFixed(1);
    for (let i = 0; i < 7; i++) { const [x, y] = pol(cx, cy, RV * 0.357, -PI / 2 + ((i + 0.5) / 7) * 2 * PI); inner += (i ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1); }
    el("path", { d: star + "Z", fill: "none", stroke: C.gold, "stroke-width": 9, "stroke-opacity": 0.07, "stroke-linejoin": "round" }, s);
    el("path", { d: star + "Z", fill: "none", stroke: C.gold, "stroke-width": 1.1, "stroke-opacity": 0.75, "stroke-linejoin": "round" }, s);
    el("path", { d: inner + "Z", fill: "rgba(240,207,120,.06)", stroke: C.gilt, "stroke-opacity": 0.45 }, s);
    el("circle", { cx, cy, r: RV, fill: "none", stroke: C.line, "stroke-dasharray": "2 5" }, s);
    el("circle", { cx, cy, r: 40, fill: C.deep, stroke: C.gilt, "stroke-opacity": 0.8 }, s);
    el("path", { d: "M6 44c10 0 11-23 23-23 11 0 11 22 20 22 5 0 7-7 9-13-1 11-5 18-11 18-12 0-10-22-19-22-8 0-11 23-22 23z", fill: C.bone, transform: `translate(${cx - 26} ${cy - 28}) scale(.82)` }, s);
    el("circle", { cx: cx - 26 + 29 * 0.82, cy: cy - 28 + 23.5 * 0.82, r: 3.5, fill: "url(#mk-real)" }, s);
    WEEK.forEach((name, i) => { const [x, y] = V[i];
      el("circle", { cx: x, cy: y, r: 50, fill: "url(#gl-real)", opacity: 0.7 }, s);
      el("circle", { cx: x, cy: y, r: 31, fill: C.deep, stroke: C.gold, "stroke-width": 1.5 }, s);
      if (ORBS) orbImage(s, name, x, y, { mercury: 21, venus: 23, mars: 22, jupiter: 24.5, saturn: 14.5, sun: 15.5, moon: 22 }[name], { light: name === "moon" ? [0.86, 0.3, 0.12] : [-0.6, 0.5, 0.62], roll: name === "saturn" ? 0.36 : name === "mars" ? 0.4 : 0.08, lean: name === "saturn" ? 0.42 : 0.12, spin: name === "jupiter" ? 0.25 : 0.9, time: 4 }, "card", 420);
      else { const u = el("use", { href: "#g-" + name, x: x - 18, y: y - 18, width: 36, height: 36 }, s); u.style.color = C.gold; } });
  }

  // ------------------------------------------------------------------ wiring it up
  const FIGS = { echo, push, face, memory, light, waning, journey, ledger };
  function drawAll() { $$("[data-fig]").forEach((h) => { try { FIGS[h.dataset.fig] && FIGS[h.dataset.fig](h); } catch (e) { console.error(h.dataset.fig, e); } }); }
  function init() {
    $$(".seal").forEach(seal); dials(); $$("[data-great-seal]").forEach(greatSeal); drawAll();
    const io = "IntersectionObserver" in window && !REDUCED ? new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { threshold: 0.2 }) : null;
    $$("[data-fig]").forEach((h) => (io ? io.observe(h) : h.classList.add("in")));
    let lastW = innerWidth; addEventListener("resize", () => { if (Math.abs(innerWidth - lastW) > 30) { lastW = innerWidth; drawAll(); $$("[data-fig]").forEach((h) => h.classList.add("in")); } });
    const rail = $("#rail"), railA = $$("#rail a"), plates = railA.map((a) => $(a.getAttribute("href"))), ans = $("#answer");
    const onRail = () => { if (!rail || !plates[0]) return; const y = scrollY + innerHeight * 0.45;
      const top0 = plates[0].getBoundingClientRect().top + scrollY, end = ans.getBoundingClientRect().bottom + scrollY;
      rail.classList.toggle("on", y > top0 && scrollY + innerHeight * 0.3 < end);
      const tops = plates.map((p) => p.getBoundingClientRect().top + scrollY); let cur = -1; tops.forEach((t, i) => { if (t <= y) cur = i; });
      const inside = y < ans.getBoundingClientRect().top + scrollY;      // plates set side by side light up together
      railA.forEach((a, i) => a.setAttribute("aria-current", String(inside && cur >= 0 && Math.abs(tops[i] - tops[cur]) < 2))); };
    addEventListener("scroll", onRail, { passive: true }); onRail();
    // words rise, numbers count, cards tilt, a line across the top keeps the place
    $$(".kin").forEach((h) => { let i = 0; Array.from(h.childNodes).forEach((n) => {
        if (n.nodeType === 3) { const f = document.createDocumentFragment(); n.textContent.split(/(\s+)/).forEach((w) => { if (!w.trim()) { f.appendChild(document.createTextNode(w)); return; } const sp = document.createElement("span"); sp.className = "w"; sp.style.setProperty("--i", i++); sp.textContent = w; f.appendChild(sp); }); h.replaceChild(f, n); }
        else if (n.nodeType === 1) { n.classList.add("w"); n.style.setProperty("--i", i++); } }); });
    const kio = !REDUCED && "IntersectionObserver" in window ? new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); kio.unobserve(e.target); } }), { threshold: 0.35 }) : null;
    $$(".kin").forEach((h) => (kio ? kio.observe(h) : h.classList.add("in")));
    const count = (b) => Array.from(b.childNodes).forEach((n) => { if (n.nodeType !== 3 || !/^[\d.]+$/.test(n.textContent.trim())) return; const txt = n.textContent.trim(), v = +txt, dp = (txt.split(".")[1] || "").length, t0 = performance.now();
      const step = (now) => { const u = Math.min(1, (now - t0) / 1300), q = 1 - Math.pow(1 - u, 3); n.textContent = (v * q).toFixed(dp); if (u < 1) requestAnimationFrame(step); else n.textContent = txt; }; requestAnimationFrame(step); });
    const cio = !REDUCED && "IntersectionObserver" in window ? new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { count(e.target); cio.unobserve(e.target); } }), { threshold: 0.6 }) : null;
    if (cio) $$(".num b, .tally b").forEach((b) => cio.observe(b));
    if (!REDUCED && matchMedia("(hover: hover)").matches) $$(".card").forEach((c) => { c.addEventListener("pointermove", (e) => { const r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        c.style.setProperty("--ry", ((x - 0.5) * 16).toFixed(2) + "deg"); c.style.setProperty("--rx", ((0.5 - y) * 10).toFixed(2) + "deg"); c.style.setProperty("--mx", (x * 100).toFixed(1) + "%"); c.style.setProperty("--my", (y * 100).toFixed(1) + "%"); });
      c.addEventListener("pointerleave", () => { c.style.setProperty("--ry", "0deg"); c.style.setProperty("--rx", "0deg"); }); });
    // the deck and the orrery answer each other: a card under the pointer lights its sphere, and a sphere under the pointer lifts its card
    const SKY = window.NEMATICA_SKY, deck = $$(".arcana .card");
    if (SKY && deck.length) { const sign = (c) => c.querySelector(".seal").dataset.g, title = (c) => `${c.querySelector(".num").firstChild.textContent.trim()}. ${c.querySelector("h3").textContent}`;
      deck.forEach((c) => { const on = () => SKY.light(sign(c), title(c)), off = () => SKY.light(null); c.addEventListener("pointerenter", on); c.addEventListener("pointerleave", off); c.addEventListener("focus", on); c.addEventListener("blur", off); });
      SKY.onplanet = (g) => { let hit = null; deck.forEach((c) => { const y = sign(c) === g; c.classList.toggle("lit", y); if (y) hit = c; }); SKY.light(g, hit ? title(hit) : ""); };
      SKY.pick = (g) => { const c = deck.find((d) => sign(d) === g), to = c && $(c.getAttribute("href")); if (to) to.scrollIntoView({ behavior: (MO ? MO.on : !REDUCED) ? "smooth" : "auto" }); }; }
    const prog = $("#progress"), onProg = () => prog && prog.style.setProperty("--p", (scrollY / Math.max(1, document.documentElement.scrollHeight - innerHeight)).toFixed(4));
    addEventListener("scroll", onProg, { passive: true }); onProg();
    const top = $("#top"), menu = $(".menu");
    const onScroll = () => top.classList.toggle("stuck", scrollY > 24); onScroll(); addEventListener("scroll", onScroll, { passive: true });
    // the state is "menu-open", not "open": ".open" is every section's opening screen, and gave the header a screen's height
    const shut = () => { top.classList.remove("menu-open"); menu.setAttribute("aria-expanded", "false"); };
    menu.addEventListener("click", () => { const o = top.classList.toggle("menu-open"); menu.setAttribute("aria-expanded", o); });
    $$("#nav a").forEach((a) => a.addEventListener("click", shut));
    addEventListener("keydown", (e) => { if (e.key === "Escape" && top.classList.contains("menu-open")) { shut(); menu.focus(); } });
    addEventListener("resize", () => { if (innerWidth > 1060) shut(); });
  }
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(init);
})();
