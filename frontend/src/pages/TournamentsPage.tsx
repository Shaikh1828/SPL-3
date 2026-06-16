import { useState, useEffect } from 'react'
import { Trophy, Plus, Calendar, MapPin, ChevronRight, PlayCircle, Archive, X } from 'lucide-react'
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

  // Modals state
  const [isCreateTournamentOpen, setIsCreateTournamentOpen] = useState(false)
  const [newTournamentData, setNewTournamentData] = useState({
    name: '',
    location: '',
    description: '',
    start_date: '',
    end_date: '',
  })
  const [isCreateSessionOpen, setIsCreateSessionOpen] = useState(false)
  const [activeTournamentForSession, setActiveTournamentForSession] = useState<number | null>(null)
  const [newSessionData, setNewSessionData] = useState({
    name: '',
    round_number: 1,
    num_lanes: 6,
    arrows_per_round: 6,
  })

  const handleCreateTournament = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTournamentData.name || !newTournamentData.start_date || !newTournamentData.end_date) {
      toast.error('Please fill in required fields')
      return
    }
    try {
      await tournamentsApi.create(newTournamentData)
      toast.success('Tournament created successfully')
      setIsCreateTournamentOpen(false)
      setNewTournamentData({ name: '', location: '', description: '', start_date: '', end_date: '' })
      loadTournaments()
    } catch {
      toast.error('Failed to create tournament')
    }
  }

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeTournamentForSession || !newSessionData.name) {
      toast.error('Please fill in required fields')
      return
    }
    try {
      await sessionsApi.create(activeTournamentForSession, newSessionData)
      toast.success('Session created successfully')
      setIsCreateSessionOpen(false)
      setNewSessionData({ name: '', round_number: 1, num_lanes: 6, arrows_per_round: 6 })
      // Refresh sessions for this tournament
      const res = await sessionsApi.listForTournament(activeTournamentForSession)
      const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
      setSessionsMap(prev => ({ ...prev, [activeTournamentForSession]: list }))
    } catch {
      toast.error('Failed to create session')
    }
  }

  useEffect(() => {
    loadTournaments()
  }, [])

  const loadTournaments = async () => {
    setLoading(true)
    try {
      const res = await tournamentsApi.list()
      const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
      setTournaments(list)
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
        const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
        setSessionsMap(prev => ({ ...prev, [tId]: list }))
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
        <button onClick={() => setIsCreateTournamentOpen(true)} className="btn-primary flex items-center gap-2">
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
                  <button 
                    onClick={() => { setActiveTournamentForSession(t.id); setIsCreateSessionOpen(true); }}
                    className="btn-ghost text-xs flex items-center gap-1"
                  >
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

      {/* Create Tournament Modal */}
      {isCreateTournamentOpen && (
        <div className="fixed inset-0 bg-navy-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 space-y-4 animate-in">
            <div className="flex justify-between items-center pb-2 border-b border-navy-700">
              <h3 className="text-lg font-bold text-slate-100">New Tournament</h3>
              <button onClick={() => setIsCreateTournamentOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateTournament} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Tournament Name *</label>
                <input
                  type="text"
                  required
                  value={newTournamentData.name}
                  onChange={e => setNewTournamentData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g. Summer Qualifier 2026"
                  className="input-dark w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Location</label>
                <input
                  type="text"
                  value={newTournamentData.location}
                  onChange={e => setNewTournamentData(prev => ({ ...prev, location: e.target.value }))}
                  placeholder="e.g. Sports Complex Range"
                  className="input-dark w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Description</label>
                <textarea
                  value={newTournamentData.description}
                  onChange={e => setNewTournamentData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Add tournament details..."
                  className="input-dark w-full min-h-[80px]"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Start Date *</label>
                  <input
                    type="date"
                    required
                    value={newTournamentData.start_date}
                    onChange={e => setNewTournamentData(prev => ({ ...prev, start_date: e.target.value }))}
                    className="input-dark w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">End Date *</label>
                  <input
                    type="date"
                    required
                    value={newTournamentData.end_date}
                    onChange={e => setNewTournamentData(prev => ({ ...prev, end_date: e.target.value }))}
                    className="input-dark w-full"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-2 border-t border-navy-700">
                <button
                  type="button"
                  onClick={() => setIsCreateTournamentOpen(false)}
                  className="btn-ghost py-2 text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary py-2 text-sm"
                >
                  Create Tournament
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Session Modal */}
      {isCreateSessionOpen && (
        <div className="fixed inset-0 bg-navy-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 space-y-4 animate-in">
            <div className="flex justify-between items-center pb-2 border-b border-navy-700">
              <h3 className="text-lg font-bold text-slate-100">Add Session</h3>
              <button onClick={() => setIsCreateSessionOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateSession} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Session Name *</label>
                <input
                  type="text"
                  required
                  value={newSessionData.name}
                  onChange={e => setNewSessionData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g. Round 1 Qualification"
                  className="input-dark w-full"
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Round #</label>
                  <input
                    type="number"
                    min="1"
                    value={newSessionData.round_number}
                    onChange={e => setNewSessionData(prev => ({ ...prev, round_number: parseInt(e.target.value) || 1 }))}
                    className="input-dark w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Num Lanes</label>
                  <input
                    type="number"
                    min="1"
                    max="12"
                    value={newSessionData.num_lanes}
                    onChange={e => setNewSessionData(prev => ({ ...prev, num_lanes: parseInt(e.target.value) || 6 }))}
                    className="input-dark w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Ends</label>
                  <input
                    type="number"
                    min="1"
                    max="12"
                    value={newSessionData.arrows_per_round}
                    onChange={e => setNewSessionData(prev => ({ ...prev, arrows_per_round: parseInt(e.target.value) || 6 }))}
                    className="input-dark w-full"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-2 border-t border-navy-700">
                <button
                  type="button"
                  onClick={() => setIsCreateSessionOpen(false)}
                  className="btn-ghost py-2 text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary py-2 text-sm"
                >
                  Create Session
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
