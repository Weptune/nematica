import { useCallback, useEffect, useState } from 'react'
import { useLab } from './store'
import { loadIndex, loadReplay } from './replay'
import Scene from './Scene'
import Overlay from './Overlay'
import WhichReal from './WhichReal'
import Swarm from './Swarm'
import Poke from './Poke'

export default function App() {
  const query = new URLSearchParams(location.search)
  const mode = query.get('mode')
  const embed = query.get('embed') === '1'
  if (embed) return <Replay embed />
  const siteHref = import.meta.env.DEV ? 'http://localhost:8080/index.html' : '../index.html'
  return <>
    <a className="lab-exit" href={siteHref}>← Research site</a>
    {mode === 'which' ? <WhichReal /> : mode === 'swarm' ? <Swarm /> : mode === 'poke' ? <Poke /> : <Replay />}
  </>
}

function Replay({ embed = false }) {
  const replay = useLab((s) => s.replay)
  const setReplay = useLab((s) => s.setReplay)
  const [index, setIndex] = useState(null)
  const [error, setError] = useState(null)

  const pick = useCallback(async (uid, idx = index) => {
    const entry = idx.replays.find((r) => r.uid === uid) ?? idx.replays[0]
    try { setReplay(await loadReplay(entry.file)) } catch (e) { setError(String(e)) }
  }, [index, setReplay])

  useEffect(() => {
    loadIndex()
      .then((idx) => {
        setIndex(idx)
        const want = new URLSearchParams(location.search).get('uid')
        return pick(want ?? '2024-06-18-12', idx)
      })
      .catch((e) => setError(String(e)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const t = new URLSearchParams(location.search).get('t')
    if (replay && t) useLab.getState().setTime(parseFloat(t))
    const q = new URLSearchParams(location.search)
    if (replay) useLab.getState().setSpeed(1)   // real time: the worm crawls at its recorded pace
    if (replay && !t && replay.uid === '2024-06-18-12') useLab.getState().setTime(5)
    if (replay && q.get('paused')) useLab.getState().setPlaying(false)
    const want = q.get('neuron')
    if (replay && want) {
      const i = replay.neurons.findIndex((nr) => nr.name === want || nr.cls === want)
      if (i >= 0) useLab.getState().setSelected(i)
    }
  }, [replay, embed])

  useEffect(() => {
    if (!embed) return
    const onMessage = (event) => {
      if (event.origin !== location.origin || event.source !== window.parent || event.data?.type !== 'nematica-lab-play') return
      useLab.getState().setPlaying(Boolean(event.data.playing))
    }
    addEventListener('message', onMessage)
    return () => removeEventListener('message', onMessage)
  }, [embed])

  if (error) return <div className="splash"><div>Could not start: {error}<br />Export replays with <code>python scripts/export_replay.py</code>, then reload.</div></div>
  if (!replay || !index) return <div className="splash">Loading recording…</div>
  return (
    <>
      <Scene key={replay.uid} cinematic={embed} />
      {!embed && <Overlay index={index} onPick={(uid) => pick(uid)} />}
    </>
  )
}
