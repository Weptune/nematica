/* NEMATICA figures. Plain SVG drawn at the page's own pixel size (never scaled), so lines stay
   one pixel and text stays at its set size. Data: window.NEMATICA_RESULTS (web/data/results.js,
   exported by scripts/export_site.py from docs/figures). Each figure redraws when its width changes. */
(function () {
  "use strict";
  const R = window.NEMATICA_RESULTS || {};
  const NS = "http://www.w3.org/2000/svg";
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const C = {
    ink: css("--ink"), ink2: css("--ink-2"), ink3: css("--ink-3"), rule: css("--rule"), soft: css("--rule-soft"),
    live: css("--live"), liveTint: css("--live-tint"), liveWash: css("--live-wash"),
    copy: css("--copy"), copyTint: css("--copy-tint"), plate: css("--plate"), page: css("--page"),
  };

  const NAMES = {
    var3_spontaneous: "Linear brain learned from rest",
    var3_all: "Linear brain, rest and pokes",
    var3_stim: "Linear brain learned from pokes",
    var3_stim_relu: "Rectified brain learned from pokes",
    var3_all_relu: "Rectified brain, rest and pokes",
    var3_all_lasso: "Sparse linear brain",
    var10_stim: "Linear brain, longer memory",
    var1_spontaneous: "Linear brain, one step of memory",
    var3_spontaneous_diagonal: "No coupling (each neuron alone)",
    creamer2024_fully_connected: "Published model, fully connected",
    creamer2024_connectome_constrained: "Published model, wiring-constrained",
    creamer2024_shuffled_constrained: "Published model, shuffled wiring",
    hybrid_kernels: "Causal links on rest dynamics",
    hybrid_kernels_shuffled: "Links on shuffled pairs (control)",
    hybrid_kernels_connectome: "Links on wired pairs only",
    hybrid_kernels_bgstim: "Dynamics learned from pokes",
    hybrid_kernels_obs: "+ measurement noise",
    hybrid_kernels_obsfit: "+ fitted measurement noise",
    hybrid_kernels_regimes_obsfit: "+ noise, calm and active states",
    "hybrid_kernels_regimes_obsfit_smooth0.8": "+ smoothed noise",
    hybrid_kernels_regimes_obsfit_lowrank6: "+ six shared brain-wide modes",
    hybrid_kernels_regimes_obsfit_indiv: "+ each worm its own dynamics",
    hybrid_kernels_quietobsfit: "+ per-neuron quiet stretches",
    hybrid_kernels_gru64: "+ learned nonlinear dynamics (GRU)",
    hybrid_kernels_gru64ss: "+ free-running GRU",
    real: "Real worms",
    shuffled_times: "Responses read at random times",
    permuted_targets: "Wrong neuron credited",
    scaled_x3: "Responses three times too big",
    time_reversed: "Responses played backwards",
    independent_shift: "Each neuron shifted in time",
    frame_shuffle: "Moments shuffled",
    phase_randomised: "Phases randomised",
    gaussian_noise: "Gaussian noise",
    hyst: "Per-worm linear brain, VAR(3)",
    hyst10: "Per-worm linear brain, VAR(10)",
  };
  const LONG = {
    hybrid_kernels: "Hybrid: causal links learned from pokes, on dynamics learned from rest",
    hybrid_kernels_regimes_obsfit: "Hybrid with measurement noise and calm and active states",
  };
  const name = (s) => NAMES[s] || s.replace(/_/g, " ");
  const longName = (s) => LONG[s] || name(s).replace(/^\+ /, "Hybrid + ");

  const LEVELS = {
    "L1.distribution": "Activity values", "L1.timescale": "Timescale", "L2.correlation": "Correlations",
    "L2.dimension": "Dimension", "L4.leadlag": "Lead and lag", "L4.dwell": "Bout lengths",
    "C1.pattern": "Echo pattern", "C2.magnitude": "Echo size", "C3.kinetics": "Echo time course",
    "P2.spread": "Echo spread", "P1.complexity": "Echo complexity",
    "M1.complexity": "Complexity", "M2.integration": "Integration", "M3.repertoire": "Repertoire",
  };

  // ------------------------------------------------------------- helpers
  function el(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs || {}) if (attrs[k] !== undefined && attrs[k] !== null) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function text(parent, x, y, s, attrs) {
    const t = el("text", Object.assign({ x, y }, attrs || {}), parent);
    t.textContent = s;
    return t;
  }
  // an SVG at exactly w x h CSS pixels
  function svg(host, w, h, label) {
    host.innerHTML = "";
    const s = el("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}`, class: "chart", role: "img", "aria-label": label || "" });
    host.appendChild(s);
    return s;
  }
  const pad = (host) => { const cs = getComputedStyle(host); return [parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight), parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom)]; };
  const widthOf = (host, min, max) => Math.floor(Math.max(min || 0, Math.min(max || 1e9, (host.clientWidth || 800) - pad(host)[0])));
  const heightOf = (host, fallback) => Math.floor(host.clientHeight ? host.clientHeight - pad(host)[1] : fallback);
  const px = (v) => Math.round(v) + 0.5;           // crisp one-pixel lines
  const lin = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0)) * (r1 - r0);
  const median = (a) => { const b = a.filter((v) => v != null && isFinite(v)).sort((x, y) => x - y);
    if (!b.length) return NaN; const m = b.length >> 1; return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2; };
  const fmt = (v, d = 2) => (v == null || !isFinite(v) ? "n/a" : (+v).toFixed(d).replace("-", "−"));
  function hline(g, x1, x2, y, attrs) { return el("line", Object.assign({ x1, x2, y1: px(y), y2: px(y) }, attrs), g); }
  function vline(g, x, y1, y2, attrs) { return el("line", Object.assign({ x1: px(x), x2: px(x), y1, y2 }, attrs), g); }
  function wrapWords(s, n) {
    const words = s.split(" "); const out = []; let cur = "";
    words.forEach((w) => { if ((cur + " " + w).trim().length > n && cur) { out.push(cur); cur = w; } else cur = (cur + " " + w).trim(); });
    if (cur) out.push(cur); return out;
  }

  // one tooltip for the page
  let tipEl;
  function tip(html, evt) {
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tip"; tipEl.setAttribute("role", "status"); document.body.appendChild(tipEl); }
    if (!html) { tipEl.style.opacity = 0; return; }
    tipEl.innerHTML = html;
    const pad = 16, w = tipEl.offsetWidth, h = tipEl.offsetHeight;
    let x = evt.clientX + pad, y = evt.clientY + pad;
    if (x + w > innerWidth - 8) x = evt.clientX - w - pad;
    if (y + h > innerHeight - 8) y = evt.clientY - h - pad;
    tipEl.style.left = x + "px"; tipEl.style.top = y + "px"; tipEl.style.opacity = 1;
  }
  function hover(node, html, onEnter, onLeave) {
    node.addEventListener("pointermove", (e) => tip(typeof html === "function" ? html() : html, e));
    node.addEventListener("pointerenter", () => onEnter && onEnter());
    node.addEventListener("pointerleave", () => { tip(null); onLeave && onLeave(); });
    node.addEventListener("focus", () => { const r = node.getBoundingClientRect(); tip(typeof html === "function" ? html() : html, { clientX: r.right, clientY: r.top }); onEnter && onEnter(); });
    node.addEventListener("blur", () => { tip(null); onLeave && onLeave(); });
  }
  const row = (a, b) => `<div class="row"><span>${a}</span><span>${b}</span></div>`;

  // verdict glyph: filled = inside, open = outside, half = too typical, dot = not run
  function glyph(g, x, y, verdict, r = 4.75) {
    const sw = 1.5, ri = r - sw / 2;
    if (verdict === "inside") return el("circle", { cx: x, cy: y, r, fill: C.ink }, g);
    if (verdict === "too typical") {
      const grp = el("g", {}, g);
      el("circle", { cx: x, cy: y, r: ri, fill: C.plate, stroke: C.ink, "stroke-width": sw }, grp);
      el("path", { d: `M${x},${y - ri} A${ri},${ri} 0 0 0 ${x},${y + ri} Z`, fill: C.ink }, grp);
      return grp;
    }
    if (verdict === "outside") return el("circle", { cx: x, cy: y, r: ri, fill: C.plate, stroke: C.ink, "stroke-width": sw }, g);
    return el("circle", { cx: x, cy: y, r: 1.6, fill: C.ink3 }, g);
  }

  // ------------------------------------------------------------- Figure: scorecard
  const GROUPS = [
    { label: "Watching", sub: "ongoing activity", metrics: ["L1.distribution", "L1.timescale", "L2.correlation", "L2.dimension", "L4.leadlag", "L4.dwell"] },
    { label: "Poking", sub: "the echo", metrics: ["C1.pattern", "C2.magnitude", "C3.kinetics", "P2.spread"] },
    { label: "Complexity", sub: "", metrics: ["P1.complexity"] },
  ];
  const SCORE_SECTIONS = [
    { label: "Learned from activity", rows: ["var3_spontaneous", "var3_stim", "var3_all_relu", "var3_all_lasso", "var10_stim", "creamer2024_fully_connected"] },
    { label: "Hybrids: causal links learned from pokes", rows: ["hybrid_kernels", "hybrid_kernels_shuffled", "hybrid_kernels_connectome", "hybrid_kernels_obsfit",
      "hybrid_kernels_regimes_obsfit", "hybrid_kernels_regimes_obsfit_smooth0.8", "hybrid_kernels_regimes_obsfit_lowrank6",
      "hybrid_kernels_regimes_obsfit_indiv", "hybrid_kernels_quietobsfit", "hybrid_kernels_gru64", "hybrid_kernels_gru64ss"] },
  ];
  const SCORE_ROWS = SCORE_SECTIONS.flatMap((s) => s.rows);
  const PASSER = "hybrid_kernels_regimes_obsfit";
  function scorecard(host) {
    const data = {};
    (R.scorecard || []).forEach((r) => { (data[r.system + "|" + r.metric] = data[r.system + "|" + r.metric] || [])[r.fold] = r; });
    const W = widthOf(host, 980);
    const labW = Math.min(330, Math.max(270, Math.round(W * 0.27)));
    const gapG = 24, nCols = 11, colW = Math.floor((W - labW - 2 * gapG - 8) / nCols);
    const rowH = 32, secH = 36, top = 84;
    const H = top + SCORE_SECTIONS.length * secH + SCORE_ROWS.length * rowH + 6;
    const s = svg(host, W, H, "Scorecard: each artificial brain against real worms on eleven tests, in three held-out groups of worms");
    const cols = [];
    let x = labW;
    GROUPS.forEach((g) => { g.x0 = x; g.metrics.forEach((m) => { cols.push({ m, x: x + colW / 2 }); x += colW; }); g.x1 = x; x += gapG; });
    GROUPS.forEach((g) => {
      el("rect", { x: g.x0 + 2, y: 0, width: g.x1 - g.x0 - 4, height: 2, fill: C.ink }, s);
      const t = text(s, g.x0 + 2, 22, g.label, { class: "label-strong", "font-size": 13 });
      if (g.sub) { const ts = el("tspan", { fill: C.ink3, "font-weight": 400, dx: 6 }, t); ts.textContent = g.sub; }
    });
    cols.forEach((c) => {
      wrapWords(LEVELS[c.m], 10).forEach((l, i) => text(s, c.x, 50 + i * 15, l, { "text-anchor": "middle", "font-size": 12, fill: C.ink2 }));
    });
    hline(s, 0, W, top - 8, { stroke: C.rule });
    let y = top;
    const rowEls = [];
    SCORE_SECTIONS.forEach((sec) => {
      text(s, 12, y + 23, sec.label, { "font-size": 12, fill: C.ink3, "font-weight": 600 });
      y += secH;
      sec.rows.forEach((sys) => {
        const yc = y + rowH / 2, isPass = sys === PASSER;
        const bg = el("rect", { x: 0, y: y + 1, width: W, height: rowH - 2, rx: 6, fill: isPass ? C.liveWash : "transparent" }, s);
        if (isPass) el("rect", { x: 0, y: y + 6, width: 3, height: rowH - 12, rx: 1.5, fill: C.live }, s);
        const label = name(sys), sub = label.startsWith("+");
        const lt = text(s, sub ? 30 : 12, yc + 4.5, label, { "font-size": 13, fill: isPass ? C.ink : C.ink2, "font-weight": isPass ? 600 : 400 });
        rowEls.push({ bg, isPass, y: y + 1, lt, isPassRow: isPass, labelX: sub ? 30 : 12 });
        cols.forEach((c) => {
          const cell = data[sys + "|" + c.m] || [];
          const g = el("g", { tabindex: 0, class: "cell", "aria-label": `${longName(sys)}, ${LEVELS[c.m]}: ${[0, 1, 2].map((f) => (cell[f] ? cell[f].verdict : "not run")).join(", ")}` }, s);
          el("rect", { x: c.x - colW / 2 + 1, y: y + 1, width: colW - 2, height: rowH - 2, class: "hit" }, g);
          const allIn = [0, 1, 2].every((f) => cell[f] && cell[f].verdict === "inside");
          if (allIn) el("rect", { x: c.x - 23, y: yc - 11, width: 46, height: 22, rx: 11, fill: C.liveTint }, g);
          [0, 1, 2].forEach((f) => glyph(g, c.x + (f - 1) * 13, yc, cell[f] ? cell[f].verdict : null));
          hover(g, () => `<b>${longName(sys)}</b><br><span class="dim">${LEVELS[c.m]}: distance from real worms, against the real-worm median</span>` +
            [0, 1, 2].map((f) => cell[f] ? row(`Group ${f + 1}: <b>${cell[f].verdict}</b>`, `${fmt(cell[f].median)} vs ${fmt(cell[f].bio)}`) : row(`Group ${f + 1}`, "not run")).join(""));
        });
        y += rowH;
      });
    });
    // a tag for the brain that passes the poke test, placed after its measured label
    rowEls.filter((o) => o.isPassRow).forEach((o) => {
      const bx = o.labelX + o.lt.getComputedTextLength() + 12, yc = o.y + rowH / 2 - 1;
      el("rect", { x: bx, y: yc - 9, width: 124, height: 18, rx: 9, fill: C.live }, s);
      text(s, bx + 62, yc + 4, "passes the poke test", { "text-anchor": "middle", "font-size": 11, fill: "#fff", "font-weight": 600 });
    });
    s.addEventListener("pointermove", (e) => {
      const r = s.getBoundingClientRect(), yy = e.clientY - r.top;
      rowEls.forEach((o) => o.bg.setAttribute("fill", o.isPass ? C.liveWash : (yy >= o.y && yy < o.y + rowH - 2 ? "#f1f4f5" : "transparent")));
    });
    s.addEventListener("pointerleave", () => rowEls.forEach((o) => o.bg.setAttribute("fill", o.isPass ? C.liveWash : "transparent")));
  }

  // ------------------------------------------------------------- Figure: watching vs poking
  function restPoke(host, opts) {
    const small = !!(opts && opts.compact);
    const pts = (R.restPoke || []).filter((d) => d.poke != null);
    const W = widthOf(host, small ? 200 : 600);
    const H = small ? heightOf(host, W * 0.75) : Math.round(Math.min(520, Math.max(380, W * 0.52)));
    const m = small ? { l: 34, r: 8, t: 20, b: 30 } : { l: 64, r: 210, t: 20, b: 60 };
    const s = svg(host, W, H, "Rest tests passed against agreement of echoes with real worms, one dot per brain and held-out group");
    const x = lin(0.5, 6.5, m.l, W - m.r), y = lin(-0.02, 0.135, H - m.b, m.t);
    const fs = small ? 10.5 : 12;
    [0, 0.04, 0.08, 0.12].forEach((v) => { hline(s, m.l, W - m.r, y(v), { stroke: v === 0 ? C.rule : C.soft }); text(s, m.l - 10, y(v) + 4, fmt(v, 2), { "text-anchor": "end", "font-size": fs }); });
    for (let k = 1; k <= 6; k++) text(s, x(k), H - m.b + (small ? 16 : 22), String(k), { "text-anchor": "middle", "font-size": fs });
    const bio = 1 - median((R.scorecard || []).filter((r) => r.metric === "C1.pattern").map((r) => r.bio));
    el("rect", { x: m.l, y: y(bio + 0.015), width: W - m.r - m.l, height: y(bio - 0.015) - y(bio + 0.015), fill: C.liveTint, opacity: 0.8 }, s);
    hline(s, m.l, W - m.r, y(bio), { stroke: C.live, "stroke-width": 1.5 });
    if (small) {
      text(s, (m.l + W - m.r) / 2, H - 4, "watching tests passed", { "text-anchor": "middle", "font-size": 10.5, fill: C.ink3 });
      text(s, m.l - 30, 10, "echo agreement", { "font-size": 10.5, fill: C.ink3 });
    } else {
      text(s, W - m.r + 16, y(bio) - 3, "Two real worms agree", { fill: C.live, "font-weight": 600, "font-size": 12.5 });
      text(s, W - m.r + 16, y(bio) + 13, `at about ${fmt(bio, 1)}`, { fill: C.live, "font-size": 12.5 });
      text(s, W - m.r + 16, y(0) + 4, "No agreement", { "font-size": 12.5, fill: C.ink3 });
      text(s, (m.l + W - m.r) / 2, H - 14, "Watching tests passed, of 6", { "text-anchor": "middle", fill: C.ink2, "font-size": 12.5 });
      text(s, 0, 0, "Echo agreement with real worms", { "text-anchor": "middle", fill: C.ink2, "font-size": 12.5, transform: `translate(18 ${(m.t + H - m.b) / 2}) rotate(-90)` });
      const ly = y(0.055), lx = W - m.r + 22;
      el("circle", { cx: lx, cy: ly, r: 4.5, fill: C.plate, stroke: C.copy, "stroke-width": 1.5 }, s);
      text(s, lx + 12, ly + 4, "Learned from activity", { "font-size": 12.5 });
      el("circle", { cx: lx, cy: ly + 24, r: 4.5, fill: C.copy }, s);
      text(s, lx + 12, ly + 28, "With causal links", { "font-size": 12.5 });
      text(s, lx + 12, ly + 44, "learned from pokes", { "font-size": 12.5 });
    }
    const byCol = {};
    pts.forEach((d) => (byCol[d.rest] = byCol[d.rest] || []).push(d));
    const r = small ? 2.8 : 4.6;
    Object.keys(byCol).forEach((k) => {
      const col = byCol[k].sort((a, b) => a.poke - b.poke), placed = [];
      col.forEach((d) => {
        const cy = y(1 - d.poke);
        let off = 0, tries = 0;
        while (placed.some((p) => Math.hypot(p.x - (x(+k) + off), p.y - cy) < 2 * r + 0.8) && tries < 60) { tries++; off = (tries % 2 ? 1 : -1) * Math.ceil(tries / 2) * (r * 0.9); }
        placed.push({ x: x(+k) + off, y: cy });
        const hybrid = d.brain.startsWith("hybrid");
        const c = el("circle", { cx: x(+k) + off, cy, r, fill: hybrid ? C.copy : C.plate, stroke: C.copy, "stroke-width": 1.5, tabindex: small ? -1 : 0, class: small ? "" : "dot",
          "aria-label": `${longName(d.brain)}, group ${d.fold + 1}: ${d.rest} of 6 watching tests, echo agreement ${fmt(1 - d.poke)}` }, s);
        if (!small) hover(c, `<b>${longName(d.brain)}</b><br><span class="dim">Held-out group ${d.fold + 1}</span>${row("Watching tests passed", d.rest + " of 6")}${row("Echo agreement", fmt(1 - d.poke))}${row("Echo pattern", d.verdict)}`);
      });
    });
  }

  // ------------------------------------------------------------- Figure: power of the poke test
  function power(host) {
    const P = R.power; if (!P) return;
    const W = widthOf(host, 640), H = 470, m = { l: 84, r: 24, t: 24, b: 160 };
    const s = svg(host, W, H, "How much true cause and effect a brain needs before the poke test calls it inside");
    const x = lin(0, 1, m.l, W - m.r), y = lin(0, 0.3, H - m.b, m.t);
    [0, 0.1, 0.2, 0.3].forEach((v) => { hline(s, m.l, W - m.r, y(v), { stroke: v === 0 ? C.rule : C.soft }); text(s, m.l - 10, y(v) + 4, fmt(v, 1), { "text-anchor": "end" }); });
    [0, 0.2, 0.4, 0.6, 0.8, 1].forEach((v) => text(s, x(v), H - m.b + 20, fmt(v, 1), { "text-anchor": "middle" }));
    text(s, (m.l + W - m.r) / 2, H - m.b + 44, "How much of the true average echo the brain carries (its correlation with it)", { "text-anchor": "middle", fill: C.ink2, "font-size": 12.5 });
    text(s, 0, 0, "Agreement with real worms", { "text-anchor": "middle", fill: C.ink2, "font-size": 12.5, transform: `translate(18 ${(m.t + H - m.b) / 2}) rotate(-90)` });
    const bio = median(Object.values(P.pools).map((p) => 1 - p.bio));
    hline(s, m.l, W - m.r, y(bio), { stroke: C.live, "stroke-width": 1.5, "stroke-dasharray": "5 4" });
    text(s, W - m.r, y(bio) + 18, `Two real worms agree at ${fmt(bio, 2)}`, { fill: C.live, "font-weight": 600, "text-anchor": "end", "font-size": 12.5 });
    const pools = [0, 1, 2];
    pools.forEach((f) => {
      const pts = P.points.filter((p) => p.fold === f).sort((a, b) => a.f - b.f);
      el("path", { d: pts.map((p, i) => (i ? "L" : "M") + x(p.f).toFixed(1) + "," + y(1 - p.d).toFixed(1)).join(""), fill: "none", stroke: C.ink, "stroke-width": 1.6, opacity: [0.35, 0.6, 0.9][f] }, s);
    });
    const step = 0.05, cw = x(step) - x(0);
    pools.forEach((f) => {
      const yy = H - m.b + 68 + f * 22;
      text(s, x(0) - cw / 2 - 8, yy + 12, `Group ${f + 1}`, { "text-anchor": "end", "font-size": 12 });
      P.points.filter((p) => p.fold === f).forEach((p) => {
        const nIn = p.verdicts.filter((q) => q === "inside").length, nOut = p.verdicts.filter((q) => q === "outside").length;
        const v = nIn >= 2 ? "inside" : nOut >= 2 ? "outside" : "too typical";
        const r = el("rect", { x: x(p.f) - cw / 2 + 1, y: yy, width: cw - 2, height: 16, rx: 3,
          fill: v === "inside" ? C.live : v === "outside" ? C.plate : "#dfe4e7", stroke: v === "outside" ? C.rule : "none" }, s);
        hover(r, `<b>Group ${f + 1}, correlation ${fmt(p.f)}</b><br>${p.verdicts.join(", ")}<br><span class="dim">agreement with real worms ${fmt(1 - p.d)}</span>`);
      });
    });
    const ly = H - m.b + 68 + 3 * 22 + 8;
    [[C.live, "none", "Inside: as real as a real worm"], [C.plate, C.rule, "Outside: too little cause and effect"], ["#dfe4e7", "none", "Too typical: more stereotyped than any worm"]].forEach((k, i) => {
      const xx = m.l + i * Math.min(260, (W - m.l) / 3);
      el("rect", { x: xx, y: ly, width: 14, height: 12, rx: 2, fill: k[0], stroke: k[1] }, s);
      text(s, xx + 20, ly + 10.5, k[2], { "font-size": 12 });
    });
    const marks = (R.signalNoise || []).filter((d) => d.avg10 != null)
      .map((d) => ({ v: d.avg10, n: d.system.startsWith("real") ? "One real worm, against the average" : name(d.system), real: d.system.startsWith("real") }))
      .sort((a, b) => a.v - b.v);
    marks.forEach((d, i) => {
      const xx = x(d.v), yy = m.t + 6 + i * 18;
      vline(s, xx, yy + 5, H - m.b, { stroke: d.real ? C.live : C.copy, "stroke-width": 1, opacity: 0.4 });
      el("circle", { cx: xx, cy: H - m.b, r: 3.5, fill: d.real ? C.live : C.copy }, s);
      el("circle", { cx: xx, cy: yy, r: 3, fill: d.real ? C.live : C.copy }, s);
      text(s, xx + 8, yy + 4, `${d.n}  ${fmt(d.v)}`, { "font-size": 12, fill: d.real ? C.live : C.ink2 });
    });
  }

  // ------------------------------------------------------------- Figure: signal or noise
  function signalNoise(host) {
    const D = (R.signalNoise || []).filter((d) => !d.system.startsWith("real"));
    const realV = ((R.signalNoise || []).find((d) => d.system.startsWith("real")) || {}).avg10;
    const W = widthOf(host, 600), rowH = 46, m = { l: Math.round(Math.min(290, W * 0.34)), r: 40, t: 46, b: 50 }, H = m.t + D.length * rowH + m.b;
    const s = svg(host, W, H, "Each model's echo, single run and averaged over ten runs, against one real worm");
    const x = lin(0, 0.3, m.l, W - m.r);
    [0, 0.1, 0.2, 0.3].forEach((v) => { vline(s, x(v), m.t - 10, H - m.b, { stroke: v === 0 ? C.rule : C.soft }); text(s, x(v), H - m.b + 20, fmt(v, 1), { "text-anchor": "middle" }); });
    text(s, (m.l + W - m.r) / 2, H - 10, "Correlation of the echo with the atlas average", { "text-anchor": "middle", fill: C.ink2, "font-size": 12.5 });
    el("rect", { x: Math.round(x(realV)) - 1, y: m.t - 16, width: 2, height: H - m.b - m.t + 16, fill: C.live }, s);
    text(s, x(realV) - 8, m.t - 22, `One real worm ${fmt(realV)}`, { fill: C.live, "font-weight": 600, "text-anchor": "end", "font-size": 12.5 });
    D.forEach((d, i) => {
      const yy = Math.round(m.t + i * rowH + rowH / 2);
      if (i % 2 === 0) el("rect", { x: 0, y: yy - rowH / 2 + 2, width: W, height: rowH - 4, rx: 6, fill: "#f7f8f9" }, s);
      text(s, m.l - 16, yy + 4.5, name(d.system), { "text-anchor": "end", "font-size": 13, fill: C.ink });
      el("line", { x1: x(d.single), x2: x(d.avg10), y1: yy, y2: yy, stroke: C.copy, "stroke-width": 2 }, s);
      el("circle", { cx: x(d.single), cy: yy, r: 5.5, fill: C.plate, stroke: C.copy, "stroke-width": 1.75 }, s);
      el("circle", { cx: x(d.avg10), cy: yy, r: 5.5, fill: C.copy }, s);
      text(s, x(d.avg10) + 11, yy + 4.5, fmt(d.avg10), { "font-size": 12, fill: C.ink2 });
      const hit = el("rect", { x: 0, y: yy - rowH / 2, width: W, height: rowH, class: "hit" }, s);
      hover(hit, `<b>${name(d.system)}</b>${row("One simulated worm", fmt(d.single))}${row("Ten repeats averaged", fmt(d.avg10))}${row("One real worm", fmt(realV))}`);
    });
    el("circle", { cx: m.l + 6, cy: 14, r: 5.5, fill: C.plate, stroke: C.copy, "stroke-width": 1.75 }, s); text(s, m.l + 18, 18, "One simulated worm", { "font-size": 12.5 });
    el("circle", { cx: m.l + 166, cy: 14, r: 5.5, fill: C.copy }, s); text(s, m.l + 178, 18, "Ten repeats averaged", { "font-size": 12.5 });
  }

  // ------------------------------------------------------------- Figure: causal fingerprints
  function fingerprint(host, opts) {
    const small = !!(opts && opts.compact);
    const rows = (R.fingerprintRows || []).filter((r) => r.fp_within != null && r.fp_between != null)
      .sort((a, b) => (a.fp_within - a.fp_between) - (b.fp_within - b.fp_between));
    const n = rows.length; if (!n) return;
    const W = widthOf(host, small ? 200 : 600);
    const m = small ? { l: 8, r: 8, t: 26, b: 30 } : { l: 70, r: Math.round(Math.min(240, W * 0.28)), t: 20, b: 60 };
    const H = small ? heightOf(host, W * 0.75) : m.t + n * 10 + m.b;
    const rh = (H - m.t - m.b) / n;
    const s = svg(host, W, H, "For each worm, how alike the two halves of its own pokes are, against other worms");
    const x = lin(0.45, 1.12, m.l, W - m.r);
    [0.5, 0.7, 0.9, 1.1].forEach((v) => { vline(s, x(v), m.t - 6, H - m.b + 2, { stroke: C.soft }); text(s, x(v), H - m.b + (small ? 16 : 22), fmt(v, 1), { "text-anchor": "middle", "font-size": small ? 10.5 : 12 }); });
    let closer = 0;
    rows.forEach((r, i) => {
      const yy = m.t + i * rh + rh / 2;
      const own = r.fp_within < r.fp_between; if (own) closer++;
      el("line", { x1: x(r.fp_within), x2: x(r.fp_between), y1: yy, y2: yy, stroke: own ? C.live : C.copy, "stroke-width": small ? 1 : 1.5, opacity: 0.45 }, s);
      el("circle", { cx: x(r.fp_between), cy: yy, r: small ? 1.8 : 3.4, fill: C.plate, stroke: C.ink3, "stroke-width": 1.2 }, s);
      el("circle", { cx: x(r.fp_within), cy: yy, r: small ? 2.1 : 3.8, fill: own ? C.live : C.copy }, s);
      if (!small) {
        const hit = el("rect", { x: m.l, y: yy - rh / 2, width: W - m.l - m.r, height: rh, class: "hit" }, s);
        hover(hit, `<b>Worm recorded ${r.worm.slice(0, 4)}-${r.worm.slice(4, 6)}-${r.worm.slice(6, 8)}</b>${row("Its own two halves", fmt(r.fp_within, 3))}${row("Against other worms", fmt(r.fp_between, 3))}<span class="dim">Lower is more alike</span>`);
      }
    });
    if (small) {
      text(s, m.l, 14, `${closer} of ${n} worms closer to themselves`, { "font-size": 11, fill: C.ink, "font-weight": 600 });
      text(s, (m.l + W - m.r) / 2, H - 4, "echo distance", { "text-anchor": "middle", "font-size": 10.5, fill: C.ink3 });
    } else {
      text(s, (m.l + W - m.r) / 2, H - 16, "Echo distance (lower is more alike)", { "text-anchor": "middle", fill: C.ink2, "font-size": 12.5 });
      text(s, 0, 0, `${n} worms, sorted by the gap`, { "text-anchor": "middle", fill: C.ink2, "font-size": 12.5, transform: `translate(${m.l - 30} ${m.t + (n * rh) / 2}) rotate(-90)` });
      const lx = W - m.r + 30;
      el("circle", { cx: lx, cy: m.t + 8, r: 4, fill: C.live }, s); text(s, lx + 12, m.t + 12, "The worm against itself", { fill: C.ink, "font-size": 12.5 });
      text(s, lx + 12, m.t + 29, "two halves of its pokes", { "font-size": 12 });
      el("circle", { cx: lx, cy: m.t + 56, r: 3.6, fill: C.plate, stroke: C.ink3, "stroke-width": 1.2 }, s); text(s, lx + 12, m.t + 60, "Against other worms", { fill: C.ink, "font-size": 12.5 });
      text(s, lx + 12, m.t + 77, "median distance", { "font-size": 12 });
      text(s, lx - 4, m.t + 128, `${closer} of ${n}`, { class: "label-strong", "font-size": 30, "letter-spacing": "-0.02em" });
      text(s, lx - 4, m.t + 150, "worms are closer to", { fill: C.ink2, "font-size": 12.5 });
      text(s, lx - 4, m.t + 167, "themselves than to others", { fill: C.ink2, "font-size": 12.5 });
    }
  }

  // ------------------------------------------------------------- Figure: who stays out of the echo
  function echoShape(host, opts) {
    const small = !!(opts && opts.compact);
    const D = [
      { k: "Neuron classes that respond at all within 30 s", real: 66, var: 93, hyb: 95 },
      { k: "Moments where the set of responders changes", real: 85, var: 97, hyb: 98 },
    ];
    const W = widthOf(host, small ? 200 : 600);
    const bh = small ? 12 : 20, gap = small ? 4 : 6;
    const m = small ? { l: 4, r: 34, t: 6, b: 0 } : { l: Math.round(Math.min(340, W * 0.38)), r: 54, t: 4, b: 10 };
    const blockH = 3 * (bh + gap) + (small ? 26 : 18);
    const H = small ? heightOf(host, W * 0.75) : m.t + D.length * blockH + m.b;
    const s = svg(host, W, H, "Share of neuron classes that respond after a poke, real worms against models");
    const x = lin(0, 100, m.l, W - m.r);
    const start = small ? Math.round((H - 2 * blockH) / 2) : m.t;
    D.forEach((d, i) => {
      const y0 = start + i * blockH;
      if (small) text(s, m.l, y0 + 11, d.k, { fill: C.ink, "font-size": 11 });
      else wrapWords(d.k, 30).forEach((l, j) => text(s, m.l - 18, y0 + 18 + j * 16, l, { "text-anchor": "end", fill: C.ink, "font-size": 13 }));
      const off = small ? 18 : 4;
      [["Real worms", d.real, C.live, 1], ["Linear brain", d.var, C.copy, 1], ["Hybrid that passes the poke test", d.hyb, C.copy, 0.5]].forEach((b, j) => {
        const yy = y0 + off + j * (bh + gap);
        el("rect", { x: x(0), y: yy, width: x(b[1]) - x(0), height: bh, rx: 3, fill: b[2], "fill-opacity": b[3] }, s);
        text(s, x(b[1]) + 7, yy + bh / 2 + 4, `${b[1]}%`, { "font-size": small ? 10.5 : 12.5, fill: C.ink, "font-weight": 600 });
        if (!small) text(s, x(0) + 9, yy + bh / 2 + 4, b[0], { "font-size": 12, fill: j === 2 ? C.ink : "#fff", "font-weight": 600 });
      });
    });
  }

  // ------------------------------------------------------------- Figure: verdict grids (calibrations, mind)
  function verdictGrid(host, rowsIn, metrics, opts) {
    opts = opts || {};
    const datasets = opts.datasets || [null];
    const labW = 270, colW = 92, rowH = 32, gap = 28, top = datasets.length > 1 ? 74 : 50;
    const W = labW + datasets.length * metrics.length * colW + (datasets.length - 1) * gap + 4;
    const sys = opts.order || [...new Set(rowsIn.map((r) => r.system))];
    const H = top + sys.length * rowH + 6;
    const s = svg(host, W, H, opts.label || "Verdict grid");
    sys.forEach((sy, i) => { if (i % 2 === 0) el("rect", { x: 0, y: top + i * rowH + 1, width: W, height: rowH - 2, rx: 6, fill: "#f7f8f9" }, s); });
    datasets.forEach((ds, di) => {
      const x0 = labW + di * (metrics.length * colW + gap);
      if (ds) { el("rect", { x: x0 + 2, y: 0, width: metrics.length * colW - 4, height: 2, fill: C.ink }, s); text(s, x0 + 2, 22, opts.dsLabel ? opts.dsLabel(ds) : ds, { class: "label-strong", "font-size": 13 }); }
      metrics.forEach((mt, mi) => wrapWords(LEVELS[mt] || mt, 11).forEach((l, j, arr) => text(s, x0 + mi * colW + colW / 2, top - 12 - (arr.length - 1 - j) * 15, l, { "text-anchor": "middle", "font-size": 12, fill: C.ink2 })));
      sys.forEach((sy, i) => {
        const y = top + i * rowH + rowH / 2;
        metrics.forEach((mt, mi) => {
          const cx = x0 + mi * colW + colW / 2;
          const cells = rowsIn.filter((r) => r.system === sy && r.metric === mt && (!ds || r.dataset === ds)).sort((a, b) => a.fold - b.fold);
          const g = el("g", { tabindex: 0 }, s);
          el("rect", { x: cx - colW / 2 + 2, y: y - rowH / 2 + 2, width: colW - 4, height: rowH - 4, class: "hit" }, g);
          const exp0 = cells[0] && cells[0].expected;
          const exp = ["inside", "outside", "too typical"].includes(exp0) ? exp0 : null;
          const met = exp && cells.every((c) => c.verdict === exp);
          if (exp) el("rect", { x: cx - 27, y: y - 11.5, width: 54, height: 23, rx: 11.5, fill: "none", stroke: met ? C.live : C.copy, "stroke-width": 1.5, "stroke-dasharray": met ? "" : "3 2.5" }, g);
          cells.forEach((c, k) => glyph(g, cx + (k - 1) * 13, y, c.verdict));
          hover(g, () => `<b>${name(sy)}</b><br><span class="dim">${LEVELS[mt] || mt}${ds ? ", " + (opts.dsLabel ? opts.dsLabel(ds) : ds) : ""}</span>` + cells.map((c) => row(`Group ${c.fold + 1}`, c.verdict)).join("") + (exp ? `<span class="dim">Written down in advance: ${exp}${met ? ", met" : ", missed in at least one group"}</span>` : ""));
        });
        if (di === 0) text(s, 12, y + 4.5, name(sy), { "font-size": 13, fill: C.ink });
      });
    });
  }
  function calibration(host) {
    verdictGrid(host, R.calibration || [], ["C1.pattern", "C2.magnitude", "C3.kinetics"],
      { order: ["real", "shuffled_times", "permuted_targets", "scaled_x3", "time_reversed"], label: "Calibrations of the poke tests" });
  }
  function mind(host) {
    verdictGrid(host, R.mind || [], ["M1.complexity", "M2.integration", "M3.repertoire"],
      { datasets: ["copper", "atanas"], dsLabel: (d) => (d === "copper" ? "Copper dataset" : "Atanas et al. 2023"),
        order: ["real", "hyst", "hyst10", "phase_randomised", "independent_shift", "frame_shuffle", "gaussian_noise"],
        label: "Consciousness-science measures of ongoing activity" });
  }

  // ------------------------------------------------------------- Figure: one test, one group, every brain
  function rulerStrip(host) {
    const metric = host.dataset.metric || "C1.pattern", fold = +(host.dataset.fold || 0);
    const rows = (R.scorecard || []).filter((r) => r.metric === metric && r.fold === fold && r.median != null && SCORE_ROWS.includes(r.system));
    if (!rows.length) return;
    const b = rows[0];
    const W = widthOf(host, 600), m = { l: 30, r: 30, t: 50, b: 56 }, H = 270;
    const s = svg(host, W, H, "Where every brain lands on one test, against the spread of distances between real worms");
    const vals = rows.map((r) => r.median).concat([b.p05, b.p95]);
    const lo = Math.floor((Math.min(...vals) - 0.02) * 20) / 20, hi = Math.ceil((Math.max(...vals) + 0.02) * 20) / 20;
    const x = lin(lo, hi, m.l, W - m.r), y0 = Math.round(m.t + 52);
    el("rect", { x: x(b.p05), y: y0 - 38, width: x(b.p95) - x(b.p05), height: 76, rx: 6, fill: C.liveTint }, s);
    vline(s, x(b.bio), y0 - 46, y0 + 46, { stroke: C.live, "stroke-width": 2 });
    text(s, x(b.bio) + 8, y0 - 26, "median of two real worms", { fill: C.live, "font-weight": 600, "font-size": 12 });
    text(s, x(b.p05) + 8, y0 + 32, "5th percentile", { "font-size": 12, fill: C.live });
    text(s, x(b.p95) - 8, y0 + 32, "95th percentile", { "font-size": 12, fill: C.live, "text-anchor": "end" });
    hline(s, m.l, W - m.r, y0, { stroke: C.rule });
    const sorted = rows.slice().sort((a, c) => a.median - c.median), placed = [];
    sorted.forEach((r) => {
      const cx = x(r.median);
      let k = 0; while (placed.some((p) => Math.abs(p.x - cx) < 11 && p.k === k)) k++;
      placed.push({ x: cx, k });
      const cy = y0 + (k % 2 ? 1 : -1) * Math.ceil(k / 2) * 12;
      const g = el("g", { tabindex: 0 }, s);
      glyph(g, cx, cy, r.verdict, 5.25);
      el("circle", { cx, cy, r: 9, class: "hit" }, g);
      hover(g, `<b>${longName(r.system)}</b>${row("Median distance", fmt(r.median, 3))}${row("Verdict", r.verdict)}`);
      const call = { var3_spontaneous: "Linear brain learned from rest", [PASSER]: "Hybrid that passes the poke test" }[r.system];
      if (call) {
        const up = r.system === PASSER, ly = up ? y0 - 64 : y0 + 58, lx = cx + (up ? -18 : 18);
        el("path", { d: `M${cx},${cy + (up ? -6 : 6)} L${cx},${up ? ly + 6 : ly - 13}`, stroke: C.ink3, "stroke-width": 1, fill: "none" }, s);
        text(s, cx, up ? ly : ly, call, { "text-anchor": "middle", "font-size": 12, fill: C.ink, "font-weight": 600 });
      }
    });
    for (let v = lo; v <= hi + 1e-9; v += 0.05) { vline(s, x(v), H - m.b - 6, H - m.b, { stroke: C.rule }); text(s, x(v), H - m.b + 14, fmt(v, 2), { "text-anchor": "middle" }); }
    text(s, (m.l + W - m.r) / 2, H - 12, `${LEVELS[metric]}: distance from real worms, held-out group ${fold + 1}`, { "text-anchor": "middle", fill: C.ink2, "font-size": 12.5 });
  }

  // ------------------------------------------------------------- Figure: artificial networks against real worms
  const SHORT = { hybrid_kernels_regimes_obsfit: "Hybrid with noise and states", hybrid_kernels: "Plain hybrid",
    kunert2014: "Wiring-diagram model (Kunert 2014)", "linear-rest": "Linear network", var3_spontaneous: "Linear VAR",
    "creamer-native": "Published model (Creamer et al.)", "task-wired": "Task-trained, real wiring", "task-dense": "Task-trained, dense",
    "random-wiring": "Linear network, wiring randomised" };
  const TINY = { hybrid_kernels_regimes_obsfit: "Hybrid + noise, states", hybrid_kernels: "Plain hybrid",
    kunert2014: "Wiring-diagram model", "linear-rest": "Linear network", var3_spontaneous: "Linear VAR",
    "creamer-native": "Published model", "task-wired": "Task, real wiring", "task-dense": "Task, dense",
    "random-wiring": "Random wiring" };
  function gallery(host, opts) {
    const small = !!(opts && opts.compact);
    const D = (R.gallery || []).filter((d) => d.echo != null).slice().sort((a, b) => b.echo - a.echo);
    if (!D.length) return;
    const real = median(D.map((d) => d.real));
    const W = widthOf(host, small ? 200 : 300);
    const narrow = !small && W < 560;                      // a phone: the thumbnail layout, taller rows
    const labelled = (small && W >= 380) || narrow;        // short labels, no second line
    const compactLook = small || narrow;
    const m = compactLook ? { l: labelled ? Math.round(Math.min(210, W * (narrow ? 0.5 : 0.46))) : 10, r: 14, t: 30, b: labelled ? 34 : 18 }
      : { l: Math.round(Math.min(300, Math.max(190, W * 0.38))), r: 56, t: 44, b: 52 };
    const rowH = narrow ? 34 : small ? (heightOf(host, W * 0.75) - m.t - m.b) / D.length : 46;
    const H = narrow ? m.t + D.length * rowH + m.b : small ? heightOf(host, W * 0.75) : m.t + D.length * rowH + m.b;
    const s = svg(host, W, H, "Echo agreement with real worms for each family of artificial network");
    const x = lin(-0.005, 0.125, m.l, W - m.r);
    if (!compactLook || labelled) {
      [0, 0.05, 0.1].forEach((v) => { vline(s, x(v), m.t - 8, H - m.b, { stroke: v === 0 ? C.rule : C.soft }); text(s, x(v), H - m.b + (compactLook ? 16 : 20), fmt(v, 2), { "text-anchor": "middle", "font-size": compactLook ? 11 : null }); });
      if (!compactLook) text(s, (m.l + W - m.r) / 2, H - 12, "How well its echoes agree with real worms' (median over six held-out groups)", { "text-anchor": "middle", fill: C.ink2, "font-size": 12.5 });
      else text(s, (m.l + W - m.r) / 2, H - 2, "echo agreement with real worms", { "text-anchor": "middle", fill: C.ink3, "font-size": 11 });
    }
    el("rect", { x: Math.round(x(real)) - 1, y: m.t - (compactLook ? 8 : 14), width: 2, height: H - m.b - m.t + (compactLook ? 8 : 14), fill: C.live }, s);
    text(s, x(real) - 6, m.t - (compactLook ? 14 : 22), compactLook ? "real worms" : `Two real worms agree at ${fmt(real, 3)}`,
      { fill: C.live, "font-weight": 600, "text-anchor": "end", "font-size": compactLook ? 11 : 12.5 });
    D.forEach((d, i) => {
      const yy = Math.round(m.t + i * rowH + rowH / 2);
      const poked = d.learned.startsWith("pokes");
      if (labelled) text(s, m.l - 10, yy + 4, (narrow ? TINY[d.family] : SHORT[d.family]) || d.label, { "text-anchor": "end", "font-size": 11.5, fill: poked ? C.ink : C.ink2, "font-weight": poked ? 600 : 400 });
      if (!compactLook) {
        if (i % 2 === 0) el("rect", { x: 0, y: yy - rowH / 2 + 2, width: W, height: rowH - 4, rx: 6, fill: "#f7f8f9" }, s);
        text(s, m.l - 16, yy - 1, SHORT[d.family] || d.label, { "text-anchor": "end", "font-size": 13, fill: C.ink, "font-weight": poked ? 600 : 400 });
        text(s, m.l - 16, yy + 14, "learned from " + d.learned, { "text-anchor": "end", "font-size": 11.5, fill: C.ink3 });
      }
      el("line", { x1: x(d.lo), x2: x(d.hi), y1: yy, y2: yy, stroke: C.copy, "stroke-width": compactLook ? 1.5 : 2, opacity: 0.55 }, s);
      el("circle", { cx: x(d.echo), cy: yy, r: compactLook ? 4 : 5.5, fill: poked ? C.copy : C.plate, stroke: C.copy, "stroke-width": 1.75 }, s);
      if (!compactLook) text(s, x(d.hi) + 10, yy + 4.5, fmt(d.echo, 3), { "font-size": 12, fill: C.ink2 });
      if (!small) {
        const hit = el("rect", { x: 0, y: yy - rowH / 2, width: W, height: rowH, class: "hit" }, s);
        hover(hit, `<b>${SHORT[d.family] || d.label}</b>${row("Learned from", d.learned)}${row("Echo agreement", fmt(d.echo, 3) + " (" + fmt(d.lo, 3) + " to " + fmt(d.hi, 3) + ")")}${row("Shown to agree on the echo pattern", d.pattern + " of " + d.pools + " groups")}${row("Watching tests passed", d.watchLo === d.watchHi ? d.watchLo + " of 6" : d.watchLo + " to " + d.watchHi + " of 6")}`);
      }
    });
  }

  // ------------------------------------------------------------- Figure: watching hits a ceiling, poking keeps climbing
  function ceiling(host, opts) {
    const small = !!(opts && opts.compact);
    const S = R.synthetic || []; if (!S.length) return;
    const hours = [...new Set(S.map((d) => d.hours))].sort((a, b) => a - b);
    const avg = (regime, key) => hours.map((h) => { const v = S.filter((d) => d.regime === regime && d.hours === h).map((d) => d[key]); return [h, v.reduce((a, b) => a + b, 0) / v.length]; });
    const series = [
      { pts: avg("hidden", "watching"), c: C.copy, dash: "5 4", w: 1.5, label: "Watching, no shared hidden drives", op: 0.6 },
      { pts: avg("drive05", "watching"), c: C.copy, w: 2.4, label: "Watching", op: 1 },
      { pts: avg("drive05", "poking"), c: C.ink, w: 2.4, label: "Poking", op: 1 },
    ];
    const W = widthOf(host, small ? 200 : 300);
    const narrow = !small && W < 560;
    const H = small ? heightOf(host, W * 0.75) : Math.round(Math.min(440, Math.max(narrow ? 280 : 320, W * 0.55)));
    const labelled = small && W >= 260;
    const m = small ? { l: labelled ? 30 : 10, r: labelled ? Math.round(Math.min(150, W * 0.3)) : 12, t: 14, b: labelled ? 30 : 16 }
      : { l: narrow ? 52 : 64, r: narrow ? 104 : Math.round(Math.min(230, W * 0.3)), t: 24, b: 58 };
    const s = svg(host, W, H, "How well a synthetic worm's cause and effect is recovered, by watching and by poking, as recording hours grow");
    const lx = (h) => Math.log10(h);
    const x = lin(lx(0.5), lx(80), m.l, W - m.r), y = lin(0, 0.7, H - m.b, m.t);
    if (labelled) {
      [0, 0.2, 0.4, 0.6].forEach((v) => { hline(s, m.l, W - m.r, y(v), { stroke: v === 0 ? C.rule : C.soft }); text(s, m.l - 6, y(v) + 4, fmt(v, 1), { "text-anchor": "end", "font-size": 11 }); });
      text(s, (m.l + W - m.r) / 2, H - 4, "hours of recording", { "text-anchor": "middle", fill: C.ink3, "font-size": 11 });
      [1, 10, 70].forEach((h) => text(s, x(lx(h)), H - m.b + 15, String(h), { "text-anchor": "middle", "font-size": 11 }));
    }
    if (!small) {
      [0, 0.2, 0.4, 0.6].forEach((v) => { hline(s, m.l, W - m.r, y(v), { stroke: v === 0 ? C.rule : C.soft }); text(s, m.l - 10, y(v) + 4, fmt(v, 1), { "text-anchor": "end" }); });
      hours.filter((h) => !narrow || h !== 40).forEach((h) => text(s, x(lx(h)), H - m.b + 20, String(h), { "text-anchor": "middle" }));
      text(s, (m.l + W - m.r) / 2, H - 14, narrow ? "Hours of recording (log scale)" : "Hours of recording (log scale; the real atlas is about 70)", { "text-anchor": "middle", fill: C.ink2, "font-size": 12.5 });
      text(s, 0, 0, "Cause and effect recovered", { "text-anchor": "middle", fill: C.ink2, "font-size": 12.5, transform: `translate(18 ${(m.t + H - m.b) / 2}) rotate(-90)` });
      vline(s, x(lx(70)), m.t, H - m.b, { stroke: C.rule, "stroke-dasharray": "2 3" });
    }
    series.forEach((sr) => {
      el("path", { d: sr.pts.map((p, i) => (i ? "L" : "M") + x(lx(p[0])).toFixed(1) + "," + y(p[1]).toFixed(1)).join(""), fill: "none", stroke: sr.c, "stroke-width": small ? sr.w * 0.8 : sr.w, "stroke-dasharray": sr.dash || null, opacity: sr.op }, s);
      sr.pts.forEach((p) => {
        const c = el("circle", { cx: x(lx(p[0])), cy: y(p[1]), r: small ? 2.5 : 4, fill: sr.dash ? C.plate : sr.c, stroke: sr.c, "stroke-width": 1.5, opacity: sr.op }, s);
        if (!small) hover(c, `<b>${sr.label}</b>${row("Hours", p[0])}${row("Recovered", fmt(p[1], 2))}`);
      });
      if (!small || labelled) {
        const last = sr.pts[sr.pts.length - 1];
        const fs = small || narrow ? 11.5 : 12.5, lh = small || narrow ? 13 : 15;
        wrapWords(sr.label, small || narrow ? 14 : 22).forEach((ln, k) => text(s, x(lx(last[0])) + (small ? 8 : 12), y(last[1]) + 4 + k * lh, ln, { "font-size": fs, fill: sr.c, "font-weight": sr.dash ? 400 : 600, opacity: sr.op }));
      }
    });
  }


  // ------------------------------------------------------------- Figure: the law in brains whose truth is known
  function law(host, opts) {
    const small = !!(opts && opts.compact);
    const A = R.ann || []; if (!A.length) return;
    const panels = [
      { rec: "every", share: 0, tau: 10, title: "Every neuron recorded", sub: "no hidden drives" },
      { rec: "every", share: 0.25, tau: 90, title: "Every neuron recorded", sub: "slow hidden drives" },
      { rec: "atlas", share: 0.05, tau: 90, title: "Recorded like the atlas", sub: "half the neurons, slow drives" },
    ];
    const use = small ? [panels[2]] : panels;
    const W = widthOf(host, small ? 200 : 300);
    const stack = !small && W < 620;
    const pw = stack ? W : W / use.length;
    const ph = small ? heightOf(host, W * 0.75) : Math.round(stack ? 230 : Math.min(330, Math.max(250, pw * 0.95)));
    const H = stack ? ph * use.length : ph;
    const s = svg(host, W, H, "Cause and effect recovered by watching and by poking, in artificial brains whose truth is known, as recording hours grow");
    const lx = (h) => Math.log10(h);
    use.forEach((P, i) => {
      const ox = stack ? 0 : i * pw, oy = stack ? i * ph : 0;
      const labelled = !small || pw >= 260;
      const m = small ? { l: labelled ? 30 : 10, r: labelled ? 92 : 12, t: 14, b: labelled ? 30 : 14 } : { l: i === 0 || stack ? 46 : 18, r: 74, t: 48, b: 40 };
      const x = lin(lx(2), lx(85), ox + m.l, ox + pw - m.r), y = lin(0, 1, oy + ph - m.b, oy + m.t);
      const pick = A.filter((d) => d.rec === P.rec && d.share === P.share && d.tau === P.tau);
      const hours = [...new Set(pick.map((d) => d.hours))].sort((a, b) => a - b);
      const mean = (k) => hours.map((h) => { const v = pick.filter((d) => d.hours === h).map((d) => d[k]); return [h, v.reduce((a, b) => a + b, 0) / v.length]; });
      const ser = [
        { k: "linear", c: C.copy, w: 1.4, dash: "4 3", op: 0.65, label: "Linear watcher" },
        { k: "mlp", c: C.copy, w: 2.4, label: "Neural-net watcher" },
        { k: "poke", c: C.ink, w: 2.4, label: "Poking" },
      ];
      if (labelled) {
        [0, 0.5, 1].forEach((v) => { hline(s, ox + m.l, ox + pw - m.r, y(v), { stroke: v === 0 ? C.rule : C.soft }); if (i === 0 || stack || small) text(s, ox + m.l - 6, y(v) + 4, fmt(v, 1), { "text-anchor": "end", "font-size": 11 }); });
        hours.forEach((h) => text(s, x(lx(h)), oy + ph - m.b + 15, String(h), { "text-anchor": "middle", "font-size": 11 }));
        if (!small) {
          text(s, ox + m.l, oy + 18, P.title, { "font-weight": 600, "font-size": 13, fill: C.ink });
          text(s, ox + m.l, oy + 34, P.sub, { "font-size": 12, fill: C.ink2 });
          text(s, (ox + m.l + ox + pw - m.r) / 2, oy + ph - 6, "hours of recording", { "text-anchor": "middle", fill: C.ink3, "font-size": 11 });
        }
      }
      // end labels, nudged apart so they never overlap
      const ends = ser.map((sr) => { const pts = mean(sr.k); return { sr, yy: y(pts[pts.length - 1][1]) + 4 }; }).sort((a, b) => a.yy - b.yy);
      for (let j = 1; j < ends.length; j++) if (ends[j].yy - ends[j - 1].yy < 13) ends[j].yy = ends[j - 1].yy + 13;
      ser.forEach((sr) => { sr.labelY = ends.find((e) => e.sr === sr).yy; });
      ser.forEach((sr) => {
        const pts = mean(sr.k);
        el("path", { d: pts.map((p, j) => (j ? "L" : "M") + x(lx(p[0])).toFixed(1) + "," + y(p[1]).toFixed(1)).join(""), fill: "none", stroke: sr.c, "stroke-width": small ? sr.w * 0.8 : sr.w, "stroke-dasharray": sr.dash || null, opacity: sr.op || 1 }, s);
        pts.forEach((p) => {
          const c = el("circle", { cx: x(lx(p[0])), cy: y(p[1]), r: small ? 2.3 : 3.6, fill: sr.dash ? C.plate : sr.c, stroke: sr.c, "stroke-width": 1.4, opacity: sr.op || 1 }, s);
          if (!small) hover(c, `<b>${sr.label}</b>${row("Recording", P.title + ", " + P.sub)}${row("Hours", p[0])}${row("Cause and effect recovered", fmt(p[1], 2))}`);
        });
        if (labelled) {
          const last = pts[pts.length - 1];
          text(s, x(lx(last[0])) + 8, sr.labelY, small ? sr.label.replace(" watcher", "") : sr.label.split(" ")[0], { "font-size": 11, fill: sr.c, "font-weight": sr.dash ? 400 : 600, opacity: sr.op || 1 });
        }
      });
    });
  }

  // ------------------------------------------------------------- Figure: the ruler checked against known truth
  const TRUTH_NAMES = {
    species_mean: "The species-average brain", another_individual: "Another individual",
    "scrambled_0.1": "10% of connections moved", "scrambled_0.25": "25% of connections moved", "scrambled_1.0": "All connections moved",
    hybrid_kernels: "Copy that learned from pokes", var3_spontaneous: "Copy that learned by watching",
  };
  function rulerTruth(host, opts) {
    const small = !!(opts && opts.compact);
    const D = (R.annRuler || []).filter((d) => d.species === "base" && TRUTH_NAMES[d.copy]).sort((a, b) => b.ratio - a.ratio);
    if (!D.length) return;
    const W = widthOf(host, small ? 200 : 300);
    const narrow = !small && W < 600;
    const rowH = small ? (heightOf(host, W * 0.75) - 20) / D.length : narrow ? 46 : 38;
    const m = small ? { l: 8, r: 8, t: 8, b: 12 } : { l: narrow ? 8 : 210, r: narrow ? 8 : 190, t: 34, b: 34 };
    const H = Math.round(m.t + m.b + rowH * D.length);
    const s = svg(host, W, H, "How close each copy truly is to real individuals, against what the ruler said");
    const x = lin(0, 1.25, m.l, W - m.r);
    if (!small) {
      [0, 0.5, 1].forEach((v) => text(s, x(v), H - 12, v === 1 ? "as close as an individual" : Math.round(v * 100) + "%", { "text-anchor": "middle", "font-size": 11, fill: C.ink3 }));
      text(s, m.l, 18, "Echo closeness to real individuals, as a share of how close individuals are to each other", { "font-size": 12, fill: C.ink2 });
    }
    el("rect", { x: x(0.8), y: m.t - 4, width: x(1.25) - x(0.8), height: H - m.t - m.b + 8, fill: C.liveWash }, s);
    vline(s, x(1), m.t - 4, H - m.b + 4, { stroke: C.live, "stroke-width": 1.5 });
    D.forEach((d, i) => {
      const yy = m.t + i * rowH;
      const col = d.copy === "hybrid_kernels" ? C.live : d.copy === "var3_spontaneous" ? C.copy : C.ink3;
      const bh = small ? Math.max(3, rowH * 0.5) : 12;
      const by = narrow ? yy + 20 : yy + (rowH - bh) / 2;
      el("rect", { x: x(0), y: by, width: Math.max(1, x(Math.max(0, d.ratio)) - x(0)), height: bh, fill: col, rx: 2 }, s);
      if (!small) {
        const lab = TRUTH_NAMES[d.copy];
        if (narrow) text(s, m.l, yy + 13, lab, { "font-size": 12, fill: C.ink, "font-weight": 500 });
        else text(s, m.l - 12, by + bh - 1, lab, { "text-anchor": "end", "font-size": 12.5, fill: C.ink });
        const verdict = d.agrees + " of " + d.pools + " groups";
        if (narrow) text(s, W - m.r, yy + 13, "shown to agree: " + verdict, { "text-anchor": "end", "font-size": 11, fill: d.agrees ? C.live : C.ink3 });
        else text(s, W - m.r + 12, by + bh - 1, "ruler: agrees in " + verdict, { "font-size": 12, fill: d.agrees ? C.live : C.ink3, "font-weight": d.agrees ? 600 : 400 });
        const hit = el("rect", { x: 0, y: yy, width: W, height: rowH, class: "hit" }, s);
        hover(hit, `<b>${lab}</b>${row("Echo closeness vs an individual", Math.round(d.ratio * 100) + "%")}${row("Pattern verdict inside", d.inside + " of " + d.pools)}${row("Shown to agree", verdict)}`);
      }
    });
  }

  // ------------------------------------------------------------- legend for verdict glyphs
  function verdictLegend(host) {
    host.innerHTML = '<span class="k"><span class="sw full"></span>Inside: as real as a real worm</span>' +
      '<span class="k"><span class="sw open"></span>Outside</span>' +
      '<span class="k"><span class="sw half"></span>Too typical: more average than any real worm</span>' +
      (host.dataset.legend === "noband" ? "" : '<span class="k"><span class="sw band"></span>Inside in all three groups</span>');
  }

  const FIGS = { rulerStrip, scorecard, restPoke, power, signalNoise, fingerprint, echoShape, calibration, mind, gallery, ceiling, law, rulerTruth };
  window.NematicaCharts = Object.assign({ verdictLegend, name }, FIGS);

  // mount every <div data-chart="..."> and redraw when its width changes
  function draw(n) {
    const fn = FIGS[n.dataset.chart];
    if (!fn) return;
    try { fn(n, { compact: n.hasAttribute("data-compact") }); } catch (e) { console.error(n.dataset.chart, e); n.textContent = "This figure could not be drawn."; }
  }
  function mount() {
    const nodes = [...document.querySelectorAll("[data-chart]")];
    const run = () => nodes.forEach(draw);
    (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(run);
    const seen = new WeakMap();
    const ro = new ResizeObserver((entries) => entries.forEach((e) => {
      const w = Math.round(e.contentRect.width);
      if (seen.get(e.target) === undefined) { seen.set(e.target, w); return; }
      if (Math.abs(seen.get(e.target) - w) > 2) { seen.set(e.target, w); draw(e.target); }
    }));
    nodes.forEach((n) => ro.observe(n));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
