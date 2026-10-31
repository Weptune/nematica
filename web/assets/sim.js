/* Simulations: a held-out real worm beside its closed-loop model worm in the same copper arena,
   and a swarm of 32 model worms. Canvas 2D, drawn at device resolution.
   Data: web/data/sim/*.js (local only; python scripts/export_site.py --sims). */
(function () {
  "use strict";
  const SIM = (window.NEMATICA_SIM = window.NEMATICA_SIM || {});
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const LIVE = "#3dd69b", COPY = "#f062b4", COPPER = "#c98546";
  const RBAR = 0.025, EPS = 0.004;
  const radiusAt = (u) => (u <= 0 || u >= 1 ? 0 : (RBAR * 2 * Math.sqrt((EPS + u) * (EPS + 1 - u))) / (1 + 2 * EPS));
  const load = (src) => new Promise((ok, bad) => { const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = bad; document.head.appendChild(s); });
  const fmtT = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  function fit(cv) {
    const r = cv.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1);
    const w = Math.round(r.width * dpr), h = Math.round(r.height * dpr);
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    const g = cv.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { g, W: r.width, H: r.height };
  }
  function ramp(glow) {
    const a = [8, 16, 20], b = [parseInt(glow.slice(1, 3), 16), parseInt(glow.slice(3, 5), 16), parseInt(glow.slice(5, 7), 16)], w = [244, 255, 250];
    const lut = new Uint8ClampedArray(256 * 3);
    for (let q = 0; q < 256; q++) {
      const t = q === 0 ? 0 : Math.max(0, Math.min(1, (q / 255 - 0.12) / 0.8));
      const c = t < 0.75 ? a.map((v, i) => v + (b[i] - v) * Math.pow(t / 0.75, 1.4)) : b.map((v, i) => v + (w[i] - v) * ((t - 0.75) / 0.25) * 0.7);
      lut.set(c, q * 3);
    }
    return lut;
  }
  const LUT = { real: ramp(LIVE), model: ramp(COPY) };

  // ============================================================== twin arenas
  const twin = document.getElementById("twin");
  if (twin) (async function () {
    try { await load("data/sim/index.js"); } catch (e) {
      twin.querySelector(".twin-body").innerHTML = '<div class="scope-empty"><div>The simulations draw from the local data.<br>Run <code>python scripts/export_site.py --sims</code> and reload.</div></div>';
      return;
    }
    const idx = SIM.index;
    const tabs = twin.querySelector(".twin-tabs");
    idx.pairs.forEach((p, i) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "chip-dark"; b.textContent = `Worm ${i + 1}`; b.title = `Held-out worm recorded ${p.uid}`;
      b.setAttribute("aria-pressed", String(i === 0));
      b.addEventListener("click", () => { tabs.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); open(p.id); });
      tabs.appendChild(b);
    });
    const cols = ["real", "model"].map((k) => {
      const col = twin.querySelector(`.twin-col.${k}`);
      return { k, col, stage: col.querySelector("canvas.stage"), raster: col.querySelector("canvas.raster"), state: col.querySelector(".state"),
        dist: col.querySelector(".dist"), labels: col.querySelector(".raster-labels") };
    });
    const playBtn = twin.querySelector(".tw-play"), scrub = twin.querySelector(".tw-scrub"), timeEl = twin.querySelector(".tw-time");
    const speeds = twin.querySelectorAll(".tw-speed button");
    let P = null, t = 0, speed = 4, playing = false, last = 0, dur = 1, lastFrameDrawn = -1;

    async function open(id) {
      if (!SIM[id]) await load(`data/sim/${id}.js`);
      P = SIM[id];
      for (const k of ["real", "model"]) {
        const s = P.sides[k];
        s.A = Float32Array.from(s.angles); s.Pth = Float32Array.from(s.path); s.T = Float64Array.from(s.t);
        const raw = atob(s.levels); s.L = new Uint8Array(raw.length); for (let i = 0; i < raw.length; i++) s.L[i] = raw.charCodeAt(i);
      }
      dur = P.sides.real.T[P.sides.real.n - 1];
      t = Math.min(t, dur);
      scrub.max = String(Math.floor(dur));
      // a few row names beside the raster
      const nC = P.classes.length;
      cols.forEach((c) => {
        c.labels.innerHTML = "";
        const want = ["AVA", "AVE", "RIM", "AIB", "RIB", "AVB", "SMDV", "RME", "ASH"];
        const used = [];
        want.forEach((w) => {
          const r = P.classes.indexOf(w); if (r < 0) return;
          const y = ((r + 0.5) / nC) * 100; if (used.some((u) => Math.abs(u - y) < 9)) return; used.push(y);
          const sp = document.createElement("span"); sp.style.top = y + "%"; sp.textContent = w; c.labels.appendChild(sp);
        });
      });
      lastFrameDrawn = -1;
      draw();
    }

    function frameAt(T, n, time) {
      if (time <= T[0]) return { i: 0, a: 0 };
      if (time >= T[n - 1]) return { i: n - 2, a: 1 };
      let lo = 0, hi = n - 1;
      while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T[m] <= time) lo = m; else hi = m; }
      return { i: lo, a: (time - T[lo]) / (T[lo + 1] - T[lo]) };
    }
    function bodyAt(s, f) {
      const k = s.k, ds = s.length / k, pts = new Float32Array((k + 1) * 2);
      let x = s.Pth[2 * f.i] + f.a * (s.Pth[2 * f.i + 2] - s.Pth[2 * f.i]);
      let y = s.Pth[2 * f.i + 1] + f.a * (s.Pth[2 * f.i + 3] - s.Pth[2 * f.i + 1]);
      pts[0] = x; pts[1] = y;
      for (let j = 0; j < k; j++) {
        let a0 = s.A[f.i * k + j], a1 = s.A[(f.i + 1) * k + j], d = a1 - a0;
        d = ((d + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
        const a = a0 + f.a * d;
        x += ds * Math.cos(a); y += ds * Math.sin(a);
        pts[2 * j + 2] = x; pts[2 * j + 3] = y;
      }
      return pts;
    }

    function drawStage(c, s, f) {
      const { g, W, H } = fit(c.stage);
      const pts = bodyAt(s, f), k = s.k;
      // camera on the body's centre, about 3 mm across
      let mx = 0, my = 0; for (let j = 0; j <= k; j++) { mx += pts[2 * j]; my += pts[2 * j + 1]; } mx /= k + 1; my /= k + 1;
      const sc = Math.min(W, H) / 2.6;
      const X = (x) => W / 2 + (x - mx) * sc, Y = (y) => H / 2 + (y - my) * sc;
      // agar
      const bg = g.createRadialGradient(W / 2, H / 2, 10, W / 2, H / 2, Math.max(W, H) * 0.75);
      bg.addColorStop(0, "#122027"); bg.addColorStop(1, "#091116");
      g.fillStyle = bg; g.fillRect(0, 0, W, H);
      // copper beyond the arena edge
      const cx = X(s.centre[0]), cy = Y(s.centre[1]), R = s.radius * sc;
      g.save();
      g.beginPath(); g.rect(0, 0, W, H); g.arc(cx, cy, R, 0, Math.PI * 2, true); g.fillStyle = "rgba(201, 133, 70, 0.16)"; g.fill("evenodd");
      g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.strokeStyle = "rgba(214, 150, 88, 0.85)"; g.lineWidth = 1.5; g.stroke();
      g.restore();
      // grid, 0.5 mm, very faint
      g.strokeStyle = "rgba(255,255,255,0.035)"; g.lineWidth = 1;
      const step = 0.5 * sc, ox = ((W / 2 - mx * sc) % step + step) % step, oy = ((H / 2 - my * sc) % step + step) % step;
      for (let x = ox; x < W; x += step) { g.beginPath(); g.moveTo(Math.round(x) + 0.5, 0); g.lineTo(Math.round(x) + 0.5, H); g.stroke(); }
      for (let y = oy; y < H; y += step) { g.beginPath(); g.moveTo(0, Math.round(y) + 0.5); g.lineTo(W, Math.round(y) + 0.5); g.stroke(); }
      // trail: the last 90 s of the head
      const col = c.k === "real" ? LIVE : COPY;
      const t0 = Math.max(0, f.i - 150);
      g.lineWidth = 1.5; g.lineCap = "butt"; g.lineJoin = "round";
      for (let i = t0 + 1; i <= f.i; i++) {
        g.strokeStyle = col; g.globalAlpha = 0.05 + 0.5 * ((i - t0) / (f.i - t0 + 1));
        g.beginPath(); g.moveTo(X(s.Pth[2 * i - 2]), Y(s.Pth[2 * i - 1])); g.lineTo(X(s.Pth[2 * i]), Y(s.Pth[2 * i + 1])); g.stroke();
      }
      g.globalAlpha = 1;
      // body: tapered outline
      const left = [], right = [];
      for (let j = 0; j <= k; j++) {
        const jx = Math.min(j + 1, k), jp = Math.max(j - 1, 0);
        let tx = pts[2 * jx] - pts[2 * jp], ty = pts[2 * jx + 1] - pts[2 * jp + 1]; const tl = Math.hypot(tx, ty) || 1; tx /= tl; ty /= tl;
        const r = Math.max(radiusAt(j / k) * 1.15, 0.0015) * sc;
        left.push([X(pts[2 * j]) - ty * r, Y(pts[2 * j + 1]) + tx * r]); right.push([X(pts[2 * j]) + ty * r, Y(pts[2 * j + 1]) - tx * r]);
      }
      g.beginPath(); g.moveTo(left[0][0], left[0][1]);
      left.forEach((p) => g.lineTo(p[0], p[1])); right.reverse().forEach((p) => g.lineTo(p[0], p[1])); g.closePath();
      const bodyGrad = g.createLinearGradient(X(pts[0]), Y(pts[1]), X(pts[2 * k]), Y(pts[2 * k + 1]));
      bodyGrad.addColorStop(0, "#eef4f2"); bodyGrad.addColorStop(1, "#b9c7c4");
      g.fillStyle = bodyGrad; g.fill();
      g.strokeStyle = "rgba(255,255,255,0.35)"; g.lineWidth = 1; g.stroke();
      // the head, where the recorded neurons are, glows with their summed activity
      const fi = Math.min(s.n - 1, Math.round(f.i + f.a)), nC = P.classes.length;
      let act = 0; for (let r = 0; r < nC; r++) act += s.L[r * s.n + fi] / 255; act /= nC;
      const hx = X(pts[2 * 4]), hy = Y(pts[2 * 4 + 1]);
      const glow = g.createRadialGradient(hx, hy, 0, hx, hy, 0.12 * sc);
      glow.addColorStop(0, col + Math.round(80 + 140 * Math.min(1, act * 1.6)).toString(16).padStart(2, "0")); glow.addColorStop(1, col + "00");
      g.fillStyle = glow; g.beginPath(); g.arc(hx, hy, 0.12 * sc, 0, Math.PI * 2); g.fill();
      g.fillStyle = col; g.beginPath(); g.arc(X(pts[0]), Y(pts[1]), 2.6, 0, Math.PI * 2); g.fill();
      // scale bar
      g.fillStyle = "rgba(230,238,240,0.85)"; g.fillRect(16, H - 22, 0.5 * sc, 2);
      g.font = "500 11px 'Schibsted Grotesk', system-ui"; g.fillText("0.5 mm", 16, H - 30);
      // inset: the whole arena, with this worm's path so far
      const iw = Math.min(118, W * 0.26), ix = W - iw - 12, iy = 12, ic = iw / 2, isc = (iw / 2 - 6) / (s.radius + 0.3);
      g.fillStyle = "rgba(6, 13, 16, 0.78)"; g.beginPath(); g.roundRect ? g.roundRect(ix, iy, iw, iw, 8) : g.rect(ix, iy, iw, iw); g.fill();
      g.strokeStyle = "rgba(214, 150, 88, 0.8)"; g.lineWidth = 1; g.beginPath(); g.arc(ix + ic, iy + ic, s.radius * isc, 0, Math.PI * 2); g.stroke();
      g.strokeStyle = col; g.globalAlpha = 0.45; g.lineWidth = 1; g.beginPath();
      for (let i = 0; i <= f.i; i += 2) { const px = ix + ic + (s.Pth[2 * i] - s.centre[0]) * isc, py = iy + ic + (s.Pth[2 * i + 1] - s.centre[1]) * isc; i ? g.lineTo(px, py) : g.moveTo(px, py); }
      g.stroke(); g.globalAlpha = 1;
      g.fillStyle = "#fff"; g.beginPath(); g.arc(ix + ic + (pts[0] - s.centre[0]) * isc, iy + ic + (pts[1] - s.centre[1]) * isc, 2.5, 0, Math.PI * 2); g.fill();
      // state
      const rev = s.reversing[fi];
      c.state.textContent = rev ? "Reversing" : "Forward";
      c.state.classList.toggle("rev", !!rev);
      const dEdge = s.radius - Math.hypot(pts[0] - s.centre[0], pts[1] - s.centre[1]);
      c.dist.textContent = `${Math.max(0, dEdge).toFixed(2)} mm from copper`;
    }

    function drawRaster(c, s, f) {
      const { g, W, H } = fit(c.raster);
      const nC = P.classes.length, span = 200;                  // about two minutes of frames
      const fi = Math.min(s.n - 1, Math.round(f.i + f.a));
      const img = g.createImageData(span, nC), lut = LUT[c.k];
      for (let r = 0; r < nC; r++) for (let q = 0; q < span; q++) {
        const fr = fi - span + 1 + q, o = (r * span + q) * 4;
        const v = fr >= 0 ? s.L[r * s.n + fr] : 0;
        img.data[o] = lut[v * 3]; img.data[o + 1] = lut[v * 3 + 1]; img.data[o + 2] = lut[v * 3 + 2]; img.data[o + 3] = 255;
      }
      const off = c._off || (c._off = document.createElement("canvas")); off.width = span; off.height = nC;
      off.getContext("2d").putImageData(img, 0, 0);
      g.imageSmoothingEnabled = false;
      g.drawImage(off, 0, 0, W, H);
      g.fillStyle = "rgba(255,255,255,0.85)"; g.fillRect(W - 2, 0, 2, H);
      // reversal marks along the top
      g.fillStyle = c.k === "real" ? LIVE : COPY;
      for (let q = 0; q < span; q++) { const fr = fi - span + 1 + q; if (fr >= 0 && s.reversing[fr]) g.fillRect((q / span) * W, 0, W / span + 0.5, 3); }
    }

    function draw() {
      if (!P) return;
      cols.forEach((c) => {
        const s = P.sides[c.k], f = frameAt(s.T, s.n, t);
        drawStage(c, s, f);
        drawRaster(c, s, f);
      });
      scrub.value = String(Math.floor(t));
      scrub.style.setProperty("--p", `${(t / dur) * 100}%`);
      timeEl.textContent = `${fmtT(t)} of ${fmtT(dur)}`;
    }
    function play(on) {
      playing = on; playBtn.textContent = on ? "Pause" : "Play";
      if (on) { last = performance.now(); requestAnimationFrame(tick); }
    }
    function tick(now) {
      if (!playing) return;
      t += ((now - last) / 1000) * speed; last = now;
      if (t >= dur) t = 0;
      draw(); requestAnimationFrame(tick);
    }
    playBtn.addEventListener("click", () => play(!playing));
    scrub.addEventListener("input", () => { t = +scrub.value; draw(); });
    speeds.forEach((b) => b.addEventListener("click", () => { speed = +b.dataset.speed; speeds.forEach((x) => x.setAttribute("aria-pressed", String(x === b))); }));
    addEventListener("resize", () => draw());
    await open(idx.pairs[0].id);
    t = 125; draw();
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting && !reduce && !playing) play(true); if (!e.isIntersecting && playing) play(false); }, { threshold: 0.25 });
    io.observe(twin);
  })();

  // ============================================================== swarm
  const swarm = document.getElementById("swarm");
  if (swarm) (async function () {
    try { await load("data/sim/swarm.js"); } catch (e) {
      swarm.querySelector(".swarm-stage").innerHTML = '<div class="scope-empty"><div>The swarm draws from the local data.<br>Run <code>python scripts/export_site.py --sims</code> and reload.</div></div>';
      return;
    }
    const D = SIM.swarm, cv = swarm.querySelector("canvas"), timeEl = swarm.querySelector(".sw-time"), playBtn = swarm.querySelector(".sw-play");
    const Pn = D.points, seg = D.length_mm / Pn, R = D.radius_mm, dur = D.frames * D.dt;
    let t = 0, playing = false, last = 0;
    const speedBtns = swarm.querySelectorAll(".sw-speed button");
    let speed = 8;
    function draw() {
      const { g, W, H } = fit(cv);
      const f = Math.min(D.frames - 1, Math.floor(t / D.dt));
      const sc = (Math.min(W, H) * 0.47) / (R + 0.9), cx = W / 2, cy = H / 2;
      const X = (x) => cx + x * sc, Y = (y) => cy - y * sc;
      const bg = g.createRadialGradient(cx, cy, 10, cx, cy, Math.max(W, H) * 0.7);
      bg.addColorStop(0, "#122027"); bg.addColorStop(1, "#081014");
      g.fillStyle = bg; g.fillRect(0, 0, W, H);
      g.fillStyle = "rgba(201, 133, 70, 0.14)"; g.beginPath(); g.arc(cx, cy, (R + 0.9) * sc, 0, Math.PI * 2); g.arc(cx, cy, R * sc, 0, Math.PI * 2, true); g.fill();
      g.strokeStyle = "rgba(214, 150, 88, 0.85)"; g.lineWidth = 1.5; g.beginPath(); g.arc(cx, cy, R * sc, 0, Math.PI * 2); g.stroke();
      g.lineCap = "round"; g.lineJoin = "round";
      let rev = 0, touch = 0;
      D.worms.forEach((w) => {
        let x = w.head[2 * f], y = w.head[2 * f + 1];
        const pts = [[x, y]];
        for (let p = 0; p < Pn; p++) { const a = w.angles[f * Pn + p]; x += seg * Math.cos(a); y += seg * Math.sin(a); pts.push([x, y]); }
        const r = w.reversing[f]; if (r) rev++;
        g.strokeStyle = r ? COPY : "#d3dedb"; g.lineWidth = Math.max(2.2, 0.05 * sc);
        g.beginPath(); pts.forEach((p, i) => (i ? g.lineTo(X(p[0]), Y(p[1])) : g.moveTo(X(p[0]), Y(p[1])))); g.stroke();
        g.fillStyle = r ? "#ffd3ea" : "#ffffff"; g.beginPath(); g.arc(X(pts[0][0]), Y(pts[0][1]), Math.max(1.6, 0.03 * sc), 0, Math.PI * 2); g.fill();
        if (w.touch[f]) { touch++; g.strokeStyle = "rgba(255,255,255,0.9)"; g.lineWidth = 1.2; g.beginPath(); g.arc(X(pts[0][0]), Y(pts[0][1]), 7, 0, Math.PI * 2); g.stroke(); }
      });
      g.fillStyle = "rgba(230,238,240,0.85)"; g.fillRect(18, H - 24, 1 * sc, 2);
      g.font = "500 11px 'Schibsted Grotesk', system-ui"; g.fillText("1 mm", 18, H - 32);
      timeEl.textContent = `${fmtT(t)} of ${fmtT(dur)}`;
      swarm.querySelector(".sw-rev").textContent = String(rev);
      swarm.querySelector(".sw-touch").textContent = String(touch);
    }
    function play(on) { playing = on; playBtn.textContent = on ? "Pause" : "Play"; if (on) { last = performance.now(); requestAnimationFrame(tick); } }
    function tick(now) { if (!playing) return; t = (t + ((now - last) / 1000) * speed) % dur; last = now; draw(); requestAnimationFrame(tick); }
    playBtn.addEventListener("click", () => play(!playing));
    speedBtns.forEach((b) => b.addEventListener("click", () => { speed = +b.dataset.speed; speedBtns.forEach((x) => x.setAttribute("aria-pressed", String(x === b))); }));
    addEventListener("resize", draw);
    const s = D.notes && D.notes.summary;
    if (s) {
      const set = (k, v) => { const n = swarm.querySelector(`[data-k="${k}"]`); if (n) n.textContent = v; };
      set("contact", `${Math.round(s.contact * 100)}%`);
      set("cluster", `${Math.round(s.frac_in_cluster * 100)}%`);
      set("rev0", s.rev_per_min_density_0.toFixed(1));
      set("rev2", s["rev_per_min_density_2+"].toFixed(1));
      set("copper", `${Math.round(s.near_copper * 100)}%`);
    }
    t = 120; draw();
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting && !reduce && !playing) play(true); if (!e.isIntersecting && playing) play(false); }, { threshold: 0.25 });
    io.observe(swarm);
  })();
})();
