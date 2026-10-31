(function () {
  "use strict";
  // the top bar sits on the dark field until the hero has scrolled away
  const bar = document.getElementById("bar"), hero = document.querySelector(".hero");
  if (bar && hero) {
    const io = new IntersectionObserver(([e]) => bar.classList.toggle("on-field", e.isIntersecting), { rootMargin: "-60px 0px 0px 0px" });
    io.observe(hero);
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
