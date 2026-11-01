(function () {
  "use strict";
  // the top bar sits on the dark field until the hero has scrolled away
  // the top bar turns dark whenever it sits over a dark section
  const bar = document.getElementById("bar");
  const dark = [...document.querySelectorAll(".arrival, .experiment, .hero, .interlude, .masthead, footer.foot")];
  if (bar && dark.length) {
    let raf = 0;
    const check = () => { raf = 0; const y = 30; bar.classList.toggle("on-field", dark.some((d) => { const r = d.getBoundingClientRect(); return r.top <= y && r.bottom >= y; })); };
    addEventListener("scroll", () => { if (!raf) raf = requestAnimationFrame(check); }, { passive: true });
    check();
  }
  const arrival = document.querySelector('.arrival');
  const arrivalFrame = document.getElementById('arrival-lab');
  if (arrival && arrivalFrame) {
    const clock = arrival.querySelector('.arrival-clock');
    const motionButton = arrival.querySelector('.arrival-motion-toggle');
    let moving = true;
    motionButton?.addEventListener('click', () => {
      moving = !moving;
      arrivalFrame.contentWindow?.postMessage({ type: 'nematica-lab-play', playing: moving }, location.origin);
      motionButton.textContent = moving ? 'Pause replay' : 'Play replay';
      motionButton.setAttribute('aria-label', moving ? 'Pause worm replay' : 'Play worm replay');
    });
    arrivalFrame.addEventListener('load', () => {
      if (!moving) arrivalFrame.contentWindow?.postMessage({ type: 'nematica-lab-play', playing: false }, location.origin);
    });
    addEventListener('message', (event) => {
      if (event.origin !== location.origin || event.source !== arrivalFrame.contentWindow || event.data?.type !== 'nematica-lab-time') return;
      const seconds = Math.max(0, Math.floor(Number(event.data.seconds) || 0));
      clock.textContent = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
    });
  }
  const menuButton = bar?.querySelector(".menu-toggle");
  const siteNav = bar?.querySelector("#site-nav");
  if (menuButton && siteNav) {
    const setMenu = (open) => {
      bar.classList.toggle("menu-open", open);
      menuButton.setAttribute("aria-expanded", String(open));
      menuButton.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      menuButton.lastElementChild.textContent = open ? "Close" : "Menu";
    };
    menuButton.addEventListener("click", () => setMenu(!bar.classList.contains("menu-open")));
    siteNav.addEventListener("click", (event) => { if (event.target.closest("a")) setMenu(false); });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && bar.classList.contains("menu-open")) {
        setMenu(false);
        menuButton.focus();
      }
    });
    document.addEventListener("click", (event) => {
      if (bar.classList.contains("menu-open") && !bar.contains(event.target)) setMenu(false);
    });
    matchMedia("(min-width: 721px)").addEventListener("change", (event) => { if (event.matches) setMenu(false); });
  }
  // verdict legends
  document.querySelectorAll("[data-legend]").forEach((n) => window.NematicaCharts && window.NematicaCharts.verdictLegend(n));
  // contents rail: highlight the section being read
  const links = [...document.querySelectorAll(".toc a")];
  if (links.length) {
    const map = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));
    const secs = [...map.keys()].map((id) => document.getElementById(id)).filter(Boolean);
    const io = new IntersectionObserver((es) => {
      es.forEach((e) => { if (e.isIntersecting) { links.forEach((a) => a.classList.remove("active")); map.get(e.target.id).classList.add("active"); } });
    }, { rootMargin: "-20% 0px -70% 0px" });
    secs.forEach((s) => io.observe(s));
  }
})();
// the closing wordmark is filled with the recorded worm's own activity, when the local data is present
(function () {
  const D = window.NEMATICA_LOCAL, big = document.querySelector("footer.foot .big");
  if (!D || !big) return;
  const s = atob(D.real), nC = D.classes.length, nT = D.frames;
  const c = document.createElement("canvas"); c.width = nT; c.height = nC;
  const ctx = c.getContext("2d"), img = ctx.createImageData(nT, nC);
  const g = [120, 255, 192], base = [88, 108, 114];
  for (let i = 0; i < nC * nT; i++) {
    const q = s.charCodeAt(i), t = q ? Math.max(0, Math.min(1, (q / 255 - 0.3) / 0.6)) : 0;
    const k = Math.pow(t, 1.2);
    img.data[i * 4] = base[0] + (g[0] - base[0]) * k; img.data[i * 4 + 1] = base[1] + (g[1] - base[1]) * k;
    img.data[i * 4 + 2] = base[2] + (g[2] - base[2]) * k; img.data[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  big.style.backgroundImage = `url(${c.toDataURL()})`;
  big.classList.add("filled");
  big.title = "Filled with eight minutes of a real worm's brain activity";
})();
// inner-page mastheads carry a strip of the recorded worm's activity along their lower edge
(function () {
  const D = window.NEMATICA_LOCAL, m = document.querySelector(".masthead");
  if (!D || !m) return;
  const s = atob(D.real), nC = D.classes.length, nT = D.frames;
  const c = document.createElement("canvas"); c.width = nT; c.height = nC; c.className = "mast-strip";
  c.setAttribute("aria-hidden", "true");
  const ctx = c.getContext("2d"), img = ctx.createImageData(nT, nC);
  const field = [13, 22, 27], g = [61, 214, 155];
  for (let i = 0; i < nC * nT; i++) {
    const q = s.charCodeAt(i), t = q ? Math.max(0, Math.min(1, (q / 255 - 0.32) / 0.6)) : 0, k = Math.pow(t, 1.5);
    img.data[i * 4] = field[0] + (g[0] - field[0]) * k; img.data[i * 4 + 1] = field[1] + (g[1] - field[1]) * k;
    img.data[i * 4 + 2] = field[2] + (g[2] - field[2]) * k; img.data[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  m.appendChild(c);
})();
