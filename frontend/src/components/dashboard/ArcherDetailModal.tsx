import { Target, X, TrendingUp } from 'lucide-react'
import type { LeaderboardEntry } from '@/types'

interface ArcherDetailModalProps {
  isOpen: boolean
  onClose: () => void
  archer: LeaderboardEntry | null
  tournamentName?: string
}

export function ArcherDetailModal({ isOpen, onClose, archer, tournamentName }: ArcherDetailModalProps) {
  if (!isOpen || !archer) return null

  const arrowsRecorded = archer.arrows_recorded || 0
  const tensCount = archer.tens_count || 0
  const xsCount = archer.xs_count || 0
  const avgScore = archer.average_score || (arrowsRecorded > 0 ? (archer.total_score / arrowsRecorded).toFixed(1) : 0)
  const recentArrows = archer.recent_arrows || []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="glass-card w-full max-w-lg shadow-2xl border border-navy-700/80 overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-navy-700/80 flex items-center justify-between bg-navy-900/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gold-500/20 border border-gold-500/30 flex items-center justify-center text-gold-400 font-black text-base">
              {archer.archer_name.charAt(0)}
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">{archer.archer_name}</h2>
              <p className="text-xs text-slate-400 flex items-center gap-2">
                <span>Lane {archer.lane_number}</span>
                {tournamentName && <span>• {tournamentName}</span>}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-navy-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4">
          {/* Quick Stats Grid */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-navy-900/60 border border-navy-800 text-center">
              <span className="text-[10px] uppercase font-semibold text-slate-400">Current Rank</span>
              <p className="text-2xl font-black text-gold-400 mt-0.5">#{archer.rank}</p>
            </div>
            <div className="p-3 rounded-xl bg-navy-900/60 border border-navy-800 text-center">
              <span className="text-[10px] uppercase font-semibold text-slate-400">Total Score</span>
              <p className="text-2xl font-black text-slate-100 mt-0.5">{archer.total_score}</p>
            </div>
            <div className="p-3 rounded-xl bg-navy-900/60 border border-navy-800 text-center">
              <span className="text-[10px] uppercase font-semibold text-slate-400">Avg / Arrow</span>
              <p className="text-2xl font-black text-emerald-400 mt-0.5">{avgScore}</p>
            </div>
          </div>

          {/* Performance Breakdown */}
          <div className="p-4 rounded-xl bg-navy-900/40 border border-navy-800 space-y-3">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-gold-400" />
              Shooting Breakdown
            </h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center justify-between p-2 rounded-lg bg-navy-950/40">
                <span className="text-slate-400">Arrows Shot:</span>
                <span className="font-semibold text-slate-200">{arrowsRecorded}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-navy-950/40">
                <span className="text-slate-400">Perfect 10s:</span>
                <span className="font-semibold text-gold-400">{tensCount}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-navy-950/40">
                <span className="text-slate-400">Bullseye Xs:</span>
                <span className="font-semibold text-purple-400">{xsCount}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-navy-950/40">
                <span className="text-slate-400">Session Round:</span>
                <span className="font-semibold text-slate-200">Round {archer.current_round ?? 1}</span>
              </div>
            </div>
          </div>

          {/* Recent Arrow Sequence */}
          {recentArrows.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Target className="w-3.5 h-3.5 text-blue-400" />
                Recent Arrow Scores
              </h3>
              <div className="flex items-center gap-2">
                {recentArrows.map((pts, i) => (
                  <span
                    key={i}
                    className={`w-9 h-9 rounded-lg flex items-center justify-center text-sm font-black border ${
                      pts === 10
                        ? 'bg-gold-500/20 text-gold-400 border-gold-500/40 shadow-sm shadow-gold-500/10'
                        : pts >= 8
                        ? 'bg-red-500/20 text-red-400 border-red-500/40'
                        : pts >= 6
                        ? 'bg-blue-500/20 text-blue-400 border-blue-500/40'
                        : 'bg-navy-800 text-slate-300 border-navy-700'
                    }`}
                  >
                    {pts}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-navy-700/80 bg-navy-900/60 flex items-center justify-end">
          <button onClick={onClose} className="btn-secondary text-xs py-2 px-4">
            Close Scorecard
          </button>
        </div>
      </div>
    </div>
  )
}
