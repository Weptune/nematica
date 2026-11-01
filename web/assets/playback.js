/* One animation clock per view. Seeking and pausing cancel pending frames. */
(function (root) {
  "use strict";
  function createPlayback({ duration, render, onState = () => {}, speed = 1,
    request = requestAnimationFrame, cancel = cancelAnimationFrame }) {
    let time = 0, playing = false, visible = true, frame = null, last = null;
    function stopFrame() { if (frame !== null) cancel(frame); frame = null; last = null; }
    function schedule() { if (playing && visible && frame === null) frame = request(tick); }
    function tick(now) {
      frame = null;
      if (!playing || !visible) return;
      if (last !== null) time = Math.min(duration, time + Math.min(0.25, Math.max(0, (now - last) / 1000)) * speed);
      last = now;
      render(time);
      if (time >= duration) { playing = false; last = null; onState(false, true); }
      else schedule();
    }
    return {
      get time() { return time; }, get playing() { return playing; },
      play(on = true) {
        if (on && time >= duration) { time = 0; render(time); }
        playing = on; stopFrame(); onState(on, time >= duration); schedule();
      },
      seek(value) { time = Math.max(0, Math.min(duration, Number(value) || 0)); stopFrame(); render(time); schedule(); },
      setSpeed(value) { if (Number.isFinite(value) && value > 0) { speed = value; last = null; } },
      setDuration(value) { duration = Math.max(0, value); this.seek(time); },
      setVisible(value) { visible = value; stopFrame(); schedule(); },
    };
  }
  root.NematicaPlayback = createPlayback;
  if (typeof module !== "undefined") module.exports = createPlayback;
})(typeof window !== "undefined" ? window : globalThis);
