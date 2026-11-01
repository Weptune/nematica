/* The opening experiment. A scroll-driven sequence on one canvas:
   1 the whole nervous system assembles, 2 it comes alive with recorded activity,
   3 a copy splits off and flickers just as convincingly, 4 one neuron is switched on in both
   and the echo spreads, 5 the verdict.
   Data (local only): NEMATICA_BRAIN (atlas positions, wiring), NEMATICA_LOCAL (recorded and
   simulated activity), NEMATICA_ECHO (average echoes). */
(function () {
  "use strict";
  const root = document.getElementById("experiment");
  if (!root) return;
  const B = window.NEMATICA_BRAIN, L = window.NEMATICA_LOCAL, E = window.NEMATICA_ECHO;
  const cv = root.querySelector("canvas");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!B || !cv) { root.classList.add("no-data"); return; }

  // ------------------------------------------------------------------ data
  const N = B.names.length;
  const P = new Float32Array(N * 3);
  for (let i = 0; i < N * 3; i++) P[i] = B.pos[i];
  const isHead = new Uint8Array(N);
  for (let i = 0; i < N; i++) isHead[i] = P[3 * i] < 175 ? 1 : 0;
  const edges = B.edges;

  const decodeU8 = (b64) => { const s = atob(b64), a = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) a[i] = s.charCodeAt(i); return a; };
  const decodeI8 = (b64) => { const s = atob(b64), a = new Int8Array(s.length); for (let i = 0; i < s.length; i++) a[i] = (s.charCodeAt(i) << 24) >> 24; return a; };
  // recorded and simulated activity, by class
  let actReal = null, actCopy = null, nT = 1, aRow = new Int16Array(N).fill(-1);
  if (L) {
    nT = L.frames;
    actReal = decodeU8(L.real);
    actCopy = decodeU8(L.brains.var3_spontaneous ? L.brains.var3_spontaneous.data : Object.values(L.brains)[0].data);
    const row = Object.fromEntries(L.classes.map((c, i) => [c, i]));
    for (let i = 0; i < N; i++) aRow[i] = row[B.cls[i]] ?? -1;
  }
  // average echoes after switching on ASH, by class
  let echo = null;
  if (E) {
    const S = E.stims.length, R = E.resp.length, T = E.nt, si = Math.max(0, E.stims.indexOf("ASH"));
    const get = (key) => { const d = decodeI8(E.sets[key]); return (r, t) => { const q = d[(si * R + r) * T + t]; return q === -128 ? NaN : (q / 127) * E.scale; }; };
    const real = get("real"), copy = get("var3_spontaneous");
    const rIdx = Object.fromEntries(E.resp.map((c, i) => [c, i]));
    echo = { T, stim: E.stims[si], real, copy, row: Array.from({ length: N }, (_, i) => rIdx[B.cls[i]] ?? -1) };
  }
  const target = (() => { const c = echo ? echo.stim : "ASH"; for (let i = 0; i < N; i++) if (B.cls[i] === c) return i; return 0; })();

  // ------------------------------------------------------------------ sprites
  function sprite(rgb, soft) {
    const c = document.createElement("canvas"); c.width = c.height = 128;
    const g = c.getContext("2d"), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, `rgba(255,255,255,1)`);
    gr.addColorStop(soft ? 0.08 : 0.12, `rgba(${rgb},0.95)`);
    gr.addColorStop(soft ? 0.3 : 0.35, `rgba(${rgb},0.28)`);
    gr.addColorStop(1, `rgba(${rgb},0)`);
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
    return c;
  }
  const SPR = { live: sprite("61,214,155"), copy: sprite("240,98,180"), down: sprite("122,167,255"), idle: sprite("150,190,200", true), white: sprite("255,255,255") };

  // ------------------------------------------------------------------ dust
  const DUST = Array.from({ length: 420 }, () => ({ x: Math.random(), y: Math.random(), z: Math.random(), s: Math.random() }));
  // starting positions for the assembly: a wide, slow nebula
  const START = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) { const a = Math.random() * Math.PI * 2, r = 300 + Math.random() * 900, h = (Math.random() - 0.5) * 900; START[3 * i] = 400 + Math.cos(a) * r; START[3 * i + 1] = h; START[3 * i + 2] = Math.sin(a) * r; }
  const seed = Array.from({ length: N }, () => Math.random());

  // ------------------------------------------------------------------ helpers
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const ease = (t) => t * t * (3 - 2 * t);
  const easeOut = (t) => 1 - Math.pow(1 - t, 3);
  const mix = (a, b, t) => a + (b - a) * t;
  const span = (p, a, b) => ease(clamp((p - a) / (b - a)));

  let W = 0, H = 0, dpr = 1, g = cv.getContext("2d");
  function resize() {
    const r = cv.getBoundingClientRect();
    dpr = Math.min(2, devicePixelRatio || 1);
    W = r.width; H = r.height;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  // the worm lies along a gentle S; positions along the body are true, the posture is drawn
  function bodyCurve(ap) {
    const u = ap / 800;
    return [ap - 400, Math.sin(u * Math.PI * 1.7 + 0.5) * 95, Math.cos(u * Math.PI * 1.1) * 30];
  }

  // ------------------------------------------------------------------ stages
  const STAGES = root.querySelectorAll(".x-stage");
  const RAIL = root.querySelectorAll(".x-rail li");
  const bounds = [0, 0.15, 0.34, 0.54, 0.8, 1.0];

  let progress = 0, tStart = performance.now(), pokeStart = null;
  function scrollProgress() {
    const r = root.getBoundingClientRect();
    return clamp(-r.top / (r.height - innerHeight));
  }

  function frame(now) {
    progress = reduce ? progress : mix(progress, scrollProgress(), 0.12);
    if (reduce) progress = scrollProgress();
    const p = progress;
    const stage = Math.min(4, bounds.findIndex((b, i) => p >= b && p < bounds[i + 1]) === -1 ? 4 : bounds.findIndex((b, i) => p >= b && p < bounds[i + 1]));
    STAGES.forEach((s, i) => s.classList.toggle("on", i === stage));
    RAIL.forEach((s, i) => { s.classList.toggle("on", i === stage); s.classList.toggle("done", i < stage); });

    const tSec = (now - tStart) / 1000;
    const assemble = reduce ? 1 : easeOut(clamp((tSec - 0.3) / 3.4));   // the neurons fly in on arrival
    const toHead = span(p, 0.12, 0.3);
    const split = span(p, 0.36, 0.5);
    const pokeOn = p >= 0.55;
    const verdict = span(p, 0.8, 0.9);
    if (pokeOn && pokeStart === null) pokeStart = now;
    if (!pokeOn) pokeStart = null;

    // camera: the whole worm across the screen, then the head filling it
    const spin = reduce ? 0.6 : tSec * 0.16 + p * 2.4;
    const tilt = mix(0.42, 0.22, toHead);
    const mobile = W < 760;
    const baseScale = (mobile ? 0.86 : 0.62) * W / 820;
    const headScale = (mobile ? 0.8 : 0.34) * W / 140 * mix(1, mobile ? 0.5 : 0.72, split) * (1 - 0.14 * verdict);
    const scale = mix(baseScale, headScale, toHead);
    const focusX = mix(0, -320, toHead);          // world x the camera looks at: body centre, then the head
    const camD = 900;
    const cxBase = W * (mobile ? 0.5 : mix(0.56, 0.6, toHead) + 0.08 * verdict), cyBase = H * (mobile ? 0.36 : 0.42);
    const sep = split * W * (mobile ? 0.25 : 0.18 - 0.03 * verdict);   // the two brains, side by side

    g.globalCompositeOperation = "source-over";
    g.fillStyle = "#04080b"; g.fillRect(0, 0, W, H);
    const bg = g.createRadialGradient(cxBase, cyBase, 0, cxBase, cyBase, Math.max(W, H) * 0.7);
    bg.addColorStop(0, "rgba(18,40,44,0.55)"); bg.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = bg; g.fillRect(0, 0, W, H);

    // shade behind the text, left and bottom
    if (!mobile) { const sh = g.createLinearGradient(0, 0, W * 0.5, 0); sh.addColorStop(0, "rgba(4,8,11,0.7)"); sh.addColorStop(1, "rgba(4,8,11,0)"); g.fillStyle = sh; g.fillRect(0, 0, W * 0.5, H); }
    // dust with parallax
    g.globalCompositeOperation = "lighter";
    for (const d of DUST) {
      const x = ((d.x + tSec * 0.004 * (0.3 + d.z) + p * 0.3 * d.z) % 1) * W, y = ((d.y - p * 0.5 * d.z) % 1 + 1) % 1 * H;
      g.globalAlpha = 0.08 + 0.25 * d.z * d.s;
      const sz = 0.6 + d.z * 1.6;
      g.drawImage(SPR.idle, x - sz * 2, y - sz * 2, sz * 4, sz * 4);
    }

    // activity clock: recorded activity plays at four times real speed
    const fr = Math.floor((tSec * 8) % nT);
    const pokeT = pokeStart === null ? -1 : (now - pokeStart) / 1000;
    const cyc = 8.5;
    const echoStep = echo && pokeT >= 0.9 ? Math.min(echo.T - 1, Math.floor(((pokeT - 0.9) % cyc) / 6 * echo.T)) : -1;
    const echoFade = pokeT >= 0 ? clamp(1 - Math.max(0, ((pokeT - 0.9) % cyc) - 6.6) / 1.5) : 0;

    const cs = Math.cos(spin), sn = Math.sin(spin), ct = Math.cos(tilt), st = Math.sin(tilt);
    function project(i, side) {
      const px = P[3 * i], dv = P[3 * i + 1], lr = P[3 * i + 2];
      const [bx, by, bz] = bodyCurve(px);
      // in the head view the body is straightened and the cross-section opened up, to show the cloud in depth
      const open = mix(1, 2.6, toHead);
      let X = mix(bx, px - 400, toHead), Y = mix(by, 0, toHead) + dv * open, Z = mix(bz, 0, toHead) + lr * open;
      X = mix(START[3 * i] - 400, X, assemble); Y = mix(START[3 * i + 1], Y, assemble); Z = mix(START[3 * i + 2], Z, assemble);
      X -= focusX;
      // spin about the long axis, then tilt toward the viewer
      const y1 = Y * cs - Z * sn, z1 = Y * sn + Z * cs;
      const x2 = X * ct + z1 * st * 0.25, z2 = -X * st * 0.25 + z1 * ct;
      const k = camD / (camD + z2 * scale / baseScale * 0.35);
      return [cxBase + side * sep + x2 * scale * k, cyBase + y1 * scale * k, k, z2];
    }

    // a ghost of the body around the overview, so the filament reads as a worm
    const bodyA = (1 - toHead) * assemble;
    if (bodyA > 0.02) {
      const cen = [];
      for (let ap = 0; ap <= 800; ap += 8) {
        const [bx, by, bz] = bodyCurve(ap);
        const X = bx - focusX, y1 = by * cs - bz * sn, z1 = by * sn + bz * cs;
        const x2 = X * ct + z1 * st * 0.25, z2 = -X * st * 0.25 + z1 * ct;
        const k = camD / (camD + z2 * 0.35);
        cen.push([cxBase + x2 * scale * k, cyBase + y1 * scale * k, 24 * Math.pow(Math.sin(Math.PI * Math.min(1, (ap + 10) / 812)), 0.6) * scale * k]);
      }
      const L = [], Rr = [];
      for (let i = 0; i < cen.length; i++) {
        const a0 = cen[Math.max(0, i - 1)], a1 = cen[Math.min(cen.length - 1, i + 1)];
        let tx = a1[0] - a0[0], ty = a1[1] - a0[1]; const tl = Math.hypot(tx, ty) || 1; tx /= tl; ty /= tl;
        L.push([cen[i][0] - ty * cen[i][2], cen[i][1] + tx * cen[i][2]]); Rr.push([cen[i][0] + ty * cen[i][2], cen[i][1] - tx * cen[i][2]]);
      }
      g.globalCompositeOperation = "source-over";
      g.beginPath(); g.moveTo(L[0][0], L[0][1]); L.forEach((q) => g.lineTo(q[0], q[1])); Rr.reverse().forEach((q) => g.lineTo(q[0], q[1])); g.closePath();
      const gr = g.createLinearGradient(0, cyBase - 120, 0, cyBase + 120);
      gr.addColorStop(0, "rgba(120,210,190,0.10)"); gr.addColorStop(0.5, "rgba(120,210,190,0.04)"); gr.addColorStop(1, "rgba(120,210,190,0.10)");
      g.globalAlpha = bodyA; g.fillStyle = gr; g.fill();
      g.strokeStyle = "rgba(150,230,210,0.32)"; g.lineWidth = 1; g.stroke();
      g.globalAlpha = 1;
    }
    // wiring, faint, in the brain on the left (and its copy)
    const showWires = 0.35 * (1 - span(p, 0.55, 0.62) * 0.6);
    for (const side of split > 0.01 ? [-1, 1] : [0]) {
      g.globalCompositeOperation = "lighter";
      g.strokeStyle = side > 0 ? "rgba(240,98,180,1)" : "rgba(80,200,170,1)";
      g.globalAlpha = 0.05 * showWires * assemble;
      g.lineWidth = 0.6;
      g.beginPath();
      const proj = new Array(N);
      for (let i = 0; i < N; i++) proj[i] = project(i, side);
      for (let e = 0; e < edges.length; e += 2) {
        const a = proj[edges[e]], b = proj[edges[e + 1]];
        if (toHead > 0.5 && (!isHead[edges[e]] || !isHead[edges[e + 1]])) continue;
        if (Math.abs(P[3 * edges[e]] - P[3 * edges[e + 1]]) > (toHead > 0.5 ? 400 : 70)) continue;   // long wires clutter the overview
        g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]);
      }
      g.stroke();

      // neurons
      const ghosts = [];
      const order = proj.map((q, i) => i).sort((a, b) => proj[b][3] - proj[a][3]);
      for (const i of order) {
        const [x, y, k] = proj[i];
        if (x < -40 || x > W + 40 || y < -40 || y > H + 40) continue;
        let lvl = 0.12, spr = side > 0 ? SPR.copy : SPR.live;
        const r = aRow[i];
        if (r >= 0 && assemble > 0.95) {
          const q = (side > 0 ? actCopy : actReal)[r * nT + fr];
          lvl = q ? 0.08 + 0.92 * Math.pow(clamp((q / 255 - 0.3) / 0.6), 1.6) : 0.08;
        } else lvl = 0.1 + 0.08 * Math.sin(tSec * 1.3 + seed[i] * 9);
        if (!split && side === 0) spr = SPR.live;
        // the echo replaces ongoing activity once the poke lands
        if (echoStep >= 0 && echo) {
          const er = echo.row[i];
          const v = er >= 0 ? (side > 0 ? echo.copy(er, echoStep) : echo.real(er, echoStep)) : NaN;
          const a = isFinite(v) ? clamp(Math.abs(v) / 1.1) : 0;
          lvl = mix(lvl * 0.35, 0.06 + 0.94 * a, echoFade);
          if (isFinite(v) && v < 0 && a > 0.2) spr = SPR.down;
        }
        if (i === target && pokeT >= 0.5) { lvl = 1; spr = SPR.white; }
        if (side > 0 && echoStep >= 0 && echo && echo.row[i] >= 0) {
          const vr = echo.real(echo.row[i], echoStep);
          if (isFinite(vr) && Math.abs(vr) > 0.55) ghosts.push([proj[i][0], proj[i][1], clamp(Math.abs(vr) / 1.1)]);
        }
        const size = (2.2 + 9 * lvl) * clamp(k * 1.4, 0.4, 2.6) * (isHead[i] ? 1 : 0.8);
        g.globalAlpha = clamp(0.25 + lvl) * (0.4 + 0.6 * assemble);
        g.drawImage(spr, x - size, y - size, size * 2, size * 2);
      }

      // in the copy, rings mark where the real worm's signal went
      if (ghosts.length) {
        g.globalCompositeOperation = "source-over";
        for (const [x, y, a] of ghosts) { g.globalAlpha = 0.35 + 0.5 * a * echoFade; g.strokeStyle = "#9fe8c4"; g.lineWidth = 1; g.beginPath(); g.arc(x, y, 6 + 3 * a, 0, Math.PI * 2); g.stroke(); }
        g.globalCompositeOperation = "lighter";
      }
      // the poke: a beam of light onto the target, then a shock ring
      if (pokeT >= 0 && echo) {
        const [tx, ty] = proj[target];
        const beam = clamp(pokeT / 0.5), fade = 1 - clamp((pokeT - 0.5) / 0.6);
        if (fade > 0) {
          const grd = g.createLinearGradient(tx, 0, tx, ty);
          grd.addColorStop(0, "rgba(255,255,255,0)"); grd.addColorStop(1, "rgba(255,255,255,0.95)");
          g.globalAlpha = fade; g.strokeStyle = grd; g.lineWidth = 2;
          g.beginPath(); g.moveTo(tx, ty - (ty + 20) * beam); g.lineTo(tx, ty); g.stroke();
        }
        // the moment the light lands: a brief bloom
        const fl = pokeT - 0.5;
        if (fl > 0 && fl < 0.7) {
          const rad = 40 + fl * 260, bl = g.createRadialGradient(tx, ty, 0, tx, ty, rad);
          bl.addColorStop(0, `rgba(255,255,255,${0.55 * (1 - fl / 0.7)})`); bl.addColorStop(1, "rgba(255,255,255,0)");
          g.globalAlpha = 1; g.fillStyle = bl; g.beginPath(); g.arc(tx, ty, rad, 0, Math.PI * 2); g.fill();
        }
        const ringT = ((pokeT - 0.5) % 8.5);
        if (ringT > 0 && ringT < 2.2) {
          g.globalAlpha = 0.7 * (1 - ringT / 2.2); g.strokeStyle = "#ffffff"; g.lineWidth = 1.5;
          g.beginPath(); g.arc(tx, ty, 8 + ringT * 55, 0, Math.PI * 2); g.stroke();
        }
        g.globalAlpha = 1; g.globalCompositeOperation = "source-over";
        g.font = "600 12px 'Schibsted Grotesk', system-ui"; g.fillStyle = "rgba(255,255,255,0.9)"; g.textAlign = "center";
        g.fillText(echo.stim, tx, ty - 18);
        g.globalCompositeOperation = "lighter";
      }
      // labels under the two brains
      if (split > 0.6) {
        g.globalCompositeOperation = "source-over"; g.globalAlpha = (split - 0.6) / 0.4 * (1 - verdict * 0.5);
        g.font = `600 ${mobile ? 10.5 : 13}px 'Schibsted Grotesk', system-ui`; g.textAlign = "center";
        g.fillStyle = side > 0 ? "#f062b4" : "#3dd69b";
        const off = mobile ? W * 0.3 : Math.min(W * 0.16, 190);
        g.fillText(side > 0 ? (mobile ? "COPY" : "COPY, BUILT BY WATCHING") : (mobile ? "LIVING WORM" : "LIVING WORM, RECORDED"), cxBase + side * sep, cyBase - off);
        if (side > 0 && ghosts.length) { g.font = `500 ${mobile ? 11 : 12}px 'Schibsted Grotesk', system-ui`; g.fillStyle = "#9fe8c4"; g.fillText("rings: where the real worm's signal went", mobile ? W / 2 : cxBase + side * sep, cyBase + off); }
        g.globalCompositeOperation = "lighter";
      }
    }
    g.globalAlpha = 1; g.globalCompositeOperation = "source-over";

    // echo clock
    const ec = root.querySelector(".x-echo-clock");
    if (ec) ec.textContent = echoStep >= 0 ? `${echoStep} s after the poke` : "";
    requestAnimationFrame(frame);
  }

  // counters in the verdict
  const counted = new WeakSet();
  const io = new IntersectionObserver((es) => es.forEach((e) => {
    if (!e.isIntersecting || counted.has(e.target)) return;
    counted.add(e.target);
    const to = parseFloat(e.target.dataset.to), t0 = performance.now();
    const step = (n) => { const k = clamp((n - t0) / 1400); e.target.textContent = (to * easeOut(k)).toFixed(2); if (k < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }), { threshold: 0.6 });
  root.querySelectorAll("[data-to]").forEach((n) => io.observe(n));

  addEventListener("resize", resize);
  resize();
  requestAnimationFrame(frame);
})();
