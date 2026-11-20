/* NEMATICA, the sky: one fixed, full-screen scene behind the whole page, made of the worm's 279 neurons.

   The same 279 points are every figure on the page. They open as the living worm (its real wiring, signals
   running along its nerve cord), can be turned into an artificial layered network, and re-form for each part
   of the page: an orrery of the seven questions, a balance, each question's planet, the seven-pointed star.
   Between figures they drift as a field of stars.

   How it moves is a pure function of where the page is scrolled to and of the clock. Each figure belongs to a
   box in the layout (a .stage inside a [data-sky] section) and travels with it, so a figure can never sit on
   top of the text beside it. A figure is "in" by as much as its stage is in view; points leave their stars
   for a figure as its stage arrives and return to them as it goes. Line work is drawn only once the points
   have landed. Nothing is remembered from frame to frame except a little smoothing, so reloading half way
   down, resizing, or scrolling fast in either direction all give the same picture. */
(function () {
  "use strict";
  const B = window.NEMATICA_WIRING || window.NEMATICA_BRAIN, cv = document.getElementById("sky");
  if (!B || !cv) return;
  const ctx = cv.getContext("2d"), N = B.names.length;
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const PI = Math.PI, TAU = 2 * PI, sin = Math.sin, cos = Math.cos, CAM = 4.2;
  const c01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);
  const smooth = (u) => { u = c01(u); return u * u * (3 - 2 * u); };
  const ease = (u) => { u = c01(u); return u * u * u * (u * (6 * u - 15) + 10); };
  const frac = (v) => v - Math.floor(v);
  let seed = 11;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
  let W = 0, H = 0, DPR = 1;

  // ---------------------------------------------------------------- colour: brass for the living, carmine for copies, a metal for each planet
  const PAL = [
    [240, 207, 120], [236, 230, 214], [255, 79, 126], [255, 250, 238],
    [196, 222, 255], [255, 122, 92], [255, 170, 118], [196, 204, 226], [255, 214, 110], [226, 234, 250], [226, 218, 204], [206, 152, 112],
  ];
  const GOLD = 0, BONE = 1, CARM = 2, WHITE = 3, BELT = 11;
  const METAL = { mercury: 4, mars: 5, venus: 6, saturn: 7, sun: 8, moon: 9, jupiter: 10 };
  const rgba = (c, a) => `rgba(${PAL[c][0]},${PAL[c][1]},${PAL[c][2]},${a < 0 ? 0 : a.toFixed(3)})`;

  // ---------------------------------------------------------------- the wiring
  const order = Array.from({ length: N }, (_, i) => i).sort((a, b) => B.pos[3 * a] - B.pos[3 * b] || B.pos[3 * a + 1] - B.pos[3 * b + 1]);
  const rank = new Uint16Array(N); order.forEach((id, k) => (rank[id] = k));
  const E = B.edges, NE = E.length / 2, EW = B.w || [], deg = new Uint16Array(N), adj = Array.from({ length: N }, () => []);
  for (let k = 0; k < NE; k++) { const a = E[2 * k], b = E[2 * k + 1]; deg[a]++; deg[b]++; adj[a].push(b); adj[b].push(a); }
  const hub = (i) => Math.min(1, deg[i] / 45);

  // ---------------------------------------------------------------- a figure: where each of the 279 points goes, and how it shows there
  function make(ext, rot) {
    return { ext, rot, P: new Float32Array(3 * N), aux: new Float32Array(4 * N), lum: new Float32Array(N).fill(1), siz: new Float32Array(N).fill(1),
      col: new Uint8Array(N).fill(BONE), alt: new Uint8Array(N), grp: new Uint8Array(N), del: new Float32Array(N), chains: [], k: 0, tint: GOLD, glow: 0.5, seg: 0.3 };
  }
  // the next free neuron, taken in head-to-tail order, placed at (x, y, z)
  function put(F, x, y, z, lum, siz, col, grp) {
    const i = order[F.k]; F.del[i] = F.k / N; F.k++;
    F.P[3 * i] = x; F.P[3 * i + 1] = y; F.P[3 * i + 2] = z;
    if (lum != null) F.lum[i] = lum; if (siz != null) F.siz[i] = siz; if (col != null) F.col[i] = col; if (grp != null) F.grp[i] = grp;
    return i;
  }
  const chain = (F, idx, closed, a, c, w) => F.chains.push({ idx, closed: !!closed, a: a == null ? 0.3 : a, c: c == null ? BONE : c, w: w || 0.8 });
  const still = (F) => (i, t, o) => { o[0] = F.P[3 * i]; o[1] = F.P[3 * i + 1]; o[2] = F.P[3 * i + 2]; };
  const norm3 = (v) => { const l = Math.hypot(v[0], v[1], v[2]); return [v[0] / l, v[1] / l, v[2] / l]; };

  // ================================================================ the worm, and the artificial network it can be turned into
  const LEN = 5.2, NR = 0.33;
  const taper = (u) => 0.3 + 0.7 * Math.pow(sin(PI * Math.min(1, c01(u) * 1.55)), 0.8);        // a full head, a long thin tail
  const WU = new Float32Array(N), WP = new Float32Array(3 * N), LAT = new Float32Array(3 * N);
  { const x0 = B.pos[3 * order[0]], x1 = B.pos[3 * order[N - 1]];
    for (let i = 0; i < N; i++) { const u = (WU[i] = 0.5 * (rank[i] / (N - 1)) + 0.5 * ((B.pos[3 * i] - x0) / (x1 - x0))), tp = taper(u);
      WP[3 * i] = (u - 0.5) * LEN; WP[3 * i + 1] = (B.pos[3 * i + 1] / 20) * NR * tp; WP[3 * i + 2] = (B.pos[3 * i + 2] / 12) * NR * tp; } }
  // the body's axis at u (0 nose, 1 tail) while it swims
  const axis = (u, t, o) => { const ph = TAU * 1.3 * u - t, A = 0.3 + 0.7 * c01(u); o[0] = (u - 0.5) * LEN; o[1] = 0.36 * A * sin(ph); o[2] = 0.28 * A * cos(ph); };
  // an artificial net: layers of thirty units, each wired to three units of the next, and a small output layer
  const LX = 0.42, LY = 0.18, ROWS = 6, COLS = 5, FULL = Math.floor(N / 30), REST = N - FULL * 30, LAYERS = FULL + (REST ? 1 : 0), LE = [], lnext = Array.from({ length: N }, () => []);
  { const link = (a, b) => { LE.push(order[a], order[b]); lnext[order[a]].push(order[b]); }, mid = (LAYERS - 1) / 2, side = Math.ceil(Math.sqrt(REST || 1));
    for (let k = 0; k < FULL * 30; k++) { const l = Math.floor(k / 30), w = k % 30, r = Math.floor(w / COLS), c = w % COLS;
      if (l < FULL - 1) [[r, c], [(r + 1) % ROWS, c], [r, (c + 1) % COLS]].forEach(([r2, c2]) => link(k, (l + 1) * 30 + r2 * COLS + c2));
      else if (REST) link(k, FULL * 30 + (w % REST)); }
    for (let k = 0; k < N; k++) { const i = order[k];
      if (k < FULL * 30) { const l = Math.floor(k / 30), w = k % 30, r = Math.floor(w / COLS), c = w % COLS; LAT[3 * i] = (l - mid) * LX; LAT[3 * i + 1] = (r - 2.5) * LY; LAT[3 * i + 2] = (c - 2) * LY; }
      else { const w = k - FULL * 30, r = Math.floor(w / side), c = w % side; LAT[3 * i] = (FULL - mid) * LX; LAT[3 * i + 1] = (r - (side - 1) / 2) * LY; LAT[3 * i + 2] = (c - (side - 1) / 2) * LY; } } }

  // links between near neighbours are drawn one by one; links that run far along the body travel in the nerve cord
  const CORD = 72, FAR = 0.1, near = [[], [], []], traffic = new Float32Array(CORD + 1), spur = new Uint8Array(N);
  for (let k = 0; k < NE; k++) { const a = E[2 * k], b = E[2 * k + 1], ua = WU[a], ub = WU[b], w = EW[k] || 1;
    if (Math.abs(ua - ub) > FAR) { spur[a] = spur[b] = 1; const k0 = Math.round(Math.min(ua, ub) * CORD), k1 = Math.round(Math.max(ua, ub) * CORD); for (let q = k0; q <= k1; q++) traffic[q] += 1; }
    else near[w >= 8 ? 2 : w >= 3 ? 1 : 0].push(a, b); }
  { let m = 0; for (let q = 0; q <= CORD; q++) m = Math.max(m, traffic[q]); for (let q = 0; q <= CORD; q++) traffic[q] = Math.pow(traffic[q] / m, 0.6); }

  const hero = make([2.62, 0.72], (t) => { const q = ease(hero.m); return [0.14 + 0.05 * sin(t * 0.2) + 0.06 * q, (0.16 * sin(t * 0.13)) * (1 - q) + (0.3 + 0.12 * sin(t * 0.22)) * q]; });
  hero.m = 0; hero.to = 0; hero.glow = 0.34;
  for (let i = 0; i < N; i++) { const d = hub(i); hero.del[i] = rank[i] / N; hero.lum[i] = 0.5 + 0.5 * d; hero.siz[i] = 1 + 1.5 * d; hero.col[i] = i % 3 === 0 || d > 0.4 ? GOLD : BONE; hero.alt[i] = CARM; }
  const tA = [0, 0, 0];
  hero.pos = (i, t, o) => {
    const u = WU[i], a = t * 0.3, c = cos(a), s = sin(a), y = WP[3 * i + 1], z = WP[3 * i + 2]; axis(u, t, tA);
    let X = WP[3 * i], Y = y * c - z * s + tA[1], Z = y * s + z * c + tA[2];
    const q = ease(hero.m * 1.5 - 0.5 * (rank[i] / N));
    if (q > 0) { X += (LAT[3 * i] - X) * q; Y += (LAT[3 * i + 1] - Y) * q; Z += (LAT[3 * i + 2] - Z) * q; }
    o[0] = X; o[1] = Y; o[2] = Z; o[3] = 1 + q * (0.85 / hero.lum[i] - 1); o[4] = q; o[5] = 1 + q * (1.25 / hero.siz[i] - 1);
  };

  // ================================================================ the orrery: one question at the centre, seven ways round it
  const SPHERES = ["moon", "mercury", "venus", "sun", "mars", "jupiter", "saturn"];     // the old order of the spheres, nearest first
  const orr = make([1.1, 0.6], (t) => [0.46 + 0.03 * sin(t * 0.17), 0.22 * sin(t * 0.09)]);
  orr.hl = -1; orr.planets = []; orr.seg = 0.2; orr.glow = 0.4;
  { for (let k = 0; k < 21; k++) { const a = rnd() * TAU, z = rnd() * 2 - 1, r = 0.085 * Math.cbrt(rnd()), s = Math.sqrt(1 - z * z); put(orr, r * s * cos(a), r * z, r * s * sin(a), 1.25, 1.2, GOLD, 0); }
    const R = SPHERES.map((_, k) => 0.34 + 0.11 * k), tot = R.reduce((a, b) => a + b, 0); let left = N - 21;
    SPHERES.forEach((name, k) => { const n = k === 6 ? left : Math.round(((N - 21) * R[k]) / tot); left -= n; const idx = [], a0 = rnd() * TAU;
      for (let j = 0; j < n; j++) { const back = j / n, i = put(orr, 0, 0, 0, j ? 0.2 + 0.8 * Math.exp(-back * 6) : 1.8, j ? 0.85 : 3.9, back < 0.2 ? METAL[name] : BONE, 1 + k);
        orr.aux[4 * i] = R[k]; orr.aux[4 * i + 1] = a0 - back * TAU; orr.aux[4 * i + 2] = 0.2 * Math.pow(R[k] / R[0], -1.5); orr.aux[4 * i + 3] = k; idx.push(i); if (!j) orr.planets.push(i); }
      chain(orr, idx, true, 0.2, BONE, 0.7); }); }
  const INC = SPHERES.map((_, k) => [0.1 * sin(k * 2.4 + 1), k * 0.9]);
  orr.pos = (i, t, o) => {
    const g = orr.grp[i];
    if (!g) { o[0] = orr.P[3 * i] * (1 + 0.25 * sin(t * 1.3 + i)); o[1] = orr.P[3 * i + 1]; o[2] = orr.P[3 * i + 2]; o[3] = orr.hl < 0 ? 1 : 0.7; return; }
    const k = g - 1, r = orr.aux[4 * i], a = orr.aux[4 * i + 1] + t * orr.aux[4 * i + 2], x = r * cos(a), z0 = r * sin(a), y = -z0 * sin(INC[k][0]), z = z0 * cos(INC[k][0]), cn = cos(INC[k][1]), sn = sin(INC[k][1]);
    o[0] = x * cn + z * sn; o[1] = y; o[2] = -x * sn + z * cn; o[3] = orr.hl < 0 ? 1 : k === orr.hl ? 1.5 : 0.35;
  };

  // ================================================================ the balance: a living system in one pan, a network in the other
  const bal = make([1.72, 1.08], (t) => [0.24, 0.42 * sin(t * 0.21)]);
  bal.seg = 0.34; bal.glow = 0.26; bal.tint = GOLD;
  { const FY = 0.68, ARM = 1.25, PAN = -0.34, PR = 0.42;
    const line = (n, f, lum, siz, col, grp, closed, a) => { const idx = []; for (let k = 0; k < n; k++) { const p = f(closed ? k / n : k / (n - 1)); idx.push(put(bal, p[0], p[1], p[2] || 0, lum, siz, col, grp)); } if (a !== 0) chain(bal, idx, closed, a == null ? 0.5 : a, col === BONE ? BONE : col, 0.9); return idx; };
    line(14, (q) => [-0.5 + q, -1.0], 0.7, 0.9, BONE, 0);                                         // the foot
    line(10, (q) => [-0.34 + 0.68 * q, -0.93], 0.7, 0.9, BONE, 0);
    line(30, (q) => [0, -0.93 + (FY + 0.93 - 0.07) * q], 0.75, 0.9, BONE, 0);                    // the pillar
    line(10, (q) => [0.065 * cos(q * TAU), FY + 0.065 * sin(q * TAU)], 1, 1, GOLD, 0, true, 0.5); // the pivot
    line(5, (q) => [0, FY + 0.1 + 0.16 * q], 0.8, 0.8, GOLD, 0);
    line(43, (q) => [-ARM + 2 * ARM * q, FY], 1, 1.1, GOLD, 1, false, 0.7);                      // the beam
    [-1, 1].forEach((sd) => { const g = sd < 0 ? 2 : 3, cx = sd * ARM;
      for (let c = 0; c < 3; c++) { const a = PI / 2 + (c * TAU) / 3; line(8, (q) => [cx + PR * cos(a) * q, FY + (PAN - FY) * q, PR * sin(a) * q], 0.55, 0.7, BONE, g, false, 0.32); }
      line(26, (q) => [cx + PR * cos(q * TAU), PAN, PR * sin(q * TAU)], 0.85, 0.9, GOLD, g, true, 0.6);     // the pan's rim
      line(10, (q) => [cx + PR * cos(PI * q), PAN - 0.13 * sin(PI * q), 0], 0.6, 0.8, BONE, g, false, 0.36);   // and its bowl
      for (let k = 0; k < 14; k++) { let i;
        if (sd < 0) { i = put(bal, cx - 0.26 + 0.04 * k, PAN + 0.1, 0, 1.25, 1.5, GOLD, g); bal.aux[4 * i] = k; bal.aux[4 * i + 1] = 1; }      // a small worm
        else if (k < 12) { const l = Math.floor(k / 4), w = k % 4; i = put(bal, cx - 0.3 + 0.2 * l, PAN + 0.07 + 0.12 * (w >> 1), 0.12 * ((w & 1) - 0.5), 1.25, 1.5, CARM, g); }   // a small network: three layers
        else i = put(bal, cx + 0.3, PAN + 0.07 + 0.12 * (k - 12), 0, 1.25, 1.5, CARM, g);                                                                                       // and its two outputs
      } });
    line(8, (q) => [0, FY - 0.08 - 0.3 * q], 0.9, 0.8, GOLD, 4, false, 0.45);                     // the needle
    line(11, (q) => { const a = -PI / 2 + (q - 0.5) * 1.1; return [0.44 * cos(a), FY + 0.44 * sin(a)]; }, 0.6, 0.7, BONE, 0, false, 0.2);   // and its scale
    bal.FY = FY; bal.ARM = ARM; }
  bal.pos = (i, t, o) => {
    const g = bal.grp[i], b = REDUCED ? 0.03 : 0.05 * sin(t * 0.6) + 0.018 * sin(t * 1.7); let x = bal.P[3 * i], y = bal.P[3 * i + 1]; const z = bal.P[3 * i + 2];
    if (g === 1) { const d = x; x = d * cos(b); y = bal.FY + d * sin(b); }
    else if (g === 2 || g === 3) { const sd = g === 2 ? -1 : 1; x += sd * bal.ARM * (cos(b) - 1); y += sd * bal.ARM * sin(b); if (bal.aux[4 * i + 1]) y += 0.035 * sin(t * 2.2 + bal.aux[4 * i] * 0.8); }
    else if (g === 4) { const d = y - bal.FY, a = -b * 5; x = -d * sin(a); y = bal.FY + d * cos(a); }
    o[0] = x; o[1] = y; o[2] = z;
  };

  // ================================================================ the seven planets, each a globe of points with what makes it itself
  const lightOf = (v) => norm3(v);
  function planet(name, opt) {
    const F = make(opt.ext || [1.12, 1.12], opt.rot || ((t) => [0.1 + 0.05 * sin(t * 0.37), 0.24 * sin(t * 0.3)]));
    F.name = name; F.tint = METAL[name]; F.R = opt.R; F.c = opt.c || [0, 0, 0]; F.tilt = opt.tilt || 0; F.spin = opt.spin || 0.3; F.light = lightOf(opt.light || [-0.55, 0.45, 0.7]);
    F.amb = opt.amb == null ? 0.14 : opt.amb; F.thru = opt.thru == null ? 0.06 : opt.thru; F.air = opt.air || 0; F.flat = opt.flat || 1; F.glow = opt.glow == null ? 0.5 : opt.glow; F.globe = true; F.seg = 0.12;
    for (let k = 0; k < opt.n; k++) { const y = 1 - (2 * (k + 0.5)) / opt.n, r = Math.sqrt(1 - y * y), a = k * 2.399963, i = put(F, r * cos(a), y, r * sin(a), 1, opt.dot || 1.2, F.tint, 0); if (opt.paint) opt.paint(F, i, y, a); }
    if (opt.more) opt.more(F);
    const cT = cos(F.tilt), sT = sin(F.tilt), L = F.light;
    F.turn = (x, y, z, a, o) => { const ca = cos(a), sa = sin(a), x1 = x * ca + z * sa, z1 = -x * sa + z * ca; o[0] = x1 * cT - y * sT; o[1] = (x1 * sT + y * cT) * F.flat; o[2] = z1; };
    F.pos = (i, t, o) => {
      const g = F.grp[i];
      if (g) return opt.extra(F, i, t, o, g);
      F.turn(F.P[3 * i], F.P[3 * i + 1], F.P[3 * i + 2], t * F.spin * (opt.wind ? opt.wind(F.P[3 * i + 1]) : 1), o);
      const d = o[0] * L[0] + o[1] * L[1] + o[2] * L[2];
      o[3] = (F.amb + (1 - F.amb) * Math.pow(d > 0 ? d : 0, 0.75)) * (F.thru + (1 - F.thru) * smooth((o[2] + 0.2) / 0.5)) * 1.2;
      o[0] = F.c[0] + F.R * o[0]; o[1] = F.c[1] + F.R * o[1]; o[2] = F.c[2] + F.R * o[2];
    };
    return F;
  }
  // a body circling the globe: aux = [radius, start angle, turns per second, lean]
  const circling = (F, i, t, o) => { const r = F.aux[4 * i], a = F.aux[4 * i + 1] + t * F.aux[4 * i + 2]; F.turn(r * cos(a), F.aux[4 * i + 3] * sin(a), r * sin(a), 0, o); o[3] = 0.45 + 0.55 * smooth((o[2] / r + 1) / 1.1); o[0] += F.c[0]; o[1] += F.c[1]; o[2] += F.c[2]; };
  const moonOf = (F, r, w, lum, siz, col) => { const i = put(F, 0, 0, 0, lum || 1.5, siz || 2.2, col == null ? WHITE : col, 1); F.aux[4 * i] = r; F.aux[4 * i + 1] = rnd() * TAU; F.aux[4 * i + 2] = w; (F.orbits = F.orbits || []).push(r); return i; };

  const FORMS = { hero, orrery: orr, balance: bal };
  FORMS.mercury = planet("mercury", { n: 150, R: 0.5, c: [0.5, 0.22, 0], spin: 0.5, tilt: 0.03, ext: [1.2, 1.0],
    more: (F) => { for (let k = 0; k < N - 150; k++) { const i = put(F, rnd() - 0.5, rnd() - 0.5, rnd() - 0.5, 1, 0.75, k % 4 ? METAL.mercury : WHITE, 1); F.aux[4 * i] = rnd(); } },   // the swift one sheds a tail
    extra: (F, i, t, o) => { const s = frac(F.aux[4 * i] + (REDUCED ? 0 : t * 0.09)), sp = 0.05 + 0.5 * s;
      o[0] = F.c[0] - 0.42 - 1.9 * s + F.P[3 * i] * sp * 0.5; o[1] = F.c[1] - 0.3 * s - 0.7 * s * s + F.P[3 * i + 1] * sp; o[2] = F.c[2] - 0.7 * s + F.P[3 * i + 2] * sp; o[3] = (0.08 + 1.1 * Math.pow(1 - s, 1.3)) * smooth(s / 0.07); } });
  FORMS.mercury.streak = (s, a) => { const F = s.F; [-0.5, 0, 0.5].forEach((off, q) => { const p = new Path2D(); for (let k = 0; k <= 24; k++) { const v = k / 24; proj(s, F.c[0] - 2.3 * v, F.c[1] - 0.3 * v - 0.7 * v * v + off * F.R * (1 - 0.6 * v), F.c[2] - 0.7 * v, q3); if (k) p.lineTo(q3[0], q3[1]); else p.moveTo(q3[0], q3[1]); }
      proj(s, F.c[0], F.c[1], 0, q3); const x0 = q3[0], y0 = q3[1]; proj(s, F.c[0] - 2.3, F.c[1] - 1, -0.7, q3); const g = ctx.createLinearGradient(x0, y0, q3[0], q3[1]); g.addColorStop(0, rgba(F.tint, (q === 1 ? 0.3 : 0.16) * a)); g.addColorStop(1, rgba(F.tint, 0)); ctx.lineWidth = q === 1 ? 1.4 : 0.8; ctx.strokeStyle = g; ctx.stroke(p); }); };
  FORMS.mars = planet("mars", { n: N - 2, R: 0.76, spin: 0.34, tilt: 0.44, paint: (F, i, y) => { if (Math.abs(y) > 0.93) F.col[i] = WHITE; },
    more: (F) => { moonOf(F, 1.02, 0.9); moonOf(F, 1.3, 0.42); }, extra: circling });
  FORMS.venus = planet("venus", { n: 196, R: 0.74, spin: -0.1, tilt: 0.05, light: [-0.4, 0.3, 0.86], amb: 0.2, glow: 0.7, air: 0.5,
    more: (F) => { for (let k = 0; k < N - 196; k++) { const y = 1 - (2 * (k + 0.5)) / (N - 196), r = Math.sqrt(1 - y * y), a = k * 2.399963; put(F, r * cos(a), y, r * sin(a), 0.42, 0.75, WHITE, 1); } },   // a veil of cloud, turning faster than the ground
    extra: (F, i, t, o) => { F.turn(F.P[3 * i], F.P[3 * i + 1], F.P[3 * i + 2], -t * 0.3, o); const d = o[0] * F.light[0] + o[1] * F.light[1] + o[2] * F.light[2]; o[3] = (0.2 + 0.8 * (d > 0 ? d : 0)) * smooth((o[2] + 0.3) / 0.6); const R = F.R * 1.13; o[0] *= R; o[1] *= R; o[2] *= R; } });
  FORMS.saturn = planet("saturn", { n: 148, R: 0.46, spin: 0.6, tilt: 0.42, flat: 0.92, ext: [1.14, 0.74], rot: (t) => [0.4 + 0.05 * sin(t * 0.3), 0.2 * sin(t * 0.24)],
    more: (F) => { for (let k = 0; k < N - 148; k++) { const band = k < 18 ? 0 : k < 92 ? 1 : 2, r = band === 0 ? 0.58 + 0.11 * rnd() : band === 1 ? 0.71 + 0.2 * rnd() : 0.95 + 0.1 * rnd(), i = put(F, 0, 0, 0, band === 0 ? 0.35 : band === 1 ? 0.9 : 0.65, 0.8, band === 1 ? WHITE : METAL.saturn, 1);
      F.aux[4 * i] = r; F.aux[4 * i + 1] = rnd() * TAU; F.aux[4 * i + 2] = 0.16 * Math.pow(r / 0.58, -1.5); } F.bands = [[0.575, 0.695, 5, 0.1], [0.71, 0.915, 13, 0.3], [0.95, 1.055, 6, 0.2]]; F.stripes = [[7, 0.02], [11, 0.05], [7, 0.02], [11, 0.06], [7, 0.03], [11, 0.05], [7, 0.02]]; },
    extra: circling });
  FORMS.sun = planet("sun", { n: 176, R: 0.55, spin: 0.16, tilt: 0.12, amb: 0.8, thru: 0.45, glow: 1, ext: [1.3, 1.3],
    more: (F) => { const rays = Array.from({ length: 11 }, () => norm3([rnd() - 0.5, rnd() - 0.5, (rnd() - 0.5) * 0.7]));
      for (let k = 0; k < N - 176; k++) { const d = rays[k % 11], v = norm3([d[0] + (rnd() - 0.5) * 0.16, d[1] + (rnd() - 0.5) * 0.16, d[2] + (rnd() - 0.5) * 0.16]), i = put(F, v[0], v[1], v[2], 1, 0.8, k % 3 ? METAL.sun : WHITE, 1); F.aux[4 * i] = rnd(); F.aux[4 * i + 1] = 0.05 + 0.05 * rnd(); } },
    extra: (F, i, t, o) => { const f = frac(F.aux[4 * i] + (REDUCED ? 0 : t * F.aux[4 * i + 1])), r = F.R * (1.04 + 1.25 * Math.pow(f, 1.15)), a = 0.55 * f, ca = cos(a), sa = sin(a), x = F.P[3 * i], y = F.P[3 * i + 1];
      o[0] = (x * ca - y * sa) * r; o[1] = (x * sa + y * ca) * r; o[2] = F.P[3 * i + 2] * r; o[3] = Math.pow(1 - f, 1.5) * 1.2 * smooth(f / 0.05); o[5] = 0.6 + 0.7 * (1 - f); } });
  FORMS.moon = planet("moon", { n: N, R: 0.8, spin: 0.045, tilt: 0.1, light: [0.86, 0.22, -0.46], amb: 0.13, glow: 0.42, rot: (t) => [0.06 + 0.04 * sin(t * 0.3), 0.16 * sin(t * 0.22)] });
  FORMS.jupiter = planet("jupiter", { n: N - 12, R: 0.74, spin: 0.42, tilt: 0.055, flat: 0.935, ext: [1.3, 1.0], wind: (y) => 1 + 0.4 * sin(y * 9.5),
    paint: (F, i, y) => { F.col[i] = Math.floor((Math.asin(y) / PI + 0.5) * 11) % 2 ? BELT : METAL.jupiter; },
    more: (F) => { for (let k = 0; k < 8; k++) { const a = 0.9 + 0.1 * cos(k * 0.785), la = -0.38 + 0.06 * sin(k * 0.785), i = put(F, cos(la) * cos(a), sin(la), cos(la) * sin(a), 1.3, 1.25, METAL.mars, 0); F.del[i] = 0.5; }   // the great red spot
      [[1.02, 0.5], [1.22, 0.31], [1.5, 0.2], [1.84, 0.13]].forEach(([r, w]) => moonOf(F, r, w, 1.5, 2));
      F.stripes = Array.from({ length: 11 }, (_, q) => (q % 2 ? [BELT, q === 5 ? 0.05 : 0.13] : [METAL.jupiter, 0.035])); },
    extra: circling });

  // ================================================================ the star of seven: every question joined in the order of the days
  const WEEK = ["saturn", "jupiter", "mars", "sun", "venus", "mercury", "moon"];        // round the circle; the star's lines then run Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn
  const star = make([1.32, 1.32], (t) => [0.2, 0.26 * sin(t * 0.3)]);
  star.seg = 0.2; star.glow = 0.5; star.tips = [];
  { const at = (k) => -PI / 2 + (k / 7) * TAU, ring = [];
    for (let k = 0; k < 98; k++) { const a = (k / 98) * TAU; ring.push(put(star, cos(a), -sin(a), 0, 0.6, 0.8, GOLD, 0)); }
    chain(star, ring, true, 0.5, GOLD, 0.9);
    const tip = WEEK.map((name, k) => put(star, cos(at(k)), -sin(at(k)), 0.02, 1.9, 3.6, METAL[name], 1)); star.tips = tip;
    for (let k = 0; k < 7; k++) { const a = at(k), b = at((k + 3) % 7), idx = [tip[k]];
      for (let q = 1; q <= 24; q++) { const f = q / 25; idx.push(put(star, cos(a) + (cos(b) - cos(a)) * f, -(sin(a) + (sin(b) - sin(a)) * f), 0, 0.75, 0.85, q % 2 ? GOLD : BONE, 0)); }
      idx.push(tip[(k + 3) % 7]); chain(star, idx, false, 0.55, GOLD, 1.1); }
    while (star.k < N) { const a = (star.k / 4) * TAU; put(star, 0.05 * cos(a), 0.05 * sin(a), 0, 1.2, 1.2, WHITE, 0); } }
  star.pos = (i, t, o) => { const a = REDUCED ? 0 : t * 0.04, c = cos(a), s = sin(a), x = star.P[3 * i], y = star.P[3 * i + 1]; o[0] = x * c - y * s; o[1] = x * s + y * c; o[2] = star.P[3 * i + 2] + 0.02 * sin(t * 1.1 + i); };
  FORMS.star = star;
  [orr, bal].forEach((F) => { if (!F.pos) F.pos = still(F); });

  // ---------------------------------------------------------------- at rest, the neurons are stars on a great slow drum that the page turns as it scrolls
  const DU = new Float32Array(4 * N), JIT = new Float32Array(2 * N);
  for (let i = 0; i < N; i++) { DU[4 * i] = (rnd() * 2 - 1) * 1.1; DU[4 * i + 1] = rnd() * TAU; DU[4 * i + 2] = 0.5 + 0.5 * Math.pow(rnd(), 0.7); DU[4 * i + 3] = rnd() * TAU; const a = rnd() * TAU; JIT[2 * i] = cos(a); JIT[2 * i + 1] = sin(a); }

  // ---------------------------------------------------------------- the page: a figure for every stage in the layout
  const stages = Array.from(document.querySelectorAll("[data-sky]")).map((sec) => ({ sec, box: sec.querySelector(".stage"), name: sec.dataset.sky, F: FORMS[sec.dataset.sky], w: 0, top: 0, bot: 0, left: 0, right: 0, cx: 0, cy: 0, S: 100, p: new Float32Array(N), o: new Float32Array(8) })).filter((s) => s.F && s.box);
  let measured = 0;
  function measure() { const y = scrollY; for (const s of stages) { const r = s.box.getBoundingClientRect(); s.top = r.top + y; s.bot = r.bottom + y; s.left = r.left; s.right = r.right; } measured = performance.now(); }
  const seen = (s, y) => { const c = (s.top + s.bot) / 2 - y; return smooth((H * 1.06 - c) / (H * 0.4)) * smooth((c + H * 0.04) / (H * 0.32)); };
  const heroStage = stages.find((s) => s.F === hero), orrStage = stages.find((s) => s.F === orr);

  // ---------------------------------------------------------------- signals
  const en = new Float32Array(N), pulses = [];
  let lastPoke = 0;
  function poke(i, now, power) {
    en[i] = 1; lastPoke = now; let n = 0;
    const send = (a, b, t0, p) => { const far = Math.abs(WU[a] - WU[b]) > FAR, d = far ? 320 + 1500 * Math.abs(WU[a] - WU[b]) : 440; pulses.push({ a, b, t0, d, p, far }); n++; return d; };
    adj[i].slice().sort(() => rnd() - 0.5).slice(0, 36).forEach((j) => { const d = send(i, j, now, power); adj[j].slice(0, 3).forEach((k) => { if (k !== i && n < 150) send(j, k, now + d, power * 0.6); }); });
  }
  function sweep(now) { let fr = []; for (let q = 0; q < 5; q++) fr.push(order[Math.floor(rnd() * 30)]);
    for (let l = 0; l < LAYERS - 1; l++) { const nx = new Set(); fr.forEach((a) => { if (l === 0) en[a] = 1; lnext[a].forEach((b) => { pulses.push({ a, b, t0: now + l * 300, d: 290, p: 1, far: false }); nx.add(b); }); }); fr = Array.from(nx).slice(0, 14); } }

  // ---------------------------------------------------------------- drawing
  const sprite = (c, soft) => { const s = document.createElement("canvas"); s.width = s.height = 128; const g = s.getContext("2d"), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64), k = PAL[c].join(",");
    if (soft) { gr.addColorStop(0, `rgba(${k},.5)`); gr.addColorStop(0.35, `rgba(${k},.2)`); gr.addColorStop(0.7, `rgba(${k},.05)`); gr.addColorStop(1, `rgba(${k},0)`); }
    else { gr.addColorStop(0, `rgba(${k},.55)`); gr.addColorStop(0.18, `rgba(${k},.22)`); gr.addColorStop(0.5, `rgba(${k},.06)`); gr.addColorStop(1, `rgba(${k},0)`); }
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128); return s; };
  const HALO = PAL.map((_, c) => sprite(c)), AURA = {};
  const aura = (c) => AURA[c] || (AURA[c] = sprite(c, true));
  const GLYPH = {}, GD = { mercury: "M16 22a8 8 0 1 0 16 0a8 8 0 1 0 -16 0M15 5a9 9 0 0 0 18 0M24 30v14M17 38h14", mars: "M9 28a11 11 0 1 0 22 0a11 11 0 1 0 -22 0M28 20L41 7M30 7h11v11", venus: "M14 17a10 10 0 1 0 20 0a10 10 0 1 0 -20 0M24 27v18M16 37h16",
    saturn: "M17 5v26M10 12h15M17 25c2-7 14-8 15 0 .7 6-6 9-5 15 .4 2.4 2.6 3.4 5 3", sun: "M10 24a14 14 0 1 0 28 0a14 14 0 1 0 -28 0M22 24a2 2 0 1 0 4 0a2 2 0 1 0 -4 0", moon: "M31 7a17 17 0 1 0 0 34 13.5 13.5 0 1 1 0-34z", jupiter: "M12 14c0-7 11-9 12-1 .7 6-6 12-14 18h28M31 9v34" };
  Object.keys(GD).forEach((k) => (GLYPH[k] = new Path2D(GD[k])));
  function glyph(name, x, y, size, c, a) { ctx.save(); ctx.translate(x - size / 2, y - size / 2); ctx.scale(size / 48, size / 48); ctx.lineWidth = 2.4; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.strokeStyle = rgba(c, a); ctx.stroke(GLYPH[name]); ctx.restore(); }
  const STARS = Array.from({ length: 170 }, () => ({ x: rnd(), y: rnd(), z: 0.25 + rnd() * 0.75, s: rnd() }));
  let QUAL = 2, slow = 0, lastT = 0;
  function resize() { DPR = Math.min(QUAL, devicePixelRatio || 1); W = innerWidth; H = innerHeight; cv.width = Math.round(W * DPR); cv.height = Math.round(H * DPR); measure(); }

  const sx = new Float32Array(N), sy = new Float32Array(N), sf = new Float32Array(N), sb = new Float32Array(N), ss = new Float32Array(N), sp = new Float32Array(N);
  const cr = new Float32Array(N), cg = new Float32Array(N), cb = new Float32Array(N), sh = new Uint8Array(N), q3 = [0, 0, 0];
  // a point of a figure's own space, on the screen
  function proj(s, x, y, z, o) { const x1 = x * s.cY + z * s.sY, z1 = -x * s.sY + z * s.cY, y2 = y * s.cX - z1 * s.sX, z2 = y * s.sX + z1 * s.cX, pf = CAM / (CAM - z2); o[0] = s.cx + x1 * pf * s.S; o[1] = s.cy - y2 * pf * s.S; o[2] = pf; return z2; }
  function segs(list, alpha, c, lw) { if (alpha < 0.01 || !list.length) return; const p = new Path2D(); for (let k = 0; k < list.length; k += 2) { const a = list[k], b = list[k + 1]; p.moveTo(sx[a], sy[a]); p.lineTo(sx[b], sy[b]); } ctx.lineWidth = lw; ctx.strokeStyle = rgba(c, alpha); ctx.stroke(p); }

  // ---- the worm's body, its nerve cord and its wiring; or the network's layers
  const CS = new Float32Array(2 * (CORD + 1)), SHN = 110, shL = new Float32Array(2 * (SHN + 1)), shR = new Float32Array(2 * (SHN + 1));
  hero.under = (s, a, t) => {
    const m = hero.m, live = a * smooth(1 - m * 3.2), net = a * smooth((m - 0.68) / 0.3);
    if (live > 0.01) {
      for (let k = 0; k <= CORD; k++) { axis(k / CORD, t, q3); proj(s, q3[0], q3[1], q3[2], q3); CS[2 * k] = q3[0]; CS[2 * k + 1] = q3[1]; }
      // the body: a glass sheath round the nervous system, ringed like the animal's skin
      for (let k = 0; k <= SHN; k++) { const f = k / SHN, u = -0.035 + 1.115 * (f < 0.12 ? 0.07 * Math.pow(f / 0.12, 2) : 0.07 + 0.93 * ((f - 0.12) / 0.88));   // more samples round the nose
        axis(u, t, q3); proj(s, q3[0], q3[1], q3[2], q3); const x = q3[0], y = q3[1], pf = q3[2];
        axis(u + 0.004, t, q3); proj(s, q3[0], q3[1], q3[2], q3); let tx = q3[0] - x, ty = q3[1] - y; const tl = Math.hypot(tx, ty) || 1; tx /= tl; ty /= tl;
        const v = c01((u + 0.035) / 0.085), r = (0.165 + 0.2 * taper(u)) * Math.sqrt(1 - (1 - v) * (1 - v)) * Math.pow(c01((1.08 - u) / 0.52), 1.05) * s.S * pf;
        shL[2 * k] = x - ty * r; shL[2 * k + 1] = y + tx * r; shR[2 * k] = x + ty * r; shR[2 * k + 1] = y - tx * r; }
      const body = new Path2D(), rings = new Path2D(); body.moveTo(shL[0], shL[1]);
      for (let k = 1; k <= SHN; k++) body.lineTo(shL[2 * k], shL[2 * k + 1]);
      for (let k = SHN; k >= 0; k--) body.lineTo(shR[2 * k], shR[2 * k + 1]); body.closePath();
      for (let k = 14; k < SHN - 3; k += 1) { rings.moveTo(shL[2 * k], shL[2 * k + 1]); rings.lineTo(shR[2 * k], shR[2 * k + 1]); }
      ctx.fillStyle = rgba(GOLD, 0.03 * live); ctx.fill(body);
      ctx.lineWidth = 0.6; ctx.strokeStyle = rgba(BONE, 0.04 * live); ctx.stroke(rings);
      ctx.lineWidth = 5; ctx.strokeStyle = rgba(GOLD, 0.035 * live); ctx.stroke(body);
      ctx.lineWidth = 0.9; ctx.strokeStyle = rgba(BONE, 0.3 * live); ctx.stroke(body);
      // the nerve cord, brightest where the most links run through it
      ctx.lineCap = "round";
      for (let k = 0; k < CORD; k++) { const f = (traffic[k] + traffic[k + 1]) / 2; ctx.lineWidth = 0.7 + 2.1 * f; ctx.strokeStyle = rgba(GOLD, (0.07 + 0.3 * f) * live); ctx.beginPath(); ctx.moveTo(CS[2 * k], CS[2 * k + 1]); ctx.lineTo(CS[2 * k + 2], CS[2 * k + 3]); ctx.stroke(); }
      const sp2 = new Path2D(); for (let i = 0; i < N; i++) if (spur[i]) { const k = Math.round(WU[i] * CORD); sp2.moveTo(sx[i], sy[i]); sp2.lineTo(CS[2 * k], CS[2 * k + 1]); }
      ctx.lineWidth = 0.5; ctx.strokeStyle = rgba(BONE, 0.075 * live); ctx.stroke(sp2);
      segs(near[0], 0.075 * live, BONE, 0.5); segs(near[1], 0.15 * live, BONE, 0.6); segs(near[2], 0.34 * live, GOLD, 0.9);
    }
    if (net > 0.01) { segs(LE, 0.15 * net, CARM, 0.6);
      const fr = new Path2D(), mid = (LAYERS - 1) / 2; for (let l = 0; l < FULL; l++) { const x = (l - mid) * LX, c = [[-0.56, -0.46], [0.56, -0.46], [0.56, 0.46], [-0.56, 0.46]]; c.forEach((v, k) => { proj(s, x, v[0], v[1], q3); if (k) fr.lineTo(q3[0], q3[1]); else fr.moveTo(q3[0], q3[1]); }); fr.closePath(); }
      ctx.fillStyle = rgba(CARM, 0.016 * net); ctx.fill(fr); ctx.lineWidth = 0.7; ctx.strokeStyle = rgba(CARM, 0.2 * net); ctx.stroke(fr); }
  };

  // ---- a globe: a solid body with a lit phase, its limb, its lines of latitude, its axis; then whatever circles it
  const lat = [-1.05, -0.52, 0, 0.52, 1.05];
  function ringPath(s, F, r, yy, front, back, n) { let px = 0, py = 0, pz = 0;
    for (let k = 0; k <= n; k++) { const a = (k / n) * TAU; F.turn(r * cos(a), yy, r * sin(a), 0, q3); const z = proj(s, F.c[0] + q3[0], F.c[1] + q3[1], F.c[2] + q3[2], q3);
      if (k) { const p = z + pz > 0 ? front : back; p.moveTo(px, py); p.lineTo(q3[0], q3[1]); } px = q3[0]; py = q3[1]; pz = z; } }
  function globeUnder(s, a, t) {
    const F = s.F, c = F.tint, L = F.light, sun = F.name === "sun"; proj(s, F.c[0], F.c[1], F.c[2], q3); const x = q3[0], y = q3[1], R = F.R * s.S * q3[2];
    // what circles it: the far half first, so the body can hide it
    const of = new Path2D(), ob = new Path2D(); (F.orbits || []).forEach((r) => ringPath(s, F, r, 0, of, ob, 72));
    const bands = (F.bands || []).map((b) => { const f = new Path2D(), k = new Path2D(); for (let q = 0; q < b[2]; q++) ringPath(s, F, b[0] + ((b[1] - b[0]) * (q + 0.5)) / b[2], 0, f, k, 96); return [f, k, b[3]]; });
    ctx.lineWidth = 0.6; ctx.strokeStyle = rgba(c, 0.1 * a); ctx.stroke(ob); bands.forEach((b) => { ctx.strokeStyle = rgba(c, b[2] * 0.55 * a); ctx.stroke(b[1]); });
    if (F.streak) F.streak(s, a, t);
    if (sun) { ctx.globalAlpha = 0.85 * a; ctx.drawImage(aura(c), x - R * 3.4, y - R * 3.4, R * 6.8, R * 6.8); ctx.globalAlpha = 1; }
    if (F.air) { const ag = ctx.createRadialGradient(x, y, R * 0.92, x, y, R * 1.42); ag.addColorStop(0, rgba(c, F.air * a)); ag.addColorStop(0.3, rgba(c, F.air * 0.35 * a)); ag.addColorStop(1, rgba(c, 0)); ctx.fillStyle = ag; ctx.beginPath(); ctx.arc(x, y, R * 1.42, 0, TAU); ctx.fill(); }
    const disc = new Path2D(); disc.ellipse(x, y, R, R * F.flat, -F.tilt, 0, TAU);
    if (!sun) { ctx.globalCompositeOperation = "destination-out"; ctx.fillStyle = `rgba(0,0,0,${(0.93 * a).toFixed(3)})`; ctx.fill(disc); ctx.globalCompositeOperation = "lighter"; }
    // the body: a faint whole disc, then the part the light reaches
    const g = ctx.createRadialGradient(x + L[0] * R * 0.6, y - L[1] * R * 0.6, R * 0.05, x + L[0] * R * 0.15, y - L[1] * R * 0.15, R * 1.05);
    g.addColorStop(0, rgba(c, (sun ? 0.55 : 0.2) * a)); g.addColorStop(0.6, rgba(c, (sun ? 0.2 : 0.06) * a)); g.addColorStop(1, rgba(c, 0.02 * a));
    ctx.fillStyle = g; ctx.fill(disc);
    if (!sun) { const an = Math.atan2(-L[1], L[0]), lz = L[2]; ctx.save(); ctx.translate(x, y); ctx.rotate(an);
      const ph = new Path2D(); ph.arc(0, 0, R, -PI / 2, PI / 2); ph.ellipse(0, 0, Math.max(0.5, Math.abs(lz) * R), R, 0, PI / 2, lz < 0 ? -PI / 2 : 1.5 * PI, lz < 0); ph.closePath();
      const pg = ctx.createLinearGradient(R, 0, -R * 0.6, 0); pg.addColorStop(0, rgba(c, 0.34 * a)); pg.addColorStop(0.45, rgba(c, 0.15 * a)); pg.addColorStop(1, rgba(c, 0.03 * a)); ctx.fillStyle = pg; ctx.fill(ph);
      ctx.lineCap = "round"; ctx.lineWidth = 7; ctx.strokeStyle = rgba(c, 0.07 * a); ctx.beginPath(); ctx.arc(0, 0, R, -1.25, 1.25); ctx.stroke();          // light caught on the limb
      ctx.lineWidth = 1.5; ctx.strokeStyle = rgba(WHITE, 0.5 * a); ctx.beginPath(); ctx.arc(0, 0, R, -1.15, 1.15); ctx.stroke(); ctx.restore(); }
    if (F.stripes) { ctx.save(); ctx.clip(disc); ctx.translate(x, y); ctx.rotate(-F.tilt); const n = F.stripes.length;                                         // belts of cloud
      for (let q = 0; q < n; q++) { const y0 = -R * F.flat * sin(-PI / 2 + (PI * q) / n), y1 = -R * F.flat * sin(-PI / 2 + (PI * (q + 1)) / n); ctx.fillStyle = rgba(F.stripes[q][0], F.stripes[q][1] * a); ctx.fillRect(-R, y1, 2 * R, y0 - y1); } ctx.restore(); }
    ctx.lineWidth = 0.8; ctx.strokeStyle = rgba(c, 0.3 * a); ctx.stroke(disc);
    const front = new Path2D(), back = new Path2D(); lat.forEach((la) => ringPath(s, F, F.R * cos(la), F.R * sin(la), front, back, 48));
    ctx.lineWidth = 0.6; ctx.strokeStyle = rgba(c, 0.12 * a); ctx.stroke(front);
    // its axis, showing past the poles
    const ax = new Path2D(); [[-1.36, -1.03], [1.03, 1.36]].forEach((e) => { F.turn(0, e[0] * F.R, 0, 0, q3); proj(s, F.c[0] + q3[0], F.c[1] + q3[1], F.c[2] + q3[2], q3); ax.moveTo(q3[0], q3[1]); F.turn(0, e[1] * F.R, 0, 0, q3); proj(s, F.c[0] + q3[0], F.c[1] + q3[1], F.c[2] + q3[2], q3); ax.lineTo(q3[0], q3[1]); });
    ctx.lineWidth = 0.8; ctx.strokeStyle = rgba(c, 0.4 * a); ctx.stroke(ax);
    ctx.lineWidth = 0.6; ctx.strokeStyle = rgba(c, 0.26 * a); ctx.stroke(of); bands.forEach((b) => { ctx.strokeStyle = rgba(c, b[2] * a); ctx.stroke(b[0]); });
  }
  Object.keys(METAL).forEach((n) => (FORMS[n].under = globeUnder));
  // a graduated circle, as on the limb of an old instrument: n ticks from r0 to r1, every k-th one longer; flat to the viewer, or lying in the figure's ground plane
  function dial(s, r0, r1, n, every, long, ground, spin, alpha, c) {
    const p = new Path2D(), ring = new Path2D(), at = (r, a) => { const x = r * cos(a), y = r * sin(a); if (ground) proj(s, x, 0, y, q3); else proj(s, x, y, 0, q3); };
    for (let k = 0; k < n; k++) { const a = spin + (k / n) * TAU; at(r0, a); p.moveTo(q3[0], q3[1]); at(k % every ? r1 : long, a); p.lineTo(q3[0], q3[1]); }
    for (let k = 0; k <= 120; k++) { at(r0, (k / 120) * TAU); if (k) ring.lineTo(q3[0], q3[1]); else ring.moveTo(q3[0], q3[1]); }
    ctx.lineWidth = 0.7; ctx.strokeStyle = rgba(c, alpha); ctx.stroke(p); ctx.strokeStyle = rgba(c, alpha * 0.8); ctx.stroke(ring);
  }
  orr.under = (s, a, t) => { dial(s, 1.1, 1.125, 84, 7, 1.15, true, REDUCED ? 0 : t * 0.01, 0.2 * a, BONE); proj(s, 0, 0, 0, q3); const r = s.S * 0.5; ctx.globalAlpha = 0.9 * a; ctx.drawImage(aura(GOLD), q3[0] - r, q3[1] - r, 2 * r, 2 * r); ctx.globalAlpha = 1; };
  star.under = (s, a, t) => { const r = REDUCED ? 0 : t * 0.04; dial(s, 1.055, 1.085, 84, 12, 1.115, false, r, 0.3 * a, GOLD);
    const wide = new Path2D(), inner = new Path2D(), at = (k, R) => { const an = -PI / 2 + (k / 7) * TAU + r; proj(s, R * cos(an), -R * sin(an), 0, q3); };
    for (let k = 0; k < 7; k++) { at(k, 1); wide.moveTo(q3[0], q3[1]); at(k + 3, 1); wide.lineTo(q3[0], q3[1]); at(k + 0.5, 0.36); if (k) inner.lineTo(q3[0], q3[1]); else inner.moveTo(q3[0], q3[1]); } inner.closePath();
    ctx.lineWidth = 6; ctx.strokeStyle = rgba(GOLD, 0.05 * a); ctx.stroke(wide); ctx.fillStyle = rgba(GOLD, 0.05 * a); ctx.fill(inner); ctx.lineWidth = 0.7; ctx.strokeStyle = rgba(GOLD, 0.3 * a); ctx.stroke(inner); };
  orr.over = (s, a) => { SPHERES.forEach((name, k) => { const i = orr.planets[k], on = orr.hl < 0 ? 0.85 : k === orr.hl ? 1 : 0.3; glyph(name, sx[i] + 20, sy[i] - 18, 21, METAL[name], a * on); });
    if (orr.hl >= 0 && orr.label) { const i = orr.planets[orr.hl]; ctx.font = "italic 500 21px Cormorant, Georgia, serif"; ctx.textAlign = "left"; ctx.fillStyle = rgba(WHITE, a); ctx.fillText(orr.label, sx[i] + 38, sy[i] - 10); } };
  star.over = (s, a, t) => { const r = REDUCED ? 0 : t * 0.04; WEEK.forEach((name, k) => { const an = -PI / 2 + (k / 7) * TAU, x = 1.24 * cos(an), y = -1.24 * sin(an); proj(s, x * cos(r) - y * sin(r), x * sin(r) + y * cos(r), 0, q3); glyph(name, q3[0], q3[1], Math.max(18, s.S * 0.11), METAL[name], 0.95 * a); }); };

  let px = 0, py = 0, tpx = 0, tpy = 0, mx = -1e4, my = -1e4, hoverI = -1, lastAuto = 0, heroHold = 0, heroForm = "worm", born = 0, hit = -1;
  function frame(now) {
    requestAnimationFrame(frame); if (document.hidden) { lastT = 0; return; }
    const dt = lastT ? Math.min(80, now - lastT) : 16;
    if (lastT) { slow = now - lastT > 30 ? slow + 1 : Math.max(0, slow - 2); if (slow > 45 && QUAL > 1) { QUAL = QUAL > 1.5 ? 1.5 : 1; slow = 0; resize(); } } lastT = now;   // keep it smooth on slow machines
    if (!born) born = now; if (now - measured > 700) measure();
    const t = REDUCED ? 8 : now / 1000, y0 = scrollY;
    px += (tpx - px) * 0.05; py += (tpy - py) * 0.05;

    // ---- how much of each figure is in, from where the page is
    const k = REDUCED ? 1 : 1 - Math.exp(-dt / (now - born < 1600 ? 520 : 150)); let top = null; const live = [];
    for (const s of stages) { s.w += (seen(s, y0) - s.w) * k; if (s.w < 0.003) continue; live.push(s); if (!top || s.w > top.w) top = s;
      const F = s.F, c = (s.top + s.bot) / 2 - y0, r = F.rot(t), rx = r[0] + py * 0.1, ry = r[1] + px * 0.16;
      s.cx = (s.left + s.right) / 2; s.cy = H * 0.5 + (c - H * 0.5) * 0.92; s.S = Math.min((s.right - s.left) / (2 * F.ext[0]), (s.bot - s.top) / (2 * F.ext[1]));
      s.cX = cos(rx); s.sX = sin(rx); s.cY = cos(ry); s.sY = sin(ry); s.unit = Math.max(0.62, Math.min(1.3, s.S / 190)); }
    if (heroStage) { const d = hero.to - hero.m; hero.m = REDUCED ? hero.to : hero.m + Math.sign(d) * Math.min(Math.abs(d), dt / 2300);
      if (!REDUCED && heroStage.w > 0.95 && now > heroHold && now - lastAuto > 9000) { lastAuto = now; setHero(heroForm === "worm" ? "lattice" : "worm", now, true); } }

    // ---- every point: its star, pulled toward whichever figures are in
    const turn = (y0 / H) * 0.8 + (REDUCED ? 0 : t * 0.012), RD = 0.7 * H, far = Math.min(W, H);
    for (let i = 0; i < N; i++) {
      const th = DU[4 * i + 1] + turn, rho = DU[4 * i + 2] * RD, dz = rho * cos(th), dpf = (2.4 * H) / (2.4 * H - dz);
      let X = W * 0.5 + DU[4 * i] * W * 0.5 * (0.7 + 0.3 * dpf), Y = H * 0.5 - rho * sin(th) * dpf, P = dpf * 0.8;
      let Bq = (0.16 + 0.34 * hub(i) + 0.2 * DU[4 * i + 2]) * smooth((dz / rho + 0.3) / 0.75) * (REDUCED ? 0.85 : 0.72 + 0.28 * sin(t * (0.5 + DU[4 * i + 3] * 0.2) + DU[4 * i + 3] * 9));
      let Sz = 0.8 + 0.9 * hub(i), R = i % 3 ? PAL[BONE][0] : PAL[GOLD][0], G = i % 3 ? PAL[BONE][1] : PAL[GOLD][1], Bl = i % 3 ? PAL[BONE][2] : PAL[GOLD][2], halo = i % 3 ? BONE : GOLD;
      const dx = X, dy = Y, dP = P, dB = Bq, dS = Sz, dR = R, dG = G, dBl = Bl; let sum = 0, best = 0;
      for (const s of live) { const p = ease(s.w * 1.45 - 0.45 * s.F.del[i]); s.p[i] = p; sum += p; }
      const nrm = sum > 1 ? 1 / sum : 1; sum = 0;
      for (const s of live) { const p = s.p[i] * nrm; if (p <= 0) continue; const F = s.F, o = s.o; o[3] = 1; o[4] = 0; o[5] = 1; F.pos(i, t, o);
        proj(s, o[0], o[1], o[2], q3); const c = PAL[F.col[i]], c2 = PAL[F.alt[i]], m = o[4];
        X += (q3[0] - dx) * p; Y += (q3[1] - dy) * p; P += (q3[2] - dP) * p; Bq += (F.lum[i] * o[3] - dB) * p; Sz += (F.siz[i] * o[5] * s.unit - dS) * p;
        R += (c[0] + (c2[0] - c[0]) * m - dR) * p; G += (c[1] + (c2[1] - c[1]) * m - dG) * p; Bl += (c[2] + (c2[2] - c[2]) * m - dBl) * p; sum += p;
        if (p > best) { best = p; if (p > 0.5) halo = m > 0.5 ? F.alt[i] : F.col[i]; } }
      // in flight a point swings wide of the straight line, and the pointer parts the stars a little
      const arc = sin(PI * c01(sum)) * far * 0.05; X += JIT[2 * i] * arc; Y += JIT[2 * i + 1] * arc;
      const ddx = X - mx, ddy = Y - my, d2 = ddx * ddx + ddy * ddy; if (d2 < 25600 && d2 > 1) { const d = Math.sqrt(d2), f = (1 - d / 160) * (1 - d / 160) * 18 * (1 - 0.8 * sum); X += (ddx / d) * f; Y += (ddy / d) * f; }
      sx[i] = X; sy[i] = Y; sf[i] = P; sb[i] = Bq; ss[i] = Sz; sp[i] = sum; cr[i] = R; cg[i] = G; cb[i] = Bl; sh[i] = halo; en[i] *= 0.965;
    }

    ctx.setTransform(DPR, 0, 0, DPR, 0, 0); ctx.clearRect(0, 0, W, H);
    // far stars, drifting a little with the scroll
    const so = y0 * 0.06; ctx.fillStyle = `rgb(${PAL[BONE].join(",")})`;
    for (const st of STARS) { let y = (st.y * (H + 200) - so * st.z) % (H + 200); if (y < 0) y += H + 200; const tw = REDUCED ? 0.7 : 0.55 + 0.45 * sin(t * (0.6 + st.s) + st.s * 40);
      ctx.globalAlpha = 0.5 * st.z * tw; const d = st.z > 0.85 ? 1.6 : 1; ctx.fillRect(Math.round(st.x * W + px * 14 * st.z), Math.round(y - 100), d, d); }
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = "lighter";

    // ---- each figure's light and line work, once its points have landed
    for (const s of live) { const F = s.F, a = smooth((s.w - 0.74) / 0.26), glow = F.glow * s.w * s.w, ax = F.ext[0] * s.S * 1.35, ay = F.ext[1] * s.S * 2;
      if (glow > 0.01) { ctx.globalAlpha = Math.min(1, glow); ctx.drawImage(aura(F === hero && hero.m > 0.5 ? CARM : F.tint), s.cx - ax, s.cy - ay, 2 * ax, 2 * ay); ctx.globalAlpha = 1; }
      if (a < 0.01) continue;
      if (F.under) F.under(s, a, t);
      const lim = s.S * F.seg;
      for (const ch of F.chains) { const p = new Path2D(), id = ch.idx, n = id.length; for (let q = 0; q < (ch.closed ? n : n - 1); q++) { const i = id[q], j = id[(q + 1) % n]; if (Math.abs(sx[i] - sx[j]) + Math.abs(sy[i] - sy[j]) < lim) { p.moveTo(sx[i], sy[i]); p.lineTo(sx[j], sy[j]); } }
        ctx.lineWidth = ch.w; ctx.strokeStyle = rgba(ch.c, ch.a * a * (F === orr && orr.hl >= 0 ? 0.6 : 1)); ctx.stroke(p); }
    }

    // ---- signals in flight: along a link, or down the nerve cord
    const hw = heroStage ? smooth((heroStage.w - 0.8) / 0.2) : 0, pc = hero.m > 0.5 ? [255, 190, 205] : PAL[GOLD];
    for (let q = pulses.length - 1; q >= 0; q--) { const pu = pulses[q], u = (now - pu.t0) / pu.d; if (u >= 1) { en[pu.b] = Math.max(en[pu.b], pu.p); pulses.splice(q, 1); continue; } if (u < 0 || hw < 0.02) continue;
      const at = (v, o) => { if (!pu.far) { o[0] = sx[pu.a] + (sx[pu.b] - sx[pu.a]) * v; o[1] = sy[pu.a] + (sy[pu.b] - sy[pu.a]) * v; return; }
        const ka = WU[pu.a] * CORD, kb = WU[pu.b] * CORD;
        if (v < 0.14) { const f = v / 0.14, k0 = Math.round(ka); o[0] = sx[pu.a] + (CS[2 * k0] - sx[pu.a]) * f; o[1] = sy[pu.a] + (CS[2 * k0 + 1] - sy[pu.a]) * f; }
        else if (v > 0.86) { const f = (v - 0.86) / 0.14, k1 = Math.round(kb); o[0] = CS[2 * k1] + (sx[pu.b] - CS[2 * k1]) * f; o[1] = CS[2 * k1 + 1] + (sy[pu.b] - CS[2 * k1 + 1]) * f; }
        else { const kk = ka + (kb - ka) * ((v - 0.14) / 0.72), k0 = Math.min(CORD - 1, Math.floor(kk)), f = kk - k0; o[0] = CS[2 * k0] + (CS[2 * k0 + 2] - CS[2 * k0]) * f; o[1] = CS[2 * k0 + 1] + (CS[2 * k0 + 3] - CS[2 * k0 + 1]) * f; } };
      at(u, q3); const x = q3[0], y = q3[1]; at(Math.max(0, u - (pu.far ? 0.07 : 0.16)), q3);
      ctx.strokeStyle = `rgba(${pc[0]},${pc[1]},${pc[2]},${(0.85 * pu.p * hw).toFixed(3)})`; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(q3[0], q3[1]); ctx.lineTo(x, y); ctx.stroke();
      ctx.globalAlpha = 0.6 * pu.p * hw; ctx.drawImage(HALO[hero.m > 0.5 ? CARM : GOLD], x - 9, y - 9, 18, 18); ctx.globalAlpha = 1; }

    // ---- the neurons: a soft halo on the bright ones, then a hard core
    for (let i = 0; i < N; i++) { const e = en[i] * hw, b = sb[i] + e; if (b < 0.02) continue; const pf = sf[i], rr = Math.max(0.35, (0.55 + 0.62 * ss[i] + 2.2 * e) * pf), a = Math.min(1, b);
      if (ss[i] > 1.55 || e > 0.04 || b > 1.25) { const h = rr * (5 + 4 * e + ss[i]); ctx.globalAlpha = Math.min(1, a * (0.42 + 0.6 * e + 0.12 * ss[i])); ctx.drawImage(HALO[e > 0.3 && sh[i] !== CARM ? GOLD : sh[i]], sx[i] - h, sy[i] - h, 2 * h, 2 * h); }
      ctx.globalAlpha = a; const w = Math.min(1, e + Math.max(0, b - 1) * 0.6);
      ctx.fillStyle = `rgb(${Math.round(cr[i] + (255 - cr[i]) * w)},${Math.round(cg[i] + (250 - cg[i]) * w)},${Math.round(cb[i] + (238 - cb[i]) * w)})`;
      ctx.beginPath(); ctx.arc(sx[i], sy[i], rr, 0, TAU); ctx.fill(); }
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over";

    // ---- what is written on the sky
    for (const s of live) { const a = smooth((s.w - 0.8) / 0.2); if (a > 0.01 && s.F.over) s.F.over(s, a, t); }
    const wormOn = heroStage && heroStage.w > 0.97 && hero.m < 0.02;
    if (wormOn) { let best = -1, bd = 26 * 26; for (let i = 0; i < N; i++) { const dx = sx[i] - mx, dy = sy[i] - my, q = dx * dx + dy * dy; if (q < bd) { bd = q; best = i; } } hoverI = best;
      if (best >= 0) { ctx.strokeStyle = "rgba(240,207,120,.9)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(sx[best], sy[best], 9, 0, TAU); ctx.stroke();
        ctx.font = "italic 500 22px Cormorant, Georgia, serif"; ctx.fillStyle = "#f0cf78"; ctx.textAlign = "center"; ctx.fillText(B.names[best], sx[best], sy[best] - 18); }
      if (!REDUCED && now - lastPoke > 1500) poke(order[Math.floor(Math.pow(rnd(), 1.8) * N)], now, 0.8);
    } else hoverI = -1;
    if (heroStage && heroStage.w > 0.97 && hero.m > 0.98 && !REDUCED && now - lastPoke > 2300) { lastPoke = now; sweep(now); }
    // the planets of the orrery answer the pointer
    if (orrStage && orrStage.w > 0.9) { let best = -1, bd = 30 * 30; orr.planets.forEach((i, q) => { const dx = sx[i] - mx, dy = sy[i] - my, d = dx * dx + dy * dy; if (d < bd) { bd = d; best = q; } });
      if (best !== hit) { hit = best; document.documentElement.style.cursor = best >= 0 ? "pointer" : ""; if (api.onplanet) api.onplanet(best >= 0 ? SPHERES[best] : null); } }
    else if (hit >= 0) { hit = -1; document.documentElement.style.cursor = ""; if (api.onplanet) api.onplanet(null); }
    const nm = top && top.w > 0.5 ? (top.F === hero ? (hero.m > 0.5 ? "lattice" : "worm") : top.name) : "stars"; if (document.documentElement.dataset.sky !== nm) document.documentElement.dataset.sky = nm;
  }

  // ---------------------------------------------------------------- the page drives it
  const cap = document.getElementById("hero-cap"), words = Array.from(document.querySelectorAll("[data-form]"));
  const CAP = { worm: "The worm’s 279 connected neurons, head to tail, wired as they really are. Touch one to send a signal.", lattice: "The same 279 units, wired as an artificial network. Signals march one way, layer by layer." };
  function setHero(name, now, auto) { heroForm = name; hero.to = name === "lattice" ? 1 : 0; if (!auto) heroHold = now + 24000; lastAuto = now; pulses.length = 0;
    words.forEach((w) => { w.classList.toggle("on", w.dataset.form === name); w.setAttribute("aria-pressed", String(w.dataset.form === name)); }); if (cap) cap.textContent = CAP[name]; }
  // other scripts can light one sphere of the orrery (a card under the pointer), and hear which one the pointer is on
  const api = (window.NEMATICA_SKY = { light(name, label) { orr.hl = name ? SPHERES.indexOf(name) : -1; orr.label = label || ""; }, onplanet: null, pick: null });
  words.forEach((w) => w.addEventListener("click", () => setHero(w.dataset.form, performance.now(), false)));
  addEventListener("pointermove", (e) => { tpx = (e.clientX / W - 0.5) * 2; tpy = (e.clientY / H - 0.5) * 2; mx = e.clientX; my = e.clientY; }, { passive: true });
  addEventListener("pointerleave", () => { mx = my = -1e4; });
  addEventListener("pointerdown", (e) => { if (e.target.closest("a,button,nav,header,input,label")) return; mx = e.clientX; my = e.clientY;
    if (hit >= 0 && api.pick) { api.pick(SPHERES[hit]); return; }
    if (!heroStage || heroStage.w < 0.9 || hero.m > 0.05) return;
    let best = -1, bd = 34 * 34; for (let i = 0; i < N; i++) { const dx = sx[i] - mx, dy = sy[i] - my, q = dx * dx + dy * dy; if (q < bd) { bd = q; best = i; } } if (best >= 0) poke(best, performance.now(), 1); });
  addEventListener("resize", resize); addEventListener("load", measure); if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure);
  resize(); setHero("worm", performance.now(), true); requestAnimationFrame(frame);
})();
