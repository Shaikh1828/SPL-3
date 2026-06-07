import { useState, useEffect } from 'react'
import { Trophy, Plus, Calendar, MapPin, ChevronRight, PlayCircle, Archive } from 'lucide-react'
import { tournamentsApi } from '@/api/tournaments'
import { sessionsApi } from '@/api/sessions'
import { useSessionStore } from '@/store/sessionStore'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { cn, formatDate } from '@/lib/utils'
import type { Tournament, Session } from '@/types'

export default function TournamentsPage() {
  const navigate = useNavigate()
  const { setActiveSession, setActiveTournament } = useSessionStore()
  const [tournaments, setTournaments] = useState<Tournament[]>([])
  const [expandedTId, setExpandedTId] = useState<number | null>(null)
  const [sessionsMap, setSessionsMap] = useState<Record<number, Session[]>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadTournaments()
  }, [])

  const loadTournaments = async () => {
    setLoading(true)
    try {
      const res = await tournamentsApi.list()
      setTournaments(res.items)
    } catch {
      toast.error('Failed to load tournaments')
    } finally {
      setLoading(false)
    }
  }

  const toggleTournament = async (tId: number) => {
    if (expandedTId === tId) {
      setExpandedTId(null)
      return
    }
    setExpandedTId(tId)
    if (!sessionsMap[tId]) {
      try {
        const res = await sessionsApi.listForTournament(tId)
        setSessionsMap(prev => ({ ...prev, [tId]: res.items }))
      } catch {
        toast.error('Failed to load sessions')
      }
    }
  }

  const handleStartSession = async (t: Tournament, s: Session) => {
    try {
      if (s.status !== 'active') {
        await sessionsApi.updateStatus(s.id, 'active')
      }
      setActiveTournament(t)
      setActiveSession({ ...s, status: 'active' })
      toast.success(`Started session: ${s.name}`)
      navigate('/dashboard')
    } catch {
      toast.error('Failed to start session')
    }
  }

  return (
    <div className="p-6 h-full flex flex-col animate-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Tournaments</h1>
          <p className="text-sm text-slate-500 mt-0.5">Manage tournaments and scoring sessions</p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Tournament
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4">
        {tournaments.map(t => (
          <div key={t.id} className="glass-card overflow-hidden">
            <div 
              className="p-5 flex items-center justify-between cursor-pointer hover:bg-navy-800/50 transition-colors"
              onClick={() => toggleTournament(t.id)}
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-gold-500/10 border border-gold-500/20 flex items-center justify-center">
                  <Trophy className="w-5 h-5 text-gold-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-200 text-lg">{t.name}</h3>
                  <div className="flex gap-4 mt-1">
                    {t.location && (
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <MapPin className="w-3 h-3" /> {t.location}
                      </span>
                    )}
                    <span className="text-xs text-slate-500 flex items-center gap-1">
                      <Calendar className="w-3 h-3" /> {formatDate(t.start_date)}
                    </span>
                  </div>
                </div>
              </div>
              <ChevronRight className={cn(
                "w-5 h-5 text-slate-500 transition-transform",
                expandedTId === t.id && "rotate-90"
              )} />
            </div>

            {expandedTId === t.id && (
              <div className="bg-navy-900/50 border-t border-navy-700 p-5">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-sm font-medium text-slate-300">Sessions</h4>
                  <button className="btn-ghost text-xs flex items-center gap-1">
                    <Plus className="w-3 h-3" /> Add Session
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {sessionsMap[t.id]?.map(s => (
                    <div key={s.id} className="bg-navy-800 border border-navy-700 rounded-lg p-4">
                      <div className="flex justify-between items-start mb-3">
                        <p className="font-medium text-slate-200">{s.name}</p>
                        <span className={cn(
                          "text-[10px] px-2 py-0.5 rounded-full font-medium uppercase tracking-wider",
                          s.status === 'active' ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" :
                          s.status === 'completed' ? "bg-slate-500/20 text-slate-400 border border-slate-500/30" :
                          "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                        )}>
                          {s.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mb-4">Round {s.round_number} · {s.num_lanes} Lanes · {s.arrows_per_round} Ends</p>
                      
                      <div className="flex gap-2">
                        {s.status !== 'completed' ? (
                          <button 
                            onClick={() => handleStartSession(t, s)}
                            className="flex-1 bg-gold-500 hover:bg-gold-400 text-navy-900 text-sm font-medium py-1.5 rounded transition-colors flex items-center justify-center gap-1.5"
                          >
                            <PlayCircle className="w-4 h-4" /> {s.status === 'active' ? 'Resume' : 'Start'}
                          </button>
                        ) : (
                          <button className="flex-1 bg-navy-700 text-slate-300 text-sm py-1.5 rounded cursor-not-allowed flex items-center justify-center gap-1.5">
                            <Archive className="w-4 h-4" /> Completed
                          </button>
                        )}
                        <button className="px-3 bg-navy-700 hover:bg-navy-600 text-slate-300 text-sm rounded transition-colors">
                          Edit
                        </button>
                      </div>
                    </div>
                  ))}
                  {(!sessionsMap[t.id] || sessionsMap[t.id].length === 0) && (
                    <p className="text-sm text-slate-500 py-4 col-span-full">No sessions created yet.</p>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
        {tournaments.length === 0 && !loading && (
          <div className="py-12 text-center text-slate-500 border border-dashed border-navy-700 rounded-xl">
            No tournaments found. Create one to get started.
          </div>
        )}
      </div>
    </div>
  )
}
