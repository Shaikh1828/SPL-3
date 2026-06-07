import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Target, Camera, Trophy, TrendingUp,
  AlertCircle, CheckCircle, Activity, HardDrive, Cpu,
  ArrowRight, RefreshCw
} from 'lucide-react'
import { healthApi } from '@/api/health'
import { sessionsApi } from '@/api/sessions'
import { tournamentsApi } from '@/api/tournaments'
import { useSessionStore } from '@/store/sessionStore'
import { useScoreStream } from '@/hooks/useScoreStream'
import type { DetailedHealth, Leaderboard, Tournament, Session } from '@/types'
import { cn, formatDate } from '@/lib/utils'

function StatCard({ icon: Icon, label, value, sub, color = 'gold' }: {
  icon: React.ElementType; label: string; value: string | number; sub?: string; color?: string
}) {
  const colors: Record<string, string> = {
    gold: 'text-gold-400 bg-gold-500/10 border-gold-500/20',
    emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    blue: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    red: 'text-red-400 bg-red-500/10 border-red-500/20',
  }
  return (
    <div className="glass-card p-5 slide-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">{label}</p>
          <p className="text-2xl font-bold text-slate-100 mt-1">{value}</p>
          {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
        </div>
        <div className={cn('p-2.5 rounded-lg border', colors[color])}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { activeSession, setActiveSession, setActiveTournament } = useSessionStore()
  const [health, setHealth] = useState<DetailedHealth | null>(null)
  const [leaderboard, setLeaderboard] = useState<Leaderboard | null>(null)
  const [tournaments, setTournaments] = useState<Tournament[]>([])
  const [sessions, setSessions] = useState<Session[]>([])

  const { lastEvent } = useScoreStream(activeSession?.id ?? null)

  const fetchHealth = useCallback(async () => {
    try { setHealth(await healthApi.detailed()) } catch { /* offline */ }
  }, [])

  const fetchLeaderboard = useCallback(async () => {
    if (!activeSession) return
    try { setLeaderboard(await sessionsApi.getLeaderboard(activeSession.id)) } catch { /* ok */ }
  }, [activeSession])

  const loadData = useCallback(async () => {
    try {
      await fetchHealth()
      const t = await tournamentsApi.list({ limit: 5 })
      setTournaments(t.items)
      if (t.items.length > 0) {
        const s = await sessionsApi.listForTournament(t.items[0].id, { status: 'active' })
        setSessions(s.items)
        if (s.items.length > 0 && !activeSession) {
          setActiveSession(s.items[0])
          setActiveTournament(t.items[0])
        }
      }
    } catch (err) {
      console.error(err)
    }
  }, [fetchHealth, activeSession, setActiveSession, setActiveTournament])

  useEffect(() => { loadData() }, [loadData])
  useEffect(() => { fetchLeaderboard() }, [fetchLeaderboard, lastEvent])

  const storage = health?.components.storage
  const usagePct = storage?.usage_percent ?? 0

  return (
    <div className="p-6 space-y-6 animate-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">System overview & live session status</p>
        </div>
        <button
          onClick={loadData}
          className="btn-ghost flex items-center gap-2 text-sm"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Trophy}
          label="Tournaments"
          value={tournaments.length}
          color="gold"
        />
        <StatCard
          icon={Target}
          label="Active Sessions"
          value={sessions.filter(s => s.status === 'active').length}
          color="emerald"
        />
        <StatCard
          icon={Activity}
          label="Total Archers"
          value={leaderboard?.total_archers ?? '—'}
          sub={activeSession?.name}
          color="blue"
        />
        <StatCard
          icon={Camera}
          label="System"
          value={health?.status === 'healthy' ? 'Healthy' : 'Degraded'}
          color={health?.status === 'healthy' ? 'emerald' : 'red'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Leaderboard */}
        <div className="lg:col-span-2 glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-slate-100 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-gold-400" />
              Live Leaderboard
            </h2>
            {activeSession && (
              <span className="text-xs text-slate-500">{activeSession.name}</span>
            )}
          </div>

          {leaderboard?.items.length ? (
            <div className="space-y-2">
              {leaderboard.items.slice(0, 8).map((entry) => (
                <div
                  key={entry.archer_id}
                  className={cn(
                    'flex items-center gap-4 px-3 py-2.5 rounded-lg',
                    entry.rank === 1
                      ? 'bg-gold-500/10 border border-gold-500/20'
                      : 'bg-navy-800/40'
                  )}
                >
                  <span className={cn(
                    'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0',
                    entry.rank === 1 ? 'bg-gold-500 text-navy-900' : 'bg-navy-700 text-slate-400'
                  )}>
                    {entry.rank}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-200 truncate">{entry.archer_name}</p>
                    <p className="text-xs text-slate-500">Lane {entry.lane_number} · {entry.arrows_recorded} arrows</p>
                  </div>
                  <span className={cn(
                    'text-lg font-bold',
                    entry.rank === 1 ? 'text-gold-400' : 'text-slate-300'
                  )}>
                    {entry.total_score}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Target className="w-10 h-10 text-slate-700 mb-3" />
              <p className="text-slate-500 text-sm">No active session</p>
              <button
                onClick={() => navigate('/tournaments')}
                className="mt-3 text-xs text-gold-400 hover:text-gold-300 flex items-center gap-1"
              >
                Start a session <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>

        {/* System Health */}
        <div className="space-y-4">
          <div className="glass-card p-5">
            <h2 className="font-semibold text-slate-100 flex items-center gap-2 mb-4">
              <Cpu className="w-4 h-4 text-blue-400" />
              System Health
            </h2>
            {health ? (
              <div className="space-y-3">
                {Object.entries(health.components).map(([key, comp]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 capitalize">{key}</span>
                    <div className="flex items-center gap-1.5">
                      {comp.status === 'healthy' ? (
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                      )}
                      <span className={cn(
                        'text-xs font-medium',
                        comp.status === 'healthy' ? 'text-emerald-400' : 'text-red-400'
                      )}>
                        {comp.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500">Loading...</p>
            )}
          </div>

          {/* Storage */}
          <div className="glass-card p-5">
            <h2 className="font-semibold text-slate-100 flex items-center gap-2 mb-3">
              <HardDrive className="w-4 h-4 text-purple-400" />
              Storage
            </h2>
            {storage ? (
              <>
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-slate-500">
                    {(storage.quota_gb! - storage.available_gb!).toFixed(1)} GB used
                  </span>
                  <span className={usagePct > 80 ? 'text-red-400' : 'text-slate-400'}>
                    {storage.quota_gb} GB total
                  </span>
                </div>
                <div className="h-2 bg-navy-700 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all duration-500',
                      usagePct > 80 ? 'bg-red-500' : usagePct > 60 ? 'bg-yellow-500' : 'bg-emerald-500'
                    )}
                    style={{ width: `${usagePct}%` }}
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">{usagePct}% used</p>
              </>
            ) : (
              <p className="text-xs text-slate-500">Loading...</p>
            )}
          </div>

          {/* Quick actions */}
          <div className="glass-card p-5">
            <h2 className="font-semibold text-slate-100 mb-3">Quick Actions</h2>
            <div className="space-y-2">
              <button
                onClick={() => navigate('/scoring')}
                className="w-full btn-primary text-sm py-2"
              >
                Go to Scoring
              </button>
              <button
                onClick={() => navigate('/tournaments')}
                className="w-full text-sm py-2 border border-navy-600 hover:border-navy-500 rounded-lg text-slate-300 hover:text-slate-100 transition-colors"
              >
                Manage Tournaments
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Recent tournaments */}
      {tournaments.length > 0 && (
        <div className="glass-card p-5">
          <h2 className="font-semibold text-slate-100 mb-4">Recent Tournaments</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {tournaments.slice(0, 3).map((t) => (
              <div key={t.id} className="glass-card-hover p-4 cursor-pointer" onClick={() => navigate('/tournaments')}>
                <p className="font-medium text-slate-200 text-sm">{t.name}</p>
                <p className="text-xs text-slate-500 mt-1">{t.location ?? 'No location'}</p>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-slate-600">{formatDate(t.start_date)}</span>
                  <ArrowRight className="w-3 h-3 text-slate-600" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
