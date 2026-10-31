/* Echo explorer: switch on one neuron class and watch the average echo spread through the head,
   in real worms and in two artificial brains run on the same worms with the same pokes.
   Drawn at the page's own pixel size; relaid out when the width changes.
   Data: window.NEMATICA_ECHO (web/data/echo.js, local only; scripts/export_site.py --local). */
(function () {
  "use strict";
  const host = document.getElementById("echo");
  if (!host) return;
  const E = window.NEMATICA_ECHO;
  const NS = "http://www.w3.org/2000/svg";
  const mapsEl = host.querySelector(".echo-maps");
  if (!E) {
    mapsEl.innerHTML = '<div class="scope-empty"><div>The echo explorer draws from the local copy of the atlas.<br>Run <code>python scripts/export_site.py --local</code> and reload.</div></div>';
    return;
  }
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const S = E.stims.length, Rn = E.resp.length, T = E.nt;
  const decode = (b64) => { const s = atob(b64), a = new Int8Array(s.length); for (let i = 0; i < s.length; i++) a[i] = (s.charCodeAt(i) << 24) >> 24; return a; };
  const UP_REAL = "#3dd69b", UP_COPY = "#f062b4", DOWN = "#7aa7ff";
  const SETS = [
    { key: "real", label: E.labels.real, note: "the truth for this held-out group", up: UP_REAL, cls: "live" },
    { key: "hybrid_kernels_regimes_obsfit", label: "Hybrid brain", note: "passes the poke test", up: UP_COPY, cls: "copy" },
    { key: "var3_spontaneous", label: "Linear brain", note: "learned from watching only", up: UP_COPY, cls: "copy" },
  ].map((s) => Object.assign(s, { data: decode(E.sets[s.key]) }));
  const raw = (set, si, ri, t) => set.data[(si * Rn + ri) * T + t];
  const val = (set, si, ri, t) => { const q = raw(set, si, ri, t); return q === -128 ? NaN : (q / 127) * E.scale; };
  const ON = 0.35;                      // a class counts as responding above this many standard deviations
  const shared = (si, r) => raw(SETS[1], si, r, 0) !== -128 && raw(SETS[0], si, r, 0) !== -128;

  function corr(a, b) {
    const n = a.length; if (n < 8) return NaN;
    let ma = 0, mb = 0; for (let i = 0; i < n; i++) { ma += a[i]; mb += b[i]; } ma /= n; mb /= n;
    let sab = 0, saa = 0, sbb = 0; for (let i = 0; i < n; i++) { sab += (a[i] - ma) * (b[i] - mb); saa += (a[i] - ma) ** 2; sbb += (b[i] - mb) ** 2; }
    return sab / Math.sqrt(saa * sbb);
  }
  const mean15 = (set, si, r) => { let m = 0, n = 0; for (let q = 0; q <= 15 && q < T; q++) { const v = val(set, si, r, q); if (isFinite(v)) { m += v; n++; } } return n ? m / n : NaN; };
  function agreementFor(set, sis) {
    const a = [], b = [];
    sis.forEach((si) => { for (let r = 0; r < Rn; r++) if (shared(si, r)) { const x = mean15(set, si, r), y = mean15(SETS[0], si, r); if (isFinite(x) && isFinite(y)) { a.push(x); b.push(y); } } });
    return corr(a, b);
  }
  const allStims = E.stims.map((_, i) => i);
  const pooled = SETS.map((s, k) => (k ? agreementFor(s, allStims) : 1));

  // ---------------------------------------------------------------- state and controls
  let si = Math.max(0, E.stims.indexOf("ASH")), t = 0, playing = false, last = 0, hoverC = null, agree = [];
  const scrub = host.querySelector(".echo-scrub"), timeOut = host.querySelector(".echo-time"), playBtn = host.querySelector(".echo-play");
  const chips = host.querySelector(".echo-chips");
  E.stims.forEach((c, i) => {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = c; b.className = "echo-chip"; b.setAttribute("aria-pressed", String(i === si));
    b.addEventListener("click", () => select(c));
    chips.appendChild(b);
  });
  scrub.max = String(T - 1);

  function svgEl(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  // ---------------------------------------------------------------- layout at the current width
  let views = [], nodes = [], byClass = {}, W = 0, H = 0;
  function layout() {
    W = Math.floor(mapsEl.clientWidth);
    H = Math.round(Math.max(140, Math.min(200, W * 0.16)));
    const pad = { l: 40, r: 18, t: 22, b: 16 };
    const xs = E.resp.map((c) => E.pos[c][0]), ys = E.resp.map((c) => E.pos[c][1]);
    const x0 = Math.min(...xs) - 6, x1 = Math.max(...xs) + 3, y0 = Math.min(...ys) - 3, y1 = Math.max(...ys) + 3;
    const sx = (W - pad.l - pad.r) / (x1 - x0), sy = (H - pad.t - pad.b) / (y1 - y0);
    nodes = E.resp.map((c, i) => ({ c, i, x: pad.l + (E.pos[c][0] - x0) * sx, y: H - pad.b - (E.pos[c][1] - y0) * sy }));
    const anchor = nodes.map((n) => ({ x: n.x, y: n.y })), minD = Math.max(12, Math.min(17, W / 70));
    for (let it = 0; it < 260; it++) {
      for (let a = 0; a < nodes.length; a++) for (let b = a + 1; b < nodes.length; b++) {
        const A = nodes[a], B = nodes[b];
        const dx = B.x - A.x, dy = B.y - A.y, d = Math.hypot(dx, dy) || 0.01;
        if (d < minD) { const k = (minD - d) / d / 2; A.x -= dx * k; A.y -= dy * k; B.x += dx * k; B.y += dy * k; }
      }
      nodes.forEach((n, i) => { n.x += (anchor[i].x - n.x) * 0.035; n.y += (anchor[i].y - n.y) * 0.035; n.y = Math.max(pad.t - 4, Math.min(H - pad.b + 4, n.y)); n.x = Math.max(pad.l, Math.min(W - 8, n.x)); });
    }
    byClass = Object.fromEntries(nodes.map((n) => [n.c, n]));
    const yc = H / 2, nose = pad.l - 30, half = H / 2 - 4;

    mapsEl.innerHTML = "";
    views = SETS.map((set, k) => {
      const wrap = document.createElement("div");
      wrap.className = "echo-map " + set.cls;
      wrap.innerHTML = `<div class="echo-map-head"><span class="echo-name">${set.label}</span><span class="echo-note">${set.note}</span>` +
        `<span class="echo-stat"></span><svg class="echo-spark" width="132" height="26" aria-hidden="true"></svg></div>`;
      const s = svgEl("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, class: "echo-svg", role: "img", "aria-label": `${set.label}: echo across the head` });
      const defs = svgEl("defs", {}, s);
      const gr = svgEl("linearGradient", { id: `body${k}`, x1: "0", x2: "0", y1: "0", y2: "1" }, defs);
      svgEl("stop", { offset: "0", "stop-color": "#10212a" }, gr); svgEl("stop", { offset: "0.5", "stop-color": "#0c1a20" }, gr); svgEl("stop", { offset: "1", "stop-color": "#0a161b" }, gr);
      const body = `M${nose},${yc} C${nose + W * 0.04},${yc - half * 0.62} ${nose + W * 0.15},${yc - half} ${nose + W * 0.33},${yc - half} L${W + 2},${yc - half} L${W + 2},${yc + half} L${nose + W * 0.33},${yc + half} C${nose + W * 0.15},${yc + half} ${nose + W * 0.04},${yc + half * 0.62} ${nose},${yc} Z`;
      svgEl("path", { d: body, fill: `url(#body${k})` }, s);
      svgEl("path", { d: `M${W + 2},${yc - half + 0.5} L${nose + W * 0.33},${yc - half + 0.5} C${nose + W * 0.15},${yc - half + 0.5} ${nose + W * 0.04},${yc - half * 0.62} ${nose},${yc} C${nose + W * 0.04},${yc + half * 0.62} ${nose + W * 0.15},${yc + half - 0.5} ${nose + W * 0.33},${yc + half - 0.5} L${W + 2},${yc + half - 0.5}`, class: "body" }, s);
      const bulbX = pad.l + (95 - x0) * sx;
      svgEl("path", { d: `M${nose + 8},${yc} L${bulbX - 22},${yc - 5} L${bulbX - 22},${yc + 5} Z`, class: "pharynx" }, s);
      svgEl("ellipse", { cx: bulbX, cy: yc, rx: Math.max(16, W * 0.022), ry: Math.max(11, H * 0.08), class: "pharynx" }, s);
      svgEl("text", { x: 8, y: 14, class: "orient" }, s).textContent = "nose";
      svgEl("text", { x: W - 8, y: 14, class: "orient", "text-anchor": "end" }, s).textContent = "toward the body";
      const gRing = svgEl("g", {}, s), gNodes = svgEl("g", {}, s), gLab = svgEl("g", {}, s), gHit = svgEl("g", {}, s);
      const els = nodes.map((n) => {
        const ring = svgEl("circle", { cx: n.x.toFixed(1), cy: n.y.toFixed(1), r: 0, class: "ring" }, gRing);
        const dot = svgEl("circle", { cx: n.x.toFixed(1), cy: n.y.toFixed(1), r: 3, class: "node" }, gNodes);
        const hit = svgEl("circle", { cx: n.x.toFixed(1), cy: n.y.toFixed(1), r: 9, class: "node-hit" + (E.stims.includes(n.c) ? " pokeable" : "") }, gHit);
        hit.addEventListener("pointerenter", () => { hoverC = n.c; draw(); });
        hit.addEventListener("pointerleave", () => { hoverC = null; draw(); });
        hit.addEventListener("click", () => { if (E.stims.includes(n.c)) select(n.c); });
        return { ring, dot };
      });
      const pr = svgEl("circle", { r: 9, class: "poke-ring" }, s);
      const wave = svgEl("circle", { r: 9, class: "poke-ring wave" }, s);
      wrap.appendChild(s);
      mapsEl.appendChild(wrap);
      return { set, k, s, els, pr, wave, gLab, stat: wrap.querySelector(".echo-stat"), spark: wrap.querySelector(".echo-spark") };
    });
    sparks();
    draw();
  }

  // responders over time, per brain, for the chosen poke
  const SPARK_MAX = 40;
  function sparks() {
    views.forEach((v) => {
      const counts = [];
      for (let q = 0; q < T; q++) { let on = 0; for (let r = 0; r < Rn; r++) if (shared(si, r) && Math.abs(val(v.set, si, r, q)) > ON) on++; counts.push(on); }
      v.counts = counts;
      const sw = 132, sh = 26;
      v.spark.innerHTML = "";
      const d = counts.map((c, q) => `${q ? "L" : "M"}${(2 + (q / (T - 1)) * (sw - 4)).toFixed(1)},${(sh - 3 - (Math.min(c, SPARK_MAX) / SPARK_MAX) * (sh - 6)).toFixed(1)}`).join("");
      svgEl("line", { x1: 2, x2: sw - 2, y1: sh - 2.5, y2: sh - 2.5, class: "spark-base" }, v.spark);
      svgEl("path", { d, class: "spark-line " + v.set.cls }, v.spark);
      v.sparkDot = svgEl("circle", { r: 2.6, class: "spark-dot " + v.set.cls }, v.spark);
    });
  }

  // label placement: above, below, right or left of the node; a label that would collide is skipped
  function placeLabels(v, labels, pc) {
    v.gLab.innerHTML = "";
    const boxes = [];
    const fits = (b) => b.x0 > 2 && b.x1 < W - 2 && b.y0 > 18 && b.y1 < H - 1 && !boxes.some((o) => !(b.x1 < o.x0 || b.x0 > o.x1 || b.y1 < o.y0 || b.y0 > o.y1));
    labels.forEach(({ c, r }) => {
      const n = byClass[c]; if (!n) return;
      const isP = c === pc, fs = isP ? 12 : 11, w = c.length * fs * 0.64 + 4, h = fs + 2, gap = r + 4;
      const cands = [[n.x - w / 2, n.y - gap - h], [n.x - w / 2, n.y + gap], [n.x + gap, n.y - h / 2], [n.x - gap - w, n.y - h / 2]];
      for (const [bx, by] of cands) {
        const box = { x0: bx - 2, y0: by - 2, x1: bx + w + 2, y1: by + h + 2 };
        if (isP || fits(box)) {
          boxes.push(box);
          const tx = svgEl("text", { x: (bx + w / 2).toFixed(1), y: (by + h - 3).toFixed(1), "text-anchor": "middle", class: "node-label" + (isP ? " poked" : "") }, v.gLab);
          tx.textContent = c;
          break;
        }
      }
    });
  }

  function draw() {
    const tt = Math.round(t);
    const pc = E.stims[si], pn = byClass[pc];
    views.forEach((v) => {
      let on = 0, meas = 0;
      const top = [];
      v.els.forEach((e, r) => {
        const n = nodes[r];
        const x = val(v.set, si, r, tt);
        if (n.c === pc) { e.dot.setAttribute("class", "node poked"); e.dot.setAttribute("r", 5.5); e.dot.style.fill = ""; e.ring.setAttribute("r", 0); return; }
        if (!isFinite(x)) { e.dot.setAttribute("class", "node absent"); e.dot.setAttribute("r", 2.6); e.dot.style.fill = ""; e.dot.style.fillOpacity = ""; e.ring.setAttribute("r", 0); return; }
        const sh = shared(si, r);
        if (sh) meas++;
        const a = Math.min(1, Math.abs(x) / 1.2);
        if (sh && Math.abs(x) > ON) on++;
        const rad = 3 + 6 * a;
        top.push({ c: n.c, m: Math.abs(x), r: rad });
        const col = x >= 0 ? v.set.up : DOWN;
        e.dot.setAttribute("class", "node live-node");
        e.dot.style.fill = col;
        e.dot.style.fillOpacity = (0.22 + 0.78 * a).toFixed(2);
        e.dot.setAttribute("r", rad.toFixed(1));
        if (a > 0.45) { e.ring.setAttribute("r", (rad + 3.5).toFixed(1)); e.ring.style.stroke = col; e.ring.style.strokeOpacity = (0.55 * a).toFixed(2); }
        else e.ring.setAttribute("r", 0);
      });
      if (pn) {
        v.pr.setAttribute("cx", pn.x); v.pr.setAttribute("cy", pn.y);
        v.wave.setAttribute("cx", pn.x); v.wave.setAttribute("cy", pn.y);
        const w = Math.min(1, t / 5);
        v.wave.setAttribute("r", (9 + w * 70).toFixed(1)); v.wave.style.opacity = (0.55 * (1 - w)).toFixed(2);
      }
      top.sort((p, q) => q.m - p.m);
      const labels = [{ c: pc, r: 6 }];
      if (hoverC && hoverC !== pc) labels.push({ c: hoverC, r: (top.find((o) => o.c === hoverC) || { r: 4 }).r });
      top.filter((o) => o.m > 0.45).slice(0, 5).forEach((o) => labels.push(o));
      placeLabels(v, labels, pc);
      const f2 = (z) => (isFinite(z) ? z.toFixed(2).replace("-", "−") : "n/a");
      v.stat.innerHTML = `<span><b>${on}</b> of ${meas} classes responding</span>` +
        (v.k > 0 ? `<span>agreement with real <b>${f2(agree[v.k])}</b> this poke, <b>${f2(pooled[v.k])}</b> all pokes</span>` : "");
      if (v.sparkDot && v.counts) { v.sparkDot.setAttribute("cx", (2 + (tt / (T - 1)) * 128).toFixed(1)); v.sparkDot.setAttribute("cy", (26 - 3 - (Math.min(v.counts[tt], SPARK_MAX) / SPARK_MAX) * 20).toFixed(1)); }
    });
    scrub.value = String(tt);
    scrub.style.setProperty("--p", `${(tt / (T - 1)) * 100}%`);
    timeOut.textContent = `${tt} s after the poke`;
    host.querySelector(".echo-poked").textContent = pc;
  }

  function select(c) {
    si = E.stims.indexOf(c);
    chips.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.textContent === c)));
    agree = SETS.map((s, k) => (k ? agreementFor(s, [si]) : 1));
    sparks();
    t = 0; draw();
    if (!reduce) play(true);
  }
  function play(on) {
    playing = on; playBtn.textContent = on ? "Pause" : "Play"; playBtn.setAttribute("aria-pressed", String(on));
    if (on) { if (t >= T - 1) t = 0; last = performance.now(); requestAnimationFrame(tick); }
  }
  function tick(now) {
    if (!playing) return;
    t += ((now - last) / 1000) * 4;    // four seconds of worm time per second
    last = now;
    if (t >= T - 1) { t = T - 1; draw(); play(false); return; }
    draw(); requestAnimationFrame(tick);
  }
  playBtn.addEventListener("click", () => play(!playing));
  scrub.addEventListener("input", () => { play(false); t = +scrub.value; draw(); });

  agree = SETS.map((s, k) => (k ? agreementFor(s, [si]) : 1));
  t = reduce ? 6 : 0;
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(layout);
  let lastW = 0;
  new ResizeObserver(() => { const w = Math.floor(mapsEl.clientWidth); if (lastW && Math.abs(w - lastW) > 4) layout(); lastW = w; }).observe(mapsEl);
  const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { io.disconnect(); if (!reduce) play(true); } }, { threshold: 0.3 });
  io.observe(host);
})();
