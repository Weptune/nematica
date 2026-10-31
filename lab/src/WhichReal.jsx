import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { EffectComposer, Bloom, Vignette, Noise } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import { useLab } from './store'
import { loadReplay, frameAt } from './replay'
import { createBodyState } from './body'
import { Clock, FollowHead } from './Scene'
import Worm from './Worm'
import Neurons from './Neurons'
import Arena from './Arena'

// "Which one is real?": two whole worms crawling side by side. One is a recording of a real
// held-out worm; the other's brain and behaviour come from a model, with body shapes borrowed
// from real training worms. Under each, the key command neurons and the reversal state.

const BASE = (new URLSearchParams(location.search).get('set') || 'which2') + '/'
const WINDOW_S = 90
const VERDICT = { inside: 'inside', 'too typical': 'too typical', outside: 'outside', 'not scored': 'n/a' }

function WormView({ replay, drivesClock }) {
  const body = useMemo(() => createBodyState(replay.k), [replay])
  return (
    <Canvas dpr={[1, 2]} camera={{ fov: 32, near: 0.005, far: 100, position: [0.3, 0.8, 0.6] }}
            gl={{ antialias: false, powerPreference: 'high-performance', preserveDrawingBuffer: true }}>
      <color attach="background" args={['#020509']} />
      {drivesClock && <Clock />}
      <Arena replay={replay} />
      <Worm body={body} replay={replay} />
      <Neurons body={body} replay={replay} />
      <FollowHead body={body} zoom={replay?.arena ? 3.4 : 2.1} />
      <EffectComposer multisampling={4}>
        <Bloom mipmapBlur intensity={1.1} luminanceThreshold={0.6} luminanceSmoothing={0.25} radius={0.65} />
        <Noise premultiply blendFunction={BlendFunction.ADD} opacity={0.1} />
        <Vignette eskil={false} offset={0.25} darkness={0.85} />
      </EffectComposer>
    </Canvas>
  )
}

// Rolling traces of the key neuron classes and the reversal state, ending at the current time.
function TraceStrip({ replay, keys }) {
  const ref = useRef()
  const rows = useMemo(() => keys
    .map((c) => ({ cls: c, nr: replay.neurons.find((n) => n.cls === c) }))
    .filter((r) => r.nr), [replay, keys])
  useEffect(() => {
    let raf
    const draw = () => {
      const cv = ref.current
      if (cv) {
        const dpr = window.devicePixelRatio || 1
        const W = cv.clientWidth, H = cv.clientHeight
        if (cv.width !== W * dpr) { cv.width = W * dpr; cv.height = H * dpr }
        const g = cv.getContext('2d')
        g.setTransform(dpr, 0, 0, dpr, 0, 0)
        g.clearRect(0, 0, W, H)
        const time = useLab.getState().time
        const t0 = Math.max(0, time - WINDOW_S)
        const x = (tt) => 46 + ((tt - t0) / WINDOW_S) * (W - 52)
        const rowH = (H - 14) / (rows.length + 1)
        const f0 = frameAt(replay, t0).i, f1 = frameAt(replay, time).i
        // reversal state band
        g.fillStyle = 'rgba(255,154,92,0.16)'
        for (let i = f0; i <= f1; i++) if (replay.reversing[i]) g.fillRect(x(replay.t[i]), 0, Math.max(1.5, x(replay.t[i + 1] ?? replay.t[i]) - x(replay.t[i])), H - 14)
        g.font = '10px "IBM Plex Mono", monospace'
        rows.forEach((r, k) => {
          const y0 = 4 + k * rowH, h = rowH - 4
          g.fillStyle = '#7d93a0'
          g.fillText(r.cls, 4, y0 + h * 0.7)
          g.strokeStyle = '#5dff8a'
          g.globalAlpha = 0.9
          g.lineWidth = 1.2
          g.beginPath()
          for (let i = f0; i <= f1; i++) {
            const yy = y0 + h * (1 - r.nr.level[i])
            if (i === f0) g.moveTo(x(replay.t[i]), yy); else g.lineTo(x(replay.t[i]), yy)
          }
          g.stroke()
          g.globalAlpha = 1
        })
        const yb = 4 + rows.length * rowH
        g.fillStyle = '#7d93a0'
        g.fillText('state', 4, yb + rowH * 0.6)
        for (let i = f0; i <= f1; i++) {
          g.fillStyle = replay.reversing[i] ? '#ff9a5c' : 'rgba(93,255,138,0.45)'
          g.fillRect(x(replay.t[i]), yb + 3, Math.max(1.5, x(replay.t[i + 1] ?? replay.t[i]) - x(replay.t[i])), rowH - 8)
        }
        g.fillStyle = '#7d93a0'
        g.fillText(`last ${WINDOW_S} s`, W - 70, H - 2)
      }
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [replay, rows])
  return <canvas ref={ref} className="strip" />
}

export default function WhichReal() {
  const [index, setIndex] = useState(null)
  const [k, setK] = useState(0)
  const [pair, setPair] = useState(null)
  const [guess, setGuess] = useState(null)
  const [score, setScore] = useState({ right: 0, played: 0 })
  const [error, setError] = useState(null)
  const playing = useLab((s) => s.playing)
  const speed = useLab((s) => s.speed)

  useEffect(() => {
    fetch('./data/' + BASE + 'index.json').then((r) => r.json()).then(setIndex).catch((e) => setError(String(e)))
    useLab.getState().setSpeed(4)
  }, [])
  useEffect(() => {
    if (!index) return
    setPair(null)
    setGuess(null)
    const r = index.rounds[k]
    Promise.all([loadReplay(BASE + r.left), loadReplay(BASE + r.right)]).then(([left, right]) => {
      useLab.getState().setReplay(left)            // drives the shared clock (same duration)
      setPair({ left, right, round: r })
    }).catch((e) => setError(String(e)))
  }, [index, k])

  const choose = (side) => {
    if (guess) return
    setGuess(side)
    setScore((s) => ({ right: s.right + (side === pair.round.answer ? 1 : 0), played: s.played + 1 }))
  }

  if (error) return <div className="splash"><div>Could not load the rounds: {error}<br />Run <code>python scripts/export_virtual_worms.py</code>, then reload.</div></div>
  if (!index || !pair) return <div className="splash">Loading worms…</div>
  const answer = pair.round.answer
  const correct = guess && guess === answer

  return (
    <div className="which2">
      <div className="halves">
        {['left', 'right'].map((side) => (
          <div key={side + k} className={'half' + (guess ? (side === answer ? ' real' : ' fake') : '')}>
            <div className="view"><WormView replay={pair[side]} drivesClock={side === 'left'} /></div>
            <TraceStrip replay={pair[side]} keys={index.key_neurons} />
            <div className="pickrow">
              {guess
                ? <div className="reveal-tag">{side === answer ? `REAL · ${pair.round.real_uid}` : 'MODEL'}</div>
                : <button className="pick" onClick={() => choose(side)}>{side === 'left' ? '← this one is real' : 'this one is real →'}</button>}
            </div>
          </div>
        ))}
      </div>

      <header className="which-head">
        <div className="brand">NEMATICA</div>
        <div className="title">Which one is real?</div>
        <div className="subtitle">{index?.rounds?.length && BASE === 'which3/'
          ? "Two worms crawling inside a copper ring, which worms avoid. One is a recording of a real worm. The other one's brain is a model that senses the copper and decides when to reverse and where to steer; only its body shapes are borrowed from real worms. Watch how the neurons under each worm line up with its reversals (orange)."
          : "Two worms crawling on agar. One is a recording of a real worm. The other one's brain activity, speed and reversals come from a model; its body shapes are borrowed from other real worms. Watch how the neurons under each worm line up with its reversals (orange)."}</div>
      </header>
      <div className="tally mono">round {k + 1} / {index.rounds.length} · score {score.right} / {score.played}</div>
      <div className="controls">
        <button className="play" onClick={() => useLab.getState().setPlaying(!playing)}>{playing ? 'Pause' : 'Play'}</button>
        <div className="seg">{[1, 2, 4, 8].map((v) => (
          <button key={v} className={speed === v ? 'on' : ''} onClick={() => useLab.getState().setSpeed(v)}>{v}×</button>))}
        </div>
      </div>

      {guess && (
        <div className="card verdict">
          <div className={'headline ' + (correct ? 'ok' : 'miss')}>{correct ? 'You spotted it.' : 'Fooled.'}</div>
          <div className="small">The real worm was on the <b>{answer}</b>. The other was generated by {index.model}, fitted on 18 other worms.</div>
          <div className="label" style={{ marginTop: 12 }}>The model's brain on the ruler</div>
          <div className="scorecard">
            {index.scorecard.map((r) => (
              <div key={r.metric} className="srow"><span>{r.what}</span><span className={'vb ' + r.verdict.replace(' ', '-')}>{VERDICT[r.verdict]}</span></div>
            ))}
          </div>
          <div className="small">A classifier still tells this model's brain apart from real ones (AUC {index.l8.model_auc}; two different real worms: {index.l8.real_auc}).</div>
          <div className="small muted">{index.note}</div>
          <div className="row" style={{ marginTop: 12 }}><button className="play" onClick={() => setK((k + 1) % index.rounds.length)}>Next round</button></div>
        </div>
      )}
    </div>
  )
}
