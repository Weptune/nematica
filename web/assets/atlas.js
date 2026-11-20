/* NEMATICA, the atlas: every drawing on the home page. All of it is SVG line work drawn at the page's own
   pixel size from window.NEMATICA_RESULTS (web/data/results.js, exported by scripts/export_site.py from
   committed result tables) and window.NEMATICA_BRAIN (the worm's wiring). No blur, no raster. */
(function () {
  "use strict";
  const R = window.NEMATICA_RESULTS || {}, B = window.NEMATICA_BRAIN;
  const NS = "http://www.w3.org/2000/svg";
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const C = { bone: "#ece6d6", b2: "rgba(236,230,214,.74)", b3: "rgba(236,230,214,.52)", line: "rgba(236,230,214,.26)",
    hair: "rgba(236,230,214,.13)", ghost: "rgba(236,230,214,.06)", real: "#b68f1b", wash: "rgba(182,143,27,.27)",
    gilt: "#dcbc62", copy: "#e03063", night: "#0c2a55" };
  const $ = (q, r) => (r || document).querySelector(q), $$ = (q, r) => Array.from((r || document).querySelectorAll(q));
  function el(tag, a, p) { const n = document.createElementNS(NS, tag); for (const k in a || {}) if (a[k] != null) n.setAttribute(k, a[k]); if (p) p.appendChild(n); return n; }
  function tx(p, x, y, s, a) { const t = el("text", Object.assign({ x, y }, a || {}), p); t.textContent = s; return t; }
  const lin = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0)) * (r1 - r0);
  const px = (v) => Math.round(v) + 0.5;
  const f2 = (v, d = 2) => (+v).toFixed(d).replace("-", "−");
  const pc = (v) => Math.round(v * 100) + "%";
  const pol = (cx, cy, r, a) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  const med = (a) => { const s = a.slice().sort((x, y) => x - y), n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
  const qt = (a, q) => { const s = a.slice().sort((x, y) => x - y), i = (s.length - 1) * q, lo = Math.floor(i); return s[lo] + (s[Math.min(s.length - 1, lo + 1)] - s[lo]) * (i - lo); };
  function bgOf(n) { for (let e = n; e && e !== document.documentElement; e = e.parentElement) { const c = getComputedStyle(e).backgroundColor; if (c && c !== "transparent" && !/, 0\)$/.test(c)) return c; } return C.night; }
  function stage(host, h, label) {
    host.innerHTML = "";
    const w = Math.max(280, Math.floor(host.clientWidth));
    const s = el("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}`, class: "show", role: "img", "aria-label": label });
    host.appendChild(s);
    return { s, w, bg: bgOf(host) };
  }
  let tipEl;
  function tip(html, e) {
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tip"; document.body.appendChild(tipEl); }
    if (!html) { tipEl.style.opacity = 0; return; }
    tipEl.innerHTML = html; const w = tipEl.offsetWidth, h = tipEl.offsetHeight;
    let x = e.clientX + 16, y = e.clientY + 16; if (x + w > innerWidth - 8) x = e.clientX - w - 16; if (y + h > innerHeight - 8) y = e.clientY - h - 16;
    tipEl.style.left = Math.max(8, x) + "px"; tipEl.style.top = Math.max(8, y) + "px"; tipEl.style.opacity = 1;
  }
  function hover(n, html) { n.addEventListener("pointermove", (e) => tip(typeof html === "function" ? html() : html, e)); n.addEventListener("pointerleave", () => tip(null)); }
  const row = (a, b) => `<div class="row"><span>${a}</span><span>${b}</span></div>`;
  const rv = (n, i, step) => { n.classList.add("rv"); n.style.setProperty("--d", Math.round(i * (step || 18)) + "ms"); return n; };
  const SF = { class: "sf", "font-style": "italic", "font-weight": 500 };
  // a direct label: a small key mark, then one or two lines of serif text in the ink colour
  function label(s, x, y, lines, mark) {
    if (mark === "real") el("circle", { cx: x + 6, cy: y - 5, r: 5.5, fill: C.real }, s);
    else if (mark === "ring") el("circle", { cx: x + 6, cy: y - 5, r: 5, fill: "none", stroke: C.copy, "stroke-width": 1.8 }, s);
    else if (mark === "copy") el("circle", { cx: x + 6, cy: y - 5, r: 5.5, fill: C.copy }, s);
    else if (mark === "band") el("rect", { x: x, y: y - 11, width: 12, height: 12, fill: C.wash, stroke: C.real, "stroke-width": 1 }, s);
    else if (mark === "light") el("rect", { x: x, y: y - 11, width: 12, height: 12, fill: C.hair }, s);
    else if (mark === "ink") el("path", { d: `M${x} ${y - 5}h12`, stroke: C.bone, "stroke-width": 2 }, s);
    const tx0 = x + (mark ? 22 : 0);
    lines.forEach((t, i) => tx(s, tx0, y + i * 19, t, Object.assign({ "font-size": 18, fill: i ? C.b2 : C.bone }, SF)));
  }
  const axisText = { "font-size": 12, fill: C.b3 }, axisTitle = { "font-size": 12.5, fill: C.b2, "font-weight": 600 };

  // ------------------------------------------------------------------ seals: a ring of ticks, one per animal, round a planet's sign
  function seal(host) {
    const n = +host.dataset.n || 0, g = host.dataset.g, legend = !host.closest(".duo") && !host.closest(".card") && host.dataset.legend;
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
    const u = el("use", { href: "#g-" + g, x: 72, y: 72, width: 56, height: 56 }, s); u.style.color = C.gilt;
  }
  // the dials of the big seals turn a little as the page scrolls past them
  function dials() {
    const D = $$(".plate-head .seal .ticks"); if (!D.length || REDUCED) return;
    let queued = false;
    const turn = () => { queued = false; D.forEach((t) => { const r = t.ownerSVGElement.getBoundingClientRect(); if (r.bottom < -50 || r.top > innerHeight + 50) return;
      t.style.transform = `rotate(${(((r.top + r.height / 2) / innerHeight - 0.5) * 70).toFixed(2)}deg)`; }); };
    addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(turn); } }, { passive: true }); turn();
  }

  // ------------------------------------------------------------------ hero: the worm's wiring, head to tail round a ring
  function cosmos() {
    const host = $("#cosmos"); if (!host || !B) return;
    const N = B.names.length, X = (i) => B.pos[3 * i];
    const order = Array.from({ length: N }, (_, i) => i).sort((a, b) => X(a) - X(b) || B.pos[3 * a + 1] - B.pos[3 * b + 1]);
    const rank = new Array(N); order.forEach((id, k) => (rank[id] = k));
    const GAP = 17 * Math.PI / 180, A0 = -Math.PI / 2 + GAP / 2, SPAN = 2 * Math.PI - GAP;
    const ang = (id) => A0 + SPAN * rank[id] / (N - 1);
    const deg = new Array(N).fill(0), adj = Array.from({ length: N }, () => []);
    const E = B.edges;
    for (let i = 0; i < E.length; i += 2) { deg[E[i]]++; deg[E[i + 1]]++; adj[E[i]].push(E[i + 1]); adj[E[i + 1]].push(E[i]); }
    const RN = 396, cx = 500, cy = 500;
    const chord = (a, b) => {
      const A = ang(a), Bn = ang(b), [x1, y1] = pol(cx, cy, RN - 7, A), [x2, y2] = pol(cx, cy, RN - 7, Bn);
      let d = Math.abs(A - Bn); if (d > Math.PI) d = 2 * Math.PI - d;
      const k = 0.62 * Math.pow(1 - d / Math.PI, 1.5), mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
      return `M${x1.toFixed(1)} ${y1.toFixed(1)}Q${(cx + (mx - cx) * k).toFixed(1)} ${(cy + (my - cy) * k).toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`;
    };
    const mqS = matchMedia("(max-width: 980px)");
    const s = el("svg", { viewBox: mqS.matches ? "40 40 920 920" : "-50 -50 1100 1100", role: "img", tabindex: 0, "aria-label": "The 300 neurons of the worm C. elegans arranged head to tail around a ring, with the 2,045 connections between them drawn as chords. Use the left and right arrow keys to move from neuron to neuron." });
    host.insertBefore(s, host.firstChild);
    mqS.addEventListener("change", () => s.setAttribute("viewBox", mqS.matches ? "40 40 920 920" : "-50 -50 1100 1100"));
    // the wiring
    let all = ""; for (let i = 0; i < E.length; i += 2) all += chord(E[i], E[i + 1]);
    el("path", { d: all, fill: "none", stroke: C.bone, "stroke-opacity": 0.13, "stroke-width": 0.45, "vector-effect": "non-scaling-stroke", class: "wires" }, s);
    const hot = el("path", { d: "", fill: "none", stroke: C.gilt, "stroke-opacity": 0.95, "stroke-width": 0.9, "vector-effect": "non-scaling-stroke", class: "hot" }, s);
    // the graduated limb
    el("circle", { cx, cy, r: 414, fill: "none", stroke: C.line }, s);
    el("circle", { cx, cy, r: 428, fill: "none", stroke: C.hair }, s);
    let tk = "";
    order.forEach((id, k) => { const a = ang(id), [x1, y1] = pol(cx, cy, 414, a), [x2, y2] = pol(cx, cy, k % 10 === 0 ? 428 : 420, a); tk += `M${x1.toFixed(1)} ${y1.toFixed(1)}L${x2.toFixed(1)} ${y2.toFixed(1)}`; });
    el("path", { d: tk, stroke: C.b3, "stroke-width": 1, fill: "none", "vector-effect": "non-scaling-stroke" }, s);
    el("circle", { cx, cy, r: 512, fill: "none", stroke: C.hair }, s);
    // head and tail meet at the top
    tx(s, cx + 10, cy - RN + 7, "head", Object.assign({ "font-size": 22, fill: C.gilt }, SF, { class: "sf lab" }));
    tx(s, cx - 10, cy - RN + 7, "tail", Object.assign({ "font-size": 22, fill: C.gilt, "text-anchor": "end" }, SF, { class: "sf lab" }));
    // the centre plate
    el("circle", { cx, cy, r: 138, fill: C.night, stroke: C.line }, s);
    el("circle", { cx, cy, r: 131, fill: "none", stroke: C.hair }, s);
    // neurons
    const nodes = new Array(N), gN = el("g", {}, s);
    order.forEach((id, k) => { const [x, y] = pol(cx, cy, RN, ang(id));
      const c = el("circle", { cx: x.toFixed(1), cy: y.toFixed(1), r: (1.5 + Math.min(3.6, deg[id] * 0.055)).toFixed(2), fill: C.bone, class: "nd" }, gN);
      c.style.setProperty("--d", Math.round(k * 2.4) + "ms"); nodes[id] = c; });
    // names of the best-connected neurons, radial, kept apart
    const hubs = order.slice().sort((a, b) => deg[b] - deg[a]), placed = [];
    for (const id of hubs) { if (placed.length >= 22) break; const a = ang(id);
      if (placed.some((p) => Math.abs(p - a) < 0.115)) continue; placed.push(a);
      const flip = Math.cos(a) < 0, [x, y] = pol(cx, cy, 436, a), d = a * 180 / Math.PI + (flip ? 180 : 0);
      tx(s, x, y, B.names[id], { class: "sf lab", "font-size": 19, "text-anchor": flip ? "end" : "start", "dominant-baseline": "middle", transform: `rotate(${d.toFixed(1)} ${x.toFixed(1)} ${y.toFixed(1)})` }); }
    // the seven questions, in orbit
    const orbit = el("g", { class: "orbit" }, s);
    $$(".arcana .card").forEach((card, i, all) => { const a = -Math.PI / 2 + ((i + 0.5) / all.length) * 2 * Math.PI, [x, y] = pol(cx, cy, 512, a);
      const link = el("a", { href: card.getAttribute("href"), "aria-label": `${card.querySelector("h3").textContent}: ${card.querySelector("p").textContent}` }, orbit);
      const g = el("g", { class: "planet" }, link); g.style.transformOrigin = `${x.toFixed(1)}px ${y.toFixed(1)}px`;
      el("circle", { cx: x, cy: y, r: 27, fill: C.night, stroke: C.line }, g);
      const u = el("use", { href: "#g-" + card.querySelector(".seal").dataset.g, x: x - 16, y: y - 16, width: 32, height: 32 }, g); u.style.color = C.gilt;
      hover(link, `<b>${card.querySelector(".num").firstChild.textContent.trim()}. ${card.querySelector("h3").textContent}</b>${card.querySelector("p").textContent}`); });
    // interaction
    const nm = $("#cosmos-name"), ct = $("#cosmos-count");
    let cur = -1, lit = [], locked = false, timer = null, qi = 0;
    const queue = hubs.slice(0, 40).sort((a, b) => ((a * 7919) % 97) - ((b * 7919) % 97));
    function show(id) {
      if (id === cur) return; cur = id;
      lit.forEach((c) => { c.setAttribute("fill", C.bone); c.classList.remove("on"); }); lit = [];
      if (id < 0) { hot.setAttribute("d", ""); nm.textContent = "C. elegans"; ct.textContent = "300 neurons, 2,045 connections"; return; }
      let d = ""; const seen = new Set();
      adj[id].forEach((j) => { if (seen.has(j)) return; seen.add(j); d += chord(id, j); nodes[j].setAttribute("fill", C.gilt); lit.push(nodes[j]); });
      hot.setAttribute("d", d); hot.classList.remove("flash"); void hot.getBBox(); hot.classList.add("flash");
      nodes[id].setAttribute("fill", C.gilt); nodes[id].classList.add("on"); lit.push(nodes[id]);
      nm.textContent = B.names[id]; ct.textContent = `wired to ${seen.size} other neurons`;
    }
    function auto() { if (locked) return; show(queue[qi++ % queue.length]); }
    function start() { stop(); if (!REDUCED) timer = setInterval(auto, 3000); }
    function stop() { if (timer) clearInterval(timer); timer = null; }
    // one wedge per neuron as the pointer target
    const gH = el("g", {}, s), half = SPAN / (N - 1) / 2;
    order.forEach((id) => { const a = ang(id), p = [pol(cx, cy, 300, a - half), pol(cx, cy, 470, a - half), pol(cx, cy, 470, a + half), pol(cx, cy, 300, a + half)];
      const w = el("path", { d: "M" + p.map((q) => q[0].toFixed(1) + " " + q[1].toFixed(1)).join("L") + "Z", fill: "transparent", class: "node" }, gH);
      w.addEventListener("pointerenter", () => { if (!locked) { stop(); show(id); } });
      w.addEventListener("click", () => { locked = !(locked && cur === id); stop(); show(id); if (!locked) start(); }); });
    s.addEventListener("pointerleave", () => { if (!locked) start(); });
    s.addEventListener("keydown", (e) => { if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return; e.preventDefault(); locked = true; stop();
      const k = cur < 0 ? 0 : (rank[cur] + (e.key === "ArrowRight" ? 1 : N - 1)) % N; show(order[k]); });
    const css = document.createElement("style");
    css.textContent = `.cosmos .nd{opacity:0}.cosmos.ready .nd{opacity:1;transition:opacity .5s ease var(--d)}.cosmos .nd.on{stroke:${C.gilt};stroke-width:5;stroke-opacity:.35}
      .cosmos .wires{opacity:0}.cosmos.ready .wires{opacity:1;transition:opacity 1.6s ease .5s}.cosmos .hot{opacity:0}.cosmos .hot.flash{opacity:1;transition:opacity .45s ease}
      @media (prefers-reduced-motion: reduce){.cosmos .nd,.cosmos .wires{opacity:1;transition:none}.cosmos .hot.flash{transition:none}}`;
    document.head.appendChild(css);
    requestAnimationFrame(() => host.classList.add("ready"));
    if (REDUCED) show(queue[0]); else { setTimeout(() => { auto(); start(); }, 1900); }
    new IntersectionObserver((es) => es.forEach((e) => (e.isIntersecting ? (locked || REDUCED || start()) : stop()))).observe(host);
    const pb = $("#cosmos-pause");
    if (pb) { if (REDUCED) pb.hidden = true;
      pb.addEventListener("click", () => { const on = !host.classList.contains("still"); host.classList.toggle("still", on); pb.setAttribute("aria-pressed", String(on)); pb.textContent = on ? "Play" : "Pause"; locked = on; if (on) stop(); else start(); }); }
  }

  // ------------------------------------------------------------------ three emblems for the three rules
  function emblem(host) {
    const k = host.dataset.emblem, s = el("svg", { viewBox: "0 0 300 150", "aria-hidden": "true" }); host.appendChild(s);
    const small = { "font-size": 11, fill: C.b3 };
    if (k === "lens") {
      const pts = [[22, 30], [48, 18], [70, 38], [36, 56], [62, 62], [86, 24], [92, 54], [18, 54]], lost = [1, 4, 6];
      [[0, C.real, true], [76, C.copy, false]].forEach(([dy, col, filled]) => {
        pts.forEach((p, i) => { el("circle", { cx: p[0], cy: p[1] + dy, r: 4, fill: filled ? col : "none", stroke: col, "stroke-width": 1.6 }, s);
          const gone = lost.includes(i);
          el("circle", { cx: p[0] + 190, cy: p[1] + dy, r: gone ? 3.2 : 4, fill: gone ? "none" : filled ? col : "none", stroke: gone ? C.line : col, "stroke-width": gone ? 1 : 1.6, "stroke-dasharray": gone ? "1.5 2" : null }, s); });
        el("path", { d: `M104 ${22 + dy}L150 ${40 + dy}L198 ${22 + dy}M104 ${40 + dy}H198M104 ${58 + dy}L150 ${40 + dy}L198 ${58 + dy}`, stroke: C.hair, fill: "none" }, s);
        el("path", { d: `M192 ${35 + dy}l6 5-6 5`, stroke: C.b3, fill: "none" }, s);
      });
      el("path", { d: "M150 8Q170 75 150 142Q130 75 150 8Z", fill: "none", stroke: C.bone, "stroke-width": 1.4 }, s);
      el("path", { d: "M150 2V8M150 142V148", stroke: C.bone }, s);
      tx(s, 4, 82, "animal", small); tx(s, 4, 148, "network", small);
    } else if (k === "rule") {
      const x = lin(0, 1, 14, 286), y = 74;
      el("rect", { x: x(0.34), y: y - 26, width: x(0.66) - x(0.34), height: 52, fill: C.wash }, s);
      el("path", { d: `M${x(0.34)} ${y - 26}V${y + 26}M${x(0.66)} ${y - 26}V${y + 26}`, stroke: C.real }, s);
      el("path", { d: `M14 ${y}H286`, stroke: C.bone, "stroke-width": 1.4 }, s);
      let t = ""; for (let i = 0; i <= 40; i++) t += `M${x(i / 40).toFixed(1)} ${y}v${i % 5 ? 5 : 10}`;
      el("path", { d: t, stroke: C.b3 }, s);
      [0.38, 0.43, 0.47, 0.5, 0.52, 0.57, 0.6, 0.63].forEach((v, i) => el("circle", { cx: x(v), cy: y - 12 - (i % 3) * 3, r: 3.4, fill: C.real }, s));
      el("circle", { cx: x(0.54), cy: y + 16, r: 5.5, fill: C.copy }, s);
      el("circle", { cx: x(0.12), cy: y + 16, r: 5, fill: "none", stroke: C.copy, "stroke-width": 1.8 }, s);
      tx(s, x(0.5), y - 36, "how far real animals sit from each other", Object.assign({ "text-anchor": "middle" }, small));
      tx(s, x(0.54), y + 40, "passes", Object.assign({ "text-anchor": "middle" }, small)); tx(s, x(0.12), y + 40, "does not", Object.assign({ "text-anchor": "middle" }, small));
    } else {
      // watch: an eye. touch: a ray striking one cell, and the rings that spread from it
      el("path", { d: "M14 62Q64 14 114 62Q64 110 14 62Z", fill: "none", stroke: C.bone, "stroke-width": 1.4 }, s);
      el("circle", { cx: 64, cy: 62, r: 19, fill: "none", stroke: C.bone, "stroke-width": 1.4 }, s);
      el("circle", { cx: 64, cy: 62, r: 7, fill: C.bone }, s);
      let r = ""; for (let i = 0; i < 9; i++) { const a = -Math.PI + (i + 0.5) * Math.PI / 9, [x1, y1] = pol(64, 62, 54, a), [x2, y2] = pol(64, 62, 62, a); if (y1 < 40) r += `M${x1.toFixed(1)} ${y1.toFixed(1)}L${x2.toFixed(1)} ${y2.toFixed(1)}`; }
      el("path", { d: r, stroke: C.b3 }, s);
      el("path", { d: "M150 20V124", stroke: C.hair }, s);
      el("circle", { cx: 232, cy: 76, r: 6, fill: C.gilt }, s);
      [18, 32, 46].forEach((q, i) => el("circle", { cx: 232, cy: 76, r: q, fill: "none", stroke: C.gilt, "stroke-opacity": 0.8 - i * 0.22, "stroke-dasharray": i ? "2 4" : null }, s));
      el("path", { d: "M186 14L226 68M214 64l12 4-1-12", fill: "none", stroke: C.bone, "stroke-width": 1.4, "stroke-linejoin": "round" }, s);
      tx(s, 64, 132, "watch", Object.assign({ "text-anchor": "middle" }, small)); tx(s, 232, 142, "touch", Object.assign({ "text-anchor": "middle" }, small));
    }
  }

  // ------------------------------------------------------------------ I. the echo
  function echo(host) {
    const pts = (R.restPoke || []).filter((d) => d.poke != null), G = (R.gaps || [])[0] || { band: [0.087, 0.121] };
    const narrow = host.clientWidth < 820;
    const H = narrow ? 490 : Math.round(Math.min(580, Math.max(460, host.clientWidth * 0.4)));
    const { s, w, bg } = stage(host, H, "Each copy of the worm brain: how many resting-activity tests it passes, against how well its answers to a poke agree with real worms");
    const m = { l: narrow ? 42 : 76, r: narrow ? 12 : 270, t: narrow ? 82 : 22, b: 66 };
    if (narrow) { label(s, 2, 18, ["two real worms agree this well"], "band"); label(s, 2, 42, ["copies that also learned from pokes"], "copy"); label(s, 2, 66, ["copies that only watched"], "ring"); }
    const x = lin(0.5, 6.5, m.l, w - m.r), y = lin(-0.008, 0.135, H - m.b, m.t), mid = (G.band[0] + G.band[1]) / 2;
    el("rect", { x: m.l, y: y(G.band[1]), width: w - m.r - m.l, height: y(G.band[0]) - y(G.band[1]), fill: C.wash }, s);
    el("path", { d: `M${m.l} ${px(y(G.band[1]))}H${w - m.r}M${m.l} ${px(y(G.band[0]))}H${w - m.r}`, stroke: C.real, "stroke-opacity": 0.7 }, s);
    [0, 0.04, 0.08, 0.12].forEach((v) => { el("path", { d: `M${m.l} ${px(y(v))}H${w - m.r}`, stroke: v ? C.hair : C.line }, s); tx(s, m.l - 12, y(v) + 4, f2(v), Object.assign({ "text-anchor": "end" }, axisText)); });
    for (let k = 1; k <= 6; k++) { el("path", { d: `M${px(x(k))} ${H - m.b}v6`, stroke: C.line }, s); tx(s, x(k), H - m.b + 24, String(k), Object.assign({ "text-anchor": "middle" }, axisText)); }
    tx(s, (m.l + w - m.r) / 2, H - 14, narrow ? "Tests of resting activity passed, of 6" : "How real it looks at rest: tests of resting activity passed, of 6", Object.assign({ "text-anchor": "middle" }, axisTitle));
    if (!narrow) tx(s, 0, 0, "How real its answers to a poke are", Object.assign({ "text-anchor": "middle", transform: `translate(20 ${(m.t + H - m.b) / 2}) rotate(-90)` }, axisTitle));
    const by = {}; pts.forEach((d) => (by[d.rest] = by[d.rest] || []).push(d));
    const r = narrow ? 4 : 5.6; let i = 0;
    Object.keys(by).sort().forEach((k) => { const placed = [];
      by[k].sort((a, b) => a.poke - b.poke).forEach((d) => { const cy = y(1 - d.poke); let off = 0, t = 0;
        while (placed.some((p) => Math.hypot(p.x - (x(+k) + off), p.y - cy) < 2 * r + 1.5) && t < 80) { t++; off = (t % 2 ? 1 : -1) * Math.ceil(t / 2) * r * 0.95; }
        placed.push({ x: x(+k) + off, y: cy });
        const learned = d.brain.startsWith("hybrid");
        const c = rv(el("circle", { cx: x(+k) + off, cy, r: learned ? r : r - 0.8, fill: learned ? C.copy : bg, stroke: learned ? bg : C.copy, "stroke-width": learned ? 1.5 : 1.7 }, s), i++, 9);
        hover(c, `<b>${learned ? "Learned from pokes too" : "Learned by watching"}</b>${row("Resting tests passed", d.rest + " of 6")}${row("Agreement with real worms", f2(1 - d.poke))}`); }); });
    if (!narrow) { const lx = w - m.r + 26;
      label(s, lx, y(mid) + 2, ["Two real worms", "agree about this well"], "band");
      label(s, lx, y(0.058), ["Copies that also", "learned from pokes"], "copy");
      label(s, lx, y(0.012), ["Copies that only", "watched"], "ring");
    }
  }

  // ------------------------------------------------------------------ II. the push
  function push(host) {
    const O = R.optoSign; if (!O) return;
    const narrow = host.clientWidth < 820, H = narrow ? 440 : 500, order = ["Sst", "Vip"];
    const D = O.mice.filter((d) => order.includes(d.line)).sort((a, b) => order.indexOf(a.line) - order.indexOf(b.line) || a.real - b.real);
    const { s, w, bg } = stage(host, H, `For ${D.length} mice: the share of brain regions a copy fitted at rest predicted would rise when one kind of inhibitory cell was driven, and the share that did`);
    const m = { l: narrow ? 42 : 76, r: narrow ? 12 : 270, t: narrow ? 58 : 22, b: 78 }, gapG = narrow ? 18 : 44, n = D.length;
    const step = (w - m.l - m.r - gapG) / n, y = lin(0, 1, H - m.b, m.t);
    if (narrow) { label(s, 2, 18, ["the copy's prediction"], "ring"); label(s, w / 2 + 6, 18, ["what happened"], "real"); label(s, 2, 42, ["light alone"], "light"); }
    el("rect", { x: m.l, y: y(O.wt[2]), width: w - m.l - m.r, height: y(O.wt[0]) - y(O.wt[2]), fill: C.hair }, s);
    [0, 0.25, 0.5, 0.75, 1].forEach((v) => { el("path", { d: `M${m.l} ${px(y(v))}H${w - m.r}`, stroke: v === 0.5 ? C.line : C.hair, "stroke-dasharray": v === 0.5 ? "3 5" : null }, s); tx(s, m.l - 12, y(v) + 4, pc(v), Object.assign({ "text-anchor": "end" }, axisText)); });
    if (!narrow) tx(s, 0, 0, "Share of brain regions that rise", Object.assign({ "text-anchor": "middle", transform: `translate(20 ${(m.t + H - m.b) / 2}) rotate(-90)` }, axisTitle));
    let xi = m.l, g = null, gx0 = 0; const r = narrow ? 3.3 : 5, groups = [];
    D.forEach((d, i) => { if (d.line !== g) { if (g) { groups.push([g, gx0, xi]); xi += gapG; } g = d.line; gx0 = xi; }
      const cx = xi + step / 2;
      rv(el("path", { d: `M${px(cx)} ${y(d.w)}V${y(d.real)}`, stroke: C.line }, s), i, 14);
      rv(el("circle", { cx, cy: y(d.w), r: r - 0.6, fill: bg, stroke: C.copy, "stroke-width": 1.7 }, s), i, 14);
      rv(el("circle", { cx, cy: y(d.real), r, fill: C.real, stroke: bg, "stroke-width": 1.2 }, s), i, 14);
      hover(el("rect", { x: xi, y: m.t, width: step, height: H - m.t - m.b, fill: "transparent" }, s), `<b>${d.line} mouse ${d.id.replace("sub-", "")}</b>${row("Copy fitted at rest predicted rising", pc(d.w))}${row("Rose when the cells were driven", pc(d.real))}${row("Light alone, median", pc(O.wt[1]))}`);
      xi += step; });
    groups.push([g, gx0, xi]);
    const cnt = (l) => D.filter((d) => d.line === l).length;
    groups.forEach(([gn, a, b]) => { el("path", { d: `M${a + 2} ${px(H - m.b + 14)}H${b - 2}`, stroke: C.line }, s);
      tx(s, (a + b) / 2, H - m.b + 38, narrow ? `${gn}, ${cnt(gn)}` : `${gn} cells, ${cnt(gn)} mice`, Object.assign({ "font-size": narrow ? 17 : 20, fill: C.bone, "text-anchor": "middle" }, SF));
      tx(s, (a + b) / 2, H - m.b + 58, gn === "Sst" ? (narrow ? "inhibit neighbours" : "they inhibit their neighbours") : (narrow ? "inhibit inhibitors" : "they inhibit other inhibitors"), Object.assign({ "text-anchor": "middle" }, axisText)); });
    if (!narrow) { const lx = w - m.r + 26;
      label(s, lx, y(0.9), ["What the copy fitted", "at rest predicted"], "ring");
      label(s, lx, y(O.wt[1]) + 4, ["What light alone does,", "in mice without the opsin"], "light");
      label(s, lx, y(0.13), ["What happened when", "the cells were driven"], "real"); }
  }

  // ------------------------------------------------------------------ III. the face
  function face(host) {
    const D = R.shrinkage || []; if (!D.length) return;
    const narrow = host.clientWidth < 820, H = narrow ? 470 : 520;
    const { s, w, bg } = stage(host, H, "As each worm's model is pulled toward the average worm, forecasting skill barely changes while individuality collapses");
    const m = { l: narrow ? 46 : 76, r: narrow ? 14 : 270, t: 40, b: 70 }, lx = (v) => Math.log10(+v);
    const x = lin(lx(D[0].lam), lx(D[D.length - 1].lam), m.l + 8, w - m.r - 8);
    const gapY = 44, ph = (H - m.t - m.b - gapY) / 2;
    const yA = lin(0.69, 0.77, m.t + ph, m.t), yB = lin(0.4, 1.12, H - m.b, H - m.b - ph);
    const iBest = D.reduce((b, d, i) => (d.r2 > D[b].r2 ? i : b), 0), iTrue = D.findIndex((d) => +d.lam === 300);
    [[iTrue, "the faithful copy"], [iBest, "the best forecaster"]].forEach(([k, t]) => { const xx = x(lx(D[k].lam));
      el("path", { d: `M${px(xx)} ${m.t - 10}V${H - m.b + 6}`, stroke: C.line, "stroke-dasharray": "3 5" }, s);
      tx(s, xx, m.t - 18, narrow ? t.replace("the ", "") : t, Object.assign({ "font-size": narrow ? 15 : 18, fill: C.bone, "text-anchor": "middle" }, SF)); });
    [0.7, 0.73, 0.76].forEach((v) => { el("path", { d: `M${m.l} ${px(yA(v))}H${w - m.r}`, stroke: C.hair }, s); tx(s, m.l - 12, yA(v) + 4, f2(v), Object.assign({ "text-anchor": "end" }, axisText)); });
    el("rect", { x: m.l, y: yB(1.05), width: w - m.r - m.l, height: yB(0.95) - yB(1.05), fill: C.wash }, s);
    el("path", { d: `M${m.l} ${px(yB(1))}H${w - m.r}`, stroke: C.real }, s);
    [0.5, 0.75, 1].forEach((v) => { if (v !== 1) el("path", { d: `M${m.l} ${px(yB(v))}H${w - m.r}`, stroke: C.hair }, s); tx(s, m.l - 12, yB(v) + 4, f2(v), Object.assign({ "text-anchor": "end" }, axisText)); });
    const curve = (yy, k, col) => { const p = D.map((d) => [x(lx(d.lam)), yy(d[k])]);
      const path = el("path", { d: p.map((q, j) => (j ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(""), fill: "none", stroke: col, "stroke-width": 2, "stroke-linejoin": "round", class: "draw" }, s);
      path.style.setProperty("--len", Math.ceil(path.getTotalLength()));
      p.forEach((q, j) => hover(rv(el("circle", { cx: q[0], cy: q[1], r: 5, fill: col, stroke: bg, "stroke-width": 2 }, s), j, 90),
        `<b>Pull toward the average: ${Number(D[j].lam).toLocaleString()}</b>${row("Forecasting skill (R²)", f2(D[j].r2, 3))}${row("Individuality (real worms are 1)", f2(D[j].ind, 2))}`));
      return p; };
    const pA = curve(yA, "r2", C.bone), pB = curve(yB, "ind", C.copy);
    if (!narrow) { const xr = w - m.r + 26;
      label(s, xr, pA[pA.length - 1][1] + 6, ["Forecasting skill", "of the copy"], "ink");
      label(s, xr, yB(1) + 6, ["Real worms", "are this individual"], "band");
      label(s, xr, pB[pB.length - 1][1] + 6, ["Individuality", "of the copy"], "copy");
    } else { tx(s, m.l, yA(0.77) + 2, "forecasting skill", Object.assign({ "font-size": 16, fill: C.bone }, SF)); tx(s, m.l, yB(1.12) + 8, "individuality (real worms are 1)", Object.assign({ "font-size": 16, fill: C.bone }, SF)); }
    tx(s, m.l, H - m.b + 28, "each worm its own model", axisText);
    tx(s, w - m.r, H - m.b + 28, "one average model", Object.assign({ "text-anchor": "end" }, axisText));
    tx(s, (m.l + w - m.r) / 2, H - 14, narrow ? "Pull toward the average worm" : "How hard each worm's model is pulled toward the average worm", Object.assign({ "text-anchor": "middle" }, axisTitle));
  }

  // ------------------------------------------------------------------ IV. the long memory
  function memory(host) {
    const PM = R.permouse; if (!PM) return;
    const D = PM.mice, n = D.length, narrow = host.clientWidth < 820, H = narrow ? 430 : 520;
    const { s, w, bg } = stage(host, H, `Slow memory in ${n} mice, in a random network recorded through each mouse's own instrument, and in the same network with strong slow drives`);
    const m = { l: narrow ? 42 : 76, r: narrow ? 12 : 270, t: narrow ? 58 : 24, b: 58 };
    const x = (i) => m.l + 12 + (i * (w - m.l - m.r - 24)) / (n - 1), y = lin(0, 0.34, H - m.b, m.t);
    if (narrow) { label(s, 2, 18, ["mouse"], "real"); label(s, 92, 18, ["random network"], "ring"); label(s, 2, 42, ["with strong slow drives"], "copy"); }
    [0, 0.1, 0.2, 0.3].forEach((v) => { el("path", { d: `M${m.l} ${px(y(v))}H${w - m.r}`, stroke: v ? C.hair : C.line }, s); tx(s, m.l - 12, y(v) + 4, f2(v, 1), Object.assign({ "text-anchor": "end" }, axisText)); });
    if (!narrow) tx(s, 0, 0, "Slow memory", Object.assign({ "text-anchor": "middle", transform: `translate(20 ${(m.t + H - m.b) / 2}) rotate(-90)` }, axisTitle));
    const r = narrow ? 3.4 : 5.2;
    D.forEach((d, i) => { const xi = x(i);
      rv(el("path", { d: `M${px(xi)} ${y(d.m)}V${y(d.rnn)}`, stroke: C.line }, s), i, 22);
      if (d.slow != null) rv(el("circle", { cx: xi, cy: y(d.slow), r: r - 1.4, fill: C.copy, stroke: bg, "stroke-width": 1 }, s), i, 22);
      rv(el("circle", { cx: xi, cy: y(d.rnn), r: r - 0.6, fill: bg, stroke: C.copy, "stroke-width": 1.7 }, s), i, 22);
      rv(el("circle", { cx: xi, cy: y(d.m), r, fill: C.real, stroke: bg, "stroke-width": 1.2 }, s), i, 22);
      hover(el("rect", { x: xi - (w - m.l - m.r) / (2 * n), y: m.t, width: (w - m.l - m.r) / n, height: H - m.t - m.b, fill: "transparent" }, s),
        `<b>Mouse ${i + 1} of ${n}</b>${row("Mouse", f2(d.m, 3))}${row("Random network, recorded like this mouse", f2(d.rnn, 3))}${row("Same network, strong slow drives", d.slow == null ? "not measured" : f2(d.slow, 3))}`); });
    tx(s, (m.l + w - m.r) / 2, H - 16, `${n} mice, ordered by their own slow memory`, Object.assign({ "text-anchor": "middle" }, axisTitle));
    if (!narrow) { const lx = w - m.r + 26, last = D[n - 1];
      const labs = [[last.slow, ["The same network", "with strong slow drives"], "copy"], [last.m, ["The mouse"], "real"], [last.rnn, ["A random network,", "recorded as that mouse was"], "ring"]]
        .map((o) => ({ yy: y(o[0]) + 6, t: o[1], k: o[2] })).sort((a, b) => a.yy - b.yy);
      for (let j = 1; j < labs.length; j++) if (labs[j].yy - labs[j - 1].yy < 48) labs[j].yy = labs[j - 1].yy + 48;
      labs.forEach((o) => label(s, lx, o.yy, o.t, o.k)); }
  }

  // ------------------------------------------------------------------ V. the inner light
  function light(host) {
    const S = R.slowStudy; if (!S) return;
    const narrow = host.clientWidth < 820, H = narrow ? 440 : 400;
    const { s, w, bg } = stage(host, H, "Share of state that is internal, in 49 mice and in each kind of network");
    const m = { l: narrow ? 14 : 34, r: narrow ? 14 : 34 }, ya = Math.round(H * 0.5), x = lin(0, 1, m.l, w - m.r), q = S.mice.M1;
    el("rect", { x: x(q[0]), y: ya - 78, width: x(q[2]) - x(q[0]), height: 156, fill: C.wash }, s);
    el("path", { d: `M${px(x(q[0]))} ${ya - 78}V${ya + 78}M${px(x(q[2]))} ${ya - 78}V${ya + 78}`, stroke: C.real, "stroke-opacity": 0.7 }, s);
    S.mice.M1all.forEach((v, i) => rv(el("path", { d: `M${px(x(v))} ${ya - 13}V${ya + 13}`, stroke: C.real, "stroke-width": 1.6 }, s), i, 12));
    tx(s, x(q[1]), ya - 90, `${S.mice.n} mice`, Object.assign({ "font-size": 20, fill: C.bone, "text-anchor": "middle" }, SF));
    el("path", { d: `M${m.l} ${px(ya)}H${w - m.r}`, stroke: C.line }, s);
    [0, 0.25, 0.5, 0.75, 1].forEach((v) => { el("path", { d: `M${px(x(v))} ${ya - 5}V${ya + 5}`, stroke: C.b3 }, s);
      tx(s, x(v), H - 36, v === 0 ? "none of it" : v === 1 ? "all of it" : pc(v), Object.assign({ "text-anchor": v === 0 ? "start" : v === 1 ? "end" : "middle" }, axisText)); });
    tx(s, (m.l + w - m.r) / 2, H - 10, narrow ? "Share of state that is internal" : "Share of the state that is internal, not locked to what it sees", Object.assign({ "text-anchor": "middle" }, axisTitle));
    const nets = [];
    S.families.filter((f) => f.counted).forEach((f) => f.members.forEach((mb) => nets.push({ v: mb.M1[1], t: f.members.length > 1 ? `${f.name} ${mb.label}` : f.name, mb })));
    nets.sort((a, b) => a.v - b.v);
    const up = [], dn = [];
    nets.forEach((o, i) => { const isUp = i % 2 === 0, lanes = isUp ? up : dn;
      const t = tx(s, 0, 0, o.t, Object.assign({ "font-size": narrow ? 15 : 18, fill: C.bone }, SF));
      const tw = t.getComputedTextLength(), lx = Math.max(m.l, Math.min(x(o.v) - tw / 2, w - m.r - tw));
      let k = 0; while ((lanes[k] || []).some((b) => lx < b[1] + 14 && lx + tw > b[0] - 14)) k++;
      (lanes[k] = lanes[k] || []).push([lx, lx + tw]);
      const ly = isUp ? ya - 36 - k * 24 : ya + 48 + k * 24;
      t.setAttribute("x", lx); t.setAttribute("y", ly);
      el("path", { d: `M${px(x(o.v))} ${isUp ? ly + 6 : ya + 9}V${isUp ? ya - 9 : ly - 15}`, stroke: C.copy, "stroke-opacity": 0.6 }, s);
      const c = rv(el("circle", { cx: x(o.v), cy: ya, r: narrow ? 5.5 : 7, fill: bg, stroke: C.copy, "stroke-width": 2 }, s), i, 60);
      const h = `<b>${o.t}</b>${row("Internal share, median over mice", pc(o.v))}${row("Middle half", `${pc(o.mb.M1[0])} to ${pc(o.mb.M1[2])}`)}`; hover(c, h); hover(t, h); });
  }

  // ------------------------------------------------------------------ VI. the waning: a moon for each answer
  function moon(s, cx, cy, r, f, col, bg) {
    el("circle", { cx, cy, r, fill: bg, stroke: col, "stroke-width": 1.4 }, s);
    if (f >= 0.999) { el("circle", { cx, cy, r, fill: col }, s); return; }
    const rx = r * Math.abs(1 - 2 * f);
    el("path", { d: `M${cx} ${cy - r}A${r} ${r} 0 0 0 ${cx} ${cy + r}A${rx.toFixed(2)} ${r} 0 0 ${f < 0.5 ? 1 : 0} ${cx} ${cy - r}Z`, fill: col }, s);
  }
  function waning(host) {
    const G = (R.gaps || []).find((g) => /same poke/i.test(g.title)) || { band: [0.34, 0.64] };
    const lo = G.band[0], hi = G.band[1], mid = (lo + hi) / 2, narrow = host.clientWidth < 470, H = narrow ? 320 : 330;
    const { s, w, bg } = stage(host, H, `A real worm's second answer to the same poke is about half its first (between ${lo} and ${hi}); an artificial network's second answer equals its first`);
    const r = narrow ? 30 : 46, x1 = r + (narrow ? 4 : 10), x2 = x1 + r * 2 + (narrow ? 40 : 70), yA = narrow ? 70 : 86, yB = narrow ? 226 : 234;
    [[yA, C.real, mid, "A real worm"], [yB, C.copy, 1, "An artificial network"]].forEach(([yy, col, f, name], k) => {
      moon(s, x1, yy, r, 1, col, bg); moon(s, x2, yy, r, f, col, bg);
      el("path", { d: `M${x1 + r + 9} ${yy}H${x2 - r - 11}m-7 -5l7 5-7 5`, fill: "none", stroke: C.b3 }, s);
      if (!k) [lo, hi].forEach((v) => { const rx = r * Math.abs(1 - 2 * v);
        el("path", { d: `M${x2} ${yy - r}A${rx.toFixed(2)} ${r} 0 0 ${v < 0.5 ? 0 : 1} ${x2} ${yy + r}`, fill: "none", stroke: C.bone, "stroke-dasharray": "2 4", "stroke-opacity": 0.8 }, s); });
      const lx = x2 + r + (narrow ? 14 : 28);
      if (narrow) {
        tx(s, 0, yy - r - 14, name, Object.assign({ "font-size": 20, fill: C.bone }, SF));
        tx(s, lx, yy - 4, k ? "the same" : "about half", { "font-size": 13, fill: C.b2 });
        tx(s, lx, yy + 14, k ? "every time" : `${f2(lo)} to ${f2(hi)}`, { "font-size": 12, fill: C.b3 });
      } else {
        tx(s, lx, yy - 12, name, Object.assign({ "font-size": 24, fill: C.bone }, SF));
        tx(s, lx, yy + 10, k ? "answers the same every time" : "second answer: about half", { "font-size": 13, fill: C.b2 });
        if (!k) tx(s, lx, yy + 29, `between ${f2(lo)} and ${f2(hi)} of the first`, { "font-size": 12, fill: C.b3 });
      }
      tx(s, x1, yy + r + 20, "first answer", Object.assign({ "text-anchor": "middle" }, axisText)); tx(s, x2, yy + r + 20, "asked again", Object.assign({ "text-anchor": "middle" }, axisText));
    });
  }

  // ------------------------------------------------------------------ VII. the journey: six tests, three trials
  function journey(host) {
    const E = R.emulator; if (!E) return;
    const mode = (k) => { const v = (E[k] || []).map((d) => d.rest), c = {}; v.forEach((n) => (c[n] = (c[n] || 0) + 1)); return [Math.min(...v), Math.max(...v), +Object.keys(c).sort((a, b) => c[b] - c[a])[0]]; };
    const rows = [["On the worms it was built on", "the recipe, held-still worms", mode("atlas_cv3")], ["On worms that move", "the same recipe, refitted, another lab", mode("atanas")], ["On worms that move", "a plain copy fitted to rest alone", mode("atanas_control_rest")]];
    const narrow = host.clientWidth < 470, rowH = narrow ? 118 : 96, H = rowH * 3 + (narrow ? 26 : 42);
    const { s, bg } = stage(host, H, "Of six tests of ongoing activity, the recipe passes five or six on the worms it was built on, one on freely moving worms, where a plain copy fitted to rest passes three");
    const r = narrow ? 13 : 15, gap = narrow ? 10 : 12, x0 = 4, y0 = narrow ? 62 : 34;
    const px5 = x0 + 4 * (2 * r + gap) - gap / 2;
    el("path", { d: narrow ? rows.map((_, k) => `M${px(px5)} ${y0 + k * rowH - r - 5}v${2 * r + 10}`).join("") : `M${px(px5)} 8V${rowH * 3 - 8}`, stroke: C.gilt, "stroke-dasharray": "3 5" }, s);
    tx(s, px5 + 8, rowH * 3 + (narrow ? 0 : 14), "pass mark: 5 of 6", { "font-size": 12, fill: C.gilt });
    rows.forEach(([a, b, v], k) => { const yy = y0 + k * rowH;
      for (let i = 0; i < 6; i++) { const cx = x0 + r + i * (2 * r + gap), on = i < v[2], maybe = i >= v[0] && i < v[1];
        rv(el("circle", { cx, cy: yy, r: on ? r : r - 1, fill: on ? C.copy : bg, stroke: on ? "none" : maybe ? C.copy : C.line, "stroke-width": 1.5, "stroke-dasharray": !on && maybe ? "3 3" : null }, s), k * 6 + i, 40); }
      const cnt = v[0] === v[1] ? `${v[0]} of 6 in all five runs` : `${v[0]} or ${v[1]} of 6 across five runs`;
      if (narrow) {
        tx(s, x0, yy - 38, a, Object.assign({ "font-size": 19, fill: C.bone }, SF));
        tx(s, x0, yy - 22, b, { "font-size": 11.5, fill: C.b2 });
        tx(s, x0 + 6 * (2 * r + gap) + 4, yy + 4, cnt.replace(" in all five runs", "").replace(" across five runs", ""), { "font-size": 12, fill: C.b2 });
      } else {
        const lx = x0 + 6 * (2 * r + gap) + 18;
        tx(s, lx, yy - 4, a, Object.assign({ "font-size": 22, fill: C.bone }, SF));
        tx(s, lx, yy + 16, b, { "font-size": 12.5, fill: C.b2 });
        tx(s, x0, yy + r + 22, cnt, axisText);
      }
    });
  }

  // ------------------------------------------------------------------ the answer: seven rows on one sheet
  function ledger(host) {
    const G = (R.gaps || []).slice(), O = R.optoSign; if (!G.length) return;
    if (O) { const sst = O.mice.filter((d) => d.line === "Sst"), re = sst.map((d) => d.real), wu = sst.map((d) => d.w);
      G.splice(1, 0, { title: "Which way a cell pushes", where: `Mouse cortex, ${O.mice.length} animals, written down in advance`, scale: "Share of regions that rise when Sst cells are switched on", domain: [0, 1], ticks: [0, 0.5, 1], pct: true,
        band: [qt(re, 0.25), qt(re, 0.75)], bandLabel: "real mice", plain: { value: med(wu), label: "copy fitted at rest" },
        status: { kind: "open", text: "Open: watching points the wrong way", sub: "A copy taught by light pulses does better; none yet answers like a second mouse" } }); }
    const names = [["mercury", "The Echo"], ["mars", "The Push"], ["venus", "The Face"], ["saturn", "The Long Memory"], ["sun", "The Inner Light"], ["moon", "The Waning"], ["jupiter", "The Journey"]];
    host.innerHTML = ""; const bg = bgOf(host);
    G.forEach((g, i) => {
      const rowEl = document.createElement("a"); rowEl.className = "row"; rowEl.href = "#q" + (i + 1); rowEl.style.textDecoration = "none"; rowEl.style.color = "inherit";
      rowEl.innerHTML = `<svg class="g" aria-hidden="true"><use href="#g-${names[i][0]}"/></svg><div class="t"><b>${names[i][1]}</b><span>${g.where}</span></div><div class="strip"></div>
        <div class="st"><svg aria-hidden="true" viewBox="0 0 48 24"><use href="#v-${g.status.kind}"/></svg><div><b>${g.status.text}</b>${g.status.sub}</div></div>`;
      host.appendChild(rowEl);
      const sh = rowEl.querySelector(".strip"), w = Math.max(240, Math.floor(sh.clientWidth)), H = 104;
      const s = el("svg", { viewBox: `0 0 ${w} ${H}`, width: w, height: H, role: "img", "aria-label": `${g.scale}. ${g.status.text}.` }); sh.appendChild(s);
      const x = lin(g.domain[0], g.domain[1], 10, w - 10), ya = 52, fmt = (v) => (g.pct ? pc(v) : g.tickFmt === "int" ? String(v) : f2(v, g.dp));
      const bw = Math.max(4, x(g.band[1]) - x(g.band[0]));
      el("rect", { x: x(g.band[0]), y: ya - 14, width: bw, height: 28, fill: C.wash }, s);
      el("path", { d: `M${px(x(g.band[0]))} ${ya - 14}v28M${px(x(g.band[0]) + bw)} ${ya - 14}v28`, stroke: C.real }, s);
      el("path", { d: `M10 ${px(ya)}H${w - 10}`, stroke: C.line }, s);
      g.ticks.forEach((v) => { el("path", { d: `M${px(x(v))} ${ya}v5`, stroke: C.b3 }, s); tx(s, x(v), ya + 19, fmt(v), { "font-size": 11, fill: C.b3, "text-anchor": "middle" }); });
      tx(s, 10, 11, g.scale, { "font-size": 11, fill: C.b3 });
      const mark = (o, filled) => { if (!o) return;
        if (o.range) el("path", { d: `M${x(o.range[0])} ${px(ya)}H${x(o.range[1])}`, stroke: C.copy, "stroke-width": 3, "stroke-linecap": "round" }, s);
        const vals = o.values || (o.value != null ? [o.value] : o.range ? [(o.range[0] + o.range[1]) / 2] : []);
        vals.forEach((v) => el("circle", { cx: x(v), cy: ya, r: filled ? 6 : 5, fill: filled ? C.copy : bg, stroke: filled ? bg : C.copy, "stroke-width": filled ? 1.5 : 1.8 }, s));
        if (!vals.length) return;
        const cxm = vals.length > 1 ? (x(vals[0]) + x(vals[vals.length - 1])) / 2 : x(vals[0]);
        const anchor = vals.length > 1 ? "middle" : cxm > w * 0.6 ? "end" : cxm < w * 0.25 ? "start" : "middle", dx = anchor === "end" ? 8 : anchor === "start" ? -8 : 0;
        tx(s, cxm + dx, filled ? ya + 40 : ya - 22, o.label, { "font-size": 11.5, fill: C.b2, "text-anchor": anchor }); };
      mark(g.plain, false); mark(g.fixed, true);
      hover(rowEl, () => `<b>${names[i][1]}</b>${(g.tip || [[g.plain.label, fmt(g.plain.value)], [g.bandLabel, `${fmt(g.band[0])} to ${fmt(g.band[1])}`]]).map((t) => row(t[0], t[1])).join("")}`);
    });
  }

  // ------------------------------------------------------------------ the great seal: seven questions on a seven-pointed star
  function greatSeal(host) {
    const cards = $$(".arcana .card"); if (!cards.length) return;
    const s = el("svg", { viewBox: "0 0 520 520", "aria-hidden": "true" }); host.appendChild(s);
    const cx = 260, cy = 260, RO = 250, RV = 178;
    el("circle", { cx, cy, r: RO, fill: "none", stroke: C.line }, s); el("circle", { cx, cy, r: RO - 6, fill: "none", stroke: C.hair }, s);
    el("circle", { cx, cy, r: RO - 34, fill: "none", stroke: C.hair }, s);
    let t = ""; for (let i = 0; i < 252; i++) { const a = (i / 252) * 2 * Math.PI, [x1, y1] = pol(cx, cy, RO - 34, a), [x2, y2] = pol(cx, cy, RO - 34 - (i % 36 === 0 ? 12 : i % 6 === 0 ? 8 : 4), a); t += `M${x1.toFixed(1)} ${y1.toFixed(1)}L${x2.toFixed(1)} ${y2.toFixed(1)}`; }
    el("path", { d: t, stroke: C.b3, "stroke-width": .8, fill: "none" }, s);
    el("path", { id: "gs-arc", d: `M${cx} ${cy - (RO - 25)}a${RO - 25} ${RO - 25} 0 1 1-.01 0`, fill: "none" }, s);
    const lt = el("text", { class: "legend", style: "font-size:11px" }, s), tp = el("textPath", { href: "#gs-arc", textLength: Math.round(2 * Math.PI * (RO - 25)) - 12, lengthAdjust: "spacing" }, lt);
    tp.textContent = "WHAT THEY WERE SHOWN ✦ WHAT THEY WERE BUILT TO CARRY ✦ NOT THAT THEY ARE ARTIFICIAL ✦ ";
    const V = cards.map((c, i) => pol(cx, cy, RV, -Math.PI / 2 + (i / 7) * 2 * Math.PI));
    let star = ""; for (let i = 0, k = 0; i < 7; i++, k = (k + 3) % 7) star += (i ? "L" : "M") + V[k][0].toFixed(1) + " " + V[k][1].toFixed(1);
    el("path", { d: star + "Z", fill: "none", stroke: C.line, "stroke-linejoin": "round" }, s);
    el("circle", { cx, cy, r: RV, fill: "none", stroke: C.hair, "stroke-dasharray": "2 5" }, s);
    el("circle", { cx, cy, r: 46, fill: C.deep || "#081f42", stroke: C.line }, s);
    el("path", { d: "M6 44c10 0 11-23 23-23 11 0 11 22 20 22 5 0 7-7 9-13-1 11-5 18-11 18-12 0-10-22-19-22-8 0-11 23-22 23z", fill: C.bone, transform: `translate(${cx - 29} ${cy - 31}) scale(.9)` }, s);
    el("circle", { cx: cx - 29 + 29 * 0.9, cy: cy - 31 + 23.5 * 0.9, r: 3.8, fill: C.gilt }, s);
    cards.forEach((c, i) => { const [x, y] = V[i], kind = (c.querySelector(".v use").getAttribute("href") || "").replace("#v-", "");
      el("circle", { cx: x, cy: y, r: 31, fill: bgOf(host), stroke: kind === "closed" ? C.gilt : C.b2, "stroke-width": kind === "closed" ? 2 : 1.2, "stroke-dasharray": kind === "open" ? "3 4" : null }, s);
      if (kind === "none") el("circle", { cx: x, cy: y, r: 36, fill: "none", stroke: C.b2 }, s);
      const u = el("use", { href: "#g-" + c.querySelector(".seal").dataset.g, x: x - 18, y: y - 18, width: 36, height: 36 }, s); u.style.color = kind === "closed" ? C.gilt : C.bone; });
  }

  // ------------------------------------------------------------------ wiring it up
  const FIGS = { echo, push, face, memory, light, waning, journey, ledger };
  function drawAll() { $$("[data-fig]").forEach((h) => { try { FIGS[h.dataset.fig] && FIGS[h.dataset.fig](h); } catch (e) { console.error(h.dataset.fig, e); } }); }
  function init() {
    $$(".seal").forEach(seal); dials(); $$("[data-great-seal]").forEach(greatSeal); $$("[data-emblem]").forEach(emblem); cosmos(); drawAll();
    const io = "IntersectionObserver" in window && !REDUCED ? new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { threshold: 0.2 }) : null;
    $$("[data-fig]").forEach((h) => (io ? io.observe(h) : h.classList.add("in")));
    let lastW = innerWidth; addEventListener("resize", () => { if (Math.abs(innerWidth - lastW) > 30) { lastW = innerWidth; drawAll(); $$("[data-fig]").forEach((h) => h.classList.add("in")); } });
    const rail = $("#rail"), railA = $$("#rail a"), plates = railA.map((a) => $(a.getAttribute("href"))), ans = $("#answer");
    const onRail = () => { if (!rail || !plates[0]) return; const y = scrollY + innerHeight * 0.45;
      const top0 = plates[0].getBoundingClientRect().top + scrollY, end = ans.getBoundingClientRect().bottom + scrollY;
      rail.classList.toggle("on", y > top0 && scrollY + innerHeight * 0.3 < end);
      let cur = -1; plates.forEach((p, i) => { if (p.getBoundingClientRect().top + scrollY <= y) cur = i; });
      railA.forEach((a, i) => a.setAttribute("aria-current", String(i === cur && y < ans.getBoundingClientRect().top + scrollY))); };
    addEventListener("scroll", onRail, { passive: true }); onRail();
    const top = $("#top"), menu = $(".menu");
    const onScroll = () => top.classList.toggle("stuck", scrollY > 24); onScroll(); addEventListener("scroll", onScroll, { passive: true });
    menu.addEventListener("click", () => { const o = top.classList.toggle("open"); menu.setAttribute("aria-expanded", o); });
    $$("#nav a").forEach((a) => a.addEventListener("click", () => { top.classList.remove("open"); menu.setAttribute("aria-expanded", "false"); }));
  }
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(init);
})();
