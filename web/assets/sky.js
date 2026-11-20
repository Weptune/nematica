/* NEMATICA, the sky: one fixed, full-screen scene behind the whole page. Its 300 points are the worm's 300
   neurons. They open as the living worm (real positions, real wiring, signals running along it), turn into
   an artificial layered network, and re-form into a new figure for every part of the page as it scrolls:
   the wiring ring, each question's planet sign, the seven-pointed star. Drawn at the screen's own pixel
   density; nothing is a bitmap. Pointer: parallax everywhere, and on the worm, touch a neuron to send a signal. */
(function () {
  "use strict";
  const B = window.NEMATICA_BRAIN, cv = document.getElementById("sky"); if (!B || !cv) return;
  const ctx = cv.getContext("2d"), N = B.names.length, REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const GOLD = [240, 207, 120], BONE = [236, 230, 214], CARM = [255, 79, 126];
  let W = 0, H = 0, DPR = 1;

  // ---------------------------------------------------------------- the wiring
  const order = Array.from({ length: N }, (_, i) => i).sort((a, b) => B.pos[3 * a] - B.pos[3 * b] || B.pos[3 * a + 1] - B.pos[3 * b + 1]);
  const rank = new Uint16Array(N); order.forEach((id, k) => (rank[id] = k));
  const E = B.edges, NE = E.length / 2, deg = new Uint16Array(N), adj = Array.from({ length: N }, () => []);
  for (let k = 0; k < NE; k++) { const a = E[2 * k], b = E[2 * k + 1]; deg[a]++; deg[b]++; adj[a].push(b); adj[b].push(a); }
  // an artificial net: ten layers of thirty units, each wired to three units of the next layer
  const LAYERS = 10, ROWS = 6, COLS = 5, LE = [], lnext = Array.from({ length: N }, () => []);
  for (let k = 0; k < N - ROWS * COLS; k++) { const l = Math.floor(k / 30), w = k % 30, r = Math.floor(w / COLS), c = w % COLS;
    [[r, c], [(r + 1) % ROWS, c], [r, (c + 1) % COLS]].forEach(([r2, c2]) => { const t = (l + 1) * 30 + r2 * COLS + c2; LE.push(order[k], order[t]); lnext[order[k]].push(order[t]); }); }

  // ---------------------------------------------------------------- formations (unit: the figure's half height is about 1)
  let seed = 11; const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
  const F = {}, mk = () => new Float32Array(N * 3);
  { // the worm: real cross-section, body axis stretched so the crowded head opens up
    const f = (F.worm = mk()), x0 = B.pos[3 * order[0]], x1 = B.pos[3 * order[N - 1]];
    for (let i = 0; i < N; i++) { const u = 0.5 * (rank[i] / (N - 1)) + 0.5 * ((B.pos[3 * i] - x0) / (x1 - x0)), tp = 1 - 0.45 * u;
      f[3 * i] = (u - 0.5) * 5.2; f[3 * i + 1] = (B.pos[3 * i + 1] / 20) * 0.4 * tp; f[3 * i + 2] = (B.pos[3 * i + 2] / 12) * 0.4 * tp; } }
  { const f = (F.lattice = mk()); for (let k = 0; k < N; k++) { const i = order[k], l = Math.floor(k / 30), w = k % 30, r = Math.floor(w / COLS), c = w % COLS;
      f[3 * i] = (l - 4.5) * 0.52; f[3 * i + 1] = (r - 2.5) * 0.32; f[3 * i + 2] = (c - 2) * 0.32; } }
  { const f = (F.ring = mk()); for (let k = 0; k < N; k++) { const i = order[k], a = -Math.PI / 2 + 0.15 + (k / N) * (2 * Math.PI - 0.3); f[3 * i] = Math.cos(a); f[3 * i + 1] = -Math.sin(a); f[3 * i + 2] = 0; } }
  { const f = (F.wave = mk()); for (let k = 0; k < N; k++) { const i = order[k]; f[3 * i] = ((k % 30) - 14.5) * 0.2; f[3 * i + 1] = 0; f[3 * i + 2] = (Math.floor(k / 30) - 4.5) * 0.42; } }
  { const f = (F.scatter = mk()); for (let i = 0; i < N; i++) { const a = rnd() * 6.283, z = rnd() * 2 - 1, r = 1.9 * Math.cbrt(rnd()), s = Math.sqrt(1 - z * z); f[3 * i] = r * s * Math.cos(a) * 1.5; f[3 * i + 1] = r * s * Math.sin(a); f[3 * i + 2] = r * z; } }
  // figures traced from paths: the seven planet signs and the seven-pointed star
  const circ = (cx, cy, r) => `M${cx - r} ${cy}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`;
  let hept = ""; for (let i = 0, k = 0; i < 8; i++, k = (k + 3) % 7) { const a = -Math.PI / 2 + (k / 7) * 2 * Math.PI; hept += (i ? "L" : "M") + (24 + 17 * Math.cos(a)).toFixed(2) + " " + (24 + 17 * Math.sin(a)).toFixed(2); }
  const SIGN = {
    mercury: [circ(24, 22, 8), "M15 5a9 9 0 0 0 18 0", "M24 30v14", "M17 38h14"], mars: [circ(20, 28, 11), "M28 20L41 7", "M30 7h11v11"],
    venus: [circ(24, 17, 10), "M24 27v18", "M16 37h16"], saturn: ["M17 5v26", "M10 12h15", "M17 25c2-7 14-8 15 0 .7 6-6 9-5 15 .4 2.4 2.6 3.4 5 3"],
    sun: [circ(24, 24, 15), circ(24, 24, 4)], moon: ["M31 7a17 17 0 1 0 0 34 13.5 13.5 0 1 1 0-34z"], jupiter: ["M12 14c0-7 11-9 12-1 .7 6-6 12-14 18h28", "M31 9v34"],
    star: [hept, circ(24, 24, 20)],
  };
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.setAttribute("width", 0); svg.setAttribute("height", 0); svg.style.position = "absolute"; document.body.appendChild(svg);
  Object.keys(SIGN).forEach((name) => { const paths = SIGN[name].map((d) => { const p = document.createElementNS(svg.namespaceURI, "path"); p.setAttribute("d", d); svg.appendChild(p); return p; });
    const len = paths.map((p) => p.getTotalLength()), tot = len.reduce((a, b) => a + b, 0), f = (F[name] = mk()); let k = 0;
    paths.forEach((p, j) => { const n = j === paths.length - 1 ? N - k : Math.round((len[j] / tot) * N);
      for (let q = 0; q < n && k < N; q++, k++) { const pt = p.getPointAtLength(((q + 0.5) / n) * len[j]), i = order[k], jit = name === "star" ? 0.006 : 0.014;
        f[3 * i] = (pt.x - 24) / 20 + (rnd() - 0.5) * jit; f[3 * i + 1] = -(pt.y - 24) / 20 + (rnd() - 0.5) * jit; f[3 * i + 2] = (rnd() - 0.5) * 0.05; } }); });
  svg.remove();

  // ---------------------------------------------------------------- scenes: a formation, how it moves, where it sits, what shows
  const wide = () => W > 900;
  // each sign shines in its planet's metal: quicksilver, iron, copper, lead, gold, silver, tin
  const METAL = { mercury: [196, 222, 255], mars: [255, 122, 92], venus: [255, 170, 118], saturn: [176, 190, 214], sun: [255, 214, 110], moon: [226, 234, 250], jupiter: [214, 226, 236] };
  const sign = (name) => ({ tint: METAL[name], f: F[name], def: (i, p, t, o) => { o[0] = p[0]; o[1] = p[1]; o[2] = p[2] + 0.025 * Math.sin(t * 1.2 + i); },
    rot: (t) => [0.12 * Math.sin(t * 0.37), 0.5 * Math.sin(t * 0.45)], at: () => (wide() ? [0.76, 0.5, H * 0.3] : [0.5, 0.3, Math.min(W, H) * 0.22]), edge: 0, lat: 0, col: 0, dim: wide() ? 1 : 0.5, pt: 1.5, chain: 1 });
  const SC = {
    worm: { f: F.worm, def: (i, p, t, o) => { const u = p[0] / 5.2 + 0.5, a = t * 0.3, c = Math.cos(a), s = Math.sin(a), ph = 6.283 * 1.3 * u - t * 1.0, A = 0.38 * (0.3 + 0.7 * u);
        o[0] = p[0]; o[1] = p[1] * c - p[2] * s + A * Math.sin(ph); o[2] = p[1] * s + p[2] * c + 0.3 * Math.cos(ph) * (0.3 + 0.7 * u); },
      rot: (t) => [0.14 + 0.05 * Math.sin(t * 0.2), 0.16 * Math.sin(t * 0.13)], at: () => [0.5, wide() ? 0.62 : 0.56, Math.min((W * 0.86) / 5.2, H * 0.34)], edge: 1, lat: 0, col: 0, dim: 1 },
    lattice: { f: F.lattice, def: (i, p, t, o) => { o[0] = p[0]; o[1] = p[1]; o[2] = p[2]; }, rot: (t) => [0.2, 0.44 * Math.sin(t * 0.22)],
      at: () => [0.5, wide() ? 0.6 : 0.56, Math.min((W * 0.72) / 5.4, H * 0.24)], edge: 0, lat: 1, col: 1, dim: 1 },
    ring: { f: F.ring, def: (i, p, t, o) => { const a = t * 0.03, c = Math.cos(a), s = Math.sin(a); o[0] = p[0] * c - p[1] * s; o[1] = p[0] * s + p[1] * c; o[2] = 0; },
      rot: (t) => [1.0 + 0.05 * Math.sin(t * 0.3), 0.12 * Math.sin(t * 0.2)], at: () => [0.5, 0.4, Math.min(W * 0.3, H * 0.5)], edge: 1.5, lat: 0, col: 0, dim: 1, longK: 0.9 },
    wave: { f: F.wave, def: (i, p, t, o) => { o[0] = p[0]; o[1] = 0.16 * Math.sin(p[0] * 1.6 + t * 0.8) + 0.12 * Math.sin(p[2] * 2.3 + t * 0.55); o[2] = p[2]; },
      rot: () => [0.5, 0], at: () => [0.5, 0.34, Math.min(W * 0.2, H * 0.36)], edge: 0, lat: 0, col: 0, dim: 0.7 },
    star: { f: F.star, def: (i, p, t, o) => { const a = t * 0.05, c = Math.cos(a), s = Math.sin(a); o[0] = p[0] * c - p[1] * s; o[1] = p[0] * s + p[1] * c; o[2] = p[2]; },
      rot: (t) => [0.3, 0.25 * Math.sin(t * 0.3)], at: () => (wide() ? [0.74, 0.36, H * 0.3] : [0.5, 0.3, Math.min(W, H) * 0.3]), edge: 0, lat: 0, col: 0, dim: 0.9, pt: 1.4, chain: 1 },
    scatter: { f: F.scatter, def: (i, p, t, o) => { o[0] = p[0]; o[1] = p[1] + 0.05 * Math.sin(t * 0.5 + i); o[2] = p[2]; }, rot: (t) => [0.1, t * 0.03], at: () => [0.5, 0.5, Math.min(W, H) * 0.34], edge: 0.12, lat: 0, col: 0, dim: 0.5 },
  };
  ["mercury", "mars", "venus", "saturn", "sun", "moon", "jupiter"].forEach((n) => (SC[n] = sign(n)));

  // ---------------------------------------------------------------- state
  const from = mk(), wp = mk(), sx = new Float32Array(N), sy = new Float32Array(N), sf = new Float32Array(N), en = new Float32Array(N), tin = [0, 0, 0], tmp = [0, 0, 0];
  for (let i = 0; i < N * 3; i++) from[i] = F.scatter[i] * 1.4;
  let scene = null, prev = { edge: 0, lat: 0, col: 0, dim: 0.6, at: [0.5, 0.5, 200], tint: GOLD }, t0 = -1e9, DUR = 2200, heroForm = "worm", heroHold = 0, lastAuto = 0;
  let px = 0, py = 0, tpx = 0, tpy = 0, hoverI = -1, mx = -1e4, my = -1e4, fade = 1, lastPoke = 0;
  const pulses = [];
  const ease = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * u * (u * (6 * u - 15) + 10));
  function go(name, now) {
    if (!SC[name] || scene === name) return;
    if (scene) { const s = SC[scene], g = ease((now - t0) / DUR), a = s.at(); prev = { edge: prev.edge + (s.edge - prev.edge) * g, lat: prev.lat + (s.lat - prev.lat) * g, col: prev.col + (s.col - prev.col) * g, dim: prev.dim + (s.dim - prev.dim) * g, at: prev.at.map((v, k) => v + (a[k] - v) * g), tint: prev.tint.map((v, k) => v + ((s.tint || GOLD)[k] - v) * g) }; }
    if (scene) from.set(wp); scene = name; t0 = now; DUR = REDUCED ? 1 : name === "worm" || name === "lattice" ? 2400 : 1700; pulses.length = 0;
    document.documentElement.dataset.sky = name;
  }
  function poke(i, now, power) {
    en[i] = 1; lastPoke = now; let n = 0;
    const l1 = adj[i].slice().sort(() => rnd() - 0.5).slice(0, 36);
    l1.forEach((j) => { pulses.push({ a: i, b: j, t0: now, d: 460, p: power }); n++;
      adj[j].slice(0, 3).forEach((k) => { if (k !== i && n < 150) { pulses.push({ a: j, b: k, t0: now + 460, d: 460, p: power * 0.6 }); n++; } }); });
  }
  function sweep(now) { let fr = []; for (let q = 0; q < 5; q++) fr.push(order[Math.floor(rnd() * 30)]);
    for (let l = 0; l < LAYERS - 1; l++) { const nx = new Set(); fr.forEach((a) => { if (l === 0) setTimeout(() => (en[a] = 1), 0); lnext[a].forEach((b) => { pulses.push({ a, b, t0: now + l * 300, d: 290, p: 1 }); nx.add(b); }); }); fr = Array.from(nx).slice(0, 14); } }

  // ---------------------------------------------------------------- drawing
  const sprite = (rgb) => { const c = document.createElement("canvas"); c.width = c.height = 128; const g = c.getContext("2d"), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, `rgba(${rgb},.55)`); gr.addColorStop(0.18, `rgba(${rgb},.22)`); gr.addColorStop(0.5, `rgba(${rgb},.06)`); gr.addColorStop(1, `rgba(${rgb},0)`); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); return c; };
  const SP = { gold: sprite(GOLD.join(",")), carm: sprite(CARM.join(",")) }, SPT = {};
  const haloOf = (name) => (SC[name].tint ? SPT[name] || (SPT[name] = sprite(SC[name].tint.join(","))) : SP.gold);
  const STARS = Array.from({ length: 170 }, () => ({ x: rnd(), y: rnd(), z: 0.25 + rnd() * 0.75, s: rnd() }));
  const mixc = (a, b, m) => `${Math.round(a[0] + (b[0] - a[0]) * m)},${Math.round(a[1] + (b[1] - a[1]) * m)},${Math.round(a[2] + (b[2] - a[2]) * m)}`;
  let QUAL = 2, slow = 0, lastT = 0;
  function resize() { DPR = Math.min(QUAL, devicePixelRatio || 1); W = innerWidth; H = innerHeight; cv.width = Math.round(W * DPR); cv.height = Math.round(H * DPR); }
  function lines(list, n, alpha, rgb, lw, longK) {
    if (alpha < 0.012) return; const bk = [new Path2D(), new Path2D(), new Path2D(), new Path2D()], far = Math.max(W, H) * 0.3;
    for (let k = 0; k < n; k++) { const a = list[2 * k], b = list[2 * k + 1], f = (sf[a] + sf[b]) * 0.5, long = Math.abs(sx[a] - sx[b]) + Math.abs(sy[a] - sy[b]) > far, q = long ? 3 : f < 0.92 ? 0 : f < 1.08 ? 1 : 2; bk[q].moveTo(sx[a], sy[a]); bk[q].lineTo(sx[b], sy[b]); }
    ctx.lineWidth = lw; [0.45, 0.8, 1.25, longK || 0.16].forEach((m, q) => { ctx.strokeStyle = `rgba(${rgb},${(alpha * m).toFixed(3)})`; ctx.stroke(bk[q]); });
  }
  function frame(now) {
    requestAnimationFrame(frame); if (document.hidden) { lastT = 0; return; }
    if (lastT) { slow = now - lastT > 30 ? slow + 1 : Math.max(0, slow - 2); if (slow > 45 && QUAL > 1) { QUAL = QUAL > 1.5 ? 1.5 : 1; slow = 0; resize(); } } lastT = now;   // keep it smooth on slow machines
    const t = REDUCED ? 8 : now / 1000, s = SC[scene]; if (!s) return;
    // which part of the page is on screen decides the figure
    if (scene === "worm" || scene === "lattice") { if (!REDUCED && now > heroHold && now - lastAuto > 9000 && now - t0 > 8000) { lastAuto = now; heroForm = heroForm === "worm" ? "lattice" : "worm"; setHero(heroForm, now, true); } }
    px += (tpx - px) * 0.05; py += (tpy - py) * 0.05;
    const g = ease((now - t0) / DUR), at = s.at(), cx = (prev.at[0] + (at[0] - prev.at[0]) * g) * W, cy = (prev.at[1] + (at[1] - prev.at[1]) * g) * H, S = prev.at[2] + (at[2] - prev.at[2]) * g;
    const edge = prev.edge + (s.edge - prev.edge) * g, lat = prev.lat + (s.lat - prev.lat) * g, col = prev.col + (s.col - prev.col) * g, dim = (prev.dim + (s.dim - prev.dim) * g) * fade;
    const r = s.rot(t), rx = r[0] + py * 0.12, ry = r[1] + px * 0.18, cX = Math.cos(rx), sX = Math.sin(rx), cY = Math.cos(ry), sY = Math.sin(ry), f = s.f;
    for (let i = 0; i < N; i++) {
      tin[0] = f[3 * i]; tin[1] = f[3 * i + 1]; tin[2] = f[3 * i + 2]; s.def(i, tin, t, tmp);
      const x1 = tmp[0] * cY + tmp[2] * sY, z1 = -tmp[0] * sY + tmp[2] * cY, y2 = tmp[1] * cX - z1 * sX, z2 = tmp[1] * sX + z1 * cX;
      const p = ease((now - t0 - (rank[i] / N) * 700) / (DUR - 700));
      const X = (wp[3 * i] = from[3 * i] + (x1 - from[3 * i]) * p), Y = (wp[3 * i + 1] = from[3 * i + 1] + (y2 - from[3 * i + 1]) * p), Z = (wp[3 * i + 2] = from[3 * i + 2] + (z2 - from[3 * i + 2]) * p);
      const pf = 4.2 / (4.2 - Z); sf[i] = pf; sx[i] = cx + X * pf * S; sy[i] = cy - Y * pf * S; en[i] *= 0.965;
    }
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0); ctx.clearRect(0, 0, W, H);
    // far stars, drifting a little with the scroll
    const so = scrollY * 0.06; ctx.fillStyle = `rgb(${BONE.join(",")})`;
    for (const st of STARS) { let y = (st.y * (H + 200) - so * st.z) % (H + 200); if (y < 0) y += H + 200; const tw = REDUCED ? 0.7 : 0.55 + 0.45 * Math.sin(t * (0.6 + st.s) + st.s * 40);
      ctx.globalAlpha = 0.5 * st.z * tw; const d = st.z > 0.85 ? 1.6 : 1; ctx.fillRect(Math.round(st.x * W + px * 14 * st.z), Math.round(y - 100), d, d); }
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "lighter";
    lines(E, NE, 0.2 * edge * dim, mixc(BONE, GOLD, 0.35), 0.6, s.longK);
    lines(LE, LE.length / 2, 0.34 * lat * dim, CARM.join(","), 0.7);
    if (s.chain && g > 0.5) { const pth = new Path2D(), lim = S * 0.11; for (let k = 0; k < N - 1; k++) { const a = order[k], b = order[k + 1]; if (Math.abs(sx[a] - sx[b]) + Math.abs(sy[a] - sy[b]) < lim) { pth.moveTo(sx[a], sy[a]); pth.lineTo(sx[b], sy[b]); } }
      ctx.lineWidth = 1; ctx.strokeStyle = `rgba(${(s.tint || GOLD).join(",")},${(0.42 * (g - 0.5) * 2 * dim).toFixed(3)})`; ctx.stroke(pth); }
    // signals in flight
    const pc = mixc(GOLD, [255, 190, 205], col);
    for (let k = pulses.length - 1; k >= 0; k--) { const q = pulses[k], u = (now - q.t0) / q.d; if (u >= 1) { en[q.b] = Math.max(en[q.b], q.p); pulses.splice(k, 1); continue; } if (u < 0) continue;
      const x = sx[q.a] + (sx[q.b] - sx[q.a]) * u, y = sy[q.a] + (sy[q.b] - sy[q.a]) * u, x0 = sx[q.a] + (sx[q.b] - sx[q.a]) * Math.max(0, u - 0.16), y0 = sy[q.a] + (sy[q.b] - sy[q.a]) * Math.max(0, u - 0.16);
      ctx.strokeStyle = `rgba(${pc},${(0.85 * q.p * dim).toFixed(3)})`; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x, y); ctx.stroke(); }
    // the neurons: a soft halo, then a hard bright core
    const tgt = s.tint || GOLD, tint = [0, 1, 2].map((k) => Math.round(prev.tint[k] + (tgt[k] - prev.tint[k]) * g)), base = mixc(tint, CARM, col), halo0 = haloOf(scene);
    for (let i = 0; i < N; i++) { const pf = sf[i], e = en[i], d = Math.min(1, deg[i] / 45), rr = (1.15 + 1.5 * d + 2.4 * e) * pf * (1 + ((s.pt || 1) - 1) * g) * Math.max(0.55, Math.min(1.2, S / 190)), a = Math.min(1, (0.55 + 0.45 * d + e) * dim) * Math.min(1, Math.max(0.25, (pf - 0.72) * 2.6));
      const h = rr * (5.5 + 5 * e + 2 * d), halo = d > 0.22 || e > 0.04 || s.pt; ctx.globalAlpha = Math.min(1, a * (0.5 + 0.7 * e + 0.35 * d));
      if (!halo) { /* small quiet neurons are a bare point */ } else if (col < 0.98) { ctx.globalAlpha *= 1 - col; ctx.drawImage(halo0, sx[i] - h, sy[i] - h, 2 * h, 2 * h); ctx.globalAlpha = Math.min(1, a * (0.5 + 0.7 * e + 0.35 * d)); }
      if (halo && col > 0.02) { ctx.globalAlpha *= col; ctx.drawImage(SP.carm, sx[i] - h, sy[i] - h, 2 * h, 2 * h); }
      ctx.globalAlpha = a; ctx.fillStyle = e > 0.05 ? `rgb(${mixc(col > 0.5 ? CARM : tint, [255, 250, 235], Math.min(1, e))})` : `rgb(${i % 3 === 0 || d > 0.4 ? base : mixc(BONE, CARM, col * 0.8)})`;
      ctx.beginPath(); ctx.arc(sx[i], sy[i], rr, 0, 6.2832); ctx.fill(); }
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over";
    // a neuron's name under the pointer
    if (scene === "worm" && g > 0.95) { let best = -1, bd = 26 * 26; for (let i = 0; i < N; i++) { const dx = sx[i] - mx, dy = sy[i] - my, q = dx * dx + dy * dy; if (q < bd) { bd = q; best = i; } } hoverI = best;
      if (best >= 0) { ctx.strokeStyle = "rgba(240,207,120,.9)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(sx[best], sy[best], 9, 0, 6.2832); ctx.stroke();
        ctx.font = "italic 500 22px Cormorant, Georgia, serif"; ctx.fillStyle = "#f0cf78"; ctx.textAlign = "center"; ctx.fillText(B.names[best], sx[best], sy[best] - 18); }
      if (!REDUCED && now - lastPoke > 1500 && fade > 0.5) poke(order[Math.floor(Math.pow(rnd(), 1.8) * N)], now, 0.8);
    } else hoverI = -1;
    if (scene === "lattice" && g > 0.9 && !REDUCED && now - lastPoke > 2300) { lastPoke = now; sweep(now); }
  }

  // ---------------------------------------------------------------- the page drives it
  const marks = Array.from(document.querySelectorAll("[data-sky]")), cap = document.getElementById("hero-cap"), words = Array.from(document.querySelectorAll("[data-form]"));
  const CAP = { worm: "The 300 neurons of one worm, where they really sit, wired as they are really wired. Touch one to send a signal.", lattice: "The same 300 units, wired as an artificial network. Signals march one way, layer by layer." };
  function setHero(name, now, auto) { heroForm = name; if (!auto) heroHold = now + 24000; lastAuto = now; words.forEach((w) => w.classList.toggle("on", w.dataset.form === name)); if (cap) cap.textContent = CAP[name];
    if (scene === "worm" || scene === "lattice") go(name, now); }
  function onScroll() { const now = performance.now(), mid = H * 0.5; let hit = null;
    for (const m of marks) { const r = m.getBoundingClientRect(); if (r.top <= mid && r.bottom > mid) hit = m; }
    if (!hit) return; const name = hit.dataset.sky === "hero" ? heroForm : hit.dataset.sky; go(name, now);
    const head = hit.querySelector(".chapter, .opening"), floor = hit.dataset.sky === "ring" ? 0.42 : 0.16;
    if (head) { const r = head.getBoundingClientRect(); fade = Math.max(floor, Math.min(1, (r.bottom - H * 0.12) / (H * 0.5))); } else fade = 1; }
  words.forEach((w) => w.addEventListener("click", () => setHero(w.dataset.form, performance.now(), false)));
  addEventListener("pointermove", (e) => { tpx = (e.clientX / W - 0.5) * 2; tpy = (e.clientY / H - 0.5) * 2; mx = e.clientX; my = e.clientY; }, { passive: true });
  addEventListener("pointerdown", (e) => { if (scene !== "worm" || e.target.closest("a,button,nav,header")) return; mx = e.clientX; my = e.clientY;
    let best = -1, bd = 34 * 34; for (let i = 0; i < N; i++) { const dx = sx[i] - mx, dy = sy[i] - my, q = dx * dx + dy * dy; if (q < bd) { bd = q; best = i; } } if (best >= 0) poke(best, performance.now(), 1); });
  addEventListener("resize", () => { resize(); onScroll(); }); addEventListener("scroll", onScroll, { passive: true });
  resize(); setHero("worm", performance.now(), true); go("worm", performance.now()); onScroll(); requestAnimationFrame(frame);
})();
