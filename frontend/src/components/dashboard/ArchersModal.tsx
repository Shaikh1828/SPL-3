import { useState } from 'react'
import { Users, Search, X, Medal, Target, Award } from 'lucide-react'
import type { LeaderboardEntry } from '@/types'

interface ArchersModalProps {
  isOpen: boolean
  onClose: () => void
  archers: LeaderboardEntry[]
  sessionName?: string
}

export function ArchersModal({ isOpen, onClose, archers, sessionName }: ArchersModalProps) {
  const [search, setSearch] = useState('')

  if (!isOpen) return null

  const filtered = archers.filter(a =>
    a.archer_name.toLowerCase().includes(search.toLowerCase()) ||
    a.lane_number.toString().includes(search)
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="glass-card w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl border border-navy-700/80 overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-navy-700 bg-navy-900/60">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">Enrolled Archers Roster</h2>
              <p className="text-xs text-slate-400">
                {sessionName ? `Competitors in ${sessionName}` : 'All active tournament competitors'} ({archers.length} archers)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-navy-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search */}
        <div className="p-4 border-b border-navy-800 bg-navy-900/30">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search archers by name or lane number..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-navy-800/80 border border-navy-700/80 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
            />
          </div>
        </div>

        {/* Archers Grid / Table */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
          {filtered.length > 0 ? (
            filtered.map((archer) => {
              const avgScore = archer.arrows_recorded > 0
                ? (archer.total_score / archer.arrows_recorded).toFixed(1)
                : '0.0'

              return (
                <div
                  key={archer.archer_id}
                  className="p-3.5 rounded-xl bg-navy-800/40 border border-navy-700/50 flex items-center justify-between gap-4 hover:border-navy-600 transition-all"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center font-bold text-xs text-slate-300 flex-shrink-0">
                      {archer.rank === 1 ? (
                        <Medal className="w-4 h-4 text-gold-400" />
                      ) : archer.rank === 2 ? (
                        <Medal className="w-4 h-4 text-slate-300" />
                      ) : archer.rank === 3 ? (
                        <Medal className="w-4 h-4 text-amber-600" />
                      ) : (
                        `#${archer.rank}`
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-200 truncate">{archer.archer_name}</p>
                      <p className="text-xs text-slate-400 flex items-center gap-2">
                        <span>Lane {archer.lane_number}</span>
                        <span>·</span>
                        <span>{archer.arrows_recorded} arrows shot</span>
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-6 text-right">
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Average</p>
                      <p className="text-xs font-semibold text-slate-300">{avgScore} / arrow</p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Score</p>
                      <p className="text-base font-bold text-gold-400">{archer.total_score}</p>
                    </div>
                  </div>
                </div>
              )
            })
          ) : (
            <div className="py-12 text-center text-slate-500">
              <Target className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No archers matching search criteria</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-navy-800 bg-navy-900/80 flex items-center justify-between text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <Award className="w-3.5 h-3.5 text-gold-400" />
            Rankings update in real-time as ends are shot
          </span>
          <button onClick={onClose} className="px-3 py-1.5 bg-navy-800 hover:bg-navy-700 text-slate-300 rounded-lg">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
