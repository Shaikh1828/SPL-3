import { useState } from 'react'
import { Target, Users, Play, CheckCircle, X, Clock, Layers, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { Session, Tournament } from '@/types'
import { useSessionStore } from '@/store/sessionStore'

interface SessionsModalProps {
  isOpen: boolean
  onClose: () => void
  sessions: Session[]
  tournaments: Tournament[]
  onSelectSession?: (session: Session) => void
}

export function SessionsModal({ isOpen, onClose, sessions, tournaments, onSelectSession }: SessionsModalProps) {
  const navigate = useNavigate()
  const { activeSession, setActiveSession, setActiveTournament } = useSessionStore()
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all')

  if (!isOpen) return null

  const filteredSessions = sessions.filter(s => {
    if (filter === 'active') return s.status === 'active'
    if (filter === 'completed') return s.status === 'completed'
    return true
  })

  const getTournamentName = (tId: number) => {
    const t = tournaments.find(item => item.id === tId)
    return t ? t.name : `Tournament #${tId}`
  }

  const handleLaunchScoring = (session: Session) => {
    setActiveSession(session)
    const t = tournaments.find(item => item.id === session.tournament_id)
    if (t) setActiveTournament(t)
    if (onSelectSession) onSelectSession(session)
    onClose()
    navigate('/scoring')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="glass-card w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl border border-navy-700/80 overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-navy-700 bg-navy-900/60">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Target className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">Tournament Sessions & Rounds</h2>
              <p className="text-xs text-slate-400">Ongoing active rounds and scheduled sessions</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-navy-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filter Tabs */}
        <div className="px-6 py-3 border-b border-navy-800 bg-navy-900/30 flex items-center gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
              filter === 'all'
                ? 'bg-emerald-500 text-navy-950 font-bold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-navy-800'
            }`}
          >
            All Sessions ({sessions.length})
          </button>
          <button
            onClick={() => setFilter('active')}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center gap-1.5 ${
              filter === 'active'
                ? 'bg-emerald-500 text-navy-950 font-bold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-navy-800'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Ongoing Active ({sessions.filter(s => s.status === 'active').length})
          </button>
          <button
            onClick={() => setFilter('completed')}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
              filter === 'completed'
                ? 'bg-emerald-500 text-navy-950 font-bold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-navy-800'
            }`}
          >
            Completed ({sessions.filter(s => s.status === 'completed').length})
          </button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {filteredSessions.length > 0 ? (
            filteredSessions.map((s) => {
              const isSelected = activeSession?.id === s.id
              const isLive = s.status === 'active'

              return (
                <div
                  key={s.id}
                  className={`p-4 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                    isSelected
                      ? 'bg-emerald-500/10 border-emerald-500/40 shadow-lg shadow-emerald-500/5'
                      : 'bg-navy-800/40 hover:bg-navy-800/70 border-navy-700/50 hover:border-emerald-500/30'
                  }`}
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                        {s.name}
                        {isSelected && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500 text-navy-950">
                            Current Active
                          </span>
                        )}
                      </h3>
                      {isLive ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          Live Shooting
                        </span>
                      ) : s.status === 'completed' ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20 flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" />
                          Completed
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          Pending Start
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 font-medium">
                      {getTournamentName(s.tournament_id)}
                    </p>
                    <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap">
                      <span className="flex items-center gap-1">
                        <Layers className="w-3.5 h-3.5 text-slate-400" />
                        {s.num_lanes || 4} Competition Lanes
                      </span>
                      <span className="flex items-center gap-1">
                        <Sparkles className="w-3.5 h-3.5 text-slate-400" />
                        {s.arrows_per_round || 3} arrows / end
                      </span>
                      {s.archers_count !== undefined && (
                        <span className="flex items-center gap-1">
                          <Users className="w-3.5 h-3.5 text-slate-400" />
                          {s.archers_count} Archers
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    <button
                      onClick={() => handleLaunchScoring(s)}
                      className="btn-primary text-xs py-2 px-3 flex items-center gap-1.5 shadow-md"
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      Open Live Scoring
                    </button>
                  </div>
                </div>
              )
            })
          ) : (
            <div className="py-12 text-center text-slate-500">
              <Target className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No sessions found for selected filter</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-navy-800 bg-navy-900/80 flex items-center justify-between text-xs text-slate-400">
          <span>Select any session to open real-time camera scoring</span>
          <button onClick={onClose} className="px-3 py-1.5 bg-navy-800 hover:bg-navy-700 text-slate-300 rounded-lg">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
