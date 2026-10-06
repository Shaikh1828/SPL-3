import React, { useState, useEffect, useRef } from 'react'
import {
  Play, Pause, RotateCcw, Upload, Sparkles, CheckCircle2,
  Crosshair, Sliders, Eye, EyeOff, FastForward,
  Rewind, ShieldAlert, Award, Film
} from 'lucide-react'
import { poseApi } from '@/api/pose'
import type { SampleVideoItem, PoseAnalysisResponse, PoseFrameData } from '@/types'
import { toast } from 'react-hot-toast'

// MediaPipe 33 Landmark Connections for Anatomical Pose
const POSE_CONNECTIONS: [number, number][] = [
  // Torso
  [11, 12], [11, 23], [12, 24], [23, 24],
  // Left Arm (Draw Side)
  [11, 13], [13, 15],
  // Right Arm (Bow Side)
  [12, 14], [14, 16],
  // Left Leg
  [23, 25], [25, 27],
  // Right Leg
  [24, 26], [26, 28],
  // Head/Spine
  [0, 11], [0, 12]
]

export default function PoseAnalysisPage() {
  // State
  const [sampleVideos, setSampleVideos] = useState<SampleVideoItem[]>([])
  const [selectedVideoId, setSelectedVideoId] = useState<string>('gold_form_10')
  const [analysisData, setAnalysisData] = useState<PoseAnalysisResponse | null>(null)
  const [analyzing, setAnalyzing] = useState<boolean>(false)
  const [activeTab, setActiveTab] = useState<'video' | 'simulator'>('video')

  // Playback State
  const [isPlaying, setIsPlaying] = useState<boolean>(false)
  const [currentTime, setCurrentTime] = useState<number>(0)
  const [duration, setDuration] = useState<number>(6.0)
  const [playbackRate, setPlaybackRate] = useState<number>(1.0)
  const [showSkeleton, setShowSkeleton] = useState<boolean>(true)
  const [showAngles, setShowAngles] = useState<boolean>(true)
  const [showHUD, setShowHUD] = useState<boolean>(true)

  // Simulator Sliders State
  const [simBowArm, setSimBowArm] = useState<number>(179.2)
  const [simDrawElbow, setSimDrawElbow] = useState<number>(139.0)
  const [simJitter, setSimJitter] = useState<number>(0.6)
  const [simDeflection, setSimDeflection] = useState<number>(0.4)
  const [simHoldDuration, setSimHoldDuration] = useState<number>(2.0)
  const [simPrediction, setSimPrediction] = useState<any>(null)

  // DOM Refs
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const animationFrameRef = useRef<number | null>(null)

  // Load sample videos on mount
  useEffect(() => {
    loadSampleVideos()
  }, [])

  const loadSampleVideos = async () => {
    try {
      const res = await poseApi.getSampleVideos()
      setSampleVideos(res.videos || [])
      if (res.videos && res.videos.length > 0) {
        // Automatically load first sample video
        loadAndAnalyzeSample('gold_form_10')
      }
    } catch (err) {
      toast.error('Failed to load benchmark videos')
    }
  }

  const loadAndAnalyzeSample = async (videoId: string) => {
    try {
      setSelectedVideoId(videoId)
      setAnalyzing(true)
      const data = await poseApi.analyzeSampleVideo(videoId)
      setAnalysisData(data)
      setDuration(data.duration_sec || 6.0)
      if (videoRef.current) {
        videoRef.current.currentTime = 0
        videoRef.current.src = poseApi.getStreamUrl(videoId)
        videoRef.current.load()
      }
      setIsPlaying(false)
      toast.success(`Loaded "${data.title}"`)
    } catch (err: any) {
      toast.error(`Analysis failed: ${err.message || 'Unknown error'}`)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    try {
      setAnalyzing(true)
      toast.loading('Analyzing archer kinematics and extracting pose...', { id: 'upload' })
      const data = await poseApi.analyzeUploadedVideo(formData)
      setAnalysisData(data)
      setSelectedVideoId('custom')
      setDuration(data.duration_sec || 6.0)
      
      // Create local object URL for instant preview
      const localUrl = URL.createObjectURL(file)
      if (videoRef.current) {
        videoRef.current.src = localUrl
        videoRef.current.currentTime = 0
        videoRef.current.load()
      }
      setIsPlaying(false)
      toast.success('Video analysis completed!', { id: 'upload' })
    } catch (err: any) {
      toast.error(`Upload analysis failed: ${err.response?.data?.detail || err.message}`, { id: 'upload' })
    } finally {
      setAnalyzing(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  // Handle Play/Pause
  const togglePlay = () => {
    if (!videoRef.current) return
    if (isPlaying) {
      videoRef.current.pause()
      setIsPlaying(false)
    } else {
      videoRef.current.play()
      setIsPlaying(true)
    }
  }

  const handleSeek = (time: number) => {
    if (!videoRef.current) return
    videoRef.current.currentTime = time
    setCurrentTime(time)
  }

  const stepFrame = (forward: boolean) => {
    if (!videoRef.current) return
    const step = 1 / (analysisData?.fps || 30)
    const newTime = Math.max(0, Math.min(duration, videoRef.current.currentTime + (forward ? step : -step)))
    videoRef.current.currentTime = newTime
    setCurrentTime(newTime)
  }

  const changeSpeed = (rate: number) => {
    setPlaybackRate(rate)
    if (videoRef.current) {
      videoRef.current.playbackRate = rate
    }
  }

  // Canvas Skeleton Rendering Loop synchronized with Video
  useEffect(() => {
    const renderOverlay = () => {
      const video = videoRef.current
      const canvas = canvasRef.current
      if (!video || !canvas || !analysisData) return

      const ctx = canvas.getContext('2d')
      if (!ctx) return

      // Sync canvas dimensions
      if (canvas.width !== video.clientWidth || canvas.height !== video.clientHeight) {
        canvas.width = video.clientWidth
        canvas.height = video.clientHeight
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Find frame landmarks matching current video timestamp
      const cTime = video.currentTime
      setCurrentTime(cTime)

      const frames = analysisData.frames_landmarks || []
      if (frames.length > 0 && showSkeleton) {
        // Find closest frame by time
        const closestFrame = frames.reduce((prev, curr) =>
          Math.abs(curr.time - cTime) < Math.abs(prev.time - cTime) ? curr : prev
        )

        if (closestFrame && closestFrame.landmarks) {
          drawSkeleton(ctx, closestFrame, canvas.width, canvas.height)
        }
      }

      animationFrameRef.current = requestAnimationFrame(renderOverlay)
    }

    animationFrameRef.current = requestAnimationFrame(renderOverlay)
    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current)
    }
  }, [analysisData, showSkeleton, showAngles, showHUD])

  const drawSkeleton = (
    ctx: CanvasRenderingContext2D,
    frameData: PoseFrameData,
    width: number,
    height: number
  ) => {
    const lms = frameData.landmarks
    const lmap = new Map(lms.map((l) => [l.id, l]))

    // Draw Bones (Lines)
    POSE_CONNECTIONS.forEach(([i1, i2]) => {
      const p1 = lmap.get(i1)
      const p2 = lmap.get(i2)
      if (p1 && p2 && p1.visibility > 0.5 && p2.visibility > 0.5) {
        const x1 = p1.x * width
        const y1 = p1.y * height
        const x2 = p2.x * width
        const y2 = p2.y * height

        // Color based on body segment
        let strokeColor = '#3b82f6' // Default cyan
        if (i1 === 12 && i2 === 14) strokeColor = '#10b981' // Bow upper arm (green)
        if (i1 === 14 && i2 === 16) strokeColor = '#10b981' // Bow forearm
        if (i1 === 11 && i2 === 13) strokeColor = '#f59e0b' // Draw arm (amber)
        if (i1 === 13 && i2 === 15) strokeColor = '#f59e0b'

        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.lineWidth = 3
        ctx.strokeStyle = strokeColor
        ctx.lineCap = 'round'
        ctx.stroke()
      }
    })

    // Draw Joints (Circles)
    lms.forEach((lm) => {
      if (lm.visibility > 0.5) {
        const x = lm.x * width
        const y = lm.y * height

        ctx.beginPath()
        ctx.arc(x, y, 4, 0, 2 * Math.PI)
        ctx.fillStyle = lm.id === 16 ? '#34d399' : (lm.id === 15 ? '#fbbf24' : '#60a5fa')
        ctx.fill()
        ctx.lineWidth = 1.5
        ctx.strokeStyle = '#ffffff'
        ctx.stroke()
      }
    })

    // Draw Biomechanical Angle Readout directly on Bow Elbow (Right Elbow id=14)
    if (showAngles && lmap.has(12) && lmap.has(14) && lmap.has(16)) {
      const e = lmap.get(14)!
      const ex = e.x * width
      const ey = e.y * height
      const bowAngle = analysisData?.biomechanics_summary?.avg_bow_arm_angle || 179.2

      ctx.fillStyle = 'rgba(15, 23, 42, 0.85)'
      ctx.fillRect(ex + 10, ey - 22, 92, 22)
      ctx.strokeStyle = '#10b981'
      ctx.strokeRect(ex + 10, ey - 22, 92, 22)

      ctx.fillStyle = '#10b981'
      ctx.font = 'bold 11px Inter, sans-serif'
      ctx.fillText(`${bowAngle}° Bow Arm`, ex + 14, ey - 7)
    }

    // Draw Anchor Crosshair (Left Wrist id=15)
    if (lmap.has(15)) {
      const w = lmap.get(15)!
      const wx = w.x * width
      const wy = w.y * height

      ctx.beginPath()
      ctx.arc(wx, wy, 8, 0, 2 * Math.PI)
      ctx.strokeStyle = '#f59e0b'
      ctx.lineWidth = 1.5
      ctx.stroke()
    }
  }

  // Simulator live prediction call
  const triggerSimulatorPrediction = async () => {
    try {
      const res = await poseApi.predictMetrics({
        bow_arm_angle: simBowArm,
        draw_elbow_angle: simDrawElbow,
        anchor_jitter: simJitter,
        bow_arm_deflection_deg: simDeflection,
        anchor_duration_sec: simHoldDuration
      })
      setSimPrediction(res.prediction)
    } catch (err) {
      toast.error('Simulation calculation failed')
    }
  }

  // Run simulator on mount or when tab changes
  useEffect(() => {
    if (activeTab === 'simulator' && !simPrediction) {
      triggerSimulatorPrediction()
    }
  }, [activeTab])

  // Current active shot phase
  const currentPhase = analysisData?.phases?.find(
    (p) => currentTime >= p.start_time && currentTime <= p.end_time
  )?.phase || 'stance'

  const prediction = analysisData?.prediction
  const bioSummary = analysisData?.biomechanics_summary

  return (
    <div className="space-y-6 pb-12">
      {/* ─── Top Header Ribbon ────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-navy-900 border border-navy-700/80 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute -right-16 -top-16 w-64 h-64 bg-gold-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex items-center gap-4 relative z-10">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-gold-600 via-amber-500 to-yellow-300 p-0.5 shadow-lg shadow-gold-500/20">
            <div className="w-full h-full bg-navy-900 rounded-[14px] flex items-center justify-center">
              <Crosshair className="w-7 h-7 text-gold-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-black text-slate-100 tracking-tight">
                Archer Pose Biomechanics Intelligence
              </h1>
              <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> AI Vision Active
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-0.5">
              Full-body kinematic tracking, multi-phase shot segmentation & Olympic score prediction
            </p>
          </div>
        </div>

        {/* Action Controls & Tab Switcher */}
        <div className="flex items-center gap-3 relative z-10">
          <div className="flex bg-navy-950 p-1 rounded-xl border border-navy-700">
            <button
              onClick={() => setActiveTab('video')}
              id="tab-video-analysis"
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'video'
                  ? 'bg-gold-500 text-navy-950 shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Film className="w-3.5 h-3.5" /> Video Telemetry
            </button>
            <button
              onClick={() => setActiveTab('simulator')}
              id="tab-form-simulator"
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'simulator'
                  ? 'bg-gold-500 text-navy-950 shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sliders className="w-3.5 h-3.5" /> Form Simulator
            </button>
          </div>

          <label
            htmlFor="video-upload"
            className="flex items-center gap-2 px-4 py-2 bg-navy-800 hover:bg-navy-700 text-slate-200 border border-navy-600 rounded-xl text-xs font-bold cursor-pointer transition-all shadow-md active:scale-95"
          >
            <Upload className="w-4 h-4 text-gold-400" />
            Upload Video
            <input
              id="video-upload"
              ref={fileInputRef}
              type="file"
              accept="video/*"
              className="hidden"
              onChange={handleFileUpload}
            />
          </label>
        </div>
      </div>

      {/* ─── 1-Click Sample Videos Ribbon ─────────────────────────────────── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-bold text-slate-400 px-1">
          <span className="flex items-center gap-1.5 uppercase tracking-wider">
            <Film className="w-3.5 h-3.5 text-gold-400" /> 1-Click Benchmark Shooting Tests
          </span>
          <span>Click any card to analyze instantly</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {sampleVideos.map((s) => {
            const isSelected = selectedVideoId === s.id
            const isGold = s.id === 'gold_form_10'
            const isDrop = s.id === 'bow_arm_drop_7'

            return (
              <button
                key={s.id}
                id={`sample-card-${s.id}`}
                onClick={() => loadAndAnalyzeSample(s.id)}
                disabled={analyzing}
                className={`text-left p-4 rounded-xl border transition-all relative overflow-hidden group ${
                  isSelected
                    ? 'bg-navy-800/90 border-gold-500/80 shadow-lg shadow-gold-500/10 ring-1 ring-gold-500/50'
                    : 'bg-navy-900/60 border-navy-700/60 hover:bg-navy-800/60 hover:border-navy-600'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <span
                    className={`px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider ${
                      isGold
                        ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30'
                        : isDrop
                        ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                        : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                    }`}
                  >
                    {s.badge}
                  </span>
                  <div className="text-right">
                    <span className="text-lg font-black text-slate-100">Score {s.score_display}</span>
                    <span className="text-[10px] block text-slate-400">{s.form_score_pct}% Form</span>
                  </div>
                </div>

                <h3 className="font-bold text-sm text-slate-100 mt-2 group-hover:text-gold-400 transition-colors">
                  {s.title}
                </h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                  {s.description}
                </p>

                {isSelected && (
                  <div className="mt-3 flex items-center gap-1.5 text-[11px] font-bold text-gold-400">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Active in Telemetry View
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {activeTab === 'video' ? (
        /* ─── Video Telemetry & Analysis Grid ──────────────────────────────── */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Video & Canvas Overlay (7 Cols) */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-navy-900 border border-navy-700 rounded-2xl overflow-hidden shadow-2xl relative flex flex-col">
              {/* Video Player + Overlay Canvas */}
              <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
                <video
                  ref={videoRef}
                  id="pose-video-player"
                  playsInline
                  crossOrigin="anonymous"
                  onEnded={() => setIsPlaying(false)}
                  className="w-full h-full object-contain"
                />
                <canvas
                  ref={canvasRef}
                  id="pose-overlay-canvas"
                  className="absolute inset-0 w-full h-full pointer-events-none"
                />

                {/* Loading / Analyzing Overlay */}
                {analyzing && (
                  <div className="absolute inset-0 bg-navy-950/80 backdrop-blur-sm flex flex-col items-center justify-center gap-3 z-30">
                    <div className="w-10 h-10 border-4 border-gold-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-sm font-bold text-slate-200">Executing Deep Kinematic Analysis...</p>
                    <p className="text-xs text-slate-400">Evaluating 33 MediaPipe Landmarks across 180 Frames</p>
                  </div>
                )}

                {/* Live Phase HUD Badge */}
                {showHUD && (
                  <div className="absolute top-4 left-4 z-20 flex items-center gap-2">
                    <span
                      id="hud-phase-badge"
                      className={`px-3 py-1 rounded-lg text-xs font-black uppercase tracking-wider backdrop-blur-md shadow-lg ${
                        currentPhase === 'stance'
                          ? 'bg-slate-800/90 text-slate-200 border border-slate-600'
                          : currentPhase === 'draw'
                          ? 'bg-blue-600/90 text-white border border-blue-400'
                          : currentPhase === 'anchor'
                          ? 'bg-emerald-600/90 text-white border border-emerald-400'
                          : 'bg-rose-600/90 text-white border border-rose-400'
                      }`}
                    >
                      Phase: {currentPhase}
                    </span>
                    <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-navy-950/80 text-slate-300 border border-navy-700 backdrop-blur-md">
                      {currentTime.toFixed(2)}s / {duration.toFixed(2)}s
                    </span>
                  </div>
                )}

                {/* Overlaid Target Score Badge */}
                {prediction && showHUD && (
                  <div className="absolute top-4 right-4 z-20">
                    <div
                      className="px-3 py-1 rounded-lg text-xs font-black uppercase tracking-wider backdrop-blur-md shadow-lg flex items-center gap-1.5"
                      style={{
                        backgroundColor: `${prediction.category_color}25`,
                        borderColor: prediction.category_color,
                        color: prediction.category_color,
                        borderWidth: 1
                      }}
                    >
                      <Crosshair className="w-3.5 h-3.5" />
                      Predicted: {prediction.score_display} ({prediction.score_category})
                    </div>
                  </div>
                )}
              </div>

              {/* Video Timeline & Scrubbing Slider */}
              <div className="p-4 bg-navy-950 border-t border-navy-800 space-y-3">
                {/* 4-Phase Timeline Bar */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] font-bold text-slate-400 px-0.5">
                    <span>Stance (0-20%)</span>
                    <span>Draw (20-42%)</span>
                    <span>Anchor Hold (42-73%)</span>
                    <span>Release (73-100%)</span>
                  </div>
                  <div className="h-2 w-full bg-navy-800 rounded-full overflow-hidden flex cursor-pointer">
                    <div
                      onClick={() => handleSeek(0.5)}
                      className="h-full bg-slate-600 hover:opacity-80 transition-opacity"
                      style={{ width: '20%' }}
                      title="Stance Phase"
                    />
                    <div
                      onClick={() => handleSeek(1.8)}
                      className="h-full bg-blue-500 hover:opacity-80 transition-opacity"
                      style={{ width: '22%' }}
                      title="Draw Phase"
                    />
                    <div
                      onClick={() => handleSeek(3.2)}
                      className="h-full bg-emerald-500 hover:opacity-80 transition-opacity"
                      style={{ width: '31%' }}
                      title="Anchor Phase"
                    />
                    <div
                      onClick={() => handleSeek(4.8)}
                      className="h-full bg-rose-500 hover:opacity-80 transition-opacity"
                      style={{ width: '27%' }}
                      title="Release Phase"
                    />
                  </div>
                </div>

                {/* Continuous Range Slider */}
                <input
                  type="range"
                  id="pose-timeline-slider"
                  min="0"
                  max={duration}
                  step="0.033"
                  value={currentTime}
                  onChange={(e) => handleSeek(parseFloat(e.target.value))}
                  className="w-full accent-gold-500 h-1.5 bg-navy-800 rounded-lg cursor-pointer"
                />

                {/* Controls Bar */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                  {/* Playback Buttons */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSeek(0)}
                      title="Reset"
                      className="p-2 text-slate-400 hover:text-slate-100 bg-navy-900 border border-navy-700 rounded-lg transition-colors"
                    >
                      <RotateCcw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => stepFrame(false)}
                      title="Step 1 Frame Back"
                      className="p-2 text-slate-400 hover:text-slate-100 bg-navy-900 border border-navy-700 rounded-lg transition-colors"
                    >
                      <Rewind className="w-4 h-4" />
                    </button>
                    <button
                      id="pose-play-pause-btn"
                      onClick={togglePlay}
                      className="flex items-center gap-1.5 px-4 py-2 bg-gold-500 hover:bg-gold-400 text-navy-950 font-black rounded-lg transition-all shadow-md active:scale-95 text-xs"
                    >
                      {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                      {isPlaying ? 'PAUSE' : 'PLAY'}
                    </button>
                    <button
                      onClick={() => stepFrame(true)}
                      title="Step 1 Frame Forward"
                      className="p-2 text-slate-400 hover:text-slate-100 bg-navy-900 border border-navy-700 rounded-lg transition-colors"
                    >
                      <FastForward className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Speed Controls */}
                  <div className="flex items-center gap-1 bg-navy-900 p-1 rounded-lg border border-navy-800 text-[11px] font-bold">
                    {[0.25, 0.5, 1.0].map((rate) => (
                      <button
                        key={rate}
                        onClick={() => changeSpeed(rate)}
                        className={`px-2 py-0.5 rounded ${
                          playbackRate === rate ? 'bg-gold-500/20 text-gold-400' : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        {rate}x
                      </button>
                    ))}
                  </div>

                  {/* Overlays Toggles */}
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                    <button
                      onClick={() => setShowSkeleton(!showSkeleton)}
                      className={`flex items-center gap-1 px-2.5 py-1 rounded-lg border text-[11px] ${
                        showSkeleton
                          ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400'
                          : 'bg-navy-900 border-navy-700 text-slate-400'
                      }`}
                    >
                      {showSkeleton ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                      Skeleton
                    </button>
                    <button
                      onClick={() => setShowAngles(!showAngles)}
                      className={`flex items-center gap-1 px-2.5 py-1 rounded-lg border text-[11px] ${
                        showAngles
                          ? 'bg-blue-500/15 border-blue-500/40 text-blue-400'
                          : 'bg-navy-900 border-navy-700 text-slate-400'
                      }`}
                    >
                      Angle Arcs
                    </button>
                    <button
                      onClick={() => setShowHUD(!showHUD)}
                      className={`flex items-center gap-1 px-2.5 py-1 rounded-lg border text-[11px] ${
                        showHUD
                          ? 'bg-purple-500/15 border-purple-500/40 text-purple-400'
                          : 'bg-navy-900 border-navy-700 text-slate-400'
                      }`}
                    >
                      HUD
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Biomechanical Telemetry Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-navy-900/90 border border-navy-700 rounded-xl p-3 shadow-md">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Bow Arm Angle
                </span>
                <span className="text-xl font-black text-emerald-400 mt-1 block">
                  {bioSummary?.avg_bow_arm_angle || 179.2}°
                </span>
                <span className="text-[10px] text-slate-400">Target: 178°-180°</span>
              </div>

              <div className="bg-navy-900/90 border border-navy-700 rounded-xl p-3 shadow-md">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Draw Elbow
                </span>
                <span className="text-xl font-black text-amber-400 mt-1 block">
                  {bioSummary?.avg_draw_elbow_angle || 138.5}°
                </span>
                <span className="text-[10px] text-slate-400">Target: 135°-145°</span>
              </div>

              <div className="bg-navy-900/90 border border-navy-700 rounded-xl p-3 shadow-md">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Anchor Hold Time
                </span>
                <span className="text-xl font-black text-cyan-400 mt-1 block">
                  {bioSummary?.anchor_hold_duration_sec || 1.9}s
                </span>
                <span className="text-[10px] text-slate-400">Optimal: 1.5-2.5s</span>
              </div>

              <div className="bg-navy-900/90 border border-navy-700 rounded-xl p-3 shadow-md">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Release Drop
                </span>
                <span
                  className={`text-xl font-black mt-1 block ${
                    (bioSummary?.bow_arm_deflection_deg || 0) > 3.0 ? 'text-rose-400' : 'text-emerald-400'
                  }`}
                >
                  {bioSummary?.bow_arm_deflection_deg || 0.4}°
                </span>
                <span className="text-[10px] text-slate-400">Limit: &lt; 1.5°</span>
              </div>
            </div>
          </div>

          {/* Right Column: AI Score Prediction & Target Radar (5 Cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Primary Score Prediction Card */}
            {prediction && (
              <div
                className="bg-navy-900 border rounded-2xl p-6 shadow-2xl relative overflow-hidden"
                style={{ borderColor: `${prediction.category_color}50` }}
              >
                <div
                  className="absolute -right-20 -top-20 w-48 h-48 rounded-full blur-3xl opacity-20 pointer-events-none"
                  style={{ backgroundColor: prediction.category_color }}
                />

                <div className="flex items-center justify-between">
                  <span className="text-xs font-black uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <Award className="w-4 h-4 text-gold-400" /> Olympic Score Forecast
                  </span>
                  <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-navy-800 text-slate-300 border border-navy-700">
                    Confidence: {(prediction.confidence * 100).toFixed(0)}%
                  </span>
                </div>

                {/* Score Number & Category Badge */}
                <div className="mt-4 flex items-center gap-6">
                  <div
                    className="w-24 h-24 rounded-2xl flex flex-col items-center justify-center font-black text-navy-950 shadow-xl"
                    style={{ backgroundColor: prediction.category_color }}
                  >
                    <span className="text-4xl leading-none">{prediction.score_display}</span>
                    <span className="text-[10px] uppercase font-bold tracking-wider mt-1">
                      {prediction.score_category}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <span className="text-xs text-slate-400 font-semibold">Predicted Hit Zone:</span>
                    <h2 className="text-xl font-black text-slate-100">{prediction.zone_description}</h2>
                    <div className="flex items-center gap-2 pt-1">
                      <span className="text-sm font-bold text-gold-400">{prediction.form_score_pct}%</span>
                      <span className="text-xs text-slate-400">Biomechanics Quality Rating</span>
                    </div>
                  </div>
                </div>

                {/* Olympic Concentric Ring Target Radar */}
                <div className="mt-6 pt-6 border-t border-navy-800">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-400 mb-2">
                    <span>Virtual Target Impact Visualization</span>
                    <span className="text-[11px] text-gold-400">{prediction.score_category} Ring</span>
                  </div>

                  <div className="relative aspect-square max-w-[200px] mx-auto bg-navy-950/80 rounded-full border border-navy-700/80 p-2 flex items-center justify-center">
                    {/* Olympic Rings */}
                    <svg viewBox="0 0 200 200" className="w-full h-full">
                      {/* 1-2 White */}
                      <circle cx="100" cy="100" r="95" fill="#f8fafc" stroke="#cbd5e1" strokeWidth="1" />
                      <circle cx="100" cy="100" r="76" fill="#f8fafc" stroke="#cbd5e1" strokeWidth="1" />
                      {/* 3-4 Black */}
                      <circle cx="100" cy="100" r="67" fill="#1e293b" />
                      <circle cx="100" cy="100" r="57" fill="#1e293b" stroke="#475569" strokeWidth="0.8" />
                      {/* 5-6 Blue */}
                      <circle cx="100" cy="100" r="48" fill="#2563eb" />
                      <circle cx="100" cy="100" r="38" fill="#2563eb" stroke="#60a5fa" strokeWidth="0.8" />
                      {/* 7-8 Red */}
                      <circle cx="100" cy="100" r="29" fill="#dc2626" />
                      <circle cx="100" cy="100" r="19" fill="#dc2626" stroke="#f87171" strokeWidth="0.8" />
                      {/* 9-10 Gold */}
                      <circle cx="100" cy="100" r="10" fill="#f59e0b" />
                      <circle cx="100" cy="100" r="5" fill="#fbbf24" stroke="#d97706" strokeWidth="0.5" />

                      {/* Predicted Impact Crosshair marker */}
                      {(() => {
                        let offset = 0
                        if (prediction.predicted_score >= 10) offset = 2
                        else if (prediction.predicted_score === 9) offset = 8
                        else if (prediction.predicted_score === 8) offset = 16
                        else if (prediction.predicted_score === 7) offset = 26
                        else if (prediction.predicted_score === 6) offset = 36
                        else offset = 48

                        // If arm drop, arrow drops downward
                        const py = 100 + offset
                        const px = 100

                        return (
                          <g>
                            <circle cx={px} cy={py} r="4" fill="#00ffff" />
                            <circle cx={px} cy={py} r="7" fill="none" stroke="#00ffff" strokeWidth="1.5" className="animate-ping" />
                            <line x1={px - 8} y1={py} x2={px + 8} y2={py} stroke="#00ffff" strokeWidth="1.5" />
                            <line x1={px} y1={py - 8} x2={px} y2={py + 8} stroke="#00ffff" strokeWidth="1.5" />
                          </g>
                        )
                      })()}
                    </svg>
                  </div>
                </div>
              </div>
            )}

            {/* Coaching Diagnostics & Actionable Corrections */}
            <div className="bg-navy-900 border border-navy-700 rounded-2xl p-5 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-amber-400" /> Biomechanical Flaw Diagnostics
                </span>
                <span className="text-[11px] text-slate-400">Coach Feedback</span>
              </div>

              <div className="space-y-2.5">
                {prediction?.diagnostics?.map((diag: any, idx: number) => {
                  const isExc = diag.status === 'EXCELLENT'
                  const isGood = diag.status === 'GOOD'

                  return (
                    <div
                      key={idx}
                      className={`p-3 rounded-xl border transition-all ${
                        isExc
                          ? 'bg-emerald-950/20 border-emerald-500/30'
                          : isGood
                          ? 'bg-blue-950/20 border-blue-500/30'
                          : 'bg-rose-950/20 border-rose-500/30'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-200">{diag.metric}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-black text-slate-100">{diag.value}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                              isExc
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : isGood
                                ? 'bg-blue-500/20 text-blue-400'
                                : 'bg-rose-500/20 text-rose-400'
                            }`}
                          >
                            {diag.status}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 leading-relaxed">{diag.message}</p>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* ─── Biomechanical Form Simulator Tab ────────────────────────────── */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 bg-navy-900 border border-navy-700 rounded-2xl p-6 shadow-xl space-y-6">
            <div>
              <h2 className="text-lg font-black text-slate-100 flex items-center gap-2">
                <Sliders className="w-5 h-5 text-gold-400" /> Biomechanical Angle Simulator
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Adjust posture angles and stability metrics to see how the trained ML model forecasts target scoring.
              </p>
            </div>

            <div className="space-y-5">
              {/* Bow Arm Slider */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-bold">
                  <span className="text-slate-300">Front Bow Arm Alignment Angle</span>
                  <span className="text-emerald-400 font-mono">{simBowArm.toFixed(1)}° (Ideal: 178°-180°)</span>
                </div>
                <input
                  type="range"
                  min="160.0"
                  max="180.0"
                  step="0.2"
                  value={simBowArm}
                  onChange={(e) => {
                    setSimBowArm(parseFloat(e.target.value))
                    triggerSimulatorPrediction()
                  }}
                  className="w-full accent-emerald-500 h-2 bg-navy-800 rounded-lg cursor-pointer"
                />
              </div>

              {/* Draw Elbow Slider */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-bold">
                  <span className="text-slate-300">Rear Draw Elbow Elevation Angle</span>
                  <span className="text-amber-400 font-mono">{simDrawElbow.toFixed(1)}° (Ideal: 135°-145°)</span>
                </div>
                <input
                  type="range"
                  min="115.0"
                  max="155.0"
                  step="0.5"
                  value={simDrawElbow}
                  onChange={(e) => {
                    setSimDrawElbow(parseFloat(e.target.value))
                    triggerSimulatorPrediction()
                  }}
                  className="w-full accent-amber-500 h-2 bg-navy-800 rounded-lg cursor-pointer"
                />
              </div>

              {/* Anchor Tremor Jitter Slider */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-bold">
                  <span className="text-slate-300">Anchor Point Tremor / Jitter (px)</span>
                  <span className="text-cyan-400 font-mono">{simJitter.toFixed(2)} px (Ideal: &lt; 1.0 px)</span>
                </div>
                <input
                  type="range"
                  min="0.2"
                  max="6.0"
                  step="0.1"
                  value={simJitter}
                  onChange={(e) => {
                    setSimJitter(parseFloat(e.target.value))
                    triggerSimulatorPrediction()
                  }}
                  className="w-full accent-cyan-500 h-2 bg-navy-800 rounded-lg cursor-pointer"
                />
              </div>

              {/* Release Deflection / Arm Drop Slider */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-bold">
                  <span className="text-slate-300">Bow Arm Drop Deflection at Release</span>
                  <span className="text-rose-400 font-mono">{simDeflection.toFixed(1)}° (Ideal: &lt; 1.2°)</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="10.0"
                  step="0.2"
                  value={simDeflection}
                  onChange={(e) => {
                    setSimDeflection(parseFloat(e.target.value))
                    triggerSimulatorPrediction()
                  }}
                  className="w-full accent-rose-500 h-2 bg-navy-800 rounded-lg cursor-pointer"
                />
              </div>

              {/* Anchor Duration Slider */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-bold">
                  <span className="text-slate-300">Anchor Aiming Hold Duration</span>
                  <span className="text-indigo-400 font-mono">{simHoldDuration.toFixed(2)}s (Ideal: 1.5 - 2.5s)</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="4.5"
                  step="0.1"
                  value={simHoldDuration}
                  onChange={(e) => {
                    setSimHoldDuration(parseFloat(e.target.value))
                    triggerSimulatorPrediction()
                  }}
                  className="w-full accent-indigo-500 h-2 bg-navy-800 rounded-lg cursor-pointer"
                />
              </div>
            </div>

            {/* Preset Buttons */}
            <div className="pt-4 border-t border-navy-800 flex flex-wrap gap-2">
              <span className="text-xs font-bold text-slate-400 w-full mb-1">Quick Form Presets:</span>
              <button
                onClick={() => {
                  setSimBowArm(179.5)
                  setSimDrawElbow(139.2)
                  setSimJitter(0.5)
                  setSimDeflection(0.3)
                  setSimHoldDuration(2.0)
                  triggerSimulatorPrediction()
                }}
                className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-bold"
              >
                Olympic Gold Preset
              </button>
              <button
                onClick={() => {
                  setSimBowArm(174.0)
                  setSimDrawElbow(134.0)
                  setSimJitter(1.6)
                  setSimDeflection(6.2)
                  setSimHoldDuration(1.6)
                  triggerSimulatorPrediction()
                }}
                className="px-3 py-1.5 rounded-lg bg-rose-500/20 text-rose-300 border border-rose-500/40 text-xs font-bold"
              >
                Shoulder Drop Preset
              </button>
              <button
                onClick={() => {
                  setSimBowArm(166.0)
                  setSimDrawElbow(121.0)
                  setSimJitter(4.5)
                  setSimDeflection(8.0)
                  setSimHoldDuration(0.8)
                  triggerSimulatorPrediction()
                }}
                className="px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-300 border border-blue-500/40 text-xs font-bold"
              >
                Tremor / Flinch Preset
              </button>
            </div>
          </div>

          {/* Right Column: Live Simulator Forecast */}
          <div className="lg:col-span-5 space-y-6">
            {simPrediction && (
              <div
                className="bg-navy-900 border rounded-2xl p-6 shadow-2xl space-y-5"
                style={{ borderColor: `${simPrediction.category_color}50` }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black uppercase text-slate-400">Model Output</span>
                  <span className="text-xs font-bold text-gold-400">{simPrediction.form_score_pct}% Form Score</span>
                </div>

                <div className="flex items-center gap-6">
                  <div
                    className="w-24 h-24 rounded-2xl flex flex-col items-center justify-center font-black text-navy-950 shadow-xl"
                    style={{ backgroundColor: simPrediction.category_color }}
                  >
                    <span className="text-4xl leading-none">{simPrediction.score_display}</span>
                    <span className="text-[10px] uppercase font-bold tracking-wider mt-1">
                      {simPrediction.score_category}
                    </span>
                  </div>

                  <div>
                    <span className="text-xs text-slate-400 font-semibold">Predicted Ring:</span>
                    <h2 className="text-xl font-black text-slate-100">{simPrediction.zone_description}</h2>
                    <p className="text-xs text-slate-400 mt-1">
                      Exact Calibrated Score: {simPrediction.exact_score} / 10.0
                    </p>
                  </div>
                </div>

                <div className="space-y-2 pt-4 border-t border-navy-800">
                  <span className="text-xs font-bold text-slate-400">Diagnostic Feedback:</span>
                  {simPrediction.diagnostics?.map((diag: any, idx: number) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-navy-950 border border-navy-800 text-xs">
                      <div className="flex justify-between font-bold">
                        <span className="text-slate-200">{diag.metric}</span>
                        <span style={{ color: simPrediction.category_color }}>{diag.status}</span>
                      </div>
                      <p className="text-slate-400 mt-0.5 text-[11px]">{diag.message}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
