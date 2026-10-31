import { useEffect, useRef, useState } from 'react'

// Arc 6: 32 model worms in one copper arena, seen from above. Each worm's brain is its own
// closed-loop model (v11) fitted on a different real worm; bodies are motion-matched from
// real worms. Orange = reversing; a white ring marks a head touching another worm.
// Data: lab/public/data/swarm1/swarm.json (python scripts/export_swarm.py).

const SPEEDS = [4, 8, 16, 32]

function bodyPoints(w, f, P, seg) {
  let x = w.head[2 * f], y = w.head[2 * f + 1]
  const pts = [[x, y]]
  for (let p = 0; p < P; p++) {
    const a = w.angles[f * P + p]
    x += seg * Math.cos(a); y += seg * Math.sin(a)
    pts.push([x, y])
  }
  return pts
}

export default function Swarm() {
  const ref = useRef()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [playing, setPlaying] = useState(true)
  const [speed, setSpeed] = useState(8)
  const [frame, setFrame] = useState(0)
  const [picked, setPicked] = useState(null)
  const st = useRef({ t: 0, last: null })

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/swarm1/swarm.json`).then((r) => {
      if (!r.ok) throw new Error(r.status + ' ' + r.statusText)
      return r.json()
    }).then(setData).catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    if (!data) return
    let raf
    const P = data.points, seg = data.length_mm / P, R = data.radius_mm
    const draw = (now) => {
      const s = st.current
      if (s.last != null && playing) s.t = (s.t + ((now - s.last) / 1000) * speed) % (data.frames * data.dt)
      s.last = now
      const f = Math.min(data.frames - 1, Math.floor(s.t / data.dt))
      const cv = ref.current
      if (cv) {
        const dpr = window.devicePixelRatio || 1
        const W = cv.clientWidth, H = cv.clientHeight
        if (cv.width !== Math.round(W * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr) }
        const g = cv.getContext('2d')
        g.setTransform(dpr, 0, 0, dpr, 0, 0)
        g.clearRect(0, 0, W, H)
        const sc = (Math.min(W, H) * 0.46) / (R + 1.9)
        const cx = W / 2, cy = H / 2
        const X = (p) => cx + p[0] * sc, Y = (p) => cy - p[1] * sc
        // copper beyond the ring
        g.fillStyle = 'rgba(184, 115, 51, 0.16)'
        g.beginPath(); g.arc(cx, cy, (R + 1.9) * sc, 0, 2 * Math.PI); g.arc(cx, cy, R * sc, 0, 2 * Math.PI, true); g.fill()
        g.strokeStyle = 'rgba(214, 140, 70, 0.75)'
        g.lineWidth = 1.5
        g.beginPath(); g.arc(cx, cy, R * sc, 0, 2 * Math.PI); g.stroke()
        // worms
        g.lineCap = 'round'; g.lineJoin = 'round'
        data.worms.forEach((w, j) => {
          const pts = bodyPoints(w, f, P, seg)
          const rev = w.reversing[f], touch = w.touch[f]
          const dim = picked !== null && picked !== j
          g.globalAlpha = dim ? 0.28 : 1
          g.strokeStyle = rev ? '#ff9a5c' : '#5dff8a'
          g.lineWidth = Math.max(2, 0.06 * sc)
          g.beginPath()
          pts.forEach((p, i) => (i ? g.lineTo(X(p), Y(p)) : g.moveTo(X(p), Y(p))))
          g.stroke()
          g.fillStyle = '#eafff1'
          g.beginPath(); g.arc(X(pts[0]), Y(pts[0]), Math.max(2.2, 0.045 * sc), 0, 2 * Math.PI); g.fill()
          if (touch) {
            g.strokeStyle = 'rgba(255,255,255,0.85)'
            g.lineWidth = 1.2
            g.beginPath(); g.arc(X(pts[0]), Y(pts[0]), Math.max(7, 0.16 * sc), 0, 2 * Math.PI); g.stroke()
          }
          if (picked === j) {
            g.strokeStyle = 'rgba(160, 200, 255, 0.9)'
            g.lineWidth = 1
            g.beginPath(); g.arc(X(pts[0]), Y(pts[0]), Math.max(12, 0.3 * sc), 0, 2 * Math.PI); g.stroke()
          }
        })
        g.globalAlpha = 1
        // scale bar: 1 mm
        g.strokeStyle = '#7d93a0'; g.lineWidth = 1
        g.beginPath(); g.moveTo(24, H - 28); g.lineTo(24 + sc, H - 28); g.stroke()
        g.fillStyle = '#7d93a0'; g.font = '11px "IBM Plex Mono", monospace'
        g.fillText('1 mm', 24, H - 34)
      }
      setFrame((old) => (old === f ? old : f))
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [data, playing, speed, picked])

  const onClick = (e) => {
    if (!data) return
    const cv = ref.current, rect = cv.getBoundingClientRect()
    const W = cv.clientWidth, H = cv.clientHeight
    const sc = (Math.min(W, H) * 0.46) / (data.radius_mm + 1.9)
    const mx = (e.clientX - rect.left - W / 2) / sc, my = -(e.clientY - rect.top - H / 2) / sc
    let best = null, bd = 0.4
    data.worms.forEach((w, j) => {
      const d = Math.hypot(w.head[2 * frame] - mx, w.head[2 * frame + 1] - my)
      if (d < bd) { bd = d; best = j }
    })
    setPicked(best)
  }

  if (error) return <div className="splash"><div>Could not load the swarm: {error}<br />Run <code>python scripts/export_swarm.py</code>, then reload.</div></div>
  if (!data) return <div className="splash">Loading swarm…</div>
  const n = data.worms.length
  const rev = data.worms.filter((w) => w.reversing[frame]).length
  const touch = data.worms.filter((w) => w.touch[frame]).length
  const onCu = data.worms.filter((w) => Math.hypot(w.head[2 * frame], w.head[2 * frame + 1]) > data.radius_mm).length
  const s = data.notes.summary
  const t = frame * data.dt
  const pw = picked !== null ? data.worms[picked] : null

  return (
    <div className="swarm">
      <canvas ref={ref} className="swarm-canvas" onClick={onClick} aria-label="Top view of the simulated swarm in the copper arena" />
      <header>
        <div className="brand">NEMATICA</div>
        <div className="subtitle">Arc 6 · a swarm of {n} model brains in one copper arena</div>
      </header>
      <div className="panel right">
        <div className="card">
          <div className="label">What you are seeing</div>
          <div className="small">Each worm's brain is a closed-loop model fitted on one real worm (16 worms, two copies each). It senses the copper ring and decides when to reverse; bodies are borrowed from real worms. Green crawls forward, orange reverses, a white ring is a head touching another worm. Touch and crowding rules are assumptions until real multi-worm data can test them.</div>
          <div className="small muted">Honest caveat: these model worms step onto the copper (shaded) far more often than real worms, which mostly turn back at the line. That is the closed loop's main remaining miss (arc 5).</div>
        </div>
        <div className="card mono">
          <div className="label">Now · {Math.floor(t / 60)}:{String(Math.floor(t % 60)).padStart(2, '0')} of {Math.round(data.frames * data.dt / 60)} min</div>
          <div className="row small"><span>reversing</span><span>{rev} / {n}</span></div>
          <div className="row small"><span>touching another worm</span><span>{touch} / {n}</span></div>
          <div className="row small"><span>head on the copper</span><span>{onCu} / {n}</span></div>
        </div>
        <div className="card mono">
          <div className="label">Whole run</div>
          <div className="row small"><span>time in contact</span><span>{(100 * s.contact).toFixed(1)}%</span></div>
          <div className="row small"><span>worms in a cluster</span><span>{(100 * s.frac_in_cluster).toFixed(0)}%</span></div>
          <div className="row small"><span>near copper</span><span>{(100 * s.near_copper).toFixed(0)}%</span></div>
          <div className="row small"><span>reversals / min, 0 · 1 · 2+ nbrs</span><span>{s.rev_per_min_density_0.toFixed(1)} · {s.rev_per_min_density_1.toFixed(1)} · {s['rev_per_min_density_2+'].toFixed(1)}</span></div>
        </div>
        <div className="card">
          <div className="label">Selected worm</div>
          <div className="small">{pw ? <>model of real worm <span className="mono">{pw.origin}</span>. <button className="linkish" onClick={() => setPicked(null)}>Clear</button></> : 'Click a worm to follow it.'}</div>
        </div>
      </div>
      <div className="controls">
        <button className="play" onClick={() => setPlaying(!playing)}>{playing ? 'Pause' : 'Play'}</button>
        <div className="seg">{SPEEDS.map((v) => (
          <button key={v} className={speed === v ? 'on' : ''} onClick={() => setSpeed(v)}>{v}×</button>))}
        </div>
        <input type="range" min={0} max={data.frames - 1} value={frame} aria-label="Time"
               onChange={(e) => { st.current.t = Number(e.target.value) * data.dt; setFrame(Number(e.target.value)) }} />
      </div>
    </div>
  )
}
