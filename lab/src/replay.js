// Loading and sampling a nematica-replay/1 bundle (written by nematica/export/replay.py).

export async function loadIndex() {
  const res = await fetch('./data/index.json')
  if (!res.ok) throw new Error('No replay index found in data/index.json')
  return res.json()
}

export async function loadReplay(file) {
  const res = await fetch(`./data/${file}`)
  if (!res.ok || !(res.headers.get('content-type') || '').includes('json')) throw new Error(`Could not load data/${file}`)
  const b = await res.json()
  if (b.format !== 'nematica-replay/1') throw new Error(`Unknown bundle format ${b.format}`)
  const n = b.n_frames
  return {
    ...b,
    t: Float64Array.from(b.t),
    angles: Float32Array.from(b.body.angles),           // n * k
    k: b.body.k,
    length: b.body.length_mm,
    path: Float32Array.from(b.path_mm),                 // n * 2
    velocity: Float32Array.from(b.behaviour.velocity),
    reversing: Uint8Array.from(b.behaviour.reversing),
    neurons: b.neurons.map((nr) => ({ ...nr, level: Float32Array.from(nr.level) })),
    duration: b.t[n - 1],
  }
}

// Fractional frame position for a time in seconds (frames are not perfectly uniform).
export function frameAt(replay, time) {
  const t = replay.t
  const n = t.length
  if (time <= t[0]) return { i: 0, a: 0 }
  if (time >= t[n - 1]) return { i: n - 2, a: 1 }
  let lo = 0, hi = n - 1
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1
    if (t[mid] <= time) lo = mid; else hi = mid
  }
  return { i: lo, a: (time - t[lo]) / (t[lo + 1] - t[lo]) }
}

// Smoothstep-free linear interpolation between the two neighbouring frames.
export function sampleBody(replay, { i, a }, outAngles, outNose) {
  const k = replay.k
  const A = replay.angles
  const o0 = i * k, o1 = (i + 1) * k
  for (let j = 0; j < k; j++) outAngles[j] = A[o0 + j] + a * (A[o1 + j] - A[o0 + j])
  const P = replay.path
  outNose[0] = P[2 * i] + a * (P[2 * i + 2] - P[2 * i])
  outNose[1] = P[2 * i + 1] + a * (P[2 * i + 3] - P[2 * i + 1])
}

export function sampleSeries(arr, { i, a }) {
  return arr[i] + a * (arr[i + 1] - arr[i])
}

export function formatTime(s) {
  const m = Math.floor(s / 60)
  const r = Math.floor(s % 60)
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
}
