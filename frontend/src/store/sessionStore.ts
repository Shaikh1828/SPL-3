import { create } from 'zustand'
import type { Session, Tournament } from '@/types'

interface SessionState {
  activeTournament: Tournament | null
  activeSession: Session | null
  currentEnd: number
  setActiveTournament: (t: Tournament | null) => void
  setActiveSession: (s: Session | null) => void
  setCurrentEnd: (end: number) => void
  clear: () => void
}

export const useSessionStore = create<SessionState>()((set) => ({
  activeTournament: null,
  activeSession: null,
  currentEnd: 1,

  setActiveTournament: (t) => set({ activeTournament: t }),
  setActiveSession: (s) => set({ activeSession: s }),
  setCurrentEnd: (end) => set({ currentEnd: end }),
  clear: () => set({ activeTournament: null, activeSession: null, currentEnd: 1 }),
}))
