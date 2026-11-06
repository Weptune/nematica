/* NEMATICA home: a small network of model neurons, simulated in the browser, seen through a
   circular field of view. You can watch it, or poke it.

   Dynamics (the same family as the project's artificial lab, scaled down): 16 units,
   x <- 0.75 x + 0.25 (W tanh x + b + G gate(x)) + 0.45 noise. W holds two visible links per
   unit. A "quiet" network also has links G that carry signal only when the sending unit is driven
   far beyond its resting range (x > 3.5), which almost never happens at rest (about 0.1% of
   frames) but does when a unit is poked.

   Watching: a linear model (ridge VAR(1) on tanh x) is fitted to 6,000 frames of spontaneous
   activity; its prediction of a poke is the summed impulse response. Poking: the network is run
   twice from the same state with the same noise, once with the kick, and the echo is the summed
   difference over 20 frames. The agreement shown is the correlation, over the other 15 units,
   between the predicted and the measured echo. */
(function () {
  "use strict";

  const N = 16, LEAK = 0.25, Q = 0.45, XTH = 3.5, K = 20, KICK_STEPS = 4, KICK = 4;

  function rng(seed) {
    let a = seed >>> 0;
    return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function gauss(r) { let u = 0; while (!u) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); }

  function makeNet(seed, quiet) {
    const r = rng(seed);
    const W = Array.from({ length: N }, () => new Float64Array(N));
    const G = Array.from({ length: N }, () => new Float64Array(N));
    for (let j = 0; j < N; j++) {
      let k = 0;
      while (k < 2) { const i = Math.floor(r() * N); if (i === j || W[i][j]) continue; W[i][j] = (r() < 0.75 ? 1 : -1) * (0.7 + 0.5 * r()); k++; }
    }
    const b = Array.from({ length: N }, () => -0.2 + 0.4 * r());
    if (quiet) {
      for (let j = 0; j < N; j++) {
        let k = 0;
        while (k < 3) { const i = Math.floor(r() * N); if (i === j || W[i][j] || G[i][j]) continue; G[i][j] = (r() < 0.8 ? 1 : -1) * (3.2 + 1.0 * r()); k++; }
      }
    }
    // positions: a loose ring of ganglia inside the field of view, deterministic
    const pr = rng(9001);
    const pos = [];
    while (pos.length < N) {
      const a = pr() * Math.PI * 2, d = 0.18 + 0.62 * Math.sqrt(pr());
      const p = [Math.cos(a) * d, Math.sin(a) * d];
      if (pos.every((q) => Math.hypot(q[0] - p[0], q[1] - p[1]) > 0.27)) pos.push(p);
    }
    return { W, G, b, quiet, pos };
  }

  function step(net, x, noise, kickUnit) {
    const t = x.map(Math.tanh), y = new Float64Array(N);
    for (let i = 0; i < N; i++) {
      let s = net.b[i];
      const Wi = net.W[i], Gi = net.G[i];
      for (let j = 0; j < N; j++) {
        if (Wi[j]) s += Wi[j] * t[j];
        if (Gi[j] && x[j] > XTH) s += Gi[j] * Math.min((x[j] - XTH) / 2, 1);
      }
      y[i] = (1 - LEAK) * x[i] + LEAK * s + Q * noise[i];
    }
    if (kickUnit != null) y[kickUnit] += KICK;
    return y;
  }

  function invert(M) {
    const n = M.length, a = M.map((r, i) => [...r, ...Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))]);
    for (let c = 0; c < n; c++) {
      let p = c;
      for (let r = c + 1; r < n; r++) if (Math.abs(a[r][c]) > Math.abs(a[p][c])) p = r;
      [a[c], a[p]] = [a[p], a[c]];
      const d = a[c][c];
      for (let k = 0; k < 2 * n; k++) a[c][k] /= d;
      for (let r = 0; r < n; r++) if (r !== c) { const f = a[r][c]; for (let k = 0; k < 2 * n; k++) a[r][k] -= f * a[c][k]; }
    }
    return a.map((r) => r.slice(n));
  }

  function fitWatching(net, seed) {
    const r = rng(seed), T = 6000;
    let x = new Float64Array(N);
    const R = [];
    for (let t = 0; t < T + 200; t++) {
      x = step(net, x, Array.from({ length: N }, () => gauss(r)));
      if (t >= 200) R.push(x.map(Math.tanh));
    }
    const mu = new Float64Array(N);
    R.forEach((v) => v.forEach((z, i) => (mu[i] += z / R.length)));
    const C0 = Array.from({ length: N }, () => new Float64Array(N)), C1 = Array.from({ length: N }, () => new Float64Array(N));
    for (let t = 0; t < R.length - 1; t++) {
      for (let i = 0; i < N; i++) {
        const a = R[t + 1][i] - mu[i], c = R[t][i] - mu[i];
        for (let j = 0; j < N; j++) { const bb = R[t][j] - mu[j]; C0[i][j] += c * bb; C1[i][j] += a * bb; }
      }
    }
    for (let i = 0; i < N; i++) C0[i][i] += 1e-3 * R.length;
    const inv = invert(C0);
    return C1.map((row) => { const o = new Float64Array(N); for (let j = 0; j < N; j++) { let s = 0; for (let k = 0; k < N; k++) s += row[k] * inv[k][j]; o[j] = s; } return o; });
  }

  function predictEcho(A, j) {
    let d = new Float64Array(N);
    const e = new Float64Array(N);
    for (let t = 0; t < K; t++) {
      const nd = new Float64Array(N);
      for (let i = 0; i < N; i++) { let s = 0; for (let k = 0; k < N; k++) s += A[i][k] * d[k]; nd[i] = s; }
      if (t < KICK_STEPS) nd[j] = 0.6;
      d = nd;
      for (let i = 0; i < N; i++) e[i] += d[i];
    }
    return e;
  }

  function corrExcept(a, b, skip) {
    const idx = [...Array(N).keys()].filter((i) => i !== skip);
    const n = idx.length;
    let ma = 0, mb = 0;
    idx.forEach((i) => { ma += a[i] / n; mb += b[i] / n; });
    let s = 0, sa = 0, sb = 0;
    idx.forEach((i) => { s += (a[i] - ma) * (b[i] - mb); sa += (a[i] - ma) ** 2; sb += (b[i] - mb) ** 2; });
    return s / Math.sqrt(sa * sb + 1e-12);
  }

  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  // motion: paused by the visitor, or by a reduced-motion preference; a poke always plays out
  let paused = reduced.matches;
  const motionButtons = [...document.querySelectorAll(".motion")];
  const syncMotion = () => motionButtons.forEach((b) => { b.textContent = paused ? "Play motion" : "Pause motion"; b.setAttribute("aria-pressed", String(paused)); });
  motionButtons.forEach((b) => b.addEventListener("click", () => { paused = !paused; syncMotion(); }));
  syncMotion();

  class Specimen {
    constructor(canvas, opts) {
      this.c = canvas;
      this.ctx = canvas.getContext("2d");
      this.o = Object.assign({ seed: 3, quiet: false, trace: false }, opts);
      this.net = makeNet(this.o.seed, this.o.quiet);
      this.A = fitWatching(this.net, this.o.seed + 100);
      this.r = rng(this.o.seed * 7 + 1);
      this.x = new Float64Array(N);
      for (let t = 0; t < 300; t++) this.x = step(this.net, this.x, this.noise());
      this.shadow = null;
      this.poke = null;
      this.result = null;
      this.resultAt = 0;
      this.glow = new Float64Array(N);
      this.hover = -1;
      this.listeners = [];
      this.resize();
      new ResizeObserver(() => this.resize()).observe(canvas);
      canvas.addEventListener("pointermove", (e) => { this.hover = this.pick(e); canvas.style.cursor = this.hover >= 0 ? "pointer" : "default"; });
      canvas.addEventListener("pointerleave", () => { this.hover = -1; });
      canvas.addEventListener("click", (e) => { const j = this.pick(e); if (j >= 0) this.emit(j); });
    }
    noise() { return Array.from({ length: N }, () => gauss(this.r)); }
    on(fn) { this.listeners.push(fn); }
    emit(j) { this.listeners.forEach((f) => f(j)); }
    resize() {
      const d = Math.min(devicePixelRatio || 1, 2), w = this.c.clientWidth;
      if (!w) return;
      this.c.width = Math.round(w * d); this.c.height = Math.round(w * d);
      this.ctx.setTransform(d, 0, 0, d, 0, 0);
      this.w = w;
      if (this.glow) this.draw(performance.now());
    }
    xy(i) { const R = this.w / 2; return [R + this.net.pos[i][0] * R * 0.86, R + this.net.pos[i][1] * R * 0.86]; }
    pick(e) {
      const b = this.c.getBoundingClientRect(), px = e.clientX - b.left, py = e.clientY - b.top;
      let best = -1, bd = Math.max(22, this.w * 0.07);
      for (let i = 0; i < N; i++) { const [x, y] = this.xy(i); const d = Math.hypot(px - x, py - y); if (d < bd) { bd = d; best = i; } }
      return best;
    }
    stimulate(j) {
      if (this.poke) return false;
      this.shadow = Float64Array.from(this.x);
      this.poke = { j, t: 0, echo: new Float64Array(N), born: performance.now() };
      this.result = null;
      this.o.onStart && this.o.onStart(j);
      return true;
    }
    tick() {
      const nz = this.noise();
      if (this.poke) {
        const p = this.poke;
        this.shadow = step(this.net, this.shadow, nz);
        this.x = step(this.net, this.x, nz, p.t < KICK_STEPS ? p.j : null);
        for (let i = 0; i < N; i++) p.echo[i] += Math.tanh(this.x[i]) - Math.tanh(this.shadow[i]);
        p.t++;
        if (p.t >= K) {
          const predicted = predictEcho(this.A, p.j);
          this.result = { j: p.j, measured: p.echo, predicted, r: corrExcept(p.echo, predicted, p.j) };
          this.resultAt = performance.now();
          this.poke = null;
          this.o.onEcho && this.o.onEcho(this.result);
        }
      } else {
        this.x = step(this.net, this.x, nz);
      }
    }
    /* geometry that never changes for a given size: each link is a gently curved neurite */
    curve(j, i) {
      const [x1, y1] = this.xy(j), [x2, y2] = this.xy(i);
      const h = Math.sin((j * 31 + i * 17 + this.o.seed) * 12.9898) * 43758.5453, f = h - Math.floor(h);
      const bend = (f - 0.5) * 0.5, mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
      return [x1, y1, mx - (y2 - y1) * bend, my + (x2 - x1) * bend, x2, y2];
    }
    at(c, t) {
      const u = 1 - t;
      return [u * u * c[0] + 2 * u * t * c[2] + t * t * c[4], u * u * c[1] + 2 * u * t * c[3] + t * t * c[5]];
    }
    path(g, c) { g.beginPath(); g.moveTo(c[0], c[1]); g.quadraticCurveTo(c[2], c[3], c[4], c[5]); }
    /* the still layer: tissue background, out-of-focus cells, neuropil, the neurites and somata outlines */
    still() {
      const w = this.w, R = w / 2, d = Math.min(devicePixelRatio || 1, 2);
      const key = `${w}x${d}`;
      if (this._stillKey === key) return this._still;
      const cv = document.createElement("canvas");
      cv.width = Math.round(w * d); cv.height = Math.round(w * d);
      const g = cv.getContext("2d");
      g.setTransform(d, 0, 0, d, 0, 0);
      const r = rng(4242 + this.o.seed);
      const bg = g.createRadialGradient(R * 0.85, R * 0.75, R * 0.05, R, R, R);
      bg.addColorStop(0, "#0e232b"); bg.addColorStop(0.6, "#08161c"); bg.addColorStop(1, "#03090c");
      g.fillStyle = bg; g.fillRect(0, 0, w, w);
      // out-of-focus cells in other planes: soft, dim discs
      for (let k = 0; k < 70; k++) {
        const x = r() * w, y = r() * w, rr = w * (0.012 + 0.03 * r()), a = 0.025 + 0.06 * r();
        const gr = g.createRadialGradient(x, y, 0, x, y, rr);
        gr.addColorStop(0, `rgba(120,200,170,${a.toFixed(3)})`); gr.addColorStop(1, "rgba(120,200,170,0)");
        g.fillStyle = gr; g.beginPath(); g.arc(x, y, rr, 0, Math.PI * 2); g.fill();
      }
      // neuropil: many faint fibres
      g.lineCap = "round";
      for (let k = 0; k < 140; k++) {
        const x = r() * w, y = r() * w, ang = r() * Math.PI * 2, len = w * (0.08 + 0.25 * r());
        const x2 = x + Math.cos(ang) * len, y2 = y + Math.sin(ang) * len;
        const cx = (x + x2) / 2 + (r() - 0.5) * len * 0.6, cy = (y + y2) / 2 + (r() - 0.5) * len * 0.6;
        g.strokeStyle = `rgba(150,210,190,${(0.025 + 0.04 * r()).toFixed(3)})`; g.lineWidth = 0.4 + 0.7 * r();
        g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(cx, cy, x2, y2); g.stroke();
      }
      // this network's neurites, with short side branches
      for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
        if (!this.net.W[i][j]) continue;
        const c = this.curve(j, i);
        g.strokeStyle = "rgba(168,224,204,0.16)"; g.lineWidth = 1.2; this.path(g, c); g.stroke();
        for (const t of [0.3, 0.62]) {
          const [bx, by] = this.at(c, t), ang = r() * Math.PI * 2, len = w * (0.015 + 0.025 * r());
          g.strokeStyle = "rgba(168,224,204,0.09)"; g.lineWidth = 0.7;
          g.beginPath(); g.moveTo(bx, by); g.quadraticCurveTo(bx + Math.cos(ang + 0.6) * len * 0.6, by + Math.sin(ang + 0.6) * len * 0.6, bx + Math.cos(ang) * len, by + Math.sin(ang) * len); g.stroke();
        }
      }
      // silent links: barely visible dashed paths until they carry signal
      if (this.o.quiet) for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
        if (!this.net.G[i][j]) continue;
        g.setLineDash([2, 5]); g.strokeStyle = "rgba(255,200,96,0.10)"; g.lineWidth = 1;
        this.path(g, this.curve(j, i)); g.stroke(); g.setLineDash([]);
      }
      // fine grain
      const img = g.getImageData(0, 0, cv.width, cv.height), px = img.data;
      for (let k = 0; k < px.length; k += 4) { const n = (r() - 0.5) * 10; px[k] += n; px[k + 1] += n; px[k + 2] += n; }
      g.putImageData(img, 0, 0);
      // cell shapes: each soma a little different (size, elongation, angle)
      this.shape = Array.from({ length: N }, () => ({ s: 0.8 + 0.45 * r(), e: 1 + 0.35 * r(), a: r() * Math.PI }));
      this._still = cv; this._stillKey = key;
      return cv;
    }
    soma(g, i, x, y, rad, v, ring) {
      const sh = this.shape[i];
      g.save(); g.translate(x, y); g.rotate(sh.a); g.scale(sh.e, 1 / sh.e);
      const r0 = rad * sh.s;
      // fluorescence: the cytoplasm lights up, the nucleus stays darker
      const body = g.createRadialGradient(-r0 * 0.25, -r0 * 0.3, r0 * 0.1, 0, 0, r0);
      body.addColorStop(0, `rgba(${Math.round(90 + 120 * v)},${Math.round(150 + 100 * v)},${Math.round(130 + 80 * v)},${(0.55 + 0.45 * v).toFixed(3)})`);
      body.addColorStop(0.75, `rgba(${Math.round(40 + 90 * v)},${Math.round(110 + 120 * v)},${Math.round(95 + 90 * v)},${(0.5 + 0.45 * v).toFixed(3)})`);
      body.addColorStop(1, `rgba(20,60,50,${(0.4 + 0.3 * v).toFixed(3)})`);
      g.fillStyle = body; g.beginPath(); g.arc(0, 0, r0, 0, Math.PI * 2); g.fill();
      g.fillStyle = `rgba(6,20,22,${(0.35 + 0.25 * v).toFixed(3)})`;
      g.beginPath(); g.arc(r0 * 0.12, r0 * 0.08, r0 * 0.42, 0, Math.PI * 2); g.fill();
      g.strokeStyle = `rgba(190,255,228,${(0.18 + 0.5 * v).toFixed(3)})`; g.lineWidth = 0.8 / sh.s;
      g.beginPath(); g.arc(0, 0, r0, 0, Math.PI * 2); g.stroke();
      g.restore();
      if (ring) {
        g.strokeStyle = "rgba(255,255,255,0.85)"; g.lineWidth = 1.25;
        g.beginPath(); g.arc(x, y, rad * 1.9, 0, Math.PI * 2); g.stroke();
      }
    }
    draw(now) {
      if (!this.w) return;
      const g = this.ctx, w = this.w, R = w / 2;
      g.clearRect(0, 0, w, w);
      g.save();
      g.beginPath(); g.arc(R, R, R - 1, 0, Math.PI * 2); g.clip();
      g.drawImage(this.still(), 0, 0, w, w);
      const rad = Math.max(5, w * 0.024);
      for (let i = 0; i < N; i++) {
        const a = (Math.tanh(this.x[i]) + 1) / 2;
        this.glow[i] += (a - this.glow[i]) * 0.3;
      }
      g.globalCompositeOperation = "lighter";
      g.lineCap = "round";
      // active neurites brighten with their sending cell
      for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
        if (!this.net.W[i][j]) continue;
        const v = Math.max(0, this.glow[j] - 0.45) / 0.55;
        if (v < 0.04) continue;
        g.strokeStyle = `rgba(90,230,170,${(0.22 * v).toFixed(3)})`; g.lineWidth = 1.4;
        this.path(g, this.curve(j, i)); g.stroke();
      }
      // signal travelling along neurites
      this.sparks = this.sparks || [];
      if (!reduced.matches) {
        if (!paused || this.poke) for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
          if (!this.net.W[i][j]) continue;
          const v = Math.max(0, this.glow[j] - 0.55);
          if (Math.random() < v * 0.04) this.sparks.push({ c: this.curve(j, i), t: 0, s: 0.012 + 0.01 * Math.random() });
        }
        this.sparks = this.sparks.filter((sp) => (sp.t += sp.s) < 1);
        for (const sp of this.sparks) {
          const [x, y] = this.at(sp.c, sp.t), al = Math.sin(Math.PI * sp.t);
          const gr = g.createRadialGradient(x, y, 0, x, y, rad * 0.9);
          gr.addColorStop(0, `rgba(170,255,220,${(0.8 * al).toFixed(3)})`); gr.addColorStop(1, "rgba(170,255,220,0)");
          g.fillStyle = gr; g.beginPath(); g.arc(x, y, rad * 0.9, 0, Math.PI * 2); g.fill();
        }
      }
      // links that are silent at rest show, in amber, only while they carry signal
      if (this.o.quiet) for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
        if (!this.net.G[i][j] || this.x[j] <= XTH) continue;
        const a = Math.min((this.x[j] - XTH) / 2, 1);
        g.strokeStyle = `rgba(255,190,90,${(0.35 + 0.6 * a).toFixed(3)})`; g.lineWidth = 2.2;
        this.path(g, this.curve(j, i)); g.stroke();
      }
      const p = this.poke, res = this.result;
      // where the signal went: arcs from the poked neuron to its strongest responders, fading
      if (this.o.trace && res) {
        const age = (now - this.resultAt) / 1000, fade = Math.max(0, 1 - age / 3);
        if (fade > 0) {
          const ranked = [...Array(N).keys()].filter((i) => i !== res.j).sort((a, b) => Math.abs(res.measured[b]) - Math.abs(res.measured[a])).slice(0, 4);
          const top = Math.abs(res.measured[ranked[0]]) || 1;
          ranked.forEach((i) => {
            const s = Math.abs(res.measured[i]) / top, c = this.curve(res.j, i);
            g.strokeStyle = `rgba(150,246,204,${(0.7 * s * fade).toFixed(3)})`; g.lineWidth = 1 + 2.5 * s;
            this.path(g, c); g.stroke();
          });
        }
      }
      // halos
      for (let i = 0; i < N; i++) {
        const [x, y] = this.xy(i), v = this.glow[i], hr = rad * (1.5 + 1.6 * v * v);
        const halo = g.createRadialGradient(x, y, rad * 0.4, x, y, hr);
        halo.addColorStop(0, `rgba(60,220,160,${(0.38 * v * v).toFixed(3)})`); halo.addColorStop(1, "rgba(60,220,160,0)");
        g.fillStyle = halo; g.beginPath(); g.arc(x, y, hr, 0, Math.PI * 2); g.fill();
      }
      g.globalCompositeOperation = "source-over";
      if (p && !reduced.matches) {
        const [px, py] = this.xy(p.j), age = (now - p.born) / 1000;
        for (let k = 0; k < 3; k++) {
          const rr = (age * 0.9 + k * 0.25) % 1;
          g.strokeStyle = `rgba(200,255,235,${(0.3 * (1 - rr)).toFixed(3)})`; g.lineWidth = 1.25;
          g.beginPath(); g.arc(px, py, 8 + rr * R * 0.9, 0, Math.PI * 2); g.stroke();
        }
      }
      for (let i = 0; i < N; i++) {
        const [x, y] = this.xy(i);
        this.soma(g, i, x, y, rad, this.glow[i], i === this.hover || (p && p.j === i) || (res && res.j === i));
      }
      // the objective's field: darker towards the edge
      const vg = g.createRadialGradient(R, R, R * 0.62, R, R, R);
      vg.addColorStop(0, "rgba(0,0,0,0)"); vg.addColorStop(1, "rgba(0,0,0,0.55)");
      g.fillStyle = vg; g.fillRect(0, 0, w, w);
      g.restore();
      g.strokeStyle = "rgba(19,33,42,0.85)"; g.lineWidth = 1; g.beginPath(); g.arc(R, R, R - 1, 0, Math.PI * 2); g.stroke();
    }
  }

  /* --- the loop: a scope advances while visible, and while not paused (a poke always plays out) */
  const loops = [];
  let last = 0;
  function frame(now) {
    if (now - last > 110) {
      loops.forEach((s) => { if (s.visible && (!paused || s.poke)) s.tick(); });
      last = now;
    }
    loops.forEach((s) => { if (s.visible && (!paused || s.poke || s.result)) s.draw(now); });
    requestAnimationFrame(frame);
  }
  function register(s) {
    s.visible = false;
    s.draw(performance.now());
    new IntersectionObserver((es) => es.forEach((e) => (s.visible = e.isIntersecting))).observe(s.c);
    loops.push(s);
  }

  // the hero: one network; switch on a neuron and see where its signal goes
  const heroCanvas = document.getElementById("hero-fov");
  if (heroCanvas) {
    const live = document.getElementById("hero-live");
    const hero = new Specimen(heroCanvas, {
      seed: 3, trace: true,
      onEcho: (res) => { if (live) live.textContent = `Neuron ${res.j + 1} was switched on; the lines show the four neurons its signal reached most.`; },
    });
    register(hero);
    const order = [5, 11, 2, 8, 14, 0, 9, 12];
    let next = 0;
    const go = (j) => { if (hero.stimulate(j) && live) live.textContent = `Switching on neuron ${j + 1}.`; };
    const btn = document.getElementById("hero-poke");
    btn && btn.addEventListener("click", () => go(order[next++ % order.length]));
    hero.on(go);
  }

  // the comparison: the same visible wiring; on the right, extra links that are silent at rest
  const left = document.getElementById("fov-plain"), right = document.getElementById("fov-quiet");
  if (left && right) {
    const live = document.getElementById("compare-live");
    const btn = document.getElementById("compare-poke");
    const tally = { plain: [], quiet: [] };
    const done = { plain: null, quiet: null };
    const box = { plain: document.getElementById("score-plain"), quiet: document.getElementById("score-quiet") };
    const show = (key, res) => {
      tally[key].push(res.r);
      done[key] = res;
      const el = box[key], n = tally[key].length, mean = tally[key].reduce((a, b) => a + b, 0) / n;
      el.querySelector(".now").textContent = res.r.toFixed(2);
      el.querySelector(".now").classList.remove("idle");
      el.querySelector(".meter i").style.setProperty("--v", Math.max(0, res.r).toFixed(3));
      el.querySelector(".avg").textContent = n > 1 ? `Average over ${n} pokes: ${mean.toFixed(2)}` : "Poke more neurons to build an average.";
      drawStrip(el.parentElement.querySelector(".echo"), res);
      if (done.plain && done.quiet) {
        if (live) live.textContent = `Neuron ${res.j + 1} poked. Watching predicted the echo at ${done.plain.r.toFixed(2)} in the network with every link active, and at ${done.quiet.r.toFixed(2)} in the network with silent links.`;
        if (btn) btn.disabled = false;
        done.plain = done.quiet = null;
      }
    };
    const start = () => {
      Object.values(box).forEach((el) => { const n = el.querySelector(".now"); n.textContent = "measuring"; n.classList.add("idle"); });
      if (btn) btn.disabled = true;
    };
    const a = new Specimen(left, { seed: 11, quiet: false, onEcho: (r) => show("plain", r) });
    const b = new Specimen(right, { seed: 11, quiet: true, onEcho: (r) => show("quiet", r) });
    register(a); register(b);
    const both = (j) => { if (a.poke || b.poke) return; start(); a.stimulate(j); b.stimulate(j); };
    a.on(both); b.on(both);
    const order = [4, 9, 1, 13, 6, 15, 3, 10, 7, 0];
    let next = 0;
    btn && btn.addEventListener("click", () => both(order[next++ % order.length]));
    const seen = new IntersectionObserver((es) => {
      if (es.some((e) => e.isIntersecting)) { seen.disconnect(); setTimeout(() => { if (!a.result && !a.poke) both(order[next++]); }, 900); }
    }, { threshold: 0.6 });
    seen.observe(left);
  }

  // the echo strip: each other neuron's measured echo (bar) beside what watching predicted (tick),
  // sorted by the measured echo, each scaled to its own largest value
  function drawStrip(svg, res) {
    if (!svg) return;
    const others = [...Array(N).keys()].filter((i) => i !== res.j).sort((p, q) => res.measured[q] - res.measured[p]);
    const mMax = Math.max(...others.map((i) => Math.abs(res.measured[i]))) || 1;
    const pMax = Math.max(...others.map((i) => Math.abs(res.predicted[i]))) || 1;
    const W = 300, H = 76, mid = 38, bw = W / others.length;
    let out = `<line x1="0" x2="${W}" y1="${mid}" y2="${mid}" class="base"/>`;
    others.forEach((i, k) => {
      const m = (res.measured[i] / mMax) * 32, q = (res.predicted[i] / pMax) * 32, x = k * bw + bw * 0.18, w = bw * 0.64;
      out += `<rect x="${x.toFixed(1)}" y="${(m > 0 ? mid - m : mid).toFixed(1)}" width="${w.toFixed(1)}" height="${Math.abs(m).toFixed(1)}" class="m"/>`;
      out += `<line x1="${(x - 2).toFixed(1)}" x2="${(x + w + 2).toFixed(1)}" y1="${(mid - q).toFixed(1)}" y2="${(mid - q).toFixed(1)}" class="p"/>`;
    });
    svg.innerHTML = out;
  }

  // the question's pair: neurons in a worm (most in the head) and units of an artificial network
  const cells = document.querySelector(".pair .cells"), units = document.querySelector(".pair .units");
  if (cells && units) {
    const r = rng(42), NS = "http://www.w3.org/2000/svg";
    const dot = (g, cx, cy, rr) => { const c = document.createElementNS(NS, "circle"); c.setAttribute("cx", cx.toFixed(1)); c.setAttribute("cy", cy.toFixed(1)); c.setAttribute("r", rr); g.appendChild(c); };
    // one centreline drives both the body outline and where the neurons sit, so every cell is inside the worm
    const X0 = 22, L = 300;
    const yc = (u) => 100 + 13 * Math.sin(u * Math.PI * 2.1 + 0.5);
    const hw = (u) => Math.max(0.8, 11.5 * (u < 0.3 ? Math.pow(u / 0.3, 0.75) : 1) * (u > 0.9 ? Math.sqrt(Math.max(0, 1 - ((u - 0.9) / 0.1) ** 2)) : 1));
    const at = (u, s) => { // a point at fraction u along the body, s in [-1, 1] across it
      const x = X0 + u * L, d = (yc(u + 0.002) - yc(u - 0.002)) / (0.004 * L), n = Math.hypot(1, d);
      return [x - (d / n) * s * hw(u), yc(u) + (1 / n) * s * hw(u)];
    };
    const worm = document.querySelector(".pair .worm");
    if (worm) {
      const top = [], bot = [];
      for (let k = 0; k <= 120; k++) { const u = k / 120; top.push(at(u, -1)); bot.push(at(u, 1)); }
      const pts = top.concat(bot.reverse());
      worm.setAttribute("d", "M" + pts.map((p) => p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" L") + " Z");
    }
    const el = (g, tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); g.appendChild(e); return e; };
    const line = (u0, u1, side, cls) => { // a nerve cord running along the body
      const pts = []; for (let k = 0; k <= 60; k++) pts.push(at(u0 + (u1 - u0) * k / 60, side));
      el(cells, "path", { d: "M" + pts.map((q) => q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" L"), class: cls });
    };
    line(0.08, 0.86, 0.42, "cord");                       // ventral nerve cord
    line(0.12, 0.84, -0.48, "cord faint");                // dorsal cord
    // the pharynx: two muscular bulbs in the head, which the nerve ring wraps around
    [[0.905, 5.2, 3.6], [0.955, 4.2, 3.4]].forEach(([u, rx, ry]) => {
      const [x, y] = at(u, 0), ang = Math.atan2(yc(u + 0.002) - yc(u - 0.002), 0.004 * L) * 180 / Math.PI;
      el(cells, "ellipse", { cx: x.toFixed(1), cy: y.toFixed(1), rx, ry, transform: `rotate(${ang.toFixed(1)} ${x.toFixed(1)} ${y.toFixed(1)})`, class: "bulb" });
    });
    const cell = (u, sd, rr, op) => { const [x, y] = at(u, sd); el(cells, "circle", { cx: x.toFixed(1), cy: y.toFixed(1), r: rr.toFixed(2), opacity: op.toFixed(2) }); };
    for (let k = 0; k < 90; k++) { const u = 0.835 + Math.pow(r(), 1.4) * 0.07, sd = (r() * 2 - 1) * 0.78; cell(u, sd, 0.9 + r() * 1.0, 0.55 + 0.45 * r()); } // nerve ring and head ganglia
    for (let k = 0; k < 30; k++) cell(0.12 + (k + r() * 0.7) / 30 * 0.7, 0.42 + (r() - 0.5) * 0.18, 0.9 + r() * 0.6, 0.5 + 0.5 * r()); // ventral cord motor neurons
    for (let k = 0; k < 12; k++) cell(0.05 + r() * 0.07, (r() * 2 - 1) * 0.55, 0.9 + r() * 0.8, 0.6 + 0.4 * r()); // tail ganglia
    // an artificial network: layers of units, every unit linked to the next layer
    const layers = [3, 5, 5, 3], x0 = 382, dx = 34, yMid = 86;
    const ys = layers.map((n) => Array.from({ length: n }, (_, k) => yMid + (k - (n - 1) / 2) * 17));
    for (let l = 0; l < layers.length - 1; l++) ys[l].forEach((y1) => ys[l + 1].forEach((y2) => el(units, "line", { x1: x0 + l * dx, y1, x2: x0 + (l + 1) * dx, y2 })));
    ys.forEach((col, l) => col.forEach((y) => el(units, "circle", { cx: x0 + l * dx, cy: y, r: 4.6 })));
  }

  // the recording schedule schematic: identical poke times in both rows (about 70 pokes in 37 min)
  document.querySelectorAll(".schedule .ticks").forEach((g) => {
    for (let k = 0; k < 70; k++) {
      const x = 22 + k * 4.8, l = document.createElementNS("http://www.w3.org/2000/svg", "line");
      l.setAttribute("x1", x); l.setAttribute("x2", x); l.setAttribute("y1", 0); l.setAttribute("y2", 16);
      g.appendChild(l);
    }
  });

  // the protocol: light the step being read
  const steps = [...document.querySelectorAll(".protocol > li")];
  if (steps.length && "IntersectionObserver" in window) {
    document.querySelector(".protocol").classList.add("tracking");
    const io = new IntersectionObserver((es) => es.forEach((e) => e.target.classList.toggle("is-on", e.isIntersecting)), { rootMargin: "-35% 0px -45% 0px" });
    steps.forEach((li) => io.observe(li));
  }

  requestAnimationFrame(frame);

  // header menu: toggles, closes on a link, on Escape and when the screen widens
  const bar = document.getElementById("bar"), mb = bar && bar.querySelector(".menu"), nav = document.getElementById("nav");
  if (mb && nav) {
    const set = (open) => { bar.classList.toggle("open", open); mb.setAttribute("aria-expanded", String(open)); mb.textContent = open ? "Close" : "Menu"; };
    mb.addEventListener("click", () => set(!bar.classList.contains("open")));
    nav.addEventListener("click", (e) => { if (e.target.closest("a")) set(false); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && bar.classList.contains("open")) { set(false); mb.focus(); } });
  }
})();
