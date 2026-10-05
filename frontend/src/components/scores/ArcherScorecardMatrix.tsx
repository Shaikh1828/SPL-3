import { Trophy } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Score, SessionArcher } from '@/types'

interface ArcherScorecardMatrixProps {
  archers: SessionArcher[]
  allScores: Score[]
  arrowsPerRound: number
  activeLane: number
  onSelectLane: (lane: number) => void
}

export function ArcherScorecardMatrix({
  archers,
  allScores,
  arrowsPerRound,
  activeLane,
  onSelectLane,
}: ArcherScorecardMatrixProps) {
  // Find highest end number
  const maxEnd = Math.max(1, ...allScores.map(s => s.round), 2)

  // Group scores by session_archer_id and round
  const archerEndMap = new Map<number, Map<number, Score[]>>()
  for (const s of allScores) {
    if (!archerEndMap.has(s.session_archer_id)) {
      archerEndMap.set(s.session_archer_id, new Map())
    }
    const endMap = archerEndMap.get(s.session_archer_id)!
    if (!endMap.has(s.round)) {
      endMap.set(s.round, [])
    }
    endMap.get(s.round)!.push(s)
  }

  // Sorted archers by total score descending
  const sortedArchers = [...archers].sort((a, b) => b.total_score - a.total_score)

  return (
    <div className="glass-card p-5 space-y-4 border-navy-700/80 shadow-xl overflow-hidden">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
          <Trophy className="w-4 h-4 text-gold-400" />
          Multi-Lane Live Match Scorecard Matrix
        </h3>
        <span className="text-xs text-slate-400">
          Click any lane row to switch active target
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-navy-700/80 bg-navy-900/60 text-slate-400 uppercase tracking-wider">
              <th className="py-3 px-3 w-12 text-center">Rank</th>
              <th className="py-3 px-3 min-w-[140px]">Archer / Lane</th>
              {Array.from({ length: maxEnd }).map((_, i) => (
                <th key={i} className="py-3 px-2 text-center min-w-[80px]">
                  End {i + 1}
                </th>
              ))}
              <th className="py-3 px-3 text-center">10s+Xs</th>
              <th className="py-3 px-3 text-center">Avg</th>
              <th className="py-3 px-4 text-right">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-navy-750">
            {sortedArchers.map((archer, rankIdx) => {
              const isActive = archer.lane_number === activeLane
              const archerScores = allScores.filter(s => s.session_archer_id === archer.id)
              const tensCount = archerScores.filter(s => s.points === 10).length
              const avgScore = archerScores.length > 0 ? (archer.total_score / archerScores.length).toFixed(1) : '0.0'
              const endMap = archerEndMap.get(archer.id) || new Map<number, Score[]>()

              return (
                <tr
                  key={archer.id}
                  onClick={() => archer.lane_number && onSelectLane(archer.lane_number)}
                  className={cn(
                    'transition-colors cursor-pointer group',
                    isActive
                      ? 'bg-gold-500/10 border-l-4 border-l-gold-500'
                      : 'hover:bg-navy-800/50'
                  )}
                >
                  {/* Rank */}
                  <td className="py-3 px-3 text-center">
                    <span className={cn(
                      'w-6 h-6 rounded-full inline-flex items-center justify-center font-black text-xs',
                      rankIdx === 0 ? 'bg-gold-500 text-navy-950 shadow-sm' :
                      rankIdx === 1 ? 'bg-slate-300 text-navy-950' :
                      rankIdx === 2 ? 'bg-amber-600 text-white' :
                      'bg-navy-800 text-slate-400'
                    )}>
                      {rankIdx + 1}
                    </span>
                  </td>

                  {/* Archer Name & Lane */}
                  <td className="py-3 px-3 font-medium">
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        'text-sm font-bold',
                        isActive ? 'text-gold-400' : 'text-slate-100 group-hover:text-gold-300'
                      )}>
                        {archer.archer_name}
                      </span>
                      <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-semibold bg-navy-700/60 text-slate-300">
                        Lane {archer.lane_number}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400">
                      {archerScores.length} arrows shot
                    </span>
                  </td>

                  {/* Ends Breakdown */}
                  {Array.from({ length: maxEnd }).map((_, endIdx) => {
                    const endNumber = endIdx + 1
                    const scoresInEnd = endMap.get(endNumber) || []
                    const subtotal = scoresInEnd.reduce((sum, s) => sum + s.points, 0)
                    const isComplete = scoresInEnd.length >= arrowsPerRound

                    return (
                      <td key={endIdx} className="py-3 px-2 text-center">
                        <div className="flex flex-col items-center">
                          <span className={cn(
                            'font-mono font-bold text-xs',
                            isComplete ? 'text-slate-200' : 'text-slate-400'
                          )}>
                            {scoresInEnd.length > 0 ? subtotal : '—'}
                          </span>
                          <div className="flex gap-0.5 mt-0.5">
                            {scoresInEnd.slice(0, 3).map((s, idx) => (
                              <span
                                key={idx}
                                className={cn(
                                  'text-[9px] px-1 rounded font-mono',
                                  s.points === 10 ? 'bg-gold-500/20 text-gold-400 font-bold' :
                                  s.points >= 8 ? 'bg-red-500/20 text-red-400' :
                                  'bg-navy-800 text-slate-400'
                                )}
                              >
                                {s.points === 10 && s.zone === 10 ? 'X' : s.points}
                              </span>
                            ))}
                            {scoresInEnd.length > 3 && (
                              <span className="text-[9px] text-slate-500 font-mono">+{scoresInEnd.length - 3}</span>
                            )}
                          </div>
                        </div>
                      </td>
                    )
                  })}

                  {/* 10s and Xs */}
                  <td className="py-3 px-3 text-center font-semibold font-mono text-gold-400">
                    {tensCount > 0 ? `${tensCount}x` : '0'}
                  </td>

                  {/* Average */}
                  <td className="py-3 px-3 text-center font-mono text-slate-300">
                    {avgScore}
                  </td>

                  {/* Total Score */}
                  <td className="py-3 px-4 text-right">
                    <span className={cn(
                      'text-lg font-black font-mono',
                      rankIdx === 0 ? 'text-gold-400' : 'text-slate-100'
                    )}>
                      {archer.total_score}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
