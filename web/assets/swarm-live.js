/* Live swarm sandbox driven by fitted per-worm motion priors. */
(function () {
  "use strict";
  const host = document.getElementById("swarm");
  const data = window.NEMATICA_SWARM_PROFILES;
  if (!host) return;
  if (!data || !window.NematicaSwarmEngine) {
    host.querySelector(".swarm-stage").innerHTML = '<p class="scope-empty">The swarm model could not load. Reload to try again.</p>';
    return;
  }
  const canvas = host.querySelector("canvas"), g = canvas.getContext("2d");
  const scrub = host.querySelector(".sw-scrub"), select = host.querySelector(".sw-select");
  const play = host.querySelector(".sw-play"), contactButton = host.querySelector(".sw-contact");
  const duration = 16 * 60, dt = .6, radius = data.radius_mm;
  const fmt = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  let seed = 7, interact = true, selected = -1, time = 0, hitPoints = [];
  let engine = NematicaSwarmEngine.create({ profiles: data.profiles, seed, interact, radius, length: data.length_mm, dt });
  scrub.max = String(duration);
  data.profiles.forEach((_, i) => select.add(new Option(`Worm ${String(i + 1).padStart(2, "0")}`, String(i))));
  function trace(pts) {
    g.beginPath(); g.moveTo(...pts[0]);
    for (let j = 1; j < pts.length - 1; j++) {
      const middle = [(pts[j][0] + pts[j + 1][0]) / 2, (pts[j][1] + pts[j + 1][1]) / 2];
      g.quadraticCurveTo(pts[j][0], pts[j][1], ...middle);
    }
    g.lineTo(...pts[pts.length - 1]);
  }
  function draw(seconds) {
    time = seconds;
    const snap = engine.seek(Math.min(Math.floor(seconds / dt), duration / dt));
    const rect = canvas.getBoundingClientRect(), W = rect.width, H = rect.height;
    if (!W || !H) return;
    const dpr = Math.min(2, devicePixelRatio || 1);
    if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) {
      canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    }
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    const outerRadius = radius + data.length_mm + .16;
    const sc = (Math.min(W, H) - 68) / (outerRadius * 2), cx = W / 2, cy = H / 2;
    const X = x => cx + x * sc, Y = y => cy - y * sc;
    g.fillStyle = "#0b171c"; g.fillRect(0, 0, W, H);
    const copper = g.createRadialGradient(cx, cy, radius * sc, cx, cy, outerRadius * sc);
    copper.addColorStop(0, "#674530"); copper.addColorStop(.23, "#332e28"); copper.addColorStop(1, "#1b2728");
    g.fillStyle = copper; g.beginPath(); g.arc(cx, cy, outerRadius * sc, 0, Math.PI * 2); g.fill();
    const field = g.createRadialGradient(cx, cy, radius * sc * .08, cx, cy, radius * sc);
    field.addColorStop(0, "#122b2d"); field.addColorStop(.78, "#10262b"); field.addColorStop(1, "#1e2728");
    g.fillStyle = field; g.beginPath(); g.arc(cx, cy, radius * sc, 0, Math.PI * 2); g.fill();
    g.strokeStyle = "rgba(214,151,83,.14)"; g.lineWidth = .42 * sc;
    g.beginPath(); g.arc(cx, cy, (radius - .21) * sc, 0, Math.PI * 2); g.stroke();
    g.strokeStyle = "#e2a45f"; g.lineWidth = 1.6;
    g.beginPath(); g.arc(cx, cy, radius * sc, 0, Math.PI * 2); g.stroke();
    g.strokeStyle = "#647970"; g.lineWidth = 1;
    g.beginPath(); g.arc(cx, cy, outerRadius * sc, 0, Math.PI * 2); g.stroke();
    g.strokeStyle = "rgba(198,228,218,.14)"; g.lineWidth = 1;
    g.beginPath(); g.moveTo(cx - 7, cy); g.lineTo(cx + 7, cy); g.moveTo(cx, cy - 7); g.lineTo(cx, cy + 7); g.stroke();
    if (selected >= 0) {
      const path = snap.agents[selected].path;
      g.strokeStyle = "rgba(112,232,195,.62)"; g.lineWidth = 1.25; g.setLineDash([3, 4]);
      g.beginPath(); path.forEach((p, i) => i ? g.lineTo(X(p[0]), Y(p[1])) : g.moveTo(X(p[0]), Y(p[1])));
      g.stroke(); g.setLineDash([]);
    }
    hitPoints = [];
    snap.agents.forEach((agent, i) => {
      const pts = engine.body(agent).map(p => [X(p[0]), Y(p[1])]);
      hitPoints.push(pts);
      g.globalAlpha = selected >= 0 && selected !== i ? .35 : 1;
      g.lineCap = "round"; g.lineJoin = "round";
      trace(pts); g.strokeStyle = "#0a1418"; g.lineWidth = Math.max(3.7, .075 * sc); g.stroke();
      trace(pts); g.strokeStyle = agent.reversing ? "#f477ba" : "#d7e9e3";
      g.lineWidth = Math.max(2.5, .052 * sc); g.stroke();
      g.fillStyle = agent.reversing ? "#ffe6f0" : "#f7fff9";
      g.beginPath(); g.arc(pts[0][0], pts[0][1], Math.max(1.8, .028 * sc), 0, Math.PI * 2); g.fill();
      if (agent.touch || selected === i) {
        g.strokeStyle = selected === i ? "#8ef2c7" : "#ffffff";
        g.lineWidth = selected === i ? 1.6 : 1;
        g.beginPath(); g.arc(pts[0][0], pts[0][1], selected === i ? 8.5 : 5.5, 0, Math.PI * 2); g.stroke();
      }
      g.globalAlpha = 1;
    });
    g.fillStyle = "#b7c9c6"; g.fillRect(18, H - 21, sc, 2);
    g.font = "11px system-ui"; g.fillText("1 mm", 18, H - 28);
    host.querySelector(".sw-rev").textContent = snap.events.reversing;
    host.querySelector(".sw-touch").textContent = snap.events.contacts;
    host.querySelector(".sw-time").textContent = `${fmt(time)} / ${fmt(duration)}`;
    scrub.value = String(time); scrub.style.setProperty("--p", `${time / duration * 100}%`);
    const measures = { contact: [snap.summary.contact, true], cluster: [snap.summary.cluster, true],
      rev0: [snap.summary.rev0, false], rev2: [snap.summary.rev2, false], copper: [snap.summary.copper, true] };
    for (const [key, [value, percent]] of Object.entries(measures)) {
      host.querySelector(`[data-k="${key}"]`).textContent = snap.frame === 0 ? "n/a" :
        percent ? `${Math.round(value * 100)}%` : value.toFixed(1);
    }
    if (selected < 0) host.querySelector(".sw-inspect").textContent = "Select a worm or click its body to follow its path.";
    else {
      const a = snap.agents[selected], distance = radius - Math.hypot(a.x, a.y);
      host.querySelector(".sw-inspect").textContent = `Worm ${String(selected + 1).padStart(2, "0")} · ${a.reversing ? "reversing" : "forward"}${a.touch ? " · head contact" : ""} · ${Math.abs(distance).toFixed(2)} mm ${distance >= 0 ? "inside" : "past"} copper`;
    }
    host.querySelector(".sw-seed-value").textContent = String(seed).padStart(2, "0");
  }
  const clock = NematicaPlayback({ duration, render: draw, speed: 4,
    onState: (on, ended) => { play.textContent = on ? "Pause" : ended ? "Replay" : "Play"; play.setAttribute("aria-pressed", String(on)); } });
  function reset(newSeed = seed) {
    clock.play(false);
    seed = newSeed;
    engine = NematicaSwarmEngine.create({ profiles: data.profiles, seed, interact, radius, length: data.length_mm, dt });
    selected = -1; select.value = "-1";
    clock.seek(0);
  }
  play.addEventListener("click", () => clock.play(!clock.playing));
  scrub.addEventListener("input", () => { clock.play(false); clock.seek(+scrub.value); });
  host.querySelector(".sw-restart").addEventListener("click", () => reset());
  host.querySelector(".sw-new-run").addEventListener("click", () => reset(seed + 1));
  contactButton.addEventListener("click", () => {
    interact = !interact;
    contactButton.setAttribute("aria-pressed", String(interact));
    contactButton.setAttribute("aria-label", `Worm interactions ${interact ? "on" : "off"}`);
    contactButton.textContent = interact ? "On" : "Off";
    reset();
  });
  select.addEventListener("change", () => { selected = +select.value; draw(time); });
  canvas.addEventListener("click", e => {
    const rect = canvas.getBoundingClientRect(), x = e.clientX - rect.left, y = e.clientY - rect.top;
    let nearest = -1, distance = 13;
    hitPoints.forEach((pts, i) => pts.forEach(p => {
      const d = Math.hypot(x - p[0], y - p[1]);
      if (d < distance) { distance = d; nearest = i; }
    }));
    selected = nearest; select.value = String(selected); draw(time);
  });
  const speeds = host.querySelectorAll(".sw-speed button");
  speeds.forEach(b => b.addEventListener("click", () => {
    clock.setSpeed(+b.dataset.speed);
    speeds.forEach(other => other.setAttribute("aria-pressed", String(other === b)));
  }));
  let inView = true;
  new IntersectionObserver(([entry]) => { inView = entry.isIntersecting; clock.setVisible(inView && !document.hidden); }).observe(host);
  document.addEventListener("visibilitychange", () => clock.setVisible(inView && !document.hidden));
  new ResizeObserver(() => draw(time)).observe(canvas);
  clock.seek(0);
})();
