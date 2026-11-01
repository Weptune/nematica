import { useEffect, useRef } from 'react'
import { useLab } from './store'
import { formatTime, frameAt, sampleSeries } from './replay'

function Sparkline({ level, t, time, width = 260, height = 56 }) {
  const ref = useRef()
  useEffect(() => {
    const c = ref.current, ctx = c.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    c.width = width * dpr; c.height = height * dpr
    ctx.scale(dpr, dpr)
    ctx.clearRect(0, 0, width, height)
    const dur = t[t.length - 1]
    ctx.strokeStyle = 'rgba(93,255,138,0.85)'; ctx.lineWidth = 1
    ctx.beginPath()
    for (let i = 0; i < level.length; i += 2) {
      const x = (t[i] / dur) * width, y = height - 4 - level[i] * (height - 8)
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
    }
    ctx.stroke()
    const x = (time / dur) * width
    ctx.strokeStyle = 'rgba(255,255,255,0.55)'
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke()
  }, [level, t, time, width, height])
  return <canvas ref={ref} style={{ width, height, display: 'block' }} />
}

function NeuronCard({ index, pinned }) {
  const replay = useLab((s) => s.replay)
  const time = useLab((s) => s.time)
  const nr = replay.neurons[index]
  const fr = frameAt(replay, time)
  return (
    <div className="card neuron">
      <div className="row">
        <span className="name">{nr.name}</span>
        <span className="muted small">class {nr.cls} · ID {nr.conf}/5{pinned ? ' · pinned' : ''}</span>
      </div>
      <Sparkline level={nr.level} t={replay.t} time={Math.round(time)} />
      <div className="row small">
        <span>activity now {(sampleSeries(nr.level, fr) * 100).toFixed(0)}% of range</span>
        <span className="tag">M</span>
      </div>
    </div>
  )
}

export default function Overlay({ index, onPick }) {
  const replay = useLab((s) => s.replay)
  const { playing, speed, time, hovered, selected, mode } = useLab()
  const { setPlaying, setSpeed, setTime, setMode } = useLab.getState()
  const fr = frameAt(replay, time)
  const v = sampleSeries(replay.velocity, fr)
  const rev = replay.reversing[Math.round(fr.i + fr.a)] === 1
  const shown = hovered ?? selected

  return (
    <div className="overlay">
      <header>
        <div className="brand">NEMATICA <span className="muted">· lab</span></div>
        <div className="subtitle">
          Real worm {replay.uid} · copper-boundary test set · whole-brain NLS-GCaMP7f
        </div>
      </header>

      <div className="panel right">
        <div className="card">
          <div className="label">Recording</div>
          <select value={replay.uid} onChange={(e) => onPick(e.target.value)}>
            {index.replays.map((r) => (
              <option key={r.uid} value={r.uid}>{r.uid} · {r.neurons} neurons</option>
            ))}
          </select>
          <div className="row small muted"><span>source: real recording, held-out test worm</span><span className="tag">M</span></div>
        </div>
        <div className="card">
          <div className="label">Behaviour</div>
          <div className="metric">
            <span className={rev ? 'badge rev' : 'badge fwd'}>{rev ? 'REVERSING' : 'FORWARD'}</span>
            <span className="mono">{(v * 1000).toFixed(0)} µm/s</span>
          </div>
          <div className="row small muted"><span>tracked velocity</span><span className="tag">M</span></div>
        </div>
        <div className="card">
          <div className="label">Display</div>
          <div className="seg">
            <button className={mode === 'gcamp' ? 'on' : ''} onClick={() => setMode('gcamp')}>GCaMP</button>
            <button className={mode === 'identity' ? 'on' : ''} onClick={() => setMode('identity')}>Identity</button>
          </div>
          <div className="small muted">{mode === 'gcamp'
            ? 'brightness = recorded activity'
            : 'one colour per neuron class (display only, not NeuroPAL colours)'}</div>
        </div>
        {shown != null && <NeuronCard index={shown} pinned={selected === shown} />}
        {shown == null && <div className="hint">The cyan line is the worm’s recent tracked path. Hover a neuron to see its trace. Drag to orbit, scroll to zoom.</div>}
      </div>

      <footer>
        <div className="transport">
          <button className="play" onClick={() => setPlaying(!playing)}>{playing ? 'Pause' : 'Play'}</button>
          <input
            type="range" min={0} max={replay.duration} step={0.1} value={time}
            onChange={(e) => setTime(parseFloat(e.target.value))}
          />
          <span className="mono">{formatTime(time)} / {formatTime(replay.duration)}</span>
          <div className="seg">
            {[0.5, 1, 2, 4, 8].map((s) => (
              <button key={s} className={speed === s ? 'on' : ''} onClick={() => setSpeed(s)}>{s}×</button>
            ))}
          </div>
        </div>
        <div className="provenance">
          <span><b>M</b> measured: activity, posture, path, copper boundary</span>
          <span><b>I</b> inferred: neuron positions from an atlas (Skuhersky et al. 2022), not this worm's own</span>
          <span><b>A</b> assumed: body width profile, interpolation between 1.67 Hz frames, glow mapping, agar texture</span>
        </div>
      </footer>
    </div>
  )
}
