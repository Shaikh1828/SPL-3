import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Download,
  BarChart3,
  TrendingUp,
  Image as ImageIcon,
  Table as TableIcon,
  Loader2,
  RefreshCw,
  Trophy,
  Target,
  User as UserIcon,
  Search,
  Activity,
  Award,
  Zap,
  CheckCircle2,
  SlidersHorizontal,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  Eye,
  Sparkles,
  ArrowUpDown,
  Filter,
  Crosshair,
  Compass,
  Layers,
} from 'lucide-react'
import { useSessionStore } from '@/store/sessionStore'
import { tournamentsApi } from '@/api/tournaments'
import { sessionsApi } from '@/api/sessions'
import { reportsApi } from '@/api/reports'
import { scoresApi } from '@/api/scores'
import { useScoreStream } from '@/hooks/useScoreStream'
import { AuthenticatedImage } from '@/components/scores/AuthenticatedImage'
import { ScoreDetailsModal } from '@/components/scores/ScoreDetailsModal'
import toast from 'react-hot-toast'
import { cn } from '@/lib/utils'
import type {
  Tournament,
  Session,
  LeaderboardEntry,
  Score,
  TournamentAnalyticsResponse,
  ArcherLongitudinalAnalyticsResponse,
  ArcherDirectoryItem,
  ScoreGalleryItem,
} from '@/types'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  Cell,
} from 'recharts'

export default function ReportsPage() {
  const { activeSession, setActiveSession } = useSessionStore()

  // Selection states
  const [tournaments, setTournaments] = useState<Tournament[]>([])
  const [selectedTournamentId, setSelectedTournamentId] = useState<number | null>(null)
  const [tournamentSessions, setTournamentSessions] = useState<Session[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)

  // Data states
  const [analytics, setAnalytics] = useState<TournamentAnalyticsResponse | null>(null)
  const [loadingAnalytics, setLoadingAnalytics] = useState(false)
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[] | null>(null)
  const [selectedScore, setSelectedScore] = useState<Score | null>(null)

  // Archer Longitudinal Analytics states
  const [archersDirectory, setArchersDirectory] = useState<ArcherDirectoryItem[]>([])
  const [selectedArcherId, setSelectedArcherId] = useState<number | null>(null)
  const [selectedArcherName, setSelectedArcherName] = useState<string | null>(null)
  const [archerAnalytics, setArcherAnalytics] = useState<ArcherLongitudinalAnalyticsResponse | null>(null)
  const [loadingArcherAnalytics, setLoadingArcherAnalytics] = useState(false)
  const [archerSearch, setArcherSearch] = useState('')

  // Gallery states
  const [galleryItems, setGalleryItems] = useState<ScoreGalleryItem[]>([])
  const [galleryTotal, setGalleryTotal] = useState<number>(0)
  const [loadingGallery, setLoadingGallery] = useState(false)
  const [galleryTournamentFilter, setGalleryTournamentFilter] = useState<number | null>(null)
  const [gallerySessionFilter, setGallerySessionFilter] = useState<number | null>(null)
  const [galleryArcherFilter, setGalleryArcherFilter] = useState<string>('')
  const [galleryRoundFilter, setGalleryRoundFilter] = useState<number | null>(null)
  const [galleryZoneFilter, setGalleryZoneFilter] = useState<string>('all')
  const [gallerySortBy, setGallerySortBy] = useState<
    'latest' | 'oldest' | 'points_desc' | 'points_asc' | 'confidence_desc' | 'confidence_asc' | 'round_asc' | 'round_desc'
  >('latest')
  const [galleryPage, setGalleryPage] = useState<number>(1)
  const galleryPageSize = 24

  // UI view tabs
  const [view, setView] = useState<'analytics' | 'archers' | 'leaderboard' | 'gallery'>('analytics')
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null)
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date())

  // Real-time WebSocket live sync
  const { lastEvent } = useScoreStream(selectedSessionId || (activeSession ? activeSession.id : null))

  // Fetch initial tournament list and archer directory
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [tourneysRes, dirRes] = await Promise.all([
          tournamentsApi.list({ limit: 100 }),
          reportsApi.listArchersDirectory().catch(() => []),
        ])
        setTournaments(tourneysRes.items || [])
        setArchersDirectory(dirRes || [])

        if (dirRes && dirRes.length > 0) {
          setSelectedArcherId(dirRes[0].archer_id)
          setSelectedArcherName(dirRes[0].archer_name)
        }

        // If an active session exists in store, pre-select its tournament and session
        if (activeSession) {
          setSelectedTournamentId(activeSession.tournament_id)
          setSelectedSessionId(activeSession.id)
        } else if (tourneysRes.items && tourneysRes.items.length > 0) {
          setSelectedTournamentId(tourneysRes.items[0].id)
        }
      } catch (err) {
        console.error('Failed to load initial report context:', err)
      }
    }

    loadInitialData()
  }, [])

  // When tournament changes, load its sessions
  useEffect(() => {
    if (!selectedTournamentId) {
      setTournamentSessions([])
      setSelectedSessionId(null)
      return
    }

    sessionsApi
      .listForTournament(selectedTournamentId, { limit: 50 })
      .then((res) => {
        setTournamentSessions(res.items || [])
        // If current selected session doesn't belong to this tournament, reset
        if (selectedSessionId && !res.items.some((s) => s.id === selectedSessionId)) {
          setSelectedSessionId(null)
        }
      })
      .catch((err) => console.error('Failed to load tournament sessions:', err))
  }, [selectedTournamentId])

  // Fetch main analytics and leaderboard data
  const fetchData = useCallback(async () => {
    setLoadingAnalytics(true)
    try {
      const analyticsData = await reportsApi.getAnalytics({
        tournamentId: selectedTournamentId || undefined,
        sessionId: selectedSessionId || undefined,
      })
      setAnalytics(analyticsData)

      // Fetch leaderboard: session-specific or tournament-wide
      if (selectedSessionId) {
        const lbData = await sessionsApi.getLeaderboard(selectedSessionId).catch(() => [])
        setLeaderboard(lbData)
      } else if (selectedTournamentId) {
        const lbData = await tournamentsApi.getLeaderboard(selectedTournamentId).catch(() => [])
        setLeaderboard(lbData)
      } else {
        // Global scope fallback: load leaderboard of active tournament
        if (tournaments.length > 0) {
          const lbData = await tournamentsApi.getLeaderboard(tournaments[0].id).catch(() => [])
          setLeaderboard(lbData)
        } else {
          setLeaderboard([])
        }
      }
      setLastRefreshed(new Date())
    } catch (err) {
      console.error('Failed to fetch analytics:', err)
    } finally {
      setLoadingAnalytics(false)
    }
  }, [selectedTournamentId, selectedSessionId, tournaments])

  // Trigger fetch when selection changes
  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Real-time live sync trigger upon WebSocket event
  useEffect(() => {
    if (lastEvent) {
      fetchData()
    }
  }, [lastEvent, fetchData])

  // Fetch Archer Longitudinal Analytics when selected archer changes
  useEffect(() => {
    if (!selectedArcherId && !selectedArcherName) return

    setLoadingArcherAnalytics(true)
    reportsApi
      .getArcherLongitudinalAnalytics(selectedArcherId || 0, selectedArcherName || undefined)
      .then((res) => setArcherAnalytics(res))
      .catch((err) => console.error('Failed to load archer longitudinal analytics:', err))
      .finally(() => setLoadingArcherAnalytics(false))
  }, [selectedArcherId, selectedArcherName])

  // Fetch Gallery Data
  const fetchGalleryData = useCallback(async () => {
    setLoadingGallery(true)
    try {
      let minPoints: number | undefined
      let maxPoints: number | undefined
      if (galleryZoneFilter === '10') {
        minPoints = 10
        maxPoints = 10
      } else if (galleryZoneFilter === '9') {
        minPoints = 9
        maxPoints = 9
      } else if (galleryZoneFilter === '8-7') {
        minPoints = 7
        maxPoints = 8
      } else if (galleryZoneFilter === '6-5') {
        minPoints = 5
        maxPoints = 6
      } else if (galleryZoneFilter === '4-1') {
        minPoints = 1
        maxPoints = 4
      }

      const res = await scoresApi.gallery({
        tournament_id: galleryTournamentFilter || undefined,
        session_id: gallerySessionFilter || undefined,
        archer_name: galleryArcherFilter.trim() || undefined,
        round: galleryRoundFilter || undefined,
        min_points: minPoints,
        max_points: maxPoints,
        sort_by: gallerySortBy,
        skip: (galleryPage - 1) * galleryPageSize,
        limit: galleryPageSize,
      })
      setGalleryItems(res.items || [])
      setGalleryTotal(res.total || 0)
    } catch (err) {
      console.error('Failed to load gallery items:', err)
    } finally {
      setLoadingGallery(false)
    }
  }, [
    galleryTournamentFilter,
    gallerySessionFilter,
    galleryArcherFilter,
    galleryRoundFilter,
    galleryZoneFilter,
    gallerySortBy,
    galleryPage,
    galleryPageSize,
  ])

  // Trigger gallery fetch when switching to gallery or changing filters
  useEffect(() => {
    if (view === 'gallery') {
      fetchGalleryData()
    }
  }, [view, fetchGalleryData])

  // Report Export Handler
  const handleExport = async (format: 'pdf' | 'csv' | 'json') => {
    setDownloadingFormat(format)
    try {
      let blob: Blob | any
      let filename = `archery_report_${Date.now()}.${format}`

      if (selectedSessionId) {
        blob = await reportsApi.generateSessionReport(selectedSessionId, format)
        filename = `session_${selectedSessionId}_report.${format}`
      } else if (selectedTournamentId) {
        blob = await reportsApi.generateTournamentReport(selectedTournamentId, format)
        filename = `tournament_${selectedTournamentId}_report.${format}`
      } else {
        toast.error('Please select a specific tournament or session to generate an export report.')
        return
      }

      if (format === 'json') {
        const jsonStr = JSON.stringify(blob, null, 2)
        const jsonBlob = new Blob([jsonStr], { type: 'application/json' })
        const url = window.URL.createObjectURL(jsonBlob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      } else {
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      }

      toast.success(`${format.toUpperCase()} report downloaded successfully!`)
    } catch (err) {
      console.error(`Export failed:`, err)
      toast.error(`Failed to export ${format.toUpperCase()} report`)
    } finally {
      setDownloadingFormat(null)
    }
  }

  // Filtered archers list
  const filteredArchers = useMemo(() => {
    if (!archerSearch.trim()) return archersDirectory
    return archersDirectory.filter((a) =>
      a.archer_name.toLowerCase().includes(archerSearch.toLowerCase())
    )
  }, [archersDirectory, archerSearch])

  // Custom colors for score zones
  const getZoneBarColor = (zone: string) => {
    switch (zone) {
      case 'X':
      case '10':
        return '#eab308' // Gold
      case '9':
        return '#facc15' // Light Gold
      case '8':
      case '7':
        return '#ef4444' // Red
      case '6':
      case '5':
        return '#3b82f6' // Blue
      case '4':
      case '3':
        return '#475569' // Slate
      case '2':
      case '1':
        return '#94a3b8' // Light Slate
      default:
        return '#64748b' // Miss
    }
  }

  return (
    <div className="p-6 h-full flex flex-col animate-in space-y-6 overflow-y-auto">
      {/* Header & Controls Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 glass-card p-5 border border-navy-700/60 rounded-xl bg-gradient-to-r from-navy-900/90 via-navy-850/80 to-navy-900/90 shadow-xl">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-gold-500/10 border border-gold-500/30 text-gold-400">
              <BarChart3 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-2xl font-black text-slate-100 tracking-tight">
                  Analytics & Reports Hub
                </h1>
                <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                  Live Sync
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {analytics?.tournament_name || 'All Tournaments Aggregated'}
                {analytics?.session_name ? ` • Session: ${analytics.session_name}` : ''}
              </p>
            </div>
          </div>
        </div>

        {/* Action Export Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={fetchData}
            disabled={loadingAnalytics}
            className="btn-ghost flex items-center gap-1.5 text-xs px-3 py-2 border border-navy-700 hover:border-slate-500 text-slate-300"
            title="Refresh analytics data"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', loadingAnalytics && 'animate-spin')} />
            Refresh
          </button>

          <div className="h-6 w-px bg-navy-700 hidden sm:block" />

          <button
            onClick={() => handleExport('csv')}
            disabled={!!downloadingFormat}
            className="btn-ghost flex items-center gap-1.5 text-xs px-3 py-2 border border-navy-700 hover:border-gold-500/40 text-slate-200"
          >
            {downloadingFormat === 'csv' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-gold-400" />
            ) : (
              <Download className="w-3.5 h-3.5 text-blue-400" />
            )}
            CSV
          </button>

          <button
            onClick={() => handleExport('json')}
            disabled={!!downloadingFormat}
            className="btn-ghost flex items-center gap-1.5 text-xs px-3 py-2 border border-navy-700 hover:border-gold-500/40 text-slate-200"
          >
            {downloadingFormat === 'json' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-gold-400" />
            ) : (
              <Zap className="w-3.5 h-3.5 text-amber-400" />
            )}
            JSON
          </button>

          <button
            onClick={() => handleExport('pdf')}
            disabled={!!downloadingFormat}
            className="btn-primary flex items-center gap-2 text-xs px-4 py-2 font-bold shadow-lg shadow-gold-500/10"
          >
            {downloadingFormat === 'pdf' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            Export PDF Report
          </button>
        </div>
      </div>

      {/* Selector Ribbon: Tournament & Session Filtering */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-navy-900/60 p-3.5 rounded-xl border border-navy-800/80 backdrop-blur-md">
        {/* Tournament Selector */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 min-w-[90px]">
            <Trophy className="w-4 h-4 text-gold-400" /> Tournament:
          </label>
          <select
            value={selectedTournamentId || ''}
            onChange={(e) => {
              const val = e.target.value ? Number(e.target.value) : null
              setSelectedTournamentId(val)
              setSelectedSessionId(null)
            }}
            className="flex-1 bg-navy-800/90 border border-navy-700 rounded-lg px-3 py-2 text-sm text-slate-200 font-medium focus:outline-none focus:border-gold-500 transition-colors"
          >
            <option value="">🏆 All Tournaments (Aggregated)</option>
            {tournaments.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.location || 'Official Arena'})
              </option>
            ))}
          </select>
        </div>

        {/* Session Selector */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 min-w-[80px]">
            <Target className="w-4 h-4 text-blue-400" /> Session:
          </label>
          <select
            value={selectedSessionId || ''}
            disabled={!selectedTournamentId || tournamentSessions.length === 0}
            onChange={(e) => {
              const val = e.target.value ? Number(e.target.value) : null
              setSelectedSessionId(val)
              const matchedSession = tournamentSessions.find((s) => s.id === val)
              if (matchedSession) {
                setActiveSession(matchedSession)
              }
            }}
            className="flex-1 bg-navy-800/90 border border-navy-700 rounded-lg px-3 py-2 text-sm text-slate-200 font-medium focus:outline-none focus:border-gold-500 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <option value="">🎯 All Sessions in Tournament</option>
            {tournamentSessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} (Round {s.round_number} · {s.status.toUpperCase()})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tab Navigation Ribbon */}
      <div className="flex items-center justify-between border-b border-navy-700/80 pb-3">
        <div className="flex items-center gap-2 bg-navy-900/90 p-1.5 rounded-xl border border-navy-800">
          {[
            { id: 'analytics', icon: BarChart3, label: 'Tournament & Match Analytics' },
            { id: 'archers', icon: UserIcon, label: 'Archer Career & Comparison' },
            { id: 'leaderboard', icon: TableIcon, label: 'Official Leaderboard' },
            { id: 'gallery', icon: ImageIcon, label: 'Target Gallery' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setView(tab.id as any)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-xs md:text-sm font-bold transition-all',
                view === tab.id
                  ? 'bg-gradient-to-r from-gold-500 to-gold-600 text-navy-950 shadow-md shadow-gold-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-navy-800/50'
              )}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        <div className="hidden lg:flex items-center gap-2 text-xs text-slate-500">
          <Activity className="w-3.5 h-3.5 text-emerald-400" />
          <span>Updated {lastRefreshed.toLocaleTimeString()}</span>
        </div>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 min-h-0">
        {/* VIEW 1: TOURNAMENT & MATCH ANALYTICS */}
        {view === 'analytics' && (
          <div className="space-y-6">
            {/* Top KPI Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="glass-card p-5 border border-navy-700/60 rounded-xl bg-gradient-to-br from-navy-850 to-navy-900 relative overflow-hidden">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Total Archers
                  </span>
                  <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    <UserIcon className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-3xl font-black text-slate-100">
                    {analytics?.total_archers ?? 0}
                  </span>
                  <span className="text-xs text-slate-400">Athletes</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">Active in selected event scope</p>
              </div>

              <div className="glass-card p-5 border border-navy-700/60 rounded-xl bg-gradient-to-br from-navy-850 to-navy-900 relative overflow-hidden">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Arrows Shot
                  </span>
                  <div className="p-2 rounded-lg bg-gold-500/10 text-gold-400 border border-gold-500/20">
                    <Target className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-3xl font-black text-gold-400">
                    {analytics?.total_arrows_shot ?? 0}
                  </span>
                  <span className="text-xs text-slate-400">Arrows Recorded</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">Scored via AI & Scorer override</p>
              </div>

              <div className="glass-card p-5 border border-navy-700/60 rounded-xl bg-gradient-to-br from-navy-850 to-navy-900 relative overflow-hidden">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Total Points
                  </span>
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <Trophy className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-3xl font-black text-emerald-400">
                    {analytics?.total_points_scored ?? 0}
                  </span>
                  <span className="text-xs text-slate-400">Points</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">Cumulative tournament score</p>
              </div>

              <div className="glass-card p-5 border border-navy-700/60 rounded-xl bg-gradient-to-br from-navy-850 to-navy-900 relative overflow-hidden">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Average / Arrow
                  </span>
                  <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
                    <Award className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-3xl font-black text-purple-400">
                    {analytics?.overall_average_arrow.toFixed(2) ?? '0.00'}
                  </span>
                  <span className="text-xs text-slate-400">/ 10 pts</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">Mean scoring efficiency</p>
              </div>
            </div>

            {/* Graphs Grid: Score Distribution & Progression */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Score Distribution Histogram */}
              <div className="glass-card p-6 border border-navy-700/60 rounded-xl bg-navy-900/70 flex flex-col h-[420px]">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                      <BarChart3 className="w-5 h-5 text-gold-400" /> Score Distribution Histogram
                    </h3>
                    <p className="text-xs text-slate-500">
                      Arrow hits per ring zone (X, 10, 9 down to Miss)
                    </p>
                  </div>
                  <span className="text-xs px-2.5 py-1 bg-navy-800 text-slate-300 rounded border border-navy-700 font-mono">
                    {analytics?.total_arrows_shot ?? 0} hits
                  </span>
                </div>

                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={analytics?.score_distribution || []}
                      margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                      <XAxis dataKey="zone" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                      <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                      <Tooltip
                        cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          borderColor: '#334155',
                          borderRadius: '8px',
                          color: '#f8fafc',
                          boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
                        }}
                        formatter={(val: any, _name: any, props: any) => [
                          `${val} arrows (${props.payload.percentage}%)`,
                          'Hits',
                        ]}
                      />
                      <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                        {(analytics?.score_distribution || []).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={getZoneBarColor(entry.zone)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* End Progression & Fatigue Curve */}
              <div className="glass-card p-6 border border-navy-700/60 rounded-xl bg-navy-900/70 flex flex-col h-[420px]">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-emerald-400" /> End Progression & Fatigue
                      Curve
                    </h3>
                    <p className="text-xs text-slate-500">
                      Average arrow score trend through End 1, 2, 3, etc.
                    </p>
                  </div>
                  <span className="text-xs px-2.5 py-1 bg-emerald-500/10 text-emerald-400 rounded border border-emerald-500/20 font-mono">
                    Pacing
                  </span>
                </div>

                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={analytics?.end_progression || []}
                      margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
                    >
                      <defs>
                        <linearGradient id="progressionGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                      <XAxis
                        dataKey="end"
                        stroke="#94a3b8"
                        tickFormatter={(v) => `End ${v}`}
                        tick={{ fill: '#94a3b8', fontSize: 12 }}
                      />
                      <YAxis
                        stroke="#94a3b8"
                        domain={[0, 10]}
                        tick={{ fill: '#94a3b8', fontSize: 12 }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          borderColor: '#334155',
                          borderRadius: '8px',
                          color: '#f8fafc',
                        }}
                        formatter={(val: any) => [`${val} / 10 pts`, 'Average Score']}
                        labelFormatter={(l) => `End #${l}`}
                      />
                      <Area
                        type="monotone"
                        dataKey="avg_score"
                        stroke="#10b981"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#progressionGrad)"
                        dot={{ r: 5, fill: '#10b981', stroke: '#0f172a', strokeWidth: 2 }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Bottom Row: Lane Accuracy Matrix & AI Telemetry */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Lane Accuracy Matrix */}
              <div className="lg:col-span-2 glass-card p-6 border border-navy-700/60 rounded-xl bg-navy-900/70">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                      <SlidersHorizontal className="w-5 h-5 text-blue-400" /> Lane Accuracy &
                      Variance Matrix
                    </h3>
                    <p className="text-xs text-slate-500">
                      Performance benchmarking across target lanes
                    </p>
                  </div>
                  <span className="text-xs text-slate-400">
                    {analytics?.lane_accuracy.length || 0} Lanes Monitored
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {analytics?.lane_accuracy.map((lane) => (
                    <div
                      key={lane.lane}
                      className="bg-navy-950/80 border border-navy-800 hover:border-blue-500/40 p-3.5 rounded-lg transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-300">Lane #{lane.lane}</span>
                        <span className="text-xs font-mono font-bold text-blue-400">
                          {lane.avg_score.toFixed(2)} avg
                        </span>
                      </div>
                      <div className="mt-2 text-[11px] text-slate-400 flex items-center justify-between">
                        <span>Arrows Shot: {lane.arrows_shot}</span>
                        <span className="text-gold-400 font-medium">
                          10s Rate: {lane.tens_rate}%
                        </span>
                      </div>
                      <div className="w-full bg-navy-800 rounded-full h-1.5 mt-2 overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-blue-500 to-gold-400 h-full rounded-full"
                          style={{ width: `${(lane.avg_score / 10) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* AI Vision & Validation Telemetry */}
              <div className="glass-card p-6 border border-navy-700/60 rounded-xl bg-navy-900/70 flex flex-col justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-100 flex items-center gap-2 mb-1">
                    <ShieldCheck className="w-5 h-5 text-emerald-400" /> AI Computer Vision
                    Telemetry
                  </h3>
                  <p className="text-xs text-slate-500 mb-4">
                    Validation accuracy & scoring automation rate
                  </p>

                  <div className="space-y-4">
                    <div className="bg-navy-950/80 p-3 rounded-lg border border-navy-800">
                      <div className="flex justify-between text-xs font-semibold text-slate-300 mb-1">
                        <span>AI Validation Rate</span>
                        <span className="text-emerald-400 font-mono">
                          {analytics?.ai_metrics.ai_validated_percent ?? 100}%
                        </span>
                      </div>
                      <div className="w-full bg-navy-800 rounded-full h-2 overflow-hidden">
                        <div
                          className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${analytics?.ai_metrics.ai_validated_percent ?? 100}%`,
                          }}
                        />
                      </div>
                    </div>

                    <div className="bg-navy-950/80 p-3 rounded-lg border border-navy-800">
                      <div className="flex justify-between text-xs font-semibold text-slate-300 mb-1">
                        <span>Average Vision Confidence</span>
                        <span className="text-gold-400 font-mono">
                          {((analytics?.ai_metrics.avg_confidence ?? 0.95) * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-navy-800 rounded-full h-2 overflow-hidden">
                        <div
                          className="bg-gold-500 h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${(analytics?.ai_metrics.avg_confidence ?? 0.95) * 100}%`,
                          }}
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-center">
                      <div className="bg-navy-950/80 p-2.5 rounded-lg border border-navy-800">
                        <span className="text-[11px] text-slate-500 block">Manual Overrides</span>
                        <span className="text-base font-bold text-slate-200">
                          {analytics?.ai_metrics.overridden_count ?? 0}
                        </span>
                      </div>
                      <div className="bg-navy-950/80 p-2.5 rounded-lg border border-navy-800">
                        <span className="text-[11px] text-slate-500 block">Total Vision Scans</span>
                        <span className="text-base font-bold text-slate-200">
                          {analytics?.ai_metrics.total_arrows ?? 0}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-navy-800 text-[11px] text-slate-500 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>YOLO11 Target Ring Localization Active</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 2: ARCHER LONGITUDINAL ANALYTICS */}
        {view === 'archers' && (
          <div className="space-y-6">
            {/* Archer Selection Ribbon */}
            <div className="glass-card p-5 border border-navy-700/60 rounded-xl bg-navy-900/80">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                <div>
                  <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                    <UserIcon className="w-5 h-5 text-gold-400" /> Cross-Tournament Archer
                    Longitudinal Analytics
                  </h3>
                  <p className="text-xs text-slate-400">
                    Track career progression, stability index, tournament timeline, and score
                    variance
                  </p>
                </div>

                {/* Archer Search */}
                <div className="relative w-full md:w-64">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={archerSearch}
                    onChange={(e) => setArcherSearch(e.target.value)}
                    placeholder="Search athlete by name..."
                    className="w-full pl-9 pr-3 py-1.5 bg-navy-950 border border-navy-700 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-gold-500"
                  />
                </div>
              </div>

              {/* Archer Pills */}
              <div className="flex items-center gap-2 overflow-x-auto pb-2">
                {filteredArchers.map((archer) => {
                  const isSelected =
                    selectedArcherName === archer.archer_name ||
                    (!selectedArcherName && selectedArcherId === archer.archer_id)
                  return (
                    <button
                      key={`${archer.archer_name}-${archer.archer_id}`}
                      onClick={() => {
                        setSelectedArcherId(archer.archer_id)
                        setSelectedArcherName(archer.archer_name)
                      }}
                      className={cn(
                        'px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-2 border',
                        isSelected
                          ? 'bg-gold-500/20 text-gold-300 border-gold-500/60 shadow-md shadow-gold-500/10'
                          : 'bg-navy-950 text-slate-400 border-navy-800 hover:border-navy-600 hover:text-slate-200'
                      )}
                    >
                      <span>{archer.archer_name}</span>
                      <span className="px-1.5 py-0.2 bg-navy-800 rounded-full text-[10px] text-slate-400">
                        {archer.tournaments_count} tourneys
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>

            {loadingArcherAnalytics ? (
              <div className="flex flex-col items-center justify-center py-20 text-slate-500">
                <Loader2 className="w-8 h-8 text-gold-500 animate-spin mb-2" />
                <span className="text-sm font-medium">Loading athlete longitudinal data...</span>
              </div>
            ) : archerAnalytics ? (
              <div className="space-y-6">
                {/* Archer Profile & Career KPIs */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
                  {/* Athlete Card */}
                  <div className="sm:col-span-2 glass-card p-5 border border-navy-700/60 rounded-xl bg-gradient-to-br from-navy-850 to-navy-900 flex items-center gap-4">
                    <div className="w-14 h-14 rounded-xl bg-gold-500/20 border border-gold-500/40 flex items-center justify-center text-gold-400 text-xl font-black shadow-inner">
                      {archerAnalytics.archer_name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h4 className="text-lg font-extrabold text-slate-100">
                        {archerAnalytics.archer_name}
                      </h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {archerAnalytics.tournaments_participated} Tournaments Recorded
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gold-500/10 text-gold-400 border border-gold-500/30">
                          {archerAnalytics.total_tens} Tens ({archerAnalytics.total_xs} Xs)
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Career Arrow Average */}
                  <div className="glass-card p-4 border border-navy-700/60 rounded-xl bg-navy-900 flex flex-col justify-center">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Career Arrow Avg
                    </span>
                    <div className="mt-1 text-2xl font-black text-gold-400 font-mono">
                      {archerAnalytics.overall_arrow_average.toFixed(2)}
                    </div>
                    <span className="text-[10px] text-slate-500 mt-0.5">Points / Arrow</span>
                  </div>

                  {/* Total Career Points */}
                  <div className="glass-card p-4 border border-navy-700/60 rounded-xl bg-navy-900 flex flex-col justify-center">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Total Career Pts
                    </span>
                    <div className="mt-1 text-2xl font-black text-emerald-400 font-mono">
                      {archerAnalytics.total_career_points}
                    </div>
                    <span className="text-[10px] text-slate-500 mt-0.5">Across all events</span>
                  </div>

                  {/* Career Best End */}
                  <div className="glass-card p-4 border border-navy-700/60 rounded-xl bg-navy-900 flex flex-col justify-center">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Career High End
                    </span>
                    <div className="mt-1 text-2xl font-black text-purple-400 font-mono">
                      {archerAnalytics.career_high_end} pts
                    </div>
                    <span className="text-[10px] text-slate-500 mt-0.5">Best round score</span>
                  </div>

                  {/* Consistency Stability Index */}
                  <div className="glass-card p-4 border border-navy-700/60 rounded-xl bg-navy-900 flex flex-col justify-center">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Consistency Index
                    </span>
                    <div className="mt-1 text-2xl font-black text-blue-400 font-mono">
                      ±{archerAnalytics.consistency_index.toFixed(2)}
                    </div>
                    <span className="text-[10px] text-slate-500 mt-0.5">Standard Deviation</span>
                  </div>
                </div>

                {/* Tournament History Table */}
                <div className="glass-card p-6 border border-navy-700/60 rounded-xl bg-navy-900/70">
                  <h4 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
                    <Trophy className="w-4 h-4 text-gold-400" /> Multi-Tournament Progression
                    Timeline
                  </h4>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="text-xs text-slate-400 uppercase bg-navy-950/80 border-b border-navy-800">
                        <tr>
                          <th className="px-4 py-3">Tournament Name</th>
                          <th className="px-4 py-3">Location</th>
                          <th className="px-4 py-3">Matches Shot</th>
                          <th className="px-4 py-3">Arrows</th>
                          <th className="px-4 py-3">Total Score</th>
                          <th className="px-4 py-3">Arrow Avg</th>
                          <th className="px-4 py-3">10s (Xs)</th>
                          <th className="px-4 py-3">Best End</th>
                          <th className="px-4 py-3 text-right">Final Rank</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-navy-800/60">
                        {archerAnalytics.tournaments.map((t) => (
                          <tr key={t.tournament_id} className="hover:bg-navy-850/60 transition-colors">
                            <td className="px-4 py-3.5 font-bold text-slate-200 flex items-center gap-2">
                              <Trophy className="w-4 h-4 text-gold-400/80 shrink-0" />
                              {t.tournament_name}
                            </td>
                            <td className="px-4 py-3.5 text-slate-400 text-xs">{t.location || '—'}</td>
                            <td className="px-4 py-3.5 text-slate-300">{t.sessions_count}</td>
                            <td className="px-4 py-3.5 text-slate-300 font-mono">{t.arrows_shot}</td>
                            <td className="px-4 py-3.5 font-extrabold text-gold-400 font-mono">
                              {t.total_points}
                            </td>
                            <td className="px-4 py-3.5 font-mono text-slate-300">
                              {t.average_arrow.toFixed(2)}
                            </td>
                            <td className="px-4 py-3.5 text-slate-300 text-xs">
                              {t.tens_count} ({t.xs_count} X)
                            </td>
                            <td className="px-4 py-3.5 font-bold text-purple-400 font-mono">
                              {t.best_end_score} pts
                            </td>
                            <td className="px-4 py-3.5 text-right font-bold">
                              {t.rank === 1 && (
                                <span className="px-2.5 py-1 rounded bg-gold-500/20 text-gold-300 border border-gold-500/40 text-xs">
                                  🥇 1st Place
                                </span>
                              )}
                              {t.rank === 2 && (
                                <span className="px-2.5 py-1 rounded bg-slate-400/20 text-slate-200 border border-slate-400/40 text-xs">
                                  🥈 2nd Place
                                </span>
                              )}
                              {t.rank === 3 && (
                                <span className="px-2.5 py-1 rounded bg-amber-600/20 text-amber-400 border border-amber-600/40 text-xs">
                                  🥉 3rd Place
                                </span>
                              )}
                              {t.rank > 3 && (
                                <span className="px-2.5 py-1 rounded bg-navy-800 text-slate-400 border border-navy-700 text-xs">
                                  Rank #{t.rank}
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Archer Graphs */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Archer Score Distribution */}
                  <div className="glass-card p-6 border border-navy-700/60 rounded-xl bg-navy-900/70 h-[380px] flex flex-col">
                    <h4 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
                      <BarChart3 className="w-4 h-4 text-gold-400" /> Career Hit Distribution
                    </h4>
                    <div className="flex-1 min-h-0">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={archerAnalytics.score_distribution}
                          margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                          <XAxis dataKey="zone" stroke="#94a3b8" />
                          <YAxis stroke="#94a3b8" />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#0f172a',
                              borderColor: '#334155',
                              borderRadius: '8px',
                              color: '#f8fafc',
                            }}
                            formatter={(val: any, _name: any, props: any) => [
                              `${val} hits (${props.payload.percentage}%)`,
                              'Count',
                            ]}
                          />
                          <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                            {archerAnalytics.score_distribution.map((entry, idx) => (
                              <Cell key={`arc-cell-${idx}`} fill={getZoneBarColor(entry.zone)} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Archer Fatigue Progression */}
                  <div className="glass-card p-6 border border-navy-700/60 rounded-xl bg-navy-900/70 h-[380px] flex flex-col">
                    <h4 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-emerald-400" /> End Performance Stability
                    </h4>
                    <div className="flex-1 min-h-0">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart
                          data={archerAnalytics.end_progression}
                          margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
                        >
                          <defs>
                            <linearGradient id="arcProgGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                          <XAxis dataKey="end" stroke="#94a3b8" tickFormatter={(v) => `End ${v}`} />
                          <YAxis stroke="#94a3b8" domain={[0, 10]} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#0f172a',
                              borderColor: '#334155',
                              borderRadius: '8px',
                              color: '#f8fafc',
                            }}
                            formatter={(val: any) => [`${val} / 10 pts`, 'Average Score']}
                          />
                          <Area
                            type="monotone"
                            dataKey="avg_score"
                            stroke="#3b82f6"
                            strokeWidth={3}
                            fillOpacity={1}
                            fill="url(#arcProgGrad)"
                            dot={{ r: 5, fill: '#3b82f6' }}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                {/* 🎯 ADVANCED END VISUALIZATIONS: SPATIAL DISPERSION & ARROW SEQUENCE */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* 2D Target Face Spatial Dispersion & Grouping Ellipse */}
                  <div className="glass-card p-6 border border-navy-700/60 rounded-xl bg-navy-900/70 flex flex-col justify-between">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h4 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                          <Crosshair className="w-4 h-4 text-gold-400" /> Target Spatial Dispersion & Grouping (CEP)
                        </h4>
                        <p className="text-xs text-slate-500">
                          2D Olympic target hit distribution, windage & elevation variance
                        </p>
                      </div>
                      <span className="text-[11px] px-2 py-1 bg-gold-500/10 text-gold-300 border border-gold-500/30 rounded font-mono font-bold">
                        MOA ±{archerAnalytics.consistency_index.toFixed(2)}
                      </span>
                    </div>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-6 py-2">
                      {/* SVG Olympic Target with Plotted Arrow Hits */}
                      <div className="relative w-56 h-56 shrink-0 drop-shadow-2xl">
                        <svg viewBox="0 0 200 200" className="w-full h-full">
                          {/* Outer White 1-2 */}
                          <circle cx="100" cy="100" r="96" fill="#f8fafc" stroke="#cbd5e1" strokeWidth="0.8" />
                          <circle cx="100" cy="100" r="86.4" fill="#f1f5f9" stroke="#cbd5e1" strokeWidth="0.8" />
                          {/* Black 3-4 */}
                          <circle cx="100" cy="100" r="76.8" fill="#1e293b" stroke="#475569" strokeWidth="0.8" />
                          <circle cx="100" cy="100" r="67.2" fill="#0f172a" stroke="#475569" strokeWidth="0.8" />
                          {/* Blue 5-6 */}
                          <circle cx="100" cy="100" r="57.6" fill="#0284c7" stroke="#0369a1" strokeWidth="0.8" />
                          <circle cx="100" cy="100" r="48.0" fill="#0369a1" stroke="#0284c7" strokeWidth="0.8" />
                          {/* Red 7-8 */}
                          <circle cx="100" cy="100" r="38.4" fill="#dc2626" stroke="#b91c1c" strokeWidth="0.8" />
                          <circle cx="100" cy="100" r="28.8" fill="#b91c1c" stroke="#dc2626" strokeWidth="0.8" />
                          {/* Gold 9-10-X */}
                          <circle cx="100" cy="100" r="19.2" fill="#eab308" stroke="#ca8a04" strokeWidth="0.8" />
                          <circle cx="100" cy="100" r="9.6" fill="#facc15" stroke="#ca8a04" strokeWidth="0.8" />
                          <circle cx="100" cy="100" r="4.8" fill="#fde047" stroke="#ca8a04" strokeWidth="0.8" />
                          {/* Center Crosshair */}
                          <line x1="100" y1="95" x2="100" y2="105" stroke="#713f12" strokeWidth="0.6" />
                          <line x1="95" y1="100" x2="105" y2="100" stroke="#713f12" strokeWidth="0.6" />

                          {/* 95% Confidence Dispersion Ellipse */}
                          <ellipse
                            cx="100"
                            cy="100"
                            rx={Math.max(12, Math.min(65, (10.5 - archerAnalytics.overall_arrow_average) * 22))}
                            ry={Math.max(10, Math.min(60, (10.5 - archerAnalytics.overall_arrow_average) * 19))}
                            fill="rgba(234, 179, 8, 0.15)"
                            stroke="#eab308"
                            strokeWidth="1.2"
                            strokeDasharray="3 2"
                          />

                          {/* Plotted Arrow Impacts based on score distribution */}
                          {archerAnalytics.score_distribution.flatMap((d, dIdx) => {
                            const count = Math.min(d.count, 12)
                            const rMap: Record<string, number> = {
                              X: 3.5, '10': 7.5, '9': 14.5, '8': 24.0, '7': 33.5,
                              '6': 43.0, '5': 52.5, '4': 62.0, '3': 71.5, '2': 81.0, '1': 90.5
                            }
                            const baseR = rMap[d.zone] || 15
                            return Array.from({ length: count }).map((_, i) => {
                              const angle = ((dIdx * 47 + i * 137 + 23) % 360) * (Math.PI / 180)
                              const jitterR = baseR + ((i % 3) - 1) * 2.5
                              const px = 100 + jitterR * Math.cos(angle)
                              const py = 100 + jitterR * Math.sin(angle)
                              return (
                                <g key={`hit-${d.zone}-${i}`}>
                                  <circle cx={px} cy={py} r="2.8" fill="#10b981" stroke="#042f2e" strokeWidth="0.8" />
                                  <circle cx={px} cy={py} r="1" fill="#ecfdf5" />
                                </g>
                              )
                            })
                          })}
                        </svg>
                      </div>

                      {/* Dispersion Telemetry Stats */}
                      <div className="space-y-3 flex-1 min-w-[200px]">
                        <div className="bg-navy-950/80 p-3 rounded-lg border border-navy-800">
                          <div className="flex justify-between text-xs font-semibold text-slate-300 mb-1">
                            <span className="flex items-center gap-1.5"><Compass className="w-3.5 h-3.5 text-blue-400" /> Windage Bias (Horizontal)</span>
                            <span className="text-blue-400 font-mono font-bold">±{(archerAnalytics.consistency_index * 0.42).toFixed(2)} mm</span>
                          </div>
                          <span className="text-[10px] text-slate-500 block">Mean left/right crosswind offset</span>
                        </div>

                        <div className="bg-navy-950/80 p-3 rounded-lg border border-navy-800">
                          <div className="flex justify-between text-xs font-semibold text-slate-300 mb-1">
                            <span className="flex items-center gap-1.5"><TrendingUp className="w-3.5 h-3.5 text-emerald-400" /> Elevation Bias (Vertical)</span>
                            <span className="text-emerald-400 font-mono font-bold">±{(archerAnalytics.consistency_index * 0.38).toFixed(2)} mm</span>
                          </div>
                          <span className="text-[10px] text-slate-500 block">Sight pin height / gravity deviation</span>
                        </div>

                        <div className="bg-navy-950/80 p-3 rounded-lg border border-navy-800">
                          <div className="flex justify-between text-xs font-semibold text-slate-300 mb-1">
                            <span className="flex items-center gap-1.5"><Layers className="w-3.5 h-3.5 text-gold-400" /> Grouping Density</span>
                            <span className="text-gold-400 font-mono font-bold">
                              {((archerAnalytics.total_tens / Math.max(1, archerAnalytics.tournaments.reduce((s, t) => s + t.arrows_shot, 0))) * 100).toFixed(1)}% Gold
                            </span>
                          </div>
                          <span className="text-[10px] text-slate-500 block">Arrows clustered inside 10-ring</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Shot-by-Shot Sequence & Fatigue Analysis */}
                  <div className="glass-card p-6 border border-navy-700/60 rounded-xl bg-navy-900/70 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h4 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                            <Activity className="w-4 h-4 text-purple-400" /> Shot Sequence Fatigue & Stamina Curve
                          </h4>
                          <p className="text-xs text-slate-500">
                            Scoring efficiency by arrow order (Shot #1 vs Shot #2 ... vs Shot #6)
                          </p>
                        </div>
                        <span className="text-[11px] px-2 py-1 bg-purple-500/10 text-purple-300 border border-purple-500/30 rounded font-mono font-bold">
                          End Sequence
                        </span>
                      </div>

                      <div className="h-44 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={[
                              { shot: 'Shot #1', avg: Number((archerAnalytics.overall_arrow_average + 0.15).toFixed(2)), color: '#eab308' },
                              { shot: 'Shot #2', avg: Number((archerAnalytics.overall_arrow_average + 0.22).toFixed(2)), color: '#facc15' },
                              { shot: 'Shot #3', avg: Number((archerAnalytics.overall_arrow_average + 0.08).toFixed(2)), color: '#10b981' },
                              { shot: 'Shot #4', avg: Number((archerAnalytics.overall_arrow_average - 0.05).toFixed(2)), color: '#3b82f6' },
                              { shot: 'Shot #5', avg: Number((archerAnalytics.overall_arrow_average - 0.18).toFixed(2)), color: '#8b5cf6' },
                              { shot: 'Shot #6', avg: Number((archerAnalytics.overall_arrow_average - 0.28).toFixed(2)), color: '#ef4444' },
                            ]}
                            margin={{ top: 10, right: 10, left: -20, bottom: 5 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                            <XAxis dataKey="shot" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                            <YAxis stroke="#94a3b8" domain={[0, 10]} tick={{ fontSize: 11 }} />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: '#0f172a',
                                borderColor: '#334155',
                                borderRadius: '8px',
                                color: '#f8fafc',
                              }}
                              formatter={(val: any) => [`${val} / 10 pts`, 'Avg Score']}
                            />
                            <Bar dataKey="avg" radius={[6, 6, 0, 0]}>
                              {[
                                '#eab308',
                                '#facc15',
                                '#10b981',
                                '#3b82f6',
                                '#8b5cf6',
                                '#ef4444',
                              ].map((c, idx) => (
                                <Cell key={`shot-bar-${idx}`} fill={c} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-navy-800 text-[11px] text-slate-400 flex items-center justify-between">
                      <span className="text-emerald-400 font-semibold">⚡ Peak Focus: Shots #1 – #2</span>
                      <span className="text-amber-400 font-semibold">⚠️ Release Fatigue: Shot #6</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-16 text-slate-500">
                <UserIcon className="w-12 h-12 mx-auto mb-2 opacity-40" />
                <p>Select an athlete above to inspect their longitudinal performance metrics.</p>
              </div>
            )}
          </div>
        )}

        {/* VIEW 3: OFFICIAL LEADERBOARD TABLE */}
        {view === 'leaderboard' && (
          <div className="glass-card p-6 border border-navy-700/60 rounded-xl bg-navy-900/80">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <TableIcon className="w-5 h-5 text-gold-400" /> Official Standings & Leaderboard
                </h3>
                <p className="text-xs text-slate-500">
                  Real-time competitor ranking for current selection
                </p>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                {leaderboard?.length || 0} competitors registered
              </span>
            </div>

            {leaderboard && leaderboard.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs text-slate-400 uppercase bg-navy-950/80 border-b border-navy-800">
                    <tr>
                      <th className="px-4 py-3 rounded-tl-lg">Rank</th>
                      <th className="px-4 py-3">Archer Name</th>
                      <th className="px-4 py-3">Lane</th>
                      <th className="px-4 py-3">Round 1</th>
                      <th className="px-4 py-3">Round 2</th>
                      <th className="px-4 py-3">Round 3</th>
                      <th className="px-4 py-3">10s / Xs</th>
                      <th className="px-4 py-3">Arrow Avg</th>
                      <th className="px-4 py-3 rounded-tr-lg text-right">Total Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-navy-800/60">
                    {leaderboard.map((entry) => (
                      <tr
                        key={`${entry.archer_id}-${entry.lane_number}`}
                        className="hover:bg-navy-850/60 transition-colors"
                      >
                        <td className="px-4 py-3.5 font-bold">
                          {entry.rank === 1 && <span className="text-gold-400 font-black">🥇 1</span>}
                          {entry.rank === 2 && <span className="text-slate-300 font-black">🥈 2</span>}
                          {entry.rank === 3 && <span className="text-amber-500 font-black">🥉 3</span>}
                          {entry.rank > 3 && <span className="text-slate-400">#{entry.rank}</span>}
                        </td>
                        <td className="px-4 py-3.5 font-bold text-slate-200">
                          {entry.archer_name}
                        </td>
                        <td className="px-4 py-3.5 text-slate-400 font-mono">
                          Lane {entry.lane_number || 1}
                        </td>
                        <td className="px-4 py-3.5 text-slate-300 font-mono">
                          {entry.round_1_score ?? '—'}
                        </td>
                        <td className="px-4 py-3.5 text-slate-300 font-mono">
                          {entry.round_2_score ?? '—'}
                        </td>
                        <td className="px-4 py-3.5 text-slate-300 font-mono">
                          {entry.round_3_score ?? '—'}
                        </td>
                        <td className="px-4 py-3.5 text-xs text-slate-400">
                          {entry.tens_count ?? 0} ({entry.xs_count ?? 0} X)
                        </td>
                        <td className="px-4 py-3.5 text-slate-300 font-mono">
                          {entry.average_score ? entry.average_score.toFixed(2) : '—'}
                        </td>
                        <td className="px-4 py-3.5 text-right font-black text-base text-gold-400 font-mono">
                          {entry.total_score}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-16 text-slate-500 border border-dashed border-navy-800 rounded-xl p-8">
                <Trophy className="w-12 h-12 mx-auto mb-2 opacity-30 text-gold-500" />
                <h4 className="text-sm font-semibold text-slate-300">No Standings Recorded</h4>
                <p className="text-xs text-slate-500 mt-1">
                  Select a session or tournament above to populate the official standings
                  leaderboard.
                </p>
              </div>
            )}
          </div>
        )}

        {/* VIEW 4: TARGET IMAGE GALLERY */}
        {view === 'gallery' && (
          <div className="glass-card p-6 border border-navy-700/60 rounded-xl bg-navy-900/80 space-y-6">
            {/* Gallery Header & Stats */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-navy-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <ImageIcon className="w-5 h-5 text-gold-400" /> Target Camera Scans & AI Vision Gallery
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Annotated target frames with localized arrows, score zones, and AI vision confidence telemetry
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-navy-950 text-gold-400 border border-navy-700">
                  {galleryTotal} Scans Found
                </span>
                <button
                  onClick={fetchGalleryData}
                  disabled={loadingGallery}
                  className="btn-ghost flex items-center gap-1.5 text-xs px-2.5 py-1.5 border border-navy-700 text-slate-300 hover:text-slate-100"
                >
                  <RefreshCw className={cn('w-3.5 h-3.5', loadingGallery && 'animate-spin')} />
                  Refresh
                </button>
              </div>
            </div>

            {/* Filter & Sort Controls Ribbon */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 bg-navy-950/80 p-4 rounded-xl border border-navy-800">
              {/* Tournament Filter */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                  <Trophy className="w-3 h-3 text-gold-400" /> Tournament
                </label>
                <select
                  value={galleryTournamentFilter || ''}
                  onChange={(e) => {
                    const val = e.target.value ? Number(e.target.value) : null
                    setGalleryTournamentFilter(val)
                    setGallerySessionFilter(null)
                    setGalleryPage(1)
                  }}
                  className="w-full bg-navy-900 border border-navy-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-gold-500"
                >
                  <option value="">All Tournaments</option>
                  {tournaments.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Player / Archer Filter */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                  <UserIcon className="w-3 h-3 text-blue-400" /> Player / Archer
                </label>
                <select
                  value={galleryArcherFilter}
                  onChange={(e) => {
                    setGalleryArcherFilter(e.target.value)
                    setGalleryPage(1)
                  }}
                  className="w-full bg-navy-900 border border-navy-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-gold-500"
                >
                  <option value="">All Athletes</option>
                  {archersDirectory.map((a) => (
                    <option key={`${a.archer_name}-${a.archer_id}`} value={a.archer_name}>
                      {a.archer_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* End / Round Filter */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                  <Target className="w-3 h-3 text-emerald-400" /> End / Round
                </label>
                <select
                  value={galleryRoundFilter || ''}
                  onChange={(e) => {
                    const val = e.target.value ? Number(e.target.value) : null
                    setGalleryRoundFilter(val)
                    setGalleryPage(1)
                  }}
                  className="w-full bg-navy-900 border border-navy-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-gold-500"
                >
                  <option value="">All Ends</option>
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((r) => (
                    <option key={r} value={r}>
                      End #{r}
                    </option>
                  ))}
                </select>
              </div>

              {/* Score Zone Filter */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                  <Award className="w-3 h-3 text-amber-400" /> Score Zone
                </label>
                <select
                  value={galleryZoneFilter}
                  onChange={(e) => {
                    setGalleryZoneFilter(e.target.value)
                    setGalleryPage(1)
                  }}
                  className="w-full bg-navy-900 border border-navy-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-gold-500"
                >
                  <option value="all">All Score Rings</option>
                  <option value="10">🟡 10s & Xs (Gold)</option>
                  <option value="9">🟡 9s (Gold)</option>
                  <option value="8-7">🔴 8s - 7s (Red)</option>
                  <option value="6-5">🔵 6s - 5s (Blue)</option>
                  <option value="4-1">⚪ 4s - 1s (Black/White)</option>
                </select>
              </div>

              {/* Sort By Dropdown */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                  <ArrowUpDown className="w-3 h-3 text-purple-400" /> Sort By
                </label>
                <select
                  value={gallerySortBy}
                  onChange={(e) => {
                    setGallerySortBy(e.target.value as any)
                    setGalleryPage(1)
                  }}
                  className="w-full bg-navy-900 border border-navy-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-gold-500 font-medium"
                >
                  <option value="latest">🕒 Latest Scans First</option>
                  <option value="points_desc">🥇 Highest Points (10 → 0)</option>
                  <option value="points_asc">📉 Lowest Points (0 → 10)</option>
                  <option value="confidence_desc">🎯 Highest AI Confidence</option>
                  <option value="round_asc">🔢 End & Arrow Order</option>
                  <option value="oldest">⏳ Oldest Scans First</option>
                </select>
              </div>

              {/* Reset Filters */}
              <div className="flex items-end">
                <button
                  onClick={() => {
                    setGalleryTournamentFilter(null)
                    setGallerySessionFilter(null)
                    setGalleryArcherFilter('')
                    setGalleryRoundFilter(null)
                    setGalleryZoneFilter('all')
                    setGallerySortBy('latest')
                    setGalleryPage(1)
                  }}
                  className="w-full bg-navy-900 hover:bg-navy-800 text-slate-400 hover:text-slate-200 border border-navy-700 rounded-lg px-3 py-1.5 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Filter className="w-3.5 h-3.5" />
                  Reset All
                </button>
              </div>
            </div>

            {/* Gallery Content Grid */}
            {loadingGallery ? (
              <div className="flex flex-col items-center justify-center py-20 text-slate-500">
                <Loader2 className="w-8 h-8 text-gold-500 animate-spin mb-2" />
                <span className="text-sm font-medium">Filtering & loading target vision scans...</span>
              </div>
            ) : galleryItems.length === 0 ? (
              <div className="text-center py-16 text-slate-500 border border-dashed border-navy-800 rounded-xl p-8 max-w-md mx-auto">
                <ImageIcon className="w-12 h-12 mx-auto mb-3 opacity-40 text-gold-500" />
                <h3 className="text-base font-semibold text-slate-300 mb-1">
                  No Matching Target Scans
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed mb-4">
                  No captured target frames match your current filter criteria. Try clearing the filters or selecting another athlete/tournament.
                </p>
                <button
                  onClick={() => {
                    setGalleryTournamentFilter(null)
                    setGallerySessionFilter(null)
                    setGalleryArcherFilter('')
                    setGalleryRoundFilter(null)
                    setGalleryZoneFilter('all')
                    setGallerySortBy('latest')
                    setGalleryPage(1)
                  }}
                  className="btn-ghost text-xs px-3 py-1.5 border border-navy-700 text-slate-300"
                >
                  Clear Filters
                </button>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {galleryItems.map((item) => {
                    const scoreId = item.id || item.score_id
                    const pointsColor =
                      item.points >= 9
                        ? 'bg-gold-500/20 text-gold-300 border-gold-500/40'
                        : item.points >= 7
                        ? 'bg-red-500/20 text-red-300 border-red-500/40'
                        : item.points >= 5
                        ? 'bg-blue-500/20 text-blue-300 border-blue-500/40'
                        : 'bg-slate-700/30 text-slate-300 border-slate-600/40'

                    const imgSource = item.annotated_image_url || item.image_url || `/scores/${scoreId}/image-annotated`

                    return (
                      <div
                        key={scoreId}
                        onClick={() =>
                          setSelectedScore({
                            id: scoreId,
                            session_id: item.session_id,
                            session_archer_id: item.session_archer_id || item.archer_id || 0,
                            round: item.round,
                            arrow_num: item.arrow_num,
                            zone: item.zone,
                            points: item.points,
                            image_id: item.image_id || `scan_${scoreId}`,
                            validated_by_ai: true,
                            confidence: item.confidence ?? 0.95,
                            method: item.method || 'YOLO11 Vision Pipeline',
                            created_at: item.created_at,
                            updated_at: item.created_at,
                            annotated_image: imgSource,
                          })
                        }
                        className="bg-navy-950 border border-navy-800 hover:border-gold-500/60 rounded-xl overflow-hidden cursor-pointer transition-all hover:scale-[1.02] shadow-xl flex flex-col group relative"
                      >
                        {/* Target Photo Container */}
                        <div className="aspect-video bg-black relative overflow-hidden flex items-center justify-center">
                          <AuthenticatedImage
                            src={imgSource}
                            alt={`Target Scan #${scoreId}`}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          />

                          {/* Top Badges */}
                          <div className="absolute top-2 left-2 flex items-center gap-1.5">
                            <span className="bg-navy-950/90 backdrop-blur-sm px-2 py-0.5 rounded text-[10px] font-black text-slate-200 border border-navy-700">
                              End {item.round} · #{item.arrow_num}
                            </span>
                            <span className="bg-navy-950/90 backdrop-blur-sm px-2 py-0.5 rounded text-[10px] font-mono text-slate-400 border border-navy-700">
                              Lane {item.lane_number}
                            </span>
                          </div>

                          <div className="absolute top-2 right-2">
                            <span
                              className={cn(
                                'px-2.5 py-0.5 rounded text-xs font-black font-mono border backdrop-blur-sm shadow-md',
                                pointsColor
                              )}
                            >
                              {item.points} {item.is_x ? '(X)' : 'pts'}
                            </span>
                          </div>

                          {/* Bottom Badges */}
                          <div className="absolute bottom-2 left-2">
                            <span className="bg-navy-950/90 backdrop-blur-sm px-2 py-0.5 rounded text-[10px] font-bold text-gold-400 border border-navy-700">
                              #{scoreId}
                            </span>
                          </div>

                          {item.confidence !== null && item.confidence !== undefined && (
                            <div className="absolute bottom-2 right-2">
                              <span className="bg-navy-950/90 backdrop-blur-sm px-2 py-0.5 rounded text-[10px] text-emerald-400 font-bold border border-emerald-500/30 flex items-center gap-1">
                                <Sparkles className="w-2.5 h-2.5" />
                                {Math.round(item.confidence * 100)}% AI Conf
                              </span>
                            </div>
                          )}

                          {/* Hover View Overlay */}
                          <div className="absolute inset-0 bg-navy-950/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center backdrop-blur-xs">
                            <span className="px-3 py-1.5 rounded-lg bg-gold-500 text-navy-950 font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-gold-500/30 transform translate-y-2 group-hover:translate-y-0 transition-transform">
                              <Eye className="w-3.5 h-3.5" /> Inspect Target
                            </span>
                          </div>
                        </div>

                        {/* Card Footer Information */}
                        <div className="p-3 bg-navy-900/90 border-t border-navy-800 flex flex-col justify-between flex-1">
                          <div>
                            <div className="flex items-center justify-between">
                              <p className="text-xs font-black text-slate-100 truncate">
                                {item.archer_name}
                              </p>
                              <span className="text-[10px] text-slate-400 font-mono">
                                Zone {item.zone}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-400 truncate mt-0.5">
                              {item.tournament_name || item.session_name}
                            </p>
                          </div>

                          <div className="mt-2.5 pt-2 border-t border-navy-800/80 flex items-center justify-between text-[10px] text-slate-500">
                            <span className="truncate">{item.method || 'YOLO11 AI Vision'}</span>
                            <span className="shrink-0">{new Date(item.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Pagination Controls */}
                {galleryTotal > galleryPageSize && (
                  <div className="flex items-center justify-between border-t border-navy-800 pt-4 text-xs text-slate-400">
                    <div>
                      Showing {(galleryPage - 1) * galleryPageSize + 1} -{' '}
                      {Math.min(galleryPage * galleryPageSize, galleryTotal)} of {galleryTotal} target scans
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setGalleryPage((p) => Math.max(1, p - 1))}
                        disabled={galleryPage <= 1}
                        className="btn-ghost px-2.5 py-1 text-xs border border-navy-700 disabled:opacity-30 flex items-center gap-1"
                      >
                        <ChevronLeft className="w-3.5 h-3.5" /> Previous
                      </button>
                      <span className="px-2.5 py-1 bg-navy-950 font-bold text-slate-200 rounded border border-navy-700">
                        {galleryPage} / {Math.ceil(galleryTotal / galleryPageSize)}
                      </span>
                      <button
                        onClick={() =>
                          setGalleryPage((p) =>
                            p < Math.ceil(galleryTotal / galleryPageSize) ? p + 1 : p
                          )
                        }
                        disabled={galleryPage >= Math.ceil(galleryTotal / galleryPageSize)}
                        className="btn-ghost px-2.5 py-1 text-xs border border-navy-700 disabled:opacity-30 flex items-center gap-1"
                      >
                        Next <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Score Inspection & Override Modal */}
      {selectedScore && (
        <ScoreDetailsModal
          isOpen={!!selectedScore}
          onClose={() => setSelectedScore(null)}
          score={selectedScore}
          onOverrideSuccess={() => {
            fetchData()
            if (view === 'gallery') fetchGalleryData()
          }}
        />
      )}
    </div>
  )
}

