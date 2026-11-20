/* NEMATICA, the three rules, drawn as three small living instruments in the scene's own language: points of
   light, hairlines, brass for the living and carmine for copies. Each is a canvas drawn at the screen's own
   pixel density, animated only while it is in view, and still when the reader asks for reduced motion.

   lens   the same instrument: an animal and a network pass through one lens and come out as the same kind
          of recording, with the same cells missing
   rule   the same yardstick: other animals sit about one unit from any animal; a copy passes inside that ring
   touch  watch, then touch: the same small network seen at rest, and answering one driven cell */
(function () {
  "use strict";
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const PI = Math.PI, TAU = 2 * PI, sin = Math.sin, cos = Math.cos;
  const GOLD = [240, 207, 120], CARM = [255, 79, 126], BONE = [236, 230, 214], BRASS = [182, 143, 27];
  const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${Math.max(0, a).toFixed(3)})`;
  let seed = 7; const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
  const sprite = (c) => { const s = document.createElement("canvas"); s.width = s.height = 96; const g = s.getContext("2d"), gr = g.createRadialGradient(48, 48, 0, 48, 48, 48), k = c.join(",");
    gr.addColorStop(0, `rgba(${k},.6)`); gr.addColorStop(0.2, `rgba(${k},.24)`); gr.addColorStop(0.55, `rgba(${k},.06)`); gr.addColorStop(1, `rgba(${k},0)`); g.fillStyle = gr; g.fillRect(0, 0, 96, 96); return s; };
  const HALO = new Map([[GOLD, sprite(GOLD)], [CARM, sprite(CARM)], [BONE, sprite(BONE)]]);
  // a point of light: a halo, then a core that whitens as it brightens
  function star(g, x, y, r, c, b) { const h = r * (3.2 + 2.2 * b); g.globalCompositeOperation = "lighter"; g.globalAlpha = Math.min(1, 0.25 + 0.75 * b); g.drawImage(HALO.get(c), x - h, y - h, 2 * h, 2 * h);
    g.globalAlpha = Math.min(1, 0.5 + 0.5 * b); const w = Math.max(0, b - 0.55) * 1.6; g.fillStyle = `rgb(${Math.round(c[0] + (255 - c[0]) * w)},${Math.round(c[1] + (250 - c[1]) * w)},${Math.round(c[2] + (238 - c[2]) * w)})`;
    g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill(); g.globalAlpha = 1; g.globalCompositeOperation = "source-over"; }
  const ring = (g, x, y, r, c, a, lw) => { g.strokeStyle = rgba(c, a); g.lineWidth = lw || 1.5; g.beginPath(); g.arc(x, y, r, 0, TAU); g.stroke(); };
  const line = (g, x0, y0, x1, y1, c, a, lw) => { g.strokeStyle = rgba(c, a); g.lineWidth = lw || 1; g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke(); };
  const text = (g, s, x, y, a, size, align) => { g.font = `italic 500 ${size || 15}px Cormorant, Georgia, serif`; g.textAlign = align || "center"; g.fillStyle = rgba(BONE, a == null ? 0.7 : a); g.fillText(s, x, y); };
  // activity that comes in bursts, like a cell lighting up and fading
  const burst = (t, f, p) => Math.pow(0.5 + 0.5 * sin(t * f + p), 6) + 0.45 * Math.pow(0.5 + 0.5 * sin(t * f * 1.7 + p * 3.1), 9);

  // ---------------------------------------------------------------- the same instrument
  const organic = Array.from({ length: 13 }, (_, i) => { const a = i * 2.4 + rnd() * 0.5, r = 0.25 + 0.75 * Math.sqrt((i + 0.5) / 13); return [cos(a) * r, sin(a) * r * 0.82, 0.5 + rnd() * 0.9, rnd() * TAU]; });
  const olinks = []; organic.forEach((p, i) => organic.forEach((q, j) => { if (j > i && Math.hypot(p[0] - q[0], p[1] - q[1]) < 0.62) olinks.push([i, j]); }));
  const layered = []; for (let c = 0; c < 3; c++) for (let r = 0; r < 4; r++) layered.push([-0.8 + c * 0.62, -0.72 + r * 0.48, c]); layered.push([1.02, 0, 3]);
  const llinks = []; layered.forEach((p, i) => layered.forEach((q, j) => { if (q[2] === p[2] + 1 && (q[2] === 3 || Math.abs(p[1] - q[1]) < 0.5)) llinks.push([i, j]); }));
  function lens(g, W, H, t) {
    const xs = W * 0.17, xl = W * 0.46, x0 = W * 0.6, x1 = W * 0.985, ys = [H * 0.3, H * 0.71], sc = Math.min(W * 0.125, H * 0.165);
    const act = [organic.map((p, i) => Math.min(1, burst(t, p[2], p[3]))), layered.map((p) => Math.pow(0.5 + 0.5 * sin(t * 1.9 - p[2] * 1.25 + p[1] * 0.5), 3))];
    // the two things to be compared: an animal's nervous system, and a network
    [[organic, olinks, GOLD], [layered, llinks, CARM]].forEach(([pts, links, c], k) => {
      g.beginPath(); links.forEach(([i, j]) => { g.moveTo(xs + pts[i][0] * sc, ys[k] + pts[i][1] * sc); g.lineTo(xs + pts[j][0] * sc, ys[k] + pts[j][1] * sc); }); g.strokeStyle = rgba(c, 0.22); g.lineWidth = 0.8; g.stroke();
      pts.forEach((p, i) => star(g, xs + p[0] * sc, ys[k] + p[1] * sc, 2.3, c, 0.25 + 0.75 * act[k][i]));
      // light gathered by the lens, and thrown onto the record
      [-0.5, 0, 0.5].forEach((o) => { const gr = g.createLinearGradient(xs + sc, 0, xl, 0); gr.addColorStop(0, rgba(c, 0)); gr.addColorStop(1, rgba(c, 0.26)); g.strokeStyle = gr; g.lineWidth = 0.8; g.beginPath(); g.moveTo(xs + sc * 1.25, ys[k] + o * sc * 1.3); g.lineTo(xl, ys[k] + o * sc * 0.25); g.stroke();
        const g2 = g.createLinearGradient(xl, 0, x0, 0); g2.addColorStop(0, rgba(c, 0.26)); g2.addColorStop(1, rgba(c, 0.05)); g.strokeStyle = g2; g.beginPath(); g.moveTo(xl, ys[k] + o * sc * 0.25); g.lineTo(x0 - 6, ys[k] + o * sc * 1.2); g.stroke(); });
      // the record: one trace per cell the instrument can see; the ones it cannot are left blank, in both
      for (let q = 0; q < 5; q++) { const y = ys[k] + (q - 2) * H * 0.068, blind = q === 1 || q === 3;
        if (blind) { g.setLineDash([2, 5]); line(g, x0, y, x1, y, BONE, 0.2, 0.8); g.setLineDash([]); continue; }
        const src = pts[(q * 3 + 1) % pts.length], f = k ? 1.9 : src[2], ph = k ? -src[2] * 1.25 + src[1] * 0.5 : src[3]; g.beginPath();
        for (let x = x0; x <= x1; x += 2) { const tt = t - (x - x0) / 34, v = k ? Math.pow(0.5 + 0.5 * sin(tt * f + ph), 3) : Math.min(1, burst(tt, f, ph)), n = 0.9 * sin(x * 1.9 + q * 7 + Math.floor(t * 9) * 2.4); if (x === x0) g.moveTo(x, y - v * H * 0.05 + n); else g.lineTo(x, y - v * H * 0.05 + n); }
        const tg = g.createLinearGradient(x0, 0, x1, 0); tg.addColorStop(0, rgba(c, 0.95)); tg.addColorStop(1, rgba(c, 0.25)); g.strokeStyle = tg; g.lineWidth = 1.1; g.stroke(); }
    });
    // the instrument: one lens for both
    const top = H * 0.06, bot = H * 0.94, bw = W * 0.034, body = new Path2D(); body.moveTo(xl, top); body.quadraticCurveTo(xl + bw * 2, H / 2, xl, bot); body.quadraticCurveTo(xl - bw * 2, H / 2, xl, top);
    const lg = g.createLinearGradient(xl - bw, 0, xl + bw, 0); lg.addColorStop(0, rgba(BONE, 0.02)); lg.addColorStop(0.5, rgba(BONE, 0.1)); lg.addColorStop(1, rgba(BONE, 0.02)); g.fillStyle = lg; g.fill(body);
    g.strokeStyle = rgba(BONE, 0.85); g.lineWidth = 1.2; g.stroke(body);
    g.beginPath(); g.moveTo(xl - bw * 0.45, H * 0.2); g.quadraticCurveTo(xl - bw * 0.9, H / 2, xl - bw * 0.45, H * 0.8); g.strokeStyle = rgba(BONE, 0.28); g.lineWidth = 0.8; g.stroke();
    line(g, xl - 9, top, xl + 9, top, BONE, 0.7, 1.2); line(g, xl - 9, bot, xl + 9, bot, BONE, 0.7, 1.2);
    for (let q = 1; q < 12; q++) { const y = top + ((bot - top) * q) / 12; line(g, xl - (q % 3 ? 2 : 4), y, xl + (q % 3 ? 2 : 4), y, BONE, 0.35, 0.8); }
    text(g, "an animal", xs, ys[0] - sc * 1.3, 0.62, 14); text(g, "a network", xs, ys[1] + sc * 1.62, 0.62, 14); text(g, W < 360 ? "what it records" : "what the instrument records", x1, H * 0.515, 0.5, 13.5, "right");
  }

  // ---------------------------------------------------------------- the same yardstick
  const herd = Array.from({ length: 13 }, (_, i) => [0.78 + 0.5 * rnd(), (i / 13) * TAU + rnd() * 0.3, 0.012 + 0.02 * rnd(), rnd() * TAU]);
  function rule(g, W, H, t) {
    const cx = W * 0.4, cy = H * 0.47, R = Math.min(H * 0.27, W * 0.2), lo = 0.82 * R, hi = 1.24 * R;
    // where another animal usually sits: a ring, engraved
    g.save(); g.beginPath(); g.arc(cx, cy, hi, 0, TAU); g.arc(cx, cy, lo, 0, TAU, true); g.clip();
    g.beginPath(); for (let x = -H; x < W; x += 5) { g.moveTo(cx - W + x, cy + H); g.lineTo(cx - W + x + 2 * H, cy - H); } g.strokeStyle = rgba(BRASS, 0.75); g.lineWidth = 1; g.stroke();
    const wash = g.createRadialGradient(cx, cy, lo, cx, cy, hi); wash.addColorStop(0, rgba(GOLD, 0.02)); wash.addColorStop(0.5, rgba(GOLD, 0.1)); wash.addColorStop(1, rgba(GOLD, 0.02)); g.fillStyle = wash; g.fillRect(0, 0, W, H); g.restore();
    ring(g, cx, cy, lo, GOLD, 0.7, 1); ring(g, cx, cy, hi, GOLD, 0.7, 1);
    g.beginPath(); for (let k = 0; k < 72; k++) { const a = (k / 72) * TAU, r0 = hi + 3, r1 = hi + (k % 6 ? 6 : 10); g.moveTo(cx + r0 * cos(a), cy + r0 * sin(a)); g.lineTo(cx + r1 * cos(a), cy + r1 * sin(a)); } g.strokeStyle = rgba(BONE, 0.3); g.lineWidth = 0.8; g.stroke();
    // the other animals, each about one unit away
    herd.forEach((p) => { const a = p[1] + (REDUCED ? 0 : t * p[2]), r = p[0] * R * (1 + 0.03 * sin(t * 0.7 + p[3])), x = cx + r * cos(a), y = cy + r * sin(a); line(g, cx, cy, x, y, GOLD, 0.07, 0.8); star(g, x, y, 2.1, GOLD, 0.45 + 0.2 * sin(t * 0.9 + p[3])); });
    star(g, cx, cy, 3.4, GOLD, 1);
    // the yardstick itself: distance from one animal, in animals
    const x2 = Math.min(W - 10, cx + 2.5 * R); line(g, cx, cy, x2, cy, BONE, 0.75, 1.1);
    g.beginPath(); for (let k = 0; k * 0.1 * R <= x2 - cx; k++) { const x = cx + k * 0.1 * R, d = k % 10 === 0 ? 9 : k % 5 === 0 ? 6 : 3.5; g.moveTo(x, cy); g.lineTo(x, cy + d); } g.strokeStyle = rgba(BONE, 0.55); g.lineWidth = 0.9; g.stroke();
    g.font = "500 13px Cormorant, Georgia, serif"; g.textAlign = "center"; g.fillStyle = rgba(BONE, 0.7); g.fillText("0", cx, cy + 23); g.fillText("1", cx + R, cy + 23); if (cx + 2 * R < x2 - 4) g.fillText("2", cx + 2 * R, cy + 23);
    // two copies: one as near as another animal would be, one not
    const a1 = -0.62, r1 = 1.02 * R, px = cx + r1 * cos(a1), py = cy + r1 * sin(a1); star(g, px, py, 4.2, CARM, 0.75 + 0.25 * sin(t * 2)); ring(g, px, py, 8.5 + 1.5 * sin(t * 2), CARM, 0.35, 1);
    const fx = Math.min(W - 30, cx + 2.2 * R), fy = cy + 0.66 * R; g.setLineDash([2, 4]); line(g, cx, cy, fx, fy, CARM, 0.3, 0.8); g.setLineDash([]); ring(g, fx, fy, 4.6, CARM, 0.95, 1.7);
    text(g, "passes", px + 12, py - 12, 0.85, 15, "left"); text(g, "does not", fx, fy + 24, 0.85, 15);
    text(g, "how far apart real animals sit", cx, cy + hi + 30, 0.55, 13.5);
  }

  // ---------------------------------------------------------------- watch, then touch
  const net = [[0, 0]]; for (let k = 0; k < 6; k++) net.push([0.56 * cos(k * 1.047 + 0.3), 0.56 * sin(k * 1.047 + 0.3)]); for (let k = 0; k < 5; k++) net.push([1.02 * cos(k * 1.257 + 0.9), 0.96 * sin(k * 1.257 + 0.9)]);
  const nl = []; net.forEach((p, i) => net.forEach((q, j) => { if (j > i && Math.hypot(p[0] - q[0], p[1] - q[1]) < 0.72) nl.push([i, j]); }));
  const nadj = net.map((_, i) => nl.filter((l) => l[0] === i || l[1] === i).map((l) => (l[0] === i ? l[1] : l[0]))), hop = net.map(() => 9); hop[3] = 0;
  for (let d = 0; d < 4; d++) net.forEach((_, i) => { if (hop[i] === d) nadj[i].forEach((j) => { if (hop[j] > d + 1) hop[j] = d + 1; }); });
  function touch(g, W, H, t) {
    const sc = Math.min(W * 0.17, H * 0.27), cy = H * 0.56, L = W * 0.25, Rr = W * 0.75, CYC = 3.4, u = REDUCED ? 0.5 : (t % CYC), T0 = 0.5;
    line(g, W / 2, H * 0.1, W / 2, H * 0.9, BONE, 0.14, 1);
    [L, Rr].forEach((cx, k) => { g.beginPath(); nl.forEach(([i, j]) => { g.moveTo(cx + net[i][0] * sc, cy + net[i][1] * sc); g.lineTo(cx + net[j][0] * sc, cy + net[j][1] * sc); }); g.strokeStyle = rgba(BONE, 0.2); g.lineWidth = 0.8; g.stroke(); });
    // watch: the network left alone, its cells flickering as they do at rest; an eye above it
    net.forEach((p, i) => star(g, L + p[0] * sc, cy + p[1] * sc, 2.4, BONE, 0.22 + 0.6 * Math.min(1, burst(t, 0.7 + (i % 5) * 0.23, i * 1.9))));
    const ex = L, ey = H * 0.105, ew = Math.min(30, W * 0.085), eh = ew * 0.52, eye = new Path2D(); eye.moveTo(ex - ew, ey); eye.quadraticCurveTo(ex, ey - eh * 1.9, ex + ew, ey); eye.quadraticCurveTo(ex, ey + eh * 1.9, ex - ew, ey);
    g.strokeStyle = rgba(BONE, 0.85); g.lineWidth = 1.2; g.stroke(eye); ring(g, ex, ey, eh * 0.78, BONE, 0.85, 1.2); g.fillStyle = rgba(BONE, 0.9); g.beginPath(); g.arc(ex, ey, eh * 0.3, 0, TAU); g.fill();
    const cone = g.createLinearGradient(0, ey + eh, 0, cy - sc); cone.addColorStop(0, rgba(BONE, 0.1)); cone.addColorStop(1, rgba(BONE, 0)); g.fillStyle = cone; g.beginPath(); g.moveTo(ex - 4, ey + eh); g.lineTo(ex + 4, ey + eh); g.lineTo(ex + sc * 1.05, cy - sc * 0.3); g.lineTo(ex - sc * 1.05, cy - sc * 0.3); g.closePath(); g.fill();
    // touch: light drives one cell, and the answer runs out along the links
    const tx = Rr + net[3][0] * sc, ty = cy + net[3][1] * sc, on = u > T0 ? Math.exp(-(u - T0) * 1.1) : 0;
    const beam = g.createLinearGradient(tx + sc * 0.9, H * 0.02, tx, ty); beam.addColorStop(0, rgba(GOLD, 0)); beam.addColorStop(1, rgba(GOLD, 0.25 + 0.7 * on)); g.strokeStyle = beam; g.lineWidth = 1.4; g.beginPath(); g.moveTo(tx + sc * 0.95, H * 0.02); g.lineTo(tx, ty); g.stroke();
    if (u > T0) [0, 0.35].forEach((d) => { const q = (u - T0 - d) / 1.5; if (q > 0 && q < 1) ring(g, tx, ty, 6 + q * sc * 0.9, GOLD, 0.6 * (1 - q), 1); });
    g.globalCompositeOperation = "lighter";
    nl.forEach(([i, j]) => { const a = hop[i] < hop[j] ? i : j, b = a === i ? j : i; if (hop[a] === hop[b]) return; const q = (u - T0 - hop[a] * 0.42) / 0.42; if (q <= 0 || q >= 1) return;
      const xa = Rr + net[a][0] * sc, ya = cy + net[a][1] * sc, xb = Rr + net[b][0] * sc, yb = cy + net[b][1] * sc, q0 = Math.max(0, q - 0.3);
      g.strokeStyle = rgba(GOLD, 0.9 * Math.pow(0.62, hop[a])); g.lineWidth = 1.5; g.beginPath(); g.moveTo(xa + (xb - xa) * q0, ya + (yb - ya) * q0); g.lineTo(xa + (xb - xa) * q, ya + (yb - ya) * q); g.stroke(); });
    g.globalCompositeOperation = "source-over";
    net.forEach((p, i) => { const since = u - T0 - hop[i] * 0.42, e = since > 0 ? Math.exp(-since * 1.5) * Math.pow(0.66, hop[i]) : 0; star(g, Rr + p[0] * sc, cy + p[1] * sc, 2.4 + (i === 3 ? 1 : 0), e > 0.08 ? GOLD : BONE, Math.min(1, 0.2 + e * 1.1)); });
    text(g, "watch", L, H * 0.97, 0.62, 15); text(g, "touch", Rr, H * 0.97, 0.62, 15);
  }

  const DRAW = { lens, rule, touch };
  function mount(host) {
    const draw = DRAW[host.dataset.emblem]; if (!draw) return;
    const cv = document.createElement("canvas"); cv.setAttribute("aria-hidden", "true"); host.appendChild(cv); const g = cv.getContext("2d");
    let W = 0, H = 0, live = false, raf = 0;
    const size = () => { const r = host.getBoundingClientRect(), d = Math.min(2, devicePixelRatio || 1); W = Math.max(240, Math.round(r.width)); H = W < 300 ? 216 : 244; cv.style.width = W + "px"; cv.style.height = H + "px"; cv.width = Math.round(W * d); cv.height = Math.round(H * d); g.setTransform(d, 0, 0, d, 0, 0); };
    const frame = (now) => { raf = 0; g.clearRect(0, 0, W, H); draw(g, W, H, REDUCED ? 2.2 : now / 1000); if (live && !REDUCED) raf = requestAnimationFrame(frame); };
    const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };
    size(); kick();
    if ("ResizeObserver" in window) new ResizeObserver(() => { size(); kick(); }).observe(host); else addEventListener("resize", () => { size(); kick(); });
    if ("IntersectionObserver" in window) new IntersectionObserver((es) => es.forEach((e) => { live = e.isIntersecting; if (live) kick(); }), { rootMargin: "80px" }).observe(host); else { live = true; kick(); }
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(kick);
  }
  document.querySelectorAll("[data-emblem]").forEach(mount);
})();
