/* Shared response grid: every class occupies the same cell in all three brains. */
(function () {
  "use strict";
  const host = document.getElementById("echo");
  if (!host) return;
  const E = window.NEMATICA_ECHO, maps = host.querySelector(".echo-maps");
  if (!E) { maps.innerHTML = '<p class="scope-empty">The local echo data is unavailable.</p>'; return; }
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const T = E.nt, R = E.resp.length, dt = E.dtSample || 1, threshold = 0.35;
  const sets = [
    { key: "real", label: "Real worms", note: `Average of ${E.nWorms} held-out worms`, color: "61,214,155" },
    { key: "hybrid_kernels_regimes_obsfit", label: "Hybrid brain", note: "Learned from activity + pokes", color: "240,98,180" },
    { key: "var3_spontaneous", label: "Linear brain", note: "Learned from activity only", color: "240,98,180" },
  ].map(s => ({ ...s, data: Int8Array.from(atob(E.sets[s.key]), c => c.charCodeAt(0)) }));
  function value(set, stimulus, neuron, frame) {
    const q = set.data[(stimulus * R + neuron) * T + frame];
    return q === -128 ? NaN : q * E.scale / 127;
  }
  function mean(set, stimulus, neuron) {
    let sum = 0, n = 0;
    for (let f = 0; f < T && f * dt <= 15; f++) {
      const v = value(set, stimulus, neuron, f); if (Number.isFinite(v)) { sum += v; n++; }
    }
    return n ? sum / n : NaN;
  }
  function agreement(set, stimuli) {
    const a = [], b = [];
    for (const stimulus of stimuli) for (let r = 0; r < R; r++) {
      const x = mean(sets[0], stimulus, r), y = mean(set, stimulus, r);
      if (Number.isFinite(x) && Number.isFinite(y)) { a.push(x); b.push(y); }
    }
    if (a.length < 8) return NaN;
    const ma = a.reduce((s, x) => s + x, 0) / a.length, mb = b.reduce((s, x) => s + x, 0) / b.length;
    let ab = 0, aa = 0, bb = 0;
    a.forEach((x, i) => { ab += (x - ma) * (b[i] - mb); aa += (x - ma) ** 2; bb += (b[i] - mb) ** 2; });
    return ab / Math.sqrt(aa * bb);
  }
  const format = v => Number.isFinite(v) ? v.toFixed(2).replace("-", "−") : "n/a";
  const pooled = sets.map(s => agreement(s, E.stims.map((_, i) => i)));
  let si = Math.max(0, E.stims.indexOf("ASH")), inspected = E.stims[si], time = 0, rendered = "";
  const select = host.querySelector(".echo-select"), scrub = host.querySelector(".echo-scrub"), play = host.querySelector(".echo-play");
  E.stims.forEach(c => select.add(new Option(c, c)));
  select.value = E.stims[si]; scrub.max = String((T - 1) * dt); scrub.step = String(dt);
  const views = sets.map((set, k) => {
    const card = document.createElement("section"); card.className = "echo-card";
    card.style.setProperty("--response", set.color);
    card.innerHTML = `<header><div class="echo-card-kicker">${k ? "MODEL 0" + k : "REFERENCE"}</div><h3>${set.label}</h3><p>${set.note}</p></header>
      <div class="echo-count"><strong>0</strong><span>responding<br><small></small></span><svg viewBox="0 0 100 32" aria-label="Number of responding classes over time"><path/><circle r="2.5"/></svg></div>
      <div class="echo-grid" role="group" aria-label="${set.label}: neuron responses"></div>
      <footer>${k ? '<span>Agreement with real</span><b class="echo-agreement"></b>' : '<span>Response threshold</span><b>±0.35 SD</b>'}</footer>`;
    const grid = card.querySelector(".echo-grid");
    const cells = E.resp.map(c => {
      const cell = document.createElement("button"); cell.type = "button"; cell.className = "echo-cell";
      cell.innerHTML = `<i></i><span>${c}</span>`;
      cell.addEventListener("pointerenter", () => inspect(c));
      cell.addEventListener("focus", () => inspect(c));
      cell.addEventListener("click", () => { inspect(c); if (E.stims.includes(c)) stimulate(c); });
      grid.appendChild(cell); return cell;
    });
    maps.appendChild(card);
    return { set, card, cells, counts: [] };
  });
  function paired(r, frame) { return sets.every(s => Number.isFinite(value(s, si, r, frame))); }
  function prepare() {
    views.forEach((v, k) => {
      v.counts = Array.from({ length: T }, (_, f) => E.resp.reduce((n, c, r) => n + (paired(r, f) && Math.abs(value(v.set, si, r, f)) > threshold ? 1 : 0), 0));
      v.card.querySelector("svg path").setAttribute("d", v.counts.map((n, f) => `${f ? "L" : "M"}${2 + f / (T - 1) * 96},${29 - n / R * 26}`).join(" "));
      if (k) v.card.querySelector(".echo-agreement").textContent = `${format(agreement(v.set, [si]))} this poke · ${format(pooled[k])} all`;
    });
  }
  function inspect(c) { inspected = c; draw(time); }
  function draw(seconds) {
    time = seconds;
    const f = Math.min(T - 1, Math.floor(time / dt)), stimulus = E.stims[si];
    scrub.value = String(f * dt); scrub.style.setProperty("--p", `${time / ((T - 1) * dt) * 100}%`);
    host.querySelector(".echo-time").textContent = `${Math.floor(time)} / ${Math.round((T - 1) * dt)} s`;
    const signature = `${si}:${f}:${inspected}`;
    if (signature === rendered) return;
    rendered = signature;
    views.forEach(v => {
      let measured = 0;
      v.cells.forEach((cell, r) => {
        const c = E.resp[r], x = value(v.set, si, r, f), available = paired(r, f), isStim = c === stimulus;
        if (available) measured++;
        cell.classList.toggle("stimulated", isStim); cell.classList.toggle("inspected", c === inspected);
        cell.classList.toggle("unmeasured", !available && !isStim);
        cell.classList.toggle("responding", available && Math.abs(x) > threshold);
        cell.style.setProperty("--cell-color", x < 0 ? "143,184,255" : v.set.color);
        cell.style.setProperty("--strength", available ? Math.min(1, Math.abs(x) / 1.5).toFixed(3) : "0");
        const desc = isStim ? "stimulated" : available ? `${format(x)} SD` : "not measured in all three brains";
        cell.title = `${c}: ${desc}${E.stims.includes(c) ? ". Click to stimulate." : ""}`;
        cell.setAttribute("aria-label", cell.title); cell.setAttribute("aria-pressed", String(isStim));
      });
      v.card.querySelector(".echo-count strong").textContent = v.counts[f];
      v.card.querySelector(".echo-count small").textContent = `of ${measured} shared classes`;
      const dot = v.card.querySelector("svg circle");
      dot.setAttribute("cx", 2 + f / (T - 1) * 96); dot.setAttribute("cy", 29 - v.counts[f] / R * 26);
    });
    const r = E.resp.indexOf(inspected);
    host.querySelector(".echo-inspect").textContent = `${inspected} · ` + (inspected === stimulus ? "Stimulated neuron" : views.map(v => `${v.set.label}: ${r >= 0 && paired(r, f) ? format(value(v.set, si, r, f)) + " SD" : "not measured"}`).join("   /   "));
  }
  const clock = NematicaPlayback({ duration: (T - 1) * dt, speed: 1, render: draw,
    onState: (on, ended) => { play.textContent = on ? "Pause" : ended ? "Replay" : "Play"; play.setAttribute("aria-pressed", String(on)); } });
  function stimulate(c) {
    si = E.stims.indexOf(c); select.value = c; inspected = c; prepare(); clock.seek(0);
    if (!reduce) clock.play(true);
  }
  select.addEventListener("change", () => stimulate(select.value));
  play.addEventListener("click", () => clock.play(!clock.playing));
  scrub.addEventListener("input", () => { clock.play(false); clock.seek(+scrub.value); });
  document.addEventListener("visibilitychange", () => clock.setVisible(!document.hidden));
  prepare(); clock.seek(6);
})();
