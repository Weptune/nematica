import { useCallback, useEffect, useState } from 'react'
import { useLab } from './store'
import { loadIndex, loadReplay } from './replay'
import Scene from './Scene'
import Overlay from './Overlay'
import WhichReal from './WhichReal'

export default function App() {
  if (new URLSearchParams(location.search).get('mode') === 'which') return <WhichReal />
  return <Replay />
}

function Replay() {
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
        return pick(want ?? idx.replays[0].uid, idx)
      })
      .catch((e) => setError(String(e)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const t = new URLSearchParams(location.search).get('t')
    if (replay && t) useLab.getState().setTime(parseFloat(t))
    const q = new URLSearchParams(location.search)
    if (replay && q.get('paused')) useLab.getState().setPlaying(false)
    const want = q.get('neuron')
    if (replay && want) {
      const i = replay.neurons.findIndex((nr) => nr.name === want || nr.cls === want)
      if (i >= 0) useLab.getState().setSelected(i)
    }
  }, [replay])

  if (error) return <div className="splash"><div>Could not start: {error}<br />Export replays with <code>python scripts/export_replay.py</code>, then reload.</div></div>
  if (!replay || !index) return <div className="splash">Loading recording…</div>
  return (
    <>
      <Scene key={replay.uid} />
      <Overlay index={index} onPick={(uid) => pick(uid)} />
    </>
  )
}
