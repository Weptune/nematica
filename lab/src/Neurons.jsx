import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useLab } from './store'
import { pointOnBody, radiusAt } from './body'
import { sampleSeries } from './replay'

const GCAMP = new THREE.Color('#5dff8a')
const tmp = new THREE.Object3D()
const col = new THREE.Color()
const p = new Float32Array(3)

// Stable pseudo-NeuroPAL colour per neuron class (display only, not the NeuroPAL atlas colours).
function identityColour(cls) {
  let h = 0
  for (let i = 0; i < cls.length; i++) h = (h * 31 + cls.charCodeAt(i)) >>> 0
  return new THREE.Color().setHSL((h % 360) / 360, 0.85, 0.6)
}

export default function Neurons({ body, replay: given }) {
  const stored = useLab((s) => s.replay)
  const replay = given ?? stored
  const mode = useLab((s) => s.mode)
  const setHovered = useLab((s) => s.setHovered)
  const setSelected = useLab((s) => s.setSelected)
  const mesh = useRef()
  const neurons = replay.neurons
  const count = neurons.length
  const ids = useMemo(() => neurons.map((nr) => identityColour(nr.cls)), [neurons])

  useEffect(() => {
    for (let i = 0; i < count; i++) mesh.current.setColorAt(i, GCAMP)
    mesh.current.instanceColor.needsUpdate = true
  }, [count])

  useFrame(() => {
    const { selected, hovered } = useLab.getState()
    const len = replay.length
    for (let i = 0; i < count; i++) {
      const nr = neurons[i]
      const s = nr.pos_um[0] / 1000
      const r = radiusAt(s / len) * 0.8
      // atlas dorsal-ventral -> in-plane offset, left-right -> vertical (worm lies on its side) [A]
      const side = Math.max(-r, Math.min(r, nr.pos_um[1] / 1000))
      const up = Math.max(-r, Math.min(r, nr.pos_um[2] / 1000))
      pointOnBody(body.pts, body.tans, body.k, len, s, side, up, p)
      const level = sampleSeries(nr.level, body.frame)
      const focus = i === selected || i === hovered
      tmp.position.set(p[0], p[1], p[2])
      tmp.scale.setScalar(focus ? 1.6 : 1)
      tmp.updateMatrix()
      mesh.current.setMatrixAt(i, tmp.matrix)
      // dim floor so silent nuclei stay faintly visible; bright neurons exceed 1 and bloom
      const gain = 0.05 + 3.2 * level * level + (focus ? 0.6 : 0)
      col.copy(mode === 'identity' ? ids[i] : GCAMP).multiplyScalar(mode === 'identity' ? 0.9 + 0.5 * level : gain)
      mesh.current.setColorAt(i, col)
    }
    mesh.current.instanceMatrix.needsUpdate = true
    mesh.current.instanceColor.needsUpdate = true
  })

  return (
    <instancedMesh
      ref={mesh}
      args={[null, null, count]}
      frustumCulled={false}
      renderOrder={3}
      onPointerMove={(e) => { e.stopPropagation(); setHovered(e.instanceId) }}
      onPointerOut={() => setHovered(null)}
      onClick={(e) => { e.stopPropagation(); setSelected(e.instanceId) }}
    >
      <sphereGeometry args={[0.0024, 12, 12]} />
      <meshBasicMaterial toneMapped={false} transparent opacity={0.95} depthWrite={false} blending={THREE.AdditiveBlending} />
    </instancedMesh>
  )
}
