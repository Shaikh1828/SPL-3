import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Camera as CameraIcon, Target, Activity, Square, Trophy,
  X, Upload, Sparkles, Layers, Eye,
  ShieldAlert, RefreshCw, UserPlus, Trash2, Play,
  Video, VideoOff, Tv, Radio
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { camerasApi } from '@/api/cameras'
import { scoresApi } from '@/api/scores'
import { sessionsApi } from '@/api/sessions'
import { tournamentsApi } from '@/api/tournaments'
import { useSessionStore } from '@/store/sessionStore'
import { useCameraStore } from '@/store/cameraStore'
import { useAuthStore } from '@/store/authStore'
import { useScoreStream } from '@/hooks/useScoreStream'
import { useCameraPreview } from '@/hooks/useCameraPreview'
import { ScoreDetailsModal } from '@/components/scores/ScoreDetailsModal'
import { RapidScorePad } from '@/components/scores/RapidScorePad'
import { ArcherScorecardMatrix } from '@/components/scores/ArcherScorecardMatrix'
import { ScorerReviewStage } from '@/components/scores/ScorerReviewStage'
import BatchScoringSection from '@/components/scoring/BatchScoringSection'
import { useCameraStream } from '@/context/CameraStreamContext'
import toast from 'react-hot-toast'
import { cn, getConfidenceColor } from '@/lib/utils'
import type {
  CameraLaneAssignment, Score, SessionArcher, Tournament, Session,
  AIScoreRoundResponse, LaneSubmission
} from '@/types'

function CameraFeed({
  cameraId,
  label,
  status,
  browserStream,
  isBridgeActiveForLane,
}: {
  cameraId: number
  label: string
  status: string
  browserStream: MediaStream | null
  isBridgeActiveForLane: boolean
}) {
  const imgRef = useRef<HTMLImageElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  useCameraPreview(cameraId, imgRef)

  useEffect(() => {
    if (isBridgeActiveForLane && browserStream && videoRef.current) {
      videoRef.current.srcObject = browserStream
    }
  }, [isBridgeActiveForLane, browserStream])

  const isLive = isBridgeActiveForLane || status === 'connected'

  return (
    <div className="relative aspect-video bg-navy-950 rounded-xl overflow-hidden border border-navy-700 shadow-inner">
      {isBridgeActiveForLane && browserStream ? (
        <>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-contain bg-black"
          />
          {/* Target centering overlay */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-30">
            <div className="w-48 h-48 border-2 border-dashed border-emerald-400 rounded-full" />
            <div className="w-1 h-1 bg-emerald-400 rounded-full absolute" />
          </div>
          <div className="absolute bottom-2 left-2 bg-emerald-950/90 text-emerald-300 border border-emerald-500/40 text-[9px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 shadow">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping" />
            DIRECT OBS STREAM
          </div>
        </>
      ) : status === 'connected' ? (
        <>
          <img ref={imgRef} className="w-full h-full object-contain" alt={label} />
          {/* Target centering overlay */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-30">
            <div className="w-48 h-48 border-2 border-dashed border-gold-500 rounded-full" />
            <div className="w-1 h-1 bg-gold-500 rounded-full absolute" />
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center h-full text-slate-500">
          <CameraIcon className="w-8 h-8 mb-2 opacity-40" />
          <p className="text-xs">Camera Feed Offline</p>
        </div>
      )}
      <div className="absolute top-2 left-2 flex items-center gap-2 bg-navy-950/80 backdrop-blur-sm px-2.5 py-1 rounded-lg text-xs border border-navy-700/60">
        <div className={cn("w-2 h-2 rounded-full", isLive ? 'bg-emerald-400 animate-pulse' : 'bg-red-500')} />
        <span className="text-slate-200 font-medium">{label}</span>
      </div>
    </div>
  )
}

export default function ScoringPage() {
  const navigate = useNavigate()
  const cameraStream = useCameraStream()
  const { activeSession, setActiveSession, activeTournament, setActiveTournament, currentEnd, setCurrentEnd } = useSessionStore()
  const { cameras, setCameras } = useCameraStore()
  const { user } = useAuthStore()
  const canScore = user?.role === 'admin' || user?.role === 'scorer'

  // Tournament & Session switcher state
  const [tournaments, setTournaments] = useState<Tournament[]>([])
  const [sessions, setSessions] = useState<Session[]>([])
  const [assignments, setAssignments] = useState<CameraLaneAssignment[]>([])
  const [archers, setArchers] = useState<SessionArcher[]>([])
  const [allScores, setAllScores] = useState<Score[]>([])
  const [activeLane, setActiveLane] = useState<number>(1)

  // Primary scoring path: 'camera' as default
  const [scoringTab, setScoringTab] = useState<'camera' | 'rapid' | 'matrix'>('camera')

  // Staged AI Round Scoring state
  const [stagedRoundData, setStagedRoundData] = useState<AIScoreRoundResponse | null>(null)
  const [isAIScoring, setIsAIScoring] = useState(false)

  // Loading & Submission states
  const [loading, setLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [calculating, setCalculating] = useState<Record<number, boolean>>({})
  const [lastScores, setLastScores] = useState<Record<number, Score | null>>({})

  // Modal states
  const [selectedScore, setSelectedScore] = useState<Score | null>(null)
  const [isScoreModalOpen, setIsScoreModalOpen] = useState(false)
  const [isAddArcherOpen, setIsAddArcherOpen] = useState(false)
  const [newArcherName, setNewArcherName] = useState('')
  const [newArcherLane, setNewArcherLane] = useState<number>(1)

  // Real-time score events
  const { lastEvent } = useScoreStream(activeSession?.id ?? null)

  // 1. Load Tournaments & Sessions
  const loadTournamentsAndSessions = useCallback(async () => {
    try {
      setLoading(true)
      const t = await tournamentsApi.list({ limit: 50 })
      const tList = Array.isArray(t) ? t : (t && Array.isArray((t as any).items) ? (t as any).items : [])
      setTournaments(tList)

      const selectedTourney = activeTournament || (tList.length > 0 ? tList[0] : null)
      if (selectedTourney) {
        setActiveTournament(selectedTourney)
        const s = await sessionsApi.listForTournament(selectedTourney.id)
        const sList = Array.isArray(s) ? s : (s && Array.isArray((s as any).items) ? (s as any).items : [])
        setSessions(sList)

        if (!activeSession && sList.length > 0) {
          const ongoing = sList.find((item: Session) => item.status === 'active') || sList[0]
          setActiveSession(ongoing)
        }
      }
    } catch (err) {
      console.error('Failed to load tournaments:', err)
    } finally {
      setLoading(false)
    }
  }, [activeTournament, activeSession, setActiveTournament, setActiveSession])

  // 2. Load Active Session Data (Cameras, Assignments, Archers, Scores)
  const loadSessionData = useCallback(async () => {
    if (!activeSession) return
    try {
      const [cams, assigns, archList, scoreList] = await Promise.all([
        camerasApi.listForSession(activeSession.id).catch(() => []),
        camerasApi.listAssignments(activeSession.id).catch(() => []),
        sessionsApi.listArchers(activeSession.id).catch(() => []),
        scoresApi.list(activeSession.id, { limit: 500 }).catch(() => []),
      ])

      setCameras(Array.isArray(cams) ? cams : [])
      setAssignments(Array.isArray(assigns) ? assigns : [])
      const archersArray = Array.isArray(archList) ? archList : []
      setArchers(archersArray)
      setAllScores(Array.isArray(scoreList) ? scoreList : [])

      // Set active lane to first assigned archer's lane
      if (archersArray.length > 0 && !archersArray.some(a => a.lane_number === activeLane)) {
        setActiveLane(archersArray[0].lane_number || 1)
      }
    } catch (err) {
      console.error('Failed to load session details:', err)
    }
  }, [activeSession, activeLane, setCameras])

  useEffect(() => {
    loadTournamentsAndSessions()
  }, [loadTournamentsAndSessions])

  useEffect(() => {
    loadSessionData()
  }, [loadSessionData])

  // Real-time update trigger
  useEffect(() => {
    if (lastEvent) {
      loadSessionData()
    }
  }, [lastEvent, loadSessionData])

  // Switch Tournament handler
  const handleTournamentChange = async (tournamentId: number) => {
    const tourney = tournaments.find(t => t.id === tournamentId)
    if (!tourney) return
    setActiveTournament(tourney)
    setStagedRoundData(null)

    try {
      const s = await sessionsApi.listForTournament(tourney.id)
      const sList = Array.isArray(s) ? s : (s && Array.isArray((s as any).items) ? (s as any).items : [])
      setSessions(sList)

      if (sList.length > 0) {
        const ongoing = sList.find((item: Session) => item.status === 'active') || sList[0]
        setActiveSession(ongoing)
      } else {
        setActiveSession(null)
      }
    } catch (err) {
      toast.error('Failed to load tournament sessions')
    }
  }

  // Switch Session handler
  const handleSessionChange = (sessionId: number) => {
    const s = sessions.find(item => item.id === sessionId)
    if (s) {
      setActiveSession(s)
      setCurrentEnd(1)
      setStagedRoundData(null)
    }
  }

  // Active Archer & Current End Scores
  const activeArcher = archers.find(a => a.lane_number === activeLane) || null
  const currentEndScores = allScores.filter(
    s => activeArcher && s.session_archer_id === activeArcher.id && s.round === currentEnd
  )

  // 🚀 PRIMARY ACTION: "Score Now" (AI Auto-Detect All Lanes for Selected Round)
  const handleAIScoreNow = async () => {
    if (!activeSession) return
    if (archers.length === 0) {
      toast.error('Please register archers in this session before scoring.')
      return
    }

    setIsAIScoring(true)
    const toastId = toast.loading(`AI Analyzing Targets for End ${currentEnd} across all lanes...`)

    try {
      // If live OBS/Camera stream is running, push freshest frame to ALL lanes
      if (cameraStream.isStreaming) {
        await cameraStream.pushCurrentFrame('all')
      }

      const res = await scoresApi.aiScoreRound(activeSession.id, {
        round: currentEnd,
        simulated: false,
      })

      setStagedRoundData(res)
      setScoringTab('camera') // Stay on primary Camera view
      toast.success(
        `AI Detection Complete: ${res.lanes.length} lanes scored for End ${currentEnd}! Review & confirm.`,
        { id: toastId }
      )
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'AI round scoring failed', { id: toastId })
    } finally {
      setIsAIScoring(false)
    }
  }

  // ✅ CONFIRM & SUBMIT ROUND BATCH
  const handleConfirmRoundSubmissions = async (submissions: LaneSubmission[]) => {
    if (!activeSession) return
    setIsSubmitting(true)
    const toastId = toast.loading(`Committing End ${currentEnd} scores to database...`)

    try {
      const res = await scoresApi.batchConfirmRound(activeSession.id, {
        round: currentEnd,
        lane_submissions: submissions,
      })

      toast.success(
        `End ${currentEnd} Confirmed! Recorded ${res.scores_recorded_count} arrows. Starting End ${res.next_round}!`,
        { id: toastId }
      )

      // Advance to next end and clear staged review
      setCurrentEnd(res.next_round)
      setStagedRoundData(null)
      await loadSessionData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to submit round scores', { id: toastId })
    } finally {
      setIsSubmitting(false)
    }
  }

  // 1. Rapid Score Pad Handler (Manual Override)
  const handleRapidScore = async (points: number, zone: number, isX: boolean = false) => {
    if (!activeSession || !activeArcher) return
    const arrowsPerRound = activeSession.arrows_per_round || 6
    if (currentEndScores.length >= arrowsPerRound) {
      toast.error(`End ${currentEnd} is full (${arrowsPerRound} arrows)! Please advance to Next End.`)
      return
    }

    const nextArrowNum = currentEndScores.length + 1
    setIsSubmitting(true)

    try {
      const score = await scoresApi.record(activeSession.id, {
        session_archer_id: activeArcher.id,
        round: currentEnd,
        arrow_num: nextArrowNum,
        zone: zone,
        points: points,
        image_id: isX ? 'x_hit.jpg' : undefined,
      })

      setLastScores(prev => ({ ...prev, [activeLane]: score }))
      toast.success(`Arrow ${nextArrowNum} Scored: ${isX ? 'X (10 pts)' : points === 0 ? 'Miss' : `${points} pts`}`)
      await loadSessionData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to record arrow score')
    } finally {
      setIsSubmitting(false)
    }
  }

  // 2. Undo Last Arrow Score
  const handleUndoLastScore = async () => {
    if (!activeSession || !activeArcher || currentEndScores.length === 0) return
    const lastScore = currentEndScores[currentEndScores.length - 1]

    setIsSubmitting(true)
    try {
      await scoresApi.delete(lastScore.id)
      toast.success(`Arrow #${lastScore.arrow_num} removed`)
      await loadSessionData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to undo score')
    } finally {
      setIsSubmitting(false)
    }
  }

  // 3. Single-Lane AI Camera Detection Scoring
  const handleCalculateCamera = async (_cameraId: number, laneId: number) => {
    if (!activeSession) return
    const laneArcher = archers.find(a => a.lane_number === laneId)
    if (!laneArcher) {
      toast.error(`Please assign an archer to Lane ${laneId} first!`)
      return
    }

    setCalculating(prev => ({ ...prev, [laneId]: true }))
    const toastId = toast.loading(`Capturing Lane ${laneId} camera & detecting arrow...`)
    try {
      if (cameraStream.isStreaming) {
        await cameraStream.pushCurrentFrame(laneId)
      }
      const score = await scoresApi.captureLaneScore(activeSession.id, laneId, currentEnd)
      setLastScores(prev => ({ ...prev, [laneId]: score }))
      toast.success(
        `AI Arrow Scored for ${laneArcher.archer_name}: ${score.points} pts (Conf: ${Math.round((score.confidence ?? 0.95) * 100)}%)`,
        { id: toastId }
      )
      await loadSessionData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Camera vision capture failed', { id: toastId })
    } finally {
      setCalculating(prev => ({ ...prev, [laneId]: false }))
    }
  }

  // 4. Upload Shot Image
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
      toast.success(`AI Detection: ${score.points} pts (Conf: ${Math.round((score.confidence ?? 0.95) * 100)}%)`)
      await loadSessionData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Image scoring failed')
    } finally {
      setCalculating(prev => ({ ...prev, [laneId]: false }))
    }
  }

  // 5. Add Archer to Session
  const handleAddArcher = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeSession || !newArcherName) return

    try {
      await sessionsApi.registerArcher(activeSession.id, {
        archer_name: newArcherName,
        lane_number: newArcherLane,
      })
      toast.success(`Archer ${newArcherName} added to Lane ${newArcherLane}`)
      setNewArcherName('')
      setIsAddArcherOpen(false)
      await loadSessionData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to register archer')
    }
  }

  // 6. Remove Archer
  const handleRemoveArcher = async (sessionArcherId: number) => {
    if (!activeSession || !window.confirm('Remove this archer from the session?')) return
    try {
      await sessionsApi.removeArcher(activeSession.id, sessionArcherId)
      toast.success('Archer removed')
      await loadSessionData()
    } catch {
      toast.error('Failed to remove archer')
    }
  }

  // 7. Complete Session
  const handleEndSession = async () => {
    if (!activeSession || !window.confirm('Mark this session as completed?')) return
    try {
      await sessionsApi.updateStatus(activeSession.id, 'completed')
      toast.success('Session marked as completed!')
      await loadTournamentsAndSessions()
    } catch {
      toast.error('Failed to update session status')
    }
  }

  return (
    <div className="p-6 space-y-6 animate-in">
      {/* Role Alert for Spectators */}
      {!canScore && (
        <div className="p-3.5 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-300 text-xs flex items-center gap-2.5">
          <ShieldAlert className="w-4 h-4 shrink-0 text-amber-400" />
          <span>Spectator View Mode: Live scoring overview (Arrow score recording and camera calculations are restricted to Admin & Scorer).</span>
        </div>
      )}

      {/* 🏆 TOURNAMENT & SESSION SWITCHER BANNER */}
      <div className="glass-card p-5 border-gold-500/30 bg-gradient-to-r from-navy-900 via-navy-800 to-navy-900 shadow-xl space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2.5 py-1 rounded-full text-xs font-black bg-gold-500 text-navy-950 flex items-center gap-1.5 shadow-md">
                <Sparkles className="w-3.5 h-3.5" />
                AI Camera Target Vision
              </span>
              {activeSession && (
                <span className={cn(
                  'px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border',
                  activeSession.status === 'active'
                    ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                    : 'bg-navy-800 text-slate-400 border-navy-700'
                )}>
                  {activeSession.status}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-black text-slate-100 tracking-tight">
              Match Scoring & Target Vision
            </h1>
            <p className="text-xs text-slate-400">
              Primary camera vision pipeline: Click <strong>Score Now</strong> to auto-score all lanes with YOLO11, review and confirm to advance rounds.
            </p>
          </div>

          {/* Tournament, Session, and Primary "Score Now" Trigger */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Tournament Dropdown */}
            <div className="flex items-center gap-2 bg-navy-950/80 px-3 py-1.5 rounded-lg border border-navy-700">
              <Trophy className="w-3.5 h-3.5 text-gold-400" />
              <span className="text-xs text-slate-400 font-medium">Tournament:</span>
              <select
                value={activeTournament?.id ?? ''}
                onChange={(e) => handleTournamentChange(Number(e.target.value))}
                className="bg-transparent text-xs font-bold text-gold-400 focus:outline-none cursor-pointer"
              >
                {tournaments.map(t => (
                  <option key={t.id} value={t.id} className="bg-navy-900 text-slate-200">
                    {t.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Session Dropdown */}
            {sessions.length > 0 && (
              <div className="flex items-center gap-2 bg-navy-950/80 px-3 py-1.5 rounded-lg border border-navy-700">
                <Target className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-xs text-slate-400 font-medium">Session:</span>
                <select
                  value={activeSession?.id ?? ''}
                  onChange={(e) => handleSessionChange(Number(e.target.value))}
                  className="bg-transparent text-xs font-bold text-emerald-400 focus:outline-none cursor-pointer"
                >
                  {sessions.map(s => (
                    <option key={s.id} value={s.id} className="bg-navy-900 text-slate-200">
                      {s.name} ({s.status})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* End / Round Control */}
            {activeSession && (
              <div className="flex items-center gap-1.5 bg-navy-950/80 p-1 rounded-lg border border-navy-700">
                <button
                  onClick={() => {
                    setCurrentEnd(Math.max(1, currentEnd - 1))
                    setStagedRoundData(null)
                  }}
                  disabled={currentEnd <= 1}
                  className="btn-ghost px-2 py-1 text-xs"
                >
                  ◀
                </button>
                <span className="text-xs font-black font-mono text-gold-400 px-2 flex items-center gap-1">
                  <span>End #{currentEnd}</span>
                  <span className="text-[10px] text-slate-400 font-normal">({activeSession.arrows_per_round || 6} arr/end)</span>
                </span>
                <button
                  onClick={() => {
                    setCurrentEnd(currentEnd + 1)
                    setStagedRoundData(null)
                  }}
                  className="btn-ghost px-2 py-1 text-xs"
                >
                  ▶
                </button>
              </div>
            )}

            {/* ⚡ PRIMARY "SCORE NOW" ACTION BUTTON */}
            {canScore && activeSession && (
              <button
                onClick={handleAIScoreNow}
                disabled={isAIScoring || archers.length === 0}
                className="btn-primary py-2 px-4 text-xs font-black flex items-center gap-2 shadow-lg shadow-gold-500/25 animate-pulse hover:animate-none"
              >
                {isAIScoring ? (
                  <>
                    <Activity className="w-4 h-4 animate-spin" />
                    <span>AI Scanning Targets...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-navy-950 text-navy-950" />
                    <span>⚡ Score Now (All Lanes)</span>
                  </>
                )}
              </button>
            )}

            <button
              onClick={() => {
                loadTournamentsAndSessions()
                loadSessionData()
              }}
              disabled={loading}
              className="btn-ghost text-xs p-2"
              title="Refresh data"
            >
              <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
            </button>
          </div>
        </div>

        {/* 🎯 LANE SELECTOR RIBBON */}
        {archers.length > 0 && (
          <div className="pt-3 border-t border-navy-700/60 flex items-center gap-2 overflow-x-auto pb-1">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex-shrink-0 mr-1">
              Active Lanes:
            </span>
            {archers.map((archer) => {
              const isSelected = archer.lane_number === activeLane
              const laneScores = allScores.filter(s => s.session_archer_id === archer.id && s.round === currentEnd)
              return (
                <button
                  key={archer.id}
                  onClick={() => archer.lane_number && setActiveLane(archer.lane_number)}
                  className={cn(
                    'px-3 py-2 rounded-xl border text-xs flex items-center gap-2.5 transition-all flex-shrink-0',
                    isSelected
                      ? 'bg-gradient-to-r from-gold-500/20 to-gold-500/10 border-gold-500 text-gold-300 shadow-md shadow-gold-500/10'
                      : 'bg-navy-950/60 border-navy-700/80 text-slate-300 hover:border-gold-500/40 hover:bg-navy-800/60'
                  )}
                >
                  <span className={cn(
                    'w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black',
                    isSelected ? 'bg-gold-500 text-navy-950' : 'bg-navy-800 text-slate-400'
                  )}>
                    {archer.lane_number}
                  </span>
                  <div className="text-left">
                    <p className="font-bold leading-none truncate max-w-[120px]">{archer.archer_name}</p>
                    <span className="text-[10px] text-slate-400 mt-0.5 block font-mono">
                      {archer.total_score} pts · End {currentEnd}: {laneScores.length}/{activeSession?.arrows_per_round || 6}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* No Active Session Fallback */}
      {!activeSession ? (
        <div className="glass-card p-12 text-center text-slate-500 space-y-3">
          <Target className="w-12 h-12 mx-auto opacity-30 text-gold-400" />
          <h2 className="text-lg font-bold text-slate-200">No Active Session Available</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Please select an existing tournament above or navigate to Tournaments to create a new match session.
          </p>
          <button
            onClick={() => navigate('/tournaments')}
            className="btn-primary text-xs py-2 px-4 inline-flex items-center gap-1.5 shadow-lg"
          >
            <Trophy className="w-4 h-4" />
            Go to Tournaments
          </button>
        </div>
      ) : (
        <>
          {/* SCORING MODE TABS */}
          <div className="flex items-center justify-between border-b border-navy-700 pb-2">
            <div className="inline-flex rounded-xl bg-navy-900/80 p-1 border border-navy-700">
              {/* PRIMARY TAB: AI Camera Target Vision */}
              <button
                onClick={() => setScoringTab('camera')}
                className={cn(
                  'px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-2',
                  scoringTab === 'camera'
                    ? 'bg-gold-500 text-navy-950 shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                )}
              >
                <CameraIcon className="w-3.5 h-3.5" />
                🤖 AI Target Cameras (Primary)
              </button>
              <button
                onClick={() => setScoringTab('matrix')}
                className={cn(
                  'px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-2',
                  scoringTab === 'matrix'
                    ? 'bg-gold-500 text-navy-950 shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                )}
              >
                <Layers className="w-3.5 h-3.5" />
                📋 Multi-Lane Scorecard Matrix
              </button>
              {/* OVERRIDE / MANUAL SCOREPAD TAB */}
              <button
                onClick={() => setScoringTab('rapid')}
                className={cn(
                  'px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-2',
                  scoringTab === 'rapid'
                    ? 'bg-purple-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                )}
              >
                <Sparkles className="w-3.5 h-3.5" />
                ⚡ Manual Override Scorepad
              </button>
            </div>

            {canScore && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsAddArcherOpen(true)}
                  className="btn-ghost text-xs py-1.5 px-3 flex items-center gap-1.5 border border-navy-700 hover:border-gold-500"
                >
                  <UserPlus className="w-3.5 h-3.5 text-gold-400" />
                  Add Archer
                </button>
                <button
                  onClick={handleEndSession}
                  className="btn-ghost text-xs py-1.5 px-3 flex items-center gap-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/10 border border-red-500/30"
                >
                  <Square className="w-3.5 h-3.5" />
                  End Session
                </button>
              </div>
            )}
          </div>

          {/* TAB 1: AI TARGET CAMERAS & STAGED REVIEW (PRIMARY) */}
          {scoringTab === 'camera' && (
            <>
              {stagedRoundData ? (
                /* Staged AI Review Matrix for End {currentEnd} */
                <ScorerReviewStage
                  stagedData={stagedRoundData}
                  archers={archers}
                  isSubmitting={isSubmitting}
                  canScore={canScore}
                  onConfirmRound={handleConfirmRoundSubmissions}
                  onRescan={handleAIScoreNow}
                  onDiscard={() => setStagedRoundData(null)}
                />
              ) : (
                /* Live Camera Lane Grid */
                <div className="space-y-6">
                  {/* Live OBS / Hardware Camera Stream Control Bar */}
                  <div className="glass-card p-4 rounded-xl bg-gradient-to-r from-navy-900 via-navy-850 to-navy-900 border border-gold-500/30 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-lg">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-10 h-10 rounded-xl flex items-center justify-center transition-all",
                        cameraStream.isStreaming
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-inner"
                          : "bg-navy-800 text-slate-400 border border-navy-700"
                      )}>
                        {cameraStream.isStreaming ? (
                          <Radio className="w-5 h-5 animate-pulse text-emerald-400" />
                        ) : (
                          <Tv className="w-5 h-5" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-bold text-slate-100">OBS & Camera Stream Bridge</h4>
                          {cameraStream.isStreaming ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                              LIVE STREAMING
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-navy-800 text-slate-400 border border-navy-700">
                              STREAM STANDBY
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          {cameraStream.isStreaming
                            ? `Active: ${cameraStream.devices.find(d => d.deviceId === cameraStream.selectedDeviceId)?.label || 'Video Device'} → ${cameraStream.activeLane === 'all' ? 'All Lanes' : `Lane ${cameraStream.activeLane}`}`
                            : 'Connect your OBS Virtual Camera or Webcam to feed live video into the AI vision pipeline.'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5 w-full md:w-auto flex-wrap">
                      {/* Device Selector */}
                      <select
                        value={cameraStream.selectedDeviceId}
                        onChange={(e) => cameraStream.setSelectedDeviceId(e.target.value)}
                        className="bg-navy-950 border border-navy-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-gold-500"
                      >
                        {cameraStream.devices.length === 0 && (
                          <option value="">No Camera Detected</option>
                        )}
                        {cameraStream.devices.map((d) => (
                          <option key={d.deviceId} value={d.deviceId}>
                            {d.isObs ? `🎥 ${d.label}` : `📷 ${d.label}`}
                          </option>
                        ))}
                      </select>

                      {/* Lane Target */}
                      <select
                        value={String(cameraStream.activeLane)}
                        onChange={(e) => cameraStream.setActiveLane(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                        className="bg-navy-950 border border-navy-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-gold-500"
                      >
                        <option value="all">🌐 Broadcast to All Lanes</option>
                        {assignments.map((a) => (
                          <option key={a.lane} value={a.lane}>
                            🎯 Bind to Lane {a.lane}
                          </option>
                        ))}
                      </select>

                      {/* Toggle Stream Button */}
                      {cameraStream.isStreaming ? (
                        <button
                          type="button"
                          onClick={() => cameraStream.stopStream()}
                          className="btn-ghost text-xs py-1.5 px-3 border border-red-500/40 text-red-400 hover:bg-red-500/10 flex items-center gap-1.5"
                        >
                          <VideoOff className="w-3.5 h-3.5" />
                          Stop Stream
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => cameraStream.startStream(cameraStream.selectedDeviceId, cameraStream.activeLane)}
                          className="btn-primary text-xs py-1.5 px-3.5 font-bold flex items-center gap-1.5 shadow-md"
                        >
                          <Video className="w-3.5 h-3.5" />
                          Connect Live Stream
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Call to action prompt */}
                  <div className="p-4 rounded-xl bg-gold-500/10 border border-gold-500/30 flex flex-col sm:flex-row items-center justify-between gap-3 text-gold-300 text-xs">
                    <div className="flex items-center gap-2.5">
                      <Sparkles className="w-4 h-4 text-gold-400 shrink-0" />
                      <span>Ready to score <strong>End {currentEnd}</strong>. Target feeds active across {archers.length} lanes.</span>
                    </div>
                    {canScore && (
                      <button
                        onClick={handleAIScoreNow}
                        disabled={isAIScoring || archers.length === 0}
                        className="btn-primary py-1.5 px-4 text-xs font-bold shrink-0 shadow-md"
                      >
                        ⚡ Score Now (AI Auto-Detect)
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                    {assignments.map(assignment => {
                      const laneArcher = archers.find(a => a.lane_number === assignment.lane)
                      const camera = cameras.find(c => c.id === assignment.camera_id)
                      const lastScore = lastScores[assignment.lane]

                      return (
                        <div key={assignment.lane} className="glass-card p-5 flex flex-col gap-4 border-navy-700 shadow-xl">
                          <div className="flex justify-between items-center">
                            <div>
                              <h3 className="font-bold text-slate-100 flex items-center gap-2">
                                <Target className="w-4 h-4 text-gold-400" />
                                Lane {assignment.lane}
                              </h3>
                              <p className="text-xs text-slate-400 mt-0.5">
                                Archer: <strong className="text-gold-400">{laneArcher?.archer_name ?? 'Unassigned'}</strong>
                              </p>
                            </div>
                            <span className="text-[10px] text-slate-400 bg-navy-900 px-2 py-1 rounded border border-navy-700">
                              {camera?.name ?? 'Camera'}
                            </span>
                          </div>

                          <CameraFeed
                            cameraId={assignment.camera_id}
                            label={`Lane ${assignment.lane}`}
                            status={camera?.status ?? 'connected'}
                            browserStream={cameraStream.activeStream}
                            isBridgeActiveForLane={cameraStream.isLaneActive(assignment.lane)}
                          />

                          {canScore && (
                            <div className="flex flex-col gap-2">
                              <button
                                onClick={() => handleCalculateCamera(assignment.camera_id, assignment.lane)}
                                disabled={calculating[assignment.lane] || !laneArcher}
                                className="btn-primary w-full flex items-center justify-center gap-2 py-2.5 text-xs font-bold"
                              >
                                {calculating[assignment.lane] ? (
                                  <><Activity className="w-4 h-4 animate-spin" /> AI Analyzing Target...</>
                                ) : (
                                  <><CameraIcon className="w-4 h-4" /> Single Lane AI Scan</>
                                )}
                              </button>

                              <label className={cn(
                                "btn-ghost w-full flex items-center justify-center gap-2 cursor-pointer border border-dashed border-navy-600 hover:border-gold-500 hover:text-gold-400 py-2 rounded-lg text-xs transition-colors",
                                (calculating[assignment.lane] || !laneArcher) && "opacity-50 pointer-events-none"
                              )}>
                                <Upload className="w-3.5 h-3.5" />
                                <span>Upload Shot Image</span>
                                <input
                                  type="file"
                                  accept="image/*"
                                  className="hidden"
                                  onChange={(e) => {
                                    const file = e.target.files?.[0]
                                    if (file) handleUploadImage(assignment.lane, file)
                                    e.target.value = ''
                                  }}
                                  disabled={calculating[assignment.lane] || !laneArcher}
                                />
                              </label>
                            </div>
                          )}

                          {lastScore && (
                            <div className="p-3 bg-navy-900/80 rounded-xl border border-navy-700/80">
                              <div className="flex justify-between items-center mb-1">
                                <span className="text-xs font-semibold text-slate-300">Last Detection Result</span>
                                <span className={cn("font-black font-mono text-sm", getConfidenceColor(lastScore.confidence ?? 1))}>
                                  {lastScore.points} pts
                                </span>
                              </div>
                              <div className="flex items-center justify-between text-[11px] text-slate-400">
                                <span>Arrow {lastScore.arrow_num} / End {lastScore.round}</span>
                                <button
                                  onClick={() => {
                                    setSelectedScore(lastScore)
                                    setIsScoreModalOpen(true)
                                  }}
                                  className="text-gold-400 hover:text-gold-300 font-semibold flex items-center gap-1"
                                >
                                  <Eye className="w-3 h-3" /> View Annotated
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}

                    {assignments.length === 0 && (
                      <div className="col-span-full py-16 text-center text-slate-500 border border-dashed border-navy-700 rounded-xl">
                        <CameraIcon className="w-10 h-10 mx-auto mb-2 opacity-30" />
                        <p className="text-sm">No cameras assigned to lanes for this session.</p>
                        <button
                          onClick={() => navigate('/cameras')}
                          className="mt-3 btn-primary text-xs py-1.5 px-3 inline-flex items-center gap-1.5"
                        >
                          Go to Camera Setup
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}

          {/* TAB 2: MANUAL OVERRIDE SCOREPAD */}
          {scoringTab === 'rapid' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column (2 Cols): Rapid Scorepad */}
              <div className="lg:col-span-2 space-y-6">
                <RapidScorePad
                  archer={activeArcher}
                  currentEnd={currentEnd}
                  arrowsPerRound={activeSession.arrows_per_round || 6}
                  endScores={currentEndScores}
                  isSubmitting={isSubmitting}
                  onRecordScore={handleRapidScore}
                  onUndoLastScore={handleUndoLastScore}
                  onNextEnd={() => setCurrentEnd(currentEnd + 1)}
                  onPrevEnd={() => setCurrentEnd(Math.max(1, currentEnd - 1))}
                  canScore={canScore}
                />

                {/* Scorecard Table for Active Archer */}
                {activeArcher && (
                  <div className="glass-card p-5 space-y-3">
                    <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                      <Target className="w-4 h-4 text-gold-400" />
                      Complete Match Scorecard — {activeArcher.archer_name} (Lane {activeArcher.lane_number})
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead>
                          <tr className="border-b border-navy-700 bg-navy-900/60 text-slate-400">
                            <th className="py-2.5 px-3">End #</th>
                            <th className="py-2.5 px-3">Arrow Scores</th>
                            <th className="py-2.5 px-3 text-center">End Total</th>
                            <th className="py-2.5 px-3 text-right">Running Total</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-navy-750">
                          {Array.from({ length: Math.max(currentEnd, 2) }).map((_, endIdx) => {
                            const endNum = endIdx + 1
                            const endSc = allScores.filter(s => s.session_archer_id === activeArcher.id && s.round === endNum)
                            const endSum = endSc.reduce((acc, curr) => acc + curr.points, 0)
                            const runningSum = allScores
                              .filter(s => s.session_archer_id === activeArcher.id && s.round <= endNum)
                              .reduce((acc, curr) => acc + curr.points, 0)

                            return (
                              <tr key={endIdx} className={cn(endNum === currentEnd && 'bg-gold-500/5 font-semibold')}>
                                <td className="py-2.5 px-3 text-gold-400 font-bold">End {endNum}</td>
                                <td className="py-2.5 px-3">
                                  <div className="flex gap-1.5 flex-wrap">
                                    {endSc.map((s) => (
                                      <span
                                        key={s.id}
                                        onClick={() => {
                                          setSelectedScore(s)
                                          setIsScoreModalOpen(true)
                                        }}
                                        className={cn(
                                          'px-2 py-0.5 rounded text-xs font-mono font-black cursor-pointer border',
                                          s.points === 10 ? 'bg-gold-500/20 text-gold-400 border-gold-500/40' :
                                          s.points >= 8 ? 'bg-red-500/20 text-red-400 border-red-500/40' :
                                          'bg-navy-800 text-slate-300 border-navy-700'
                                        )}
                                        title="Click to view/override score"
                                      >
                                        {s.points === 10 && s.zone === 10 ? 'X' : s.points}
                                      </span>
                                    ))}
                                    {endSc.length === 0 && <span className="text-slate-500">—</span>}
                                  </div>
                                </td>
                                <td className="py-2.5 px-3 text-center font-mono font-bold text-slate-200">
                                  {endSc.length > 0 ? `${endSum} pts` : '—'}
                                </td>
                                <td className="py-2.5 px-3 text-right font-mono font-black text-emerald-400">
                                  {endSc.length > 0 ? `${runningSum} pts` : '—'}
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>

              {/* Right Column (1 Col): Archers List & Lane Summary */}
              <div className="space-y-6">
                <div className="glass-card p-5 space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-navy-700">
                    <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                      <Trophy className="w-4 h-4 text-gold-400" />
                      Session Competitors ({archers.length})
                    </h3>
                  </div>

                  <div className="space-y-2">
                    {archers.map(a => {
                      const isSelected = a.lane_number === activeLane
                      return (
                        <div
                          key={a.id}
                          onClick={() => a.lane_number && setActiveLane(a.lane_number)}
                          className={cn(
                            'flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer',
                            isSelected
                              ? 'bg-gold-500/15 border-gold-500/40 shadow-sm'
                              : 'bg-navy-900/60 border-navy-750 hover:bg-navy-800/60'
                          )}
                        >
                          <div className="flex items-center gap-3">
                            <span className={cn(
                              'w-7 h-7 rounded-full flex items-center justify-center text-xs font-black',
                              isSelected ? 'bg-gold-500 text-navy-950' : 'bg-navy-800 text-slate-400'
                            )}>
                              {a.lane_number}
                            </span>
                            <div>
                              <p className="text-xs font-bold text-slate-100">{a.archer_name}</p>
                              <p className="text-[10px] text-slate-400">Lane {a.lane_number} · Round {a.current_round}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="text-right">
                              <span className="text-sm font-black font-mono text-gold-400">{a.total_score}</span>
                              <span className="text-[10px] text-slate-400 block -mt-0.5">pts</span>
                            </div>
                            {canScore && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleRemoveArcher(a.id)
                                }}
                                className="p-1 rounded text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                                title="Remove archer from session"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: MULTI-LANE SCORECARD MATRIX */}
          {scoringTab === 'matrix' && (
            <ArcherScorecardMatrix
              archers={archers}
              allScores={allScores}
              arrowsPerRound={activeSession.arrows_per_round || 6}
              activeLane={activeLane}
              onSelectLane={(lane) => {
                setActiveLane(lane)
                setScoringTab('camera')
              }}
            />
          )}

          {/* Integrated Batch Scoring Section */}
          <div id="batch-scoring-section" className="pt-4">
            <BatchScoringSection onScoreUpdated={loadSessionData} />
          </div>
        </>
      )}

      {/* Add Archer Modal */}
      {isAddArcherOpen && (
        <div className="fixed inset-0 bg-navy-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 space-y-4 animate-in shadow-2xl border border-navy-700">
            <div className="flex justify-between items-center pb-2 border-b border-navy-700">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-gold-400" />
                Add Competitor to Session
              </h3>
              <button onClick={() => setIsAddArcherOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleAddArcher} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Archer Full Name *</label>
                <input
                  type="text"
                  required
                  value={newArcherName}
                  onChange={e => setNewArcherName(e.target.value)}
                  placeholder="e.g. Brady Ellison"
                  className="input-dark w-full text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Assign Shooting Lane (1-{activeSession?.num_lanes || 6}) *</label>
                <input
                  type="number"
                  required
                  min="1"
                  max={activeSession?.num_lanes || 6}
                  value={newArcherLane}
                  onChange={e => setNewArcherLane(parseInt(e.target.value) || 1)}
                  className="input-dark w-full text-xs"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-navy-700">
                <button
                  type="button"
                  onClick={() => setIsAddArcherOpen(false)}
                  className="btn-ghost py-1.5 px-3 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary py-1.5 px-4 text-xs font-bold"
                >
                  Add Competitor
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Score Details & Override Modal */}
      <ScoreDetailsModal
        isOpen={isScoreModalOpen}
        onClose={() => {
          setIsScoreModalOpen(false)
          setSelectedScore(null)
        }}
        score={selectedScore}
        onOverrideSuccess={async () => {
          await loadSessionData()
        }}
      />
    </div>
  )
}
