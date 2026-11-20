/* NEMATICA, the bench: two small networks you can watch and then touch. Both have the same visible wiring;
   the second also has links that stay silent at rest. A model fitted by watching knows only the visible
   links (with a little estimation error), so its predicted echo holds in the first network and fails in
   the second. Everything is simulated here, in the page; nothing is recorded data. Crisp SVG, no blur. */
(function () {
  "use strict";
  const hosts = Array.from(document.querySelectorAll("[data-net]")); if (!hosts.length) return;
  const NS = "http://www.w3.org/2000/svg", REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const C = { bone: "#ece6d6", b3: "rgba(236,230,214,.64)", line: "rgba(236,230,214,.26)", hair: "rgba(236,230,214,.13)", gilt: "#dcbc62", copy: "#e03063" };
  function el(tag, a, p) { const n = document.createElementNS(NS, tag); for (const k in a || {}) if (a[k] != null) n.setAttribute(k, a[k]); if (p) p.appendChild(n); return n; }
  const N = 12;
  const POS = [[200, 66], [296, 102], [340, 196], [302, 294], [214, 340], [116, 308], [62, 214], [94, 118], [178, 150], [252, 188], [206, 252], [138, 216]];
  const VIS = [[0, 8, .7], [8, 9, .6], [9, 2, .7], [1, 9, .5], [9, 10, .6], [10, 4, .7], [10, 11, .5], [11, 6, .6], [7, 8, .6], [8, 11, .5], [11, 5, .6], [3, 10, .5], [2, 3, .6], [5, 4, .4], [6, 7, .5], [1, 0, .5], [4, 3, .4], [7, 11, .5], [3, 2, .4], [5, 6, .5], [0, 1, .4], [6, 11, .4], [4, 10, .4], [2, 1, .5]];
  const SIL = [[0, 3, 1], [2, 6, 1], [5, 1, 1], [7, 4, 1], [9, 5, 1], [11, 2, 1], [4, 0, 1], [6, 9, 1], [1, 7, .9], [3, 8, .9], [8, 5, .9], [10, 7, .9]];
  const mat = (L) => { const W = Array.from({ length: N }, () => new Array(N).fill(0)); L.forEach(([a, b, w]) => (W[b][a] += w)); return W; };
  // the echo of switching on neuron i: three steps of spread, each weaker; also when each neuron is first reached
  function echo(W, i) {
    let v = new Array(N).fill(0); v[i] = 1; const e = new Array(N).fill(0), first = new Array(N).fill(-1); let g = 1;
    for (let h = 0; h < 3; h++) { const nv = new Array(N).fill(0);
      for (let r = 0; r < N; r++) for (let c = 0; c < N; c++) nv[r] += W[r][c] * v[c];
      v = nv; for (let r = 0; r < N; r++) { e[r] += g * v[r]; if (v[r] > 0.08 && first[r] < 0 && r !== i) first[r] = h; } g *= 0.55; }
    e[i] = 0; return { e, first };
  }
  function corr(a, b, skip) { const A = [], Bv = []; for (let i = 0; i < N; i++) if (i !== skip) { A.push(a[i]); Bv.push(b[i]); }
    const m = (x) => x.reduce((s, v) => s + v, 0) / x.length, ma = m(A), mb = m(Bv); let sab = 0, sa = 0, sb = 0;
    A.forEach((v, k) => { sab += (v - ma) * (Bv[k] - mb); sa += (v - ma) ** 2; sb += (Bv[k] - mb) ** 2; }); return sab / Math.sqrt(sa * sb || 1); }
  let seed = 7; const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
  const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-9)) * Math.cos(2 * Math.PI * rnd());
  const Wv = mat(VIS), Wt = mat(VIS.concat(SIL));
  const What = Wv.map((r) => r.map((v) => (v ? v * (1 + 0.15 * gauss()) : rnd() < 0.08 ? 0.08 * gauss() : 0)));   // what watching recovers
  const rad = (e) => (e > 0.04 ? 3.5 + 14 * Math.sqrt(Math.min(1, e / 1.6)) : 0);

  const nets = hosts.map((host) => {
    const quiet = host.dataset.net === "quiet", W = quiet ? Wt : Wv, links = quiet ? VIS.concat(SIL) : VIS;
    const s = el("svg", { viewBox: "0 0 400 400", class: "net", role: "group", "aria-label": quiet ? "A network with some links silent at rest. Select a neuron to poke it." : "A network whose links are all active at rest. Select a neuron to poke it." }); host.appendChild(s);
    el("circle", { cx: 200, cy: 200, r: 188, fill: "none", stroke: C.line }, s); el("circle", { cx: 200, cy: 200, r: 181, fill: "none", stroke: C.hair }, s);
    let tk = ""; for (let i = 0; i < 72; i++) { const a = (i / 72) * 2 * Math.PI, r2 = i % 6 ? 177 : 172; tk += `M${(200 + 181 * Math.cos(a)).toFixed(1)} ${(200 + 181 * Math.sin(a)).toFixed(1)}L${(200 + r2 * Math.cos(a)).toFixed(1)} ${(200 + r2 * Math.sin(a)).toFixed(1)}`; }
    el("path", { d: tk, stroke: C.b3, "stroke-width": .8 }, s);
    const gL = el("g", {}, s), sil = {};
    VIS.forEach(([a, b]) => el("path", { d: `M${POS[a][0]} ${POS[a][1]}L${POS[b][0]} ${POS[b][1]}`, stroke: C.line }, gL));
    if (quiet) SIL.forEach(([a, b]) => { sil[a + ">" + b] = el("path", { d: `M${POS[a][0]} ${POS[a][1]}L${POS[b][0]} ${POS[b][1]}`, stroke: C.gilt, "stroke-width": 1.6, "stroke-dasharray": "5 4", opacity: 0 }, gL); });
    const gP = el("g", {}, s), disc = [], ring = [], dot = [];
    POS.forEach(([x, y], i) => { disc[i] = el("circle", { cx: x, cy: y, r: 0, fill: C.bone }, s); });
    POS.forEach(([x, y], i) => { ring[i] = el("circle", { cx: x, cy: y, r: 0, fill: "none", stroke: C.copy, "stroke-width": 2, opacity: 0 }, s); });
    POS.forEach(([x, y], i) => { dot[i] = el("circle", { cx: x, cy: y, r: 3.6, fill: C.bone }, s); });
    const halo = el("circle", { cx: 0, cy: 0, r: 0, fill: "none", stroke: C.gilt, "stroke-width": 1.5, opacity: 0 }, s);
    POS.forEach(([x, y], i) => { const h = el("circle", { cx: x, cy: y, r: 21, fill: "transparent", class: "n", tabindex: 0, role: "button", "aria-label": `Poke neuron ${i + 1}` }, s);
      h.addEventListener("click", () => poke(i));
      h.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); poke(i); } }); });
    return { quiet, W, links, s, gP, sil, disc, ring, dot, halo, scores: [], key: quiet ? "quiet" : "plain" };
  });

  // moving marks: pulses along links, and radii easing toward targets
  const pulses = [], tweens = [];
  let paused = REDUCED, visible = false, raf = 0, lastRest = 0, pokeAt = -1, nextI = 5;
  function pulse(net, a, b, t0, dur, col, r) { pulses.push({ c: el("circle", { r, fill: col, opacity: 0 }, net.gP), a: POS[a], b: POS[b], t0, dur }); }
  function tween(node, attr, to, t0, dur) { tweens.push({ node, attr, from: +node.getAttribute(attr) || 0, to, t0, dur }); }
  function frame(now) {
    raf = 0;
    for (let k = pulses.length - 1; k >= 0; k--) { const p = pulses[k], u = (now - p.t0) / p.dur;
      if (u >= 1) { p.c.remove(); pulses.splice(k, 1); continue; } if (u < 0) continue;
      p.c.setAttribute("cx", p.a[0] + (p.b[0] - p.a[0]) * u); p.c.setAttribute("cy", p.a[1] + (p.b[1] - p.a[1]) * u); p.c.setAttribute("opacity", 1); }
    for (let k = tweens.length - 1; k >= 0; k--) { const t = tweens[k], u = (now - t.t0) / t.dur; if (u < 0) continue;
      const q = u >= 1 ? 1 : 1 - Math.pow(1 - u, 3); t.node.setAttribute(t.attr, (t.from + (t.to - t.from) * q).toFixed(2)); if (u >= 1) tweens.splice(k, 1); }
    if (!paused && visible && now - lastRest > 260 && now - pokeAt > 2600) { lastRest = now;       // resting activity: only the visible links ever carry it
      nets.forEach((net) => { const [a, b] = VIS[Math.floor(Math.random() * VIS.length)]; pulse(net, a, b, now, 900, C.b3, 1.8);
        tween(net.dot[b], "r", 5, now + 850, 120); tween(net.dot[b], "r", 3.6, now + 1000, 300); }); }
    if (pulses.length || tweens.length || (!paused && visible)) raf = requestAnimationFrame(frame);
  }
  const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };

  function poke(i) {
    const now = performance.now(), inst = paused, HOP = 620; pokeAt = now; nextI = (i + 7) % N;
    const out = {};
    nets.forEach((net) => {
      const tr = echo(net.W, i), pr = echo(What, i), sc = corr(pr.e, tr.e, i);
      net.scores.push(sc); out[net.key] = sc;
      Object.values(net.sil).forEach((l) => l.setAttribute("opacity", 0));
      net.dot.forEach((d, k) => { d.setAttribute("fill", k === i ? C.gilt : C.bone); d.setAttribute("r", k === i ? 6 : 3.6); });
      net.halo.setAttribute("cx", POS[i][0]); net.halo.setAttribute("cy", POS[i][1]);
      if (!inst) { net.halo.setAttribute("r", 6); net.halo.setAttribute("opacity", 1); tween(net.halo, "r", 30, now, 700); tween(net.halo, "opacity", 0, now + 250, 500); }
      // spread: follow real links outward for three steps
      let front = [i]; const seen = new Set([i]);
      for (let h = 0; h < 3; h++) { const nxt = [];
        front.forEach((a) => net.links.forEach(([p, q, w]) => { if (p !== a || q === i) return;
          const silent = net.sil[p + ">" + q];
          if (!inst) pulse(net, p, q, now + h * HOP, HOP - 40, silent ? C.gilt : C.bone, 3);
          if (silent && h < 2) { if (inst) silent.setAttribute("opacity", 1); else tween(silent, "opacity", 1, now + h * HOP, 200); }
          if (!seen.has(q)) { seen.add(q); nxt.push(q); } }));
        front = nxt; }
      for (let k = 0; k < N; k++) { const r = k === i ? 0 : rad(tr.e[k]), rp = k === i ? 0 : rad(pr.e[k]);
        net.ring[k].setAttribute("r", rp ? rp + 2.5 : 0);
        if (inst) { net.disc[k].setAttribute("r", r); net.ring[k].setAttribute("opacity", rp ? 1 : 0); }
        else { net.disc[k].setAttribute("r", 0); net.ring[k].setAttribute("opacity", 0); tween(net.disc[k], "r", r, now + (Math.max(0, tr.first[k]) + 1) * HOP - 60, 380); if (rp) tween(net.ring[k], "opacity", 1, now + 3 * HOP + 150, 450); } }
      const b = document.getElementById("sc-" + net.key), sm = document.getElementById("sn-" + net.key), avg = net.scores.reduce((s, v) => s + v, 0) / net.scores.length;
      const write = () => { b.textContent = sc.toFixed(2).replace("-", "−"); sm.textContent = net.scores.length > 1 ? `average over ${net.scores.length} pokes: ${avg.toFixed(2).replace("-", "−")}` : "1 is a perfect prediction, 0 is none"; };
      if (inst) write(); else { b.textContent = "…"; setTimeout(write, 3 * HOP + 300); }
    });
    const live = document.getElementById("bench-live");
    if (live) live.textContent = `Poked neuron ${i + 1}. Watching predicted the echo at ${out.plain.toFixed(2)} where every link is active at rest, and at ${out.quiet.toFixed(2)} where some links are silent.`;
    kick();
  }

  const btn = document.getElementById("bench-poke"), mo = document.getElementById("bench-motion");
  if (btn) btn.addEventListener("click", () => poke(nextI));
  if (mo) { if (REDUCED) { mo.setAttribute("aria-pressed", "true"); mo.textContent = "Play motion"; }
    mo.addEventListener("click", () => { paused = !paused; mo.setAttribute("aria-pressed", String(paused)); mo.textContent = paused ? "Play motion" : "Pause motion"; kick(); }); }
  new IntersectionObserver((es) => es.forEach((e) => { visible = e.isIntersecting; if (visible) kick(); }), { threshold: 0.15 }).observe(document.getElementById("bench") || hosts[0]);
})();
