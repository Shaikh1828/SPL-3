import { useState, useEffect } from 'react'
import { FolderOpen, Play, Activity, CheckCircle, AlertCircle, TrendingUp, Cpu, Award, Upload, Eye } from 'lucide-react'
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

export default function BatchTestingPage() {
  const { activeSession } = useSessionStore()
  const [sourceMode, setSourceMode] = useState<'upload' | 'server'>('upload')
  const [directoryPath, setDirectoryPath] = useState('')
  const [selectedFolderFiles, setSelectedFolderFiles] = useState<File[]>([])
  const [folderName, setFolderName] = useState('')
  const [currentProgress, setCurrentProgress] = useState(0)
  
  const [saveToSession, setSaveToSession] = useState(false)
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
    // If a score was overridden, reload its data to update the results list
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
  }

  useEffect(() => {
    const loadArchers = async () => {
      if (!activeSession) return
      try {
        const list = await sessionsApi.listArchers(activeSession.id)
        setArchers(Array.isArray(list) ? list : [])
        if (list && list.length > 0) {
          setSelectedArcherId(list[0].id)
        }
      } catch {
        toast.error('Failed to load session archers')
      }
    }
    loadArchers()
  }, [activeSession])

  const triggerFolderPicker = () => {
    if (isLoading) return
    const input = document.getElementById('folder-picker')
    if (input) {
      input.click()
    }
  }

  const handleFolderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    // Filter only images (JPG, PNG, JPEG)
    const imageFiles = Array.from(files).filter(file =>
      /\.(jpe?g|png)$/i.test(file.name)
    )

    if (imageFiles.length === 0) {
      toast.error('No JPEG or PNG images found in the selected folder')
      return
    }

    // Get the name of the folder from the first file's webkitRelativePath
    const firstPath = imageFiles[0].webkitRelativePath
    const name = firstPath ? firstPath.split('/')[0] : 'Selected Folder'

    setSelectedFolderFiles(imageFiles)
    setFolderName(name)
    setResults([]) // Clear old results when folder changes
    toast.success(`Loaded ${imageFiles.length} images from folder "${name}"`)
  }

  const handleRunBatch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeSession) {
      toast.error('You need an active session to use this tool.')
      return
    }

    if (sourceMode === 'server' && !directoryPath) {
      toast.error('Please enter a directory path')
      return
    }

    if (sourceMode === 'upload' && selectedFolderFiles.length === 0) {
      toast.error('Please select a folder with images first')
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

        toast.loading('Scanning server folder and scoring images...', { id: 'batch-toast' })
        const res = await scoresApi.batchDirectory(activeSession.id, payload)
        
        setResults(res)
        
        const successCount = res.filter(r => r.status === 'success').length
        const errorCount = res.filter(r => r.status === 'error').length
        
        toast.success(
          `Batch scan complete! Processed ${res.length} files (${successCount} succeeded, ${errorCount} failed)`,
          { id: 'batch-toast' }
        )
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || 'Batch processing failed'
        toast.error(errorMsg, { id: 'batch-toast' })
      } finally {
        setIsLoading(false)
      }
    } else {
      // Browser-side folder upload mode
      toast.loading(`Scoring images: 0 / ${selectedFolderFiles.length}`, { id: 'batch-toast' })
      const tempResults: BatchResult[] = []

      for (let i = 0; i < selectedFolderFiles.length; i++) {
        const file = selectedFolderFiles[i]
        setCurrentProgress(i)
        
        toast.loading(`Scoring images: ${i + 1} / ${selectedFolderFiles.length} (${file.name})`, { id: 'batch-toast' })

        try {
          const formData = new FormData()
          formData.append('file', file)
          formData.append('session_archer_id', saveToSession ? selectedArcherId.toString() : '0')
          formData.append('round', roundNumber.toString())

          // Upload and score image file
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
            error: err.response?.data?.detail || 'Upload or CV pipeline failed'
          })
        }
        
        // Update results state dynamically after each file
        setResults([...tempResults])
      }

      setCurrentProgress(selectedFolderFiles.length)
      
      const successCount = tempResults.filter(r => r.status === 'success').length
      const errorCount = tempResults.filter(r => r.status === 'error').length
      
      toast.success(
        `Batch processing complete! Processed ${tempResults.length} files (${successCount} succeeded, ${errorCount} failed)`,
        { id: 'batch-toast' }
      )
      setIsLoading(false)
    }
  }

  // Calculate statistics
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

  if (!activeSession) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <FolderOpen className="w-16 h-16 text-slate-700 mb-4" />
        <h2 className="text-xl font-semibold text-slate-200 mb-2">No Active Session</h2>
        <p className="text-slate-500 mb-6 max-w-md">
          You need an active session to use the batch directory scorer. Go to Tournaments to start one.
        </p>
      </div>
    )
  }

  return (
    <div className="p-6 h-full flex flex-col space-y-6 overflow-y-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
          <FolderOpen className="text-gold-500 w-7 h-7" />
          Batch Folder Scorer
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Scan and automatically score all target pictures in a directory using the backend CV pipeline.
        </p>
      </div>

      {/* Control Panel */}
      <div className="glass-card p-6 border border-navy-700">
        {/* Source Mode Tabs */}
        <div className="flex border-b border-navy-750 mb-6">
          <button
            type="button"
            className={cn(
              "px-4 py-2 text-sm font-semibold border-b-2 transition-colors mr-4",
              sourceMode === 'upload'
                ? "border-gold-500 text-gold-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            )}
            onClick={() => !isLoading && setSourceMode('upload')}
            disabled={isLoading}
          >
            Browse Folder (Upload)
          </button>
          <button
            type="button"
            className={cn(
              "px-4 py-2 text-sm font-semibold border-b-2 transition-colors",
              sourceMode === 'server'
                ? "border-gold-500 text-gold-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            )}
            onClick={() => !isLoading && setSourceMode('server')}
            disabled={isLoading}
          >
            Local Server Path
          </button>
        </div>

        <form onSubmit={handleRunBatch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              {sourceMode === 'upload' ? (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Select Target Folder *
                  </label>
                  
                  <div
                    onClick={triggerFolderPicker}
                    className={cn(
                      "border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[140px]",
                      isLoading 
                        ? "opacity-50 cursor-not-allowed border-navy-700 bg-navy-800/5" 
                        : "border-navy-600 hover:border-gold-500/50 bg-navy-800/10 hover:bg-navy-800/20"
                    )}
                  >
                    <input
                      type="file"
                      id="folder-picker"
                      className="hidden"
                      multiple
                      {...({ webkitdirectory: '', directory: '' } as any)}
                      onChange={handleFolderChange}
                      disabled={isLoading}
                    />
                    <Upload className="w-8 h-8 text-slate-400 mb-2 transition-colors" />
                    {folderName ? (
                      <div>
                        <p className="text-sm font-semibold text-emerald-400">
                          Folder: "{folderName}"
                        </p>
                        <p className="text-xs text-slate-400 mt-1">
                          Ready to score {selectedFolderFiles.length} image files. Click to select another.
                        </p>
                      </div>
                    ) : (
                      <div>
                        <p className="text-sm font-medium text-slate-300">
                          Click to browse and choose folder
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          Selects all image files (.jpg, .png) inside the folder.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Local Directory Path *
                  </label>
                  <input
                    type="text"
                    required
                    value={directoryPath}
                    onChange={e => setDirectoryPath(e.target.value)}
                    placeholder="e.g. C:\Users\Shaikhul\Pictures\shots"
                    className="input-dark w-full"
                    disabled={isLoading}
                  />
                  <span className="text-xs text-slate-500 mt-1 block">
                    Path must exist on the local machine hosting the backend server.
                  </span>
                </div>
              )}

              <div className="flex items-center gap-3 pt-2">
                <input
                  type="checkbox"
                  id="saveToSession"
                  checked={saveToSession}
                  onChange={e => setSaveToSession(e.target.checked)}
                  className="w-4 h-4 accent-gold-500 rounded border-navy-700 bg-navy-800"
                  disabled={isLoading}
                />
                <label htmlFor="saveToSession" className="text-sm font-medium text-slate-300 cursor-pointer">
                  Save scored results to the active session database
                </label>
              </div>
            </div>

            {saveToSession && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-navy-800/30 p-4 rounded-lg border border-navy-750 animate-in">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Select Archer
                  </label>
                  <select
                    value={selectedArcherId}
                    onChange={e => setSelectedArcherId(parseInt(e.target.value) || 0)}
                    className="input-dark w-full"
                    disabled={isLoading}
                  >
                    {archers.map(a => (
                      <option key={a.id} value={a.id}>
                        {a.archer_name} (Lane {a.lane_number})
                      </option>
                    ))}
                    {archers.length === 0 && (
                      <option value="0">No archers in session</option>
                    )}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Round/End Number
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={roundNumber}
                    onChange={e => setRoundNumber(parseInt(e.target.value) || 1)}
                    className="input-dark w-full"
                    disabled={isLoading}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Real-time upload progress bar */}
          {isLoading && sourceMode === 'upload' && selectedFolderFiles.length > 0 && (
            <div className="mt-4 space-y-2 bg-navy-900/20 p-3 rounded border border-navy-750">
              <div className="flex justify-between text-xs font-semibold text-slate-300">
                <span className="flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-gold-500 animate-pulse" />
                  Uploading and Scoring Images...
                </span>
                <span>
                  {currentProgress} / {selectedFolderFiles.length} files ({Math.round((currentProgress / selectedFolderFiles.length) * 100)}%)
                </span>
              </div>
              <div className="w-full bg-navy-850 h-2 rounded-full overflow-hidden border border-navy-700">
                <div 
                  className="bg-gold-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${(currentProgress / selectedFolderFiles.length) * 100}%` }}
                />
              </div>
            </div>
          )}

          <div className="pt-2 border-t border-navy-750 flex justify-end">
            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary flex items-center justify-center gap-2 px-6 py-2 disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Activity className="w-5 h-5 animate-spin" />
                  <span>Scoring...</span>
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  <span>Run Batch Scorer</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Progress & Stats Summary */}
      {results.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 animate-in">
          <div className="glass-card p-4 flex items-center gap-4 border border-navy-700">
            <div className="p-3 bg-navy-800 rounded-lg text-slate-400">
              <FolderOpen className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium uppercase">Total Scored</p>
              <h3 className="text-xl font-bold text-slate-100">{totalFiles}</h3>
            </div>
          </div>

          <div className="glass-card p-4 flex items-center gap-4 border border-navy-700">
            <div className="p-3 bg-emerald-500/10 rounded-lg text-emerald-400">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium uppercase">Average Score</p>
              <h3 className="text-xl font-bold text-slate-100">{averageScore} <span className="text-xs font-normal text-slate-400">pts</span></h3>
            </div>
          </div>

          <div className="glass-card p-4 flex items-center gap-4 border border-navy-700">
            <div className="p-3 bg-gold-500/10 rounded-lg text-gold-400">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium uppercase">Average Confidence</p>
              <h3 className="text-xl font-bold text-slate-100">{averageConfidence}%</h3>
            </div>
          </div>

          <div className="glass-card p-4 flex items-center gap-4 border border-navy-700">
            <div className="p-3 bg-navy-800 rounded-lg">
              <div className="flex gap-1.5 text-xs font-bold text-slate-200">
                <span className="text-emerald-400">{successCount} OK</span>
                <span>/</span>
                <span className="text-red-400">{failedCount} ERR</span>
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium uppercase">Accuracy Rate</p>
              <h3 className="text-xl font-bold text-slate-100">
                {totalFiles > 0 ? ((successCount / totalFiles) * 100).toFixed(0) : 0}%
              </h3>
            </div>
          </div>
        </div>
      )}

      {/* Results Table */}
      {results.length > 0 && (
        <div className="glass-card overflow-hidden border border-navy-700 flex-1 flex flex-col min-h-[300px]">
          <div className="px-6 py-4 border-b border-navy-700 flex justify-between items-center bg-navy-800/20">
            <h2 className="font-semibold text-slate-200 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-gold-500" />
              Scored Files List
            </h2>
          </div>
          <div className="overflow-auto flex-1">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-navy-700 bg-navy-900/40 text-xs text-slate-500 font-semibold uppercase">
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Filename</th>
                  <th className="px-6 py-3">Detected Score</th>
                  <th className="px-6 py-3">AI Confidence</th>
                  <th className="px-6 py-3">Detection Method</th>
                  <th className="px-6 py-3">DB Score ID</th>
                  <th className="px-6 py-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-750 text-sm text-slate-300">
                {results.map((result, idx) => (
                  <tr key={idx} className="hover:bg-navy-800/20 transition-colors">
                    <td className="px-6 py-3.5">
                      {result.status === 'success' ? (
                        <div className="flex items-center gap-1.5 text-emerald-400 text-xs">
                          <CheckCircle className="w-4 h-4" />
                          <span>Scored</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-red-400 text-xs">
                          <AlertCircle className="w-4 h-4" />
                          <span>Error</span>
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-3.5 font-medium max-w-[200px] truncate" title={result.path}>
                      {result.filename}
                    </td>
                    <td className="px-6 py-3.5">
                      {result.status === 'success' ? (
                        <span className="font-bold text-slate-200">{result.points} pts</span>
                      ) : (
                        <span className="text-red-400/80 text-xs" title={result.error}>
                          {result.error || 'Scoring failed'}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-3.5">
                      {result.status === 'success' ? (
                        <span className={cn("font-bold text-xs", getConfidenceColor(result.confidence))}>
                          {Math.round(result.confidence * 100)}%
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-6 py-3.5 text-xs text-slate-400">
                      {result.status === 'success' ? result.method : '—'}
                    </td>
                    <td className="px-6 py-3.5 text-xs font-mono text-slate-500">
                      {result.score_id ? `#${result.score_id}` : '—'}
                    </td>
                    <td className="px-6 py-3.5">
                      {result.status === 'success' && (
                        <button
                          onClick={() => handleViewResult(result)}
                          className="text-gold-400 hover:text-gold-300 font-semibold text-xs flex items-center gap-1 bg-gold-500/10 hover:bg-gold-500/20 px-2 py-1 rounded transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          View
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
