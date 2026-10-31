/* Echo explorer: poke one neuron class and watch the average echo spread through the head,
   in real worms and in two artificial brains run on the same worms with the same pokes.
   Data: window.NEMATICA_ECHO (web/data/echo.js, local only; scripts/export_site.py --local). */
(function () {
  "use strict";
  const host = document.getElementById("echo");
  if (!host) return;
  const E = window.NEMATICA_ECHO;
  const NS = "http://www.w3.org/2000/svg";
  if (!E) {
    host.querySelector(".echo-maps").innerHTML = '<div class="scope-empty"><div>The echo explorer draws from the local copy of the atlas.<br>Run <code>python scripts/export_site.py --local</code> and reload.</div></div>';
    return;
  }
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const S = E.stims.length, Rn = E.resp.length, T = E.nt;
  const decode = (b64) => { const s = atob(b64), a = new Int8Array(s.length); for (let i = 0; i < s.length; i++) a[i] = (s.charCodeAt(i) << 24) >> 24; return a; };
  const SETS = [
    { key: "real", label: E.labels.real, glow: "#3dd69b", cls: "live" },
    { key: "hybrid_kernels_regimes_obsfit", label: E.labels.hybrid_kernels_regimes_obsfit, note: "passes the poke test", glow: "#f062b4", cls: "copy" },
    { key: "var3_spontaneous", label: E.labels.var3_spontaneous, note: "learned from rest", glow: "#f062b4", cls: "copy" },
  ].map((s) => Object.assign(s, { data: decode(E.sets[s.key]) }));
  const val = (set, si, ri, t) => { const q = set.data[(si * Rn + ri) * T + t]; return q === -128 ? NaN : (q / 127) * E.scale; };

  // ---------------------------------------------------------------- layout
  const W = 1000, H = 196, pad = { l: 44, r: 24, t: 24, b: 20 };
  const xs = Object.values(E.pos).map((p) => p[0]), ys = Object.values(E.pos).map((p) => p[1]);
  const x0 = Math.min(...xs) - 6, x1 = Math.max(...xs) + 4, y0 = Math.min(...ys) - 4, y1 = Math.max(...ys) + 4;
  const sx = (W - pad.l - pad.r) / (x1 - x0), sy = (H - pad.t - pad.b) / (y1 - y0);
  const nodes = E.resp.map((c, i) => ({ c, i, x: pad.l + (E.pos[c][0] - x0) * sx, y: H - pad.b - (E.pos[c][1] - y0) * sy }));
  // relax overlaps so every class stays visible and near its true place
  const anchor = nodes.map((n) => ({ x: n.x, y: n.y }));
  for (let it = 0; it < 220; it++) {
    for (let a = 0; a < nodes.length; a++) for (let b = a + 1; b < nodes.length; b++) {
      const A = nodes[a], B = nodes[b];
      let dx = B.x - A.x, dy = B.y - A.y, d = Math.hypot(dx, dy) || 0.01;
      const min = 15;
      if (d < min) { const k = (min - d) / d / 2; A.x -= dx * k; A.y -= dy * k; B.x += dx * k; B.y += dy * k; }
    }
    nodes.forEach((n, i) => { n.x += (anchor[i].x - n.x) * 0.04; n.y += (anchor[i].y - n.y) * 0.04;
      n.y = Math.max(pad.t - 6, Math.min(H - pad.b + 6, n.y)); });
  }
  const byClass = Object.fromEntries(nodes.map((n) => [n.c, n]));

  function svgEl(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  // worm head silhouette, nose to the left
  function outline(g) {
    const yc = (H - pad.b + pad.t) / 2, nose = pad.l - 30;
    const half = (H - pad.t - pad.b) / 2 + 22;
    const d = `M${nose},${yc} C${nose + 40},${yc - half * 0.55} ${nose + 150},${yc - half} ${nose + 330},${yc - half} L${W + 10},${yc - half} L${W + 10},${yc + half} L${nose + 330},${yc + half} C${nose + 150},${yc + half} ${nose + 40},${yc + half * 0.55} ${nose},${yc} Z`;
    svgEl("path", { d, class: "body-fill" }, g);
    svgEl("path", { d: `M${W + 10},${yc - half} L${nose + 330},${yc - half} C${nose + 150},${yc - half} ${nose + 40},${yc - half * 0.55} ${nose},${yc} C${nose + 40},${yc + half * 0.55} ${nose + 150},${yc + half} ${nose + 330},${yc + half} L${W + 10},${yc + half}`, class: "body" }, g);
    // pharynx, faint: a tube from the mouth to the terminal bulb
    const bulbX = pad.l + (95 - x0) * sx;
    svgEl("path", { d: `M${nose + 6},${yc} L${bulbX - 30},${yc - 7} L${bulbX - 30},${yc + 7} Z`, class: "pharynx" }, g);
    svgEl("ellipse", { cx: bulbX, cy: yc, rx: 26, ry: 17, class: "pharynx" }, g);
  }

  const maps = host.querySelector(".echo-maps");
  maps.innerHTML = "";
  const views = SETS.map((set, k) => {
    const wrap = document.createElement("div");
    wrap.className = "echo-map " + set.cls;
    wrap.innerHTML = `<div class="echo-map-head"><span class="echo-name">${set.label}</span>${set.note ? `<span class="echo-note">${set.note}</span>` : ""}<span class="echo-stat" aria-live="polite"></span></div>`;
    const s = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "echo-svg", role: "img", "aria-label": `${set.label}: echo across the head` });
    const defs = svgEl("defs", {}, s);
    const f = svgEl("filter", { id: `glow${k}`, x: "-100%", y: "-100%", width: "300%", height: "300%" }, defs);
    svgEl("feGaussianBlur", { stdDeviation: "4.5", result: "b" }, f);
    const mg = svgEl("feMerge", {}, f); svgEl("feMergeNode", { in: "b" }, mg); svgEl("feMergeNode", { in: "SourceGraphic" }, mg);
    const g0 = svgEl("g", {}, s); outline(g0);
    svgEl("text", { x: pad.l - 34, y: pad.t - 8, class: "orient" }, s).textContent = "nose";
    svgEl("text", { x: W - pad.r, y: pad.t - 8, class: "orient", "text-anchor": "end" }, s).textContent = "toward the body";
    const gHalo = svgEl("g", { filter: `url(#glow${k})` }, s);
    const gNodes = svgEl("g", {}, s);
    const gLab = svgEl("g", {}, s);
    const els = nodes.map((n) => {
      const halo = svgEl("circle", { cx: n.x, cy: n.y, r: 0, fill: set.glow, opacity: 0 }, gHalo);
      const dot = svgEl("circle", { cx: n.x, cy: n.y, r: 4.2, class: "node" }, gNodes);
      const hit = svgEl("circle", { cx: n.x, cy: n.y, r: 9, class: "node-hit", tabindex: -1 }, gNodes);
      hit.addEventListener("pointerenter", () => showLabel(n.c));
      hit.addEventListener("pointerleave", () => showLabel(null));
      hit.addEventListener("click", () => { if (E.stims.includes(n.c)) select(n.c); });
      if (E.stims.includes(n.c)) hit.classList.add("pokeable");
      return { halo, dot };
    });
    const ring = svgEl("circle", { r: 12, class: "poke-ring" }, s);
    const ring2 = svgEl("circle", { r: 12, class: "poke-ring wave" }, s);
    wrap.appendChild(s);
    maps.appendChild(wrap);
    return { set, s, els, ring, ring2, gLab, stat: wrap.querySelector(".echo-stat") };
  });

  // ---------------------------------------------------------------- state
  let si = Math.max(0, E.stims.indexOf("ASH")), t = 0, playing = false, last = 0, hoverC = null;
  const scrub = host.querySelector(".echo-scrub"), timeOut = host.querySelector(".echo-time"), playBtn = host.querySelector(".echo-play");
  const chips = host.querySelector(".echo-chips");
  E.stims.forEach((c, i) => {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = c; b.className = "echo-chip"; b.setAttribute("aria-pressed", String(i === si));
    b.addEventListener("click", () => select(c));
    chips.appendChild(b);
  });
  scrub.max = String(T - 1);

  function agreement(set) {
    // correlation, across responding classes, of the 0 to 15 s mean echo with the real average
    const a = [], b = [];
    for (let r = 0; r < Rn; r++) {
      let ma = 0, mb = 0, na = 0, nb = 0;
      for (let k = 0; k <= 15 && k < T; k++) { const va = val(set, si, r, k), vb = val(SETS[0], si, r, k); if (isFinite(va)) { ma += va; na++; } if (isFinite(vb)) { mb += vb; nb++; } }
      if (na && nb) { a.push(ma / na); b.push(mb / nb); }
    }
    if (a.length < 8) return NaN;
    const m = (v) => v.reduce((p, q) => p + q, 0) / v.length, A = m(a), B = m(b);
    let sab = 0, saa = 0, sbb = 0;
    for (let i = 0; i < a.length; i++) { sab += (a[i] - A) * (b[i] - B); saa += (a[i] - A) ** 2; sbb += (b[i] - B) ** 2; }
    return sab / Math.sqrt(saa * sbb);
  }
  let agree = [];
  const pooled = SETS.map((set, k) => {
    if (!k) return 1;
    const a = [], b = [];
    for (let i = 0; i < S; i++) for (let r = 0; r < Rn; r++) {
      let ma = 0, mb = 0, na = 0, nb = 0;
      for (let q = 0; q <= 15 && q < T; q++) { const va = set.data[(i * Rn + r) * T + q], vb = SETS[0].data[(i * Rn + r) * T + q]; if (va !== -128) { ma += va; na++; } if (vb !== -128) { mb += vb; nb++; } }
      if (na && nb) { a.push(ma / na); b.push(mb / nb); }
    }
    const m = (v) => v.reduce((p, q) => p + q, 0) / v.length, A = m(a), B = m(b);
    let sab = 0, saa = 0, sbb = 0;
    for (let i = 0; i < a.length; i++) { sab += (a[i] - A) * (b[i] - B); saa += (a[i] - A) ** 2; sbb += (b[i] - B) ** 2; }
    return sab / Math.sqrt(saa * sbb);
  });

  function showLabel(c) { hoverC = c; draw(); }

  function draw() {
    const tt = Math.round(t);
    const pc = E.stims[si], pn = byClass[pc];
    views.forEach((v, k) => {
      let on = 0, meas = 0;
      const top = [];
      v.els.forEach((e, r) => {
        const x = val(v.set, si, r, tt);
        const n = nodes[r];
        if (n.c === pc) { e.dot.setAttribute("class", "node poked"); e.halo.setAttribute("opacity", 0); return; }
        if (!isFinite(x)) { e.dot.setAttribute("class", "node absent"); e.halo.setAttribute("opacity", 0); e.dot.setAttribute("r", 3.2); return; }
        const shared = isFinite(val(SETS[1], si, r, tt));
        if (shared) meas++;
        const a = Math.min(1, Math.abs(x) / 1.1);
        if (shared && Math.abs(x) > 0.35) on++;
        top.push([Math.abs(x), r]);
        if (x >= 0) {
          e.dot.setAttribute("class", "node up"); e.dot.style.fill = v.set.glow; e.dot.style.fillOpacity = 0.18 + 0.82 * a;
          e.halo.setAttribute("fill", v.set.glow);
        } else {
          e.dot.setAttribute("class", "node down"); e.dot.style.fill = "#8fb8ff"; e.dot.style.fillOpacity = 0.15 + 0.85 * a;
          e.halo.setAttribute("fill", "#8fb8ff");
        }
        e.dot.setAttribute("r", 3.6 + 4.2 * a);
        e.halo.setAttribute("r", 4 + 11 * a);
        e.halo.setAttribute("opacity", a > 0.25 ? 0.55 * a : 0);
      });
      if (pn) {
        [v.ring, v.ring2].forEach((rg) => { rg.setAttribute("cx", pn.x); rg.setAttribute("cy", pn.y); });
        const w = Math.min(1, tt / 6);
        v.ring2.setAttribute("r", 12 + w * 60); v.ring2.style.opacity = String(0.6 * (1 - w));
      }
      // labels: the poked class, the strongest three responders, and any hovered class
      v.gLab.innerHTML = "";
      const lab = new Set([pc]);
      top.sort((p, q) => q[0] - p[0]).slice(0, 3).forEach(([m, r]) => { if (m > 0.35) lab.add(nodes[r].c); });
      if (hoverC) lab.add(hoverC);
      lab.forEach((c) => {
        const n = byClass[c]; if (!n) return;
        const tx = svgEl("text", { x: n.x, y: n.y - 13, class: "node-label" + (c === pc ? " poked" : ""), "text-anchor": "middle" }, v.gLab);
        tx.textContent = c;
      });
      const f2 = (x) => x.toFixed(2).replace("-", "\u2212");
      v.stat.innerHTML = `<span>${on} of ${meas} classes responding</span>` + (k > 0 ? `<span>agreement with real: this poke <b>${isFinite(agree[k]) ? f2(agree[k]) : "n/a"}</b>, all pokes <b>${f2(pooled[k])}</b></span>` : "");
    });
    scrub.value = String(tt);
    timeOut.textContent = `${tt} s after the poke`;
    host.querySelector(".echo-poked").textContent = pc;
  }

  function select(c) {
    si = E.stims.indexOf(c);
    chips.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.textContent === c)));
    agree = SETS.map((s, k) => (k ? agreement(s) : 1));
    t = 0; draw();
    if (!reduce) play(true);
  }
  function play(on) {
    playing = on; playBtn.textContent = on ? "Pause" : "Play"; playBtn.setAttribute("aria-pressed", String(on));
    if (on) { if (t >= T - 1) t = 0; last = performance.now(); requestAnimationFrame(tick); }
  }
  function tick(now) {
    if (!playing) return;
    t += ((now - last) / 1000) * 5;   // five seconds of worm time per second
    last = now;
    if (t >= T - 1) { t = T - 1; draw(); play(false); return; }
    draw(); requestAnimationFrame(tick);
  }
  playBtn.addEventListener("click", () => play(!playing));
  scrub.addEventListener("input", () => { play(false); t = +scrub.value; draw(); });

  // start when the section scrolls into view
  agree = SETS.map((s, k) => (k ? agreement(s) : 1));
  t = reduce ? 6 : 0; draw();
  const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { io.disconnect(); if (!reduce) play(true); } }, { threshold: 0.35 });
  io.observe(host);
})();
