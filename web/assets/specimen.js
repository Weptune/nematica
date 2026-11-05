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

  /* One field of view. opts: seed, quiet, label (aria), onEcho(result) */
  class Specimen {
    constructor(canvas, opts) {
      this.c = canvas;
      this.ctx = canvas.getContext("2d");
      this.o = Object.assign({ seed: 3, quiet: false, palette: "real", showPrediction: false }, opts);
      this.net = makeNet(this.o.seed, this.o.quiet);
      this.A = fitWatching(this.net, this.o.seed + 100);
      this.r = rng(this.o.seed * 7 + 1);
      this.x = new Float64Array(N);
      for (let t = 0; t < 300; t++) this.x = step(this.net, this.x, this.noise());
      this.shadow = null;
      this.poke = null;      // {j, t, echo, ring}
      this.result = null;    // {j, measured, predicted, r}
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
    emit(j) { this.listeners.length ? this.listeners.forEach((f) => f(j)) : this.stimulate(j); }
    resize() {
      const d = Math.min(devicePixelRatio || 1, 2), w = this.c.clientWidth;
      this.c.width = Math.round(w * d); this.c.height = Math.round(w * d);
      this.ctx.setTransform(d, 0, 0, d, 0, 0);
      this.w = w;
      if (this.glow) this.draw(performance.now());
    }
    xy(i) { const R = this.w / 2; return [R + this.net.pos[i][0] * R * 0.86, R + this.net.pos[i][1] * R * 0.86]; }
    pick(e) {
      const b = this.c.getBoundingClientRect(), px = e.clientX - b.left, py = e.clientY - b.top;
      let best = -1, bd = this.w * 0.07;
      for (let i = 0; i < N; i++) { const [x, y] = this.xy(i); const d = Math.hypot(px - x, py - y); if (d < bd) { bd = d; best = i; } }
      return best;
    }
    stimulate(j) {
      this.shadow = Float64Array.from(this.x);
      this.poke = { j, t: 0, echo: new Float64Array(N), born: performance.now() };
      this.result = null;
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
          this.poke = null;
          this.o.onEcho && this.o.onEcho(this.result);
        }
      } else {
        this.x = step(this.net, this.x, nz);
      }
    }
    draw(now) {
      const g = this.ctx, w = this.w, R = w / 2, pal = PALETTES[this.o.palette];
      g.clearRect(0, 0, w, w);
      g.save();
      g.beginPath(); g.arc(R, R, R - 1, 0, Math.PI * 2); g.clip();
      const bg = g.createRadialGradient(R * 0.8, R * 0.7, R * 0.1, R, R, R);
      bg.addColorStop(0, pal.field2); bg.addColorStop(1, pal.field);
      g.fillStyle = bg; g.fillRect(0, 0, w, w);
      // visible wiring, faint
      g.lineWidth = 1;
      for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
        if (!this.net.W[i][j]) continue;
        const [x1, y1] = this.xy(j), [x2, y2] = this.xy(i);
        g.strokeStyle = pal.wire; g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke();
      }
      // quiet links show only while they carry signal
      if (this.o.quiet) for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
        if (!this.net.G[i][j] || this.x[j] <= XTH) continue;
        const a = Math.min((this.x[j] - XTH) / 2, 1);
        const [x1, y1] = this.xy(j), [x2, y2] = this.xy(i);
        g.strokeStyle = pal.quiet(a); g.lineWidth = 1.6; g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke(); g.lineWidth = 1;
      }
      // poke ripple
      const p = this.poke, res = this.result;
      if (p && !reduced.matches) {
        const [px, py] = this.xy(p.j), age = (now - p.born) / 1000;
        for (let k = 0; k < 3; k++) {
          const rr = (age * 0.9 + k * 0.25) % 1;
          g.strokeStyle = pal.ring(1 - rr); g.lineWidth = 1.5;
          g.beginPath(); g.arc(px, py, 8 + rr * R * 0.9, 0, Math.PI * 2); g.stroke();
        }
        g.lineWidth = 1;
      }
      // neurons
      const rad = Math.max(5, w * 0.022);
      for (let i = 0; i < N; i++) {
        const [x, y] = this.xy(i), a = (Math.tanh(this.x[i]) + 1) / 2;
        this.glow[i] += (a - this.glow[i]) * 0.35;
        const v = this.glow[i];
        const halo = g.createRadialGradient(x, y, 0, x, y, rad * (2.2 + 2.4 * v));
        halo.addColorStop(0, pal.glow(0.55 * v)); halo.addColorStop(1, pal.glow(0));
        g.fillStyle = halo; g.beginPath(); g.arc(x, y, rad * (2.2 + 2.4 * v), 0, Math.PI * 2); g.fill();
        g.fillStyle = pal.body(0.25 + 0.75 * v);
        g.beginPath(); g.arc(x, y, rad, 0, Math.PI * 2); g.fill();
        if (i === this.hover || (p && p.j === i) || (res && res.j === i)) {
          g.strokeStyle = pal.mark; g.lineWidth = 1.5; g.beginPath(); g.arc(x, y, rad + 5, 0, Math.PI * 2); g.stroke(); g.lineWidth = 1;
        }
      }
      // echo readout: measured (filled arc) against watching's prediction (thin ring)
      if (res && this.o.showPrediction) {
        const mMax = Math.max(...res.measured.map((v, i) => (i === res.j ? 0 : Math.abs(v)))) || 1;
        const pMax = Math.max(...res.predicted.map((v, i) => (i === res.j ? 0 : Math.abs(v)))) || 1;
        for (let i = 0; i < N; i++) {
          if (i === res.j) continue;
          const [x, y] = this.xy(i);
          const m = res.measured[i] / mMax, q = res.predicted[i] / pMax;
          arcBar(g, x, y, rad + 9, m, pal.measured, 3.2);
          arcBar(g, x, y, rad + 15, q, pal.predicted, 1.6);
        }
      }
      g.restore();
      // rim
      g.strokeStyle = pal.rim; g.lineWidth = 1; g.beginPath(); g.arc(R, R, R - 1, 0, Math.PI * 2); g.stroke();
    }
  }

  function arcBar(g, x, y, r, v, color, lw) {
    if (Math.abs(v) < 0.04) return;
    g.strokeStyle = color(Math.min(1, Math.abs(v)) * (v < 0 ? 0.55 : 1)); g.lineWidth = lw;
    g.setLineDash(v < 0 ? [2, 2] : []);
    const a0 = -Math.PI / 2;
    g.beginPath(); g.arc(x, y, r, a0, a0 + Math.PI * 2 * Math.min(1, Math.abs(v))); g.stroke();
    g.setLineDash([]); g.lineWidth = 1;
  }

  const rgba = (rgb) => (a) => `rgba(${rgb},${a.toFixed(3)})`;
  const PALETTES = {
    real: {
      field: "#050d11", field2: "#0c1d24", wire: "rgba(168,214,196,0.10)", rim: "rgba(19,33,42,0.85)",
      glow: rgba("70,227,165"), body: rgba("150,246,204"), mark: "rgba(255,255,255,0.85)", ring: (a) => `rgba(255,255,255,${(0.35 * a).toFixed(3)})`,
      quiet: (a) => `rgba(255,214,120,${(0.25 + 0.6 * a).toFixed(3)})`,
      measured: rgba("150,246,204"), predicted: rgba("255,255,255"),
    },
  };

  /* --- page wiring --------------------------------------------------------------------------- */
  const loops = [];
  let last = 0;
  function frame(now) {
    const dt = reduced.matches ? 220 : 110;
    if (now - last > dt) { loops.forEach((s) => { if (s.visible) s.tick(); }); last = now; }
    loops.forEach((s) => { if (s.visible) s.draw(now); });
    requestAnimationFrame(frame);
  }
  function register(s) {
    s.visible = false;
    s.draw(performance.now());
    new IntersectionObserver((es) => es.forEach((e) => (s.visible = e.isIntersecting))).observe(s.c);
    loops.push(s);
  }

  // hero: one network, poke it
  const heroCanvas = document.getElementById("hero-fov");
  if (heroCanvas) {
    const live = document.getElementById("hero-live");
    const hero = new Specimen(heroCanvas, {
      seed: 3, quiet: false,
      onEcho: (res) => { if (live) live.textContent = `Neuron ${res.j + 1} was switched on. Its signal reached the neurons that light up, then faded.`; },
    });
    register(hero);
    let next = 0;
    const btn = document.getElementById("hero-poke");
    btn && btn.addEventListener("click", () => { const j = [5, 11, 2, 8, 14, 0, 9, 12][next++ % 8]; hero.stimulate(j); if (live) live.textContent = `Switching on neuron ${j + 1}.`; });
    hero.on((j) => { hero.stimulate(j); if (live) live.textContent = `Switching on neuron ${j + 1}.`; });
  }

  // the comparison: same visible wiring, one with links that stay quiet at rest
  const left = document.getElementById("fov-plain"), right = document.getElementById("fov-quiet");
  if (left && right) {
    const out = { plain: document.getElementById("score-plain"), quiet: document.getElementById("score-quiet") };
    const tally = { plain: [], quiet: [] };
    const show = (key, res) => {
      tally[key].push(res.r);
      const mean = tally[key].reduce((a, b) => a + b, 0) / tally[key].length;
      out[key].querySelector(".now").textContent = res.r.toFixed(2);
      out[key].querySelector(".avg").textContent = tally[key].length > 1 ? `average of ${tally[key].length} pokes: ${mean.toFixed(2)}` : "poke more neurons to build an average";
      out[key].querySelector(".meter i").style.setProperty("--v", Math.max(0, res.r).toFixed(3));
    };
    const a = new Specimen(left, { seed: 11, quiet: false, showPrediction: true, onEcho: (r) => show("plain", r) });
    const b = new Specimen(right, { seed: 11, quiet: true, showPrediction: true, onEcho: (r) => show("quiet", r) });
    register(a); register(b);
    const both = (j) => { a.stimulate(j); b.stimulate(j); };
    a.on(both); b.on(both);
    let next = 0;
    const order = [4, 9, 1, 13, 6, 15, 3, 10, 7, 0];
    const btn = document.getElementById("compare-poke");
    btn && btn.addEventListener("click", () => both(order[next++ % order.length]));
    // one demonstration poke the first time the pair comes into view, so the scores are not empty
    const seen = new IntersectionObserver((es) => {
      if (es.some((e) => e.isIntersecting)) { seen.disconnect(); setTimeout(() => { if (!a.result && !a.poke) both(order[next++]); }, 900); }
    }, { threshold: 0.6 });
    seen.observe(left);
  }

  // the recording schedule schematic: identical poke times in both rows
  document.querySelectorAll(".schedule .ticks").forEach((g) => {
    for (let x = 78; x <= 356; x += 9.5) {
      const l = document.createElementNS("http://www.w3.org/2000/svg", "line");
      l.setAttribute("x1", x); l.setAttribute("x2", x); l.setAttribute("y1", 0); l.setAttribute("y2", 16);
      g.appendChild(l);
    }
  });

  requestAnimationFrame(frame);

  // header menu
  const bar = document.getElementById("bar"), mb = bar && bar.querySelector(".menu");
  if (mb) mb.addEventListener("click", () => { const open = bar.classList.toggle("open"); mb.setAttribute("aria-expanded", String(open)); mb.textContent = open ? "Close" : "Menu"; });
})();
