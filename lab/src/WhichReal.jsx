import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { EffectComposer, Bloom, Vignette, Noise } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import * as THREE from 'three'

// "Which one is real?": two brains, one real recording and one model sample, same neurons,
// shown class by class at atlas positions. Brains only: the model has no body yet.

const BASE = 'data/which/'
const UM = 0.0115                      // scene units per micrometre
const GCAMP = new THREE.Color('#5dff8a')
const DIM = new THREE.Color('#0b2a18')
const col = new THREE.Color()
const tmp = new THREE.Object3D()
const SPEED = 3                        // playback speed (x real time)
const VERDICT = { inside: 'inside', 'too typical': 'too typical', outside: 'outside', 'not scored': 'n/a' }

function flatten(levels) {
  const n = levels.length
  const m = levels[0].length
  const out = new Float32Array(n * m)
  for (let t = 0; t < n; t++) for (let i = 0; i < m; i++) out[t * m + i] = levels[t][i] / 255
  return out
}

function Brain({ round, levels, offsetX, clock }) {
  const mesh = useRef()
  const group = useRef()
  const n = round.neurons.length
  const centre = useMemo(() => {
    const ap = round.neurons.map((nr) => nr.pos_um[0])
    return (Math.min(...ap) + Math.max(...ap)) / 2
  }, [round])

  useEffect(() => {
    round.neurons.forEach((nr, i) => {
      const [ap, dv, lr] = nr.pos_um
      tmp.position.set((ap - centre) * UM, dv * UM, lr * UM)
      tmp.updateMatrix()
      mesh.current.setMatrixAt(i, tmp.matrix)
      mesh.current.setColorAt(i, DIM)
    })
    mesh.current.instanceMatrix.needsUpdate = true
    mesh.current.instanceColor.needsUpdate = true
  }, [round, centre])

  useFrame((_, delta) => {
    const f = Math.floor(clock.current.t / round.dt) % round.n_frames
    for (let i = 0; i < n; i++) {
      const level = levels[f * n + i]
      col.copy(DIM).lerp(GCAMP, level).multiplyScalar(0.35 + 2.4 * level * level)
      mesh.current.setColorAt(i, col)
    }
    mesh.current.instanceColor.needsUpdate = true
    group.current.rotation.x = 0.35 * Math.sin(clock.current.t * 0.05)   // slow turn, for depth
  })

  return (
    <group position={[offsetX, 0, 0]}>
      <group ref={group}>
        <instancedMesh ref={mesh} args={[null, null, n]}>
          <sphereGeometry args={[1.6 * UM, 14, 10]} />
          <meshBasicMaterial toneMapped={false} />
        </instancedMesh>
      </group>
    </group>
  )
}

function Clock({ clock, playing }) {
  useFrame((_, delta) => { if (playing) clock.current.t += delta * SPEED })
  return null
}

export default function WhichReal() {
  const [index, setIndex] = useState(null)
  const [k, setK] = useState(0)
  const [round, setRound] = useState(null)
  const [guess, setGuess] = useState(null)
  const [score, setScore] = useState({ right: 0, played: 0 })
  const [playing, setPlaying] = useState(true)
  const [error, setError] = useState(null)
  const clock = useRef({ t: 0 })
  const [shownT, setShownT] = useState(0)

  useEffect(() => {
    fetch(BASE + 'index.json').then((r) => r.json()).then(setIndex).catch((e) => setError(String(e)))
  }, [])
  useEffect(() => {
    if (!index) return
    setRound(null)
    setGuess(null)
    clock.current.t = 0
    fetch(BASE + index.rounds[k].file).then((r) => r.json()).then((d) => setRound({
      ...d, leftLv: flatten(d.left), rightLv: flatten(d.right),
    })).catch((e) => setError(String(e)))
  }, [index, k])
  useEffect(() => {
    const id = setInterval(() => setShownT(clock.current.t), 250)
    return () => clearInterval(id)
  }, [])

  const choose = (side) => {
    if (guess) return
    setGuess(side)
    setScore((s) => ({ right: s.right + (side === round.answer ? 1 : 0), played: s.played + 1 }))
  }

  if (error) return <div className="splash"><div>Could not load the rounds: {error}<br />Run <code>python scripts/export_which_real.py</code>, then reload.</div></div>
  if (!index || !round) return <div className="splash">Loading brains…</div>

  const correct = guess && guess === round.answer
  const t = shownT % (round.n_frames * round.dt)
  return (
    <>
      <Canvas camera={{ position: [0, 0.55, 3.1], fov: 38 }} gl={{ antialias: true }}>
        <color attach="background" args={['#020509']} />
        <Clock clock={clock} playing={playing} />
        <Brain round={round} levels={round.leftLv} offsetX={-1.12} clock={clock} />
        <Brain round={round} levels={round.rightLv} offsetX={1.12} clock={clock} />
        <EffectComposer multisampling={4}>
          <Bloom mipmapBlur intensity={1.25} luminanceThreshold={0.45} luminanceSmoothing={0.25} radius={0.7} />
          <Noise premultiply blendFunction={BlendFunction.ADD} opacity={0.1} />
          <Vignette eskil={false} offset={0.25} darkness={0.85} />
        </EffectComposer>
      </Canvas>

      <div className="overlay which">
        <header>
          <div className="brand">NEMATICA</div>
          <div className="title">Which one is real?</div>
          <div className="subtitle">Two worm brains. One is a recording of a real worm; the other was generated by a model. Same neurons, same atlas positions.</div>
        </header>
        <div className="tally mono">round {k + 1} / {index.rounds.length} · score {score.right} / {score.played}</div>

        <div className="sides">
          {['left', 'right'].map((side) => (
            <div key={side} className={'side' + (guess ? (side === round.answer ? ' real' : ' fake') : '')}>
              {guess ? <div className="reveal-tag">{side === round.answer ? `REAL · ${round.real_uid}` : 'MODEL'}</div> : null}
              <button className="pick" disabled={!!guess} onClick={() => choose(side)}>
                {side === 'left' ? '← this one is real' : 'this one is real →'}
              </button>
            </div>
          ))}
        </div>

        {guess && (
          <div className="card verdict">
            <div className={'headline ' + (correct ? 'ok' : 'miss')}>{correct ? 'You spotted it.' : 'Fooled.'}</div>
            <div className="small">The real worm was on the <b>{round.answer}</b>. The other brain was generated by {index.model}, fitted on 18 other worms.</div>
            <div className="label" style={{ marginTop: 12 }}>How the model scores on the ruler</div>
            <div className="scorecard">
              {index.scorecard.map((r) => (
                <div key={r.metric} className="srow">
                  <span>{r.what}</span>
                  <span className={'vb ' + r.verdict.replace(' ', '-')}>{VERDICT[r.verdict]}</span>
                </div>
              ))}
            </div>
            <div className="small">
              {index.scorecard.filter((r) => r.verdict === 'inside').length} of {index.scorecard.length} levels as close to real worms as real worms are to each other.
              A classifier still tells this model apart from real worms (AUC {index.l8.model_auc}; two different real worms: {index.l8.real_auc}).
            </div>
            <div className="row" style={{ marginTop: 12 }}>
              <button className="play" onClick={() => setK((k + 1) % index.rounds.length)}>Next round</button>
            </div>
          </div>
        )}

        <footer className="which-footer">
          <div className="transport">
            <button className="play" onClick={() => setPlaying(!playing)}>{playing ? 'Pause' : 'Play'}</button>
            <span className="mono">{t.toFixed(0)} s / {(round.n_frames * round.dt).toFixed(0)} s · {SPEED}x</span>
            <span className="hint">{index.note} Brightness: activity per neuron class, scaled within each brain.</span>
          </div>
        </footer>
      </div>
    </>
  )
}
