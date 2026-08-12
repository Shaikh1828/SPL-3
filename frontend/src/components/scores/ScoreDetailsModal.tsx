import { useState } from 'react'
import { X, Image as ImageIcon, ShieldAlert, CheckCircle } from 'lucide-react'
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
  dryRunData,
  onOverrideSuccess,
}: ScoreDetailsModalProps) {
  const { user } = useAuthStore()
  const canOverride = user?.role === 'admin' || user?.role === 'scorer'
  const [activeTab, setActiveTab] = useState<'annotated' | 'raw'>('annotated')
  const [overrideZone, setOverrideZone] = useState<number>(score?.zone ?? 0)
  const [overridePoints, setOverridePoints] = useState<number>(score?.points ?? 0)
  const [overrideReason, setOverrideReason] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)

  // Initialize values when modal opens/score changes
  useState(() => {
    if (score) {
      setOverrideZone(score.zone)
      setOverridePoints(score.points)
      setOverrideReason('')
    } else if (dryRunData) {
      setOverrideZone(dryRunData.zone)
      setOverridePoints(dryRunData.points)
      setOverrideReason('')
    }
  })

  if (!isOpen) return null

  const isDryRun = !!dryRunData
  const filename = isDryRun ? dryRunData.filename : `Score Record #${score?.id}`
  const zone = isDryRun ? dryRunData.zone : score?.zone
  const points = isDryRun ? dryRunData.points : score?.points
  const confidence = isDryRun ? dryRunData.confidence : score?.confidence ?? 0
  const method = isDryRun ? dryRunData.method : score?.method ?? 'unknown'
  const isValidated = isDryRun ? false : score?.validated_by_ai

  const handleOverrideSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!score) return

    setIsSubmitting(true)
    try {
      await scoresApi.override(score.id, {
        zone: overrideZone,
        points: overridePoints,
        reason: overrideReason,
      })
      toast.success('Score overridden successfully')
      if (onOverrideSuccess) {
        onOverrideSuccess()
      }
      onClose()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to override score')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Determine Image sources
  const rawImageSrc = score ? scoresApi.getRawImageUrl(score.id) : ''
  const annotatedImageSrc = score ? scoresApi.getAnnotatedImageUrl(score.id) : ''
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
              <h3 className="text-base font-bold text-slate-100">Shot Analysis</h3>
              <button onClick={onClose} className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-navy-800">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Score Grid */}
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
              <div className="mt-6 border-t border-navy-800 pt-6">
                <h4 className="text-sm font-bold text-slate-200 flex items-center gap-2 mb-3">
                  <ShieldAlert className="w-4 h-4 text-rose-500 animate-pulse" />
                  Score Override
                </h4>
                
                {canOverride ? (
                  <form onSubmit={handleOverrideSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-slate-400 text-xs mb-1">Override Zone</label>
                        <input
                          type="number"
                          min="0"
                          max="10"
                          required
                          value={overrideZone}
                          onChange={(e) => setOverrideZone(parseInt(e.target.value) || 0)}
                          className="input-dark w-full py-1 text-sm text-center"
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
                          className="input-dark w-full py-1 text-sm text-center"
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
