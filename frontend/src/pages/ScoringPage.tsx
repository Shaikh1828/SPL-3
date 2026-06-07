import { useState, useEffect, useRef } from 'react'
import { Camera as CameraIcon, Target, Activity, Square } from 'lucide-react'
import { camerasApi } from '@/api/cameras'
import { scoresApi } from '@/api/scores'
import { useSessionStore } from '@/store/sessionStore'
import { useCameraStore } from '@/store/cameraStore'
import { useCameraPreview } from '@/hooks/useCameraPreview'
import toast from 'react-hot-toast'
import { cn, getConfidenceColor } from '@/lib/utils'
import type { Camera, CameraLaneAssignment, Score } from '@/types'

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
  onCalculate, 
  isCalculating,
  lastScore
}: { 
  assignment: CameraLaneAssignment, 
  camera?: Camera,
  onCalculate: (cameraId: number, laneId: number) => void,
  isCalculating: boolean,
  lastScore?: Score | null
}) {
  return (
    <div className="glass-card p-4 flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="font-semibold text-slate-200">Lane {assignment.lane_number}</h3>
          <p className="text-xs text-slate-500">Camera: {camera?.name ?? 'Unknown'}</p>
        </div>
      </div>

      <CameraFeed 
        cameraId={assignment.camera_id} 
        label={`Lane ${assignment.lane_number}`} 
        status={camera?.status ?? 'disconnected'} 
      />

      <div className="flex items-center justify-between mt-2">
        <button
          onClick={() => onCalculate(assignment.camera_id, assignment.lane_number)}
          disabled={isCalculating || camera?.status !== 'connected'}
          className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {isCalculating ? (
            <><Activity className="w-4 h-4 animate-spin" /> Analyzing...</>
          ) : (
            <><CameraIcon className="w-4 h-4" /> Calculate Score</>
          )}
        </button>
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
            <span>Arrow {lastScore.arrow_number} / Round {lastScore.round_number}</span>
            <button className="text-gold-400 hover:text-gold-300">View Image</button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ScoringPage() {
  const { activeSession, currentEnd, setCurrentEnd } = useSessionStore()
  const { cameras, setCameras } = useCameraStore()
  const [assignments, setAssignments] = useState<CameraLaneAssignment[]>([])
  const [calculating, setCalculating] = useState<Record<number, boolean>>({})
  const [lastScores, setLastScores] = useState<Record<number, Score | null>>({})

  useEffect(() => {
    if (!activeSession) return
    const load = async () => {
      try {
        const cams = await camerasApi.listForSession(activeSession.id)
        setCameras(cams.items)
        // In a real implementation, we'd fetch actual assignments. 
        // For now, we mock them based on cameras.
        setAssignments(cams.items.map((c, i) => ({
          id: i, session_id: activeSession.id, camera_id: c.id, lane_number: i + 1, assigned_at: ''
        })))
      } catch {
        toast.error('Failed to load cameras')
      }
    }
    load()
  }, [activeSession, setCameras])

  const handleCalculate = async (_cameraId: number, laneId: number) => {
    if (!activeSession) return
    setCalculating(prev => ({ ...prev, [laneId]: true }))
    try {
      // Mock score creation for now since we don't have the full archer/arrow context here without a form
      const score = await scoresApi.record(activeSession.id, {
        session_archer_id: laneId, // Mock
        round_number: currentEnd,
        arrow_number: 1, // Mock
        zone: 9,
        points: 9,
        image_path: 'mock.jpg'
      })
      setLastScores(prev => ({ ...prev, [laneId]: score }))
      toast.success(`Score recorded: ${score.points}`)
    } catch (err) {
      toast.error('Scoring failed')
    } finally {
      setCalculating(prev => ({ ...prev, [laneId]: false }))
    }
  }

  const handleCalculateAll = async () => {
    assignments.forEach(a => handleCalculate(a.camera_id, a.lane_number))
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
          <button className="btn-ghost flex items-center gap-2 text-red-400 hover:text-red-300 hover:bg-red-500/10">
            <Square className="w-4 h-4" />
            End Session
          </button>
        </div>
      </div>

      {/* Camera Grid */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 pb-6">
          {assignments.map(assignment => (
            <ScoringLane
              key={assignment.lane_number}
              assignment={assignment}
              camera={cameras.find(c => c.id === assignment.camera_id)}
              onCalculate={handleCalculate}
              isCalculating={calculating[assignment.lane_number] || false}
              lastScore={lastScores[assignment.lane_number]}
            />
          ))}
          {assignments.length === 0 && (
             <div className="col-span-full py-12 text-center text-slate-500 border border-dashed border-navy-700 rounded-xl">
               No cameras assigned to lanes for this session.
             </div>
          )}
        </div>
      </div>
    </div>
  )
}
