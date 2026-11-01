/* Interpolate the exported posture, keeping every segment at its recorded length. */
(function (root) {
  "use strict";
  function bodyAt(data, worm, time) {
    const frame = Math.max(0, Math.min(data.frames - 1, time / data.dt));
    const i = Math.floor(frame), j = Math.min(data.frames - 1, i + 1), mix = frame - i;
    let x = worm.head[2 * i] + mix * (worm.head[2 * j] - worm.head[2 * i]);
    let y = worm.head[2 * i + 1] + mix * (worm.head[2 * j + 1] - worm.head[2 * i + 1]);
    const pts = [[x, y]], step = data.length_mm / data.points;
    for (let p = 0; p < data.points; p++) {
      const a = worm.angles[i * data.points + p], b = worm.angles[j * data.points + p];
      const angle = a + mix * Math.atan2(Math.sin(b - a), Math.cos(b - a));
      x += step * Math.cos(angle); y += step * Math.sin(angle); pts.push([x, y]);
    }
    return pts;
  }
  function extent(data) {
    let bound = data.radius_mm;
    for (const worm of data.worms) for (let i = 0; i < data.frames; i++) {
      bound = Math.max(bound, Math.abs(worm.head[2 * i]) + data.length_mm,
        Math.abs(worm.head[2 * i + 1]) + data.length_mm);
    }
    return bound + 0.15;
  }
  root.NematicaSwarm = { bodyAt, extent };
  if (typeof module !== "undefined") module.exports = root.NematicaSwarm;
})(typeof window !== "undefined" ? window : globalThis);
