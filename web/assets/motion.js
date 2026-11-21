/* NEMATICA: one switch for everything that moves.

   Motion follows the visitor's system setting ("reduce motion", which on Windows is Settings, Accessibility,
   Visual effects, Animation effects) until they choose with a button on the page; the choice is then kept on
   this device. Loaded in the head, before the first paint, so the page never starts in the wrong state.

   - Scripts read NEMATICA_MOTION.on and listen with NEMATICA_MOTION.sub(fn).
   - Styles follow html.still (motion off) and html.moving (motion on).
   - Any button with a data-motion attribute becomes the switch. One marked data-motion="icon" has no words
     of its own, so its name is kept in step: it says what pressing it does. */
(() => {
  "use strict";
  const KEY = "nematica-motion", root = document.documentElement, subs = [], sys = matchMedia("(prefers-reduced-motion: reduce)");
  let saved = null; try { saved = localStorage.getItem(KEY); } catch (e) { /* private mode: follow the system */ }
  const chosen = saved === "on" || saved === "off";
  const M = window.NEMATICA_MOTION = { on: chosen ? saved === "on" : !sys.matches, chosen,
    sub(fn) { subs.push(fn); },
    set(on) { M.on = !!on; M.chosen = true; try { localStorage.setItem(KEY, M.on ? "on" : "off"); } catch (e) { /* not kept, still applied */ } apply(); } };
  function label() { document.querySelectorAll("[data-motion]").forEach((b) => { const s = M.on ? "Pause motion" : "Play motion";
    if (b.dataset.motion === "icon") { b.setAttribute("aria-label", s); b.title = s; } }); }
  function apply() { root.classList.toggle("still", !M.on); root.classList.toggle("moving", M.on); label(); subs.forEach((f) => { try { f(M.on); } catch (e) { /* one listener must not stop the rest */ } }); }
  root.classList.toggle("still", !M.on); root.classList.toggle("moving", M.on);
  const follow = () => { if (!M.chosen) { M.on = !sys.matches; apply(); } };                       // the system setting changed while the page was open
  if (sys.addEventListener) sys.addEventListener("change", follow); else if (sys.addListener) sys.addListener(follow);
  const wire = () => { label(); document.querySelectorAll("[data-motion]").forEach((b) => b.addEventListener("click", () => M.set(!M.on))); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire); else wire();
})();
