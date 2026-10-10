import { useState, useEffect } from 'react'
import { Target, RotateCcw, ArrowRight, ArrowLeft, Check, Sparkles, Edit3 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Score, SessionArcher } from '@/types'

interface RapidScorePadProps {
  archer: SessionArcher | null
  currentEnd: number
  arrowsPerRound: number
  endScores: Score[]
  isSubmitting: boolean
  onRecordScore: (points: number, zone: number, isX?: boolean) => Promise<void>
  onUpdateSlotScore?: (scoreId: number, points: number, zone: number, isX?: boolean) => Promise<void>
  onUndoLastScore: () => Promise<void>
  onNextEnd: () => void
  onPrevEnd: () => void
  canScore: boolean
}

const SCORE_BUTTONS = [
  { label: 'X', points: 10, zone: 10, isX: true, bg: 'bg-amber-500 hover:bg-amber-400 text-navy-950 font-black border-amber-300 shadow-amber-500/30' },
  { label: '10', points: 10, zone: 10, isX: false, bg: 'bg-amber-500 hover:bg-amber-400 text-navy-950 font-black border-amber-300 shadow-amber-500/30' },
  { label: '9', points: 9, zone: 9, isX: false, bg: 'bg-amber-500/80 hover:bg-amber-400/90 text-navy-950 font-bold border-amber-400/50' },
  { label: '8', points: 8, zone: 8, isX: false, bg: 'bg-red-600 hover:bg-red-500 text-white font-bold border-red-400 shadow-red-500/20' },
  { label: '7', points: 7, zone: 7, isX: false, bg: 'bg-red-600/80 hover:bg-red-500/90 text-white font-bold border-red-400/50' },
  { label: '6', points: 6, zone: 6, isX: false, bg: 'bg-sky-600 hover:bg-sky-500 text-white font-bold border-sky-400 shadow-sky-500/20' },
  { label: '5', points: 5, zone: 5, isX: false, bg: 'bg-sky-600/80 hover:bg-sky-500/90 text-white font-bold border-sky-400/50' },
  { label: '4', points: 4, zone: 4, isX: false, bg: 'bg-slate-700 hover:bg-slate-600 text-slate-100 font-bold border-slate-500' },
  { label: '3', points: 3, zone: 3, isX: false, bg: 'bg-slate-700/80 hover:bg-slate-600/90 text-slate-200 font-bold border-slate-600' },
  { label: '2', points: 2, zone: 2, isX: false, bg: 'bg-slate-200 hover:bg-white text-navy-950 font-bold border-slate-300 shadow-sm' },
  { label: '1', points: 1, zone: 1, isX: false, bg: 'bg-slate-300 hover:bg-slate-100 text-navy-950 font-bold border-slate-400 shadow-sm' },
  { label: 'M', points: 0, zone: 0, isX: false, bg: 'bg-navy-800 hover:bg-navy-700 text-slate-400 font-bold border-navy-600' },
]

export function RapidScorePad({
  archer,
  currentEnd,
  arrowsPerRound,
  endScores,
  isSubmitting,
  onRecordScore,
  onUpdateSlotScore,
  onUndoLastScore,
  onNextEnd,
  onPrevEnd,
  canScore,
}: RapidScorePadProps) {
  const [lastClicked, setLastClicked] = useState<string | null>(null)
  const [selectedSlotIndex, setSelectedSlotIndex] = useState<number>(0)

  const arrowsShot = endScores.length
  const isEndComplete = arrowsShot >= arrowsPerRound
  const endSubtotal = endScores.reduce((sum, s) => sum + s.points, 0)
  const tensCount = endScores.filter(s => s.points === 10).length

  // Sync selected slot only when changing end or archer
  useEffect(() => {
    setSelectedSlotIndex(Math.min(endScores.length, arrowsPerRound - 1))
  }, [currentEnd, archer?.id, arrowsPerRound])

  const handleScoreClick = async (item: typeof SCORE_BUTTONS[0]) => {
    if (!canScore || isSubmitting || !archer) return
    setLastClicked(item.label)

    const existingScore = endScores[selectedSlotIndex]
    if (existingScore && onUpdateSlotScore) {
      // Overriding existing slot in place
      await onUpdateSlotScore(existingScore.id, item.points, item.zone, item.isX)
    } else {
      // Appending new arrow score
      await onRecordScore(item.points, item.zone, item.isX)
      setSelectedSlotIndex((prev) => Math.min(prev + 1, arrowsPerRound - 1))
    }

    setLastClicked(null)
  }

  const isBullseyeX = (score: Score | undefined) => {
    if (!score) return false
    return (
      score.image_id === 'x_hit.jpg' ||
      (score.points === 10 && score.zone === 10 && (
        (score as any).isX ||
        score.override_reason?.includes('X') ||
        score.override_reason?.includes('Bullseye')
      ))
    )
  }

  const selectedScore = endScores[selectedSlotIndex]
  const isEditingExisting = !!selectedScore

  return (
    <div className="glass-card p-5 space-y-5 border-navy-700/80 shadow-2xl">
      {/* End Progress & Target Slot Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-navy-700">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-xs font-bold bg-gold-500/20 text-gold-400 border border-gold-500/30">
              End {currentEnd}
            </span>
            <h3 className="text-base font-bold text-slate-100">
              {archer ? archer.archer_name : 'No Archer Selected'}
            </h3>
            {archer && (
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-navy-800 text-slate-300 border border-navy-700">
                Lane {archer.lane_number}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-2">
            <span>Arrow Slot #{selectedSlotIndex + 1} Selected</span>
            {isEditingExisting && (
              <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.2 rounded font-semibold border border-amber-500/30 flex items-center gap-1">
                <Edit3 className="w-3 h-3" /> Edit mode
              </span>
            )}
          </p>
        </div>

        {/* End Subtotal & Archer Match Total */}
        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">End Subtotal</span>
            <span className="text-xl font-black text-gold-400 font-mono">{endSubtotal} <span className="text-xs font-normal text-slate-400">pts</span></span>
          </div>
          <div className="h-8 w-px bg-navy-700" />
          <div className="text-right">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Total Score</span>
            <span className="text-xl font-black text-emerald-400 font-mono">{archer?.total_score ?? 0} <span className="text-xs font-normal text-slate-400">pts</span></span>
          </div>
        </div>
      </div>

      {/* Arrow Slots Visualizer (Clickable Slots for Direct Editing) */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Current End Arrows (Click any slot to edit)
          </span>
          {tensCount > 0 && (
            <span className="text-xs text-gold-400 font-bold flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> {tensCount}x 10s this end
            </span>
          )}
        </div>

        <div className="grid grid-cols-6 gap-2">
          {Array.from({ length: arrowsPerRound }).map((_, idx) => {
            const scoreItem = endScores[idx]
            const isSelected = idx === selectedSlotIndex
            const isFilled = !!scoreItem

            return (
              <button
                key={idx}
                type="button"
                data-testid={`arrow-slot-${idx + 1}`}
                onClick={() => setSelectedSlotIndex(idx)}
                className={cn(
                  'h-14 rounded-xl border flex flex-col items-center justify-center transition-all relative overflow-hidden text-left focus:outline-none cursor-pointer',
                  isSelected && 'ring-2 ring-gold-400 ring-offset-2 ring-offset-navy-950 scale-102 z-10 shadow-lg',
                  isFilled
                    ? scoreItem.points === 10
                      ? 'bg-gradient-to-b from-amber-500/25 to-amber-500/10 border-amber-400 text-amber-300 shadow-md shadow-amber-500/10'
                      : scoreItem.points >= 8
                      ? 'bg-gradient-to-b from-red-600/25 to-red-600/10 border-red-500 text-red-300 shadow-md shadow-red-500/10'
                      : scoreItem.points >= 6
                      ? 'bg-gradient-to-b from-sky-600/25 to-sky-600/10 border-sky-500 text-sky-300'
                      : 'bg-navy-800/80 border-navy-700 text-slate-200'
                    : isSelected
                    ? 'border-gold-500/80 bg-gold-500/10 animate-pulse text-gold-400 shadow-lg shadow-gold-500/10'
                    : 'border-dashed border-navy-700/80 bg-navy-950/40 text-slate-600 hover:border-slate-500'
                )}
              >
                <span className="text-[10px] font-mono text-slate-400 absolute top-1 left-1.5 flex items-center gap-1">
                  #{idx + 1}
                </span>

                {isFilled ? (
                  <span className="text-xl font-black font-mono mt-2">
                    {isBullseyeX(scoreItem) ? 'X' : scoreItem.points === 0 ? 'M' : scoreItem.points}
                  </span>
                ) : isSelected ? (
                  <Target className="w-5 h-5 text-gold-400 animate-spin-slow mt-2" />
                ) : (
                  <span className="text-sm font-mono text-slate-600 mt-2">—</span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Tactile Score Buttons Grid */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            {isEditingExisting ? `Tap Score to Override Arrow #${selectedSlotIndex + 1}` : `Tap Score to Record Arrow #${selectedSlotIndex + 1}`}
          </span>
          {isEditingExisting && (
            <span className="text-xs text-gold-400 font-semibold">
              Current: {isBullseyeX(selectedScore) ? 'X' : selectedScore.points} pts
            </span>
          )}
        </div>

        <div className="grid grid-cols-4 sm:grid-cols-6 gap-2.5">
          {SCORE_BUTTONS.map((btn) => (
            <button
              key={btn.label}
              data-testid={`score-pad-btn-${btn.label}`}
              onClick={() => handleScoreClick(btn)}
              disabled={!canScore || isSubmitting || !archer}
              className={cn(
                'h-14 rounded-xl border flex flex-col items-center justify-center transition-all transform active:scale-95 shadow-md',
                btn.bg,
                (!canScore || isSubmitting || !archer) && 'opacity-40 cursor-not-allowed transform-none shadow-none',
                lastClicked === btn.label && 'ring-2 ring-gold-400 scale-95'
              )}
            >
              <span className="text-2xl leading-none font-black">{btn.label}</span>
              <span className="text-[10px] uppercase opacity-75 font-sans mt-0.5">
                {btn.points === 10 && btn.isX ? 'Bullseye' : btn.points === 0 ? 'Miss' : `${btn.points} pts`}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Controls & End Progression Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-navy-700">
        <div className="flex items-center gap-2">
          <button
            onClick={onPrevEnd}
            disabled={currentEnd <= 1 || isSubmitting}
            className="btn-ghost py-1.5 px-3 text-xs flex items-center gap-1 border border-navy-700"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Prev End
          </button>

          <button
            onClick={onNextEnd}
            disabled={isSubmitting}
            className="btn-ghost py-1.5 px-3 text-xs flex items-center gap-1 border border-navy-700 text-gold-400 hover:text-gold-300"
          >
            Next End <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          {canScore && (
            <button
              onClick={onUndoLastScore}
              disabled={arrowsShot === 0 || isSubmitting}
              className="btn-ghost py-1.5 px-3 text-xs flex items-center gap-1 text-red-400 hover:text-red-300 hover:bg-red-500/10 border border-red-500/30"
              title="Undo last scored arrow"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Undo Arrow
            </button>
          )}

          {isEndComplete && (
            <button
              onClick={onNextEnd}
              className="btn-primary py-1.5 px-4 text-xs flex items-center gap-1.5 shadow-md shadow-gold-500/20 animate-bounce-subtle"
            >
              <Check className="w-3.5 h-3.5" /> End Complete → Next End
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
