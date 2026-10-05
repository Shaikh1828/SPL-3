import { useState } from 'react'
import {
  CheckCircle2, Sparkles, AlertTriangle, RotateCcw,
  Edit3, Eye, ShieldCheck, ArrowRight, X, Trophy, Camera
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AIScoreRoundResponse, LaneDetectionResult, DetectedArrow, LaneSubmission, SessionArcher } from '@/types'

interface ScorerReviewStageProps {
  stagedData: AIScoreRoundResponse
  archers: SessionArcher[]
  isSubmitting: boolean
  canScore: boolean
  onConfirmRound: (submissions: LaneSubmission[]) => Promise<void>
  onRescan: () => Promise<void>
  onDiscard: () => void
}

const SCORE_VALUES = [
  { label: 'X', points: 10, zone: 'X', isX: true, color: 'bg-gold-500 text-navy-950 hover:bg-gold-400 border-gold-400 font-black' },
  { label: '10', points: 10, zone: '10', isX: false, color: 'bg-gold-500 text-navy-950 hover:bg-gold-400 border-gold-400 font-black' },
  { label: '9', points: 9, zone: '9', isX: false, color: 'bg-gold-600 text-navy-950 hover:bg-gold-500 border-gold-500 font-bold' },
  { label: '8', points: 8, zone: '8', isX: false, color: 'bg-red-500 text-white hover:bg-red-400 border-red-400 font-bold' },
  { label: '7', points: 7, zone: '7', isX: false, color: 'bg-red-600 text-white hover:bg-red-500 border-red-500 font-bold' },
  { label: '6', points: 6, zone: '6', isX: false, color: 'bg-blue-500 text-white hover:bg-blue-400 border-blue-400 font-bold' },
  { label: '5', points: 5, zone: '5', isX: false, color: 'bg-blue-600 text-white hover:bg-blue-500 border-blue-500 font-bold' },
  { label: '4', points: 4, zone: '4', isX: false, color: 'bg-slate-700 text-white hover:bg-slate-600 border-slate-500 font-bold' },
  { label: '3', points: 3, zone: '3', isX: false, color: 'bg-slate-800 text-white hover:bg-slate-700 border-slate-600 font-bold' },
  { label: '2', points: 2, zone: '2', isX: false, color: 'bg-slate-200 text-navy-950 hover:bg-white border-slate-300 font-bold' },
  { label: '1', points: 1, zone: '1', isX: false, color: 'bg-slate-300 text-navy-950 hover:bg-white border-slate-400 font-bold' },
  { label: 'M', points: 0, zone: '0', isX: false, color: 'bg-slate-900 text-slate-400 hover:text-slate-200 border-slate-700 font-bold' },
]

export function ScorerReviewStage({
  stagedData,
  archers,
  isSubmitting,
  canScore,
  onConfirmRound,
  onRescan,
  onDiscard,
}: ScorerReviewStageProps) {
  const [lanes, setLanes] = useState<LaneDetectionResult[]>(stagedData.lanes)
  const [inspectImage, setInspectImage] = useState<{ src: string; title: string } | null>(null)
  const [overrideModal, setOverrideModal] = useState<{
    laneIndex: number
    arrowIndex: number
    laneNumber: number
    archerName: string
    currentArrow: DetectedArrow
  } | null>(null)
  const [overrideReason, setOverrideReason] = useState('Line judge confirmed score')

  // Total stats across all staged lanes
  const totalArrows = lanes.reduce((sum, l) => sum + l.detected_arrows.length, 0)
  const totalPoints = lanes.reduce((sum, l) => sum + l.end_total, 0)
  const overriddenCount = lanes.reduce(
    (sum, l) => sum + l.detected_arrows.filter(a => a.is_override).length,
    0
  )

  // Handle single arrow override
  const handleApplyOverride = (val: typeof SCORE_VALUES[0]) => {
    if (!overrideModal) return
    const { laneIndex, arrowIndex } = overrideModal

    setLanes(prev => {
      const copy = [...prev]
      const lane = { ...copy[laneIndex] }
      const arrows = [...lane.detected_arrows]

      arrows[arrowIndex] = {
        ...arrows[arrowIndex],
        points: val.points,
        zone: val.zone,
        is_x: val.isX,
        is_override: true,
        override_reason: overrideReason,
        confidence: 1.0,
      }

      lane.detected_arrows = arrows
      lane.end_total = arrows.reduce((sum, a) => sum + a.points, 0)
      lane.status = 'overridden'
      copy[laneIndex] = lane
      return copy
    })

    setOverrideModal(null)
  }

  // Handle submit batch
  const handleSubmit = async () => {
    const submissions: LaneSubmission[] = lanes.map(lane => ({
      session_archer_id: lane.session_archer_id,
      lane_number: lane.lane_number,
      arrows: lane.detected_arrows,
    }))
    await onConfirmRound(submissions)
  }

  return (
    <div className="space-y-6 animate-in">
      {/* 🚀 STAGE HEADER BANNER */}
      <div className="glass-card p-5 bg-gradient-to-r from-navy-900 via-gold-950/20 to-navy-900 border-gold-500/40 shadow-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="px-3 py-1 rounded-full text-xs font-black bg-gold-500 text-navy-950 flex items-center gap-1.5 shadow-md">
              <Sparkles className="w-3.5 h-3.5" />
              AI Round Scoring Review · End {stagedData.round}
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              {lanes.length} Lanes Ready for Confirmation
            </span>
            {overriddenCount > 0 && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                <Edit3 className="w-3.5 h-3.5" />
                {overriddenCount} Arrow(s) Overridden
              </span>
            )}
          </div>
          <h2 className="text-xl font-black text-slate-100">
            Scorer Verification & Staging Matrix
          </h2>
          <p className="text-xs text-slate-400">
            Review detected arrow impacts for End {stagedData.round}. Click any arrow to override before confirming and starting the next round.
          </p>
        </div>

        {/* Action Buttons Top */}
        <div className="flex items-center gap-2 w-full md:w-auto justify-end flex-wrap">
          <button
            onClick={onRescan}
            disabled={isSubmitting}
            className="btn-ghost text-xs py-2 px-3 flex items-center gap-1.5 border border-navy-700 hover:border-gold-500"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Re-Scan AI
          </button>
          <button
            onClick={onDiscard}
            disabled={isSubmitting}
            className="btn-ghost text-xs py-2 px-3 text-slate-400 hover:text-red-400 border border-navy-700 hover:border-red-500/40"
          >
            Discard
          </button>
          {canScore && (
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="btn-primary text-xs py-2.5 px-5 font-black flex items-center gap-2 shadow-lg shadow-gold-500/20"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-navy-950 border-t-transparent rounded-full animate-spin" />
                  <span>Committing End {stagedData.round}...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Confirm & Submit End {stagedData.round}</span>
                  <ArrowRight className="w-4 h-4 ml-1" />
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* 🎯 LANE REVIEW CARDS GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {lanes.map((lane, laneIdx) => {
          const archer = archers.find(a => a.id === lane.session_archer_id)
          const runningTotal = (archer?.total_score || 0) + lane.end_total

          return (
            <div
              key={lane.lane_number}
              className={cn(
                'glass-card p-5 space-y-4 border transition-all flex flex-col justify-between shadow-xl',
                lane.status === 'overridden'
                  ? 'border-purple-500/40 bg-navy-900/90'
                  : 'border-navy-700/80 bg-navy-900/60 hover:border-gold-500/40'
              )}
            >
              {/* Lane Header */}
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-gold-500/20 border border-gold-500/40 flex items-center justify-center font-black text-sm text-gold-400 shadow-inner">
                    L{lane.lane_number}
                  </div>
                  <div>
                    <h3 className="font-bold text-sm text-slate-100 flex items-center gap-1.5">
                      {lane.archer_name}
                    </h3>
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mt-0.5">
                      <Camera className="w-3 h-3 text-slate-500" />
                      <span className="truncate max-w-[130px]">{lane.camera_name || 'Lane Camera'}</span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col items-end gap-1">
                  <span className={cn(
                    'px-2 py-0.5 rounded-full text-[10px] font-bold border uppercase tracking-wider',
                    lane.avg_confidence >= 0.90
                      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                      : 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                  )}>
                    {Math.round(lane.avg_confidence * 100)}% {lane.method === 'yolo11_consensus' ? 'YOLO11' : 'CV'}
                  </span>
                  {lane.status === 'overridden' && (
                    <span className="text-[10px] font-bold text-purple-400 flex items-center gap-1">
                      <Edit3 className="w-2.5 h-2.5" /> Edited
                    </span>
                  )}
                </div>
              </div>

              {/* Annotated Target Preview */}
              {lane.annotated_image ? (
                <div className="relative aspect-video rounded-xl overflow-hidden bg-navy-950 border border-navy-700/80 group">
                  <img
                    src={lane.annotated_image}
                    alt={`Lane ${lane.lane_number} Target`}
                    className="w-full h-full object-contain cursor-pointer transition-transform duration-300 group-hover:scale-105"
                    onClick={() => setInspectImage({ src: lane.annotated_image!, title: `Lane ${lane.lane_number} Target — ${lane.archer_name}` })}
                  />
                  <div className="absolute inset-0 bg-navy-950/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center pointer-events-none">
                    <span className="px-3 py-1.5 rounded-lg bg-navy-900/90 text-xs text-gold-400 font-bold flex items-center gap-1.5 shadow-lg">
                      <Eye className="w-3.5 h-3.5" /> Inspect Target
                    </span>
                  </div>
                </div>
              ) : (
                <div className="aspect-video rounded-xl bg-navy-950 flex flex-col items-center justify-center text-slate-500 border border-dashed border-navy-700 text-xs">
                  <AlertTriangle className="w-6 h-6 mb-1 opacity-40 text-amber-400" />
                  <span>Image Preview Processing...</span>
                </div>
              )}

              {/* 🎯 Detected Arrows Sequence (Interactive) */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span className="font-semibold uppercase tracking-wider">End {stagedData.round} Arrow Scores:</span>
                  <span className="text-slate-500">Click arrow to override</span>
                </div>

                <div className="grid grid-cols-6 gap-1.5">
                  {lane.detected_arrows.map((arr, arrIdx) => {
                    const isX = arr.is_x || arr.zone === 'X'
                    return (
                      <button
                        key={arrIdx}
                        type="button"
                        onClick={() => {
                          if (canScore) {
                            setOverrideModal({
                              laneIndex: laneIdx,
                              arrowIndex: arrIdx,
                              laneNumber: lane.lane_number,
                              archerName: lane.archer_name,
                              currentArrow: arr,
                            })
                          }
                        }}
                        className={cn(
                          'h-11 rounded-lg border flex flex-col items-center justify-center transition-all relative group',
                          arr.is_override
                            ? 'bg-purple-950/50 border-purple-500 text-purple-200 shadow-md shadow-purple-500/20'
                            : isX || arr.points === 10
                            ? 'bg-gold-500/20 border-gold-500/50 text-gold-400 hover:bg-gold-500/30'
                            : arr.points >= 8
                            ? 'bg-red-500/20 border-red-500/40 text-red-400 hover:bg-red-500/30'
                            : arr.points >= 6
                            ? 'bg-blue-500/20 border-blue-500/40 text-blue-400 hover:bg-blue-500/30'
                            : 'bg-navy-950 border-navy-700 text-slate-300 hover:border-slate-500'
                        )}
                        title={`Arrow #${arr.arrow_num}: ${isX ? 'X (10 pts)' : `${arr.points} pts`} · Click to override`}
                      >
                        <span className="text-sm font-black font-mono">
                          {isX ? 'X' : arr.points === 0 ? 'M' : arr.points}
                        </span>
                        <span className="text-[9px] text-slate-400 leading-none">
                          #{arr.arrow_num}
                        </span>

                        {arr.is_override && (
                          <div className="w-1.5 h-1.5 rounded-full bg-purple-400 absolute top-1 right-1" />
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* End Subtotal & Running Total */}
              <div className="pt-3 border-t border-navy-700/80 flex items-center justify-between">
                <div>
                  <span className="text-[11px] text-slate-400 block">End {stagedData.round} Subtotal:</span>
                  <span className="text-base font-black font-mono text-gold-400">
                    {lane.end_total} <span className="text-xs text-slate-400 font-normal">pts</span>
                  </span>
                </div>

                <div className="text-right">
                  <span className="text-[11px] text-slate-400 block">Projected Total:</span>
                  <span className="text-base font-black font-mono text-emerald-400">
                    {runningTotal} <span className="text-xs text-slate-400 font-normal">pts</span>
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* 🌟 FLOATING CONFIRMATION BAR */}
      <div className="sticky bottom-4 z-40 glass-card p-4 bg-navy-950/95 backdrop-blur-md border border-gold-500/50 shadow-2xl rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gold-500/20 border border-gold-500/30 flex items-center justify-center text-gold-400">
            <Trophy className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-bold text-slate-100">
              End {stagedData.round} Review Complete · {lanes.length} Lanes ({totalArrows} Arrows) · Total: {totalPoints} pts
            </p>
            <p className="text-[11px] text-slate-400">
              Submitting will commit all scores to database, update live leaderboards, and advance to End {stagedData.round + 1}.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
          <button
            onClick={onDiscard}
            disabled={isSubmitting}
            className="btn-ghost text-xs py-2 px-4 text-slate-400 hover:text-red-400"
          >
            Cancel
          </button>
          {canScore && (
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="btn-primary text-xs py-3 px-6 font-black flex items-center gap-2 shadow-xl shadow-gold-500/25"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-navy-950 border-t-transparent rounded-full animate-spin" />
                  <span>Submitting End {stagedData.round}...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Confirm & Start End {stagedData.round + 1}</span>
                  <ArrowRight className="w-4 h-4 ml-1" />
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* ✏️ QUICK ARROW OVERRIDE MODAL */}
      {overrideModal && (
        <div className="fixed inset-0 bg-navy-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 space-y-5 animate-in shadow-2xl border border-navy-700 bg-navy-900">
            <div className="flex justify-between items-center pb-2 border-b border-navy-700">
              <div>
                <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <Edit3 className="w-4 h-4 text-purple-400" />
                  Manual Score Override · Arrow #{overrideModal.currentArrow.arrow_num}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Lane {overrideModal.laneNumber} — {overrideModal.archerName}
                </p>
              </div>
              <button
                onClick={() => setOverrideModal(null)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Current Score vs New */}
            <div className="p-3 bg-navy-950 rounded-xl border border-navy-700 flex justify-between items-center text-xs">
              <span className="text-slate-400">Current AI Detected Score:</span>
              <span className="font-mono font-black text-sm text-gold-400">
                {overrideModal.currentArrow.is_x ? 'X (10 pts)' : `${overrideModal.currentArrow.points} pts`} (Zone {overrideModal.currentArrow.zone})
              </span>
            </div>

            {/* Tactile Keypad */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">Select Corrected Score:</label>
              <div className="grid grid-cols-4 gap-2">
                {SCORE_VALUES.map(val => (
                  <button
                    key={val.label}
                    type="button"
                    onClick={() => handleApplyOverride(val)}
                    className={cn(
                      'h-12 rounded-xl border text-sm flex items-center justify-center transition-transform active:scale-95 shadow-md',
                      val.color
                    )}
                  >
                    {val.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Reason Selector */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">Override Reason:</label>
              <div className="flex flex-wrap gap-1.5">
                {[
                  'Line judge confirmed score',
                  'Line touch bullseye ruling',
                  'Camera occlusion correction',
                  'Target ring boundary touch',
                ].map(r => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setOverrideReason(r)}
                    className={cn(
                      'px-2.5 py-1 rounded-lg text-[11px] border transition-colors',
                      overrideReason === r
                        ? 'bg-purple-500/20 text-purple-300 border-purple-500/50 font-bold'
                        : 'bg-navy-950 text-slate-400 border-navy-700 hover:text-slate-200'
                    )}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setOverrideModal(null)}
                className="btn-ghost py-1.5 px-4 text-xs"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 🔍 FULLSCREEN TARGET INSPECT MODAL */}
      {inspectImage && (
        <div
          className="fixed inset-0 bg-navy-950/90 backdrop-blur-md z-50 flex items-center justify-center p-4"
          onClick={() => setInspectImage(null)}
        >
          <div className="relative max-w-4xl w-full glass-card p-4 space-y-3 animate-in" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center pb-2 border-b border-navy-700">
              <h3 className="text-sm font-bold text-slate-100">{inspectImage.title}</h3>
              <button onClick={() => setInspectImage(null)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="aspect-video bg-navy-950 rounded-xl overflow-hidden flex items-center justify-center">
              <img src={inspectImage.src} alt="Inspected target" className="max-h-[75vh] w-auto object-contain" />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
