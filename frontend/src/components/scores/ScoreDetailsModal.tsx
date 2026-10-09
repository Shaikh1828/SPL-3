import { useState, useEffect } from 'react'
import { X, Image as ImageIcon, ShieldAlert, CheckCircle, Target } from 'lucide-react'
import { scoresApi } from '@/api/scores'
import { useAuthStore } from '@/store/authStore'
import { cn, getConfidenceColor } from '@/lib/utils'
import { AuthenticatedImage } from './AuthenticatedImage'
import toast from 'react-hot-toast'
import type { Score } from '@/types'

interface ScoreDetailsModalProps {
  isOpen: boolean
  onClose: () => void
  score: Score | null
  allScores?: Score[]
  dryRunData?: {
    filename: string
    zone: number
    points: number
    confidence: number
    method: string
    annotated_image: string | null
  } | null
  onOverrideSuccess?: () => void
}

export function ScoreDetailsModal({
  isOpen,
  onClose,
  score,
  allScores = [],
  dryRunData,
  onOverrideSuccess,
}: ScoreDetailsModalProps) {
  const { user } = useAuthStore()
  const canOverride = user?.role === 'admin' || user?.role === 'scorer'
  const [activeTab, setActiveTab] = useState<'annotated' | 'raw'>('annotated')
  const [selectedScoreId, setSelectedScoreId] = useState<number | null>(null)
  const [overrideZone, setOverrideZone] = useState<number>(0)
  const [overridePoints, setOverridePoints] = useState<number>(0)
  const [overrideReason, setOverrideReason] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)

  // Find sibling scores in the same round for this archer
  const roundScores = (score && allScores.length > 0)
    ? allScores.filter(s => s.session_archer_id === score.session_archer_id && s.round === score.round)
    : (score ? [score] : [])

  const currentScore = roundScores.find(s => s.id === selectedScoreId) || score

  // Sync selection and form fields when score or modal opens
  useEffect(() => {
    if (score) {
      setSelectedScoreId(score.id)
    } else {
      setSelectedScoreId(null)
    }
  }, [score])

  useEffect(() => {
    if (currentScore) {
      setOverrideZone(currentScore.zone)
      setOverridePoints(currentScore.points)
      setOverrideReason('')
    } else if (dryRunData) {
      setOverrideZone(dryRunData.zone)
      setOverridePoints(dryRunData.points)
      setOverrideReason('')
    }
  }, [currentScore?.id, currentScore?.zone, currentScore?.points, dryRunData])

  if (!isOpen) return null

  const isDryRun = !!dryRunData
  const filename = isDryRun ? dryRunData.filename : `Score Record #${currentScore?.id}`
  const zone = isDryRun ? dryRunData.zone : currentScore?.zone
  const points = isDryRun ? dryRunData.points : currentScore?.points
  const confidence = isDryRun ? dryRunData.confidence : currentScore?.confidence ?? 0
  const method = isDryRun ? dryRunData.method : currentScore?.method ?? 'unknown'
  const isValidated = isDryRun ? false : currentScore?.validated_by_ai

  const scanTotalPoints = roundScores.length > 0
    ? roundScores.reduce((sum, s) => sum + s.points, 0)
    : (points ?? 0)

  const handleOverrideSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentScore) return

    setIsSubmitting(true)
    try {
      await scoresApi.override(currentScore.id, {
        zone: overrideZone,
        points: overridePoints,
        reason: overrideReason || 'Manual adjustment via score modal',
      })
      toast.success(`Arrow #${currentScore.arrow_num} score updated to ${overridePoints} pts`)
      if (onOverrideSuccess) {
        onOverrideSuccess()
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to override score')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Determine Image sources
  const activeImageId = currentScore?.id || score?.id
  const rawImageSrc = activeImageId ? scoresApi.getRawImageUrl(activeImageId) : ''
  const annotatedImageSrc = activeImageId ? scoresApi.getAnnotatedImageUrl(activeImageId) : ''
  const base64Annotated = dryRunData?.annotated_image

  return (
    <div className="fixed inset-0 bg-navy-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card max-w-4xl w-full flex flex-col md:flex-row overflow-hidden border border-navy-700 animate-in max-h-[90vh]">
        
        {/* Left Side: Image Display */}
        <div className="flex-1 bg-black p-4 flex flex-col justify-between items-center border-b md:border-b-0 md:border-r border-navy-800">
          <div className="flex justify-between items-center w-full mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <ImageIcon className="w-3.5 h-3.5 text-gold-500" />
              {activeTab === 'annotated' ? 'Annotated Target Detection' : 'Raw Original Image'}
            </span>
            <div className="flex bg-navy-900 p-0.5 rounded-lg border border-navy-800 text-[11px]">
              <button
                onClick={() => setActiveTab('annotated')}
                className={cn('px-2.5 py-1 rounded-md transition-colors font-medium', activeTab === 'annotated' ? 'bg-gold-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-slate-200')}
              >
                Annotated
              </button>
              <button
                onClick={() => setActiveTab('raw')}
                className={cn('px-2.5 py-1 rounded-md transition-colors font-medium', activeTab === 'raw' ? 'bg-gold-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-slate-200')}
              >
                Raw
              </button>
            </div>
          </div>

          <div className="w-full flex-1 flex items-center justify-center min-h-[300px] max-h-[450px] relative bg-navy-950/50 rounded-lg overflow-hidden border border-navy-900">
            {activeTab === 'annotated' ? (
              isDryRun && base64Annotated ? (
                <img src={base64Annotated} alt="Annotated Target" className="w-full h-full object-contain" />
              ) : (
                <AuthenticatedImage src={annotatedImageSrc} alt="Annotated Target" className="w-full h-full object-contain" />
              )
            ) : (
              <AuthenticatedImage src={rawImageSrc} alt="Raw Target" className="w-full h-full object-contain" />
            )}
          </div>

          <div className="w-full flex items-center justify-between mt-3 text-[11px] text-slate-500">
            <span className="truncate max-w-[200px]">{filename}</span>
            <span>Target Image Preview</span>
          </div>
        </div>

        {/* Right Side: Score Details & Actions */}
        <div className="w-full md:w-80 p-6 flex flex-col justify-between bg-navy-900/60 overflow-y-auto">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-100">Shot Analysis</h3>
                {!isDryRun && currentScore && (
                  <p className="text-[11px] text-gold-400 font-mono mt-0.5">
                    End {currentScore.round} · Arrow #{currentScore.arrow_num}
                  </p>
                )}
              </div>
              <button onClick={onClose} className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-navy-800">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scan / End Aggregate Header */}
            {!isDryRun && roundScores.length > 0 && (
              <div className="mb-4 p-3 bg-navy-850 border border-navy-750 rounded-xl">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Target className="w-3.5 h-3.5 text-gold-400" />
                    End {score?.round} Scan Total
                  </span>
                  <span className="text-sm font-black font-mono text-gold-400">
                    {scanTotalPoints} pts <span className="text-[10px] text-slate-400 font-normal">({roundScores.length} arrows)</span>
                  </span>
                </div>

                {/* Arrow Pills Selector */}
                {roundScores.length > 1 && (
                  <div className="mt-2.5 pt-2 border-t border-navy-800 flex gap-1.5 flex-wrap">
                    {roundScores.map((arr) => {
                      const isSelected = arr.id === currentScore?.id
                      return (
                        <button
                          key={arr.id}
                          onClick={() => setSelectedScoreId(arr.id)}
                          className={cn(
                            'px-2 py-1 rounded text-xs font-mono font-bold transition-all border flex items-center gap-1',
                            isSelected
                              ? 'bg-gold-500 text-navy-950 border-gold-400 shadow-md ring-1 ring-gold-400'
                              : 'bg-navy-900/80 text-slate-300 border-navy-700 hover:border-slate-500'
                          )}
                          title={`Click to view Arrow #${arr.arrow_num}`}
                        >
                          <span>#{arr.arrow_num}:</span>
                          <span className={isSelected ? 'text-navy-950 font-black' : 'text-gold-400 font-black'}>
                            {arr.points === 10 && arr.zone === 10 ? 'X' : arr.points}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Selected Arrow Score Grid */}
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-navy-850/50 border border-navy-800/80 p-3 rounded-lg text-center">
                  <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider block">Zone</span>
                  <span className="text-gold-400 text-2xl font-black block mt-0.5">{zone ?? '-'}</span>
                </div>
                <div className="bg-navy-850/50 border border-navy-800/80 p-3 rounded-lg text-center">
                  <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider block">Points</span>
                  <span className="text-slate-100 text-2xl font-black block mt-0.5">{points ?? '-'}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="bg-navy-850/50 border border-navy-800/80 p-3 rounded-lg">
                  <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider block">Confidence</span>
                  <span className={cn('text-xs font-semibold block mt-1', getConfidenceColor(confidence))}>
                    {(confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="bg-navy-850/50 border border-navy-800/80 p-3 rounded-lg">
                  <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider block">CV Method</span>
                  <span className="text-slate-200 text-xs font-semibold block mt-1 truncate" title={method}>
                    {method}
                  </span>
                </div>
              </div>

              {!isDryRun && (
                <div className="bg-navy-850/50 border border-navy-800/80 p-3 rounded-lg flex items-center justify-between">
                  <div>
                    <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider block">Status</span>
                    <span className="text-slate-200 text-xs font-semibold block mt-1">
                      {isValidated ? 'Validated by AI' : 'Manual / Override'}
                    </span>
                  </div>
                  {isValidated ? (
                    <CheckCircle className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <ShieldAlert className="w-5 h-5 text-yellow-400" />
                  )}
                </div>
              )}
            </div>

            {/* Admin / Scorer Override Section */}
            {!isDryRun && (
              <div className="mt-6 border-t border-navy-800 pt-5">
                <h4 className="text-sm font-bold text-slate-200 flex items-center gap-2 mb-3">
                  <ShieldAlert className="w-4 h-4 text-rose-500" />
                  Override Arrow #{currentScore?.arrow_num ?? 1}
                </h4>
                
                {canOverride ? (
                  <form onSubmit={handleOverrideSubmit} className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-slate-400 text-xs mb-1">Override Zone</label>
                        <input
                          type="number"
                          min="0"
                          max="10"
                          required
                          value={overrideZone}
                          onChange={(e) => {
                            const val = parseInt(e.target.value) || 0
                            setOverrideZone(val)
                            setOverridePoints(val)
                          }}
                          className="input-dark w-full py-1 text-sm text-center font-bold"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-400 text-xs mb-1">Override Points</label>
                        <input
                          type="number"
                          min="0"
                          max="10"
                          required
                          value={overridePoints}
                          onChange={(e) => setOverridePoints(parseInt(e.target.value) || 0)}
                          className="input-dark w-full py-1 text-sm text-center font-bold"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-slate-400 text-xs mb-1">Reason for Override *</label>
                      <textarea
                        required
                        rows={2}
                        value={overrideReason}
                        onChange={(e) => setOverrideReason(e.target.value)}
                        placeholder="e.g., Target paper reflection, line cutting..."
                        className="input-dark w-full text-xs placeholder:text-slate-600"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="btn-danger w-full py-2 text-xs font-bold rounded-lg flex items-center justify-center gap-2"
                    >
                      Apply Score Override
                    </button>
                  </form>
                ) : (
                  <div className="bg-navy-950/40 border border-navy-850 p-3 rounded-lg text-slate-500 text-xs flex gap-2">
                    <ShieldAlert className="w-4 h-4 text-slate-600 flex-shrink-0" />
                    <p>Score overrides can only be performed by Admin or Scorer accounts. Spectators have read-only access here.</p>
                  </div>
                )}
              </div>
            )}
          </div>
          
          <div className="mt-6 pt-4 border-t border-navy-850 flex justify-end">
            <button
              onClick={onClose}
              className="btn-ghost py-1.5 px-4 text-xs font-medium"
            >
              Close Preview
            </button>
          </div>
        </div>

      </div>
    </div>
  )
}
