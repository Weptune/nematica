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
    if (attrs && attrs["aria-label"] && !attrs.role) n.setAttribute("role", "img");                 // a name is only allowed on a mark that has a role
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
      rowEls.forEach((o) => o.bg.setAttribute("fill", o.isPass ? C.liveWash : (yy >= o.y && yy < o.y + rowH - 2 ? "rgba(12,42,85,.06)" : "transparent")));
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
          fill: v === "inside" ? C.live : v === "outside" ? C.plate : "rgba(12,42,85,.14)", stroke: v === "outside" ? C.rule : "none" }, s);
        hover(r, `<b>Group ${f + 1}, correlation ${fmt(p.f)}</b><br>${p.verdicts.join(", ")}<br><span class="dim">agreement with real worms ${fmt(1 - p.d)}</span>`);
      });
    });
    const ly = H - m.b + 68 + 3 * 22 + 8;
    [[C.live, "none", "Inside: as real as a real worm"], [C.plate, C.rule, "Outside: too little cause and effect"], ["rgba(12,42,85,.14)", "none", "Too typical: more stereotyped than any worm"]].forEach((k, i) => {
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
      if (i % 2 === 0) el("rect", { x: 0, y: yy - rowH / 2 + 2, width: W, height: rowH - 4, rx: 6, fill: "rgba(12,42,85,.04)" }, s);
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
    sys.forEach((sy, i) => { if (i % 2 === 0) el("rect", { x: 0, y: top + i * rowH + 1, width: W, height: rowH - 2, rx: 6, fill: "rgba(12,42,85,.04)" }, s); });
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
        if (i % 2 === 0) el("rect", { x: 0, y: yy - rowH / 2 + 2, width: W, height: rowH - 4, rx: 6, fill: "rgba(12,42,85,.04)" }, s);
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

  // ------------------------------------------------------------- Figure: mouse by mouse (map study, amendment 27)
  function permouse(host) {
    const P = R.permouse; if (!P) return;
    const D = P.mice, n = D.length;
    const W = widthOf(host, 300), narrow = W < 680;
    const m = { l: 44, r: narrow ? 14 : 178, t: narrow ? 58 : 22, b: 44 };
    const H = narrow ? 340 : 400;
    const s = svg(host, W, H, `Slow memory of ${n} Allen mice, of a random network recorded at each mouse's own instrument, and of the same network with slow drives`);
    const x = (i) => m.l + 8 + (i * (W - m.l - m.r - 16)) / (n - 1);
    const y = lin(0, 0.34, H - m.b, m.t);
    [0, 0.1, 0.2, 0.3].forEach((v) => { hline(s, m.l, W - m.r, y(v), { stroke: v ? C.soft : C.rule }); text(s, m.l - 8, y(v) + 4, fmt(v, 1), { "text-anchor": "end", "font-size": 11, fill: C.ink3 }); });
    text(s, m.l, H - 14, narrow ? `${n} mice, by their own slow memory` : `${n} mice, ordered by their own slow memory (spontaneous activity)`, { "font-size": 11.5, fill: C.ink3 });
    const lab = (t, xx, yy, col, w) => text(s, xx, yy, t, { "font-size": 12, fill: col, "font-weight": w || 500 });
    D.forEach((d, i) => {
      const xi = x(i);
      vline(s, xi, y(Math.max(d.m, d.rnn)), y(Math.min(d.m, d.rnn)), { stroke: C.rule, "stroke-width": 1 });
      if (d.slow != null) el("circle", { cx: xi, cy: y(d.slow), r: 4.2, fill: C.plate, stroke: C.ink3, "stroke-width": 1.4 }, s);
      el("circle", { cx: xi, cy: y(d.rnn), r: 4.2, fill: C.copy }, s);
      el("circle", { cx: xi, cy: y(d.m), r: 4.6, fill: C.live, stroke: C.plate, "stroke-width": 1.2 }, s);
      const hit = el("rect", { x: xi - (W - m.l - m.r) / (2 * n), y: m.t, width: (W - m.l - m.r) / n, height: H - m.t - m.b, class: "hit", tabindex: 0,
        "aria-label": `Mouse ${i + 1}: ${fmt(d.m, 3)}; random network ${fmt(d.rnn, 3)}; with slow drives ${d.slow == null ? "not measured" : fmt(d.slow, 3)}` }, s);
      hover(hit, `<b>Mouse ${i + 1} of ${n}</b>${row("Mouse", fmt(d.m, 3))}${row("Random network at its instrument", fmt(d.rnn, 3))}` +
        row("Same network with slow drives", d.slow == null ? "not measured" : fmt(d.slow, 3)) +
        row("Mouse minus network", `${fmt((d.m - d.rnn) / P.rulerSD, 1)} between-mouse SDs`));
    });
    if (!narrow) {
      const last = D[n - 1], xe = x(n - 1) + 14;
      const ys = [{ t: "Mouse", v: last.m, c: C.live }, { t: "Random network, recorded", v: last.rnn, c: C.copy, t2: "at that mouse's instrument" },
        { t: "Same network with", v: last.slow != null ? last.slow : 0.3, c: C.ink2, t2: "strong slow drives" }].map((o) => Object.assign(o, { yy: y(o.v) + 4 }))
        .sort((a, b) => a.yy - b.yy);
      for (let j = 1; j < ys.length; j++) if (ys[j].yy - ys[j - 1].yy < 32) ys[j].yy = ys[j - 1].yy + 32;
      ys.forEach((o) => { lab(o.t, xe, o.yy, o.c, 600); if (o.t2) lab(o.t2, xe, o.yy + 15, o.c, 400); });
    } else {
      const items = [["Mouse", C.live, "f"], ["Network", C.copy, "f"], ["Slow drives", C.ink3, "o"]];
      let lx = m.l;
      items.forEach(([t, c, k]) => {
        el("circle", { cx: lx + 4, cy: 20, r: 4, fill: k === "f" ? c : C.plate, stroke: c, "stroke-width": 1.4 }, s);
        const tt = lab(t, lx + 13, 24, C.ink2, 500); lx += 13 + tt.getComputedTextLength() + 16;
      });
    }
  }

  // ------------------------------------------------------------- Figure: Study 2, network families against 49 mice
  function slowFamilies(host) {
    const S = R.slowStudy; if (!S) return;
    const W = widthOf(host, 760), narrow = false;
    const labW = Math.min(280, Math.round(W * 0.3));
    const gap = narrow ? 22 : 34, pw = Math.floor((W - labW - gap - 8) / 2);
    const x1 = lin(0, 1, labW + 4, labW + pw - 4);
    const lo = Math.log10(0.06), hi = Math.log10(2.6);
    const x2 = (v) => labW + pw + gap + 4 + ((Math.log10(Math.max(0.06, Math.min(2.6, v))) - lo) / (hi - lo)) * (pw - 8);
    const F = Object.fromEntries(S.families.map((f) => [f.id, f]));
    const rows = [];
    [{ label: "Counted toward the verdict", fams: ["A2", "A3", "A5", "A6", "A7"] },
     { label: "Shown, not counted: changing their playback speed moved them", fams: ["A1", "A4"] }].forEach((sc) => {
      rows.push({ kind: "sec", label: sc.label, h: 36 });
      sc.fams.forEach((id) => {
        const f = F[id]; if (!f) return;
        if (id === "A1" || id === "A4") rows.push({ kind: "sweep", f, h: narrow ? 66 : 54 });
        else if (f.members.length > 1) { rows.push({ kind: "head", f, h: narrow ? 50 : 50 }); f.members.forEach((mb) => rows.push({ kind: "mem", f, mb, sub: true, h: narrow ? 36 : 27 })); }
        else rows.push({ kind: "mem", f, mb: f.members[0], h: narrow ? 66 : 54 });
      });
    });
    const top = 74, H = top + rows.reduce((a, r) => a + r.h, 0) + 34;
    const s = svg(host, W, H, "Internal share and relative slowness of each network family, against 49 mice");
    const panels = [{ x: x1, a: labW, title: "How much state is internal", sub: "internal share (M1)", key: "M1", ticks: [0, 0.25, 0.5, 0.75, 1], tf: (v) => (v === 0 || v === 1 ? String(v) : String(v)) },
      { x: x2, a: labW + pw + gap, title: "How slow it is, relative to the input", sub: "internal ÷ locked timescale (M2), log scale", key: "M2", ticks: [0.1, 0.3, 1, 2], tf: (v) => String(v) }];
    panels.forEach((p) => {
      el("rect", { x: p.a + 2, y: 0, width: pw - 4, height: 2, fill: C.ink }, s);
      text(s, p.a + 2, 20, p.title, { class: "label-strong", "font-size": 12.5 });
      text(s, p.a + 2, 36, p.sub, { "font-size": 11.5, fill: C.ink3 });
      const q = S.mice[p.key];
      el("rect", { x: p.x(q[0]), y: top - 16, width: p.x(q[2]) - p.x(q[0]), height: H - top - 12, fill: C.liveWash }, s);
      vline(s, p.x(q[1]), top - 16, H - 28, { stroke: C.live, "stroke-width": 1.5 });
      S.mice[p.key + "all"].forEach((v) => vline(s, p.x(v), top - 14, top - 6, { stroke: C.live, "stroke-width": 1, opacity: 0.55 }));
      text(s, p.x(q[1]) + 5, top - 20, `${S.mice.n} mice, median ${fmt(q[1], 2)}`, { "font-size": 11, fill: C.live, "font-weight": 600 });
      p.ticks.forEach((v) => { vline(s, p.x(v), H - 28, H - 22, { stroke: C.rule }); text(s, p.x(v), H - 8, p.tf(v), { "text-anchor": "middle", "font-size": 11, fill: C.ink3 }); });
    });
    vline(s, x2(1), top - 4, H - 28, { stroke: C.ink3, "stroke-dasharray": "2 3", opacity: 0.6 });
    if (!narrow) text(s, x2(1) - 5, H - 34, "1: as slow as the input", { "font-size": 10.5, fill: C.ink3, "text-anchor": "end" });
    const v1 = (f) => f.M1.verdict === "confirmed" ? "more in the mice" : f.M1.verdict === "refuted" ? "more in the network" :
      f.M1.d === 0 ? (f.id === "A6" ? "sizes span the mice" : "gains span the mice") : "not decided";
    const v2 = (f) => f.M2.verdict === "confirmed" ? "mice slower" : f.M2.verdict === "refuted" ? "network slower" :
      ["A5", "A6", "A7"].includes(f.id) ? "not decided, leaning network slower" : "not decided";
    const tipFor = (f, mb) => `<b>${f.name}${mb && mb.label ? " " + mb.label : ""}</b>` +
      (mb ? row("Recordings (one per mouse)", mb.n) + row("Internal share M1", `${fmt(mb.M1[1])} [${fmt(mb.M1[0])} to ${fmt(mb.M1[2])}]`) + row("Relative slowness M2", `${fmt(mb.M2[1])} [${fmt(mb.M2[0])} to ${fmt(mb.M2[2])}]`) : "") +
      row("Internal share", `${v1(f)} (${fmt(f.M1.d, 1)} rulers)`) + row("Slowness", `${v2(f)} (${fmt(f.M2.d, 1)})`) +
      (f.counted ? "" : row("Counted", "no: playback-speed sensitive"));
    let y = top;
    rows.forEach((r) => {
      if (r.kind === "sec") { text(s, 2, y + 24, r.label, { "font-size": 11.5, fill: C.ink3, "font-weight": 600 }); y += r.h; return; }
      const fam = r.kind !== "mem" || !r.sub;
      const yc = r.sub ? y + r.h / 2 : y + (narrow ? 46 : 18);
      if (fam) {
        text(s, 2, y + 18 + (narrow ? 0 : 4), r.f.name, { "font-size": 13, fill: C.ink, "font-weight": 650 });
        if (narrow) text(s, 2, y + 33, `internal share: ${v1(r.f)}; slowness: ${v2(r.f)}`, { "font-size": 10.5, fill: C.ink3 });
        else { text(s, 2, y + 37, "internal share: " + v1(r.f), { "font-size": 11, fill: C.ink3 }); text(s, 2, y + 50, "slowness: " + v2(r.f), { "font-size": 11, fill: C.ink3 }); }
      } else text(s, narrow ? 2 : 20, narrow ? y + 12 : yc + 4, r.mb.label, { "font-size": 12, fill: C.ink2 });
      const ym = r.sub && narrow ? y + 26 : yc;
      if (r.kind === "mem") {
        [[x1, "M1"], [x2, "M2"]].forEach(([fx, k]) => {
          const q = r.mb[k]; if (!q) return;
          el("line", { x1: fx(q[0]), x2: fx(q[2]), y1: ym, y2: ym, stroke: C.copy, "stroke-width": 2.6, "stroke-linecap": "round" }, s);
          el("circle", { cx: fx(q[1]), cy: ym, r: 5, fill: C.copy, stroke: C.plate, "stroke-width": 1.5 }, s);
        });
      }
      if (r.kind === "sweep") {
        [[x1, "M1"], [x2, "M2"]].forEach(([fx, k]) => {
          const meds = r.f.members.map((mb) => mb[k][1]);
          el("path", { d: meds.map((v, j) => (j ? "L" : "M") + fx(v).toFixed(1) + "," + ym).join(""), stroke: C.ink3, "stroke-width": 1.2, "stroke-dasharray": "1 2.5", fill: "none" }, s);
          meds.forEach((v) => el("circle", { cx: fx(v), cy: ym, r: 3.6, fill: C.plate, stroke: C.ink3, "stroke-width": 1.4 }, s));
        });
      }
      if (r.kind !== "head") {
        const hit = el("rect", { x: 0, y, width: W, height: r.h, class: "hit", tabindex: 0, "aria-label": `${r.f.name} ${r.mb ? r.mb.label : ""}` }, s);
        hover(hit, () => tipFor(r.f, r.mb) + (r.kind === "sweep" ? `<br><span class="dim">Medians at eight input gains, ${r.f.members[0].label.slice(5)} to ${r.f.members[r.f.members.length - 1].label.slice(5)}, shown as rings</span>` : ""));
      }
      y += r.h;
    });
  }

  // ------------------------------------------------------------- Figure: the emulator on its own worms and on others
  function emulator(host) {
    const E = R.emulator; if (!E) return;
    const W = widthOf(host, 720), narrow = false;
    const ROWS = [
      { k: "atlas_cv3", t: "Atlas worms", s: "the split it was chosen on" },
      { k: "atlas_blocks1", t: "Atlas worms", s: "a second split of the same worms" },
      { k: "unc31", t: "unc-31 worms", s: "same atlas, never used to build it", bar: 4 },
      { k: "unc31_control_rest", t: "Control: fitted to rest only", s: "", control: true },
      { k: "atanas", t: "Freely moving worms", s: "another lab; no pokes, activity tests only", bar: 4 },
      { k: "atanas_control_rest", t: "Control: fitted to rest only", s: "", control: true },
    ];
    const labW = narrow ? 0 : Math.min(260, Math.round(W * 0.3)), resW = narrow ? 0 : 150;
    const sq = narrow ? 5 : W > 900 ? 9 : 7, sgap = 2, block = 9 * (sq + sgap) + 6, seedGap = narrow ? 6 : 14;
    const seedsW = 5 * block + 4 * seedGap;
    const x0 = narrow ? 2 : labW + Math.max(0, (W - labW - resW - seedsW) / 2);
    const rh = narrow ? 52 : 46, top = 46;
    const H = top + ROWS.length * rh + 8;
    const s = svg(host, W, H, "The emulator recipe: activity and stimulation tests passed in each of five noise draws, on the worms it was built on and on others");
    for (let k = 0; k < 5; k++) {
      const bx = x0 + k * (block + seedGap);
      text(s, bx + block / 2, 16, `draw ${k + 1}`, { "text-anchor": "middle", "font-size": 11, fill: C.ink3 });
      if (k === 0 && !narrow) { text(s, bx, 34, "activity", { "font-size": 10, fill: C.ink3 }); text(s, bx + 6 * (sq + sgap) + 4, 34, "pokes", { "font-size": 10, fill: C.ink3 }); }
    }
    if (!narrow) text(s, W - resW + 10, 16, "passes the rule", { "font-size": 11, fill: C.ink3 });
    ROWS.forEach((rw, i) => {
      const d = E[rw.k]; if (!d) return;
      const y = top + i * rh, yc = narrow ? y + 34 : y + rh / 2;
      if (i && !rw.control) hline(s, 0, W, y + 2, { stroke: C.soft });
      const passN = d.filter((v) => v.pass).length;
      if (narrow) { text(s, 2, y + 16, rw.t + (rw.s ? ": " + rw.s : ""), { "font-size": 11.5, fill: rw.control ? C.ink3 : C.ink, "font-weight": rw.control ? 400 : 600 });
        text(s, W - 2, y + 16, `${passN} of 5`, { "text-anchor": "end", "font-size": 11.5, fill: passN >= 4 ? C.live : C.copy, "font-weight": 600 }); }
      else {
        text(s, rw.control ? 16 : 2, yc + (rw.s ? -2 : 4), rw.t, { "font-size": rw.control ? 12 : 13, fill: rw.control ? C.ink3 : C.ink, "font-weight": rw.control ? 400 : 600 });
        if (rw.s) text(s, 2, yc + 13, rw.s, { "font-size": 11, fill: C.ink3 });
      }
      d.forEach((v, k) => {
        const bx = x0 + k * (block + seedGap), ok = v.pass;
        const col = rw.control ? C.ink3 : ok ? C.live : C.copy;
        for (let j = 0; j < 9; j++) {
          const isPoke = j >= 6, xx = bx + j * (sq + sgap) + (isPoke ? 6 : 0);
          if (isPoke && v.poke == null) { hline(s, xx, xx + sq, yc, { stroke: C.rule }); continue; }
          const filled = isPoke ? j - 6 < v.poke : j < v.rest;
          el("rect", { x: xx, y: yc - sq / 2, width: sq, height: sq, rx: 1.2, fill: filled ? col : C.plate, stroke: filled ? col : C.rule, "stroke-width": 1 }, s);
        }
        const hit = el("rect", { x: bx - 3, y: y + 4, width: block + 6, height: rh - 8, class: "hit", tabindex: 0, "aria-label": `${rw.t}, draw ${k + 1}: ${v.rest} of 6 activity tests, ${v.poke == null ? "no pokes" : v.poke + " of 3 poke tests"}, ${ok ? "passes" : "fails"}` }, s);
        hover(hit, `<b>${rw.t}, noise draw ${k + 1}</b>${row("Activity tests passed", v.rest + " of 6 (needs 5)")}${row("Poke tests passed", v.poke == null ? "no pokes in this data" : v.poke + " of 3 (needs 3)")}${row("Rule", ok ? "passes" : "fails")}`);
      });
      if (!narrow) {
        text(s, W - resW + 10, yc + 4, `${passN} of 5`, { "font-size": 13, fill: rw.control ? C.ink3 : passN >= 4 ? C.live : C.copy, "font-weight": 650 });
        if (rw.bar && !rw.control) text(s, W - resW + 52, yc + 4, `(needs ${rw.bar})`, { "font-size": 11, fill: C.ink3 });
      }
    });
  }

  // ------------------------------------------------------------- Figure: where the answer stands (home page)
  function gaps(host) {
    const G = R.gaps; if (!G) return;
    const W = widthOf(host, 300), narrow = W < 820;
    const labW = narrow ? 0 : Math.min(300, Math.round(W * 0.25)), stW = narrow ? 0 : Math.min(270, Math.round(W * 0.23));
    const trA = labW + (narrow ? 6 : 34), trB = W - stW - (narrow ? 6 : 44);
    const rh = narrow ? 240 : 138;
    const H = G.length * rh + 4;
    const s = svg(host, W, H, "Each measured difference between real and artificial networks, and what closed it");
    const STC = { closed: C.live, none: C.ink, open: C.copy };
    G.forEach((g, i) => {
      const y0 = i * rh;
      hline(s, 0, W, y0 + 1, { stroke: i ? C.rule : C.ink, "stroke-width": i ? 1 : 2 });
      const ty = y0 + 32;
      text(s, 0, ty, g.title, { "font-size": narrow ? 16 : 17, fill: C.ink, "font-weight": 650 });
      text(s, 0, ty + 19, g.where, { "font-size": 12.5, fill: C.ink3 });
      const yt = narrow ? y0 + 112 : y0 + 74;
      const x = lin(g.domain[0], g.domain[1], trA, trB);
      hline(s, trA, trB, yt, { stroke: C.rule });
      (g.ticks || g.domain).forEach((v) => { vline(s, x(v), yt, yt + 5, { stroke: C.rule });
        text(s, x(v), yt + 19, g.tickFmt === "int" ? String(v) : fmt(v, g.dp == null ? 2 : g.dp), { "text-anchor": "middle", "font-size": 11, fill: C.ink3 }); });
      text(s, trA, yt + 38, g.scale, { "font-size": 11.5, fill: C.ink2 });
      const labels = [];
      if (g.band) {
        const bw = Math.max(4, x(g.band[1]) - x(g.band[0]));
        el("rect", { x: x(g.band[0]) - (bw === 4 ? 2 : 0), y: yt - 11, width: bw, height: 22, rx: 4, fill: C.liveTint }, s);
        if (g.bandLabel) labels.push({ x: x((g.band[0] + g.band[1]) / 2), t: g.bandLabel, c: C.live, w: 600 });
      }
      const mark = (o, filled) => {
        if (!o) return;
        const v0 = o.value != null ? o.value : o.values ? null : (o.range[0] + o.range[1]) / 2;
        const inBand = g.band && v0 != null && v0 >= g.band[0] && v0 <= g.band[1];
        const col = filled ? (inBand || o.ok ? C.live : C.copy) : C.copy;
        if (o.range) el("line", { x1: x(o.range[0]), x2: x(o.range[1]), y1: yt, y2: yt, stroke: col, "stroke-width": 3.2, "stroke-linecap": "round", opacity: 0.5 }, s);
        (o.values || [v0]).forEach((v) => el("circle", { cx: x(v), cy: yt, r: filled ? 6 : 5.2, fill: filled ? col : C.plate, stroke: col, "stroke-width": 1.9 }, s));
        if (o.label) {
          const xs = (o.values || [v0]).map(x);
          labels.push({ x: (Math.min(...xs) + Math.max(...xs)) / 2, t: o.label, c: col, w: 500 });
        }
      };
      mark(g.plain, false); mark(g.fixed, true);
      // place labels above the track, lifting any that would overlap a neighbour
      const placed = [];
      labels.sort((a, b) => a.x - b.x).forEach((L) => {
        const tt = text(s, 0, 0, L.t, { "font-size": 11.5, fill: L.c, "font-weight": L.w });
        const w = tt.getComputedTextLength();
        let lx = Math.max(trA - 20, Math.min(L.x - w / 2, trB + 20 - w));
        let lvl = 0;
        while (placed.some((p) => p.lvl === lvl && lx < p.x1 + 10 && lx + w > p.x0 - 10)) lvl++;
        placed.push({ x0: lx, x1: lx + w, lvl });
        tt.setAttribute("x", lx); tt.setAttribute("y", yt - 17 - lvl * 16);
        if (lvl) vline(s, L.x, yt - 14 - lvl * 16 + 4, yt - 9, { stroke: L.c, "stroke-width": 1, opacity: 0.5 });
      });
      // status
      const sx = narrow ? 0 : W - stW, sy = narrow ? y0 + 186 : y0 + 32;
      el("circle", { cx: sx + 5.5, cy: sy - 4.5, r: 5, fill: g.status.kind === "open" ? C.plate : STC[g.status.kind], stroke: STC[g.status.kind], "stroke-width": 1.7 }, s);
      text(s, sx + 18, sy, g.status.text, { "font-size": 14, fill: STC[g.status.kind], "font-weight": 650 });
      if (!narrow) wrapWords(g.status.sub || "", 36).forEach((l, j) => text(s, sx + 18, sy + 20 + j * 16, l, { "font-size": 12, fill: C.ink3 }));
      else if (g.status.sub) wrapWords(g.status.sub, Math.floor((W - 24) / 6.3)).slice(0, 3).forEach((l, j) => text(s, sx + 18, sy + 18 + j * 15, l, { "font-size": 11.5, fill: C.ink3 }));
      const hit = el("rect", { x: 0, y: y0 + 2, width: W, height: rh - 4, class: "hit", tabindex: 0, "aria-label": `${g.title}: ${g.status.text}` }, s);
      hover(hit, `<b>${g.title}</b><br><span class="dim">${g.where}</span>${(g.tip || []).map((t) => row(t[0], t[1])).join("")}${g.note ? `<br><span class="dim">${g.note}</span>` : ""}`);
    });
  }

  // ------------------------------------------------------------- legend for verdict glyphs
  function verdictLegend(host) {
    host.innerHTML = '<span class="k"><span class="sw full"></span>Inside: as real as a real worm</span>' +
      '<span class="k"><span class="sw open"></span>Outside</span>' +
      '<span class="k"><span class="sw half"></span>Too typical: more average than any real worm</span>' +
      (host.dataset.legend === "noband" ? "" : '<span class="k"><span class="sw band"></span>Inside in all three groups</span>');
  }

  // one point per model: how unlike real worms at rest, against how unlike them when poked
  function restAvg(host) {
    const by = {}; (R.restPoke || []).filter((d) => d.poke != null && d.restScore != null).forEach((d) => (by[d.brain] = by[d.brain] || []).push(d));
    const P = Object.keys(by).map((k) => ({ k, x: by[k].reduce((a, d) => a + d.restScore, 0) / by[k].length, y: by[k].reduce((a, d) => a + d.poke, 0) / by[k].length,
      g: k.startsWith("hybrid_kernels") ? (/connectome|shuffled/.test(k) ? "wiring" : "poke") : "watch" }));
    if (!P.length) return;
    const W = widthOf(host, 300), narrow = W < 680, H = narrow ? 410 : 470, m = { l: 56, r: narrow ? 14 : 236, t: narrow ? 76 : 22, b: 62 };
    const s = svg(host, W, H, `${P.length} models: distance from real worms at rest against distance of their answers to a poke. No relation; only models that learned from pokes reach the real-worm band.`);
    const xs = P.map((d) => d.x), x = lin(Math.min(...xs) - 0.008, Math.max(...xs) + 0.008, m.l, W - m.r), y = lin(0.86, 1.012, H - m.b, m.t);
    el("rect", { x: m.l, y: y(0.91), width: W - m.l - m.r, height: y(0.89) - y(0.91), fill: C.liveWash }, s);
    hline(s, m.l, W - m.r, y(0.91), { stroke: C.live, "stroke-opacity": .6 }); hline(s, m.l, W - m.r, y(0.89), { stroke: C.live, "stroke-opacity": .6 });
    [0.88, 0.92, 0.96, 1].forEach((v) => { hline(s, m.l, W - m.r, y(v), { stroke: C.soft }); text(s, m.l - 8, y(v) + 4, fmt(v), { "text-anchor": "end", "font-size": 11, fill: C.ink3 }); });
    hline(s, m.l, W - m.r, H - m.b, { stroke: C.rule });
    [0.04, 0.06, 0.08, 0.1, 0.12].forEach((v) => { if (x(v) > m.l + 10 && x(v) < W - m.r - 10) { vline(s, x(v), H - m.b, H - m.b + 5, { stroke: C.rule }); text(s, x(v), H - m.b + 18, fmt(v), { "text-anchor": "middle", "font-size": 11, fill: C.ink3 }); } });
    text(s, m.l, H - 14, narrow ? "Unlike real worms at rest (lower is more real)" : "How unlike real worms the model is at rest (lower is more realistic)", { "font-size": 11.5, fill: C.ink3 });
    if (!narrow) text(s, 0, 0, "How unlike real worms its answers to a poke are", { "font-size": 11.5, fill: C.ink3, "text-anchor": "middle", transform: `translate(14 ${(m.t + H - m.b) / 2}) rotate(-90)` });
    const NAME = { watch: "Learned by watching or forecasting", wiring: "Links only along a wiring diagram", poke: "Links learned from pokes" };
    const mark = (g, cx, cy, p) => g === "poke" ? el("circle", { cx, cy, r: 6, fill: C.copy, stroke: C.plate, "stroke-width": 1.5 }, p)
      : g === "wiring" ? el("rect", { x: cx - 4.6, y: cy - 4.6, width: 9.2, height: 9.2, fill: C.plate, stroke: C.copy, "stroke-width": 1.7, transform: `rotate(45 ${cx} ${cy})` }, p)
      : el("circle", { cx, cy, r: 5, fill: C.plate, stroke: C.copy, "stroke-width": 1.7 }, p);
    P.forEach((d) => { mark(d.g, x(d.x), y(d.y), s);
      const c = el("circle", { cx: x(d.x), cy: y(d.y), r: 11, class: "hit", tabindex: 0, "aria-label": `${NAMES[d.k] || d.k}: rest ${fmt(d.x, 3)}, poke ${fmt(d.y, 3)}` }, s);
      hover(c, `<b>${NAMES[d.k] || d.k}</b>${row("Group", NAME[d.g])}${row("Unlike real worms at rest", fmt(d.x, 3))}${row("Unlike real worms when poked", fmt(d.y, 3))}`); });
    const keys = [["poke", ["Links learned from pokes"]], ["wiring", ["Links only along a", "wiring diagram"]], ["watch", ["Learned by watching", "or forecasting"]]];
    if (narrow) keys.forEach(([g, t], i) => { mark(g, 10, 14 + i * 22, s); text(s, 24, 18 + i * 22, t.join(" "), { "font-size": 12, fill: C.ink2 }); });
    else { const lx = W - m.r + 24; text(s, lx, y(0.9) + 4, "Real worm against real worm", { "font-size": 12, fill: C.ink, "font-weight": 600 });
      keys.forEach(([g, t], i) => { const yy = m.t + 16 + i * 46; mark(g, lx + 6, yy, s); t.forEach((u, j) => text(s, lx + 22, yy + 4 + j * 16, u, { "font-size": 12, fill: j ? C.ink2 : C.ink, "font-weight": j ? 500 : 600 })); }); }
  }

  // a repeat poke: the response as a share of the previous one, by the time between the two pokes
  function recovery(host) {
    const D = R.recovery || []; if (!D.length) return;
    const W = widthOf(host, 300), narrow = W < 680, H = narrow ? 340 : 400, m = { l: 56, r: narrow ? 14 : 200, t: 26, b: 58 };
    const s = svg(host, W, H, "Repeat response as a share of the previous one, by time between pokes: " + D.map((d) => `${Math.round(d.pct * 100)}% at ${d.gap} minutes`).join(", "));
    const x = (i) => m.l + ((i + 0.5) * (W - m.l - m.r)) / D.length, y = lin(0, 1.6, H - m.b, m.t);
    [0, 0.5, 1, 1.5].forEach((v) => { hline(s, m.l, W - m.r, y(v), { stroke: v === 1 ? C.ink3 : v ? C.soft : C.rule, "stroke-dasharray": v === 1 ? "3 4" : null }); text(s, m.l - 8, y(v) + 4, Math.round(v * 100) + "%", { "text-anchor": "end", "font-size": 11, fill: C.ink3 }); });
    el("path", { d: D.map((d, i) => (i ? "L" : "M") + x(i).toFixed(1) + " " + y(d.pct).toFixed(1)).join(""), fill: "none", stroke: C.live, "stroke-width": 2, "stroke-linejoin": "round" }, s);
    D.forEach((d, i) => { vline(s, x(i), y(d.hi), y(d.lo), { stroke: C.live, "stroke-width": 1.4 });
      el("path", { d: `M${x(i) - 5} ${px(y(d.hi))}h10M${x(i) - 5} ${px(y(d.lo))}h10`, stroke: C.live, "stroke-width": 1.4 }, s);
      el("circle", { cx: x(i), cy: y(d.pct), r: 5.5, fill: C.live, stroke: C.plate, "stroke-width": 2 }, s);
      text(s, x(i) + 10, y(d.pct) - 9, Math.round(d.pct * 100) + "%", { "font-size": 13, fill: C.ink, "font-weight": 650 });
      text(s, x(i), H - m.b + 20, d.gap.replace("-", " to "), { "text-anchor": "middle", "font-size": 12, fill: C.ink2 });
      const hit = el("rect", { x: x(i) - (W - m.l - m.r) / (2 * D.length), y: m.t, width: (W - m.l - m.r) / D.length, height: H - m.t - m.b, class: "hit", tabindex: 0, "aria-label": `${d.gap} minutes apart: ${Math.round(d.pct * 100)}% of the previous response` }, s);
      hover(hit, `<b>${d.gap.replace("-", " to ")} minutes apart</b>${row("Second response", Math.round(d.pct * 100) + "% of the previous")}${row("90% interval", `${Math.round(d.lo * 100)}% to ${Math.round(d.hi * 100)}%`)}${row("Pairs, worms", `${d.pairs}, ${d.worms}`)}`); });
    text(s, (m.l + W - m.r) / 2, H - 12, "Minutes between the two pokes of the same neuron", { "text-anchor": "middle", "font-size": 11.5, fill: C.ink3 });
    if (!narrow) { text(s, W - m.r + 16, y(1) + 4, "the same as before", { "font-size": 12, fill: C.ink2 }); text(s, W - m.r + 16, y(D[0].pct) + 4, "about half, at first", { "font-size": 12, fill: C.ink, "font-weight": 600 }); }
  }

  // which way driving a cell pushes the brain: the copy fitted at rest against what happened, mouse by mouse
  function push(host) {
    const O = R.optoSign; if (!O) return;
    const order = ["Sst", "Vip"], D = O.mice.filter((d) => order.includes(d.line)).sort((a, b) => order.indexOf(a.line) - order.indexOf(b.line) || a.real - b.real);
    const W = widthOf(host, 300), narrow = W < 680, H = narrow ? 400 : 440, m = { l: 48, r: narrow ? 12 : 210, t: narrow ? 64 : 18, b: 64 };
    const s = svg(host, W, H, `For ${D.length} mice, the share of brain regions a copy fitted at rest predicted would rise when the cells were switched on, and the share that did`);
    const gapG = narrow ? 14 : 30, step = (W - m.l - m.r - gapG) / D.length, y = lin(0, 1, H - m.b, m.t);
    el("rect", { x: m.l, y: y(O.wt[2]), width: W - m.l - m.r, height: y(O.wt[0]) - y(O.wt[2]), fill: C.soft }, s);
    [0, 0.25, 0.5, 0.75, 1].forEach((v) => { hline(s, m.l, W - m.r, y(v), { stroke: v === 0.5 ? C.ink3 : C.soft, "stroke-dasharray": v === 0.5 ? "3 4" : null }); text(s, m.l - 8, y(v) + 4, Math.round(v * 100) + "%", { "text-anchor": "end", "font-size": 11, fill: C.ink3 }); });
    let xi = m.l, g = null, gx0 = 0; const groups = [], r = narrow ? 3.2 : 4.4;
    D.forEach((d) => { if (d.line !== g) { if (g) { groups.push([g, gx0, xi]); xi += gapG; } g = d.line; gx0 = xi; }
      const cx = xi + step / 2;
      vline(s, cx, y(d.w), y(d.real), { stroke: C.rule });
      el("circle", { cx, cy: y(d.w), r: r - 0.4, fill: C.plate, stroke: C.copy, "stroke-width": 1.6 }, s);
      el("circle", { cx, cy: y(d.real), r, fill: C.live, stroke: C.plate, "stroke-width": 1 }, s);
      const hit = el("rect", { x: xi, y: m.t, width: step, height: H - m.t - m.b, class: "hit", tabindex: 0, "aria-label": `${d.line} mouse: copy predicted ${Math.round(d.w * 100)}% rising, ${Math.round(d.real * 100)}% rose` }, s);
      hover(hit, `<b>${d.line} mouse ${d.id.replace("sub-", "")}</b>${row("Copy fitted at rest predicted rising", Math.round(d.w * 100) + "%")}${row("Rose when the cells were driven", Math.round(d.real * 100) + "%")}${row("Light alone, median", Math.round(O.wt[1] * 100) + "%")}`);
      xi += step; });
    groups.push([g, gx0, xi]);
    groups.forEach(([gn, a, b]) => { hline(s, a + 2, b - 2, H - m.b + 12, { stroke: C.ink3 }); const n = D.filter((d) => d.line === gn).length;
      text(s, (a + b) / 2, H - m.b + 30, narrow ? `${gn}, ${n}` : `${gn} cells, ${n} mice`, { "text-anchor": "middle", "font-size": 12.5, fill: C.ink, "font-weight": 650 });
      text(s, (a + b) / 2, H - m.b + 46, gn === "Sst" ? (narrow ? "inhibit neighbours" : "inhibit their neighbours") : (narrow ? "inhibit inhibitors" : "inhibit other inhibitors"), { "text-anchor": "middle", "font-size": 11.5, fill: C.ink3 }); });
    const key = (x0, y0, k, t) => { if (k === "ring") el("circle", { cx: x0 + 5, cy: y0 - 4, r: 4.4, fill: C.plate, stroke: C.copy, "stroke-width": 1.6 }, s);
      else if (k === "dot") el("circle", { cx: x0 + 5, cy: y0 - 4, r: 4.8, fill: C.live }, s); else el("rect", { x: x0, y: y0 - 10, width: 11, height: 11, fill: C.soft, stroke: C.rule }, s);
      t.forEach((u, j) => text(s, x0 + 19, y0 + j * 15, u, { "font-size": 12, fill: j ? C.ink2 : C.ink, "font-weight": j ? 500 : 600 })); };
    if (narrow) { key(0, 14, "ring", ["copy fitted at rest"]); key(W / 2, 14, "dot", ["what happened"]); key(0, 38, "band", ["light alone, mice without the channel"]); }
    else { const lx = W - m.r + 22; key(lx, y(0.92), "ring", ["What the copy fitted", "at rest predicted"]); key(lx, y(O.wt[1]) + 4, "band", ["Light alone, in mice", "without the channel"]); key(lx, y(0.12), "dot", ["What happened when", "the cells were driven"]); }
  }

  // the open test: eight signatures for three systems, each against the band real worms span
  function testSky(host) {
    const Bd = R.testBoard || []; if (!Bd.length) return;
    const pick = [Bd.find((b) => /^Real worms/.test(b.name)), Bd.find((b) => /emulator/i.test(b.name)), Bd.find((b) => /Random tanh/.test(b.name))].filter(Boolean);
    const keys = Object.keys(pick[0].sig), W = widthOf(host, 300), narrow = W < 680, rowH = 34, m = { l: narrow ? 128 : 190, r: 14, t: narrow ? 92 : 46, b: 34 };
    const H = m.t + keys.length * rowH + m.b + 16, s = svg(host, W, H, "Eight signatures of activity for a held-out group of real worms, the worm emulator and a random network, each against the range real worm groups span");
    const cap = 6, x = lin(-cap, cap, m.l, W - m.r);
    el("rect", { x: x(-1), y: m.t - 6, width: x(1) - x(-1), height: keys.length * rowH + 6, fill: C.liveWash }, s);
    vline(s, x(-1), m.t - 6, m.t + keys.length * rowH, { stroke: C.live, "stroke-opacity": .6 }); vline(s, x(1), m.t - 6, m.t + keys.length * rowH, { stroke: C.live, "stroke-opacity": .6 });
    text(s, x(0), m.t - 14, "real worm groups", { "text-anchor": "middle", "font-size": 11.5, fill: C.live, "font-weight": 650 });
    [-6, -3, 0, 3, 6].forEach((v) => text(s, x(v), H - 28, (v > 0 ? "+" : "") + v, { "text-anchor": "middle", "font-size": 11, fill: C.ink3 }));
    if (!narrow) { text(s, m.l, H - 12, "lower", { "font-size": 11, fill: C.ink3 }); text(s, W - m.r, H - 12, "higher", { "text-anchor": "end", "font-size": 11, fill: C.ink3 }); }
    const ST = [{ f: C.live, k: "dot" }, { f: C.ink, k: "sq" }, { f: C.copy, k: "ring" }];
    const mark = (k, cx, cy, i) => { const st = ST[i]; if (st.k === "dot") return el("circle", { cx, cy, r: 5, fill: st.f }, s);
      if (st.k === "sq") return el("rect", { x: cx - 4.3, y: cy - 4.3, width: 8.6, height: 8.6, fill: st.f }, s); return el("circle", { cx, cy, r: 4.6, fill: C.plate, stroke: st.f, "stroke-width": 1.7 }, s); };
    keys.forEach((k, j) => { const yy = m.t + j * rowH + rowH / 2; hline(s, m.l, W - m.r, yy, { stroke: C.soft });
      const ls = narrow ? wrapWords(pick[0].sig[k].label, 16) : [pick[0].sig[k].label];      // on a phone a long name takes two lines; it used to run off the left edge
      ls.forEach((t, q) => text(s, m.l - 12, yy + 4 + (q - (ls.length - 1) / 2) * 13, t, { "text-anchor": "end", "font-size": 12, fill: C.ink2 }));
      pick.forEach((p, i) => { const v = p.sig[k]; if (!v) return; const dv = Math.max(-cap, Math.min(cap, v.d)); mark(k, x(dv), yy + (i - 1) * 7, i);
        const c = el("circle", { cx: x(dv), cy: yy + (i - 1) * 7, r: 9, class: "hit" }, s); hover(c, `<b>${p.name}</b>${row(v.label, (v.d > 0 ? "+" : "") + fmt(v.d, 2))}${row("Inside the real-worm range", v.in ? "yes" : "no")}`); }); });
    const lab = pick.map((p) => p.name.replace(/, group \d/, "").replace(" held out of the reference", " the test never saw").replace(" (minimal recipe)", ""));
    pick.forEach((p, i) => { const lx = narrow ? 8 : m.l + i * ((W - m.l) / 3), ly = narrow ? 14 + i * 22 : 16; mark(null, lx + 5, ly - 4, i); text(s, lx + 16, ly, lab[i], { "font-size": 12, fill: C.ink, "font-weight": 600 }); });
  }
  function testBoard(host) {
    const Bd = R.testBoard || []; if (!Bd.length) return;
    host.innerHTML = `<div class="table-wrap"><table class="data"><thead><tr><th>#</th><th>System</th><th>Distance from real worms</th><th>Signatures inside</th></tr></thead><tbody>${
      Bd.map((b, i) => `<tr><td>${i + 1}</td><td><b>${b.name}</b><br><small>${b.about}</small></td><td>${fmt(b.distance, 2)}</td><td>${b.score} of ${b.outOf}</td></tr>`).join("")}</tbody></table></div>`;
  }

  const FIGS = { push, testSky, testBoard, rulerStrip, scorecard, restPoke, power, signalNoise, fingerprint, echoShape, calibration, mind, gallery, ceiling, law, rulerTruth, permouse, slowFamilies, emulator, gaps, restAvg, recovery };
  window.NematicaCharts = Object.assign({ verdictLegend, name }, FIGS);

  // mount every <div data-chart="..."> and redraw when its width changes
  function draw(n) {
    const fn = FIGS[n.dataset.chart];
    if (!fn) return;
    try { fn(n, { compact: n.hasAttribute("data-compact") }); } catch (e) { console.error(n.dataset.chart, e); n.textContent = "This figure could not be drawn."; }
    // a figure wider than its frame scrolls sideways; on a phone nothing showed that, so its caption now says so
    requestAnimationFrame(() => { const fig = n.closest("figure"), cap = fig && fig.querySelector("figcaption"); if (!cap) return;
      const wide = n.scrollWidth > n.clientWidth + 1, had = cap.querySelector(".swipe-hint");
      if (wide && !had) { const h = document.createElement("span"); h.className = "swipe-hint"; h.textContent = "Swipe sideways to see the whole figure. "; cap.insertBefore(h, cap.firstChild); }
      else if (!wide && had) had.remove();
      if (wide) { n.tabIndex = 0; n.setAttribute("role", "group"); n.setAttribute("aria-label", "Figure, scrolls sideways"); }   // so the keyboard can scroll it too
      else if (n.getAttribute("aria-label") === "Figure, scrolls sideways") { n.removeAttribute("tabindex"); n.removeAttribute("role"); n.removeAttribute("aria-label"); } });
  }
  function mount() {
    const nodes = [...document.querySelectorAll("[data-chart]")];
    const run = () => { nodes.forEach(draw);       // figures change the page's height; land on the linked section again
      const t = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1))); if (t) requestAnimationFrame(() => t.scrollIntoView()); };
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
