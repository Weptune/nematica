import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useLab } from '../src/store'

// Procedural agar: dark field with fine grain and slow, soft density variation.  [A: display]
const agarFrag = /* glsl */ `
  varying vec2 vXY;
  uniform vec2 uCentre;
  uniform float uRadius;
  float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
  }
  float fbm(vec2 p) { float v = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { v += a * noise(p); p *= 2.03; a *= 0.5; } return v; }
  void main() {
    float d = fbm(vXY * 6.0) * 0.6 + fbm(vXY * 40.0) * 0.4;
    float grain = hash(floor(vXY * 900.0)) * 0.5;
    vec3 base = vec3(0.026, 0.020, 0.072) + vec3(0.012, 0.009, 0.024) * d + vec3(0.002) * grain;
    // outside the arena: copper-containing agar, faintly warmer
    float r = length(vXY - uCentre);
    float outside = smoothstep(uRadius, uRadius + 0.15, r);
    base = mix(base, base * vec3(1.25, 0.95, 0.85) + vec3(0.030, 0.012, 0.010), outside);
    gl_FragColor = vec4(base, 1.0);
  }
`
const agarVert = /* glsl */ `
  varying vec2 vXY;
  void main() {
    vec4 w = modelMatrix * vec4(position, 1.0);
    vXY = w.xz;
    gl_Position = projectionMatrix * viewMatrix * w;
  }
`

const NOAGAR = new URLSearchParams(location.search).get('noagar')
export default function Arena({ replay: given, trail: showTrail = true }) {
  const stored = useLab((s) => s.replay)
  const replay = given ?? stored
  const ring = !!replay.arena                     // no arena in the bundle: plain agar, no copper ring
  const centre = replay.arena?.centre_mm ?? [0, 0]
  const radius = replay.arena?.radius_mm ?? 40

  const agar = useMemo(() => new THREE.ShaderMaterial({
    vertexShader: agarVert,
    fragmentShader: agarFrag,
    uniforms: { uCentre: { value: new THREE.Vector2(centre[0], centre[1]) }, uRadius: { value: radius } },
  }), [centre[0], centre[1], radius])

  // Short, lightly smoothed path trail. Smoothing only affects the display, not the replay.
  const trail = useMemo(() => {
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(400 * 3), 3))
    return g
  }, [])
  const trailRef = useRef()

  useFrame(() => {
    const { time } = useLab.getState()
    const P = replay.path, t = replay.t
    const pos = trail.attributes.position.array
    let count = 0
    for (let j = 0; j < t.length && count < 400; j++) {
      if (t[j] > time) break
      if (t[j] < time - 8) continue
      let x = 0, z = 0, samples = 0
      for (let k = Math.max(0, j - 2); k <= Math.min(t.length - 1, j + 2); k++) {
        x += P[2 * k]; z += P[2 * k + 1]; samples++
      }
      pos[3 * count] = x / samples; pos[3 * count + 1] = 0.004; pos[3 * count + 2] = z / samples
      count++
    }
    trail.setDrawRange(0, count)
    trail.attributes.position.needsUpdate = true
  })

  return (
    <group>
      <mesh rotation-x={-Math.PI / 2} position={[centre[0], 0, centre[1]]} material={NOAGAR ? undefined : agar}>
        <planeGeometry args={[radius * 3, radius * 3, 1, 1]} />
      </mesh>
      {/* copper boundary, drawn as a faint metallic ring at the recorded arena radius [M] */}
      {ring && (
        <mesh rotation-x={-Math.PI / 2} position={[centre[0], 0.001, centre[1]]}>
          <ringGeometry args={[radius - 0.012, radius + 0.012, 256]} />
          <meshBasicMaterial color="#c9874a" transparent opacity={0.55} toneMapped={false} />
        </mesh>
      )}
      {showTrail && <line ref={trailRef} geometry={trail} renderOrder={1}>
        <lineBasicMaterial color="#2f6f86" transparent opacity={0.28} />
      </line>}
    </group>
  )
}
