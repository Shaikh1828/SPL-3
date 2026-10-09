import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Target, Trophy, Users, Activity, Play,
  Sparkles, RefreshCw, ChevronRight, Medal, Flame,
  Camera, BarChart3, ArrowUpRight, Clock, Search,
  Calendar, MapPin, Eye, CheckCircle
} from 'lucide-react'
import { sessionsApi } from '@/api/sessions'
import { tournamentsApi } from '@/api/tournaments'
import { scoresApi } from '@/api/scores'
import { useSessionStore } from '@/store/sessionStore'
import { useScoreStream } from '@/hooks/useScoreStream'
import type { LeaderboardEntry, Tournament, Session, RecentScoreItem } from '@/types'
import { cn, formatDate } from '@/lib/utils'

import { TournamentsModal } from '@/components/dashboard/TournamentsModal'
import { SessionsModal } from '@/components/dashboard/SessionsModal'
import { ArchersModal } from '@/components/dashboard/ArchersModal'
import { ArcherDetailModal } from '@/components/dashboard/ArcherDetailModal'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { activeSession, setActiveSession, activeTournament, setActiveTournament } = useSessionStore()
  
  const [tournaments, setTournaments] = useState<Tournament[]>([])
  const [tournamentSessions, setTournamentSessions] = useState<Session[]>([])
  const [allSessions, setAllSessions] = useState<Session[]>([])
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [recentScores, setRecentScores] = useState<RecentScoreItem[]>([])
  const [selectedTournament, setSelectedTournament] = useState<Tournament | null>(null)
  const [leaderboardScope, setLeaderboardScope] = useState<'tournament' | 'session'>('tournament')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [leaderboardLoading, setLeaderboardLoading] = useState(false)

  // Interactive modal states
  const [isTournamentsOpen, setIsTournamentsOpen] = useState(false)
  const [isSessionsOpen, setIsSessionsOpen] = useState(false)
  const [isArchersOpen, setIsArchersOpen] = useState(false)
  const [selectedArcherForDetail, setSelectedArcherForDetail] = useState<LeaderboardEntry | null>(null)

  // Real-time score stream subscription
  const { lastEvent } = useScoreStream(activeSession?.id ?? null)

  const fetchRecentActivity = useCallback(async () => {
    try {
      const data = await scoresApi.recent(10)
      setRecentScores(data)
    } catch {
      // ignore
    }
  }, [])

  // Fetch leaderboard based on selected tournament & scope
  const fetchLeaderboardData = useCallback(async (tourney: Tournament | null, session: Session | null, scope: 'tournament' | 'session') => {
    if (!tourney) return
    try {
      setLeaderboardLoading(true)
      if (scope === 'tournament') {
        const data = await tournamentsApi.getLeaderboard(tourney.id)
        setLeaderboard(data || [])
      } else if (session) {
        const data = await sessionsApi.getLeaderboard(session.id)
        setLeaderboard(data || [])
      }
    } catch (err) {
      console.error('Failed to fetch leaderboard:', err)
    } finally {
      setLeaderboardLoading(false)
    }
  }, [])

  // Handle tournament click/selection
  const handleSelectTournament = async (tourney: Tournament, scrollToLeaderboard = false) => {
    setSelectedTournament(tourney)
    setActiveTournament(tourney)

    // Load sessions for this tournament
    try {
      const s = await sessionsApi.listForTournament(tourney.id)
      const sList = Array.isArray(s) ? s : (s && Array.isArray((s as any).items) ? (s as any).items : [])
      setTournamentSessions(sList)

      const ongoing = sList.find((item: Session) => item.status === 'active') || (sList.length > 0 ? sList[0] : null)
      if (ongoing) {
        setActiveSession(ongoing)
      }

      // Fetch tournament-wide leaderboard
      await fetchLeaderboardData(tourney, ongoing, leaderboardScope)
    } catch (err) {
      console.error('Failed to load tournament sessions:', err)
    }

    if (scrollToLeaderboard) {
      setTimeout(() => {
        const el = document.getElementById('tournament-live-dashboard-section')
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 60)
    }
  }

  // Initial load on mount
  useEffect(() => {
    let isMounted = true
    const init = async () => {
      try {
        setLoading(true)
        const t = await tournamentsApi.list({ limit: 50 })
        const tList = Array.isArray(t) ? t : (t && Array.isArray((t as any).items) ? (t as any).items : [])
        if (!isMounted) return
        setTournaments(tList)

        if (tList.length > 0) {
          const current = activeTournament || tList[0]
          setSelectedTournament(current)
          setActiveTournament(current)

          // Load sessions for aggregate metrics
          const promises = tList.slice(0, 5).map((tourney: Tournament) => 
            sessionsApi.listForTournament(tourney.id).catch(() => [])
          )
          const results = await Promise.all(promises)
          const flattened = results.flatMap(res => 
            Array.isArray(res) ? res : (res && Array.isArray((res as any).items) ? (res as any).items : [])
          )
          if (!isMounted) return
          setAllSessions(flattened)

          // Load sessions for selected tournament
          const s = await sessionsApi.listForTournament(current.id)
          const sList = Array.isArray(s) ? s : (s && Array.isArray((s as any).items) ? (s as any).items : [])
          if (!isMounted) return
          setTournamentSessions(sList)

          const ongoing = activeSession || sList.find((item: Session) => item.status === 'active') || (sList.length > 0 ? sList[0] : null)
          if (ongoing && !activeSession) {
            setActiveSession(ongoing)
          }

          // Fetch tournament leaderboard
          await fetchLeaderboardData(current, ongoing, leaderboardScope)
        }

        await fetchRecentActivity()
      } catch (err) {
        console.error('Error loading dashboard:', err)
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    init()
    return () => {
      isMounted = false
    }
  }, []) // Run once on component mount

  // Real-time live score updates
  useEffect(() => {
    if (lastEvent && selectedTournament) {
      fetchLeaderboardData(selectedTournament, activeSession, leaderboardScope)
      fetchRecentActivity()
    }
  }, [lastEvent, selectedTournament, activeSession, leaderboardScope, fetchLeaderboardData, fetchRecentActivity])

  // Filter leaderboard items based on search query
  const filteredLeaderboard = leaderboard.filter(item =>
    item.archer_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.lane_number?.toString().includes(searchQuery)
  )

  // Computed metrics
  const activeSessionsCount = allSessions.filter(s => s.status === 'active').length
  const totalArrowsInView = leaderboard.reduce((acc, curr) => acc + (curr.arrows_recorded || 0), 0)
  const topArcher = filteredLeaderboard.length > 0 ? filteredLeaderboard[0] : null
  const podiumTop3 = filteredLeaderboard.slice(0, 3)

  return (
    <div className="p-6 space-y-6 animate-in">
      {/* Interactive KPI Cards (Click to Open Modals) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Tournaments KPI Card */}
        <div
          onClick={() => setIsTournamentsOpen(true)}
          className="glass-card p-5 hover:border-gold-500/40 hover:bg-navy-800/60 transition-all cursor-pointer group relative overflow-hidden shadow-lg"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                Tournaments
                <span className="text-[10px] text-gold-400 bg-gold-500/10 px-1.5 py-0.2 rounded font-normal">Click to View</span>
              </p>
              <p className="text-3xl font-black text-slate-100 mt-1 group-hover:text-gold-400 transition-colors">
                {tournaments.length}
              </p>
              <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                <span>All Enrolled Competitions</span>
                <ChevronRight className="w-3.5 h-3.5 text-gold-400 group-hover:translate-x-1 transition-transform" />
              </p>
            </div>
            <div className="p-3 rounded-xl bg-gold-500/10 border border-gold-500/20 text-gold-400 group-hover:scale-110 transition-transform">
              <Trophy className="w-6 h-6" />
            </div>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-gold-500 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>

        {/* 2. Active Sessions KPI Card */}
        <div
          onClick={() => setIsSessionsOpen(true)}
          className="glass-card p-5 hover:border-emerald-500/40 hover:bg-navy-800/60 transition-all cursor-pointer group relative overflow-hidden shadow-lg"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                Active Sessions
                <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded font-normal">Ongoing</span>
              </p>
              <p className="text-3xl font-black text-slate-100 mt-1 group-hover:text-emerald-400 transition-colors">
                {activeSessionsCount || allSessions.length}
              </p>
              <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                <span>{activeSession ? activeSession.name : 'View Ongoing Rounds'}</span>
                <ChevronRight className="w-3.5 h-3.5 text-emerald-400 group-hover:translate-x-1 transition-transform" />
              </p>
            </div>
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 group-hover:scale-110 transition-transform">
              <Target className="w-6 h-6" />
            </div>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-emerald-500 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>

        {/* 3. Total Archers KPI Card */}
        <div
          onClick={() => setIsArchersOpen(true)}
          className="glass-card p-5 hover:border-blue-500/40 hover:bg-navy-800/60 transition-all cursor-pointer group relative overflow-hidden shadow-lg"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                Total Archers
                <span className="text-[10px] text-blue-400 bg-blue-500/10 px-1.5 py-0.2 rounded font-normal">Roster</span>
              </p>
              <p className="text-3xl font-black text-slate-100 mt-1 group-hover:text-blue-400 transition-colors">
                {leaderboard.length || 4}
              </p>
              <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                <span>Competitor Roster</span>
                <ChevronRight className="w-3.5 h-3.5 text-blue-400 group-hover:translate-x-1 transition-transform" />
              </p>
            </div>
            <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 group-hover:scale-110 transition-transform">
              <Users className="w-6 h-6" />
            </div>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>

        {/* 4. Arrows Shot & Telemetry Card */}
        <div
          onClick={() => navigate('/scoring')}
          className="glass-card p-5 hover:border-purple-500/40 hover:bg-navy-800/60 transition-all cursor-pointer group relative overflow-hidden shadow-lg"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                Arrows Recorded
                <span className="text-[10px] text-purple-400 bg-purple-500/10 px-1.5 py-0.2 rounded font-normal">Live</span>
              </p>
              <p className="text-3xl font-black text-slate-100 mt-1 group-hover:text-purple-400 transition-colors">
                {totalArrowsInView}
              </p>
              <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                <span>Top: <strong className="text-gold-400">{topArcher?.archer_name ?? '—'}</strong></span>
              </p>
            </div>
            <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 group-hover:scale-110 transition-transform">
              <Activity className="w-6 h-6" />
            </div>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-purple-500 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </div>

      {/* 🏆 TOURNAMENT SELECTOR RIBBON (Fixed height & scrollable with smooth leaderboard jump) */}
      <div className="glass-card p-5 space-y-3 border-gold-500/20 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-gold-400" />
            <h2 className="text-base font-bold text-slate-100">Select Tournament to View Standings</h2>
          </div>
          <span className="text-xs text-slate-400">
            Click any tournament below to view its enrolled player list & scores
          </span>
        </div>

        <div className="max-h-[260px] overflow-y-auto pr-1.5 scrollbar-thin scrollbar-thumb-navy-700 hover:scrollbar-thumb-gold-500/40 scrollbar-track-transparent">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {tournaments.map((tourney) => {
              const isSelected = selectedTournament?.id === tourney.id
              return (
                <div
                  key={tourney.id}
                  onClick={() => handleSelectTournament(tourney, true)}
                  className={cn(
                    'p-4 rounded-xl border transition-all cursor-pointer relative overflow-hidden group',
                    isSelected
                      ? 'bg-gradient-to-b from-gold-500/15 via-navy-800 to-navy-900 border-gold-500 shadow-lg shadow-gold-500/10'
                      : 'bg-navy-900/60 border-navy-700/60 hover:border-gold-500/40 hover:bg-navy-800/50'
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <h3 className={cn(
                        'text-sm font-bold truncate transition-colors',
                        isSelected ? 'text-gold-400' : 'text-slate-200 group-hover:text-gold-300'
                      )}>
                        {tourney.name}
                      </h3>
                      <p className="text-xs text-slate-400 flex items-center gap-1 mt-1 truncate">
                        <MapPin className="w-3 h-3 text-slate-500 flex-shrink-0" />
                        <span>{tourney.location || 'Archery Arena'}</span>
                      </p>
                      <p className="text-[11px] text-slate-500 flex items-center gap-1 mt-0.5">
                        <Calendar className="w-3 h-3 flex-shrink-0" />
                        <span>{formatDate(tourney.start_date)}</span>
                      </p>
                    </div>
                    {isSelected && (
                      <div className="w-6 h-6 rounded-full bg-gold-500 text-navy-950 flex items-center justify-center flex-shrink-0">
                        <CheckCircle className="w-4 h-4 fill-current" />
                      </div>
                    )}
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-navy-700/50 flex items-center justify-between text-xs">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
                      Active
                    </span>
                    <span className="text-slate-400 group-hover:text-gold-400 transition-colors flex items-center gap-1 text-[11px]">
                      View Leaderboard <ChevronRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* 🎯 TOURNAMENT LIVE DASHBOARD BANNER (Placed right above the Leaderboard) */}
      <div id="tournament-live-dashboard-section" className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 glass-card p-5 border-gold-500/20 bg-gradient-to-r from-navy-900 via-navy-800 to-navy-900 shadow-xl scroll-mt-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-gold-500/20 text-gold-400 border border-gold-500/30 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              Championship Leaderboard Hub
            </span>
            {selectedTournament && (
              <span className="text-xs text-slate-300 font-medium flex items-center gap-1.5 bg-navy-950/60 px-2.5 py-1 rounded-full border border-navy-700">
                <Trophy className="w-3.5 h-3.5 text-gold-400" />
                <span>Selected: <strong className="text-gold-400">{selectedTournament.name}</strong></span>
              </span>
            )}
          </div>
          <h1 className="text-2xl font-black text-slate-100 tracking-tight">
            Tournament Live Dashboard
          </h1>
          <p className="text-xs text-slate-400">
            Tournament-wise live scoring, archer roster rankings, and real-time score population
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => navigate('/scoring')}
            className="btn-primary text-xs py-2 px-3 flex items-center gap-1.5 shadow-md"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            Live Scoring
          </button>

          <button
            onClick={() => {
              if (selectedTournament) {
                fetchLeaderboardData(selectedTournament, activeSession, leaderboardScope)
              }
              fetchRecentActivity()
            }}
            disabled={loading || leaderboardLoading}
            className="btn-ghost text-xs p-2"
            title="Refresh leaderboard and scores"
          >
            <RefreshCw className={cn('w-4 h-4', (loading || leaderboardLoading) && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* Main Dashboard Interactive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Selected Tournament Leaderboard & Players */}
        <div className="lg:col-span-2 space-y-6">
          {/* Top 3 Podium Highlights for Selected Tournament */}
          {podiumTop3.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* 1st Place Gold */}
              {podiumTop3[0] && (
                <div
                  onClick={() => setSelectedArcherForDetail(podiumTop3[0])}
                  className="p-4 rounded-xl glass-card border-gold-500/40 bg-gradient-to-b from-gold-500/15 via-navy-800/60 to-navy-900/80 relative overflow-hidden shadow-lg cursor-pointer group hover:border-gold-500 transition-all"
                >
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-gold-500 text-navy-950 flex items-center gap-1">
                      <Medal className="w-3.5 h-3.5" />
                      1st Place
                    </span>
                    <span className="text-xs font-mono text-gold-400 font-semibold">Lane {podiumTop3[0].lane_number}</span>
                  </div>
                  <h3 className="text-base font-bold text-slate-100 mt-2 truncate group-hover:text-gold-400 transition-colors">{podiumTop3[0].archer_name}</h3>
                  <div className="flex items-baseline justify-between mt-2 pt-2 border-t border-gold-500/20">
                    <span className="text-xs text-slate-400">{podiumTop3[0].arrows_recorded} arrows</span>
                    <span className="text-2xl font-black text-gold-400">{podiumTop3[0].total_score} <span className="text-xs font-normal text-slate-400">pts</span></span>
                  </div>
                </div>
              )}

              {/* 2nd Place Silver */}
              {podiumTop3[1] && (
                <div
                  onClick={() => setSelectedArcherForDetail(podiumTop3[1])}
                  className="p-4 rounded-xl glass-card border-slate-400/30 bg-gradient-to-b from-slate-400/10 via-navy-800/60 to-navy-900/80 relative overflow-hidden shadow-lg cursor-pointer group hover:border-slate-300 transition-all"
                >
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-300 text-navy-950 flex items-center gap-1">
                      <Medal className="w-3.5 h-3.5" />
                      2nd Place
                    </span>
                    <span className="text-xs font-mono text-slate-300 font-semibold">Lane {podiumTop3[1].lane_number}</span>
                  </div>
                  <h3 className="text-base font-bold text-slate-100 mt-2 truncate group-hover:text-slate-100 transition-colors">{podiumTop3[1].archer_name}</h3>
                  <div className="flex items-baseline justify-between mt-2 pt-2 border-t border-slate-700/60">
                    <span className="text-xs text-slate-400">{podiumTop3[1].arrows_recorded} arrows</span>
                    <span className="text-2xl font-black text-slate-200">{podiumTop3[1].total_score} <span className="text-xs font-normal text-slate-400">pts</span></span>
                  </div>
                </div>
              )}

              {/* 3rd Place Bronze */}
              {podiumTop3[2] && (
                <div
                  onClick={() => setSelectedArcherForDetail(podiumTop3[2])}
                  className="p-4 rounded-xl glass-card border-amber-600/30 bg-gradient-to-b from-amber-600/10 via-navy-800/60 to-navy-900/80 relative overflow-hidden shadow-lg cursor-pointer group hover:border-amber-500 transition-all"
                >
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-600 text-slate-100 flex items-center gap-1">
                      <Medal className="w-3.5 h-3.5" />
                      3rd Place
                    </span>
                    <span className="text-xs font-mono text-amber-400 font-semibold">Lane {podiumTop3[2].lane_number}</span>
                  </div>
                  <h3 className="text-base font-bold text-slate-100 mt-2 truncate group-hover:text-amber-400 transition-colors">{podiumTop3[2].archer_name}</h3>
                  <div className="flex items-baseline justify-between mt-2 pt-2 border-t border-navy-700/60">
                    <span className="text-xs text-slate-400">{podiumTop3[2].arrows_recorded} arrows</span>
                    <span className="text-2xl font-black text-amber-400">{podiumTop3[2].total_score} <span className="text-xs font-normal text-slate-400">pts</span></span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Full Live Leaderboard & Player Roster Table */}
          <div className="glass-card p-5 space-y-4">
            {/* Header with Search and Scope Filters */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <Flame className="w-5 h-5 text-gold-400" />
                  <span>Leaderboard & Player Roster: <strong className="text-gold-400">{selectedTournament?.name || 'Tournament'}</strong></span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Live arrow scoring updates populate automatically as scorers input scores
                </p>
              </div>

              {/* Scope Toggles: Tournament Consolidated vs Session */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="inline-flex rounded-lg bg-navy-950/60 p-1 border border-navy-700">
                  <button
                    onClick={() => {
                      setLeaderboardScope('tournament')
                      if (selectedTournament) fetchLeaderboardData(selectedTournament, activeSession, 'tournament')
                    }}
                    className={cn(
                      'px-3 py-1 text-xs font-semibold rounded-md transition-all',
                      leaderboardScope === 'tournament'
                        ? 'bg-gold-500 text-navy-950 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    )}
                  >
                    Tournament Overall
                  </button>
                  <button
                    onClick={() => {
                      setLeaderboardScope('session')
                      if (selectedTournament) fetchLeaderboardData(selectedTournament, activeSession, 'session')
                    }}
                    className={cn(
                      'px-3 py-1 text-xs font-semibold rounded-md transition-all',
                      leaderboardScope === 'session'
                        ? 'bg-gold-500 text-navy-950 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    )}
                  >
                    Session Specific
                  </button>
                </div>

                {/* Session Dropdown (shown when in session scope) */}
                {leaderboardScope === 'session' && tournamentSessions.length > 0 && (
                  <select
                    value={activeSession?.id ?? ''}
                    onChange={(e) => {
                      const sId = Number(e.target.value)
                      const found = tournamentSessions.find(item => item.id === sId)
                      if (found) {
                        setActiveSession(found)
                        if (selectedTournament) fetchLeaderboardData(selectedTournament, found, 'session')
                      }
                    }}
                    className="bg-navy-900 text-xs font-semibold text-gold-400 px-3 py-1.5 rounded-lg border border-navy-700 focus:outline-none cursor-pointer"
                  >
                    {tournamentSessions.map(s => (
                      <option key={s.id} value={s.id} className="bg-navy-900 text-slate-200">
                        {s.name} ({s.status})
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            {/* Search Bar */}
            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search players by name or lane number..."
                className="w-full bg-navy-900/80 border border-navy-700 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-gold-500 transition-colors"
              />
            </div>

            {/* Player Roster Table */}
            {filteredLeaderboard.length > 0 ? (
              <div className="space-y-2">
                {filteredLeaderboard.map((entry) => (
                  <div
                    key={entry.archer_id}
                    onClick={() => setSelectedArcherForDetail(entry)}
                    className={cn(
                      'flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 rounded-xl transition-all cursor-pointer group',
                      entry.rank === 1
                        ? 'bg-gold-500/10 border border-gold-500/30 hover:border-gold-500/60'
                        : 'bg-navy-800/40 hover:bg-navy-800/70 border border-navy-700/40'
                    )}
                  >
                    <div className="flex items-center gap-3.5 min-w-0">
                      <span className={cn(
                        'w-8 h-8 rounded-full flex items-center justify-center text-xs font-black flex-shrink-0',
                        entry.rank === 1
                          ? 'bg-gold-500 text-navy-950 shadow-md shadow-gold-500/20'
                          : entry.rank === 2
                          ? 'bg-slate-300 text-navy-950'
                          : entry.rank === 3
                          ? 'bg-amber-600 text-white'
                          : 'bg-navy-700 text-slate-400'
                      )}>
                        {entry.rank}
                      </span>

                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-bold text-slate-100 truncate group-hover:text-gold-400 transition-colors">
                            {entry.archer_name}
                          </p>
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-semibold bg-navy-700/70 text-slate-300">
                            Lane {entry.lane_number}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                          <span>{entry.arrows_recorded} arrows shot</span>
                          {entry.average_score && (
                            <span>• Avg: <strong className="text-emerald-400">{entry.average_score}</strong></span>
                          )}
                          {entry.tens_count !== undefined && entry.tens_count > 0 && (
                            <span className="text-gold-400 font-semibold">• {entry.tens_count}x 10s</span>
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between sm:justify-end gap-4 pt-2 sm:pt-0 border-t sm:border-t-0 border-navy-700/40">
                      {/* Recent arrow sequence preview */}
                      {entry.recent_arrows && entry.recent_arrows.length > 0 && (
                        <div className="hidden md:flex items-center gap-1">
                          {entry.recent_arrows.slice(0, 4).map((pt, i) => (
                            <span
                              key={i}
                              className={`w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold border ${
                                pt === 10
                                  ? 'bg-gold-500/20 text-gold-400 border-gold-500/40'
                                  : pt >= 8
                                  ? 'bg-red-500/20 text-red-400 border-red-500/40'
                                  : 'bg-navy-700 text-slate-300 border-navy-600'
                              }`}
                            >
                              {pt}
                            </span>
                          ))}
                        </div>
                      )}

                      <div className="text-right">
                        <span className={cn(
                          'text-xl font-black font-mono',
                          entry.rank === 1 ? 'text-gold-400' : 'text-slate-100'
                        )}>
                          {entry.total_score}
                        </span>
                        <span className="text-[10px] text-slate-400 block -mt-0.5 uppercase tracking-wider">points</span>
                      </div>

                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedArcherForDetail(entry)
                        }}
                        className="p-1.5 rounded-lg bg-navy-700/50 hover:bg-gold-500/20 text-slate-400 hover:text-gold-400 transition-colors"
                        title="View detailed scorecard"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500">
                <Target className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No scores recorded for this tournament yet</p>
                <button
                  onClick={() => navigate('/scoring')}
                  className="mt-3 btn-primary text-xs py-1.5 px-3 inline-flex items-center gap-1.5"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  Begin Scoring Now
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Column (1 Col): Actions & Real-time Live Score Updates Feed */}
        <div className="space-y-6">
          {/* Quick Action Center */}
          <div className="glass-card p-5 space-y-3">
            <h2 className="font-bold text-sm text-slate-100 uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-gold-400" />
              Quick Actions
            </h2>
            <div className="grid grid-cols-1 gap-2">
              <button
                onClick={() => navigate('/scoring')}
                className="w-full btn-primary text-sm py-2.5 flex items-center justify-center gap-2 shadow-lg shadow-gold-500/10"
              >
                <Target className="w-4 h-4" />
                Live Target Scoring
              </button>
              <button
                onClick={() => navigate('/tournaments')}
                className="w-full text-xs py-2 px-3 border border-navy-700 hover:border-gold-500/40 rounded-lg text-slate-300 hover:text-slate-100 hover:bg-navy-800/60 transition-all flex items-center justify-between"
              >
                <span className="flex items-center gap-2">
                  <Trophy className="w-4 h-4 text-gold-400" />
                  Manage Tournaments
                </span>
                <ArrowUpRight className="w-3.5 h-3.5 text-slate-500" />
              </button>
              <button
                onClick={() => navigate('/cameras')}
                className="w-full text-xs py-2 px-3 border border-navy-700 hover:border-blue-500/40 rounded-lg text-slate-300 hover:text-slate-100 hover:bg-navy-800/60 transition-all flex items-center justify-between"
              >
                <span className="flex items-center gap-2">
                  <Camera className="w-4 h-4 text-blue-400" />
                  Target Camera Feeds
                </span>
                <ArrowUpRight className="w-3.5 h-3.5 text-slate-500" />
              </button>
              <button
                onClick={() => navigate('/reports')}
                className="w-full text-xs py-2 px-3 border border-navy-700 hover:border-purple-500/40 rounded-lg text-slate-300 hover:text-slate-100 hover:bg-navy-800/60 transition-all flex items-center justify-between"
              >
                <span className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-purple-400" />
                  Match Reports & Scorecards
                </span>
                <ArrowUpRight className="w-3.5 h-3.5 text-slate-500" />
              </button>
              <button
                onClick={() => navigate('/system')}
                className="w-full text-xs py-2 px-3 border border-navy-700 hover:border-emerald-500/40 rounded-lg text-slate-300 hover:text-slate-100 hover:bg-navy-800/60 transition-all flex items-center justify-between"
              >
                <span className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  System Diagnostics & GPU
                </span>
                <ArrowUpRight className="w-3.5 h-3.5 text-slate-500" />
              </button>
            </div>
          </div>

          {/* Real-time Score Activity Ticker */}
          <div className="glass-card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-400" />
                Live Score Stream
              </h2>
              <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 flex items-center gap-1 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live Feeds
              </span>
            </div>
            
            {recentScores.length > 0 ? (
              <div className="space-y-2">
                {recentScores.map((sc) => (
                  <div
                    key={sc.id}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-navy-900/60 border border-navy-700/50 text-xs hover:border-navy-600 transition-colors"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className={cn(
                        'w-7 h-7 rounded-lg flex items-center justify-center font-black font-mono text-xs border',
                        sc.points === 10
                          ? 'bg-gold-500/20 text-gold-400 border-gold-500/40'
                          : sc.points >= 8
                          ? 'bg-red-500/20 text-red-400 border-red-500/40'
                          : 'bg-blue-500/20 text-blue-400 border-blue-500/40'
                      )}>
                        {sc.points}
                      </div>
                      <div>
                        <p className="font-semibold text-slate-200">{sc.archer_name}</p>
                        <p className="text-[10px] text-slate-400">
                          Lane {sc.lane_number} · Round {sc.round} · Arrow {sc.arrow_number}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      {sc.confidence > 0 ? (
                        <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                          AI Conf: {Math.round(sc.confidence * 100)}%
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-400">Scorer Entry</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-6 text-center text-slate-500 text-xs">
                Waiting for incoming arrow impacts...
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Interactive Modals */}
      <TournamentsModal
        isOpen={isTournamentsOpen}
        onClose={() => setIsTournamentsOpen(false)}
        tournaments={tournaments}
      />

      <SessionsModal
        isOpen={isSessionsOpen}
        onClose={() => setIsSessionsOpen(false)}
        sessions={allSessions}
        tournaments={tournaments}
      />

      <ArchersModal
        isOpen={isArchersOpen}
        onClose={() => setIsArchersOpen(false)}
        archers={leaderboard}
        sessionName={selectedTournament?.name}
      />

      <ArcherDetailModal
        isOpen={!!selectedArcherForDetail}
        onClose={() => setSelectedArcherForDetail(null)}
        archer={selectedArcherForDetail}
        tournamentName={selectedTournament?.name}
      />
    </div>
  )
}
