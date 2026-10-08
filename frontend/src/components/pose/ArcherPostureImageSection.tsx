import React, { useState, useEffect, useRef } from 'react'
import {
  Camera, Upload, Sparkles, CheckCircle2, AlertTriangle,
  Crosshair, Award, ShieldCheck, RefreshCw, Download, User, Check, Zap
} from 'lucide-react'
import { poseApi } from '@/api/pose'
import type {
  PostureSampleItem,
  PostureImageAnalysisResponse,
  RangeLaneArcherItem
} from '@/types'
import { toast } from 'react-hot-toast'

interface ArcherPostureImageSectionProps {
  selectedLane: RangeLaneArcherItem | null
  lanes: RangeLaneArcherItem[]
  onSelectLane: (lane: RangeLaneArcherItem) => void
}

export default function ArcherPostureImageSection({
  selectedLane,
  lanes,
  onSelectLane
}: ArcherPostureImageSectionProps) {
  // ─── Input & Analysis State ───────────────────────────────────────────────
  const [samples, setSamples] = useState<PostureSampleItem[]>([])
  const [selectedSample, setSelectedSample] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<PostureImageAnalysisResponse | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false)
  const [activeSource, setActiveSource] = useState<'benchmarks' | 'upload' | 'camera'>('benchmarks')
  const [viewMode, setViewMode] = useState<'annotated' | 'raw' | 'split'>('annotated')
  const [customImageUri, setCustomImageUri] = useState<string | null>(null)

  // ─── Camera Snapshot State ────────────────────────────────────────────────
  const [isCameraActive, setIsCameraActive] = useState<boolean>(false)
  const [videoDevices, setVideoDevices] = useState<MediaDeviceInfo[]>([])
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('')
  const cameraVideoRef = useRef<HTMLVideoElement>(null)
  const cameraStreamRef = useRef<MediaStream | null>(null)
  const fileUploadInputRef = useRef<HTMLInputElement>(null)

  // ─── Mount: Load Benchmark Samples & Cameras ──────────────────────────────
  useEffect(() => {
    loadPostureSamples()
    enumerateCameras()

    return () => {
      stopCamera()
    }
  }, [])

  const enumerateCameras = async () => {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        // Quick permission prompt so labels (e.g. OBS Virtual Camera) become readable
        try {
          const tempStream = await navigator.mediaDevices.getUserMedia({ video: true })
          tempStream.getTracks().forEach((t) => t.stop())
        } catch {
          // Handled or already permitted
        }
        const devs = await navigator.mediaDevices.enumerateDevices()
        const videoInputs = devs.filter((d) => d.kind === 'videoinput')
        setVideoDevices(videoInputs)
        // Auto-select OBS Virtual Camera if present
        if (videoInputs.length > 0) {
          const obs = videoInputs.find(d => 
            d.label.toLowerCase().includes('obs') || d.label.toLowerCase().includes('virtual')
          )
          if (obs) {
            setSelectedDeviceId(obs.deviceId)
          } else if (!selectedDeviceId) {
            setSelectedDeviceId(videoInputs[0].deviceId)
          }
        }
      }
    } catch {
      // Browser permissions or device without camera
    }
  }

  const loadPostureSamples = async () => {
    try {
      const res = await poseApi.getPostureSamples()
      if (res.success && res.samples && res.samples.length > 0) {
        setSamples(res.samples)
        // Automatically analyze sample with great form e.g. images (9).jpg or first
        const initialSample = res.samples.find(s => s.filename.includes('(9)')) || res.samples[0]
        if (initialSample) {
          analyzeSample(initialSample.filename)
        }
      }
    } catch {
      toast.error('Failed to load posture sample gallery')
    }
  }

  // ─── Analyze Benchmark Sample ─────────────────────────────────────────────
  const analyzeSample = async (filename: string) => {
    try {
      setSelectedSample(filename)
      setCustomImageUri(null)
      setIsAnalyzing(true)
      const res = await poseApi.analyzePostureSample(filename, {
        lane_number: selectedLane?.lane_number,
        archer_id: selectedLane?.archer.id,
        archer_name: selectedLane?.archer.name
      })
      setAnalysis(res)
      toast.success(`Form evaluated: Score ${res.prediction.score_display} (${res.posture_accuracy.overall_accuracy_pct}%)`)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Posture analysis failed')
    } finally {
      setIsAnalyzing(false)
    }
  }

  // ─── Handle Upload ────────────────────────────────────────────────────────
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      setIsAnalyzing(true)
      setSelectedSample(file.name)
      const reader = new FileReader()
      reader.onload = (ev) => {
        setCustomImageUri(ev.target?.result as string)
      }
      reader.readAsDataURL(file)

      const formData = new FormData()
      formData.append('file', file)
      if (selectedLane) {
        formData.append('lane_number', String(selectedLane.lane_number))
        formData.append('archer_id', String(selectedLane.archer.id))
        formData.append('archer_name', selectedLane.archer.name)
        formData.append('camera_source', selectedLane.camera.name)
      }

      const res = await poseApi.analyzeUploadedImage(formData)
      setAnalysis(res)
      toast.success(`Uploaded & analyzed: Predicted Score ${res.prediction.score_display}`)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Image posture analysis failed')
    } finally {
      setIsAnalyzing(false)
    }
  }

  // ─── Live Camera Control & Snapshot ───────────────────────────────────────
  const startCamera = async (overrideDeviceId?: string) => {
    const devId = overrideDeviceId || selectedDeviceId
    try {
      const constraints: MediaStreamConstraints = {
        video: devId
          ? { deviceId: { exact: devId }, width: { ideal: 1280 }, height: { ideal: 720 } }
          : { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false
      }
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      cameraStreamRef.current = stream
      if (cameraVideoRef.current) {
        cameraVideoRef.current.srcObject = stream
        cameraVideoRef.current.play()
      }
      setIsCameraActive(true)
      const dev = videoDevices.find(d => d.deviceId === devId)
      toast.success(dev?.label ? `Connected: ${dev.label}` : 'Camera stream connected')
    } catch {
      toast.error('Unable to access camera. Check device permissions.')
    }
  }

  const stopCamera = () => {
    if (cameraStreamRef.current) {
      cameraStreamRef.current.getTracks().forEach((track) => track.stop())
      cameraStreamRef.current = null
    }
    setIsCameraActive(false)
  }

  const handleDeviceChange = async (newDeviceId: string) => {
    setSelectedDeviceId(newDeviceId)
    if (isCameraActive) {
      stopCamera()
      setTimeout(() => {
        startCamera(newDeviceId)
      }, 150)
    }
  }

  const analyzeAssignedLaneCamera = async () => {
    const laneNum = selectedLane?.lane_number || 1
    try {
      setIsAnalyzing(true)
      setSelectedSample(`lane_${laneNum}_assigned_camera.jpg`)
      const res = await poseApi.analyzeLaneCamera(laneNum)
      setAnalysis(res)
      if (res.annotated_image_base64) {
        setCustomImageUri(`data:image/jpeg;base64,${res.annotated_image_base64}`)
      }
      toast.success(`Lane ${laneNum} Camera Evaluated: Score ${res.prediction.score_display} (${res.posture_accuracy.overall_accuracy_pct}%)`)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to analyze assigned lane camera')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const captureCameraSnapshot = async () => {
    const video = cameraVideoRef.current
    if (!video || video.videoWidth === 0) {
      toast.error('Camera stream is not active')
      return
    }

    try {
      setIsAnalyzing(true)
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.drawImage(video, 0, 0)
      const base64Data = canvas.toDataURL('image/jpeg', 0.92)
      setCustomImageUri(base64Data)
      setSelectedSample(`lane_${selectedLane?.lane_number || 1}_cam_frame.jpg`)

      const res = await poseApi.analyzeCameraSnapshot({
        image_base64: base64Data,
        filename: `snapshot_lane_${selectedLane?.lane_number || 1}_${Date.now()}.jpg`,
        lane_number: selectedLane?.lane_number,
        archer_id: selectedLane?.archer.id,
        archer_name: selectedLane?.archer.name,
        camera_source: selectedLane?.camera.name || 'Assigned Lane Camera'
      })

      setAnalysis(res)
      toast.success(`Live Snapshot analyzed: ${res.prediction.score_display} (${res.posture_accuracy.overall_accuracy_pct}%)`)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to analyze camera snapshot')
    } finally {
      setIsAnalyzing(false)
    }
  }

  // ─── Save Posture Record ──────────────────────────────────────────────────
  const handleSaveRecord = async () => {
    if (!analysis || !selectedLane) {
      toast.error('Select an archer lane first')
      return
    }
    try {
      await poseApi.recordArcherPosture({
        archer_id: selectedLane.archer.id,
        archer_name: selectedLane.archer.name,
        lane_number: selectedLane.lane_number,
        camera_source: selectedLane.camera.name,
        overall_accuracy_pct: analysis.posture_accuracy.overall_accuracy_pct,
        accuracy_tier: analysis.posture_accuracy.accuracy_tier,
        predicted_score: analysis.prediction.predicted_score,
        bow_arm_angle: analysis.biomechanics.bow_arm_angle,
        draw_elbow_angle: analysis.biomechanics.draw_elbow_angle,
        notes: `Photo evaluation: ${analysis.prediction.score_display} (${analysis.prediction.score_category})`
      })
      toast.success(`Evaluation recorded for ${selectedLane.archer.name}!`)
    } catch {
      toast.error('Failed to save posture record')
    }
  }

  // ─── Ring Category Colors ─────────────────────────────────────────────────
  const getRingColorStyle = (category: string) => {
    switch (category?.toLowerCase()) {
      case 'gold':
      case 'gold / bullseye':
        return {
          bg: 'from-amber-500/20 via-yellow-500/10 to-transparent',
          border: 'border-yellow-400/40',
          text: 'text-yellow-400',
          badge: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40',
          ringBg: '#fbbf24'
        }
      case 'red':
        return {
          bg: 'from-rose-500/20 via-red-500/10 to-transparent',
          border: 'border-rose-400/40',
          text: 'text-rose-400',
          badge: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
          ringBg: '#ef4444'
        }
      case 'blue':
        return {
          bg: 'from-blue-500/20 via-cyan-500/10 to-transparent',
          border: 'border-blue-400/40',
          text: 'text-blue-400',
          badge: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
          ringBg: '#3b82f6'
        }
      case 'black':
        return {
          bg: 'from-slate-700/30 via-slate-800/10 to-transparent',
          border: 'border-slate-500/40',
          text: 'text-slate-300',
          badge: 'bg-slate-700/40 text-slate-200 border-slate-600',
          ringBg: '#334155'
        }
      default:
        return {
          bg: 'from-slate-500/10 via-slate-600/5 to-transparent',
          border: 'border-slate-400/30',
          text: 'text-slate-100',
          badge: 'bg-slate-200/20 text-slate-100 border-slate-300',
          ringBg: '#e2e8f0'
        }
    }
  }

  const ringStyle = getRingColorStyle(analysis?.prediction?.score_category || 'Gold')

  return (
    <div className="space-y-6">
      {/* ─── Top Control Bar: Lane & Camera Context ───────────────────────── */}
      <div className="bg-navy-900 border border-navy-700 rounded-2xl p-4 shadow-xl">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          {/* Lane Selector */}
          <div className="flex items-center gap-3 overflow-x-auto w-full lg:w-auto pb-1 lg:pb-0">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider whitespace-nowrap flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-gold-400" /> Assigned Archer:
            </span>
            <div className="flex items-center gap-2">
              {lanes.map((lane) => (
                <button
                  key={lane.lane_number}
                  onClick={() => onSelectLane(lane)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap flex items-center gap-2 ${
                    selectedLane?.lane_number === lane.lane_number
                      ? 'bg-gold-500 text-navy-950 shadow-md shadow-gold-500/20'
                      : 'bg-navy-950 text-slate-300 hover:bg-navy-800 border border-navy-800'
                  }`}
                >
                  <span className="w-4 h-4 rounded-full bg-navy-900/30 flex items-center justify-center text-[10px]">
                    0{lane.lane_number}
                  </span>
                  {lane.archer.name}
                </button>
              ))}
            </div>
          </div>

          {/* Input Source Modes */}
          <div className="flex items-center bg-navy-950 p-1 rounded-xl border border-navy-800 self-stretch lg:self-auto justify-center">
            <button
              onClick={() => setActiveSource('benchmarks')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeSource === 'benchmarks'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" /> 14 Benchmark Photos
            </button>
            <button
              onClick={() => setActiveSource('upload')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeSource === 'upload'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Upload className="w-3.5 h-3.5" /> Upload Photo
            </button>
            <button
              onClick={() => setActiveSource('camera')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeSource === 'camera'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Camera className="w-3.5 h-3.5" /> Lane Camera Snapshot
            </button>
          </div>
        </div>
      </div>

      {/* ─── Source 1: Benchmark Posture Gallery (14 Images) ───────────────── */}
      {activeSource === 'benchmarks' && (
        <div className="bg-navy-900 border border-navy-700 rounded-2xl p-5 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-gold-400" />
              <h2 className="text-sm font-black text-slate-100 uppercase tracking-wider">
                Tournament Archer Posture Benchmarks ({samples.length} Photos)
              </h2>
            </div>
            <span className="text-xs text-slate-400">
              Click any photo to instantly identify MediaPipe skeleton landmarks, form angles & predicted score
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2.5">
            {samples.map((s, idx) => {
              const isSelected = selectedSample === s.filename
              const imgUrl = poseApi.getPostureSampleUrl(s.filename)
              return (
                <div
                  key={s.filename}
                  onClick={() => analyzeSample(s.filename)}
                  className={`group relative rounded-xl overflow-hidden border cursor-pointer transition-all aspect-[4/3] bg-navy-950 ${
                    isSelected
                      ? 'border-gold-400 ring-2 ring-gold-400/30 scale-[1.03] shadow-lg shadow-gold-500/10'
                      : 'border-navy-800 hover:border-navy-600 hover:scale-[1.01]'
                  }`}
                >
                  <img
                    src={imgUrl}
                    alt={s.filename}
                    className="w-full h-full object-cover transition-transform group-hover:scale-105"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-navy-950/90 via-navy-950/20 to-transparent flex flex-col justify-end p-2">
                    <span className="text-[10px] font-bold text-slate-200 truncate">
                      Sample #{idx + 1}
                    </span>
                    <span className="text-[9px] text-slate-400 truncate">
                      {s.filename}
                    </span>
                  </div>
                  {isSelected && (
                    <div className="absolute top-1.5 right-1.5 bg-gold-500 text-navy-950 p-1 rounded-full shadow-md">
                      <Check className="w-3 h-3 stroke-[3]" />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ─── Source 2: Upload Photo ───────────────────────────────────────── */}
      {activeSource === 'upload' && (
        <div className="bg-navy-900 border border-navy-700 rounded-2xl p-6 shadow-xl">
          <div
            onClick={() => fileUploadInputRef.current?.click()}
            className="border-2 border-dashed border-navy-600 hover:border-gold-400/60 rounded-2xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all bg-navy-950/50 hover:bg-navy-950/80 group"
          >
            <div className="w-16 h-16 rounded-2xl bg-navy-800 group-hover:bg-gold-500/10 border border-navy-700 group-hover:border-gold-500/30 flex items-center justify-center mb-3 transition-all">
              <Upload className="w-8 h-8 text-slate-400 group-hover:text-gold-400 transition-colors" />
            </div>
            <h3 className="text-base font-bold text-slate-200">
              Drag & Drop Archer Posture Photo
            </h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm">
              Supports JPEG, PNG, WebP up to 15MB. Best results when full upper body, arms, and bow are clearly visible.
            </p>
            <button className="mt-4 px-4 py-2 rounded-xl text-xs font-bold bg-gold-500 hover:bg-gold-400 text-navy-950 transition-all shadow-md">
              Browse Image File
            </button>
            <input
              ref={fileUploadInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileUpload}
            />
          </div>
        </div>
      )}

      {/* ─── Source 3: Assigned Lane Camera Snapshot ──────────────────────── */}
      {activeSource === 'camera' && (
        <div className="bg-navy-900 border border-navy-700 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-black text-slate-100 uppercase tracking-wider flex items-center gap-2">
                <Camera className="w-4 h-4 text-emerald-400" />
                Live Camera Feed (Lane {selectedLane?.lane_number || 1}: {selectedLane?.camera.name || 'Archer Cam'})
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Stream real-time video and grab high-resolution snapshots directly from the assigned shooter camera
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                value={selectedDeviceId}
                onChange={(e) => handleDeviceChange(e.target.value)}
                className="bg-navy-950 border border-gold-500/40 rounded-xl px-3 py-2 text-xs font-semibold text-slate-100 focus:outline-none focus:border-gold-400 max-w-[260px] truncate"
              >
                {videoDevices.map((d, i) => {
                  const isObs = d.label.toLowerCase().includes('obs') || d.label.toLowerCase().includes('virtual')
                  return (
                    <option key={d.deviceId || i} value={d.deviceId}>
                      {isObs ? '🎥 [OBS Virtual Camera] ' : '📹 '} {d.label || `Camera ${i + 1}`}
                    </option>
                  )
                })}
                {videoDevices.length === 0 && (
                  <option value="">🎥 OBS Virtual Camera (Auto-Detect)</option>
                )}
              </select>

              <button
                onClick={isCameraActive ? stopCamera : () => startCamera()}
                className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all shadow-md flex items-center gap-1.5 ${
                  isCameraActive
                    ? 'bg-rose-600 hover:bg-rose-500 text-white'
                    : 'bg-emerald-600 hover:bg-emerald-500 text-white'
                }`}
              >
                <Camera className="w-3.5 h-3.5" />
                {isCameraActive ? 'Disconnect' : 'Connect Camera'}
              </button>

              <button
                onClick={analyzeAssignedLaneCamera}
                disabled={isAnalyzing}
                className="px-3.5 py-2 rounded-xl text-xs font-bold bg-navy-800 hover:bg-navy-700 border border-gold-500/40 text-gold-300 transition-all flex items-center gap-1.5 shadow-md hover:scale-[1.02]"
                title="Fetch and evaluate the live camera frame assigned to this lane in the Camera section"
              >
                <Zap className="w-3.5 h-3.5 text-gold-400" />
                Analyze Lane {selectedLane?.lane_number || 1} Feed
              </button>
            </div>
          </div>

          <div className="relative aspect-video max-h-[460px] bg-black rounded-2xl overflow-hidden flex items-center justify-center border border-navy-800">
            {isCameraActive ? (
              <video
                ref={cameraVideoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-center p-8 space-y-3">
                <Camera className="w-12 h-12 text-slate-600 mx-auto" />
                <span className="text-sm font-bold text-slate-400 block">
                  Camera stream offline
                </span>
                <button
                  onClick={() => startCamera()}
                  className="px-4 py-2 bg-navy-800 hover:bg-navy-700 border border-navy-700 rounded-xl text-xs font-bold text-slate-200"
                >
                  Start Camera Feed
                </button>
              </div>
            )}

            {isCameraActive && (
              <div className="absolute bottom-4 inset-x-0 flex justify-center z-20">
                <button
                  onClick={captureCameraSnapshot}
                  disabled={isAnalyzing}
                  className="px-6 py-3 bg-gradient-to-r from-gold-500 to-amber-500 hover:from-gold-400 hover:to-amber-400 text-navy-950 font-black text-sm rounded-2xl shadow-2xl flex items-center gap-2 transition-transform active:scale-95 disabled:opacity-50"
                >
                  <Camera className="w-5 h-5" />
                  Capture Snapshot & Predict Form
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── Loading State ─────────────────────────────────────────────────── */}
      {isAnalyzing && (
        <div className="bg-navy-900/80 border border-gold-500/30 rounded-2xl p-8 text-center space-y-3 shadow-xl backdrop-blur-sm animate-pulse">
          <RefreshCw className="w-8 h-8 text-gold-400 animate-spin mx-auto" />
          <h3 className="text-base font-black text-slate-100">
            Extracting 33-Point MediaPipe Skeletal Biometrics...
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Computing bow arm skeletal alignment, draw elbow elevation line, handedness, and machine learning target score prediction.
          </p>
        </div>
      )}

      {/* ─── Main Analysis Dashboard ───────────────────────────────────────── */}
      {analysis && !isAnalyzing && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Visual Skeleton & Comparison (7 Cols) */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-navy-900 border border-navy-700 rounded-2xl overflow-hidden shadow-2xl">
              {/* Image Viewer Header */}
              <div className="px-4 py-3 bg-navy-950 border-b border-navy-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs font-bold text-slate-200">
                    {analysis.filename}
                  </span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
                    {analysis.handedness_label}
                  </span>
                </div>

                {/* View Mode Switcher */}
                <div className="flex bg-navy-900 p-0.5 rounded-lg border border-navy-700 text-[11px] font-bold">
                  <button
                    onClick={() => setViewMode('annotated')}
                    className={`px-2.5 py-1 rounded-md transition-all ${
                      viewMode === 'annotated'
                        ? 'bg-gold-500 text-navy-950'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    AI Skeleton
                  </button>
                  <button
                    onClick={() => setViewMode('raw')}
                    className={`px-2.5 py-1 rounded-md transition-all ${
                      viewMode === 'raw'
                        ? 'bg-gold-500 text-navy-950'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Original
                  </button>
                  <button
                    onClick={() => setViewMode('split')}
                    className={`px-2.5 py-1 rounded-md transition-all ${
                      viewMode === 'split'
                        ? 'bg-gold-500 text-navy-950'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Side-by-Side
                  </button>
                </div>
              </div>

              {/* Image Display Area */}
              <div className="p-3 bg-black flex items-center justify-center min-h-[380px]">
                {viewMode === 'annotated' && (
                  <img
                    src={analysis.annotated_image_base64}
                    alt="Annotated Pose"
                    className="max-h-[520px] w-auto object-contain rounded-lg shadow-lg"
                  />
                )}

                {viewMode === 'raw' && (
                  <img
                    src={
                      customImageUri ||
                      (selectedSample ? poseApi.getPostureSampleUrl(selectedSample) : analysis.annotated_image_base64)
                    }
                    alt="Original Form"
                    className="max-h-[520px] w-auto object-contain rounded-lg shadow-lg"
                  />
                )}

                {viewMode === 'split' && (
                  <div className="grid grid-cols-2 gap-2 w-full">
                    <div className="relative">
                      <img
                        src={
                          customImageUri ||
                          (selectedSample ? poseApi.getPostureSampleUrl(selectedSample) : analysis.annotated_image_base64)
                        }
                        alt="Raw"
                        className="w-full h-auto object-contain rounded-lg"
                      />
                      <span className="absolute top-2 left-2 bg-navy-950/80 text-white text-[10px] font-bold px-2 py-0.5 rounded border border-navy-700">
                        Raw Photo
                      </span>
                    </div>
                    <div className="relative">
                      <img
                        src={analysis.annotated_image_base64}
                        alt="AI Annotated"
                        className="w-full h-auto object-contain rounded-lg"
                      />
                      <span className="absolute top-2 left-2 bg-navy-950/80 text-gold-400 text-[10px] font-bold px-2 py-0.5 rounded border border-gold-500/30">
                        MediaPipe Skeletal
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Image Info Footer */}
              <div className="px-4 py-2.5 bg-navy-950 border-t border-navy-800 flex items-center justify-between text-[11px] text-slate-400 font-semibold">
                <span>
                  Resolution: {analysis.resolution.width} × {analysis.resolution.height} px
                </span>
                <span>
                  33 Full-Body Anatomical Landmarks Detected
                </span>
                <a
                  href={analysis.annotated_image_base64}
                  download={`pose_analysis_${analysis.filename}`}
                  className="flex items-center gap-1 text-gold-400 hover:text-gold-300 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" /> Save Annotated Image
                </a>
              </div>
            </div>

            {/* 4 Biomechanical Angle Telemetry Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {/* Bow Arm Angle */}
              <div className="bg-navy-900 border border-navy-700 rounded-xl p-3 space-y-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Bow Arm Angle
                </span>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-xl font-black text-slate-100">
                    {analysis.biomechanics.bow_arm_angle}°
                  </span>
                  <span
                    className={`text-[9px] font-black px-1.5 py-0.5 rounded ${
                      analysis.biomechanics.bow_arm_status === 'OPTIMAL'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : analysis.biomechanics.bow_arm_status === 'ACCEPTABLE'
                        ? 'bg-amber-500/20 text-amber-400'
                        : 'bg-rose-500/20 text-rose-400'
                    }`}
                  >
                    {analysis.biomechanics.bow_arm_status}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 block">
                  Ideal: {analysis.biomechanics.bow_arm_ideal_range}
                </span>
              </div>

              {/* Draw Elbow Angle */}
              <div className="bg-navy-900 border border-navy-700 rounded-xl p-3 space-y-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Draw Elbow Pull
                </span>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-xl font-black text-slate-100">
                    {analysis.biomechanics.draw_elbow_angle}°
                  </span>
                  <span
                    className={`text-[9px] font-black px-1.5 py-0.5 rounded ${
                      analysis.biomechanics.draw_elbow_status === 'OPTIMAL'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'bg-amber-500/20 text-amber-400'
                    }`}
                  >
                    {analysis.biomechanics.draw_elbow_status}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 block">
                  Ideal: {analysis.biomechanics.draw_elbow_ideal_range}
                </span>
              </div>

              {/* Torso Tilt */}
              <div className="bg-navy-900 border border-navy-700 rounded-xl p-3 space-y-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Torso Verticality
                </span>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-xl font-black text-slate-100">
                    {analysis.biomechanics.torso_tilt_deg}°
                  </span>
                  <span className="text-[9px] font-black px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                    {Math.abs(90.0 - analysis.biomechanics.torso_tilt_deg) <= 3.0 ? 'VERTICAL' : 'INCLINED'}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 block">
                  Ideal: {analysis.biomechanics.torso_ideal_range}
                </span>
              </div>

              {/* Shoulder Tilt */}
              <div className="bg-navy-900 border border-navy-700 rounded-xl p-3 space-y-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Shoulder Balance
                </span>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-xl font-black text-slate-100">
                    {analysis.biomechanics.shoulder_tilt_deg}°
                  </span>
                  <span className="text-[9px] font-black px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">
                    LEVEL
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 block">
                  Ideal: 0.0° - 5.0°
                </span>
              </div>
            </div>

            {/* Coaching Feedback & Diagnostics */}
            <div className="bg-navy-900 border border-navy-700 rounded-2xl p-5 shadow-xl space-y-3">
              <h3 className="text-xs font-black text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <Award className="w-4 h-4 text-gold-400" />
                Form Diagnostics & Coach Feedback
              </h3>
              <div className="space-y-2">
                {analysis.diagnostics && analysis.diagnostics.length > 0 ? (
                  analysis.diagnostics.map((diag, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-xl border flex items-start gap-3 text-xs ${
                        diag.severity === 'OPTIMAL'
                          ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-200'
                          : diag.severity === 'WARNING'
                          ? 'bg-amber-950/30 border-amber-500/30 text-amber-200'
                          : 'bg-rose-950/30 border-rose-500/30 text-rose-200'
                      }`}
                    >
                      {diag.severity === 'OPTIMAL' ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      )}
                      <div>
                        <span className="font-bold block">{diag.rule_id || 'Form Telemetry'}</span>
                        <p className="text-slate-300 mt-0.5">{diag.message}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-3 bg-navy-950 rounded-xl border border-navy-800 text-xs text-slate-400">
                    Form biomechanics meet standard shooting criteria.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Prediction, Olympic Radar, Accuracy Gauge (5 Cols) */}
          <div className="lg:col-span-5 space-y-4">
            {/* Predicted Target Score Banner */}
            <div
              className={`bg-gradient-to-br ${ringStyle.bg} bg-navy-900 border ${ringStyle.border} rounded-2xl p-6 shadow-2xl relative overflow-hidden`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                    Predicted Olympic Score
                  </span>
                  <div className="flex items-baseline gap-3 mt-1">
                    <span className={`text-5xl font-black ${ringStyle.text} tracking-tight`}>
                      {analysis.prediction.score_display}
                    </span>
                    <span className="text-sm font-bold text-slate-400">
                      / 10 Ring
                    </span>
                  </div>
                  <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-black uppercase mt-2 border ${ringStyle.badge}`}>
                    {analysis.prediction.score_category} Zone
                  </span>
                </div>

                {/* Score execution rating badge */}
                <div className="text-right">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Execution Score
                  </span>
                  <span className="text-2xl font-black text-slate-100 block">
                    {analysis.prediction.execution_score_pct}%
                  </span>
                  <span className="text-[10px] text-emerald-400 font-bold block mt-0.5">
                    Confidence: {(analysis.prediction.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-300 mt-3 border-t border-navy-800/80 pt-2">
                {analysis.prediction.zone_description}
              </p>
            </div>

            {/* Olympic Target Face Concentric Radar */}
            <div className="bg-navy-900 border border-navy-700 rounded-2xl p-5 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                  <Crosshair className="w-4 h-4 text-gold-400" />
                  Target Face Radar Simulation
                </span>
                <span className="text-[10px] font-bold text-slate-400">
                  Projected Arrow Impact
                </span>
              </div>

              <div className="relative aspect-square max-w-[240px] mx-auto bg-slate-900 rounded-full border border-navy-700 p-1 flex items-center justify-center shadow-inner">
                {/* 1-2 White Ring */}
                <div className="w-full h-full rounded-full bg-slate-100 flex items-center justify-center border border-slate-300 shadow-md">
                  {/* 3-4 Black Ring */}
                  <div className="w-[80%] h-[80%] rounded-full bg-slate-900 flex items-center justify-center border border-slate-700">
                    {/* 5-6 Blue Ring */}
                    <div className="w-[75%] h-[75%] rounded-full bg-blue-600 flex items-center justify-center border border-blue-400">
                      {/* 7-8 Red Ring */}
                      <div className="w-[66%] h-[66%] rounded-full bg-red-600 flex items-center justify-center border border-red-400">
                        {/* 9-10 Gold Ring */}
                        <div className="w-[50%] h-[50%] rounded-full bg-yellow-400 flex items-center justify-center border border-yellow-300 shadow-inner">
                          {/* Inner 10-X Ring */}
                          <div className="w-4 h-4 rounded-full bg-yellow-500 border border-yellow-700" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Projected Impact Marker with animated ping */}
                <div
                  className="absolute w-5 h-5 -translate-x-1/2 -translate-y-1/2 pointer-events-none transition-all duration-500 z-10"
                  style={{
                    left: `${50 + (analysis.prediction.target_coordinates?.x || 0) * 80}%`,
                    top: `${50 + (analysis.prediction.target_coordinates?.y || 0) * 80}%`
                  }}
                >
                  <div className="w-full h-full rounded-full bg-rose-500 border-2 border-white shadow-xl animate-ping absolute inset-0 opacity-75" />
                  <div className="w-full h-full rounded-full bg-rose-600 border-2 border-white shadow-xl flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-white" />
                  </div>
                </div>
              </div>

              <div className="text-center pt-1">
                <span className="text-xs font-black text-slate-200 block">
                  Ring Impact: {analysis.prediction.score_display} ({analysis.prediction.score_category})
                </span>
                <span className="text-[10px] text-slate-400 block">
                  Target Coords: X: {analysis.prediction.target_coordinates?.x || 0}, Y: {analysis.prediction.target_coordinates?.y || 0}
                </span>
              </div>
            </div>

            {/* Posture Accuracy Gauge & Breakdown */}
            <div className="bg-navy-900 border border-navy-700 rounded-2xl p-5 shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  Posture Accuracy Gauge
                </span>
                <span
                  className="text-[10px] font-black px-2 py-0.5 rounded-full uppercase"
                  style={{
                    backgroundColor: `${analysis.posture_accuracy.tier_color}25`,
                    color: analysis.posture_accuracy.tier_color
                  }}
                >
                  {analysis.posture_accuracy.accuracy_tier}
                </span>
              </div>

              {/* Big Accuracy Percentage */}
              <div className="flex items-baseline justify-between border-b border-navy-800 pb-3">
                <span className="text-3xl font-black text-slate-100">
                  {analysis.posture_accuracy.overall_accuracy_pct}%
                </span>
                <span className="text-xs font-bold text-slate-400">
                  {analysis.posture_accuracy.accuracy_label}
                </span>
              </div>

              {/* Breakdown Bars */}
              <div className="space-y-3 pt-1">
                {/* Bow Arm Alignment */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="font-semibold text-slate-300">Bow Arm Extension Alignment</span>
                    <span className="font-bold text-gold-400">
                      {analysis.posture_accuracy.components.bow_arm_accuracy_pct}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-navy-950 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-gold-500 to-amber-400 rounded-full transition-all duration-500"
                      style={{ width: `${analysis.posture_accuracy.components.bow_arm_accuracy_pct}%` }}
                    />
                  </div>
                </div>

                {/* Draw Elbow Pull Line */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="font-semibold text-slate-300">Draw Elbow Pull Alignment</span>
                    <span className="font-bold text-blue-400">
                      {analysis.posture_accuracy.components.draw_elbow_accuracy_pct}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-navy-950 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full transition-all duration-500"
                      style={{ width: `${analysis.posture_accuracy.components.draw_elbow_accuracy_pct}%` }}
                    />
                  </div>
                </div>

                {/* Anchor Stability */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="font-semibold text-slate-300">Anchor Hold Stability</span>
                    <span className="font-bold text-emerald-400">
                      {analysis.posture_accuracy.components.anchor_stability_accuracy_pct}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-navy-950 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all duration-500"
                      style={{ width: `${analysis.posture_accuracy.components.anchor_stability_accuracy_pct}%` }}
                    />
                  </div>
                </div>

                {/* Torso & Balance */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="font-semibold text-slate-300">Torso & Release Balance</span>
                    <span className="font-bold text-purple-400">
                      {analysis.posture_accuracy.components.release_follow_through_accuracy_pct}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-navy-950 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-purple-500 to-pink-400 rounded-full transition-all duration-500"
                      style={{ width: `${analysis.posture_accuracy.components.release_follow_through_accuracy_pct}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Save Record Action */}
              <button
                onClick={handleSaveRecord}
                className="w-full mt-4 py-2.5 bg-navy-950 hover:bg-navy-800 border border-gold-500/40 hover:border-gold-500 text-gold-300 hover:text-gold-200 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-2 shadow-md active:scale-95"
              >
                <Award className="w-4 h-4 text-gold-400" />
                Record Evaluation to {selectedLane?.archer.name || 'Archer Profile'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
