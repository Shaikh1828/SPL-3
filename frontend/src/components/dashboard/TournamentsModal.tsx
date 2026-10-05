import { useState } from 'react'
import { Trophy, Calendar, MapPin, ArrowRight, Plus, Search, X, CheckCircle, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { Tournament } from '@/types'
import { formatDate } from '@/lib/utils'

interface TournamentsModalProps {
  isOpen: boolean
  onClose: () => void
  tournaments: Tournament[]
}

export function TournamentsModal({ isOpen, onClose, tournaments }: TournamentsModalProps) {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')

  if (!isOpen) return null

  const filtered = tournaments.filter(t =>
    t.name.toLowerCase().includes(search.toLowerCase()) ||
    (t.location && t.location.toLowerCase().includes(search.toLowerCase())) ||
    (t.description && t.description.toLowerCase().includes(search.toLowerCase()))
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
            <div className="p-2.5 rounded-lg bg-gold-500/10 border border-gold-500/20 text-gold-400">
              <Trophy className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">Enrolled Tournaments</h2>
              <p className="text-xs text-slate-400">All registered competitions ({tournaments.length} total)</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-navy-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search & Actions Bar */}
        <div className="p-4 border-b border-navy-800 bg-navy-900/30 flex items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search tournaments by name, location..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-navy-800/80 border border-navy-700/80 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-gold-500/50"
            />
          </div>
          <button
            onClick={() => {
              onClose()
              navigate('/tournaments')
            }}
            className="btn-primary flex items-center gap-1.5 text-xs py-2 px-3 whitespace-nowrap"
          >
            <Plus className="w-4 h-4" />
            New Tournament
          </button>
        </div>

        {/* Tournament List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {filtered.length > 0 ? (
            filtered.map((t) => {
              const isPast = new Date(t.end_date) < new Date()
              const isOngoing = new Date(t.start_date) <= new Date() && new Date(t.end_date) >= new Date()

              return (
                <div
                  key={t.id}
                  onClick={() => {
                    onClose()
                    navigate('/tournaments')
                  }}
                  className="p-4 rounded-xl bg-navy-800/40 hover:bg-navy-800/70 border border-navy-700/50 hover:border-gold-500/30 transition-all cursor-pointer group flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-sm font-semibold text-slate-200 group-hover:text-gold-300 transition-colors">
                        {t.name}
                      </h3>
                      {isOngoing ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          Ongoing Active
                        </span>
                      ) : isPast ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20 flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" />
                          Completed
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          Upcoming
                        </span>
                      )}
                    </div>
                    {t.description && (
                      <p className="text-xs text-slate-400 line-clamp-1">{t.description}</p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        {formatDate(t.start_date)} — {formatDate(t.end_date)}
                      </span>
                      {t.location && (
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5 text-slate-400" />
                          {t.location}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    <button className="text-xs text-gold-400 font-medium group-hover:translate-x-1 transition-transform flex items-center gap-1">
                      Manage <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )
            })
          ) : (
            <div className="py-12 text-center text-slate-500">
              <Trophy className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No tournaments matching "{search}"</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-navy-800 bg-navy-900/80 flex items-center justify-between text-xs text-slate-400">
          <span>Click any tournament to view rounds & participants</span>
          <button onClick={onClose} className="px-3 py-1.5 bg-navy-800 hover:bg-navy-700 text-slate-300 rounded-lg">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
