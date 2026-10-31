import { useEffect, useMemo, useRef, useState } from 'react'

// "Poke it yourself": switch on one neuron class in a real worm brain and in artificial ones,
// and watch the echo spread. Real echoes come from the optogenetic atlas (Randi et al. 2023);
// artificial brains were fitted on other worms and stimulated at the same moments.
// Data: lab/public/data/poke1/poke.json (python scripts/export_poke.py).

const NAMES = {
  'Real worm': 'Real worm',
  var3_spontaneous: 'Artificial brain, learned from rest',
  var3_stim: 'Artificial brain, learned from pokes',
  creamer2024_fully_connected: 'Published atlas model',
  creamer2024_connectome_constrained: 'Published model, wiring-constrained',
}
const SPEEDS = [1, 2, 4]

function colorFor(v, a = 1) {
  return v >= 0 ? `rgba(93,255,138,${a})` : `rgba(255,154,92,${a})`
}

function Panel({ title, echo, stim, pos, bounds, t, threshold, highlight }) {
  const ref = useRef()
  const heatRef = useRef()
  useEffect(() => {
    const draw = (cv, fn) => {
      if (!cv) return
      const dpr = window.devicePixelRatio || 1
      const W = cv.clientWidth, H = cv.clientHeight
      if (cv.width !== Math.round(W * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr) }
      const g = cv.getContext('2d')
      g.setTransform(dpr, 0, 0, dpr, 0, 0)
      g.clearRect(0, 0, W, H)
      fn(g, W, H)
    }
    draw(ref.current, (g, W, H) => {
      const [x0, x1, y0, y1] = bounds
      const X = (x) => 24 + ((x - x0) / (x1 - x0 || 1)) * (W - 48)
      // schematic side view: anterior to the left, vertical spread stretched to fill the panel
      const Y = (y) => 28 + ((y1 - y) / ((y1 - y0) || 1)) * (H - 56)
      // all classes faintly
      Object.entries(pos).forEach(([c, p]) => {
        g.fillStyle = 'rgba(160,200,220,0.13)'
        g.beginPath(); g.arc(X(p[0]), Y(p[1]), 3, 0, 2 * Math.PI); g.fill()
      })
      if (!echo) return
      const f = Math.min(echo.R[0].length - 1, Math.floor(t))
      echo.classes.forEach((c, i) => {
        const p = pos[c]
        if (!p) return
        const v = echo.R[i][f]
        const a = Math.min(1, Math.abs(v) / threshold)
        const sig = Math.abs(v) > threshold
        const r = 3 + 7 * a + (sig ? 3 : 0)
        g.fillStyle = colorFor(v, 0.15 + 0.85 * a)
        if (sig) { g.shadowColor = colorFor(v, 1); g.shadowBlur = 14 }
        g.beginPath(); g.arc(X(p[0]), Y(p[1]), r, 0, 2 * Math.PI); g.fill()
        g.shadowBlur = 0
        if (sig || c === highlight) {
          g.fillStyle = 'rgba(220,235,240,0.85)'
          g.font = '10px "IBM Plex Mono", monospace'
          g.fillText(c, X(p[0]) + r + 2, Y(p[1]) - r)
        }
      })
      const sp = pos[stim]
      if (sp) {
        const pulse = t < 2 ? 1 : Math.max(0, 1 - (t - 2) / 8)
        g.strokeStyle = `rgba(255,255,255,${0.35 + 0.65 * pulse})`
        g.lineWidth = 2
        g.beginPath(); g.arc(X(sp[0]), Y(sp[1]), 14 + 6 * pulse, 0, 2 * Math.PI); g.stroke()
        g.fillStyle = 'rgba(255,255,255,0.9)'
        g.font = '11px "IBM Plex Mono", monospace'
        g.fillText(stim + ' (stimulated)', X(sp[0]) - 30, Y(sp[1]) + 30)
      }
    })
    draw(heatRef.current, (g, W, H) => {
      if (!echo) return
      const n = echo.classes.length, T = echo.R[0].length
      const order = echo.classes.map((_, i) => i).sort((a, b) =>
        Math.max(...echo.R[b].map(Math.abs)) - Math.max(...echo.R[a].map(Math.abs)))
      const cw = W / T, ch = H / n
      order.forEach((i, row) => {
        echo.R[i].forEach((v, j) => {
          if (Math.abs(v) < 1.5) return
          g.fillStyle = colorFor(v, Math.min(1, 0.2 + 0.8 * (Math.abs(v) - 1.5) / 4))
          g.fillRect(j * cw, row * ch, Math.max(1, cw - 0.5), Math.max(1, ch - 0.3))
        })
      })
      g.fillStyle = 'rgba(255,255,255,0.8)'
      g.fillRect((t / T) * W, 0, 1.5, H)
    })
  }, [echo, stim, pos, bounds, t, threshold, highlight])

  const live = echo ? echo.R.filter((r) => Math.abs(r[Math.min(r.length - 1, Math.floor(t))]) > threshold).length : 0
  return (
    <div className="poke-panel">
      <div className="row"><div className="poke-title">{title}</div>
        {echo && <div className="mono small">{live} / {echo.classes.length} answering now</div>}</div>
      <canvas ref={ref} className="poke-map" aria-label={`${title}: map of neuron classes lighting up`} />
      <canvas ref={heatRef} className="poke-heat" aria-label={`${title}: response of each class over 30 seconds`} />
      {echo
        ? <div className="mono small muted">whole echo: {(100 * echo.spread).toFixed(1)}% of the brain over 30 s · complexity {echo.pci.toFixed(2)}</div>
        : <div className="small muted">This brain has no matching stimulation.</div>}
    </div>
  )
}

export default function Poke() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [k, setK] = useState(0)
  const [t, setT] = useState(0)
  const [playing, setPlaying] = useState(true)
  const [speed, setSpeed] = useState(2)
  const st = useRef({ last: null, t: 0 })

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/poke1/poke.json`).then((r) => {
      if (!r.ok) throw new Error(r.status + ' ' + r.statusText)
      return r.json()
    }).then(setData).catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    let raf
    const T = data ? data.events[0].echoes[0].R[0].length : 61
    const tick = (now) => {
      const s = st.current
      if (s.last != null && playing) s.t = Math.min(T - 1, s.t + ((now - s.last) / 1000) * speed / (data?.dt || 0.5))
      s.last = now
      setT(s.t)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [data, playing, speed])

  const ev = data?.events[k]
  const used = useMemo(() => {
    if (!data) return null
    const cs = new Set()
    data.events.forEach((e) => e.echoes.forEach((x) => x && x.classes.forEach((c) => cs.add(c))))
    data.events.forEach((e) => cs.add(e.stim))
    const pos = Object.fromEntries([...cs].filter((c) => data.positions[c]).map((c) => [c, data.positions[c]]))
    const P = Object.values(pos)
    const xs = P.map((p) => p[0]), ys = P.map((p) => p[1])
    return { pos, bounds: [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)] }
  }, [data])

  if (error) return <div className="splash"><div>Could not load the echoes: {error}<br />Run <code>python scripts/export_poke.py</code>, then reload.</div></div>
  if (!data || !ev) return <div className="splash">Loading brains…</div>
  const choose = (i) => { setK(i); st.current.t = 0; setT(0); setPlaying(true) }

  return (
    <div className="poke">
      <header className="poke-head">
        <div className="brand">NEMATICA</div>
        <div className="title">Poke it yourself</div>
        <div className="subtitle">Pick a neuron. A pulse of light switches it on in a real worm's brain (recorded by Randi et al. 2023), and the same pulse is given to two artificial brains trained on other worms. Watch where the echo goes: green rises, orange falls, bright dots are clear responses. Real brains answer sparsely and specifically; see whether the artificial ones do.</div>
      </header>
      <div className="poke-body">
        <nav className="poke-list" aria-label="Neuron to stimulate">
          {data.events.map((e, i) => (
            <button key={e.stim + i} className={'poke-btn' + (i === k ? ' on' : '')} onClick={() => choose(i)}>
              <span className="mono">{e.stim}</span><span className="small muted">{data.labels[e.stim] || ''}</span>
            </button>
          ))}
        </nav>
        <div className="poke-panels">
          {data.brains.map((b, i) => (
            <Panel key={b} title={NAMES[b] || b} echo={ev.echoes[i]} stim={ev.stim} pos={used.pos}
                   bounds={used.bounds} t={t} threshold={data.threshold} highlight={ev.stim} />
          ))}
        </div>
      </div>
      <div className="controls poke-controls">
        <button className="play" onClick={() => { if (t >= 59) st.current.t = 0; setPlaying(!playing) }}>{playing ? 'Pause' : 'Play'}</button>
        <div className="seg">{SPEEDS.map((v) => (
          <button key={v} className={speed === v ? 'on' : ''} onClick={() => setSpeed(v)}>{v}×</button>))}
        </div>
        <input type="range" min={0} max={60} step={0.5} value={t} aria-label="Seconds after the pulse, in frames"
               onChange={(e) => { st.current.t = Number(e.target.value); setT(Number(e.target.value)) }} />
        <span className="mono small">{(t * data.dt).toFixed(1)} s after the pulse</span>
      </div>
      <div className="small muted poke-note">Worm {data.worm}, a held-out worm neither model was trained on. Positions are approximate (Skuhersky et al. 2022 atlas, left and right members averaged). Each brain is one noisy trial, as in the real experiment.</div>
    </div>
  )
}
