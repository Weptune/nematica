/* The opening figure: a held-out real worm and an artificial brain, the same 52 neuron classes,
   the same optogenetic pokes, drawn as two channels of one instrument. Data: window.NEMATICA_LOCAL
   (web/data/local.js, local only; see scripts/export_site.py). */
(function () {
  "use strict";
  const host = document.getElementById("scope");
  if (!host) return;
  const D = window.NEMATICA_LOCAL;
  if (!D) {
    host.querySelector(".scope-body").innerHTML =
      '<div class="scope-empty"><div>This figure draws a recorded worm from the local copy of the atlas.<br>' +
      "Run <code>python scripts/export_site.py --local</code> and reload.</div></div>";
    return;
  }
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const decode = (b64) => { const s = atob(b64), a = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) a[i] = s.charCodeAt(i); return a; };
  const nC = D.classes.length, nT = D.frames;
  const real = decode(D.real);
  const brains = {}; for (const k in D.brains) brains[k] = decode(D.brains[k].data);
  let current = Object.keys(D.brains)[0];

  const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const FIELD = hex("#060d10");
  function ramp(glow) {
    const g = hex(glow), white = [244, 255, 250];
    const lut = new Uint8ClampedArray(256 * 3);
    for (let q = 0; q < 256; q++) {
      let c;
      if (q === 0) c = [20, 28, 32];
      else {
        const t = Math.max(0, Math.min(1, (q / 255 - 0.3) / 0.62));
        if (t < 0.7) { const k = Math.pow(t / 0.7, 1.35); c = FIELD.map((f, i) => f + (g[i] - f) * k); }
        else { const k = (t - 0.7) / 0.3; c = g.map((v, i) => v + (white[i] - v) * k * 0.85); }
      }
      lut[q * 3] = c[0]; lut[q * 3 + 1] = c[1]; lut[q * 3 + 2] = c[2];
    }
    return lut;
  }
  const LUT = { live: ramp("#3dd69b"), copy: ramp("#f062b4") };

  function bitmap(data, lut) {
    const c = document.createElement("canvas"); c.width = nT; c.height = nC;
    const ctx = c.getContext("2d"), img = ctx.createImageData(nT, nC);
    for (let r = 0; r < nC; r++) for (let t = 0; t < nT; t++) {
      const q = data[r * nT + t], o = (r * nT + t) * 4;
      img.data[o] = lut[q * 3]; img.data[o + 1] = lut[q * 3 + 1]; img.data[o + 2] = lut[q * 3 + 2]; img.data[o + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    return c;
  }

  const cvLive = host.querySelector("canvas.live"), cvCopy = host.querySelector("canvas.copy");
  let bmLive = bitmap(real, LUT.live), bmCopy = bitmap(brains[current], LUT.copy);
  let progress = reduce ? 1 : 0;

  function size(cv) {
    const r = cv.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1);
    cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr);
    return cv;
  }
  function draw(cv, bm, glow) {
    const ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
    ctx.fillStyle = "#060d10"; ctx.fillRect(0, 0, W, H);
    // horizontal: smooth (averages frames); vertical: crisp rows
    const mid = document.createElement("canvas"); mid.width = W; mid.height = nC;
    const m = mid.getContext("2d"); m.imageSmoothingEnabled = true; m.imageSmoothingQuality = "high";
    m.drawImage(bm, 0, 0, W, nC);
    ctx.imageSmoothingEnabled = false;
    const shown = Math.round(W * progress);
    if (shown > 0) ctx.drawImage(mid, 0, 0, shown, nC, 0, 0, shown, H);
    // row separators, faint
    ctx.fillStyle = "rgba(6,13,16,0.55)";
    const rh = H / nC;
    if (rh > 3.2) for (let r = 1; r < nC; r++) ctx.fillRect(0, Math.round(r * rh), W, 1);
    // pokes
    D.stims.forEach((s) => {
      const x = Math.round((s.frame / nT) * W);
      if (x > shown) return;
      ctx.fillStyle = "rgba(255,255,255,0.22)"; ctx.fillRect(x, 0, Math.max(1, Math.round(devicePixelRatio || 1)), H);
    });
    if (progress < 1) {
      ctx.fillStyle = glow; ctx.fillRect(shown - 1, 0, 2, H);
    }
  }
  function render() {
    draw(cvLive, bmLive, "#3dd69b");
    draw(cvCopy, bmCopy, "#f062b4");
  }
  function layout() { size(cvLive); size(cvCopy); render(); }

  // poke markers and time axis
  const axis = host.querySelector(".scope-axis .ticks");
  const dur = nT * D.dt;
  const every = host.getBoundingClientRect().width < 560 ? 120 : 60;
  for (let s = 0; s <= dur; s += every) {
    const sp = document.createElement("span");
    sp.style.left = (s / dur) * 100 + "%";
    sp.textContent = s === 0 ? "0" : s / 60 + " min";
    if (s === 0) sp.style.transform = "none";
    if (s + every > dur) sp.style.transform = "translateX(-100%)";
    axis.appendChild(sp);
  }
  host.querySelector(".worm").textContent = `Worm ${D.worm.slice(0, 8)}, held out from training`;

  // readout on hover
  const read = host.querySelector(".scope-read");
  function onMove(e, which) {
    const cv = which === "live" ? cvLive : cvCopy;
    const r = cv.getBoundingClientRect();
    const t = Math.max(0, Math.min(nT - 1, Math.floor(((e.clientX - r.left) / r.width) * nT)));
    const row = Math.max(0, Math.min(nC - 1, Math.floor(((e.clientY - r.top) / r.height) * nC)));
    const z = (a) => { const q = a[row * nT + t]; return q === 0 ? "n/a" : (-1.5 + ((q - 1) / 254) * 4.5).toFixed(1).replace("-", "−"); };
    const last = D.stims.filter((s) => s.frame <= t).pop();
    const since = last ? (t - last.frame) * D.dt : null;
    read.innerHTML = `<b>${D.classes[row]}</b> at ${(t * D.dt).toFixed(0)} s<br>` +
      `<span class="l">Real worm</span> ${z(real)} SD<br><span class="c">${D.brains[current].label}</span> ${z(brains[current])} SD` +
      (last && since <= 30 ? `<br>${since.toFixed(0)} s after a poke to ${last.cls}` : "");
    const hr = host.getBoundingClientRect();
    let x = e.clientX - hr.left + 14, y = e.clientY - hr.top + 14;
    read.style.display = "block";
    if (x + read.offsetWidth > hr.width - 6) x = e.clientX - hr.left - read.offsetWidth - 14;
    read.style.left = x + "px"; read.style.top = y + "px";
  }
  [["live", cvLive], ["copy", cvCopy]].forEach(([w, cv]) => {
    cv.addEventListener("pointermove", (e) => onMove(e, w));
    cv.addEventListener("pointerleave", () => (read.style.display = "none"));
  });

  // brain switch
  host.querySelectorAll(".seg button").forEach((b) => {
    b.addEventListener("click", () => {
      current = b.dataset.brain;
      host.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      bmCopy = bitmap(brains[current], LUT.copy);
      host.querySelector(".channel.copy .tag").textContent = D.brains[current].label;
      render();
    });
  });
  host.querySelector(".channel.copy .tag").textContent = D.brains[current].label;

  addEventListener("resize", layout);
  layout();
  if (!reduce) {
    const t0 = performance.now(), T = 2600;
    const step = (now) => {
      progress = Math.min(1, (now - t0) / T);
      progress = 1 - Math.pow(1 - progress, 2.2);
      render();
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
})();
