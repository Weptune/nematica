/* NEMATICA, the orbs: every lit sphere on the page is rendered, not drawn. One fragment shader paints a body
   from nothing but arithmetic: a surface made of layered noise (craters, cloud bands, dust, granules), lit
   from one side with a soft terminator, wrapped in air that glows at the limb. Saturn's rings cast a shadow
   on the globe and the globe casts one on the rings; the Sun has a corona; the Moon keeps its seas.

   Nothing here is a photograph or a texture file. The scene (sky.js) asks for a body at a place, size, turn
   and light each frame; the cards and figures ask once for a small picture. If WebGL is not available,
   window.NEMATICA_ORBS is null and everything falls back to its drawn form. */
(function () {
  "use strict";
  const cv = document.createElement("canvas"); cv.width = cv.height = 1024;
  let gl = null;
  try { gl = cv.getContext("webgl", { alpha: true, premultipliedAlpha: true, antialias: false, depth: false, stencil: false, preserveDrawingBuffer: true }); } catch (e) { gl = null; }
  if (!gl || gl.getShaderPrecisionFormat(gl.FRAGMENT_SHADER, gl.HIGH_FLOAT).precision < 16) { window.NEMATICA_ORBS = null; return; }

  const VS = "attribute vec2 a; varying vec2 v; void main() { v = a; gl_Position = vec4(a, 0., 1.); }";
  const FS = `
precision highp float;
varying vec2 v;
uniform float uKind, uR, uPx, uTime, uSeed, uAmb, uAirH, uFlat, uRoll, uRing, uGain;
uniform mat3 uRot;
uniform vec3 uL, uAxis, uTint;
uniform vec4 uAir;

float hash(vec3 p) { p = fract(p * vec3(.1031, .1030, .0973)); p += dot(p, p.yxz + 33.33); return fract((p.x + p.y) * p.z); }
vec3 hash3(vec3 p) { p = fract(p * vec3(.1031, .1030, .0973)); p += dot(p, p.yxz + 33.33); return fract((p.xxy + p.yxx) * p.zyx); }
float noise(vec3 x) { vec3 i = floor(x), f = fract(x); f = f * f * (3. - 2. * f);
  return mix(mix(mix(hash(i), hash(i + vec3(1, 0, 0)), f.x), mix(hash(i + vec3(0, 1, 0)), hash(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(hash(i + vec3(0, 0, 1)), hash(i + vec3(1, 0, 1)), f.x), mix(hash(i + vec3(0, 1, 1)), hash(i + vec3(1, 1, 1)), f.x), f.y), f.z); }
float fbm(vec3 p) { float a = .5, s = 0.; for (int i = 0; i < 5; i++) { s += a * noise(p); p = p * 2.03 + 11.7; a *= .5; } return s; }
float fbm3(vec3 p) { float a = .5, s = 0.; for (int i = 0; i < 3; i++) { s += a * noise(p); p = p * 2.03 + 11.7; a *= .5; } return s; }
// the nearest of a scatter of points: how far it is, and a number that belongs to it
vec2 cells(vec3 p) { vec3 i = floor(p), f = fract(p); float d = 9., id = 0.;
  for (int x = -1; x <= 1; x++) for (int y = -1; y <= 1; y++) for (int z = -1; z <= 1; z++) { vec3 g = vec3(float(x), float(y), float(z)), o = hash3(i + g), r = g + o - f; float dd = dot(r, r); if (dd < d) { d = dd; id = hash(i + g + 7.31); } }
  return vec2(sqrt(d), id); }
// a field of craters at one size: darker floors, bright rims; only some cells hold one
float craters(vec3 s, float scale, float depth) { vec2 c = cells(s * scale); float rc = .16 + .3 * c.y, t = c.x / rc, on = step(.35, c.y);
  return on * (depth * (smoothstep(.72, 1., t) - smoothstep(1., 1.28, t)) - depth * 1.5 * (1. - smoothstep(.0, .85, t))); }
vec3 turnY(vec3 s, float a) { float c = cos(a), d = sin(a); return vec3(s.x * c - s.z * d, s.y, s.x * d + s.z * c); }

vec3 mercury(vec3 s) {
  float n = fbm(s * 2.1 + uSeed), m = fbm(s * 7.3 + 3.1);
  vec3 col = mix(vec3(.27, .30, .37), vec3(.70, .75, .84), smoothstep(.28, .78, n * .62 + m * .46));
  col += craters(s, 3.8, .11) + craters(s + 3.7, 9., .09) + craters(s + 8.1, 21., .06);
  float ray = cells(s * 2.2 + 1.9).y; col += .22 * step(.9, ray) * (1. - smoothstep(0., .45, cells(s * 2.2 + 1.9).x));
  return col;
}
vec3 moon(vec3 s) {
  float seas = smoothstep(.47, .6, fbm(s * 1.25 + 4.2 + uSeed)), fine = fbm(s * 10.);
  vec3 col = mix(vec3(.80, .82, .87), vec3(.36, .39, .47), seas * .9) * (.8 + .4 * fine);
  col += (craters(s, 3.6, .15) + craters(s + 2.3, 8., .12) + craters(s + 6.9, 19., .08)) * (1. - .5 * seas);
  vec2 r = cells(s * 1.9 + 5.5); col += .3 * step(.88, r.y) * (1. - smoothstep(0., .5, r.x)) * (.6 + .8 * noise(s * 30.));
  return col;
}
vec3 mars(vec3 s) {
  vec3 w = s + .32 * vec3(fbm3(s * 2. + 1.), fbm3(s * 2. + 7.), fbm3(s * 2. + 13.));
  float n = fbm(w * 2.4 + uSeed), d = fbm(w * 7. + 2.);
  vec3 col = mix(vec3(.72, .30, .16), vec3(.98, .60, .36), smoothstep(.3, .75, n));
  col = mix(col, vec3(.30, .13, .10), smoothstep(.5, .7, fbm(w * 1.45 + 9.)) * .82);
  col *= .84 + .34 * d; col += craters(s + 1.1, 13., .035);
  float cap = smoothstep(.87, .93, abs(s.y) + .07 * (d - .5)); return mix(col, vec3(.98, .95, .93), cap);
}
vec3 venus(vec3 s) {
  float a = 2.3 * (1. - abs(s.y)) + uTime * .02; vec3 q = turnY(s, a); q.y *= 2.7;
  float n = fbm(q * 1.5 + uSeed), m = fbm(q * 4.2 + n * 1.6);
  return mix(vec3(.80, .50, .26), vec3(1., .91, .72), smoothstep(.28, .76, n * .6 + m * .5));
}
float belt(float l, float c, float w) { float d = (l - c) / w; return exp(-d * d); }
vec3 jupiter(vec3 s) {
  vec3 q = turnY(s, sin(s.y * 9.5) * .5 * uTime * .05);
  float swirl = fbm(q * vec3(5., 3.2, 5.) + uSeed) - .5, streak = fbm(q * vec3(2.6, 34., 2.6) + 3.) - .5, fine = fbm(q * vec3(11., 22., 11.) + 8.) - .5;
  float l = s.y + .075 * swirl + .012 * fine;
  // the two great belts either side of the equator, lesser ones toward the poles, and a faint band on the equator itself
  float dark = belt(l, .21, .095) + .95 * belt(l, -.27, .105) + .62 * belt(l, .5, .06) + .58 * belt(l, -.56, .065) + .46 * belt(l, .7, .045) + .44 * belt(l, -.75, .05);
  float thin = .22 * belt(l, 0., .028) + .3 * (noise(vec3(1.7, l * 26., uSeed)) - .5);
  vec3 zone = vec3(.96, .92, .83), tan = vec3(.80, .58, .40), brown = vec3(.52, .31, .22);
  vec3 col = mix(zone, tan, clamp(dark * .9 + thin, 0., 1.)); col = mix(col, brown, smoothstep(.62, 1.05, dark + .35 * streak) * .8);
  col = mix(col, vec3(.62, .70, .80), smoothstep(.0, .5, -swirl - .16) * belt(l, .1, .06) * .7);       // blue-grey festoons off the northern belt
  col = mix(col, vec3(.70, .74, .80), smoothstep(.74, 1., abs(s.y)) * .6);
  col *= .92 + .3 * streak + .22 * fine;
  vec3 d = q - normalize(vec3(-.28, -.39, .88)); float e = length(d * vec3(1., 1.9, 1.)) / .21, spot = 1. - smoothstep(.55, 1., e);
  return mix(col, mix(vec3(.74, .28, .18), vec3(.95, .56, .38), fbm(vec3(d.xy * 13., e * 3.))), spot * .92);
}
vec3 saturn(vec3 s) {
  float turb = fbm(s * vec3(2.5, 8., 2.5) + uSeed) - .5, l = s.y + .03 * turb, b = sin(l * 16.) * .5 + .5, b2 = sin(l * 6. + .7) * .5 + .5;
  vec3 col = mix(vec3(.95, .87, .68), vec3(.80, .66, .45), smoothstep(.3, .8, b) * .72); col = mix(col, vec3(.70, .61, .48), b2 * .28);
  col = mix(col, vec3(.58, .64, .72), smoothstep(.68, 1., abs(s.y)) * .65);
  return col * (.95 + .14 * turb);
}
vec3 sun(vec3 s, float mu) {
  float g = fbm(s * 10. + vec3(0., uTime * .1, 0.)), big = fbm(s * 2.6 - uTime * .025), spots = smoothstep(.7, .77, fbm(s * 3.4 + 5. + uSeed)) * smoothstep(.8, .3, abs(s.y));
  vec3 hot = vec3(1., .99, .88), mid = vec3(1., .80, .36), cool = vec3(.96, .44, .10);
  vec3 col = mix(mid, hot, smoothstep(.32, .74, .55 * g + .45 * big)); col = mix(col, cool * .5, spots * .88);
  float limb = pow(mu, .5); return mix(cool, col, limb) * (.6 + .46 * limb);
}
// the rings, by distance from the centre in planet radii: the faint inner ring, the bright one, the gap, the outer one
vec4 rings(float r) {
  float fine = noise(vec3(r * 62., 1.3, 4.)) * .55 + noise(vec3(r * 200., 7., 2.)) * .45, a = 0.;
  a += .17 * smoothstep(1.22, 1.3, r) * (1. - smoothstep(1.5, 1.53, r));
  a += .9 * smoothstep(1.52, 1.56, r) * (1. - smoothstep(1.93, 1.955, r));
  a += .62 * smoothstep(2.02, 2.04, r) * (1. - smoothstep(2.25, 2.28, r)) * (1. - .85 * (smoothstep(2.19, 2.2, r) - smoothstep(2.215, 2.225, r)));
  return vec4(mix(vec3(.74, .65, .52), vec3(.98, .92, .80), fine), clamp(a * (.62 + .55 * fine), 0., 1.));
}
// not a body: the far cloud behind everything, a band of blue and violet gas crossed by dark lanes, with a little gold where it is thickest
vec4 nebula(vec2 u) {
  vec3 p = vec3(u * 1.5, uSeed), w = p + .95 * vec3(fbm3(p * 1.2 + 2.), fbm3(p * 1.2 + 9.), 0.);
  float n = fbm(w * 1.05), m = fbm(w * 2.7 + 5.), band = exp(-pow((u.y + u.x * .42 - .08 + .3 * (n - .5)) / .5, 2.));
  float dens = smoothstep(.36, .82, n * .72 + m * .34) * (.22 + .9 * band) * (1. - .62 * smoothstep(.52, .74, fbm(w * 3.3 + 11.)) * band);
  vec3 c = mix(vec3(.10, .27, .74), vec3(.30, .19, .64), smoothstep(.36, .72, m)); c = mix(c, vec3(.92, .70, .42), smoothstep(.64, .92, n) * band * .4);
  float a = clamp(dens * .5, 0., 1.) * (1. - smoothstep(.8, 1., max(abs(u.x), abs(u.y)) * .98)); return vec4(c * a, a);
}
vec4 over(vec4 top, vec4 under) { return vec4(top.rgb + under.rgb * (1. - top.a), top.a + under.a * (1. - top.a)); }

void main() {
  if (uKind > 7.5) { gl_FragColor = nebula(v) * uGain; return; }
  vec2 p = v / uR; float px = uPx / uR;
  float cr = cos(uRoll), sr = sin(uRoll); vec2 q = vec2(p.x * cr + p.y * sr, -p.x * sr + p.y * cr); q.y /= uFlat;      // the body's own upright, squashed at the poles
  float r2 = dot(q, q), r = sqrt(r2); bool isSun = uKind > 4.5 && uKind < 5.5;
  vec4 col = vec4(0.);
  // what lies round the body: its air catching the light, or a sun's corona
  if (isSun) { float an = atan(p.y, p.x), st = fbm(vec3(cos(an) * 2.4, sin(an) * 2.4, uTime * .04 + r * .5)), h = max(r - 1., 0.);
    float glow = exp(-h * 2.4) * (.42 + .9 * st) + .1 * exp(-h * .8); vec3 c = mix(vec3(1., .93, .66), vec3(1., .56, .16), smoothstep(0., .9, h));
    float a = clamp(glow, 0., 1.) * (1. - smoothstep(.72, .98, length(v))); col = vec4(c * a, a); }
  else if (r > 1. && uAir.a > 0.) { float h = r - 1., side = .22 + .78 * smoothstep(-.5, .6, dot(normalize(p), uL.xy)), a = clamp(uAir.a * exp(-h / uAirH) * side, 0., 1.) * (1. - smoothstep(.86, .99, length(v))); col = vec4(uAir.rgb * a, a); }
  // the ring plane, wherever this line of sight meets it
  vec4 ring = vec4(0.); float zr = 0.;
  if (uRing > .5) { zr = -(uAxis.x * p.x + uAxis.y * p.y) / uAxis.z; vec3 Q = vec3(p, zr); ring = rings(length(Q));
    float t = -dot(Q, uL), d2 = dot(Q, Q) - t * t, sh = t > 0. ? 0. : 1. - smoothstep(.9, 1.02, sqrt(max(d2, 0.)));     // the globe's shadow across the rings
    ring.rgb *= (.5 + .5 * abs(dot(uAxis, uL))) * (1. - .86 * sh); ring.rgb *= ring.a; }
  if (r < 1.) {
    float z = sqrt(1. - r2); vec3 nq = normalize(vec3(q.x, q.y / uFlat, z)), n = vec3(nq.x * cr - nq.y * sr, nq.x * sr + nq.y * cr, nq.z);
    vec3 P = vec3(p, z), s = uRot * normalize(vec3(q.x * cr - q.y * sr, q.x * sr + q.y * cr, z));
    float ndl = dot(n, uL), day = smoothstep(-.12, .3, ndl); vec3 c;
    if (isSun) c = sun(s, n.z);
    else { vec3 alb;
      if (uKind < .5) alb = mercury(s); else if (uKind < 1.5) alb = venus(s); else if (uKind < 2.5) alb = mars(s); else if (uKind < 3.5) alb = jupiter(s); else if (uKind < 4.5) alb = saturn(s); else alb = moon(s);
      alb *= uTint; float lit = day * (.3 + .8 * max(ndl, 0.));
      if (uRing > .5) { float den = dot(uAxis, uL); if (abs(den) > .02) { float t = -dot(uAxis, P) / den; if (t > 0.) lit *= 1. - .7 * rings(length(P + t * uL)).a; } }
      c = alb * (uAmb + (1. - uAmb) * lit);
      c += uAir.rgb * pow(1. - n.z, 2.6) * (.12 + .88 * day) * min(1., uAir.a * 2.2); }
    float a = clamp((1. - r) / (1.6 * px), 0., 1.); vec4 body = vec4(c * a, a);
    col = over(body, col);
    if (uRing > .5 && zr > z) col = over(ring, col);
  } else if (uRing > .5) col = over(ring, col);
  gl_FragColor = col * uGain;
}`;
  function shader(type, src) { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; }
  let U = {};
  try {
    const pr = gl.createProgram(); gl.attachShader(pr, shader(gl.VERTEX_SHADER, VS)); gl.attachShader(pr, shader(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(pr);
    if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(pr));
    gl.useProgram(pr); const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(pr, "a"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    ["uKind", "uR", "uPx", "uTime", "uSeed", "uAmb", "uAirH", "uFlat", "uRoll", "uRing", "uGain", "uRot", "uL", "uAxis", "uTint", "uAir"].forEach((k) => (U[k] = gl.getUniformLocation(pr, k)));
    gl.disable(gl.BLEND); gl.clearColor(0, 0, 0, 0);
  } catch (e) { console.warn("orbs: shader unavailable,", e.message); window.NEMATICA_ORBS = null; return; }

  // each body: which surface, how much of the square its radius takes (room for air, rings, corona), its air, its shape
  const BODY = {
    mercury: { kind: 0, R: 0.86, air: [0.72, 0.84, 1, 0.1], airH: 0.03, amb: 0.012, seed: 1.3 },
    venus: { kind: 1, R: 0.7, air: [1, 0.8, 0.52, 0.5], airH: 0.13, amb: 0.02, seed: 2.9 },
    mars: { kind: 2, R: 0.84, air: [1, 0.66, 0.5, 0.2], airH: 0.045, amb: 0.012, seed: 4.1 },
    jupiter: { kind: 3, R: 0.86, air: [1, 0.9, 0.76, 0.14], airH: 0.035, amb: 0.012, flat: 0.935, seed: 0.7 },
    saturn: { kind: 4, R: 0.42, air: [1, 0.92, 0.72, 0.12], airH: 0.04, amb: 0.012, flat: 0.9, ring: 1, seed: 6.2 },
    sun: { kind: 5, R: 0.36, air: [0, 0, 0, 0], airH: 0.1, amb: 1, seed: 3.3 },
    moon: { kind: 6, R: 0.9, air: [0.8, 0.88, 1, 0.07], airH: 0.02, amb: 0.03, seed: 5.5 },
    nebula: { kind: 8, R: 1, air: [0, 0, 0, 0], airH: 0.1, amb: 1, seed: 7.7 },
  };
  const norm = (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
  // paint one body into the corner of the working canvas at s by s device pixels
  function paint(name, s, o) {
    const B = BODY[name], roll = o.roll || 0, lean = o.lean || 0, spin = o.spin || 0;
    const cs = Math.cos(spin), ss = Math.sin(spin), cl = Math.cos(lean), sl = Math.sin(lean), cr = Math.cos(roll), sr = Math.sin(roll);
    // view space to the body's own space: undo the roll (about the line of sight), undo the lean (about x), undo the spin (about its axis)
    const m = (a, b) => { const r = []; for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) r.push(a[3 * i] * b[j] + a[3 * i + 1] * b[3 + j] + a[3 * i + 2] * b[6 + j]); return r; };
    const Rz = [cr, sr, 0, -sr, cr, 0, 0, 0, 1], Rx = [1, 0, 0, 0, cl, sl, 0, -sl, cl], Ry = [cs, 0, -ss, 0, 1, 0, ss, 0, cs], M = m(Ry, m(Rx, Rz));
    const axis = o.A ? [o.A[1], o.A[4], o.A[7]] : [-sr * cl, cr * cl, sl], L = norm(o.light || [-0.5, 0.45, 0.72]), t = o.tint || [1, 1, 1];
    const rollNow = o.A ? Math.atan2(-axis[0], axis[1]) : roll, sz = o.A ? axis[2] : sl;
    gl.viewport(0, 0, s, s); gl.scissor(0, 0, s, s); gl.enable(gl.SCISSOR_TEST); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform1f(U.uKind, B.kind); gl.uniform1f(U.uR, B.R); gl.uniform1f(U.uPx, 2 / s); gl.uniform1f(U.uTime, o.time || 0); gl.uniform1f(U.uSeed, B.seed + (o.seed || 0));
    gl.uniform1f(U.uAmb, o.amb == null ? B.amb : o.amb); gl.uniform1f(U.uAirH, B.airH); gl.uniform1f(U.uFlat, B.flat ? B.flat + (1 - B.flat) * sz * sz : 1); gl.uniform1f(U.uRoll, rollNow);
    gl.uniform1f(U.uRing, B.ring ? 1 : 0); gl.uniform1f(U.uGain, o.gain == null ? 1 : o.gain);
    gl.uniformMatrix3fv(U.uRot, false, new Float32Array(o.A || [M[0], M[3], M[6], M[1], M[4], M[7], M[2], M[5], M[8]]));       // column-major; o.A is body-to-view by rows, which read by columns is view-to-body
    gl.uniform3f(U.uL, L[0], L[1], L[2]); gl.uniform3f(U.uAxis, axis[0], axis[1], Math.abs(axis[2]) < 0.06 ? 0.06 : axis[2]); gl.uniform3f(U.uTint, t[0], t[1], t[2]);
    const a = o.air == null ? B.air : [B.air[0], B.air[1], B.air[2], B.air[3] * o.air]; gl.uniform4f(U.uAir, a[0], a[1], a[2], a[3]);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    return B;
  }
  let scale = 1;       // lowered by the scene when frames run slow: bodies are then painted smaller and stretched
  window.NEMATICA_ORBS = {
    has: (name) => !!BODY[name],
    // draw a body into a 2D canvas: centre (x, y) and globe radius R in that canvas's own units; dpr is its pixel density
    draw(ctx, name, x, y, R, dpr, o) { const B = BODY[name], half = R / B.R, s = Math.max(48, Math.min(768, Math.round(2 * half * dpr * scale)));
      paint(name, s, o || {}); const g = ctx.globalAlpha; if (o && o.alpha != null) ctx.globalAlpha = g * o.alpha;
      ctx.drawImage(cv, 0, cv.height - s, s, s, x - half, y - half, 2 * half, 2 * half); ctx.globalAlpha = g; },
    // a small picture of a body, as its own canvas; .R is the share of its half-width the globe's radius takes
    sprite(name, size, o) { const s = Math.min(1024, Math.round(size)), B = paint(name, s, o || {}), c = document.createElement("canvas"); c.width = c.height = s;
      c.getContext("2d").drawImage(cv, 0, cv.height - s, s, s, 0, 0, s, s); c.R = B.R; return c; },
    share: (name) => BODY[name].R,
    quality(q) { scale = q; },
  };
})();
