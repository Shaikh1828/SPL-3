import { useState, useEffect, useRef } from 'react'
import { Camera as CameraIcon, Target, Activity, Square, Trophy, Plus, Trash2, X, Upload } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { camerasApi } from '@/api/cameras'
import { scoresApi } from '@/api/scores'
import { sessionsApi } from '@/api/sessions'
import { useSessionStore } from '@/store/sessionStore'
import { useCameraStore } from '@/store/cameraStore'
import { useCameraPreview } from '@/hooks/useCameraPreview'
import { ScoreDetailsModal } from '@/components/scores/ScoreDetailsModal'
import toast from 'react-hot-toast'
import { cn, getConfidenceColor } from '@/lib/utils'
import type { Camera, CameraLaneAssignment, Score, SessionArcher } from '@/types'

function CameraFeed({ cameraId, label, status }: { cameraId: number, label: string, status: string }) {
  const imgRef = useRef<HTMLImageElement>(null)
  useCameraPreview(cameraId, imgRef)

  return (
    <div className="relative aspect-video bg-black rounded-lg overflow-hidden border border-navy-700">
      {status === 'connected' ? (
        <>
          <img ref={imgRef} className="w-full h-full object-contain" alt={label} />
          {/* Targeting overlay */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-30">
            <div className="w-48 h-48 border-2 border-dashed border-gold-500 rounded-full" />
            <div className="w-1 h-1 bg-gold-500 rounded-full absolute" />
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center h-full text-slate-500">
          <CameraIcon className="w-8 h-8 mb-2 opacity-50" />
          <p className="text-sm">Camera Disconnected</p>
        </div>
      )}
      <div className="absolute top-2 left-2 flex items-center gap-2 bg-black/60 backdrop-blur-sm px-2 py-1 rounded text-xs">
        <div className={cn("w-2 h-2 rounded-full", status === 'connected' ? 'bg-emerald-500' : 'bg-red-500')} />
        <span className="text-slate-200">{label}</span>
      </div>
    </div>
  )
}

function ScoringLane({ 
  assignment, 
  camera, 
  archer, 
  onCalculate, 
  onUploadImage,
  isCalculating,
  lastScore,
  onViewImage
}: { 
  assignment: CameraLaneAssignment, 
  camera?: Camera,
  archer?: SessionArcher,
  onCalculate: (cameraId: number, laneId: number) => void,
  onUploadImage: (laneId: number, file: File) => void,
  isCalculating: boolean,
  lastScore?: Score | null,
  onViewImage: (score: Score) => void
}) {
  return (
    <div className="glass-card p-4 flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="font-semibold text-slate-200">Lane {assignment.lane}</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Archer: <span className="text-gold-400 font-medium">{archer?.archer_name ?? 'Unassigned'}</span>
          </p>
          <p className="text-xs text-slate-500 mt-0.5">Camera: {camera?.name ?? 'Unknown'}</p>
        </div>
      </div>

      <CameraFeed 
        cameraId={assignment.camera_id} 
        label={`Lane ${assignment.lane}`} 
        status={camera?.status ?? 'disconnected'} 
      />

      <div className="flex flex-col gap-2 mt-2">
        <button
          onClick={() => onCalculate(assignment.camera_id, assignment.lane)}
          disabled={isCalculating || camera?.status !== 'connected' || !archer}
          className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {isCalculating ? (
            <><Activity className="w-4 h-4 animate-spin" /> Analyzing...</>
          ) : (
            <><CameraIcon className="w-4 h-4" /> Calculate Score</>
          )}
        </button>

        <label className={cn(
          "btn-ghost w-full flex items-center justify-center gap-2 cursor-pointer border border-dashed border-navy-600 hover:border-gold-500 hover:text-gold-400 py-2 rounded-lg text-sm transition-colors",
          (isCalculating || !archer) && "opacity-50 pointer-events-none"
        )}>
          <Upload className="w-4 h-4" />
          <span>Upload Shot Image</span>
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) {
                onUploadImage(assignment.lane, file)
              }
              e.target.value = ''
            }}
            disabled={isCalculating || !archer}
          />
        </label>
      </div>

      {lastScore && (
        <div className="mt-2 p-3 bg-navy-800/50 rounded-lg border border-navy-700">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-slate-300">Last Result</span>
            <span className={cn("font-bold", getConfidenceColor(lastScore.confidence ?? 1))}>
              {lastScore.points} pts
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Arrow {lastScore.arrow_num} / Round {lastScore.round}</span>
            <button 
              onClick={() => onViewImage(lastScore)}
              className="text-gold-400 hover:text-gold-300 font-semibold"
            >
              View Image
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ScoringPage() {
  const navigate = useNavigate()
  const { activeSession, currentEnd, setCurrentEnd } = useSessionStore()
  const { cameras, setCameras } = useCameraStore()
  const [assignments, setAssignments] = useState<CameraLaneAssignment[]>([])
  const [archers, setArchers] = useState<SessionArcher[]>([])
  const [calculating, setCalculating] = useState<Record<number, boolean>>({})
  const [lastScores, setLastScores] = useState<Record<number, Score | null>>({})

  // Modal states
  const [selectedScore, setSelectedScore] = useState<Score | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Archer Modal state
  const [isAddArcherOpen, setIsAddArcherOpen] = useState(false)
  const [newArcherName, setNewArcherName] = useState('')
  const [newArcherLane, setNewArcherLane] = useState<number>(1)

  const loadData = async () => {
    if (!activeSession) return
    try {
      // Load cameras
      const cams = await camerasApi.listForSession(activeSession.id)
      setCameras(Array.isArray(cams) ? cams : [])

      // Load assignments
      const assigns = await camerasApi.listAssignments(activeSession.id)
      setAssignments(Array.isArray(assigns) ? assigns : [])

      // Load archers
      const archList = await sessionsApi.listArchers(activeSession.id)
      setArchers(Array.isArray(archList) ? archList : [])
    } catch {
      toast.error('Failed to load session details')
    }
  }

  useEffect(() => {
    loadData()
  }, [activeSession])

  const handleCalculate = async (_cameraId: number, laneId: number) => {
    if (!activeSession) return
    const laneArcher = archers.find(a => a.lane_number === laneId)
    if (!laneArcher) {
      toast.error(`Please assign an archer to Lane ${laneId} first!`)
      return
    }

    setCalculating(prev => ({ ...prev, [laneId]: true }))
    try {
      const score = await scoresApi.record(activeSession.id, {
        session_archer_id: laneArcher.id,
        round: currentEnd,
        arrow_num: 1, // Mock
        zone: 9,
        points: 9,
        image_id: 'mock.jpg'
      })
      setLastScores(prev => ({ ...prev, [laneId]: score }))
      toast.success(`Score recorded for ${laneArcher.archer_name}: ${score.points}`)
      // Refresh archers list to get updated total score
      const archList = await sessionsApi.listArchers(activeSession.id)
      setArchers(Array.isArray(archList) ? archList : [])
    } catch (err) {
      toast.error('Scoring failed')
    } finally {
      setCalculating(prev => ({ ...prev, [laneId]: false }))
    }
  }

  const handleUploadImage = async (laneId: number, file: File) => {
    if (!activeSession) return
    const laneArcher = archers.find(a => a.lane_number === laneId)
    if (!laneArcher) {
      toast.error(`Please assign an archer to Lane ${laneId} first!`)
      return
    }

    setCalculating(prev => ({ ...prev, [laneId]: true }))
    try {
      const formData = new FormData()
      formData.append('session_archer_id', laneArcher.id.toString())
      formData.append('round', currentEnd.toString())
      formData.append('file', file)

      const score = await scoresApi.upload(activeSession.id, formData)
      
      setLastScores(prev => ({ ...prev, [laneId]: score }))
      toast.success(`Score recorded for ${laneArcher.archer_name}: ${score.points} pts (AI Confidence: ${Math.round((score.confidence ?? 0) * 100)}%)`)
      
      // Refresh archers list to get updated total score
      const archList = await sessionsApi.listArchers(activeSession.id)
      setArchers(Array.isArray(archList) ? archList : [])
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Image upload/scoring failed'
      toast.error(errorMsg)
    } finally {
      setCalculating(prev => ({ ...prev, [laneId]: false }))
    }
  }

  const handleCalculateAll = async () => {
    assignments.forEach(a => handleCalculate(a.camera_id, a.lane))
  }

  const handleAddArcher = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeSession) return
    if (!newArcherName) {
      toast.error('Please enter archer name')
      return
    }
    try {
      await sessionsApi.registerArcher(activeSession.id, {
        archer_name: newArcherName,
        lane_number: newArcherLane,
      })
      toast.success('Archer registered successfully')
      setNewArcherName('')
      setIsAddArcherOpen(false)
      // Refresh archers
      const archList = await sessionsApi.listArchers(activeSession.id)
      setArchers(Array.isArray(archList) ? archList : [])
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to add archer')
    }
  }

  const handleRemoveArcher = async (sessionArcherId: number) => {
    if (!activeSession) return
    if (!window.confirm('Remove this archer from the session?')) return
    try {
      await sessionsApi.removeArcher(activeSession.id, sessionArcherId)
      toast.success('Archer removed')
      // Refresh archers
      const archList = await sessionsApi.listArchers(activeSession.id)
      setArchers(Array.isArray(archList) ? archList : [])
    } catch {
      toast.error('Failed to remove archer')
    }
  }

  const handleEndSession = async () => {
    if (!activeSession) return
    if (!window.confirm('Are you sure you want to end this session? This will mark it as completed.')) return
    try {
      await sessionsApi.updateStatus(activeSession.id, 'completed')
      toast.success('Session completed successfully')
      useSessionStore.getState().setActiveSession(null)
      navigate('/tournaments')
    } catch {
      toast.error('Failed to end session')
    }
  }

  if (!activeSession) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <Target className="w-16 h-16 text-slate-700 mb-4" />
        <h2 className="text-xl font-semibold text-slate-200 mb-2">No Active Session</h2>
        <p className="text-slate-500 mb-6 max-w-md">
          You need an active session to use the scoring screen. Go to Tournaments to start one.
        </p>
      </div>
    )
  }

  return (
    <div className="p-6 h-full flex flex-col animate-in">
      {/* Header controls */}
      <div className="flex items-center justify-between mb-6 bg-navy-800 p-4 rounded-xl border border-navy-700">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">Session:</span>
            <span className="font-semibold text-slate-200">{activeSession.name}</span>
          </div>
          <div className="h-6 w-px bg-navy-700" />
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setCurrentEnd(Math.max(1, currentEnd - 1))}
              className="btn-ghost px-2 py-1 text-sm"
              disabled={currentEnd <= 1}
            >
              ◀ Prev End
            </button>
            <span className="font-bold text-gold-400 bg-gold-500/10 px-3 py-1 rounded-lg border border-gold-500/20">
              End {currentEnd} / {activeSession.arrows_per_round}
            </span>
            <button 
              onClick={() => setCurrentEnd(currentEnd + 1)}
              className="btn-ghost px-2 py-1 text-sm"
            >
              Next End ▶
            </button>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <button onClick={handleCalculateAll} className="btn-primary flex items-center gap-2">
            <CameraIcon className="w-4 h-4" />
            Calculate All
          </button>
          <button 
            onClick={handleEndSession}
            className="btn-ghost flex items-center gap-2 text-red-400 hover:text-red-300 hover:bg-red-500/10"
          >
            <Square className="w-4 h-4" />
            End Session
          </button>
        </div>
      </div>

      {/* Main Grid & Archers sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 overflow-y-auto min-h-0">
        {/* Camera Grid */}
        <div className="lg:col-span-3 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {assignments.map(assignment => {
              const laneArcher = archers.find(a => a.lane_number === assignment.lane)
              return (
                <ScoringLane
                  key={assignment.lane}
                  assignment={assignment}
                  camera={cameras.find(c => c.id === assignment.camera_id)}
                  archer={laneArcher}
                  onCalculate={handleCalculate}
                  onUploadImage={handleUploadImage}
                  isCalculating={calculating[assignment.lane] || false}
                  lastScore={lastScores[assignment.lane]}
                  onViewImage={(score) => {
                    setSelectedScore(score)
                    setIsModalOpen(true)
                  }}
                />
              )
            })}
            {assignments.length === 0 && (
              <div className="col-span-full py-12 text-center text-slate-500 border border-dashed border-navy-700 rounded-xl">
                No cameras assigned to lanes for this session. Go to Cameras to assign one.
              </div>
            )}
          </div>
        </div>

        {/* Archers List Sidebar */}
        <div className="glass-card p-5 h-fit flex flex-col space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-navy-700">
            <h2 className="font-semibold text-slate-200 flex items-center gap-2">
              <Trophy className="w-4 h-4 text-gold-400" />
              Archers
            </h2>
            <button 
              onClick={() => setIsAddArcherOpen(true)}
              className="btn-primary text-xs py-1 px-2.5 flex items-center gap-1"
            >
              <Plus className="w-3 h-3" /> Add Archer
            </button>
          </div>

          <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
            {archers.map(a => (
              <div key={a.id} className="flex items-center justify-between bg-navy-800/40 p-3 rounded-lg border border-navy-750">
                <div>
                  <p className="text-sm font-semibold text-slate-200">{a.archer_name}</p>
                  <p className="text-xs text-slate-500">Lane {a.lane_number ?? 'None'} · Score: {a.total_score}</p>
                </div>
                <button 
                  onClick={() => handleRemoveArcher(a.id)}
                  className="text-slate-500 hover:text-red-400 p-1 rounded transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            {archers.length === 0 && (
              <p className="text-sm text-slate-500 text-center py-4">No archers registered in this session.</p>
            )}
          </div>
        </div>
      </div>

      {/* Add Archer Modal */}
      {isAddArcherOpen && (
        <div className="fixed inset-0 bg-navy-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 space-y-4 animate-in">
            <div className="flex justify-between items-center pb-2 border-b border-navy-700">
              <h3 className="text-lg font-bold text-slate-100">Add Archer to Session</h3>
              <button onClick={() => setIsAddArcherOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleAddArcher} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Archer Name *</label>
                <input
                  type="text"
                  required
                  value={newArcherName}
                  onChange={e => setNewArcherName(e.target.value)}
                  placeholder="e.g. John Doe"
                  className="input-dark w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Assign to Lane (1-{activeSession.num_lanes}) *</label>
                <input
                  type="number"
                  required
                  min="1"
                  max={activeSession.num_lanes}
                  value={newArcherLane}
                  onChange={e => setNewArcherLane(parseInt(e.target.value) || 1)}
                  className="input-dark w-full"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2 border-t border-navy-700">
                <button
                  type="button"
                  onClick={() => setIsAddArcherOpen(false)}
                  className="btn-ghost py-1.5 px-3 text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary py-1.5 px-3 text-sm"
                >
                  Add Archer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Score details and override modal */}
      <ScoreDetailsModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedScore(null)
        }}
        score={selectedScore}
        onOverrideSuccess={async () => {
          // Refresh archers & lanes
          await loadData()
          if (selectedScore) {
            try {
              const updated = await scoresApi.get(selectedScore.id)
              setLastScores(prev => {
                const next = { ...prev }
                for (const laneId in next) {
                  if (next[laneId]?.id === updated.id) {
                    next[laneId] = updated
                  }
                }
                return next
              })
            } catch {}
          }
        }}
      />
    </div>
  )
}
