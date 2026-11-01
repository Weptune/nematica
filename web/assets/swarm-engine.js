/* Seeded, live behavioral sandbox. Fitted model runs supply individual motion priors;
   the copper and contact rules here are explicit, uncalibrated assumptions. */
(function (root) {
  "use strict";
  const TAU = Math.PI * 2;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const angleDiff = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b));
  function random(seed) {
    let s = seed >>> 0;
    return () => {
      s += 0x6D2B79F5;
      let t = s;
      t = Math.imul(t ^ t >>> 15, t | 1);
      t ^= t + Math.imul(t ^ t >>> 7, t | 61);
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function body(agent, length, points = 12) {
    const pts = [[agent.x, agent.y]];
    const ux = Math.cos(agent.heading), uy = Math.sin(agent.heading);
    const px = -uy, py = ux;
    for (let k = 1; k <= points; k++) {
      const q = k / points;
      const wave = .048 * Math.sin(TAU * (agent.phase - 1.45 * q)) * Math.sin(Math.PI * q);
      pts.push([agent.x - ux * length * q + px * wave, agent.y - uy * length * q + py * wave]);
    }
    return pts;
  }
  function pointDistance(x, y, points) {
    let best = Infinity, closest = null;
    for (const p of points) {
      const d = Math.hypot(x - p[0], y - p[1]);
      if (d < best) { best = d; closest = p; }
    }
    return { distance: best, point: closest };
  }
  function closeBodies(a, b, threshold) {
    for (const p of a) for (const q of b)
      if (Math.hypot(p[0] - q[0], p[1] - q[1]) < threshold) return true;
    return false;
  }
  function create({ profiles, seed = 7, interact = true, radius = 4.067, length = .77, dt = .6 }) {
    if (!profiles || !profiles.length) throw new Error("The swarm needs motion profiles.");
    const n = profiles.length;
    let rng = random(seed);
    let agents, frame, counters, events;
    function start() {
      rng = random(seed);
      agents = [];
      for (let i = 0; i < n; i++) {
        let x, y, attempts = 0;
        do {
          const r = Math.sqrt(rng()) * (radius - .85), a = rng() * TAU;
          x = r * Math.cos(a); y = r * Math.sin(a);
        } while (++attempts < 400 && agents.some(w => Math.hypot(w.x - x, w.y - y) < .48));
        const heading = rng() * TAU;
        agents.push({ x, y, heading, phase: rng(), turn: 0, reversing: false,
          reverseLeft: 0, cooldown: 0, touch: false, density: 0, blocked: false,
          profile: profiles[i], path: [[x, y]], steerSign: rng() < .5 ? -1 : 1 });
      }
      frame = 0;
      counters = { contact: 0, clustered: 0, copper: 0, blocked: 0, reversals: 0,
        exposure: [0, 0, 0], onsets: [0, 0, 0] };
      events = { contacts: 0, clusters: 0, reversing: 0, blocked: 0, copper: 0 };
    }
    function step() {
      const bodies = agents.map(a => body(a, length));
      const touch = Array(n).fill(false), density = Array(n).fill(0);
      const parent = Array.from({ length: n }, (_, i) => i);
      const find = i => { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; };
      for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
        const separation = Math.hypot(agents[i].x - agents[j].x, agents[i].y - agents[j].y);
        if (separation < 1) { density[i]++; density[j]++; }
        if (separation > length * 2 + .16) continue;
        if (pointDistance(agents[i].x, agents[i].y, bodies[j]).distance < .12) touch[i] = true;
        if (pointDistance(agents[j].x, agents[j].y, bodies[i]).distance < .12) touch[j] = true;
        if (closeBodies(bodies[i], bodies[j], .105)) parent[find(i)] = find(j);
      }
      const components = Array(n).fill(0);
      for (let i = 0; i < n; i++) components[find(i)]++;
      let contacts = 0, clustered = 0, reversing = 0, blocked = 0, nearCopper = 0;
      const proposed = [];
      for (let i = 0; i < n; i++) {
        const a = agents[i], p = a.profile;
        a.touch = touch[i]; a.density = density[i]; a.blocked = false;
        contacts += +touch[i]; clustered += +(components[find(i)] > 1);
        const bin = Math.min(2, density[i]);
        if (!a.reversing) counters.exposure[bin]++;
        if (a.cooldown > 0) a.cooldown--;
        if (a.reversing) {
          if (--a.reverseLeft <= 0) {
            a.reversing = false;
            a.cooldown = Math.round(2.4 / dt);
            a.heading += a.steerSign * (.45 + rng() * .6);
          }
        }
        const r = Math.hypot(a.x, a.y), edge = radius - r;
        const outward = r ? (a.x * Math.cos(a.heading) + a.y * Math.sin(a.heading)) / r : 0;
        const spontaneous = 1 - Math.exp(-p.reversals_per_min * dt / 60);
        const contactChance = interact && touch[i] ? .3 : 0;
        const copperTurn = !a.reversing && edge < .26 && outward > .1;
        if (!a.reversing && a.cooldown === 0 && (rng() < spontaneous + contactChance - spontaneous * contactChance || copperTurn)) {
          a.reversing = true;
          a.reverseLeft = Math.round((2.4 + rng() * 2.4) / dt);
          counters.reversals++; counters.onsets[bin]++;
        }
        // Persistent turning and a gradual turn away from the copper line.
        a.turn = .76 * a.turn + (rng() - rng()) * p.turn_rad_step * .68;
        a.heading += a.turn;
        if (!a.reversing && edge < 1.2 && outward > -.2) {
          const inward = Math.atan2(-a.y, -a.x);
          let delta = angleDiff(inward, a.heading);
          if (Math.abs(delta) > 3.05) delta = a.steerSign * Math.PI;
          a.heading += clamp(delta, -.13, .13) * (1 - clamp(edge / 1.2, 0, 1));
        }
        const speed = a.reversing ? p.reverse_mm_s : p.forward_mm_s;
        const direction = a.reversing ? -1 : 1;
        proposed.push([a.x + direction * speed * dt * Math.cos(a.heading),
          a.y + direction * speed * dt * Math.sin(a.heading)]);
        a.phase = (a.phase + dt * (a.reversing ? -.75 : 1.0)) % 1;
        reversing += +a.reversing;
      }
      for (let i = 0; i < n; i++) {
        const a = agents[i]; let [x, y] = proposed[i];
        if (interact) {
          let now = Infinity, next = Infinity, closest = null;
          for (let j = 0; j < n; j++) {
            if (i === j) continue;
            const d0 = pointDistance(a.x, a.y, bodies[j]).distance;
            const d1 = pointDistance(x, y, bodies[j]);
            if (d0 < now) now = d0;
            if (d1.distance < next) { next = d1.distance; closest = d1.point; }
          }
          if (next < .105 && next < now && closest) {
            const dx = x - closest[0], dy = y - closest[1], mag = Math.hypot(dx, dy) || 1;
            x = a.x + (x - a.x) * .2 + dx / mag * (.105 - next) * .45;
            y = a.y + (y - a.y) * .2 + dy / mag * (.105 - next) * .45;
            a.blocked = true; blocked++;
          }
        }
        // The copper line is a cue. The tiny outer tolerance is an explicit
        // containment assumption so this exploratory run cannot drift away.
        const r = Math.hypot(x, y), maxR = radius + .12;
        if (r > maxR) {
          x *= maxR / r; y *= maxR / r;
          a.heading = Math.atan2(y, x);
          a.reversing = true;
          a.reverseLeft = Math.max(a.reverseLeft, Math.round(3 / dt));
        }
        a.x = x; a.y = y;
        a.path.push([x, y]);
        if (a.path.length > 150) a.path.shift();
        nearCopper += +(radius - Math.hypot(x, y) < .5);
      }
      frame++;
      counters.contact += contacts; counters.clustered += clustered; counters.copper += nearCopper; counters.blocked += blocked;
      events = { contacts, clusters: clustered, reversing, blocked, copper: nearCopper };
      return snapshot();
    }
    function snapshot() {
      const samples = Math.max(1, n * frame), minutes = dt / 60;
      const rate = k => counters.exposure[k] * minutes > .05 ? counters.onsets[k] / (counters.exposure[k] * minutes) : 0;
      return { agents, frame, time: frame * dt, events,
        summary: { contact: counters.contact / samples, cluster: counters.clustered / samples,
          copper: counters.copper / samples, blocked: counters.blocked / samples,
          rev0: rate(0), rev2: rate(2), reversals: counters.reversals } };
    }
    function seek(target) {
      target = Math.max(0, Math.floor(target));
      if (target < frame) start();
      while (frame < target) step();
      return snapshot();
    }
    start();
    return { step, snapshot, seek, body: a => body(a, length), radius, length, dt, seed, interact };
  }
  root.NematicaSwarmEngine = { create, body };
  if (typeof module !== "undefined") module.exports = root.NematicaSwarmEngine;
})(typeof window !== "undefined" ? window : globalThis);
