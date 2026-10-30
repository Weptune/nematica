import { useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useLab } from './store'
import { centreline, radiusAt } from './body'
import { frameAt, sampleBody } from './replay'

const RING = 20

// Dark-field look: the cuticle glows at grazing angles (fresnel rim), with a faint fill.
const vertex = /* glsl */ `
  varying vec3 vNormal;
  varying vec3 vView;
  varying float vU;
  attribute float u;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vNormal = normalize(normalMatrix * normal);
    vView = normalize(-mv.xyz);
    vU = u;
    gl_Position = projectionMatrix * mv;
  }
`
const fragment = /* glsl */ `
  uniform vec3 uRim;
  uniform vec3 uFill;
  varying vec3 vNormal;
  varying vec3 vView;
  varying float vU;
  void main() {
    float f = 1.0 - abs(dot(normalize(vNormal), normalize(vView)));
    float rim = pow(f, 3.0);
    float head = smoothstep(0.22, 0.0, vU) * 0.10;     // pharynx reads slightly brighter
    float tail = smoothstep(0.88, 1.0, vU) * 0.35;     // tail fades
    vec3 col = uRim * rim * 0.75 + uFill * (0.018 + head);
    gl_FragColor = vec4(col * (1.0 - tail), 1.0);
  }
`

// Solves the body for the current time (runs first each frame) and draws it.
export default function Worm({ body }) {
  const replay = useLab((s) => s.replay)
  const n = body.n

  const geometry = useMemo(() => {
    const geom = new THREE.BufferGeometry()
    const u = new Float32Array(n * RING)
    const idx = []
    for (let i = 0; i < n; i++) for (let r = 0; r < RING; r++) u[i * RING + r] = i / (n - 1)
    for (let i = 0; i < n - 1; i++) {
      for (let r = 0; r < RING; r++) {
        const a = i * RING + r, b = i * RING + ((r + 1) % RING)
        const c = (i + 1) * RING + r, d = (i + 1) * RING + ((r + 1) % RING)
        idx.push(a, c, b, b, c, d)
      }
    }
    geom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * RING * 3), 3))
    geom.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(n * RING * 3), 3))
    geom.setAttribute('u', new THREE.BufferAttribute(u, 1))
    geom.setIndex(idx)
    return geom
  }, [n])

  const material = useMemo(() => new THREE.ShaderMaterial({
    vertexShader: vertex,
    fragmentShader: fragment,
    uniforms: { uRim: { value: new THREE.Color('#a6e6ff') }, uFill: { value: new THREE.Color('#4b8aa3') } },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
  }), [])

  useFrame(() => {
    const { time } = useLab.getState()
    body.frame = frameAt(replay, time)
    sampleBody(replay, body.frame, body.angles, body.nose)
    centreline(body.angles, body.nose, replay.length, body.pts, body.tans)

    const pos = geometry.attributes.position.array
    const nor = geometry.attributes.normal.array
    for (let i = 0; i < n; i++) {
      const px = body.pts[3 * i], py = body.pts[3 * i + 1], pz = body.pts[3 * i + 2]
      const nx = -body.tans[3 * i + 2], nz = body.tans[3 * i]
      const rad = radiusAt(i / (n - 1))
      for (let r = 0; r < RING; r++) {
        const phi = (r / RING) * Math.PI * 2
        const c = Math.cos(phi), s = Math.sin(phi)
        const o = (i * RING + r) * 3
        pos[o] = px + rad * nx * c; pos[o + 1] = py + rad * s * 0.92; pos[o + 2] = pz + rad * nz * c
        nor[o] = nx * c; nor[o + 1] = s; nor[o + 2] = nz * c
      }
    }
    geometry.attributes.position.needsUpdate = true
    geometry.attributes.normal.needsUpdate = true
  }, -2)

  return <mesh geometry={geometry} material={material} renderOrder={2} frustumCulled={false} />
}
