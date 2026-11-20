/* NEMATICA, the light under the plates. Each data plate on the home page is an SVG of scales, numerals and
   notes lying over a canvas of light: the marks themselves and the glow they throw, the gold dust that fills
   the span between real animals, and light moving along the lines that join what a copy predicted to what
   happened. atlas.js says where things are and what they mean; this file makes them shine. Nothing here
   carries meaning the labels do not, and with this file missing the plates fall back to drawn marks.
   Under reduced motion every layer is painted once, fully lit, and left still. */
(function () {
  "use strict";
  if (!document.createElement("canvas").getContext) return;
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches, TAU = Math.PI * 2, PI = Math.PI;
  const COL = { real: [240, 207, 120], copy: [255, 84, 128], ring: [255, 93, 136], bone: [236, 230, 214], line: [236, 230, 214] };
  const rgba = (c, a) => "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a.toFixed(3) + ")";
  const smooth = (v) => (v <= 0 ? 0 : v >= 1 ? 1 : v * v * (3 - 2 * v));
  const back = (v) => { if (v <= 0) return 0; if (v >= 1) return 1; const c = 2.2, u = v - 1; return 1 + (c + 1) * u * u * u + c * u * u; };   // a little past, then home
  const rnd = (seed) => () => { seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

  // ------------------------------------------------------------------ things painted once and stamped many times
  const SPR = {};
  const sprite = (key, n, paint) => SPR[key] || (SPR[key] = (() => { const c = document.createElement("canvas"); c.width = c.height = n; paint(c.getContext("2d"), n); return c; })());
  const halo = (k) => sprite("h" + k, 160, (g, n) => { const r = g.createRadialGradient(n / 2, n / 2, 0, n / 2, n / 2, n / 2);
    [[0, 0.6], [0.07, 0.4], [0.18, 0.2], [0.36, 0.085], [0.6, 0.028], [0.82, 0.007], [1, 0]].forEach((s) => r.addColorStop(s[0], rgba(COL[k], s[1]))); g.fillStyle = r; g.fillRect(0, 0, n, n); });
  const TONE = { real: ["#fffbee", "#f7dc8f", "#cda033", "#75560b"], copy: ["#ffe6ee", "#ff6a93", "#d2225e", "#640b2c"], bone: ["#ffffff", "#f1ecde", "#bdb6a3", "#666154"] };
  // a mark is a polished bead: lit from the upper left, a little light coming back from below, one spark
  const bead = (k) => sprite("b" + k, 112, (g, n) => { const c = TONE[k], R = n / 2 - 1.5;
    let r = g.createRadialGradient(n * 0.37, n * 0.33, 0, n / 2, n / 2, R); r.addColorStop(0, c[0]); r.addColorStop(0.36, c[1]); r.addColorStop(0.8, c[2]); r.addColorStop(1, c[3]);
    g.beginPath(); g.arc(n / 2, n / 2, R, 0, TAU); g.fillStyle = r; g.fill(); g.save(); g.clip();
    r = g.createRadialGradient(n / 2, n * 0.4, R * 0.74, n / 2, n * 0.4, R * 1.12); r.addColorStop(0, "rgba(255,255,255,0)"); r.addColorStop(1, "rgba(255,255,255,.3)"); g.fillStyle = r; g.fillRect(0, n * 0.56, n, n * 0.44);
    r = g.createRadialGradient(n * 0.35, n * 0.3, 0, n * 0.35, n * 0.3, R * 0.34); r.addColorStop(0, "rgba(255,255,255,.95)"); r.addColorStop(1, "rgba(255,255,255,0)"); g.fillStyle = r; g.fillRect(0, 0, n, n); g.restore(); });
  // a grain of gold dust: a point with a little light round it
  const grain = (k) => sprite("g" + k, 24, (g, n) => { const r = g.createRadialGradient(n / 2, n / 2, 0, n / 2, n / 2, n / 2), c = k === 2 ? [255, 122, 158] : k ? [255, 244, 214] : [246, 204, 104];
    r.addColorStop(0, rgba(c, 1)); r.addColorStop(0.22, rgba(c, 0.85)); r.addColorStop(0.5, rgba(c, 0.2)); r.addColorStop(1, rgba(c, 0)); g.fillStyle = r; g.fillRect(0, 0, n, n); });
  const WASH = [228, 172, 58];
  // the four points a bright light throws
  const cross = (k) => sprite("x" + k, 192, (g, n) => { for (let q = 0; q < 2; q++) { g.save(); g.translate(n / 2, n / 2); g.rotate((q * PI) / 2); g.scale(1, 0.022);
      const r = g.createRadialGradient(0, 0, 0, 0, 0, n / 2); r.addColorStop(0, "rgba(255,255,255,.95)"); r.addColorStop(0.25, rgba(COL[k], 0.6)); r.addColorStop(1, rgba(COL[k], 0)); g.fillStyle = r; g.beginPath(); g.arc(0, 0, n / 2, 0, TAU); g.fill(); g.restore(); } });

  // ------------------------------------------------------------------ the pieces of a layer
  // gold dust between two lines: where real animals sit. A wash, deeper at its edges, and grains that drift and catch the light
  function dust(g, b, t, a) {
    if (a <= 0) return;
    g.globalAlpha = a;
    if (b.arc) { g.beginPath(); g.arc(b.cx, b.cy, b.r1, b.a0, b.a1); g.arc(b.cx, b.cy, b.r0, b.a1, b.a0, true); g.closePath(); g.fillStyle = rgba(WASH, 0.12); g.fill(); }
    else { if (!b.wash) { const w = b.up ? g.createLinearGradient(b.x, 0, b.x + b.w, 0) : g.createLinearGradient(0, b.y, 0, b.y + b.h);
        [[0, 0.24], [0.14, 0.11], [0.5, 0.07], [0.86, 0.11], [1, 0.24]].forEach((s) => w.addColorStop(s[0], rgba(WASH, s[1]))); b.wash = w; }
      g.fillStyle = b.wash; g.fillRect(b.x, b.y, b.w, b.h); }
    const f = b.f, n = b.n, bright = Math.floor(n * 0.08), g0 = grain(0), g1 = grain(1);
    for (let i = 0, k = 0; i < n; i++, k += 5) {
      let u = f[k] + t * f[k + 4]; u -= Math.floor(u); const v = f[k + 1], s = (i < bright ? f[k + 2] * 1.5 : f[k + 2]) * 2.7;
      const tw = Math.sin(t * (0.45 + f[k + 2] * 0.5) + f[k + 3]), al = a * (0.2 + 0.8 * tw * tw) * (0.62 + 0.38 * Math.sin(u * 9 - t * 0.35 + v * 3));
      let x, y; if (b.arc) { const an = b.a0 + (b.a1 - b.a0) * u, r = b.r0 + (b.r1 - b.r0) * v; x = b.cx + r * Math.cos(an); y = b.cy + r * Math.sin(an); }
      else if (b.up) { x = b.x + v * b.w; y = b.y + (1 - u) * b.h; } else { x = b.x + u * b.w; y = b.y + v * b.h; }
      g.globalAlpha = al; g.drawImage(i < bright ? g1 : g0, x - s / 2, y - s / 2, s, s);
    }
  }
  // part of a line of points, from one distance along it to another
  function trace(g, r, a, b) {
    a = Math.max(0, a); b = Math.min(r.len, b); if (b <= a) return false; const P = r.pts, C = r.cum; let on = false; g.beginPath();
    for (let i = 1; i < P.length; i++) { if (C[i] < a) continue; if (C[i - 1] > b) break;
      const sg = C[i] - C[i - 1] || 1, u0 = Math.max(0, (a - C[i - 1]) / sg), u1 = Math.min(1, (b - C[i - 1]) / sg), dx = P[i][0] - P[i - 1][0], dy = P[i][1] - P[i - 1][1];
      if (!on) { g.moveTo(P[i - 1][0] + dx * u0, P[i - 1][1] + dy * u0); on = true; } g.lineTo(P[i - 1][0] + dx * u1, P[i - 1][1] + dy * u1); }
    return on;
  }
  // a curve that glows, with a sheen that passes along it now and then
  function ribbon(g, r, t, A) {
    const gr = smooth((A - r.d) / 1500); if (gr <= 0) return; g.lineJoin = g.lineCap = "round";
    [[20, 0.028], [11, 0.05], [5, 0.085]].forEach((p) => { if (trace(g, r, 0, r.len * gr)) { g.globalAlpha = 1; g.lineWidth = p[0] * r.w; g.strokeStyle = rgba(r.c, p[1]); g.stroke(); } });
    if (REDUCED || gr < 1) return;
    const u = ((((t - r.off) % r.per) + r.per) % r.per) / 2.8; if (u >= 1) return;
    const s = u * r.len * 1.25, fade = Math.sin(PI * Math.min(1, u * 1.02));
    [[0.2, 0, 0.1], [0.13, 0.02, 0.16], [0.07, 0.035, 0.26]].forEach((p) => { if (trace(g, r, s - p[0] * r.len, s - p[1] * r.len)) { g.lineWidth = 2.6 * r.w; g.strokeStyle = rgba([255, 250, 236], p[2] * fade); g.stroke(); } });
  }
  // a curve that is losing something: embers leave it and fall, more of them where it has sunk further
  function shed(g, r, t, A) {
    const a = smooth((A - r.d) / 900); if (a <= 0 || REDUCED) return; const P = r.pts, C = r.cum, im = grain(2);
    for (const e of r.em) { const d = e.u * r.len; let i = 1; while (i < P.length - 1 && C[i] < d) i++;
      const sg = C[i] - C[i - 1] || 1, f = (d - C[i - 1]) / sg, x0 = P[i - 1][0] + (P[i][0] - P[i - 1][0]) * f, y0 = P[i - 1][1] + (P[i][1] - P[i - 1][1]) * f, w = Math.min(1, Math.max(0, (y0 - r.y0) / r.span));
      if (w <= 0.02) continue; const p = (t / e.per + e.off) % 1, y = y0 + p * p * e.fall * (0.4 + 0.6 * w), x = x0 + e.sway * Math.sin(p * 5 + e.off * 9) * p, sz = e.s * (1 - 0.45 * p);
      g.globalAlpha = a * Math.min(1, w * 1.6) * Math.min(1, p * 9) * Math.pow(1 - p, 1.2); g.drawImage(im, x - sz / 2, y - sz / 2, sz, sz); }
  }
  // a line from one mark to another, and now and then a light that runs along it and lands
  function beam(g, b, t, A, now) {
    const gr = smooth((A - b.d) / 520); if (gr <= 0) return;
    const dx = b.x1 - b.x0, dy = b.y1 - b.y0;
    if (!b.grad) { b.grad = g.createLinearGradient(b.x0, b.y0, b.x1, b.y1); b.grad.addColorStop(0, rgba(b.ca, 1)); b.grad.addColorStop(1, rgba(b.cb, 1)); }
    g.strokeStyle = b.grad; g.lineCap = "round"; g.beginPath(); g.moveTo(b.x0, b.y0); g.lineTo(b.x0 + dx * gr, b.y0 + dy * gr);
    if (b.glow) { g.globalAlpha = 0.085 * b.a; g.lineWidth = b.w * 5.5; g.stroke(); }
    g.globalAlpha = b.a; g.lineWidth = b.w; g.stroke();
    if (!b.pulse || REDUCED || gr < 1 || b.len < 12) return;
    const u = ((((t - b.off) % b.per) + b.per) % b.per) / b.run; if (u >= 1) { b.hit = false; return; }
    const e = b.fall ? u * u : u, tl = Math.max(0, e - Math.min(0.4, 64 / b.len)), hx = b.x0 + dx * e, hy = b.y0 + dy * e, tx = b.x0 + dx * tl, ty = b.y0 + dy * tl;
    const tg = g.createLinearGradient(tx, ty, hx, hy); tg.addColorStop(0, "rgba(255,240,206,0)"); tg.addColorStop(0.7, "rgba(255,240,206,.34)"); tg.addColorStop(1, "rgba(255,248,232,.8)");
    g.globalAlpha = Math.min(1, u * 8) * b.glint; g.strokeStyle = tg; g.lineWidth = b.w * 1.6; g.beginPath(); g.moveTo(tx, ty); g.lineTo(hx, hy); g.stroke();
    const hr = 6.5 * b.glint + 2; g.globalAlpha = (1 - e) * 0.9; g.drawImage(halo(b.ka), hx - hr, hy - hr, 2 * hr, 2 * hr); g.globalAlpha = e * 0.9; g.drawImage(halo(b.kb), hx - hr, hy - hr, 2 * hr, 2 * hr);
    if (b.to && u > 0.93 && !b.hit) { b.hit = true; b.to.kick = now; }
  }

  function paint(L, now) {
    const g = L.g, t = REDUCED ? 3.7 : now / 1000, A = REDUCED || L.old ? 1e9 : L.born ? now - L.born : -1;
    g.setTransform(L.dpr, 0, 0, L.dpr, 0, 0); g.clearRect(0, 0, L.w, L.h); if (A < 0) return;
    g.globalCompositeOperation = "lighter";
    for (const b of L.bands) dust(g, b, t, smooth((A - b.d) / 1100));
    for (const r of L.ribbons) ribbon(g, r, t, A);
    for (const r of L.sheds) shed(g, r, t, A);
    for (const b of L.beams) beam(g, b, t, A, now);
    const S = L.stars;
    for (const s of S) {                                        // what each mark throws
      s.a = smooth((A - s.d) / 420); if (s.a <= 0) continue;
      s.h += ((s.hot ? 1 : 0) - s.h) * 0.22; s.fl = Math.exp(-Math.max(0, A - s.d) / 300) * (A < 1e8 ? 1 : 0) + (s.kick ? Math.exp(-(now - s.kick) / 340) * 0.75 : 0);
      if (s.kind === "ring" && s.h < 0.02) continue;
      const R = s.r * (s.kind === "ring" ? 2.6 * s.h : 3.3 * (1 + 0.09 * Math.sin(t * s.om + s.ph)) + 3.2 * s.fl + 1.7 * s.h + (s.wave && !REDUCED ? s.wave * (0.5 + 0.5 * Math.sin(t * 0.8 - s.x * 0.012)) : 0));
      g.globalAlpha = s.a * (s.kind === "ring" ? 0.7 : 0.92); g.drawImage(halo(s.kind), s.x - R, s.y - R, 2 * R, 2 * R);
    }
    g.globalCompositeOperation = "source-over";
    for (const s of S) {                                        // the marks themselves
      if (s.a <= 0) continue; const r = s.r * (A > 1e8 ? 1 : back((A - s.d) / 620)) * (1 + 0.1 * s.h); g.globalAlpha = Math.min(1, s.a * 1.4);
      if (s.kind === "ring") { g.beginPath(); g.arc(s.x, s.y, r, 0, TAU); g.fillStyle = "rgba(6,15,40,.94)"; g.fill(); g.lineWidth = s.r > 6 ? 2 : 1.7; g.strokeStyle = "#ff5d88"; g.stroke();
        g.beginPath(); g.arc(s.x, s.y, r, PI * 1.08, PI * 1.52); g.strokeStyle = "rgba(255,216,228,.92)"; g.lineWidth = 1.1; g.stroke(); }
      else g.drawImage(bead(s.kind), s.x - r, s.y - r, 2 * r, 2 * r);
    }
    g.globalCompositeOperation = "lighter";
    for (const s of S) {                                        // and a glint, now and then
      if (s.a <= 0 || s.kind === "ring") continue; const p = (t / s.per + s.off) % 1, k = Math.max(REDUCED ? 0 : p < 0.09 ? Math.sin((PI * p) / 0.09) * 0.8 : 0, s.h, Math.min(1, s.fl));
      if (k < 0.03) continue; const len = s.r * (2 + 3.4 * k); g.globalAlpha = s.a * k * 0.9; g.drawImage(cross(s.kind), s.x - len, s.y - len, 2 * len, 2 * len);
    }
    g.globalAlpha = 1;
  }

  // ------------------------------------------------------------------ the layers, and one clock for all of them
  const LAYERS = []; let running = false;
  const io = "IntersectionObserver" in window ? new IntersectionObserver((es) => es.forEach((e) => { const L = LAYERS.find((l) => l.cv === e.target); if (L) { L.vis = e.isIntersecting; if (L.vis) kick(); } }), { rootMargin: "140px 0px" }) : null;
  function kick() { if (!running) { running = true; requestAnimationFrame(loop); } }
  function loop(now) {
    let any = false;
    for (let i = LAYERS.length - 1; i >= 0; i--) { const L = LAYERS[i];
      if (!L.cv.isConnected) { LAYERS.splice(i, 1); if (io) io.unobserve(L.cv); continue; }
      if (!L.vis) continue;
      if (!L.born && L.host.closest(".in")) L.born = now;
      paint(L, now); any = true; }
    running = any && !REDUCED; if (running) requestAnimationFrame(loop);
  }

  function layer(host, w, h) {
    const dpr = Math.min(3, window.devicePixelRatio || 1), cv = document.createElement("canvas"); cv.className = "lum"; cv.setAttribute("aria-hidden", "true");
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); host.appendChild(cv);
    const q = rnd(Math.round(w * 31 + h * 17 + LAYERS.length * 101));
    const L = { host, cv, g: cv.getContext("2d"), w, h, dpr, stars: [], beams: [], bands: [], ribbons: [], sheds: [], vis: !io, born: 0, old: !!host.closest(".in") };
    LAYERS.push(L); if (io) io.observe(cv); else kick();
    const grains = (area, long) => { const n = Math.round(Math.min(1500, Math.max(30, area / 44))), f = new Float32Array(n * 5);
      for (let i = 0, k = 0; i < n; i++, k += 5) { f[k] = q(); f[k + 1] = 0.02 + q() * 0.96; f[k + 2] = 0.7 + q() * q() * 1.5; f[k + 3] = q() * TAU; f[k + 4] = (2.5 + q() * 6) / Math.max(40, long); } return { f, n }; };
    return {
      // a mark: kind is real, copy, bone or ring. The thing returned can be told it is under the pointer (hot) or struck (kick)
      // wave: how far its glow swells as a slow wave passes along the plate, in its own radii
      star(kind, x, y, r, delay, wave) { const s = { kind, x, y, r, d: delay || 0, ph: q() * TAU, om: 0.5 + q() * 1.1, per: 7 + q() * 11, off: q(), hot: 0, h: 0, a: 0, fl: 0, kick: 0, wave: wave || 0 }; L.stars.push(s); return s; },
      heat(s, on) { s.hot = on ? 1 : 0; kick(); },
      beam(x0, y0, x1, y1, ka, kb, delay, o) { o = o || {}; const len = Math.hypot(x1 - x0, y1 - y0);
        const b = { x0, y0, x1, y1, ka, kb, ca: COL[ka], cb: COL[kb], d: delay || 0, w: o.w || 1.25, a: o.a == null ? 0.72 : o.a, glow: o.glow !== false, pulse: !!o.pulse, fall: !!o.fall, to: o.to || null,
          off: o.off != null ? o.off : q() * 9, per: o.per || 7, run: o.run || Math.max(0.7, Math.min(1.5, len / 190)), glint: o.glint || 1, len, hit: false }; L.beams.push(b); return b; },
      band(x, y, w2, h2, upright, delay) { const gr = grains(w2 * h2, upright ? h2 : w2); L.bands.push({ x, y, w: w2, h: h2, up: !!upright, d: delay || 0, f: gr.f, n: gr.n }); },
      // the same between two arcs: angles as the canvas counts them
      arcBand(cx, cy, r0, r1, a0, a1, delay) { const gr = grains(Math.abs(a1 - a0) * 0.5 * (r1 * r1 - r0 * r0), Math.abs(a1 - a0) * r1); L.bands.push({ arc: true, cx, cy, r0, r1, a0, a1, d: delay || 0, f: gr.f, n: gr.n }); },
      ribbon(pts, kind, delay, o) { o = o || {}; const cum = [0]; for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
        L.ribbons.push({ pts, cum, len: cum[cum.length - 1], c: COL[kind], d: delay || 0, w: o.w || 1, off: o.off != null ? o.off : q() * 6, per: o.per || 9 }); },
      // embers falling from a curve, wherever it lies below the level y0; thickest where it is span or more below
      shed(pts, y0, span, delay, n) { const cum = [0]; for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
        const em = []; for (let i = 0; i < (n || 90); i++) em.push({ u: Math.sqrt(q()), per: 2.8 + q() * 3.6, off: q(), fall: 34 + q() * 62, sway: (q() - 0.5) * 18, s: 5 + q() * q() * 7.5 });
        L.sheds.push({ pts, cum, len: cum[cum.length - 1], y0, span, d: delay || 0, em }); },
    };
  }
  window.NEMATICA_LUMEN = { layer };
})();
