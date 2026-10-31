/* NEMATICA figures. Plain SVG, no dependencies, drawn from window.NEMATICA_RESULTS
   (web/data/results.js, exported by scripts/export_site.py from docs/figures). */
(function () {
  "use strict";
  const R = window.NEMATICA_RESULTS || {};
  const NS = "http://www.w3.org/2000/svg";
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const C = {
    ink: css("--ink"), ink2: css("--ink-2"), ink3: css("--ink-3"), rule: css("--rule"), soft: css("--rule-soft"),
    live: css("--live"), liveTint: css("--live-tint"), liveWash: css("--live-wash"),
    copy: css("--copy"), copyTint: css("--copy-tint"), plate: css("--plate"),
  };

  const NAMES = {
    var3_spontaneous: "Linear brain learned from rest",
    var3_all: "Linear brain, rest and pokes",
    var3_stim: "Linear brain learned from pokes",
    var3_stim_relu: "Rectified brain learned from pokes",
    var3_all_relu: "Rectified brain, rest and pokes",
    var3_all_lasso: "Sparse linear brain",
    var10_stim: "Linear brain, longer memory, from pokes",
    var1_spontaneous: "Linear brain, one step of memory",
    var3_spontaneous_diagonal: "No coupling (each neuron alone)",
    creamer2024_fully_connected: "Published model, fully connected",
    creamer2024_connectome_constrained: "Published model, wiring-constrained",
    creamer2024_shuffled_constrained: "Published model, shuffled wiring",
    hybrid_kernels: "Hybrid: poke kernels on rest dynamics",
    hybrid_kernels_shuffled: "Hybrid, kernels on shuffled pairs",
    hybrid_kernels_connectome: "Hybrid, kernels on wired pairs only",
    hybrid_kernels_bgstim: "Hybrid, dynamics learned from pokes",
    hybrid_kernels_obs: "Hybrid + measurement noise",
    hybrid_kernels_obsfit: "Hybrid + fitted measurement noise",
    hybrid_kernels_regimes_obsfit: "Hybrid + noise + calm and active states",
    "hybrid_kernels_regimes_obsfit_smooth0.8": "  + smoothed noise",
    hybrid_kernels_regimes_obsfit_lowrank6: "  + six shared brain-wide modes",
    hybrid_kernels_regimes_obsfit_indiv: "  + each worm its own dynamics",
    hybrid_kernels_quietobsfit: "Hybrid + per-neuron quiet stretches",
    hybrid_kernels_gru64: "Hybrid + learned nonlinear dynamics (GRU)",
    hybrid_kernels_gru64ss: "Hybrid + free-running GRU",
    real: "Real worms (calibration)",
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
  const name = (s) => NAMES[s] || s.replace(/_/g, " ");

  const LEVELS = {
    "L1.distribution": "Activity values", "L1.timescale": "Timescale", "L2.correlation": "Correlations",
    "L2.dimension": "Dimension", "L4.leadlag": "Lead and lag", "L4.dwell": "Bout lengths",
    "C1.pattern": "Echo pattern", "C2.magnitude": "Echo size", "C3.kinetics": "Echo time course",
    "P2.spread": "Echo spread", "P1.complexity": "Echo complexity",
    "M1.complexity": "Complexity", "M2.integration": "Integration", "M3.repertoire": "Repertoire",
  };
  const VERDICT = { inside: "inside", outside: "outside", "too typical": "too typical" };

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
  function svg(host, w, h, label) {
    host.innerHTML = "";
    const s = el("svg", { viewBox: `0 0 ${w} ${h}`, class: "chart", role: "img", "aria-label": label || "" });
    host.appendChild(s);
    return s;
  }
  const lin = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0)) * (r1 - r0);
  const median = (a) => { const b = a.filter((v) => v != null && isFinite(v)).sort((x, y) => x - y);
    if (!b.length) return NaN; const m = b.length >> 1; return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2; };
  const fmt = (v, d = 2) => (v == null || !isFinite(v) ? "n/a" : (+v).toFixed(d).replace("-", "−"));

  // one tooltip for the page
  let tipEl;
  function tip(html, evt) {
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tip"; tipEl.setAttribute("role", "status"); document.body.appendChild(tipEl); }
    if (!html) { tipEl.style.opacity = 0; return; }
    tipEl.innerHTML = html;
    const pad = 14, w = tipEl.offsetWidth, h = tipEl.offsetHeight;
    let x = evt.clientX + pad, y = evt.clientY + pad;
    if (x + w > innerWidth - 8) x = evt.clientX - w - pad;
    if (y + h > innerHeight - 8) y = evt.clientY - h - pad;
    tipEl.style.left = x + "px"; tipEl.style.top = y + "px"; tipEl.style.opacity = 1;
  }
  function hover(node, html) {
    node.addEventListener("pointermove", (e) => tip(typeof html === "function" ? html() : html, e));
    node.addEventListener("pointerleave", () => tip(null));
    node.addEventListener("focus", () => { const r = node.getBoundingClientRect(); tip(typeof html === "function" ? html() : html, { clientX: r.right, clientY: r.top }); });
    node.addEventListener("blur", () => tip(null));
  }

  // verdict glyph: filled = inside, open = outside, half = too typical
  function glyph(g, x, y, verdict, r = 4.6) {
    if (verdict === "inside") return el("circle", { cx: x, cy: y, r, fill: C.ink }, g);
    if (verdict === "too typical") {
      const grp = el("g", {}, g);
      el("circle", { cx: x, cy: y, r: r - 0.7, fill: C.plate, stroke: C.ink, "stroke-width": 1.4 }, grp);
      el("path", { d: `M${x},${y - r + 0.7} A${r - 0.7},${r - 0.7} 0 0 0 ${x},${y + r - 0.7} Z`, fill: C.ink }, grp);
      return grp;
    }
    if (verdict === "outside") return el("circle", { cx: x, cy: y, r: r - 0.7, fill: C.plate, stroke: C.ink, "stroke-width": 1.4 }, g);
    return el("circle", { cx: x, cy: y, r: 1.5, fill: C.ink3 }, g);
  }

  // ------------------------------------------------------------- Figure: scorecard
  const GROUPS = [
    { label: "Watching: ongoing activity", metrics: ["L1.distribution", "L1.timescale", "L2.correlation", "L2.dimension", "L4.leadlag", "L4.dwell"] },
    { label: "Poking: the echo", metrics: ["C1.pattern", "C2.magnitude", "C3.kinetics", "P2.spread"] },
    { label: "Complexity", metrics: ["P1.complexity"] },
  ];
  const SCORE_ROWS = [
    "var3_spontaneous", "var3_stim", "var3_all_relu", "var3_all_lasso", "var10_stim", "creamer2024_fully_connected",
    "hybrid_kernels", "hybrid_kernels_shuffled", "hybrid_kernels_connectome", "hybrid_kernels_obsfit",
    "hybrid_kernels_regimes_obsfit", "hybrid_kernels_regimes_obsfit_smooth0.8", "hybrid_kernels_regimes_obsfit_lowrank6",
    "hybrid_kernels_regimes_obsfit_indiv", "hybrid_kernels_quietobsfit", "hybrid_kernels_gru64", "hybrid_kernels_gru64ss",
  ];
  function scorecard(host, opts) {
    opts = opts || {};
    const rows = opts.rows || SCORE_ROWS;
    const data = {};
    (R.scorecard || []).forEach((r) => { (data[r.system + "|" + r.metric] = data[r.system + "|" + r.metric] || [])[r.fold] = r; });
    const labW = 300, colW = 74, gapG = 22, rowH = 30, top = 70;
    const cols = [];
    let x = labW;
    GROUPS.forEach((g, gi) => { g.x0 = x; g.metrics.forEach((m) => { cols.push({ m, x: x + colW / 2, g: gi }); x += colW; }); g.x1 = x; x += gapG; });
    const W = x - gapG + 8, H = top + rows.length * rowH + 8;
    const s = svg(host, W, H, "Scorecard: each artificial brain against real worms on eleven tests, in three groups of held-out worms");
    s.style.minWidth = "820px";
    GROUPS.forEach((g) => {
      el("line", { x1: g.x0 + 4, x2: g.x1 - 4, y1: 22, y2: 22, stroke: C.ink, "stroke-width": 1 }, s);
      text(s, g.x0 + 4, 14, g.label, { class: "label-strong", "font-size": 12.5 });
    });
    cols.forEach((c) => {
      const words = LEVELS[c.m].split(" ");
      const l1 = words.length > 1 ? words.slice(0, Math.ceil(words.length / 2)).join(" ") : words[0];
      const l2 = words.length > 1 ? words.slice(Math.ceil(words.length / 2)).join(" ") : "";
      text(s, c.x, 42, l1, { "text-anchor": "middle", "font-size": 11.5 });
      if (l2) text(s, c.x, 56, l2, { "text-anchor": "middle", "font-size": 11.5 });
    });
    rows.forEach((sys, i) => {
      const y = top + i * rowH + rowH / 2;
      const isPass = sys === "hybrid_kernels_regimes_obsfit";
      if (isPass) el("rect", { x: 0, y: y - rowH / 2 + 2, width: W, height: rowH - 4, rx: 4, fill: C.liveWash }, s);
      else if (i % 2 === 0) el("rect", { x: 0, y: y - rowH / 2 + 2, width: W, height: rowH - 4, rx: 4, fill: "#f8f9f9" }, s);
      const label = name(sys);
      text(s, 10, y + 4, label.trim(), { "font-size": 13, fill: isPass ? C.ink : C.ink2, "font-weight": isPass ? 600 : 400, dx: label.startsWith("  ") ? 14 : 0 });
      cols.forEach((c) => {
        const cell = data[sys + "|" + c.m] || [];
        const g = el("g", { tabindex: 0, "aria-label": `${name(sys)}, ${LEVELS[c.m]}: ${[0, 1, 2].map((f) => (cell[f] ? cell[f].verdict : "not run")).join(", ")}` }, s);
        el("rect", { x: c.x - colW / 2 + 2, y: y - rowH / 2 + 2, width: colW - 4, height: rowH - 4, class: "hit" }, g);
        const allIn = [0, 1, 2].every((f) => cell[f] && cell[f].verdict === "inside");
        if (allIn) el("rect", { x: c.x - colW / 2 + 5, y: y - 10, width: colW - 10, height: 20, rx: 10, fill: C.liveTint }, g);
        [0, 1, 2].forEach((f) => glyph(g, c.x + (f - 1) * 13, y, cell[f] ? cell[f].verdict : null));
        hover(g, () => `<b>${name(sys).trim()}</b><br><span class="dim">${LEVELS[c.m]}</span>` +
          [0, 1, 2].map((f) => cell[f] ? `<div class="row"><span>Group ${f + 1}: ${cell[f].verdict}</span><span class="dim">${fmt(cell[f].median)} vs real ${fmt(cell[f].bio)}</span></div>` : `<div class="row"><span>Group ${f + 1}</span><span class="dim">not run</span></div>`).join(""));
      });
    });
  }

  // ------------------------------------------------------------- Figure: watching vs poking
  function restPoke(host, opts) {
    opts = opts || {};
    const pts = (R.restPoke || []).filter((d) => d.poke != null);
    const small = !!opts.compact;
    const W = small ? 360 : 860, H = small ? 270 : 470;
    const m = small ? { l: 34, r: 10, t: 18, b: 34 } : { l: 64, r: 200, t: 24, b: 56 };
    const s = svg(host, W, H, "Scatter: rest tests passed against agreement of echoes with real worms, one dot per brain and group");
    const x = lin(0.5, 6.5, m.l, W - m.r), y = lin(-0.02, 0.14, H - m.b, m.t);
    const gGrid = el("g", { class: "grid" }, s);
    [0, 0.04, 0.08, 0.12].forEach((v) => { el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v) }, gGrid); text(s, m.l - 8, y(v) + 4, fmt(v, 2), { "text-anchor": "end", "font-size": small ? 10 : 12 }); });
    for (let k = 1; k <= 6; k++) text(s, x(k), H - m.b + (small ? 16 : 20), String(k), { "text-anchor": "middle", "font-size": small ? 10 : 12 });
    // real worms agree with each other at about 1 - bio median
    const bio = 1 - median((R.scorecard || []).filter((r) => r.metric === "C1.pattern").map((r) => r.bio));
    el("rect", { x: m.l, x2: 0, y: y(bio + 0.015), width: W - m.r - m.l, height: y(bio - 0.015) - y(bio + 0.015), fill: C.liveTint }, s);
    el("line", { x1: m.l, x2: W - m.r, y1: y(bio), y2: y(bio), stroke: C.live, "stroke-width": 1.5 }, s);
    el("line", { x1: m.l, x2: W - m.r, y1: y(0), y2: y(0), stroke: C.rule }, s);
    if (small) {
      text(s, (m.l + W - m.r) / 2, H - 2, "rest tests passed", { "text-anchor": "middle", "font-size": 10 });
      text(s, m.l + 4, m.t - 2, "echo agreement", { "font-size": 10 });
    }
    if (!small) {
      text(s, W - m.r + 12, y(bio) - 4, "Two real worms agree", { fill: C.live, "font-weight": 600 });
      text(s, W - m.r + 12, y(bio) + 12, `at about ${fmt(bio, 1)}`, { fill: C.live });
      text(s, W - m.r + 12, y(0) + 4, "No agreement");
      text(s, (m.l + W - m.r) / 2, H - 14, "Rest tests passed (of 6): how alive the brain looks when watched", { "text-anchor": "middle", fill: C.ink2 });
      const yl = text(s, 0, 0, "Echo agreement with real worms (correlation)", { "text-anchor": "middle", fill: C.ink2, transform: `translate(16 ${(m.t + H - m.b) / 2}) rotate(-90)` });
    }
    // deterministic swarm per column
    const byCol = {};
    pts.forEach((d) => (byCol[d.rest] = byCol[d.rest] || []).push(d));
    Object.keys(byCol).forEach((k) => {
      const col = byCol[k].sort((a, b) => a.poke - b.poke);
      const placed = [];
      col.forEach((d) => {
        const cy = y(1 - d.poke);
        let off = 0, step = small ? 5 : 8, tries = 0;
        const r = small ? 2.6 : 4.4;
        while (placed.some((p) => Math.hypot(p.x - (x(+k) + off), p.y - cy) < 2 * r + 0.6) && tries < 40) { tries++; off = (tries % 2 ? 1 : -1) * Math.ceil(tries / 2) * step * 0.55; }
        placed.push({ x: x(+k) + off, y: cy });
        const hybrid = d.brain.startsWith("hybrid");
        const c = el("circle", { cx: x(+k) + off, cy, r, fill: hybrid ? C.copy : C.plate, stroke: C.copy, "stroke-width": 1.4, tabindex: small ? -1 : 0,
          "aria-label": `${name(d.brain)}, group ${d.fold + 1}: rest ${d.rest} of 6, echo agreement ${fmt(1 - d.poke)}` }, s);
        if (!small) hover(c, `<b>${name(d.brain).trim()}</b><br><span class="dim">Held-out group ${d.fold + 1}</span><div class="row"><span>Rest tests passed</span><span>${d.rest} of 6</span></div><div class="row"><span>Echo agreement</span><span>${fmt(1 - d.poke)}</span></div><div class="row"><span>Echo pattern</span><span>${d.verdict}</span></div>`);
      });
    });
    if (!small) {
      const lg = el("g", {}, s);
      const ly = y(0.06);
      el("circle", { cx: W - m.r + 18, cy: ly, r: 4.4, fill: C.plate, stroke: C.copy, "stroke-width": 1.4 }, lg);
      text(lg, W - m.r + 30, ly + 4, "Learned from activity");
      el("circle", { cx: W - m.r + 18, cy: ly + 24, r: 4.4, fill: C.copy, stroke: C.copy }, lg);
      text(lg, W - m.r + 30, ly + 28, "With causal links");
      text(lg, W - m.r + 30, ly + 43, "learned from pokes");
    }
  }

  // ------------------------------------------------------------- Figure: power of the poke test
  function power(host) {
    const P = R.power; if (!P) return;
    const W = 860, H = 450, m = { l: 84, r: 24, t: 30, b: 150 };
    const s = svg(host, W, H, "How much true cause and effect a brain needs before the poke test calls it inside");
    const x = lin(0, 1, m.l, W - m.r), y = lin(0, 0.3, H - m.b, m.t);
    const g = el("g", { class: "grid" }, s);
    [0, 0.1, 0.2, 0.3].forEach((v) => { el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v) }, g); text(s, m.l - 8, y(v) + 4, fmt(v, 1), { "text-anchor": "end" }); });
    [0, 0.2, 0.4, 0.6, 0.8, 1].forEach((v) => text(s, x(v), H - m.b + 18, fmt(v, 1), { "text-anchor": "middle" }));
    text(s, (m.l + W - m.r) / 2, H - m.b + 40, "How much of the true average echo the brain carries (its correlation with it)", { "text-anchor": "middle", fill: C.ink2 });
    text(s, 0, 0, "Agreement with real worms", { "text-anchor": "middle", fill: C.ink2, transform: `translate(16 ${(m.t + H - m.b) / 2}) rotate(-90)` });
    // real-worm agreement band (median over pools)
    const bio = median(Object.values(P.pools).map((p) => 1 - p.bio));
    el("line", { x1: m.l, x2: W - m.r, y1: y(bio), y2: y(bio), stroke: C.live, "stroke-width": 1.5, "stroke-dasharray": "5 4" }, s);
    text(s, W - m.r, y(bio) + 18, `Two real worms agree at ${fmt(bio, 2)}`, { fill: C.live, "font-weight": 600, "text-anchor": "end" });
    // lines per pool
    const pools = [0, 1, 2];
    pools.forEach((f) => {
      const pts = P.points.filter((p) => p.fold === f).sort((a, b) => a.f - b.f);
      el("path", { d: pts.map((p, i) => (i ? "L" : "M") + x(p.f) + "," + y(1 - p.d)).join(""), fill: "none", stroke: C.ink, "stroke-width": 1.4, opacity: 0.35 + 0.25 * f }, s);
    });
    // verdict strips
    const step = 0.05, cw = x(step) - x(0);
    pools.forEach((f) => {
      const yy = H - m.b + 62 + f * 22;
      text(s, x(0) - cw / 2 - 6, yy + 12, `Group ${f + 1}`, { "text-anchor": "end", "font-size": 11.5 });
      P.points.filter((p) => p.fold === f).forEach((p) => {
        const v = p.verdicts.filter((q) => q === "inside").length >= 2 ? "inside" : p.verdicts.filter((q) => q === "outside").length >= 2 ? "outside" : "too typical";
        const r = el("rect", { x: x(p.f) - cw / 2 + 1, y: yy, width: cw - 2, height: 16, rx: 2,
          fill: v === "inside" ? C.live : v === "outside" ? C.plate : C.soft, stroke: v === "outside" ? C.rule : "none" }, s);
        hover(r, `<b>Group ${f + 1}, correlation ${fmt(p.f)}</b><br>${p.verdicts.join(", ")}<br><span class="dim">agreement with real worms ${fmt(1 - p.d)}</span>`);
      });
    });
    const ly = H - m.b + 62 + 3 * 22 + 6;
    [["inside", C.live, "none", "Inside: as real as a real worm"], ["outside", C.plate, C.rule, "Outside: too little cause and effect"], ["too typical", C.soft, "none", "Too typical: more stereotyped than any worm"]].forEach((k, i) => {
      const xx = m.l + i * 250;
      el("rect", { x: xx, y: ly, width: 14, height: 12, rx: 2, fill: k[1], stroke: k[2] }, s);
      text(s, xx + 20, ly + 10, k[3], { "font-size": 11.5 });
    });
    // where brains sit: one label row each, in the empty upper-left of the plot
    const marks = (R.signalNoise || []).filter((d) => d.avg10 != null)
      .map((d) => ({ v: d.avg10, n: d.system.startsWith("real") ? "One real worm (against the average)" : name(d.system), real: d.system.startsWith("real") }))
      .sort((a, b) => a.v - b.v);
    marks.forEach((d, i) => {
      const xx = x(d.v), yy = m.t + 4 + i * 17;
      el("line", { x1: xx, x2: xx, y1: yy + 4, y2: H - m.b, stroke: d.real ? C.live : C.copy, "stroke-width": 1, opacity: 0.45 }, s);
      el("circle", { cx: xx, cy: H - m.b, r: 3.5, fill: d.real ? C.live : C.copy }, s);
      el("circle", { cx: xx, cy: yy, r: 2.5, fill: d.real ? C.live : C.copy }, s);
      text(s, xx + 7, yy + 4, `${d.n}  ${fmt(d.v)}`, { "font-size": 11.5, fill: d.real ? C.live : C.ink2 });
    });
  }

  // ------------------------------------------------------------- Figure: signal or noise
  function signalNoise(host) {
    const D = (R.signalNoise || []).filter((d) => !d.system.startsWith("real"));
    const realV = ((R.signalNoise || []).find((d) => d.system.startsWith("real")) || {}).avg10;
    const W = 860, rowH = 44, m = { l: 300, r: 40, t: 40, b: 46 }, H = m.t + D.length * rowH + m.b;
    const s = svg(host, W, H, "Each model's echo, single run and averaged over ten runs, against one real worm");
    const x = lin(0, 0.3, m.l, W - m.r);
    const g = el("g", { class: "grid" }, s);
    [0, 0.1, 0.2, 0.3].forEach((v) => { el("line", { x1: x(v), x2: x(v), y1: m.t - 8, y2: H - m.b }, g); text(s, x(v), H - m.b + 18, fmt(v, 1), { "text-anchor": "middle" }); });
    text(s, (m.l + W - m.r) / 2, H - 8, "Correlation of the echo with the atlas average", { "text-anchor": "middle", fill: C.ink2 });
    el("rect", { x: x(realV) - 1, y: m.t - 14, width: 2, height: H - m.b - m.t + 14, fill: C.live }, s);
    text(s, x(realV) + 6, m.t - 16, `One real worm ${fmt(realV)}`, { fill: C.live, "font-weight": 600 });
    D.forEach((d, i) => {
      const yy = m.t + i * rowH + rowH / 2;
      text(s, m.l - 14, yy + 4, name(d.system), { "text-anchor": "end", "font-size": 13, fill: C.ink });
      el("line", { x1: x(d.single), x2: x(d.avg10), y1: yy, y2: yy, stroke: C.copy, "stroke-width": 2 }, s);
      el("circle", { cx: x(d.single), cy: yy, r: 5, fill: C.plate, stroke: C.copy, "stroke-width": 1.6 }, s);
      el("circle", { cx: x(d.avg10), cy: yy, r: 5, fill: C.copy }, s);
      const hit = el("rect", { x: m.l, y: yy - rowH / 2, width: W - m.l - m.r, height: rowH, class: "hit" }, s);
      hover(hit, `<b>${name(d.system)}</b><div class="row"><span>One simulated worm</span><span>${fmt(d.single)}</span></div><div class="row"><span>Ten repeats averaged</span><span>${fmt(d.avg10)}</span></div><div class="row"><span>One real worm</span><span>${fmt(realV)}</span></div>`);
    });
    const lg = el("g", {}, s);
    el("circle", { cx: m.l, cy: 14, r: 5, fill: C.plate, stroke: C.copy, "stroke-width": 1.6 }, lg); text(lg, m.l + 10, 18, "One simulated worm");
    el("circle", { cx: m.l + 150, cy: 14, r: 5, fill: C.copy }, lg); text(lg, m.l + 160, 18, "Ten repeats averaged");
  }

  // ------------------------------------------------------------- Figure: causal fingerprints
  // Each worm: distance between the two halves of its own pokes (green) against its distance to
  // other worms (open). Sorted by the gap.
  function fingerprint(host, opts) {
    opts = opts || {};
    const small = !!opts.compact;
    const rows = (R.fingerprintRows || []).filter((r) => r.fp_within != null && r.fp_between != null)
      .sort((a, b) => (a.fp_within - a.fp_between) - (b.fp_within - b.fp_between));
    const n = rows.length; if (!n) return;
    const W = small ? 360 : 860, m = small ? { l: 10, r: 10, t: 22, b: 30 } : { l: 64, r: 230, t: 30, b: 56 };
    const rh = small ? 4.4 : 9, H = m.t + n * rh + m.b;
    const s = svg(host, W, H, "For each worm, how alike the two halves of its own pokes are, against other worms");
    const x = lin(0.45, 1.25, m.l, W - m.r);
    const g = el("g", { class: "grid" }, s);
    [0.5, 0.7, 0.9, 1.1].forEach((v) => { el("line", { x1: x(v), x2: x(v), y1: m.t - 6, y2: H - m.b + 4 }, g); text(s, x(v), H - m.b + (small ? 14 : 20), fmt(v, 1), { "text-anchor": "middle", "font-size": small ? 10 : 12 }); });
    let closer = 0;
    rows.forEach((r, i) => {
      const yy = m.t + i * rh + rh / 2;
      const own = r.fp_within < r.fp_between; if (own) closer++;
      el("line", { x1: x(r.fp_within), x2: x(r.fp_between), y1: yy, y2: yy, stroke: own ? C.live : C.copy, "stroke-width": small ? 1 : 1.4, opacity: 0.55 }, s);
      el("circle", { cx: x(r.fp_between), cy: yy, r: small ? 1.8 : 3.2, fill: C.plate, stroke: C.ink3, "stroke-width": 1.1 }, s);
      el("circle", { cx: x(r.fp_within), cy: yy, r: small ? 2 : 3.4, fill: C.live }, s);
      if (!small) {
        const hit = el("rect", { x: m.l, y: yy - rh / 2, width: W - m.l - m.r, height: rh, class: "hit" }, s);
        hover(hit, `<b>Worm ${r.worm}</b><div class="row"><span>Its two halves</span><span>${fmt(r.fp_within, 3)}</span></div><div class="row"><span>Against other worms</span><span>${fmt(r.fp_between, 3)}</span></div><span class="dim">Lower is more alike</span>`);
      }
    });
    if (small) {
      text(s, m.l, 12, `${closer} of ${n} worms closer to themselves`, { "font-size": 10.5, fill: C.ink });
      text(s, (m.l + W - m.r) / 2, H - 2, "echo distance", { "text-anchor": "middle", "font-size": 10 });
    } else {
      text(s, (m.l + W - m.r) / 2, H - 14, "Echo distance (lower is more alike)", { "text-anchor": "middle", fill: C.ink2 });
      text(s, 0, 0, "Worms, sorted by the gap", { "text-anchor": "middle", fill: C.ink2, transform: `translate(${m.l - 24} ${m.t + (n * rh) / 2}) rotate(-90)` });
      const lx = W - m.r + 24;
      el("circle", { cx: lx, cy: m.t + 6, r: 4, fill: C.live }, s); text(s, lx + 12, m.t + 10, "The worm against itself", { fill: C.ink });
      text(s, lx + 12, m.t + 26, "(two halves of its pokes)");
      el("circle", { cx: lx, cy: m.t + 50, r: 3.6, fill: C.plate, stroke: C.ink3, "stroke-width": 1.1 }, s); text(s, lx + 12, m.t + 54, "The same worm against", { fill: C.ink });
      text(s, lx + 12, m.t + 70, "other worms (median)");
      text(s, lx, m.t + 110, `${closer} of ${n} worms`, { class: "label-strong", "font-size": 22 });
      text(s, lx, m.t + 130, "are closer to themselves", { fill: C.ink2 });
      text(s, lx, m.t + 148, "than to other worms", { fill: C.ink2 });
    }
  }

  // ------------------------------------------------------------- Figure: who stays out of the echo
  function echoShape(host, opts) {
    const small = opts && opts.compact;
    const D = [
      { k: "Neuron classes that respond at all within 30 s", real: 66, var: 93, hyb: 95, u: "%" },
      { k: "Moments where the set of responders changes", real: 85, var: 97, hyb: 98, u: "%" },
    ];
    const W = small ? 360 : 860, m = small ? { l: 8, r: 8, t: 6, b: 6 } : { l: 330, r: 60, t: 10, b: 36 };
    const bh = small ? 13 : 16, gap = small ? 4 : 6, blockH = 3 * (bh + gap) + (small ? 22 : 26);
    const H = m.t + D.length * blockH + m.b;
    const s = svg(host, W, H, "Share of neuron classes that respond after a poke, real worms against models");
    const x = lin(0, 100, small ? m.l : m.l, W - m.r);
    D.forEach((d, i) => {
      const y0 = m.t + i * blockH;
      if (!small) text(s, m.l - 14, y0 + 20, d.k, { "text-anchor": "end", fill: C.ink, "font-size": 13 });
      else text(s, m.l, y0 + 11, d.k, { fill: C.ink, "font-size": 10.5 });
      const off = small ? 16 : 6;
      [["Real worms", d.real, C.live], ["Linear brain", d.var, C.copy], ["Hybrid that passes the poke test", d.hyb, C.copy]].forEach((b, j) => {
        const yy = y0 + off + j * (bh + gap);
        el("rect", { x: x(0), y: yy, width: x(b[1]) - x(0), height: bh, rx: 2, fill: b[2], opacity: j === 2 ? 0.55 : 1 }, s);
        text(s, x(b[1]) + 6, yy + bh - 3, `${b[1]}${d.u}`, { "font-size": small ? 10 : 12, fill: C.ink });
        if (!small) text(s, x(0) + 8, yy + bh - 4, b[0], { "font-size": 11.5, fill: "#fff", "font-weight": 600 });
      });
    });
  }

  // ------------------------------------------------------------- Figure: verdict grid for calibrations / mind
  function verdictGrid(host, rowsIn, metrics, opts) {
    opts = opts || {};
    const datasets = opts.datasets || [null];
    const labW = 270, colW = 84, rowH = 30, top = datasets.length > 1 ? 72 : 48;
    const W = labW + datasets.length * metrics.length * colW + (datasets.length - 1) * 18 + 8;
    const sys = opts.order || [...new Set(rowsIn.map((r) => r.system))];
    const H = top + sys.length * rowH + 8;
    const s = svg(host, W, H, opts.label || "Verdict grid");
    s.style.minWidth = Math.min(W, 640) + "px";
    s.style.maxWidth = W + "px";
    datasets.forEach((ds, di) => {
      const x0 = labW + di * (metrics.length * colW + 18);
      if (ds) { el("line", { x1: x0 + 4, x2: x0 + metrics.length * colW - 4, y1: 22, y2: 22, stroke: C.ink }, s); text(s, x0 + 4, 14, opts.dsLabel ? opts.dsLabel(ds) : ds, { class: "label-strong", "font-size": 12.5 }); }
      metrics.forEach((mt, mi) => {
        const words = (LEVELS[mt] || mt).split(" ");
        const cut = Math.ceil(words.length / 2);
        if (words.length > 1) { text(s, x0 + mi * colW + colW / 2, top - 24, words.slice(0, cut).join(" "), { "text-anchor": "middle", "font-size": 11.5 }); text(s, x0 + mi * colW + colW / 2, top - 10, words.slice(cut).join(" "), { "text-anchor": "middle", "font-size": 11.5 }); }
        else text(s, x0 + mi * colW + colW / 2, top - 10, words[0], { "text-anchor": "middle", "font-size": 11.5 });
      });
      sys.forEach((sy, i) => {
        const y = top + i * rowH + rowH / 2;
        metrics.forEach((mt, mi) => {
          const cx = x0 + mi * colW + colW / 2;
          const cells = rowsIn.filter((r) => r.system === sy && r.metric === mt && (!ds || r.dataset === ds)).sort((a, b) => a.fold - b.fold);
          const g = el("g", { tabindex: 0 }, s);
          el("rect", { x: cx - colW / 2 + 2, y: y - rowH / 2 + 2, width: colW - 4, height: rowH - 4, class: "hit" }, g);
          const exp0 = cells[0] && cells[0].expected;
          const exp = ["inside", "outside", "too typical"].includes(exp0) ? exp0 : null;
          if (exp) el("rect", { x: cx - 26, y: y - 10, width: 52, height: 20, rx: 10, fill: "none", stroke: cells.every((c) => c.verdict === exp) ? C.live : C.copy, "stroke-width": 1.2, "stroke-dasharray": cells.every((c) => c.verdict === exp) ? "" : "3 2" }, g);
          cells.forEach((c, k) => glyph(g, cx + (k - 1) * 13, y, c.verdict));
          hover(g, () => `<b>${name(sy)}</b><br><span class="dim">${LEVELS[mt] || mt}${ds ? ", " + (opts.dsLabel ? opts.dsLabel(ds) : ds) : ""}</span>` + cells.map((c) => `<div class="row"><span>Group ${c.fold + 1}</span><span>${c.verdict}</span></div>`).join("") + (exp ? `<span class="dim">Designed outcome: ${exp}</span>` : ""));
        });
        if (di === 0) text(s, 10, y + 4, name(sy), { "font-size": 13, fill: C.ink2 });
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
  function rulerStrip(host, opts) {
    const metric = (opts && opts.metric) || host.dataset.metric || "C1.pattern";
    const fold = +((opts && opts.fold) || host.dataset.fold || 0);
    const rows = (R.scorecard || []).filter((r) => r.metric === metric && r.fold === fold && r.median != null && SCORE_ROWS.includes(r.system));
    if (!rows.length) return;
    const b = rows[0];
    const W = 860, m = { l: 24, r: 24, t: 70, b: 52 }, rh = 22, H = m.t + rows.length * 0 + 150 + m.b;
    const s = svg(host, W, H, "Where every brain lands on one test, against the spread of distances between real worms");
    const vals = rows.map((r) => r.median).concat([b.p05, b.p95]);
    const lo = Math.min(...vals) - 0.03, hi = Math.max(...vals) + 0.03;
    const x = lin(lo, hi, m.l, W - m.r);
    const y0 = m.t + 40;
    el("rect", { x: x(b.p05), y: y0 - 34, width: x(b.p95) - x(b.p05), height: 68, rx: 4, fill: C.liveTint }, s);
    el("line", { x1: x(b.bio), x2: x(b.bio), y1: y0 - 40, y2: y0 + 40, stroke: C.live, "stroke-width": 2 }, s);
    text(s, x(b.bio), y0 - 48, "median distance between two real worms", { "text-anchor": "middle", fill: C.live, "font-weight": 600 });
    text(s, x(b.p05) + 6, y0 + 52, "5th percentile", { "font-size": 11.5, fill: C.live });
    text(s, x(b.p95) - 6, y0 + 52, "95th percentile", { "font-size": 11.5, fill: C.live, "text-anchor": "end" });
    el("line", { x1: m.l, x2: W - m.r, y1: y0, y2: y0, stroke: C.rule }, s);
    // stack markers that collide
    const sorted = rows.slice().sort((a, c) => a.median - c.median);
    const placed = [];
    sorted.forEach((r) => {
      const cx = x(r.median);
      let k = 0; while (placed.some((p) => Math.abs(p.x - cx) < 10 && p.k === k)) k++;
      placed.push({ x: cx, k });
      const cy = y0 + (k % 2 ? 1 : -1) * Math.ceil(k / 2) * 11;
      const g = el("g", { tabindex: 0 }, s);
      glyph(g, cx, cy, r.verdict, 5);
      el("circle", { cx, cy, r: 9, class: "hit" }, g);
      hover(g, `<b>${name(r.system).trim()}</b><div class="row"><span>Median distance</span><span>${fmt(r.median, 3)}</span></div><div class="row"><span>Verdict</span><span>${r.verdict}</span></div>`);
    });
    for (let v = Math.ceil(lo * 20) / 20; v <= hi; v += 0.05) text(s, x(v), H - m.b + 8, fmt(v, 2), { "text-anchor": "middle" });
    text(s, (m.l + W - m.r) / 2, H - 14, `${LEVELS[metric]}: distance from real worms (group ${fold + 1})`, { "text-anchor": "middle", fill: C.ink2 });
  }

  // ------------------------------------------------------------- legend for verdict glyphs
  function verdictLegend(host) {
    host.innerHTML = '<span class="k"><span class="sw full"></span>Inside: as real as a real worm</span>' +
      '<span class="k"><span class="sw open"></span>Outside</span>' +
      '<span class="k"><span class="sw half"></span>Too typical: more average than any real worm</span>' +
      (host.dataset.legend === "noband" ? "" : '<span class="k"><span class="sw band"></span>Inside in all three groups</span>');
  }

  window.NematicaCharts = { rulerStrip, scorecard, restPoke, power, signalNoise, fingerprint, echoShape, calibration, mind, verdictLegend, name };

  // auto-mount: <div data-chart="restPoke" data-compact>
  function mount() {
    document.querySelectorAll("[data-chart]").forEach((n) => {
      const fn = window.NematicaCharts[n.dataset.chart];
      if (fn) try { fn(n, { compact: n.hasAttribute("data-compact") }); } catch (e) { console.error(n.dataset.chart, e); n.textContent = "This figure could not be drawn."; }
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
