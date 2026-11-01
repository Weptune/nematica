/* Inspectable replay of the exported swarm, without changing its trajectories. */
(async function () {
  "use strict";
  const host = document.getElementById("swarm");
  if (!host) return;
  try {
    await new Promise((resolve, reject) => {
      const script = document.createElement("script"); script.src = "data/sim/swarm.js";
      script.onload = resolve; script.onerror = reject; document.head.appendChild(script);
    });
  } catch (_) { host.querySelector(".swarm-stage").innerHTML = '<p class="scope-empty">The swarm recording could not load. Reload to try again.</p>'; return; }
  const D = window.NEMATICA_SIM.swarm, canvas = host.querySelector("canvas"), g = canvas.getContext("2d");
  const scrub = host.querySelector(".sw-scrub"), select = host.querySelector(".sw-select"), play = host.querySelector(".sw-play");
  const duration = (D.frames - 1) * D.dt, bound = NematicaSwarm.extent(D);
  const fmt = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  let selected = -1, time = 0, hitPoints = [];
  scrub.max = String(duration);
  D.worms.forEach((w, i) => select.add(new Option(`Worm ${String(i + 1).padStart(2, "0")}`, String(i))));
  function draw(seconds) {
    time = seconds;
    const rect = canvas.getBoundingClientRect(), W = rect.width, H = rect.height, dpr = Math.min(2, devicePixelRatio || 1);
    if (!W || !H) return;
    if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) { canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr); }
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    const sc = (Math.min(W, H) - 48) / (bound * 2), cx = W / 2, cy = H / 2;
    const X = x => cx + x * sc, Y = y => cy - y * sc;
    const frame = Math.min(D.frames - 1, Math.floor(time / D.dt));
    g.fillStyle = "#0b171c"; g.fillRect(0, 0, W, H);
    // Copper extends beyond the cue boundary; it is not a physical container.
    g.fillStyle = "rgba(201,133,70,.055)";
    g.beginPath(); g.rect(0, 0, W, H); g.arc(cx, cy, D.radius_mm * sc, 0, Math.PI * 2, true); g.fill("evenodd");
    const gradient = g.createRadialGradient(cx, cy, 0, cx, cy, D.radius_mm * sc);
    gradient.addColorStop(0, "#12292d"); gradient.addColorStop(1, "#102126");
    g.fillStyle = gradient; g.beginPath(); g.arc(cx, cy, D.radius_mm * sc, 0, Math.PI * 2); g.fill();
    g.fillStyle = "rgba(160,195,200,.13)";
    for (let x = -Math.floor(bound); x <= bound; x++) for (let y = -Math.floor(bound); y <= bound; y++) {
      g.beginPath(); g.arc(X(x), Y(y), .65, 0, Math.PI * 2); g.fill();
    }
    g.strokeStyle = "#b27d4b"; g.lineWidth = 1.2;
    g.beginPath(); g.arc(cx, cy, D.radius_mm * sc, 0, Math.PI * 2); g.stroke();
    // A selected worm's recent path gives motion a readable direction.
    if (selected >= 0) {
      const worm = D.worms[selected], start = Math.max(0, frame - Math.ceil(20 / D.dt));
      g.strokeStyle = "rgba(109,225,202,.45)"; g.lineWidth = 1; g.setLineDash([3, 3]); g.beginPath();
      for (let f = start; f <= frame; f++) {
        const x = X(worm.head[2 * f]), y = Y(worm.head[2 * f + 1]);
        f === start ? g.moveTo(x, y) : g.lineTo(x, y);
      }
      g.stroke(); g.setLineDash([]);
    }
    let reversing = 0, touching = 0;
    hitPoints = [];
    D.worms.forEach((worm, i) => {
      const pts = NematicaSwarm.bodyAt(D, worm, time), rev = worm.reversing[frame], touch = worm.touch[frame];
      reversing += !!rev; touching += !!touch;
      const pixel = pts.map(p => [X(p[0]), Y(p[1])]); hitPoints.push(pixel);
      g.globalAlpha = selected >= 0 && selected !== i ? .34 : 1;
      // A tapered silhouette instead of a constant-width zigzag.
      const left = [], right = [];
      pixel.forEach((p, j) => {
        const before = pixel[Math.max(0, j - 1)], after = pixel[Math.min(pixel.length - 1, j + 1)];
        const dx = after[0] - before[0], dy = after[1] - before[1], len = Math.hypot(dx, dy) || 1;
        const radius = Math.max(.45, Math.sin(Math.PI * (j + .5) / pixel.length) * Math.max(1.35, .025 * sc));
        left.push([p[0] - dy / len * radius, p[1] + dx / len * radius]);
        right.push([p[0] + dy / len * radius, p[1] - dx / len * radius]);
      });
      g.fillStyle = rev ? "#ee74b9" : "#cbded9";
      g.beginPath(); g.moveTo(...left[0]); left.slice(1).forEach(p => g.lineTo(...p)); right.reverse().forEach(p => g.lineTo(...p)); g.closePath(); g.fill();
      g.fillStyle = rev ? "#ffe0f0" : "#f1fffa"; g.beginPath(); g.arc(...pixel[0], 1.65, 0, Math.PI * 2); g.fill();
      if (touch || selected === i) {
        g.strokeStyle = selected === i ? "#6de1ca" : "#fff"; g.lineWidth = 1;
        g.beginPath(); g.arc(...pixel[0], selected === i ? 8 : 5.5, 0, Math.PI * 2); g.stroke();
      }
      g.globalAlpha = 1;
      if (selected === i) {
        const distance = D.radius_mm - Math.hypot(...pts[0]);
        host.querySelector(".sw-inspect").textContent = `Worm ${i + 1} · ${rev ? "Reversing" : "Forward"}${touch ? " · Head contact" : ""} · ${Math.abs(distance).toFixed(2)} mm ${distance >= 0 ? "inside" : "beyond"} copper`;
      }
    });
    g.fillStyle = "#a4b9bf"; g.fillRect(18, H - 20, sc, 2); g.font = "11px system-ui"; g.fillText("1 mm", 18, H - 28);
    host.querySelector(".sw-rev").textContent = reversing;
    host.querySelector(".sw-touch").textContent = touching;
    host.querySelector(".sw-time").textContent = `${fmt(time)} / ${fmt(duration)}`;
    scrub.value = String(time); scrub.style.setProperty("--p", `${time / duration * 100}%`);
    if (selected < 0) host.querySelector(".sw-inspect").textContent = "Select a worm or click its body to see its recent path.";
  }
  const clock = NematicaPlayback({ duration, render: draw, speed: 4,
    onState: (on, ended) => { play.textContent = on ? "Pause" : ended ? "Replay" : "Play"; play.setAttribute("aria-pressed", String(on)); } });
  play.addEventListener("click", () => clock.play(!clock.playing));
  scrub.addEventListener("input", () => { clock.play(false); clock.seek(+scrub.value); });
  host.querySelector(".sw-restart").addEventListener("click", () => { clock.play(false); clock.seek(0); });
  select.addEventListener("change", () => { selected = +select.value; draw(time); });
  canvas.addEventListener("click", e => {
    const rect = canvas.getBoundingClientRect(), x = e.clientX - rect.left, y = e.clientY - rect.top;
    let nearest = -1, distance = 16;
    hitPoints.forEach((pts, i) => pts.forEach(p => { const d = Math.hypot(x - p[0], y - p[1]); if (d < distance) { distance = d; nearest = i; } }));
    selected = nearest; select.value = String(selected); draw(time);
  });
  const speeds = host.querySelectorAll(".sw-speed button");
  speeds.forEach(b => b.addEventListener("click", () => { clock.setSpeed(+b.dataset.speed); speeds.forEach(other => other.setAttribute("aria-pressed", String(other === b))); }));
  let inView = true;
  new IntersectionObserver(([entry]) => { inView = entry.isIntersecting; clock.setVisible(inView && !document.hidden); }).observe(host);
  document.addEventListener("visibilitychange", () => clock.setVisible(inView && !document.hidden));
  new ResizeObserver(() => draw(time)).observe(canvas);
  const summary = D.notes && D.notes.summary;
  if (summary) {
    const fields = { contact: ["contact", true], cluster: ["frac_in_cluster", true], rev0: ["rev_per_min_density_0"], rev2: ["rev_per_min_density_2+"], copper: ["near_copper", true] };
    for (const [key, [source, percent]] of Object.entries(fields)) {
      const v = summary[source]; host.querySelector(`[data-k="${key}"]`).textContent = Number.isFinite(v) ? percent ? `${Math.round(v * 100)}%` : v.toFixed(1) : "n/a";
    }
  }
  clock.seek(0);
})();
