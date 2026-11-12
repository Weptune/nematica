import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { EffectComposer, Bloom, Vignette, Noise, DepthOfField, SMAA } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import * as THREE from 'three'
import { useLab } from '../src/store'
import { loadReplay } from '../src/replay'
import { createBodyState, pointOnBody, radiusAt, RBAR } from '../src/body'
import Worm from './FilmWorm'
import Neurons from './FilmNeurons'
import Arena from './FilmArena'

// Film renders of the project's real data: no interface, a scripted camera, time driven by the page clock.
const q = new URLSearchParams(location.search)
const SHOT = q.get('shot') || 'hero'
const MS = parseInt(q.get('ms') ?? '4')
let P0 = null                                  // page time when the shot starts
const elapsed = () => (P0 === null ? 0 : (performance.now() - P0) / 1000)
const ease = (x) => { x = Math.min(Math.max(x, 0), 1); return x * x * (3 - 2 * x) }
const mix = (a, b, x) => a + (b - a) * x
const D = Math.PI / 180

const SHOTS = {
  hero: { uid: '2024-06-18-12', t0: 231, dur: 12, s: 0.48, r: [1.6, 1.15], el: [34, 21], az: [-70, -25], dof: 0.9 },
  brain: { uid: '2024-06-18-12', t0: 246, dur: 10, tau: 0.35, s: 0.11, r: [0.34, 0.2], el: [14, 30], az: [-120, -30], dof: 3.2 },
}

function FilmClock({ t0 = 0, speed = 1, still = null }) {
  useFrame(() => { useLab.getState().setTime(still ?? t0 + speed * elapsed()) }, -3)
  return null
}

// Camera on a spherical path around a smoothed point on the body.
function BodyCamera({ body, cfg, dofRef }) {
  const { camera } = useThree()
  const tgt = useMemo(() => new THREE.Vector3(), [])
  const raw = useMemo(() => new THREE.Vector3(), [])
  const p = useMemo(() => new Float32Array(3), [])
  const first = useRef(true), last = useRef(0)
  const replay = useLab((s) => s.replay)
  useFrame(() => {
    pointOnBody(body.pts, body.tans, body.k, replay.length, cfg.s * replay.length, 0, 0, p)
    raw.set(p[0], p[1], p[2])
    const e = elapsed(), k = 1 - Math.exp(-Math.max(e - last.current, 0) / (cfg.tau ?? 0.6)); last.current = e
    if (first.current) { tgt.copy(raw); first.current = false } else tgt.lerp(raw, k)
    const x = ease(elapsed() / cfg.dur)
    const r = mix(cfg.r[0], cfg.r[1], x), el = mix(cfg.el[0], cfg.el[1], x) * D, az = mix(cfg.az[0], cfg.az[1], x) * D
    camera.position.set(tgt.x + r * Math.cos(el) * Math.sin(az), tgt.y + r * Math.sin(el), tgt.z + r * Math.cos(el) * Math.cos(az))
    camera.lookAt(tgt)
    if (dofRef?.current) dofRef.current.target = tgt
  }, -1)
  return null
}

function Post({ bloom = 0.6 }) {
  if (q.get('nopost')) return null
  return (
    <EffectComposer multisampling={MS}>
      <Bloom mipmapBlur intensity={bloom} luminanceThreshold={0.62} luminanceSmoothing={0.2} radius={0.55} />
      <Vignette eskil={false} offset={0.32} darkness={0.55} />
      {MS === 0 ? <SMAA /> : null}
    </EffectComposer>
  )
}

function Ready({ onReady }) {
  const n = useRef(0)
  useFrame(() => { if (++n.current === 3) onReady() })
  return null
}
const markReady = () => { P0 = performance.now(); window.__filmReady = true }

// ---------------------------------------------------------------- a recorded worm
function BodyShot({ cfg }) {
  const replay = useLab((s) => s.replay)
  const body = useMemo(() => createBodyState(replay.k), [replay])
  const dofRef = useRef()
  return (
    <Canvas dpr={1} camera={{ fov: 30, near: 0.005, far: 100 }} gl={{ antialias: true, preserveDrawingBuffer: true }}>
      <color attach="background" args={['#0d0a24']} />
      <FilmClock t0={cfg.t0} />
      <Arena trail={false} />
      <CopperGlow replay={replay} />
      <Worm body={body} />
      <Neurons body={body} />
      <BodyCamera body={body} cfg={cfg} dofRef={dofRef} />
      <Post />
      <Ready onReady={markReady} />
    </Canvas>
  )
}

function CopperGlow({ replay, wide = false }) {
  if (!replay.arena) return null
  const [cx, cz] = replay.arena.centre_mm, R = replay.arena.radius_mm, k = wide ? 4 : 1
  return <group rotation-x={-Math.PI / 2} position={[cx, 0.0015, cz]}>
    <mesh><ringGeometry args={[R - 0.005 * k, R + 0.005 * k, 1024]} /><meshBasicMaterial color={new THREE.Color('#ffb35c').multiplyScalar(1.05)} toneMapped={false} /></mesh>
    <mesh><ringGeometry args={[R - 0.03 * k, R + 0.03 * k, 1024]} /><meshBasicMaterial color="#ff9a4a" transparent opacity={0.05} toneMapped={false} depthWrite={false} blending={THREE.AdditiveBlending} /></mesh>
  </group>
}

function useReplay(file) {
  const [r, setR] = useState(null)
  useEffect(() => { loadReplay(file).then(setR) }, [file])
  return r
}

function Single({ cfg }) {
  const r = useReplay(`replay_${cfg.uid}.json`)
  const setReplay = useLab((s) => s.setReplay)
  useEffect(() => { if (r) setReplay(r) }, [r, setReplay])
  const replay = useLab((s) => s.replay)
  if (!replay) return null
  return <BodyShot cfg={cfg} />
}

// ---------------------------------------------------------------- real and model side by side
function PairView({ replay, side }) {
  const body = useMemo(() => createBodyState(replay.k), [replay])
  const dofRef = useRef()
  const cfg = { dur: 10, s: 0.45, r: [1.45, 1.15], el: [48, 34], az: [20, 45], tau: 0.7 }
  return (
    <Canvas dpr={1} camera={{ fov: 30, near: 0.005, far: 100 }} gl={{ antialias: true, preserveDrawingBuffer: true }}>
      <color attach="background" args={['#0d0a24']} />
      <Arena replay={replay} trail={false} />
      <CopperGlow replay={replay} />
      <Worm body={body} replay={replay} />
      <Neurons body={body} replay={replay} />
      <PairCamera body={body} replay={replay} cfg={cfg} />
      <Post />
      {side === 0 && <FilmClock t0={PAIR_T0} speed={2} />}
      {side === 0 && <Ready onReady={markReady} />}
    </Canvas>
  )
}
function PairCamera({ body, replay, cfg }) {
  const { camera } = useThree()
  const tgt = useMemo(() => new THREE.Vector3(), [])
  const p = useMemo(() => new Float32Array(3), [])
  const first = useRef(true), last = useRef(0)
  useFrame(() => {
    pointOnBody(body.pts, body.tans, body.k, replay.length, cfg.s * replay.length, 0, 0, p)
    const e = elapsed(), k = 1 - Math.exp(-Math.max(e - last.current, 0) / (cfg.tau ?? 0.6)); last.current = e
    if (first.current) { tgt.set(p[0], p[1], p[2]); first.current = false } else tgt.lerp(new THREE.Vector3(p[0], p[1], p[2]), k)
    const x = ease(elapsed() / cfg.dur)
    const r = mix(cfg.r[0], cfg.r[1], x), el = mix(cfg.el[0], cfg.el[1], x) * D, az = mix(cfg.az[0], cfg.az[1], x) * D
    camera.position.set(tgt.x + r * Math.cos(el) * Math.sin(az), tgt.y + r * Math.sin(el), tgt.z + r * Math.cos(el) * Math.cos(az))
    camera.lookAt(tgt)
  }, -1)
  return null
}
function Pair() {
  const set = q.get('set') || 'which2/round_1'
  const real = useReplay(`${set}_real.json`)
  const model = useReplay(`${set}_model.json`)
  if (!real || !model) return null
  return (
    <div className="pair">
      <div className="half"><PairView replay={real} side={0} /><div className="tag"><b>Recorded</b>a real worm, held out of training</div></div>
      <div className="half"><PairView replay={model} side={1} /><div className="tag"><b>Model</b>brain activity, speed and reversals simulated</div></div>
    </div>
  )
}
const PAIR_T0 = parseFloat(q.get('t0') || '60')

// ---------------------------------------------------------------- the swarm, in 3D
const swarmVert = /* glsl */ `
  varying vec3 vNormal; varying vec3 vView; varying float vU;
  attribute float u;
  void main() { vec4 mv = modelViewMatrix * vec4(position, 1.0); vNormal = normalize(normalMatrix * normal);
    vView = normalize(-mv.xyz); vU = u; gl_Position = projectionMatrix * mv; }`
const swarmFrag = /* glsl */ `
  varying vec3 vNormal; varying vec3 vView; varying float vU;
  attribute float rev;
  uniform vec3 uFwd; uniform vec3 uRev;
  varying float vRev;
  void main() {
    float f = 1.0 - abs(dot(normalize(vNormal), normalize(vView)));
    vec3 c = mix(uFwd, uRev, vRev);
    float head = smoothstep(0.12, 0.0, vU);
    vec3 col = c * (pow(f, 2.2) * 1.1 + 0.08) + c * head * 1.6;
    gl_FragColor = vec4(col * (1.0 - smoothstep(0.85, 1.0, vU) * 0.6), 1.0);
  }`

function SwarmWorms({ data }) {
  const W = data.worms.length, P = data.points, seg = data.length_mm / P
  const N = 40, RING = 10
  const geom = useMemo(() => {
    const g = new THREE.BufferGeometry()
    const verts = W * N * RING
    const u = new Float32Array(verts), rev = new Float32Array(verts), idx = []
    for (let w = 0; w < W; w++) for (let i = 0; i < N; i++) for (let r = 0; r < RING; r++) u[(w * N + i) * RING + r] = i / (N - 1)
    for (let w = 0; w < W; w++) for (let i = 0; i < N - 1; i++) for (let r = 0; r < RING; r++) {
      const o = w * N * RING, a = o + i * RING + r, b = o + i * RING + ((r + 1) % RING), c = o + (i + 1) * RING + r, d = o + (i + 1) * RING + ((r + 1) % RING)
      idx.push(a, c, b, b, c, d)
    }
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(verts * 3), 3))
    g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(verts * 3), 3))
    g.setAttribute('u', new THREE.BufferAttribute(u, 1))
    g.setAttribute('rev', new THREE.BufferAttribute(rev, 1))
    g.setIndex(idx)
    return g
  }, [W])
  const mat = useMemo(() => new THREE.ShaderMaterial({
    vertexShader: swarmVert.replace('attribute float u;', 'attribute float u; attribute float rev; varying float vRev;').replace('vU = u;', 'vU = u; vRev = rev;'),
    fragmentShader: swarmFrag.replace('attribute float rev;', ''),
    uniforms: { uFwd: { value: new THREE.Color('#d9d2ff') }, uRev: { value: new THREE.Color('#ffb35c') } },
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
  }), [])
  const revS = useMemo(() => new Float32Array(W), [W])
  const pts = useMemo(() => new Float32Array((P + 1) * 2), [P])
  const sm = useMemo(() => new Float32Array(N * 2), [])
  useFrame(() => {
    const ft = Math.min(useLab.getState().time / data.dt, data.frames - 1.001)
    const f = Math.floor(ft), a = ft - f
    const pos = geom.attributes.position.array, nor = geom.attributes.normal.array, rv = geom.attributes.rev.array
    for (let w = 0; w < W; w++) {
      const wd = data.worms[w]
      let x = wd.head[2 * f] * (1 - a) + wd.head[2 * f + 2] * a, y = wd.head[2 * f + 1] * (1 - a) + wd.head[2 * f + 3] * a
      pts[0] = x; pts[1] = y
      for (let p = 0; p < P; p++) {
        const a0 = wd.angles[f * P + p]; let a1 = wd.angles[(f + 1) * P + p]
        while (a1 - a0 > Math.PI) a1 -= 2 * Math.PI
        while (a1 - a0 < -Math.PI) a1 += 2 * Math.PI
        const an = a0 + (a1 - a0) * a
        x += seg * Math.cos(an); y += seg * Math.sin(an)
        pts[2 * p + 2] = x; pts[2 * p + 3] = y
      }
      // smooth resample to N points (Catmull-Rom through the P+1 joints)
      for (let i = 0; i < N; i++) {
        const s = (i / (N - 1)) * P, j = Math.min(Math.floor(s), P - 1), t = s - j
        const i0 = Math.max(j - 1, 0), i3 = Math.min(j + 2, P)
        for (let c = 0; c < 2; c++) {
          const p0 = pts[2 * i0 + c], p1 = pts[2 * j + c], p2 = pts[2 * (j + 1) + c], p3 = pts[2 * i3 + c]
          sm[2 * i + c] = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)
        }
      }
      const target = wd.reversing[f] ? 1 : 0
      revS[w] += (target - revS[w]) * 0.25
      for (let i = 0; i < N; i++) {
        const i2 = Math.min(i + 1, N - 1), i1 = Math.max(i - 1, 0)
        let tx = sm[2 * i2] - sm[2 * i1], tz = sm[2 * i2 + 1] - sm[2 * i1 + 1]
        const l = Math.hypot(tx, tz) || 1; tx /= l; tz /= l
        const nx = -tz, nz = tx, rad = radiusAt(i / (N - 1)) * 1.6
        for (let r = 0; r < RING; r++) {
          const ph = (r / RING) * Math.PI * 2, c = Math.cos(ph), s = Math.sin(ph)
          const o = ((w * N + i) * RING + r)
          pos[3 * o] = sm[2 * i] + rad * nx * c; pos[3 * o + 1] = RBAR * 1.6 + rad * s; pos[3 * o + 2] = sm[2 * i + 1] + rad * nz * c
          nor[3 * o] = nx * c; nor[3 * o + 1] = s; nor[3 * o + 2] = nz * c
          rv[o] = revS[w]
        }
      }
    }
    geom.attributes.position.needsUpdate = true; geom.attributes.normal.needsUpdate = true; geom.attributes.rev.needsUpdate = true
  }, -2)
  return <mesh geometry={geom} material={mat} frustumCulled={false} />
}

function SwarmCamera() {
  const { camera } = useThree()
  useFrame(() => {
    const x = ease(elapsed() / 14)
    const r = mix(11.5, 7.2, x), el = mix(62, 34, x) * D, az = mix(-25, 15, x) * D
    camera.position.set(r * Math.cos(el) * Math.sin(az), r * Math.sin(el), r * Math.cos(el) * Math.cos(az))
    camera.lookAt(0, 0, 0.4)
  }, -1)
  return null
}

function Swarm3D() {
  const [data, setData] = useState(null)
  useEffect(() => { fetch('./data/swarm1/swarm.json').then((r) => r.json()).then(setData) }, [])
  if (!data) return null
  const R = data.radius_mm
  const fake = { arena: { centre_mm: [0, 0], radius_mm: R }, path: new Float32Array(0), t: new Float64Array(0) }
  return (
    <Canvas dpr={1} camera={{ fov: 32, near: 0.05, far: 200 }} gl={{ antialias: true, preserveDrawingBuffer: true }}>
      <color attach="background" args={['#0d0a24']} />
      <FilmClock t0={parseFloat(q.get('t0') || '120')} speed={8} />
      <Arena replay={fake} trail={false} />
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.002, 0]}>
        <ringGeometry args={[R - 0.03, R + 0.03, 256]} />
        <meshBasicMaterial color={new THREE.Color('#ffb35c').multiplyScalar(1.2)} toneMapped={false} />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.001, 0]}>
        <ringGeometry args={[R + 0.03, R + 0.9, 256]} />
        <meshBasicMaterial color="#2a1530" transparent opacity={0.45} />
      </mesh>
      <SwarmWorms data={data} />
      <SwarmCamera />
      <Post />
      <Ready onReady={markReady} />
    </Canvas>
  )
}

// ---------------------------------------------------------------- the echo of one stimulation, in 3D
const RISE = new THREE.Color('#ff5fae'), FALL = new THREE.Color('#5fb8ff'), STIM = new THREE.Color('#fff4e0')
function EchoNeurons({ body, echo, brain }) {
  const replay = useLab((s) => s.replay)
  const mesh = useRef(), bg = useRef()
  const list = echo.neurons, R = echo.brains[brain].R
  const tmp = useMemo(() => new THREE.Object3D(), []), col = useMemo(() => new THREE.Color(), []), p = useMemo(() => new Float32Array(3), [])
  const place = (pos) => {
    const s = pos[0] / 1000, r = radiusAt(s / replay.length) * 0.8
    pointOnBody(body.pts, body.tans, body.k, replay.length, s, Math.max(-r, Math.min(r, pos[1] / 1000)), Math.max(-r, Math.min(r, pos[2] / 1000)), p)
  }
  useFrame(() => {
    const te = elapsed() * 2 - 2                 // two seconds before the pulse, then 2x speed
    const fi = Math.max(0, te / echo.dt), i0 = Math.min(Math.floor(fi), 59), a = Math.min(fi - i0, 1)
    for (let i = 0; i < echo.background.length; i++) {
      place(echo.background[i].pos_um); tmp.position.set(p[0], p[1], p[2]); tmp.scale.setScalar(0.75); tmp.updateMatrix()
      bg.current.setMatrixAt(i, tmp.matrix)
    }
    bg.current.instanceMatrix.needsUpdate = true
    for (let i = 0; i < list.length; i++) {
      const nr = list[i]
      place(nr.pos_um)
      let v = 0, glow = 0
      if (nr.cls === echo.stim) {
        glow = te > 0 && te < 2 ? 1.5 : te >= 2 ? 1.3 * Math.exp(-(te - 2) / 1.5) + 0.2 : 0.2
        col.copy(STIM).multiplyScalar(glow)
      } else if (R[nr.cls] && te > 0) {
        const s = R[nr.cls]; v = s[i0] + (s[Math.min(i0 + 1, s.length - 1)] - s[i0]) * a
        const z = Math.min(Math.abs(v) / echo.threshold, 1.4)
        glow = 0.05 + 0.55 * z * z
        col.copy(v > 0 ? RISE : FALL).multiplyScalar(glow)
      } else { col.copy(RISE).multiplyScalar(0.06) }
      tmp.position.set(p[0], p[1], p[2]); tmp.scale.setScalar(1 + Math.min(glow, 2) * 0.18); tmp.updateMatrix()
      mesh.current.setMatrixAt(i, tmp.matrix); mesh.current.setColorAt(i, col)
    }
    mesh.current.instanceMatrix.needsUpdate = true; mesh.current.instanceColor.needsUpdate = true
  })
  return <>
    <instancedMesh ref={bg} args={[null, null, echo.background.length]} frustumCulled={false}>
      <sphereGeometry args={[0.0022, 10, 10]} />
      <meshBasicMaterial color={new THREE.Color('#4a3f86')} toneMapped={false} transparent opacity={0.6} depthWrite={false} blending={THREE.AdditiveBlending} />
    </instancedMesh>
    <instancedMesh ref={mesh} args={[null, null, list.length]} frustumCulled={false}>
      <sphereGeometry args={[0.0028, 14, 14]} />
      <meshBasicMaterial toneMapped={false} transparent opacity={0.95} depthWrite={false} blending={THREE.AdditiveBlending} />
    </instancedMesh>
  </>
}
function EchoView({ echo, brain, ready }) {
  const replay = useLab((s) => s.replay)
  const body = useMemo(() => createBodyState(replay.k), [replay])
  const dofRef = useRef()
  const cfg = { dur: 14, s: 0.1, r: [0.4, 0.29], el: [24, 36], az: [-100, -45], tau: 0.01 }
  return (
    <Canvas dpr={1} camera={{ fov: 30, near: 0.002, far: 50 }} gl={{ antialias: true, preserveDrawingBuffer: true }}>
      <color attach="background" args={['#0d0a24']} />
      <Arena trail={false} />
      <Worm body={body} />
      <EchoNeurons body={body} echo={echo} brain={brain} />
      <BodyCamera body={body} cfg={cfg} dofRef={dofRef} />
      <Post />
      {ready && <Ready onReady={markReady} />}
    </Canvas>
  )
}
function Echo() {
  const [echo, setEcho] = useState(null)
  const r = useReplay('replay_2024-06-18-12.json')
  const setReplay = useLab((s) => s.setReplay)
  useEffect(() => { fetch('./data/film_echo.json').then((x) => x.json()).then(setEcho) }, [])
  useEffect(() => { if (r) { setReplay(r); useLab.getState().setTime(parseFloat(q.get('pose') || '300')) } }, [r, setReplay])
  const replay = useLab((s) => s.replay)
  if (!echo || !replay) return null
  const b = parseInt(q.get('brain') || '-1')
  if (b >= 0) return <EchoView echo={echo} brain={b} ready />
  return (
    <div className="pair">
      <PulseClock />
      <div className="half"><EchoView echo={echo} brain={0} ready /><div className="tag"><b>Real worm</b>AVE switched on with light</div></div>
      <div className="half"><EchoView echo={echo} brain={1} /><div className="tag"><b>Model learned from rest</b>the same pulse</div></div>
    </div>
  )
}

function PulseClock() {
  const ref = useRef()
  useEffect(() => {
    let raf
    const tick = () => {
      const te = elapsed() * 2 - 2
      if (ref.current) {
        ref.current.className = 'clock' + (te > 0 && te < 2 ? ' on' : '')
        ref.current.innerHTML = te < 0 ? 'Before the pulse' : te < 2 ? 'Light pulse to AVE' : `${(te).toFixed(1)} s after the pulse`
      }
      raf = requestAnimationFrame(tick)
    }
    tick()
    return () => cancelAnimationFrame(raf)
  }, [])
  return <div ref={ref} className="clock" />
}

// ---------------------------------------------------------------- one real worm's whole recorded path, as a time-lapse
function PathRibbon({ replay, speed, t0 }) {
  const n = replay.t.length, P = replay.path
  const geom = useMemo(() => {
    const g = new THREE.BufferGeometry()
    const pos = new Float32Array(n * 2 * 3), col = new Float32Array(n * 2 * 3), idx = []
    const fwd = new THREE.Color('#b9a8ff'), rev = new THREE.Color('#ffb35c'), c = new THREE.Color()
    // lightly smoothed centre path
    const sx = new Float32Array(n), sz = new Float32Array(n)
    for (let j = 0; j < n; j++) { let x = 0, z = 0, k = 0; for (let m = Math.max(0, j - 3); m <= Math.min(n - 1, j + 3); m++) { x += P[2 * m]; z += P[2 * m + 1]; k++ } sx[j] = x / k; sz[j] = z / k }
    const w = 0.014
    for (let j = 0; j < n; j++) {
      const a = Math.max(j - 1, 0), b = Math.min(j + 1, n - 1)
      let tx = sx[b] - sx[a], tz = sz[b] - sz[a]; const l = Math.hypot(tx, tz) || 1; tx /= l; tz /= l
      pos.set([sx[j] - tz * w, 0.003, sz[j] + tx * w, sx[j] + tz * w, 0.003, sz[j] - tx * w], 6 * j)
      c.copy(replay.reversing[j] ? rev : fwd).multiplyScalar(replay.reversing[j] ? 1.2 : 0.85)
      col.set([c.r, c.g, c.b, c.r, c.g, c.b], 6 * j)
      if (j < n - 1) { const o = 2 * j; idx.push(o, o + 2, o + 1, o + 1, o + 2, o + 3) }
    }
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.BufferAttribute(col, 3)); g.setIndex(idx)
    return g
  }, [replay])
  useFrame(() => {
    const t = useLab.getState().time
    let j = 0; while (j < n - 1 && replay.t[j] < t) j++
    geom.setDrawRange(0, Math.max(0, (j - 1) * 6))
  })
  return <mesh geometry={geom} frustumCulled={false}><meshBasicMaterial vertexColors toneMapped={false} transparent opacity={0.85} side={THREE.DoubleSide} depthWrite={false} /></mesh>
}
function HeadMarker({ body }) {
  const ref = useRef()
  useFrame(() => { ref.current.position.set(body.pts[0], 0.02, body.pts[2]) })
  return <mesh ref={ref}><sphereGeometry args={[0.035, 20, 20]} /><meshBasicMaterial color={new THREE.Color('#fff2fb').multiplyScalar(1.4)} toneMapped={false} /></mesh>
}
function PathCamera({ replay }) {
  const { camera } = useThree()
  useFrame(() => {
    const [cx, cz] = replay.arena.centre_mm
    const x = ease(elapsed() / 14)
    const r = mix(15.5, 13.2, x), el = mix(72, 60, x) * D, az = mix(-20, 25, x) * D
    camera.position.set(cx + r * Math.cos(el) * Math.sin(az), r * Math.sin(el), cz + r * Math.cos(el) * Math.cos(az))
    camera.lookAt(cx, 0, cz + 0.3)
  }, -1)
  return null
}
function PathShot() {
  const r = useReplay('replay_2024-06-18-12.json')
  const setReplay = useLab((s) => s.setReplay)
  useEffect(() => { if (r) setReplay(r) }, [r, setReplay])
  const replay = useLab((s) => s.replay)
  const body = useMemo(() => replay && createBodyState(replay.k), [replay])
  if (!replay) return null
  const speed = replay.duration / 13
  return (
    <>
      <Canvas dpr={1} camera={{ fov: 30, near: 0.05, far: 200 }} gl={{ antialias: true, preserveDrawingBuffer: true }}>
        <color attach="background" args={['#0d0a24']} />
        <FilmClock t0={0} speed={speed} />
        <Arena trail={false} />
        <CopperGlow replay={replay} wide />
        <PathRibbon replay={replay} />
        <Worm body={body} />
        <HeadMarker body={body} />
        <PathCamera replay={replay} />
        <Post />
        <Ready onReady={markReady} />
      </Canvas>
      <PathClock duration={replay.duration} speed={speed} />
    </>
  )
}
function PathClock({ duration, speed }) {
  const ref = useRef()
  useEffect(() => {
    let raf
    const tick = () => {
      const t = Math.min(elapsed() * speed, duration)
      if (ref.current) ref.current.innerHTML = `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')} <span>of ${Math.floor(duration / 60)}:${String(Math.floor(duration % 60)).padStart(2, '0')} recorded</span>`
      raf = requestAnimationFrame(tick)
    }
    tick()
    return () => cancelAnimationFrame(raf)
  }, [duration, speed])
  return <div ref={ref} className="clock corner" />
}

export default function Film() {
  useEffect(() => { useLab.getState().setPlaying(false) }, [])
  if (SHOT === 'pair') return <Pair />
  if (SHOT === 'swarm') return <Swarm3D />
  if (SHOT === 'echo') return <Echo />
  if (SHOT === 'path') return <PathShot />
  return <Single cfg={SHOTS[SHOT]} />
}
