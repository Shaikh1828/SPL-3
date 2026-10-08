import React, { useState, useEffect } from 'react'
import { FolderOpen, Play, Activity, CheckCircle, AlertCircle, TrendingUp, Cpu, Award, Upload, Eye, ChevronDown, ChevronUp } from 'lucide-react'
import { scoresApi } from '@/api/scores'
import { sessionsApi } from '@/api/sessions'
import { useSessionStore } from '@/store/sessionStore'
import type { SessionArcher, Score } from '@/types'
import toast from 'react-hot-toast'
import { cn, getConfidenceColor } from '@/lib/utils'
import { ScoreDetailsModal } from '@/components/scores/ScoreDetailsModal'

interface BatchResult {
  filename: string
  path: string
  zone: number
  points: number
  confidence: number
  method: string
  image_id: string | null
  score_id: number | null
  status: 'success' | 'error'
  error?: string
  annotated_image?: string | null
}

interface BatchScoringSectionProps {
  onScoreUpdated?: () => Promise<void> | void
}

export default function BatchScoringSection({ onScoreUpdated }: BatchScoringSectionProps) {
  const { activeSession } = useSessionStore()
  const [isExpanded, setIsExpanded] = useState(true)
  const [sourceMode, setSourceMode] = useState<'upload' | 'server'>('upload')
  const [directoryPath, setDirectoryPath] = useState('')
  const [selectedFolderFiles, setSelectedFolderFiles] = useState<File[]>([])
  const [folderName, setFolderName] = useState('')
  const [currentProgress, setCurrentProgress] = useState(0)

  const [saveToSession, setSaveToSession] = useState(true)
  const [selectedArcherId, setSelectedArcherId] = useState<number>(0)
  const [roundNumber, setRoundNumber] = useState<number>(1)
  const [archers, setArchers] = useState<SessionArcher[]>([])

  const [isLoading, setIsLoading] = useState(false)
  const [results, setResults] = useState<BatchResult[]>([])

  // Modal states
  const [selectedScore, setSelectedScore] = useState<Score | null>(null)
  const [dryRunScoreData, setDryRunScoreData] = useState<any | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleViewResult = async (result: BatchResult) => {
    if (result.score_id) {
      try {
        toast.loading('Fetching score record...', { id: 'fetch-score' })
        const score = await scoresApi.get(result.score_id)
        setSelectedScore(score)
        setDryRunScoreData(null)
        setIsModalOpen(true)
        toast.dismiss('fetch-score')
      } catch {
        toast.error('Failed to load score record', { id: 'fetch-score' })
      }
    } else {
      setSelectedScore(null)
      setDryRunScoreData({
        filename: result.filename,
        zone: result.zone,
        points: result.points,
        confidence: result.confidence,
        method: result.method,
        annotated_image: result.annotated_image || null,
      })
      setIsModalOpen(true)
    }
  }

  const handleOverrideSuccess = async () => {
    if (selectedScore) {
      try {
        const updated = await scoresApi.get(selectedScore.id)
        setResults(prev =>
          prev.map(r =>
            r.score_id === updated.id
              ? { ...r, zone: updated.zone, points: updated.points, confidence: updated.confidence ?? 0 }
              : r
          )
        )
      } catch {}
    }
    if (onScoreUpdated) {
      await onScoreUpdated()
    }
  }

  useEffect(() => {
    const loadArchers = async () => {
      if (!activeSession) return
      try {
        const list = await sessionsApi.listArchers(activeSession.id)
        const archerList = Array.isArray(list) ? list : []
        setArchers(archerList)
        if (archerList.length > 0 && !selectedArcherId) {
          setSelectedArcherId(archerList[0].id)
        }
      } catch {
        // Handled silently
      }
    }
    loadArchers()
  }, [activeSession])

  const triggerFolderPicker = () => {
    if (isLoading) return
    const input = document.getElementById('batch-folder-picker')
    if (input) {
      input.click()
    }
  }

  const handleFolderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const imageFiles = Array.from(files).filter(file =>
      /\.(jpe?g|png)$/i.test(file.name)
    )

    if (imageFiles.length === 0) {
      toast.error('No JPEG or PNG images found in the selected folder')
      return
    }

    const firstPath = imageFiles[0].webkitRelativePath
    const name = firstPath ? firstPath.split('/')[0] : 'Selected Folder'

    setSelectedFolderFiles(imageFiles)
    setFolderName(name)
    setResults([])
    toast.success(`Loaded ${imageFiles.length} images from folder "${name}"`)
  }

  const handleRunBatch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeSession) {
      toast.error('Active tournament session required')
      return
    }

    if (sourceMode === 'server' && !directoryPath) {
      toast.error('Please enter a server directory path')
      return
    }

    if (sourceMode === 'upload' && selectedFolderFiles.length === 0) {
      toast.error('Please select an image folder first')
      return
    }

    setIsLoading(true)
    setResults([])
    setCurrentProgress(0)

    if (sourceMode === 'server') {
      try {
        const payload = {
          directory_path: directoryPath,
          session_archer_id: saveToSession ? selectedArcherId : 0,
          round: roundNumber,
        }

        toast.loading('Scanning and scoring server folder images...', { id: 'batch-toast' })
        const res = await scoresApi.batchDirectory(activeSession.id, payload)
        setResults(res)

        const successCount = res.filter(r => r.status === 'success').length
        const errorCount = res.filter(r => r.status === 'error').length

        toast.success(
          `Batch completed: ${res.length} files (${successCount} scored, ${errorCount} errors)`,
          { id: 'batch-toast' }
        )
        if (onScoreUpdated) onScoreUpdated()
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || 'Batch processing failed'
        toast.error(errorMsg, { id: 'batch-toast' })
      } finally {
        setIsLoading(false)
      }
    } else {
      toast.loading(`Scoring images: 0 / ${selectedFolderFiles.length}`, { id: 'batch-toast' })
      const tempResults: BatchResult[] = []

      for (let i = 0; i < selectedFolderFiles.length; i++) {
        const file = selectedFolderFiles[i]
        setCurrentProgress(i)

        try {
          const formData = new FormData()
          formData.append('file', file)
          formData.append('session_archer_id', saveToSession ? selectedArcherId.toString() : '0')
          formData.append('round', roundNumber.toString())

          const score = await scoresApi.upload(activeSession.id, formData)

          tempResults.push({
            filename: file.name,
            path: file.webkitRelativePath || file.name,
            zone: score.zone,
            points: score.points,
            confidence: score.confidence || 0,
            method: score.method || 'unknown',
            image_id: score.image_id || null,
            score_id: score.id || null,
            status: 'success',
            annotated_image: score.annotated_image || null
          })
        } catch (err: any) {
          tempResults.push({
            filename: file.name,
            path: file.webkitRelativePath || file.name,
            zone: 0,
            points: 0,
            confidence: 0,
            method: '—',
            image_id: null,
            score_id: null,
            status: 'error',
            error: err.response?.data?.detail || 'Scoring pipeline failed'
          })
        }

        setResults([...tempResults])
      }

      setCurrentProgress(selectedFolderFiles.length)
      const successCount = tempResults.filter(r => r.status === 'success').length
      const errorCount = tempResults.filter(r => r.status === 'error').length

      toast.success(
        `Batch complete: ${tempResults.length} files (${successCount} scored, ${errorCount} errors)`,
        { id: 'batch-toast' }
      )
      setIsLoading(false)
      if (onScoreUpdated) onScoreUpdated()
    }
  }

  const totalFiles = results.length
  const successFiles = results.filter(r => r.status === 'success')
  const failedFiles = results.filter(r => r.status === 'error')
  const successCount = successFiles.length
  const failedCount = failedFiles.length

  const averageScore = successCount > 0
    ? (successFiles.reduce((acc, curr) => acc + curr.points, 0) / successCount).toFixed(1)
    : '0'

  const averageConfidence = successCount > 0
    ? (successFiles.reduce((acc, curr) => acc + curr.confidence, 0) / successCount * 100).toFixed(0)
    : '0'

  return (
    <div className="bg-navy-900/90 border border-navy-700 rounded-2xl p-6 shadow-2xl space-y-5">
      {/* Header & Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-navy-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gold-500/15 border border-gold-500/30 flex items-center justify-center flex-shrink-0">
            <FolderOpen className="w-5 h-5 text-gold-400" />
          </div>
          <div>
            <h3 className="text-base font-black text-slate-100 uppercase tracking-wider flex items-center gap-2">
              Batch Folder & Target Image Scorer
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Upload a folder of target photos or specify a server directory to auto-score multiple shots at once
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {results.length > 0 && (
            <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              {successCount}/{totalFiles} Scored
            </span>
          )}
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="px-3 py-1.5 rounded-xl bg-navy-800 hover:bg-navy-750 text-slate-300 border border-navy-700 text-xs font-bold flex items-center gap-1.5 transition-all"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-4 h-4" /> Minimize Batch Scorer
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" /> Expand Batch Scorer
              </>
            )}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="space-y-5">
          {/* Source Mode Tabs */}
          <div className="flex border-b border-navy-800">
            <button
              type="button"
              className={cn(
                'px-4 py-2 text-xs font-bold border-b-2 transition-all mr-3 flex items-center gap-2',
                sourceMode === 'upload'
                  ? 'border-gold-500 text-gold-400 bg-gold-500/5 rounded-t-lg'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              )}
              onClick={() => !isLoading && setSourceMode('upload')}
              disabled={isLoading}
            >
              <Upload className="w-3.5 h-3.5" />
              Browse Local Folder (Upload)
            </button>
            <button
              type="button"
              className={cn(
                'px-4 py-2 text-xs font-bold border-b-2 transition-all flex items-center gap-2',
                sourceMode === 'server'
                  ? 'border-gold-500 text-gold-400 bg-gold-500/5 rounded-t-lg'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              )}
              onClick={() => !isLoading && setSourceMode('server')}
              disabled={isLoading}
            >
              <Cpu className="w-3.5 h-3.5" />
              Local Server Directory Path
            </button>
          </div>

          <form onSubmit={handleRunBatch} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="space-y-3">
                {sourceMode === 'upload' ? (
                  <div>
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                      Select Target Image Folder *
                    </label>

                    <div
                      onClick={triggerFolderPicker}
                      className={cn(
                        'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[130px]',
                        isLoading
                          ? 'opacity-50 cursor-not-allowed border-navy-700 bg-navy-950/40'
                          : 'border-navy-600 hover:border-gold-400/60 bg-navy-950/50 hover:bg-navy-950/80 group'
                      )}
                    >
                      <input
                        type="file"
                        id="batch-folder-picker"
                        className="hidden"
                        multiple
                        {...({ webkitdirectory: '', directory: '' } as any)}
                        onChange={handleFolderChange}
                        disabled={isLoading}
                      />
                      <Upload className="w-8 h-8 text-slate-400 group-hover:text-gold-400 mb-2 transition-colors" />
                      {folderName ? (
                        <div>
                          <p className="text-xs font-bold text-emerald-400">
                            Folder: "{folderName}"
                          </p>
                          <p className="text-[11px] text-slate-400 mt-1">
                            Ready to score {selectedFolderFiles.length} images. Click to choose another folder.
                          </p>
                        </div>
                      ) : (
                        <div>
                          <p className="text-xs font-bold text-slate-200">
                            Click to select an entire folder of target photos
                          </p>
                          <p className="text-[10px] text-slate-400 mt-1">
                            Automatically loads and scores all .JPG and .PNG files
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div>
                    <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                      Local Server Directory Path *
                    </label>
                    <input
                      type="text"
                      required
                      value={directoryPath}
                      onChange={e => setDirectoryPath(e.target.value)}
                      placeholder="e.g. C:\ArcheryData\Session_01_Images"
                      className="input-dark w-full text-xs"
                      disabled={isLoading}
                    />
                    <span className="text-[10px] text-slate-500 mt-1 block">
                      Absolute path accessible on the server hosting the system.
                    </span>
                  </div>
                )}

                <div className="flex items-center gap-2.5 pt-1">
                  <input
                    type="checkbox"
                    id="batchSaveToSession"
                    checked={saveToSession}
                    onChange={e => setSaveToSession(e.target.checked)}
                    className="w-4 h-4 accent-gold-500 rounded border-navy-700 bg-navy-800"
                    disabled={isLoading}
                  />
                  <label htmlFor="batchSaveToSession" className="text-xs font-semibold text-slate-300 cursor-pointer">
                    Save scored points & arrows directly to active session database
                  </label>
                </div>
              </div>

              {/* Session Archer & Round Assignment */}
              <div className="space-y-3 bg-navy-950/70 p-4 rounded-xl border border-navy-800 flex flex-col justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Score Attribution
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                        Assign to Archer
                      </label>
                      <select
                        value={selectedArcherId}
                        onChange={e => setSelectedArcherId(parseInt(e.target.value) || 0)}
                        className="input-dark w-full text-xs"
                        disabled={isLoading || !saveToSession}
                      >
                        {archers.map(a => (
                          <option key={a.id} value={a.id}>
                            Lane {a.lane_number}: {a.archer_name}
                          </option>
                        ))}
                        {archers.length === 0 && (
                          <option value="0">No archers in session</option>
                        )}
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                        End / Round Number
                      </label>
                      <input
                        type="number"
                        min="1"
                        value={roundNumber}
                        onChange={e => setRoundNumber(parseInt(e.target.value) || 1)}
                        className="input-dark w-full text-xs"
                        disabled={isLoading || !saveToSession}
                      />
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-navy-800 flex justify-end">
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="btn-primary flex items-center justify-center gap-2 px-6 py-2.5 text-xs font-bold disabled:opacity-50 shadow-lg shadow-gold-500/20"
                  >
                    {isLoading ? (
                      <>
                        <Activity className="w-4 h-4 animate-spin" />
                        <span>Scoring Images ({currentProgress}/{selectedFolderFiles.length || '...'})</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4" />
                        <span>Start Batch Processing</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Real-time Progress Bar */}
            {isLoading && sourceMode === 'upload' && selectedFolderFiles.length > 0 && (
              <div className="space-y-1.5 bg-navy-950 p-3 rounded-xl border border-navy-800">
                <div className="flex justify-between text-xs font-semibold text-slate-300">
                  <span className="flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5 text-gold-400 animate-pulse" />
                    Analyzing Target Images with YOLO AI Vision...
                  </span>
                  <span>
                    {currentProgress} / {selectedFolderFiles.length} files ({Math.round((currentProgress / selectedFolderFiles.length) * 100)}%)
                  </span>
                </div>
                <div className="w-full bg-navy-900 h-2 rounded-full overflow-hidden border border-navy-700">
                  <div
                    className="bg-gradient-to-r from-gold-500 to-amber-400 h-full rounded-full transition-all duration-300"
                    style={{ width: `${(currentProgress / selectedFolderFiles.length) * 100}%` }}
                  />
                </div>
              </div>
            )}
          </form>

          {/* Progress & Stats Summary */}
          {results.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-navy-950/80 p-3.5 rounded-xl border border-navy-800 flex items-center gap-3">
                <div className="p-2.5 bg-navy-800 rounded-lg text-slate-400">
                  <FolderOpen className="w-5 h-5 text-gold-400" />
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Total Scored</p>
                  <h3 className="text-lg font-black text-slate-100">{totalFiles}</h3>
                </div>
              </div>

              <div className="bg-navy-950/80 p-3.5 rounded-xl border border-navy-800 flex items-center gap-3">
                <div className="p-2.5 bg-emerald-500/10 rounded-lg text-emerald-400">
                  <Award className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Average Score</p>
                  <h3 className="text-lg font-black text-slate-100">{averageScore} <span className="text-xs font-normal text-slate-400">pts</span></h3>
                </div>
              </div>

              <div className="bg-navy-950/80 p-3.5 rounded-xl border border-navy-800 flex items-center gap-3">
                <div className="p-2.5 bg-gold-500/10 rounded-lg text-gold-400">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Avg Confidence</p>
                  <h3 className="text-lg font-black text-slate-100">{averageConfidence}%</h3>
                </div>
              </div>

              <div className="bg-navy-950/80 p-3.5 rounded-xl border border-navy-800 flex items-center gap-3">
                <div className="p-2.5 bg-navy-800 rounded-lg">
                  <div className="flex gap-1 text-[11px] font-bold">
                    <span className="text-emerald-400">{successCount} OK</span>
                    <span>/</span>
                    <span className="text-rose-400">{failedCount} ERR</span>
                  </div>
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Success Rate</p>
                  <h3 className="text-lg font-black text-slate-100">
                    {totalFiles > 0 ? ((successCount / totalFiles) * 100).toFixed(0) : 0}%
                  </h3>
                </div>
              </div>
            </div>
          )}

          {/* Results Table */}
          {results.length > 0 && (
            <div className="bg-navy-950 rounded-xl overflow-hidden border border-navy-800 flex flex-col max-h-[360px]">
              <div className="px-4 py-3 border-b border-navy-800 flex justify-between items-center bg-navy-900/60">
                <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                  <Cpu className="w-3.5 h-3.5 text-gold-400" />
                  Scored Images List ({results.length} files)
                </h4>
              </div>
              <div className="overflow-auto flex-1">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-navy-800 bg-navy-900/40 text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                      <th className="px-4 py-2.5">Status</th>
                      <th className="px-4 py-2.5">Filename</th>
                      <th className="px-4 py-2.5">Score</th>
                      <th className="px-4 py-2.5">Confidence</th>
                      <th className="px-4 py-2.5">Method</th>
                      <th className="px-4 py-2.5">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-navy-850 text-slate-300 font-medium">
                    {results.map((result, idx) => (
                      <tr key={idx} className="hover:bg-navy-900/40 transition-colors">
                        <td className="px-4 py-2">
                          {result.status === 'success' ? (
                            <div className="flex items-center gap-1 text-emerald-400 text-[11px] font-bold">
                              <CheckCircle className="w-3.5 h-3.5" />
                              <span>Scored</span>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1 text-rose-400 text-[11px] font-bold">
                              <AlertCircle className="w-3.5 h-3.5" />
                              <span>Error</span>
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-2 max-w-[220px] truncate" title={result.path}>
                          {result.filename}
                        </td>
                        <td className="px-4 py-2 font-bold text-slate-100">
                          {result.status === 'success' ? `${result.points} pts (Ring ${result.zone})` : '—'}
                        </td>
                        <td className="px-4 py-2">
                          {result.status === 'success' ? (
                            <span className={cn('font-bold', getConfidenceColor(result.confidence))}>
                              {Math.round(result.confidence * 100)}%
                            </span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-slate-400">
                          {result.status === 'success' ? result.method : '—'}
                        </td>
                        <td className="px-4 py-2">
                          {result.status === 'success' && (
                            <button
                              onClick={() => handleViewResult(result)}
                              className="text-gold-400 hover:text-gold-300 font-bold text-xs flex items-center gap-1 bg-gold-500/10 hover:bg-gold-500/20 px-2.5 py-1 rounded-lg transition-colors"
                            >
                              <Eye className="w-3 h-3" />
                              Inspect
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Score details and override modal */}
      <ScoreDetailsModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedScore(null)
          setDryRunScoreData(null)
        }}
        score={selectedScore}
        dryRunData={dryRunScoreData}
        onOverrideSuccess={handleOverrideSuccess}
      />
    </div>
  )
}
