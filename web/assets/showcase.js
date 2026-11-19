/* NEMATICA home page: the results, drawn large. Each figure reads window.NEMATICA_RESULTS (web/data/
   results.js, exported by scripts/export_site.py from committed result tables), draws at the page's own
   pixel size, takes its palette from the section it sits in (dark or light), and plays one short reveal
   when it first scrolls into view. */
(function () {
  "use strict";
  const R = window.NEMATICA_RESULTS || {};
  const NS = "http://www.w3.org/2000/svg";
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const PAL = {
    dark: { ink: "#eaf1ee", dim: "#8ea5a3", faint: "rgba(234,241,238,.10)", axis: "rgba(234,241,238,.22)", real: "#46e3a5",
      realWash: "rgba(70,227,165,.14)", copy: "#ff6fb5", ring: "#c9d6d3", bg: "#061015" },
    light: { ink: "#13212a", dim: "#5a6a71", faint: "#d8dfdb", axis: "#c9d3cf", real: "#0a7a5a",
      realWash: "#cfe8dc", copy: "#b8357f", ring: "#6f7f86", bg: "#edf1ef" },
  };
  function el(tag, a, p) { const n = document.createElementNS(NS, tag); for (const k in a || {}) if (a[k] != null) n.setAttribute(k, a[k]); if (p) p.appendChild(n); return n; }
  function tx(p, x, y, s, a) { const t = el("text", Object.assign({ x, y }, a || {}), p); t.textContent = s; return t; }
  const lin = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0)) * (r1 - r0);
  const px = (v) => Math.round(v) + 0.5;
  const f2 = (v, d = 2) => (+v).toFixed(d).replace("-", "−");
  function stage(host, h, label) {
    host.innerHTML = "";
    const w = Math.floor(host.clientWidth);
    const s = el("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}`, class: "show", role: "img", "aria-label": label }, null);
    host.appendChild(s);
    const P = PAL[host.closest(".dark") ? "dark" : "light"];
    const defs = el("defs", {}, s);
    const f = el("filter", { id: "glow-" + host.dataset.show, x: "-50%", y: "-50%", width: "200%", height: "200%" }, defs);
    el("feGaussianBlur", { stdDeviation: 3.2, result: "b" }, f);
    const m = el("feMerge", {}, f); el("feMergeNode", { in: "b" }, m); el("feMergeNode", { in: "SourceGraphic" }, m);
    return { s, w, P, glow: `url(#glow-${host.dataset.show})` };
  }
  // one tooltip
  let tipEl;
  function tip(html, e) {
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tip"; document.body.appendChild(tipEl); }
    if (!html) { tipEl.style.opacity = 0; return; }
    tipEl.innerHTML = html; const w = tipEl.offsetWidth, h = tipEl.offsetHeight;
    let x = e.clientX + 16, y = e.clientY + 16; if (x + w > innerWidth - 8) x = e.clientX - w - 16; if (y + h > innerHeight - 8) y = e.clientY - h - 16;
    tipEl.style.left = x + "px"; tipEl.style.top = y + "px"; tipEl.style.opacity = 1;
  }
  function hover(n, html) { n.addEventListener("pointermove", (e) => tip(html, e)); n.addEventListener("pointerleave", () => tip(null)); }
  const row = (a, b) => `<div class="row"><span>${a}</span><span>${b}</span></div>`;
  // staggered reveal: marks carry class "rv" and a --d delay
  const rv = (n, i, step) => { n.classList.add("rv"); n.style.setProperty("--d", Math.round(i * (step || 18)) + "ms"); return n; };

  // ------------------------------------------------------------ 1. watching vs poking (worm)
  function poke(host) {
    const pts = (R.restPoke || []).filter((d) => d.poke != null);
    const narrow = host.clientWidth < 640;
    const H = narrow ? 420 : Math.round(Math.min(560, Math.max(440, host.clientWidth * 0.42)));
    const { s, w, P, glow } = stage(host, H, "Each artificial brain: how many watching tests it passes, against how well its answers to a poke agree with real worms");
    const m = { l: narrow ? 40 : 70, r: narrow ? 12 : 220, t: 26, b: 64 };
    const x = lin(0.5, 6.5, m.l, w - m.r), y = lin(-0.01, 0.135, H - m.b, m.t);
    // real worms: the band where two real worms agree
    el("rect", { x: m.l, y: y(0.121), width: w - m.r - m.l, height: y(0.087) - y(0.121), fill: P.realWash }, s);
    el("line", { x1: m.l, x2: w - m.r, y1: px(y(0.104)), y2: px(y(0.104)), stroke: P.real, "stroke-width": 1.4, opacity: 0.8 }, s);
    [0, 0.04, 0.08, 0.12].forEach((v) => { el("line", { x1: m.l, x2: w - m.r, y1: px(y(v)), y2: px(y(v)), stroke: v ? P.faint : P.axis }, s);
      tx(s, m.l - 12, y(v) + 4, f2(v), { "text-anchor": "end", "font-size": 12, fill: P.dim }); });
    for (let k = 1; k <= 6; k++) tx(s, x(k), H - m.b + 24, String(k), { "text-anchor": "middle", "font-size": 13, fill: P.dim });
    tx(s, (m.l + w - m.r) / 2, H - 12, "How real it looks: watching tests passed, of 6", { "text-anchor": "middle", "font-size": 13, fill: P.ink, "font-weight": 600 });
    if (!narrow) tx(s, 0, 0, "How real its answers are", { "text-anchor": "middle", "font-size": 13, fill: P.ink, "font-weight": 600, transform: `translate(18 ${(m.t + H - m.b) / 2}) rotate(-90)` });
    const by = {}; pts.forEach((d) => (by[d.rest] = by[d.rest] || []).push(d));
    const r = narrow ? 4 : 5.4; let i = 0;
    Object.keys(by).sort().forEach((k) => {
      const placed = [];
      by[k].sort((a, b) => a.poke - b.poke).forEach((d) => {
        const cy = y(1 - d.poke); let off = 0, t = 0;
        while (placed.some((p) => Math.hypot(p.x - (x(+k) + off), p.y - cy) < 2 * r + 1) && t < 80) { t++; off = (t % 2 ? 1 : -1) * Math.ceil(t / 2) * r * 0.95; }
        placed.push({ x: x(+k) + off, y: cy });
        const learned = d.brain.startsWith("hybrid");
        const c = rv(el("circle", { cx: x(+k) + off, cy, r, fill: learned ? P.copy : "none", stroke: P.copy, "stroke-width": 1.6, filter: learned ? glow : null }, s), i++, 9);
        hover(c, `<b>${learned ? "Learned from pokes too" : "Learned by watching"}</b>${row("Watching tests passed", d.rest + " of 6")}${row("Echo agreement with real worms", f2(1 - d.poke))}`);
      });
    });
    if (!narrow) {
      const lx = w - m.r + 22;
      tx(s, lx, y(0.104) - 6, "Two real worms", { "font-size": 14, fill: P.real, "font-weight": 650 });
      tx(s, lx, y(0.104) + 12, "agree about this well", { "font-size": 13, fill: P.real });
      el("circle", { cx: lx + 5, cy: y(0.06), r: 5.4, fill: P.copy, stroke: P.copy, filter: glow }, s);
      tx(s, lx + 18, y(0.06) + 5, "Copies that also", { "font-size": 13, fill: P.ink, "font-weight": 600 });
      tx(s, lx + 18, y(0.06) + 22, "learned from pokes", { "font-size": 13, fill: P.ink, "font-weight": 600 });
      el("circle", { cx: lx + 5, cy: y(0.012), r: 5, fill: "none", stroke: P.copy, "stroke-width": 1.6 }, s);
      tx(s, lx + 18, y(0.012) + 5, "Copies that only", { "font-size": 13, fill: P.ink, "font-weight": 600 });
      tx(s, lx + 18, y(0.012) + 22, "watched", { "font-size": 13, fill: P.ink, "font-weight": 600 });
    }
  }

  // ------------------------------------------------------------ 2. forecasting against individuality (worm)
  function individual(host) {
    const D = R.shrinkage || []; if (!D.length) return;
    const narrow = host.clientWidth < 640;
    const H = narrow ? 460 : 500;
    const { s, w, P, glow } = stage(host, H, "As each worm's model is pulled toward the average, forecasting improves slightly while individuality collapses");
    const m = { l: narrow ? 44 : 70, r: narrow ? 14 : 200, t: 30, b: 70 };
    const lx = (v) => Math.log10(+v);
    const x = lin(lx(D[0].lam), lx(D[D.length - 1].lam), m.l, w - m.r);
    const gapY = 34, ph = (H - m.t - m.b - gapY) / 2;
    const yA = lin(0.69, 0.77, m.t + ph, m.t), yB = lin(0.4, 1.12, H - m.b, H - m.b - ph);
    const iBest = D.reduce((b, d, i) => (d.r2 > D[b].r2 ? i : b), 0), iTrue = D.findIndex((d) => +d.lam === 300);
    // guides
    [[iTrue, P.real, narrow ? "faithful" : "faithful copy"], [iBest, P.copy, narrow ? "best forecaster" : "best forecaster"]].forEach(([k, c, t]) => {
      const xx = x(lx(D[k].lam));
      el("line", { x1: px(xx), x2: px(xx), y1: m.t - 8, y2: H - m.b + 6, stroke: c, "stroke-dasharray": "3 4", opacity: 0.8 }, s);
      tx(s, xx, m.t - 14, t, { "text-anchor": "middle", "font-size": 12.5, fill: c, "font-weight": 650 });
    });
    // panel A: forecasting
    [0.7, 0.73, 0.76].forEach((v) => { el("line", { x1: m.l, x2: w - m.r, y1: px(yA(v)), y2: px(yA(v)), stroke: P.faint }, s); tx(s, m.l - 10, yA(v) + 4, f2(v), { "text-anchor": "end", "font-size": 11.5, fill: P.dim }); });
    tx(s, m.l, m.t + 8, "", {});
    // panel B: individuality, with the real-worm line
    el("rect", { x: m.l, y: yB(1.05), width: w - m.r - m.l, height: yB(0.95) - yB(1.05), fill: P.realWash }, s);
    el("line", { x1: m.l, x2: w - m.r, y1: px(yB(1)), y2: px(yB(1)), stroke: P.real, "stroke-width": 1.4 }, s);
    [0.5, 0.75, 1].forEach((v) => tx(s, m.l - 10, yB(v) + 4, f2(v), { "text-anchor": "end", "font-size": 11.5, fill: P.dim }));
    const line = (yy, k, c, lab) => {
      const p = D.map((d) => [x(lx(d.lam)), yy(d[k])]);
      const path = el("path", { d: p.map((q, j) => (j ? "L" : "M") + q[0].toFixed(1) + "," + q[1].toFixed(1)).join(""), fill: "none", stroke: c, "stroke-width": 2.6, "stroke-linejoin": "round", class: "draw" }, s);
      p.forEach((q, j) => { const c2 = rv(el("circle", { cx: q[0], cy: q[1], r: 4.6, fill: c, filter: glow }, s), j, 70);
        hover(c2, `<b>Pull toward the average: ${Number(D[j].lam).toLocaleString()}</b>${row("Forecasting skill (R²)", f2(D[j].r2, 3))}${row("Individuality (1 = real worms)", f2(D[j].ind, 2))}${row("Tests too typical", D[j].typical)}`); });
      if (!narrow) { const last = p[p.length - 1]; tx(s, last[0] + 14, last[1] + 5, lab, { "font-size": 13.5, fill: c, "font-weight": 650 }); }
      return path;
    };
    line(yA, "r2", P.ink, "forecasting skill");
    line(yB, "ind", P.real, "individuality");
    if (!narrow) tx(s, w - m.r + 14, yB(1) - 10, "real worms", { "font-size": 12, fill: P.real });
    if (narrow) { tx(s, m.l, yA(0.77) + 14, "forecasting skill", { "font-size": 12.5, fill: P.ink, "font-weight": 650 }); tx(s, m.l, yB(1.12) - 2, "individuality", { "font-size": 12.5, fill: P.real, "font-weight": 650 }); }
    tx(s, m.l, H - m.b + 26, "each worm its own model", { "font-size": 12.5, fill: P.dim });
    tx(s, w - m.r, H - m.b + 26, "one average model", { "text-anchor": "end", "font-size": 12.5, fill: P.dim });
    tx(s, (m.l + w - m.r) / 2, H - 16, narrow ? "Pull toward the average" : "How strongly each worm's model is pulled toward the average", { "text-anchor": "middle", "font-size": 13, fill: P.ink, "font-weight": 600 });
  }

  // ------------------------------------------------------------ 3. mouse by mouse (mouse visual cortex)
  function mouse(host) {
    const PM = R.permouse; if (!PM) return;
    const D = PM.mice, n = D.length, narrow = host.clientWidth < 640;
    const H = narrow ? 400 : 520;
    const { s, w, P, glow } = stage(host, H, `Slow memory in ${n} mice, in a random network recorded through each mouse's own instrument, and in the same network with slow drives`);
    const m = { l: narrow ? 36 : 56, r: narrow ? 12 : 230, t: 24, b: 56 };
    const x = (i) => m.l + 10 + (i * (w - m.l - m.r - 20)) / (n - 1), y = lin(0, 0.34, H - m.b, m.t);
    [0, 0.1, 0.2, 0.3].forEach((v) => { el("line", { x1: m.l, x2: w - m.r, y1: px(y(v)), y2: px(y(v)), stroke: v ? P.faint : P.axis }, s); tx(s, m.l - 10, y(v) + 4, f2(v, 1), { "text-anchor": "end", "font-size": 12, fill: P.dim }); });
    const r = narrow ? 3.6 : 5.4;
    D.forEach((d, i) => {
      const xi = x(i);
      rv(el("line", { x1: px(xi), x2: px(xi), y1: y(d.m), y2: y(d.rnn), stroke: P.axis, "stroke-width": 1.2 }, s), i, 22);
      if (d.slow != null) rv(el("circle", { cx: xi, cy: y(d.slow), r: r - 0.6, fill: "none", stroke: P.ring, "stroke-width": 1.4, opacity: 0.85 }, s), i, 22);
      rv(el("circle", { cx: xi, cy: y(d.rnn), r: r - 0.4, fill: P.copy }, s), i, 22);
      rv(el("circle", { cx: xi, cy: y(d.m), r, fill: P.real, filter: glow }, s), i, 22);
      const hit = el("rect", { x: xi - (w - m.l - m.r) / (2 * n), y: m.t, width: (w - m.l - m.r) / n, height: H - m.t - m.b, fill: "transparent" }, s);
      hover(hit, `<b>Mouse ${i + 1} of ${n}</b>${row("Mouse", f2(d.m, 3))}${row("Network, recorded like this mouse", f2(d.rnn, 3))}${row("Same network with slow drives", d.slow == null ? "not measured" : f2(d.slow, 3))}`);
    });
    tx(s, m.l, H - 18, `${n} mice, ordered by their own slow memory`, { "font-size": 13, fill: P.ink, "font-weight": 600 });
    if (!narrow) {
      const xe = x(n - 1) + 22, last = D[n - 1];
      const labs = [[last.slow, P.ring, "Same network with", "strong slow drives"], [last.m, P.real, "Mouse"], [last.rnn, P.copy, "Random network, recorded", "the way that mouse was"]]
        .map((o) => ({ yy: y(o[0]) + 5, c: o[1], a: o[2], b: o[3] })).sort((a, b) => a.yy - b.yy);
      for (let j = 1; j < labs.length; j++) if (labs[j].yy - labs[j - 1].yy < 40) labs[j].yy = labs[j - 1].yy + 40;
      labs.forEach((o) => { tx(s, xe, o.yy, o.a, { "font-size": 14, fill: o.c, "font-weight": 650 }); if (o.b) tx(s, xe, o.yy + 18, o.b, { "font-size": 13, fill: o.c }); });
    }
  }

  // ------------------------------------------------------------ 4. seven kinds of network against the mice
  function families(host) {
    const S = R.slowStudy; if (!S) return;
    const narrow = host.clientWidth < 640;
    const H = narrow ? 420 : 400;
    const { s, w, P, glow } = stage(host, H, "Share of state that is internal, in 49 mice and in each network family");
    const m = { l: narrow ? 14 : 30, r: narrow ? 14 : 30 }, ya = Math.round(H * 0.5);
    const x = lin(0, 1, m.l, w - m.r);
    const q = S.mice.M1;
    el("rect", { x: x(q[0]), y: ya - 70, width: x(q[2]) - x(q[0]), height: 140, rx: 6, fill: P.realWash }, s);
    S.mice.M1all.forEach((v, i) => rv(el("line", { x1: px(x(v)), x2: px(x(v)), y1: ya - 12, y2: ya + 12, stroke: P.real, "stroke-width": 1.6, opacity: 0.9 }, s), i, 12));
    tx(s, x(q[1]), ya - 80, `${S.mice.n} mice`, { "text-anchor": "middle", "font-size": 14, fill: P.real, "font-weight": 650 });
    el("line", { x1: m.l, x2: w - m.r, y1: px(ya), y2: px(ya), stroke: P.axis }, s);
    [0, 0.25, 0.5, 0.75, 1].forEach((v) => tx(s, x(v), H - 34, v === 0 ? "0" : v === 1 ? "all of it" : String(v), { "text-anchor": v === 0 ? "start" : v === 1 ? "end" : "middle", "font-size": 12, fill: P.dim }));
    tx(s, (m.l + w - m.r) / 2, H - 10, narrow ? "Share of state that is internal" : "Share of the brain's state that is internal, not locked to what it sees", { "text-anchor": "middle", "font-size": 13, fill: P.ink, "font-weight": 600 });
    const nets = [];
    S.families.filter((f) => f.counted).forEach((f) => f.members.forEach((mb) => nets.push({ v: mb.M1[1], t: f.members.length > 1 ? `${f.name} ${mb.label}` : f.name, f, mb })));
    nets.sort((a, b) => a.v - b.v);
    // labels in lanes above and below the axis, kept apart
    const lanesUp = [], lanesDn = [];
    nets.forEach((o, i) => {
      const up = i % 2 === 0, lanes = up ? lanesUp : lanesDn;
      const t = tx(s, 0, 0, o.t, { "font-size": narrow ? 11.5 : 13, fill: P.ink, "font-weight": 600 });
      const tw = t.getComputedTextLength(), lx = Math.max(m.l, Math.min(x(o.v) - tw / 2, w - m.r - tw));
      let k = 0; while ((lanes[k] || []).some((b) => lx < b[1] + 12 && lx + tw > b[0] - 12)) k++;
      (lanes[k] = lanes[k] || []).push([lx, lx + tw]);
      const ly = up ? ya - 34 - k * 22 : ya + 44 + k * 22;
      t.setAttribute("x", lx); t.setAttribute("y", ly);
      el("line", { x1: px(x(o.v)), x2: px(x(o.v)), y1: up ? ly + 5 : ya + 8, y2: up ? ya - 8 : ly - 14, stroke: P.copy, "stroke-width": 1, opacity: 0.55 }, s);
      const c = rv(el("circle", { cx: x(o.v), cy: ya, r: narrow ? 5.5 : 7, fill: P.copy, stroke: P.bg, "stroke-width": 2, filter: glow }, s), i, 60);
      hover(c, `<b>${o.t}</b>${row("Internal share, median over mice", f2(o.v))}${row("Middle half", `${f2(o.mb.M1[0])} to ${f2(o.mb.M1[2])}`)}`);
      hover(t, `<b>${o.t}</b>${row("Internal share, median over mice", f2(o.v))}`);
    });
  }

  // ------------------------------------------------------------ 5. what watching predicts vs what driving does (mouse)
  function sign(host) {
    const O = R.optoSign; if (!O) return;
    const narrow = host.clientWidth < 640;
    const H = narrow ? 430 : 480;
    const order = ["Sst", "Vip"];
    const D = O.mice.filter((d) => order.includes(d.line)).sort((a, b) => order.indexOf(a.line) - order.indexOf(b.line) || a.real - b.real);
    const { s, w, P, glow } = stage(host, H, `For ${D.length} mice: the share of brain regions a copy fitted at rest predicted would rise when one kind of inhibitory cell was driven, and the share that did`);
    const m = { l: narrow ? 40 : 64, r: narrow ? 12 : 220, t: narrow ? 52 : 22, b: 74 };
    const gapG = narrow ? 18 : 40, n = D.length;
    if (narrow) {
      el("circle", { cx: 8, cy: 12, r: 4, fill: "none", stroke: P.copy, "stroke-width": 1.8 }, s); tx(s, 18, 16, "copy fitted at rest", { "font-size": 12, fill: P.copy });
      el("circle", { cx: 150, cy: 12, r: 4.2, fill: P.real }, s); tx(s, 160, 16, "what happened", { "font-size": 12, fill: P.real });
      el("rect", { x: 4, y: 26, width: 10, height: 10, fill: P.faint }, s); tx(s, 18, 35, "light alone, mice without the opsin", { "font-size": 12, fill: P.dim });
    }
    const step = (w - m.l - m.r - gapG) / n;
    const y = lin(0, 1, H - m.b, m.t);
    // light alone, in mice without the opsin
    el("rect", { x: m.l, y: y(O.wt[2]), width: w - m.l - m.r, height: y(O.wt[0]) - y(O.wt[2]), fill: P.faint, opacity: 0.9 }, s);
    [0, 0.25, 0.5, 0.75, 1].forEach((v) => {
      el("line", { x1: m.l, x2: w - m.r, y1: px(y(v)), y2: px(y(v)), stroke: v === 0.5 ? P.axis : P.faint, "stroke-dasharray": v === 0.5 ? "4 4" : null }, s);
      tx(s, m.l - 10, y(v) + 4, `${Math.round(v * 100)}%`, { "text-anchor": "end", "font-size": 12, fill: P.dim });
    });
    if (!narrow) tx(s, 14, (m.t + H - m.b) / 2, "Share of brain regions that rise", { "font-size": 12.5, fill: P.ink, "font-weight": 600, "text-anchor": "middle", transform: `rotate(-90 14 ${(m.t + H - m.b) / 2})` });
    let xi = m.l, g = null, gx0 = 0;
    const r = narrow ? 3.2 : 4.6;
    const groups = [];
    D.forEach((d, i) => {
      if (d.line !== g) { if (g) { groups.push([g, gx0, xi]); xi += gapG; } g = d.line; gx0 = xi; }
      const cx = xi + step / 2;
      rv(el("line", { x1: px(cx), x2: px(cx), y1: y(d.w), y2: y(d.real), stroke: P.axis, "stroke-width": 1.2 }, s), i, 14);
      rv(el("circle", { cx, cy: y(d.w), r: r - 0.4, fill: P.bg, stroke: P.copy, "stroke-width": 1.8 }, s), i, 14);
      rv(el("circle", { cx, cy: y(d.real), r, fill: P.real, filter: glow }, s), i, 14);
      const hit = el("rect", { x: xi, y: m.t, width: step, height: H - m.t - m.b, fill: "transparent" }, s);
      hover(hit, `<b>${d.line} mouse ${d.id.replace("sub-", "")}</b>${row("Copy fitted at rest predicted rising", Math.round(d.w * 100) + "%")}${row("Actually rose when the cells were driven", Math.round(d.real * 100) + "%")}${row("Light alone, mice without the opsin", Math.round(O.wt[1] * 100) + "% (median)")}`);
      xi += step;
    });
    groups.push([g, gx0, xi]);
    const cnt = (l) => D.filter((d) => d.line === l).length;
    const LN = narrow ? { Sst: `Sst, ${cnt("Sst")}`, Vip: `Vip, ${cnt("Vip")}` } : { Sst: `Sst cells, ${cnt("Sst")} mice`, Vip: `Vip cells, ${cnt("Vip")} mice` };
    const SUB = narrow ? { Sst: "inhibit neighbours", Vip: "inhibit inhibitors" } : { Sst: "inhibit their neighbours", Vip: "inhibit other inhibitors" };
    groups.forEach(([gname, a, b]) => {
      el("line", { x1: a + 2, x2: b - 2, y1: H - m.b + 14, y2: H - m.b + 14, stroke: P.axis }, s);
      tx(s, (a + b) / 2, H - m.b + 34, LN[gname], { "text-anchor": "middle", "font-size": narrow ? 12 : 14, fill: P.ink, "font-weight": 650 });
      tx(s, (a + b) / 2, H - m.b + 52, SUB[gname], { "text-anchor": "middle", "font-size": narrow ? 11 : 12, fill: P.dim });
    });
    if (!narrow) {
      const xe = w - m.r + 24;
      tx(s, xe, y(0.9), "What the copy fitted", { "font-size": 14, fill: P.copy, "font-weight": 650 });
      tx(s, xe, y(0.9) + 18, "at rest predicted", { "font-size": 13, fill: P.copy });
      tx(s, xe, y(O.wt[1]) + 4, "Light alone, in mice", { "font-size": 12.5, fill: P.dim });
      tx(s, xe, y(O.wt[1]) + 20, "without the opsin", { "font-size": 12.5, fill: P.dim });
      tx(s, xe, y(0.14), "What happened when", { "font-size": 14, fill: P.real, "font-weight": 650 });
      tx(s, xe, y(0.14) + 18, "the cells were driven", { "font-size": 13, fill: P.real });
    }
  }

  const FIGS = { poke, individual, mouse, families, sign };
  function drawAll(only) {
    document.querySelectorAll("[data-show]").forEach((h) => { if (!only || only === h) { try { FIGS[h.dataset.show] && FIGS[h.dataset.show](h); } catch (e) { console.error(e); } } });
  }
  function init() {
    drawAll();
    const io = "IntersectionObserver" in window && !REDUCED ? new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { threshold: 0.25 }) : null;
    document.querySelectorAll("[data-show]").forEach((h) => { if (io) io.observe(h); else h.classList.add("in"); });
    let lastW = innerWidth;
    addEventListener("resize", () => { if (Math.abs(innerWidth - lastW) > 40) { lastW = innerWidth; drawAll(); } });
  }
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(init);
})();
