import { create } from 'zustand'

// UI state only. High-rate simulation state lives in refs and typed arrays.
export const useLab = create((set) => ({
  replay: null,          // parsed bundle (see replay.js)
  playing: true,
  speed: 1,
  time: 0,               // seconds into the recording
  hovered: null,         // neuron index under the pointer
  selected: null,        // neuron index clicked
  mode: 'gcamp',         // 'gcamp' | 'identity'
  setReplay: (replay) => set({ replay, time: 0, hovered: null, selected: null }),
  setPlaying: (playing) => set({ playing }),
  setSpeed: (speed) => set({ speed }),
  setTime: (time) => set({ time }),
  setHovered: (hovered) => set({ hovered }),
  setSelected: (selected) => set({ selected }),
  setMode: (mode) => set({ mode }),
}))
