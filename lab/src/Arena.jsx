import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useLab } from './store'

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
    vec3 base = vec3(0.004, 0.009, 0.014) + vec3(0.006, 0.012, 0.018) * d + vec3(0.003) * grain;
    // outside the arena: copper-containing agar, faintly warmer
    float r = length(vXY - uCentre);
    float outside = smoothstep(uRadius, uRadius + 0.15, r);
    base = mix(base, base * vec3(1.6, 1.15, 0.8) + vec3(0.012, 0.006, 0.0), outside);
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

export default function Arena() {
  const replay = useLab((s) => s.replay)
  const centre = replay.arena?.centre_mm ?? [0, 0]
  const radius = replay.arena?.radius_mm ?? 4

  const agar = useMemo(() => new THREE.ShaderMaterial({
    vertexShader: agarVert,
    fragmentShader: agarFrag,
    uniforms: { uCentre: { value: new THREE.Vector2(centre[0], centre[1]) }, uRadius: { value: radius } },
  }), [centre[0], centre[1], radius])

  // faint trail of where the real worm has been (last 60 s)
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
      if (t[j] < time - 60) continue
      pos[3 * count] = P[2 * j]; pos[3 * count + 1] = 0.0005; pos[3 * count + 2] = P[2 * j + 1]
      count++
    }
    trail.setDrawRange(0, count)
    trail.attributes.position.needsUpdate = true
  })

  return (
    <group>
      <mesh rotation-x={-Math.PI / 2} position={[centre[0], 0, centre[1]]} material={agar}>
        <planeGeometry args={[radius * 3, radius * 3, 1, 1]} />
      </mesh>
      {/* copper boundary, drawn as a faint metallic ring at the recorded arena radius [M] */}
      <mesh rotation-x={-Math.PI / 2} position={[centre[0], 0.001, centre[1]]}>
        <ringGeometry args={[radius - 0.012, radius + 0.012, 256]} />
        <meshBasicMaterial color="#c9874a" transparent opacity={0.55} toneMapped={false} />
      </mesh>
      <line ref={trailRef} geometry={trail}>
        <lineBasicMaterial color="#2f6f86" transparent opacity={0.22} />
      </line>
    </group>
  )
}
