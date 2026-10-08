import { useState, useEffect, useMemo } from 'react'
import { 
  Trophy, 
  Plus, 
  Calendar, 
  MapPin, 
  ChevronRight, 
  PlayCircle, 
  Archive, 
  X, 
  ShieldAlert, 
  Search, 
  CheckCircle2, 
  Clock, 
  Trash2, 
  FileText, 
  Users, 
  Activity,
  Award
} from 'lucide-react'
import { tournamentsApi } from '@/api/tournaments'
import { sessionsApi } from '@/api/sessions'
import { useSessionStore } from '@/store/sessionStore'
import { useAuthStore } from '@/store/authStore'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { cn, formatDate } from '@/lib/utils'
import type { Tournament, Session } from '@/types'

export default function TournamentsPage() {
  const navigate = useNavigate()
  const { setActiveSession, setActiveTournament } = useSessionStore()
  const { user } = useAuthStore()
  const canManageTournaments = user?.role === 'admin' || user?.role === 'scorer'
  const isAdmin = user?.role === 'admin'

  const [tournaments, setTournaments] = useState<Tournament[]>([])
  const [expandedTId, setExpandedTId] = useState<number | null>(null)
  const [sessionsMap, setSessionsMap] = useState<Record<number, Session[]>>({})
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'all' | 'ongoing' | 'completed' | 'upcoming'>('all')
  const [searchQuery, setSearchQuery] = useState('')

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

  const loadTournaments = async () => {
    setLoading(true)
    try {
      const res = await tournamentsApi.list({ limit: 100 })
      const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
      setTournaments(list)
    } catch {
      toast.error('Failed to load tournaments')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTournaments()
  }, [])

  const handleCreateTournament = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTournamentData.name || !newTournamentData.start_date || !newTournamentData.end_date) {
      toast.error('Please fill in required fields')
      return
    }
    try {
      const payload = {
        ...newTournamentData,
        start_date: new Date(newTournamentData.start_date + 'T00:00:00').toISOString(),
        end_date: new Date(newTournamentData.end_date + 'T23:59:59').toISOString(),
      }
      await tournamentsApi.create(payload)
      toast.success('Tournament created successfully')
      setIsCreateTournamentOpen(false)
      setNewTournamentData({ name: '', location: '', description: '', start_date: '', end_date: '' })
      loadTournaments()
    } catch {
      toast.error('Failed to create tournament')
    }
  }

  const handleDeleteTournament = async (tId: number, name: string) => {
    if (!window.confirm(`Are you sure you want to delete "${name}"? This action cannot be undone.`)) {
      return
    }
    try {
      await tournamentsApi.delete(tId)
      toast.success(`Deleted tournament: ${name}`)
      setTournaments(prev => prev.filter(t => t.id !== tId))
    } catch {
      toast.error('Failed to delete tournament')
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
      const res = await sessionsApi.listForTournament(activeTournamentForSession)
      const list = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
      setSessionsMap(prev => ({ ...prev, [activeTournamentForSession]: list }))
      loadTournaments()
    } catch {
      toast.error('Failed to create session')
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
      toast.success(`Active session: ${s.name}`)
      navigate('/scoring')
    } catch {
      toast.error('Failed to start session')
    }
  }

  const handleJumpToLiveScoring = async (t: Tournament) => {
    try {
      // Fetch sessions for this tournament
      let sessions = sessionsMap[t.id]
      if (!sessions) {
        const res = await sessionsApi.listForTournament(t.id)
        sessions = Array.isArray(res) ? res : (res && Array.isArray(res.items) ? res.items : [])
        setSessionsMap(prev => ({ ...prev, [t.id]: sessions }))
      }
      const activeSess = sessions.find(s => s.status === 'active') || sessions[0]
      if (activeSess) {
        setActiveTournament(t)
        setActiveSession(activeSess)
        toast.success(`Jumping to live scoring: ${activeSess.name}`)
        navigate('/scoring')
      } else {
        toast.error('No sessions found for this tournament')
      }
    } catch {
      toast.error('Failed to navigate to scoring')
    }
  }

  const handleViewReports = (t: Tournament) => {
    setActiveTournament(t)
    toast.success(`Loading reports for ${t.name}`)
    navigate('/reports')
  }

  // Filtered tournaments based on tab and search
  const filteredTournaments = useMemo(() => {
    return tournaments.filter(t => {
      const matchesTab = activeTab === 'all' || (t.status || 'ongoing') === activeTab
      const query = searchQuery.toLowerCase().trim()
      const matchesSearch = !query || 
        t.name.toLowerCase().includes(query) ||
        (t.location && t.location.toLowerCase().includes(query)) ||
        (t.winner_name && t.winner_name.toLowerCase().includes(query))
      return matchesTab && matchesSearch
    })
  }, [tournaments, activeTab, searchQuery])

  // Counts for tabs
  const ongoingCount = useMemo(() => tournaments.filter(t => t.status === 'ongoing').length, [tournaments])
  const completedCount = useMemo(() => tournaments.filter(t => t.status === 'completed').length, [tournaments])
  const upcomingCount = useMemo(() => tournaments.filter(t => t.status === 'upcoming').length, [tournaments])

  return (
    <div className="p-6 h-full flex flex-col animate-in overflow-hidden">
      {!canManageTournaments && (
        <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-300 text-sm flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 shrink-0 text-amber-400" />
          <span>Spectator Mode: View live tournaments, completed results & championship leaderboards.</span>
        </div>
      )}

      {/* Header & Quick Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2.5">
            <Trophy className="w-6 h-6 text-gold-400" />
            Tournament Management
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Multi-stage championship control, real-time live scoring, and archived competition results
          </p>
        </div>
        {canManageTournaments && (
          <button 
            onClick={() => setIsCreateTournamentOpen(true)} 
            className="btn-primary flex items-center gap-2 shadow-lg shadow-gold-500/20"
          >
            <Plus className="w-4 h-4" /> Create Tournament
          </button>
        )}
      </div>

      {/* Top Stat Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="glass-card p-3.5 flex items-center gap-3 border-l-4 border-l-blue-500">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
            <Trophy className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Total Events</div>
            <div className="text-xl font-bold text-slate-100">{tournaments.length}</div>
          </div>
        </div>

        <div className="glass-card p-3.5 flex items-center gap-3 border-l-4 border-l-emerald-500">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 relative">
            <Activity className="w-5 h-5" />
            {ongoingCount > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            )}
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Live / Ongoing</div>
            <div className="text-xl font-bold text-emerald-400">{ongoingCount}</div>
          </div>
        </div>

        <div className="glass-card p-3.5 flex items-center gap-3 border-l-4 border-l-purple-500">
          <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Completed</div>
            <div className="text-xl font-bold text-purple-300">{completedCount}</div>
          </div>
        </div>

        <div className="glass-card p-3.5 flex items-center gap-3 border-l-4 border-l-amber-500">
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Upcoming</div>
            <div className="text-xl font-bold text-amber-300">{upcomingCount}</div>
          </div>
        </div>
      </div>

      {/* Filter Tabs & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-1.5 p-1 bg-navy-900/80 border border-navy-700/80 rounded-xl overflow-x-auto">
          <button
            onClick={() => setActiveTab('all')}
            className={cn(
              "px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 whitespace-nowrap",
              activeTab === 'all'
                ? "bg-navy-700 text-slate-100 shadow"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            All Tournaments
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-navy-800 text-slate-300">
              {tournaments.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('ongoing')}
            className={cn(
              "px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 whitespace-nowrap",
              activeTab === 'ongoing'
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Live / Ongoing
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-950 text-emerald-300">
              {ongoingCount}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('completed')}
            className={cn(
              "px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 whitespace-nowrap",
              activeTab === 'completed'
                ? "bg-purple-500/20 text-purple-300 border border-purple-500/30 shadow"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-purple-400" />
            Completed / Finished
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-purple-950 text-purple-300">
              {completedCount}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('upcoming')}
            className={cn(
              "px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 whitespace-nowrap",
              activeTab === 'upcoming'
                ? "bg-blue-500/20 text-blue-300 border border-blue-500/30 shadow"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            <Clock className="w-3.5 h-3.5 text-blue-400" />
            Upcoming
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-blue-950 text-blue-300">
              {upcomingCount}
            </span>
          </button>
        </div>

        {/* Live Search */}
        <div className="relative min-w-[240px]">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search tournament, venue, champion..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-dark w-full pl-9 pr-8 py-1.5 text-xs rounded-xl"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Tournaments List */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {filteredTournaments.map(t => {
          const status = t.status || 'ongoing'
          const isOngoing = status === 'ongoing'
          const isCompleted = status === 'completed'
          const isUpcoming = status === 'upcoming'

          return (
            <div 
              key={t.id} 
              className={cn(
                "glass-card overflow-hidden transition-all duration-200",
                isOngoing && "border-emerald-500/30 shadow-lg shadow-emerald-950/20",
                isCompleted && "border-purple-500/20",
                isUpcoming && "border-blue-500/20"
              )}
            >
              {/* Card Main Bar */}
              <div 
                className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-navy-800/40 transition-colors"
                onClick={() => toggleTournament(t.id)}
              >
                <div className="flex items-start md:items-center gap-4">
                  {/* Status Indicator Icon */}
                  <div className={cn(
                    "w-12 h-12 rounded-xl flex items-center justify-center shrink-0 border",
                    isOngoing && "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 shadow-inner",
                    isCompleted && "bg-purple-500/10 border-purple-500/30 text-purple-400",
                    isUpcoming && "bg-blue-500/10 border-blue-500/30 text-blue-400"
                  )}>
                    {isOngoing ? (
                      <div className="relative">
                        <Activity className="w-6 h-6 animate-pulse" />
                        <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full animate-ping" />
                      </div>
                    ) : isCompleted ? (
                      <Trophy className="w-6 h-6 text-gold-400" />
                    ) : (
                      <Calendar className="w-6 h-6" />
                    )}
                  </div>

                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <h3 className="font-bold text-slate-100 text-lg">{t.name}</h3>

                      {/* Status Tag */}
                      <span className={cn(
                        "text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1 border",
                        isOngoing && "bg-emerald-500/15 text-emerald-300 border-emerald-500/40 shadow-sm",
                        isCompleted && "bg-purple-500/15 text-purple-300 border-purple-500/40",
                        isUpcoming && "bg-blue-500/15 text-blue-300 border-blue-500/40"
                      )}>
                        {isOngoing && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping inline-block" />}
                        {isOngoing ? '🟢 Live / In-Progress' : isCompleted ? '🏁 Completed' : '📅 Upcoming'}
                      </span>
                    </div>

                    {t.description && (
                      <p className="text-xs text-slate-400 mb-2 line-clamp-1 max-w-2xl">{t.description}</p>
                    )}

                    {/* Metadata & Stats Pills */}
                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                      {t.location && (
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5 text-slate-500" /> {t.location}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        {formatDate(t.start_date)} – {formatDate(t.end_date)}
                      </span>
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-navy-800 text-slate-300 border border-navy-700">
                        <Activity className="w-3 h-3 text-blue-400" />
                        {t.total_sessions || 0} Sessions ({t.active_sessions || 0} active, {t.completed_sessions || 0} completed)
                      </span>
                      {t.total_archers ? (
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-navy-800 text-slate-300 border border-navy-700">
                          <Users className="w-3 h-3 text-emerald-400" />
                          {t.total_archers} Archers
                        </span>
                      ) : null}
                    </div>

                    {/* Champion Podium Badge for Completed Tournaments */}
                    {isCompleted && t.winner_name && (
                      <div className="mt-2.5 inline-flex items-center gap-2 px-3 py-1 bg-gold-500/10 border border-gold-500/30 rounded-lg text-gold-300 text-xs font-semibold">
                        <Award className="w-4 h-4 text-gold-400 shrink-0" />
                        <span>Championship Gold: <strong className="text-slate-100">{t.winner_name}</strong> ({t.winner_score} pts)</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Right Action Buttons */}
                <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                  {isOngoing && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleJumpToLiveScoring(t); }}
                      className="px-3.5 py-1.5 bg-emerald-500 hover:bg-emerald-400 text-navy-950 font-bold text-xs rounded-lg transition-colors flex items-center gap-1.5 shadow-md shadow-emerald-500/20"
                    >
                      <PlayCircle className="w-4 h-4" /> Live Scoring
                    </button>
                  )}

                  {isCompleted && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleViewReports(t); }}
                      className="px-3.5 py-1.5 bg-navy-700 hover:bg-navy-600 text-gold-300 border border-gold-500/30 font-semibold text-xs rounded-lg transition-colors flex items-center gap-1.5"
                    >
                      <FileText className="w-4 h-4 text-gold-400" /> Official Results
                    </button>
                  )}

                  {isAdmin && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteTournament(t.id, t.name); }}
                      className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                      title="Delete Tournament"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}

                  <div className="p-1 text-slate-500">
                    <ChevronRight className={cn(
                      "w-5 h-5 transition-transform duration-200",
                      expandedTId === t.id && "rotate-90 text-gold-400"
                    )} />
                  </div>
                </div>
              </div>

              {/* Expanded Sessions Drawer */}
              {expandedTId === t.id && (
                <div className="bg-navy-900/60 border-t border-navy-700/80 p-5 animate-in">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                        <Activity className="w-4 h-4 text-blue-400" />
                        Sessions & Match Rounds
                      </h4>
                      <p className="text-xs text-slate-500">Active and completed scoring heats for this tournament</p>
                    </div>
                    {canManageTournaments && (
                      <button 
                        onClick={() => { setActiveTournamentForSession(t.id); setIsCreateSessionOpen(true); }}
                        className="btn-ghost text-xs flex items-center gap-1 border border-navy-700 hover:border-gold-500/40"
                      >
                        <Plus className="w-3.5 h-3.5" /> Add Session Heat
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {sessionsMap[t.id]?.map(s => (
                      <div 
                        key={s.id} 
                        className={cn(
                          "bg-navy-800/90 border rounded-xl p-4 transition-all",
                          s.status === 'active' ? "border-emerald-500/40 shadow-md shadow-emerald-950/20" :
                          s.status === 'completed' ? "border-navy-700/80" : "border-navy-700"
                        )}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <p className="font-semibold text-slate-200 text-sm">{s.name}</p>
                          <span className={cn(
                            "text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider",
                            s.status === 'active' ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" :
                            s.status === 'completed' ? "bg-purple-500/20 text-purple-300 border border-purple-500/30" :
                            "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                          )}>
                            {s.status}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mb-4">
                          Round {s.round_number} · {s.num_lanes} Lanes · {s.arrows_per_round} Arrows/End
                        </p>
                        
                        <div className="flex gap-2">
                          {s.status !== 'completed' ? (
                            <button 
                              onClick={() => handleStartSession(t, s)}
                              className="flex-1 bg-gold-500 hover:bg-gold-400 text-navy-950 text-xs font-bold py-2 rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow"
                            >
                              <PlayCircle className="w-4 h-4" /> {s.status === 'active' ? 'Resume Scoring' : 'Start Heat'}
                            </button>
                          ) : (
                            <button 
                              onClick={() => handleViewReports(t)}
                              className="flex-1 bg-navy-700 hover:bg-navy-600 text-slate-200 text-xs font-medium py-2 rounded-lg transition-colors flex items-center justify-center gap-1.5"
                            >
                              <Archive className="w-3.5 h-3.5 text-purple-400" /> View Session Report
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                    {(!sessionsMap[t.id] || sessionsMap[t.id].length === 0) && (
                      <div className="py-6 text-center text-slate-500 border border-dashed border-navy-700/70 rounded-xl col-span-full">
                        No session heats configured yet. Click "Add Session Heat" to create one.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}

        {filteredTournaments.length === 0 && !loading && (
          <div className="py-16 text-center text-slate-400 border border-dashed border-navy-700/80 rounded-2xl p-8 glass-card">
            <Trophy className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-200 mb-1">No tournaments matching criteria</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">
              {searchQuery ? `No events match "${searchQuery}" in category "${activeTab}".` : `No ${activeTab} tournaments available.`}
            </p>
            {canManageTournaments && (
              <button onClick={() => setIsCreateTournamentOpen(true)} className="btn-primary text-xs mx-auto">
                <Plus className="w-4 h-4 mr-1.5" /> Create New Tournament
              </button>
            )}
          </div>
        )}
      </div>

      {/* Create Tournament Modal */}
      {isCreateTournamentOpen && (
        <div className="fixed inset-0 bg-navy-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 space-y-4 animate-in">
            <div className="flex justify-between items-center pb-2 border-b border-navy-700">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Trophy className="w-5 h-5 text-gold-400" /> New Tournament
              </h3>
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
                  placeholder="e.g. Bangladesh Independence Cup 2026"
                  className="input-dark w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Location / Venue</label>
                <input
                  type="text"
                  value={newTournamentData.location}
                  onChange={e => setNewTournamentData(prev => ({ ...prev, location: e.target.value }))}
                  placeholder="e.g. National Sports Stadium Range, Dhaka"
                  className="input-dark w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Description</label>
                <textarea
                  value={newTournamentData.description}
                  onChange={e => setNewTournamentData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Premiere outdoor archery championship featuring 70m Olympic rounds..."
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
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Plus className="w-5 h-5 text-gold-400" /> Add Session Heat
              </h3>
              <button onClick={() => setIsCreateSessionOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateSession} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Session Heat Name *</label>
                <input
                  type="text"
                  required
                  value={newSessionData.name}
                  onChange={e => setNewSessionData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g. Session 1 - Recurve 720 Round"
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
