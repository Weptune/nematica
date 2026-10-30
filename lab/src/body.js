// Body geometry from sampled segment angles. Units: mm. World: x right, z = image y, y up.
//
// The worm lies on its side on the agar, so the centreline sits one radius above the plane.
// Radius profile: Cohen and Ranner taper R(u) = Rbar * 2 sqrt((eps+u)(eps+1-u)) / (1+2 eps).  [A]

export const RBAR = 0.025      // mm, about 50 um wide at mid-body for a young adult  [A]
export const EPS = 0.004

// Closed at both ends (radius 0 at the nose and tail tips) so the tube is capped.
export function radiusAt(u) {
  const v = Math.min(Math.max(u, 0), 1)
  if (v <= 0 || v >= 1) return 0
  return (RBAR * 2 * Math.sqrt((EPS + v) * (EPS + 1 - v))) / (1 + 2 * EPS)
}

// Fill pts (n+1)*3 and tangents (n+1)*3 from angles (n) and nose position.
// Angles give the direction of each segment from nose to tail.
export function centreline(angles, nose, length, pts, tans) {
  const n = angles.length
  const ds = length / n
  let x = nose[0], z = nose[1]
  pts[0] = x; pts[1] = RBAR; pts[2] = z
  for (let j = 0; j < n; j++) {
    x += ds * Math.cos(angles[j])
    z += ds * Math.sin(angles[j])
    pts[3 * (j + 1)] = x; pts[3 * (j + 1) + 1] = RBAR; pts[3 * (j + 1) + 2] = z
  }
  for (let j = 0; j <= n; j++) {
    const a = Math.min(Math.max(j - 0.5, 0), n - 1)
    const lo = Math.floor(a), hi = Math.min(lo + 1, n - 1), f = a - lo
    // tangent points from tail toward nose (the direction of forward motion)
    const th = angles[lo] + f * (angles[hi] - angles[lo]) + Math.PI
    tans[3 * j] = Math.cos(th); tans[3 * j + 1] = 0; tans[3 * j + 2] = Math.sin(th)
  }
}

// Shared per-frame body state, solved once per frame and read by the body and the neurons.
export function createBodyState(k) {
  return { k, n: k + 1, angles: new Float32Array(k), nose: new Float32Array(2),
           pts: new Float32Array((k + 1) * 3), tans: new Float32Array((k + 1) * 3), frame: { i: 0, a: 0 } }
}

// Position along the body at arclength s (mm from the nose), with an in-plane offset
// `side` (mm, along the body normal) and a vertical offset `up` (mm).
export function pointOnBody(pts, tans, n, length, s, side, up, out) {
  const f = Math.min(Math.max((s / length) * n, 0), n)
  const lo = Math.min(Math.floor(f), n - 1), a = f - lo
  const px = pts[3 * lo] + a * (pts[3 * lo + 3] - pts[3 * lo])
  const pz = pts[3 * lo + 2] + a * (pts[3 * lo + 5] - pts[3 * lo + 2])
  const tx = tans[3 * lo], tz = tans[3 * lo + 2]
  // in-plane normal (rotate tangent by 90 degrees)
  out[0] = px - tz * side
  out[1] = RBAR + up
  out[2] = pz + tx * side
  return out
}
