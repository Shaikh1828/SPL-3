import React, { useState, useEffect, useRef } from 'react'
import {
  Play, Pause, RotateCcw, Upload, Sparkles, CheckCircle2,
  Crosshair, Sliders, Eye, EyeOff, FastForward,
  Rewind, ShieldAlert, Award, Film, Video, Radio, Camera as CameraIcon,
  Layers, ShieldCheck
} from 'lucide-react'
import { poseApi } from '@/api/pose'
import type { SampleVideoItem, PoseAnalysisResponse, PoseFrameData, PostureAccuracyData } from '@/types'
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

  // Dual-Camera Mode
  const [cameraLayout, setCameraLayout] = useState<'dual' | 'posture_only'>('dual')
  const [isWebcamActive, setIsWebcamActive] = useState<boolean>(false)

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
  const webcamVideoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const animationFrameRef = useRef<number | null>(null)
  const webcamStreamRef = useRef<MediaStream | null>(null)

  // Load sample videos on mount
  useEffect(() => {
    loadSampleVideos()
    return () => {
      stopWebcam()
    }
  }, [])

  const loadSampleVideos = async () => {
    try {
      const res = await poseApi.getSampleVideos()
      setSampleVideos(res.videos || [])
      if (res.videos && res.videos.length > 0) {
        loadAndAnalyzeSample('gold_form_10')
      }
    } catch (err) {
      toast.error('Failed to load benchmark videos')
    }
  }

  const loadAndAnalyzeSample = async (videoId: string) => {
    try {
      if (isWebcamActive) stopWebcam()
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

    if (isWebcamActive) stopWebcam()

    const formData = new FormData()
    formData.append('file', file)

    try {
      setAnalyzing(true)
      toast.loading('Analyzing archer kinematics and extracting pose...', { id: 'upload' })
      const data = await poseApi.analyzeUploadedVideo(formData)
      setAnalysisData(data)
      setSelectedVideoId('custom')
      setDuration(data.duration_sec || 6.0)

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

  // Live Webcam Controls for Archer Posture Camera
  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        audio: false
      })
      webcamStreamRef.current = stream
      if (webcamVideoRef.current) {
        webcamVideoRef.current.srcObject = stream
        webcamVideoRef.current.play()
      }
      setIsWebcamActive(true)
      toast.success('Archer Posture Camera connected live!')
    } catch (err: any) {
      toast.error(`Camera permission denied or camera unavailable: ${err.message}`)
    }
  }

  const stopWebcam = () => {
    if (webcamStreamRef.current) {
      webcamStreamRef.current.getTracks().forEach((track) => track.stop())
      webcamStreamRef.current = null
    }
    if (webcamVideoRef.current) {
      webcamVideoRef.current.srcObject = null
    }
    setIsWebcamActive(false)
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
      if (!video || !canvas || !analysisData || isWebcamActive) return

      const ctx = canvas.getContext('2d')
      if (!ctx) return

      if (canvas.width !== video.clientWidth || canvas.height !== video.clientHeight) {
        canvas.width = video.clientWidth
        canvas.height = video.clientHeight
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const cTime = video.currentTime
      setCurrentTime(cTime)

      const frames = analysisData.frames_landmarks || []
      if (frames.length > 0 && showSkeleton) {
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
  }, [analysisData, showSkeleton, showAngles, showHUD, isWebcamActive])

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

        let strokeColor = '#3b82f6'
        if (i1 === 12 && i2 === 14) strokeColor = '#10b981'
        if (i1 === 14 && i2 === 16) strokeColor = '#10b981'
        if (i1 === 11 && i2 === 13) strokeColor = '#f59e0b'
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

    // Draw Joints
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

    // Biomechanical Angle Readout directly on Bow Elbow
    if (showAngles && lmap.has(12) && lmap.has(14) && lmap.has(16)) {
      const e = lmap.get(14)!
      const ex = e.x * width
      const ey = e.y * height
      const bowAngle = analysisData?.biomechanics_summary?.avg_bow_arm_angle || 179.2

      ctx.fillStyle = 'rgba(15, 23, 42, 0.85)'
      ctx.fillRect(ex + 10, ey - 22, 95, 22)
      ctx.strokeStyle = '#10b981'
      ctx.strokeRect(ex + 10, ey - 22, 95, 22)

      ctx.fillStyle = '#10b981'
      ctx.font = 'bold 11px Inter, sans-serif'
      ctx.fillText(`${bowAngle}° Bow Arm`, ex + 14, ey - 7)
    }

    // Anchor Crosshair (Left Wrist id=15)
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
  const postureAccuracy: PostureAccuracyData | undefined = prediction?.posture_accuracy

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
                Archer Posture & Biomechanics Intelligence
              </h1>
              <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> Multi-Cam AI Vision Active
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-0.5">
              Dedicated Archer Body Camera, Real-Time Posture Accuracy % & Target Scoring Simulation
            </p>
          </div>
        </div>

        {/* Action Controls & Tab Switcher */}
        <div className="flex items-center gap-3 relative z-10">
          {/* Dual Camera Layout Selector */}
          <div className="flex bg-navy-950 p-1 rounded-xl border border-navy-700">
            <button
              onClick={() => setCameraLayout('dual')}
              title="Dual Camera (Archer Posture + Target View)"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                cameraLayout === 'dual'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" /> Dual-Cam
            </button>
            <button
              onClick={() => setCameraLayout('posture_only')}
              title="Archer Posture Camera Only"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                cameraLayout === 'posture_only'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Video className="w-3.5 h-3.5" /> Archer Cam
            </button>
          </div>

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

          {/* Live Webcam Toggle for Archer Posture Camera */}
          <button
            onClick={isWebcamActive ? stopWebcam : startWebcam}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shadow-md ${
              isWebcamActive
                ? 'bg-rose-600 hover:bg-rose-500 text-white animate-pulse'
                : 'bg-navy-800 hover:bg-navy-700 text-slate-200 border border-navy-600'
            }`}
          >
            <CameraIcon className="w-4 h-4 text-emerald-400" />
            {isWebcamActive ? 'Stop Live Cam' : 'Live Archer Cam'}
          </button>

          <label
            htmlFor="video-upload"
            className="flex items-center gap-2 px-3.5 py-2 bg-navy-800 hover:bg-navy-700 text-slate-200 border border-navy-600 rounded-xl text-xs font-bold cursor-pointer transition-all shadow-md active:scale-95"
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

      {/* ─── Real-Time Posture Accuracy Status Banner ─────────────────────── */}
      {postureAccuracy && (
        <div
          className="bg-navy-900 border rounded-2xl p-5 shadow-xl relative overflow-hidden transition-all"
          style={{ borderColor: `${postureAccuracy.tier_color}60` }}
        >
          <div
            className="absolute -right-16 -top-16 w-48 h-48 rounded-full blur-3xl opacity-20 pointer-events-none"
            style={{ backgroundColor: postureAccuracy.tier_color }}
          />

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              {/* Circular Gauge Ring */}
              <div
                className="w-16 h-16 rounded-2xl flex flex-col items-center justify-center font-black text-navy-950 shadow-lg"
                style={{ backgroundColor: postureAccuracy.tier_color }}
              >
                <span className="text-2xl leading-none">{postureAccuracy.overall_accuracy_pct}%</span>
                <span className="text-[9px] uppercase font-bold tracking-wider mt-0.5">Accurate</span>
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-black uppercase tracking-wider text-slate-400">
                    Archer Posture Camera Feedback
                  </span>
                  <span
                    className="px-2 py-0.5 text-[10px] font-black rounded uppercase tracking-wider"
                    style={{
                      backgroundColor: `${postureAccuracy.tier_color}20`,
                      color: postureAccuracy.tier_color,
                      border: `1px solid ${postureAccuracy.tier_color}40`
                    }}
                  >
                    {postureAccuracy.accuracy_label}
                  </span>
                </div>
                <h3 className="text-lg font-black text-slate-100 mt-0.5">
                  {postureAccuracy.overall_accuracy_pct >= 90
                    ? '✨ Flawless Body Mechanics — Minimal Jitter & Crisp Level Release'
                    : postureAccuracy.overall_accuracy_pct >= 75
                    ? '⚠️ Minor Posture Deviation Detected — Shoulder Drop pulling score down'
                    : '🚨 Form Flaws Detected — Unstable Anchor Hold and Sagging Elbow'}
                </h3>
              </div>
            </div>

            {/* Sub-Metric Accuracy Progress Bars */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-semibold">
              <div className="bg-navy-950/80 p-2.5 rounded-xl border border-navy-800">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Bow Arm</span>
                  <span className="font-bold text-slate-200">
                    {postureAccuracy.components.bow_arm_accuracy_pct}%
                  </span>
                </div>
                <div className="h-1.5 w-full bg-navy-800 rounded-full mt-1.5 overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full"
                    style={{ width: `${postureAccuracy.components.bow_arm_accuracy_pct}%` }}
                  />
                </div>
              </div>

              <div className="bg-navy-950/80 p-2.5 rounded-xl border border-navy-800">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Release Drop</span>
                  <span className="font-bold text-slate-200">
                    {postureAccuracy.components.release_follow_through_accuracy_pct}%
                  </span>
                </div>
                <div className="h-1.5 w-full bg-navy-800 rounded-full mt-1.5 overflow-hidden">
                  <div
                    className="h-full bg-amber-500 rounded-full"
                    style={{ width: `${postureAccuracy.components.release_follow_through_accuracy_pct}%` }}
                  />
                </div>
              </div>

              <div className="bg-navy-950/80 p-2.5 rounded-xl border border-navy-800">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Anchor Jitter</span>
                  <span className="font-bold text-slate-200">
                    {postureAccuracy.components.anchor_stability_accuracy_pct}%
                  </span>
                </div>
                <div className="h-1.5 w-full bg-navy-800 rounded-full mt-1.5 overflow-hidden">
                  <div
                    className="h-full bg-cyan-500 rounded-full"
                    style={{ width: `${postureAccuracy.components.anchor_stability_accuracy_pct}%` }}
                  />
                </div>
              </div>

              <div className="bg-navy-950/80 p-2.5 rounded-xl border border-navy-800">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Draw Elbow</span>
                  <span className="font-bold text-slate-200">
                    {postureAccuracy.components.draw_elbow_accuracy_pct}%
                  </span>
                </div>
                <div className="h-1.5 w-full bg-navy-800 rounded-full mt-1.5 overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 rounded-full"
                    style={{ width: `${postureAccuracy.components.draw_elbow_accuracy_pct}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── 1-Click Sample Videos Ribbon ─────────────────────────────────── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-bold text-slate-400 px-1">
          <span className="flex items-center gap-1.5 uppercase tracking-wider">
            <Film className="w-3.5 h-3.5 text-gold-400" /> 1-Click Benchmark Shooting Tests
          </span>
          <span>Click any card to analyze posture accuracy instantly</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {sampleVideos.map((s) => {
            const isSelected = selectedVideoId === s.id && !isWebcamActive
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
        /* ─── Video Telemetry & Dual-Camera Analysis Grid ───────────────────── */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Camera Viewers (7 Cols or 8 Cols depending on dual view) */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-navy-900 border border-navy-700 rounded-2xl overflow-hidden shadow-2xl relative flex flex-col">
              {/* Dual Camera Layout Header */}
              <div className="px-4 py-2.5 bg-navy-950 border-b border-navy-800 flex items-center justify-between text-xs font-bold text-slate-400">
                <span className="flex items-center gap-2">
                  <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
                  {isWebcamActive
                    ? 'CAM-01: LIVE ARCHER POSTURE FEED'
                    : 'CAM-01: ARCHER BODY POSTURE CAMERA'}
                </span>
                {cameraLayout === 'dual' && (
                  <span className="text-gold-400 flex items-center gap-1">
                    <Crosshair className="w-3.5 h-3.5" /> CAM-02: SYNCHRONIZED TARGET FACE
                  </span>
                )}
              </div>

              {/* Cameras Display Area (Dual Camera or Single Camera) */}
              <div
                className={`relative bg-black flex items-center justify-center overflow-hidden ${
                  cameraLayout === 'dual' ? 'grid grid-cols-1 md:grid-cols-12 gap-1' : ''
                }`}
              >
                {/* CAM 1: Archer Posture Camera Feed */}
                <div
                  className={`relative aspect-video flex items-center justify-center overflow-hidden ${
                    cameraLayout === 'dual' ? 'md:col-span-8 border-r border-navy-800' : 'w-full'
                  }`}
                >
                  {isWebcamActive ? (
                    <video
                      ref={webcamVideoRef}
                      autoPlay
                      playsInline
                      muted
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <video
                      ref={videoRef}
                      id="pose-video-player"
                      playsInline
                      crossOrigin="anonymous"
                      onEnded={() => setIsPlaying(false)}
                      className="w-full h-full object-contain"
                    />
                  )}

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
                  {showHUD && !isWebcamActive && (
                    <div className="absolute top-3 left-3 z-20 flex items-center gap-2">
                      <span
                        id="hud-phase-badge"
                        className={`px-2.5 py-0.5 rounded-lg text-[11px] font-black uppercase tracking-wider backdrop-blur-md shadow-lg ${
                          currentPhase === 'stance'
                            ? 'bg-slate-800/90 text-slate-200 border border-slate-600'
                            : currentPhase === 'draw'
                            ? 'bg-blue-600/90 text-white border border-blue-400'
                            : currentPhase === 'anchor'
                            ? 'bg-emerald-600/90 text-white border border-emerald-400'
                            : 'bg-rose-600/90 text-white border border-rose-400'
                        }`}
                      >
                        {currentPhase}
                      </span>
                      <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold bg-navy-950/80 text-slate-300 border border-navy-700 backdrop-blur-md">
                        {currentTime.toFixed(2)}s
                      </span>
                    </div>
                  )}

                  {/* Live Accuracy Badge in Camera Corner */}
                  {postureAccuracy && showHUD && (
                    <div className="absolute bottom-3 left-3 z-20">
                      <div
                        className="px-2.5 py-1 rounded-lg text-[11px] font-black uppercase tracking-wider backdrop-blur-md shadow-lg flex items-center gap-1.5"
                        style={{
                          backgroundColor: `${postureAccuracy.tier_color}30`,
                          borderColor: postureAccuracy.tier_color,
                          color: postureAccuracy.tier_color,
                          borderWidth: 1
                        }}
                      >
                        <ShieldCheck className="w-3.5 h-3.5" />
                        Posture Accuracy: {postureAccuracy.overall_accuracy_pct}%
                      </div>
                    </div>
                  )}
                </div>

                {/* CAM 2: Synchronized Target Board Camera (When in Dual View) */}
                {cameraLayout === 'dual' && (
                  <div className="md:col-span-4 bg-navy-950/90 flex flex-col items-center justify-center p-3 relative aspect-video md:aspect-auto">
                    <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-1 flex items-center gap-1">
                      <Crosshair className="w-3 h-3 text-gold-400" /> Target Camera 02
                    </span>

                    {/* Concentric Olympic Target Diagram */}
                    <div className="relative aspect-square w-36 max-w-full bg-slate-900 rounded-full border border-navy-700 p-1 flex items-center justify-center">
                      <svg viewBox="0 0 200 200" className="w-full h-full">
                        <circle cx="100" cy="100" r="95" fill="#f8fafc" stroke="#cbd5e1" strokeWidth="1" />
                        <circle cx="100" cy="100" r="76" fill="#f8fafc" stroke="#cbd5e1" strokeWidth="1" />
                        <circle cx="100" cy="100" r="67" fill="#1e293b" />
                        <circle cx="100" cy="100" r="57" fill="#1e293b" stroke="#475569" strokeWidth="0.8" />
                        <circle cx="100" cy="100" r="48" fill="#2563eb" />
                        <circle cx="100" cy="100" r="38" fill="#2563eb" stroke="#60a5fa" strokeWidth="0.8" />
                        <circle cx="100" cy="100" r="29" fill="#dc2626" />
                        <circle cx="100" cy="100" r="19" fill="#dc2626" stroke="#f87171" strokeWidth="0.8" />
                        <circle cx="100" cy="100" r="10" fill="#f59e0b" />
                        <circle cx="100" cy="100" r="5" fill="#fbbf24" stroke="#d97706" strokeWidth="0.5" />

                        {/* Arrow Impact Point */}
                        {prediction && (() => {
                          let offset = 0
                          if (prediction.predicted_score >= 10) offset = 2
                          else if (prediction.predicted_score === 9) offset = 8
                          else if (prediction.predicted_score === 8) offset = 16
                          else if (prediction.predicted_score === 7) offset = 26
                          else if (prediction.predicted_score === 6) offset = 36
                          else offset = 48

                          const py = 100 + offset
                          const px = 100

                          return (
                            <g>
                              <circle cx={px} cy={py} r="4" fill="#00ffff" />
                              <circle cx={px} cy={py} r="8" fill="none" stroke="#00ffff" strokeWidth="1.5" className="animate-ping" />
                              <line x1={px - 6} y1={py} x2={px + 6} y2={py} stroke="#00ffff" strokeWidth="1.5" />
                              <line x1={px} y1={py - 6} x2={px} y2={py + 6} stroke="#00ffff" strokeWidth="1.5" />
                            </g>
                          )
                        })()}
                      </svg>
                    </div>

                    <div className="mt-2 text-center">
                      <span className="text-xs font-black text-slate-100 block">
                        Impact: {prediction?.score_display || '10'} Ring
                      </span>
                      <span className="text-[10px] text-slate-400 block">
                        {prediction?.zone_description || 'Gold 10-Ring'}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Video Timeline & Scrubbing Slider */}
              {!isWebcamActive && (
                <div className="p-4 bg-navy-950 border-t border-navy-800 space-y-3">
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
              )}
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

          {/* Right Column: AI Score Prediction & Coaching Cards (5 Cols) */}
          <div className="lg:col-span-5 space-y-6">
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
              </div>
            )}

            {/* Coaching Diagnostics & Actionable Corrections */}
            <div className="bg-navy-900 border border-navy-700 rounded-2xl p-5 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-amber-400" /> Biomechanical Flaw Diagnostics
                </span>
                <span className="text-[11px] text-slate-400">Coach Telemetry</span>
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
                Adjust posture angles and stability metrics to simulate how the Archer Posture Camera evaluates accuracy % and target score.
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

          {/* Right Column: Live Simulator Forecast & Accuracy Gauge */}
          <div className="lg:col-span-5 space-y-6">
            {simPrediction && (
              <div
                className="bg-navy-900 border rounded-2xl p-6 shadow-2xl space-y-5"
                style={{ borderColor: `${simPrediction.category_color}50` }}
              >
                {/* Accuracy Gauge in Simulator */}
                {simPrediction.posture_accuracy && (
                  <div className="p-4 bg-navy-950 rounded-xl border border-navy-800 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                        Simulated Posture Accuracy
                      </span>
                      <h4 className="text-xl font-black text-slate-100 mt-0.5">
                        {simPrediction.posture_accuracy.overall_accuracy_pct}% Accurate
                      </h4>
                      <span
                        className="text-xs font-bold"
                        style={{ color: simPrediction.posture_accuracy.tier_color }}
                      >
                        {simPrediction.posture_accuracy.accuracy_label}
                      </span>
                    </div>

                    <div
                      className="w-14 h-14 rounded-2xl flex items-center justify-center font-black text-navy-950 text-xl"
                      style={{ backgroundColor: simPrediction.posture_accuracy.tier_color }}
                    >
                      {simPrediction.posture_accuracy.overall_accuracy_pct >= 90 ? 'A+' : simPrediction.posture_accuracy.overall_accuracy_pct >= 75 ? 'B' : 'C'}
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <span className="text-xs font-black uppercase text-slate-400">Target Impact Forecast</span>
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
