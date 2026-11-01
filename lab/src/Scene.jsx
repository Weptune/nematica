import { useMemo, useRef } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { EffectComposer, Bloom, Vignette, Noise, ChromaticAberration } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import * as THREE from 'three'
import { useLab } from './store'
import { createBodyState } from './body'
import Worm from './Worm'
import Neurons from './Neurons'
import Arena from './Arena'

// Advances time while playing (one place, so everything stays in sync).
export function Clock({ embedded = false }) {
  const lastSent = useRef(-1)
  useFrame((_, dt) => {
    const s = useLab.getState()
    if (!s.playing || !s.replay) return
    let t = s.time + Math.min(dt, 0.1) * s.speed
    if (t >= s.replay.duration) t = 0
    s.setTime(t)
    if (embedded && window.parent !== window && Math.floor(t) !== lastSent.current) {
      lastSent.current = Math.floor(t)
      window.parent.postMessage({ type: 'nematica-lab-time', seconds: lastSent.current }, location.origin)
    }
  }, -3)
  return null
}

// Keep the world orientation stable and let the worm travel through the frame.
// The camera only catches up once the body crosses a loose central tracking window.
export function FollowHead({ body, zoom = 1, cinematic = false }) {
  const controls = useRef()
  const { camera } = useThree()
  const target = useMemo(() => new THREE.Vector3(), [])
  const delta = useMemo(() => new THREE.Vector3(), [])
  const started = useRef(false)
  useFrame(() => {
    if (!controls.current) return
    // Framing the mid-body shows a complete crawl instead of a head turning in place.
    const s = Math.floor((body.n - 1) * 0.48)
    target.set(body.pts[3 * s], 0.02, body.pts[3 * s + 2])
    if (!started.current) {
      controls.current.target.copy(target)
      const overview = new URLSearchParams(location.search).get('view') === 'arena'
      if (overview) camera.position.set(target.x + 2, 12, target.z + 9)
      else camera.position.set(target.x + 0.2 * zoom, 1.65 * zoom, target.z + 1.25 * zoom)
      started.current = true
    }
    delta.copy(target).sub(controls.current.target)
    delta.y = 0
    const drift = delta.length()
    const window = cinematic ? 0.24 : 0.20
    if (drift > window) {
      delta.multiplyScalar(((drift - window) / drift) * (cinematic ? 0.09 : 0.065))
      controls.current.target.add(delta)
      camera.position.add(delta)
    }
    controls.current.update()
  }, -1)
  return <OrbitControls ref={controls} makeDefault enableDamping dampingFactor={0.08} minDistance={0.12} maxDistance={8} enableRotate={!cinematic} enableZoom={!cinematic} />
}

export default function Scene({ cinematic = false }) {
  const replay = useLab((s) => s.replay)
  const body = useMemo(() => createBodyState(replay.k), [replay])
  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ fov: 32, near: 0.005, far: 100, position: [0.3, 0.8, 0.6] }}
      gl={{ antialias: false, powerPreference: 'high-performance', preserveDrawingBuffer: true }}
      onPointerMissed={() => useLab.getState().setSelected(null)}
    >
      <color attach="background" args={['#020509']} />
      <Clock embedded={cinematic} />
      <Arena />
      <Worm body={body} />
      <Neurons body={body} />
      <FollowHead body={body} zoom={window.innerWidth < 700 ? 1.35 : 1} cinematic={cinematic} />
      <EffectComposer multisampling={4}>
        <Bloom mipmapBlur intensity={1.1} luminanceThreshold={0.6} luminanceSmoothing={0.25} radius={0.65} />
        <ChromaticAberration offset={[0.0006, 0.0004]} radialModulation modulationOffset={0.4} />
        <Noise premultiply blendFunction={BlendFunction.ADD} opacity={0.12} />
        <Vignette eskil={false} offset={0.25} darkness={0.85} />
      </EffectComposer>
    </Canvas>
  )
}
