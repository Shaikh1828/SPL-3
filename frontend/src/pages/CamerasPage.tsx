import { useState, useEffect, useRef } from 'react'
import {
  Camera as CameraIcon, Plus, RefreshCw, Trash2, X, ShieldAlert,
  Radio, CheckCircle2, AlertCircle, Video, Sparkles, Loader2,
  Settings2, Target, Zap, HelpCircle, Play, Square, GripVertical,
  Layers, ArrowLeftRight
} from 'lucide-react'
import { useCameraStore } from '@/store/cameraStore'
import { camerasApi } from '@/api/cameras'
import { useSessionStore } from '@/store/sessionStore'
import { useAuthStore } from '@/store/authStore'
import { useCameraPreview } from '@/hooks/useCameraPreview'
import { useCameraStream } from '@/context/CameraStreamContext'
import toast from 'react-hot-toast'
import { cn } from '@/lib/utils'
import type { Camera as CameraType, CameraDiscoveryItem, CameraTestResponse } from '@/types'

// ─── Live Camera Card Component with Drag & Drop ──────────────────────────────
function LiveCameraCard({
  camera,
  numLanes,
  canManage,
  browserStream,
  isBridgeActiveForLane,
  isDragging,
  isDragOver,
  onDragStart,
  onDragOver,
  onDragLeave,
  onDrop,
  onEdit,
  onUnassign,
  onReconnect,
  onLaneChange,
}: {
  camera: CameraType
  numLanes: number
  canManage: boolean
  browserStream: MediaStream | null
  isBridgeActiveForLane: boolean
  isDragging: boolean
  isDragOver: boolean
  onDragStart: (e: React.DragEvent, cam: CameraType) => void
  onDragOver: (e: React.DragEvent, cam: CameraType) => void
  onDragLeave: (e: React.DragEvent) => void
  onDrop: (e: React.DragEvent, targetCam: CameraType) => void
  onEdit: (camera: CameraType) => void
  onUnassign: (id: number) => void
  onReconnect: (id: number) => void
  onLaneChange: (cameraId: number, newLane: number) => void
}) {
  const imgRef = useRef<HTMLImageElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  useCameraPreview(camera.id, imgRef)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<CameraTestResponse | null>(null)

  // Attach direct browser MediaStream if host bridge is active for this lane
  useEffect(() => {
    if (isBridgeActiveForLane && browserStream && videoRef.current) {
      videoRef.current.srcObject = browserStream
    }
  }, [isBridgeActiveForLane, browserStream])

  const handleTestFeed = async () => {
    setTesting(true)
    try {
      const res = await camerasApi.testCamera(camera.id)
      setTestResult(res)
      if (res.connected) {
        toast.success(`Stream Active! Res: ${res.resolution || 'HD'} @ ${res.fps || 30} FPS`)
      } else {
        toast.error(res.message || 'Stream connection failed')
      }
    } catch {
      toast.error('Failed to probe camera stream')
    } finally {
      setTesting(false)
    }
  }

  return (
    <div
      draggable={canManage}
      onDragStart={(e) => onDragStart(e, camera)}
      onDragOver={(e) => onDragOver(e, camera)}
      onDragLeave={onDragLeave}
      onDrop={(e) => onDrop(e, camera)}
      className={cn(
        'glass-card flex flex-col overflow-hidden border shadow-xl group transition-all rounded-2xl relative select-none',
        isDragging && 'opacity-40 scale-95 border-gold-400 border-dashed',
        isDragOver && 'ring-2 ring-gold-400 scale-[1.02] border-gold-400 bg-gold-500/10 shadow-gold-500/20',
        !isDragging && !isDragOver && 'border-navy-700/80 hover:border-gold-500/50'
      )}
    >
      {/* Drag Indicator Tooltip on DragOver */}
      {isDragOver && (
        <div className="absolute inset-0 bg-gold-500/10 backdrop-blur-[2px] z-30 flex items-center justify-center pointer-events-none">
          <div className="bg-navy-950/90 border border-gold-400 text-gold-300 px-3 py-1.5 rounded-xl font-bold text-xs flex items-center gap-1.5 shadow-2xl animate-bounce">
            <ArrowLeftRight className="w-4 h-4 text-gold-400" />
            Drop to Swap with Lane {camera.lane || '?'}
          </div>
        </div>
      )}

      {/* Live Video Preview Screen */}
      <div className="bg-navy-950 aspect-video relative border-b border-navy-800 flex items-center justify-center overflow-hidden">
        {isBridgeActiveForLane && browserStream ? (
          <>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-contain bg-black"
            />
            {/* Target reticle overlay */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-30 group-hover:opacity-50 transition-opacity">
              <div className="w-36 h-36 border-2 border-dashed border-emerald-400 rounded-full" />
              <div className="w-2 h-2 bg-emerald-400 rounded-full absolute" />
            </div>
            <div className="absolute bottom-2 left-2 bg-emerald-950/90 text-emerald-300 border border-emerald-500/40 text-[9px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 shadow">
              <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping" />
              DIRECT OBS STREAM
            </div>
          </>
        ) : camera.status === 'connected' ? (
          <>
            <img
              ref={imgRef}
              className="w-full h-full object-contain bg-black"
              alt={camera.name}
            />
            {/* Target reticle overlay */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-25 group-hover:opacity-40 transition-opacity">
              <div className="w-36 h-36 border border-dashed border-gold-500 rounded-full" />
              <div className="w-1.5 h-1.5 bg-gold-400 rounded-full absolute" />
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 p-4 text-center">
            <CameraIcon className="w-10 h-10 mb-2 opacity-30 text-slate-400" />
            <p className="text-xs font-semibold text-slate-400">Stream Offline</p>
            <p className="text-[10px] text-slate-600 mt-0.5">Click Configure to select OBS Virtual Camera or Stream URL</p>
          </div>
        )}

        {/* Lane Assignment Badge (Top Right) */}
        <div className="absolute top-2 right-2 flex items-center gap-1.5 z-10">
          {camera.lane ? (
            <span className="px-2.5 py-1 text-xs font-black rounded-lg border backdrop-blur-md flex items-center gap-1.5 shadow-lg bg-gold-500/20 text-gold-300 border-gold-500/40">
              <Target className="w-3.5 h-3.5 text-gold-400" />
              LANE {camera.lane}
            </span>
          ) : (
            <span className="px-2 py-0.5 text-[10px] font-semibold rounded-md border backdrop-blur-md bg-slate-800/80 text-slate-400 border-slate-700">
              Unassigned
            </span>
          )}

          {/* Status Dot */}
          <span
            className={cn(
              'px-2 py-0.5 text-[10px] font-bold rounded-full border backdrop-blur-md flex items-center gap-1 shadow-md',
              isBridgeActiveForLane || camera.status === 'connected'
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                : camera.status === 'error'
                ? 'bg-red-500/20 text-red-300 border-red-500/40'
                : 'bg-slate-700/40 text-slate-300 border-slate-600/40'
            )}
          >
            <span
              className={cn(
                'w-1.5 h-1.5 rounded-full',
                isBridgeActiveForLane || camera.status === 'connected'
                  ? 'bg-emerald-400 animate-pulse'
                  : 'bg-slate-400'
              )}
            />
            {isBridgeActiveForLane ? 'LIVE (OBS)' : camera.status.toUpperCase()}
          </span>
        </div>

        {/* Source Protocol Badge (Top Left) */}
        <div className="absolute top-2 left-2 flex items-center gap-1 z-10">
          <span className="bg-navy-950/90 text-slate-300 border border-navy-700 text-[10px] font-mono px-2 py-0.5 rounded backdrop-blur-sm">
            {camera.camera_type}
          </span>
          <span className="bg-navy-950/90 text-gold-400 border border-navy-700 text-[10px] font-mono px-1.5 py-0.5 rounded backdrop-blur-sm">
            #{camera.id}
          </span>
        </div>
      </div>

      {/* Info & Action Toolbar */}
      <div className="p-4 flex-1 flex flex-col justify-between space-y-3 bg-navy-900/60">
        <div>
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 min-w-0">
              {canManage && (
                <div
                  className="cursor-grab active:cursor-grabbing text-slate-500 hover:text-gold-400 p-0.5 rounded"
                  title="Drag to swap or re-arrange lanes"
                >
                  <GripVertical className="w-4 h-4 shrink-0" />
                </div>
              )}
              <h3 className="font-bold text-slate-100 text-sm truncate">{camera.name}</h3>
            </div>
            {canManage && (
              <button
                onClick={() => onEdit(camera)}
                className="text-xs text-gold-400 hover:text-gold-300 hover:bg-gold-500/10 py-1 px-2 rounded-lg border border-gold-500/20 flex items-center gap-1 shrink-0 transition-colors"
                title="Configure Virtual / Device Camera, Stream URL, or Name"
              >
                <Settings2 className="w-3.5 h-3.5" />
                <span className="text-[11px] font-semibold">Configure</span>
              </button>
            )}
          </div>
          <p className="text-xs text-slate-400 truncate mt-1 font-mono">
            {isBridgeActiveForLane ? 'Host OBS / Device Camera Stream' : camera.url || camera.connection_url || 'Default Stream'}
          </p>
          {testResult && (
            <div className="mt-2 p-1.5 rounded bg-navy-950/80 border border-navy-700 text-[10px] text-slate-300 flex items-center justify-between">
              <span>Status: {testResult.connected ? '🟢 Online' : '🔴 Unreachable'}</span>
              {testResult.resolution && (
                <span>
                  Res: {testResult.resolution} {testResult.fps ? `• ${testResult.fps} FPS` : ''}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Quick Lane Switcher & Actions */}
        {canManage && (
          <div className="pt-3 border-t border-navy-800 space-y-2">
            {/* Lane Switcher Dropdown */}
            <div className="flex items-center justify-between gap-2">
              <label className="text-[11px] font-bold text-slate-400 flex items-center gap-1">
                <Target className="w-3 h-3 text-gold-400" />
                Assigned Lane:
              </label>
              <select
                value={camera.lane || ''}
                onChange={(e) => {
                  const val = parseInt(e.target.value)
                  if (val) onLaneChange(camera.id, val)
                }}
                className="input-dark py-1 px-2 text-xs font-semibold bg-navy-950 border-navy-700 text-gold-400 rounded"
              >
                <option value="">-- Select Lane --</option>
                {Array.from({ length: numLanes }, (_, i) => i + 1).map((laneNum) => (
                  <option key={laneNum} value={laneNum}>
                    Lane {laneNum} {camera.lane === laneNum ? '(Current)' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Action Buttons Row */}
            <div className="flex items-center justify-between gap-2 pt-1">
              <button
                onClick={handleTestFeed}
                disabled={testing}
                className="btn-ghost py-1 px-2.5 text-xs text-slate-300 border border-navy-700 hover:border-gold-500/40 flex items-center gap-1.5"
                title="Probe Stream Connectivity"
              >
                {testing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-gold-400" />
                ) : (
                  <Radio className="w-3.5 h-3.5 text-emerald-400" />
                )}
                Test Stream
              </button>

              <div className="flex items-center gap-1">
                {camera.status !== 'connected' && !isBridgeActiveForLane && (
                  <button
                    onClick={() => onReconnect(camera.id)}
                    className="btn-primary text-xs py-1 px-2 flex items-center gap-1"
                    title="Reconnect camera stream"
                  >
                    <RefreshCw className="w-3 h-3" /> Reconnect
                  </button>
                )}
                <button
                  onClick={() => onUnassign(camera.id)}
                  className="btn-ghost p-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded"
                  title="Remove from session"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Edit / Configure Camera Modal with Host Device / OBS Selection ──────────
function EditCameraModal({
  camera,
  numLanes,
  onClose,
  onSave,
}: {
  camera: CameraType
  numLanes: number
  onClose: () => void
  onSave: (updatedData: { name: string; camera_type: string; url: string; lane?: number; startLive?: boolean }) => Promise<void>
}) {
  const cameraStream = useCameraStream()
  const [formData, setFormData] = useState({
    name: camera.name,
    camera_type: camera.camera_type,
    url: camera.url || '',
    lane: camera.lane || 1,
    startLive: true,
  })
  const [streamScope, setStreamScope] = useState<'lane' | 'all'>('lane')
  const [selectedHostDevice, setSelectedHostDevice] = useState<string>(cameraStream.selectedDeviceId || '')
  const [testingStream, setTestingStream] = useState(false)
  const [streamTestResult, setStreamTestResult] = useState<CameraTestResponse | null>(null)
  const [saving, setSaving] = useState(false)

  const handleHostDeviceSelect = (deviceId: string) => {
    setSelectedHostDevice(deviceId)
    const dev = cameraStream.devices.find((d) => d.deviceId === deviceId)
    if (dev) {
      setFormData((prev) => ({
        ...prev,
        name: dev.isObs ? `OBS Virtual Camera (Lane ${prev.lane})` : `${dev.label} (Lane ${prev.lane})`,
        camera_type: 'USB',
        url: dev.isObs ? 'camera://0' : 'camera://0',
        startLive: true,
      }))
    }
    setStreamTestResult(null)
  }

  const handleApplyPreset = (name: string, type: 'USB' | 'RTSP' | 'HTTP', url: string) => {
    setFormData((prev) => ({ ...prev, name, camera_type: type, url }))
    setStreamTestResult(null)
  }

  const handleTestStream = async () => {
    if (!formData.url) {
      toast.error('Please enter a Stream URL or device index first')
      return
    }
    setTestingStream(true)
    try {
      const res = await camerasApi.testStream({
        url: formData.url,
        camera_type: formData.camera_type,
      })
      setStreamTestResult(res)
      if (res.connected) {
        toast.success(`Stream Online! Resolution: ${res.resolution || 'Standard'}`)
      } else {
        toast.error(res.message || 'Stream connection test failed')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Test stream request failed')
    } finally {
      setTestingStream(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name || !formData.url) {
      toast.error('Please fill in required fields')
      return
    }
    setSaving(true)
    try {
      await onSave(formData)
      if (formData.startLive && selectedHostDevice) {
        const laneToUse = streamScope === 'all' ? 'all' : (formData.lane || camera.lane || 1)
        await cameraStream.startStream(selectedHostDevice, laneToUse)
      }
      toast.success('Camera stream configured and active for scoring!')
      onClose()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to update camera')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-navy-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card max-w-lg w-full p-6 space-y-4 animate-in border border-navy-700 shadow-2xl rounded-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center pb-2 border-b border-navy-700">
          <div>
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-gold-400" />
              Configure Camera Stream #{camera.id}
            </h3>
            <p className="text-xs text-slate-400">
              Select Virtual/Device camera, OBS stream preset, or stream URL.
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 1. Host Video Device / Virtual Camera Direct Dropdown */}
          <div className="p-3 rounded-xl bg-navy-900/90 border border-gold-500/30 space-y-2.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold uppercase tracking-wider text-gold-300 flex items-center gap-1.5">
                <Video className="w-4 h-4 text-gold-400" />
                Host Device / Virtual Camera
              </label>
              <button
                type="button"
                onClick={() => cameraStream.refreshDevices()}
                className="text-[10px] text-slate-400 hover:text-gold-400 flex items-center gap-1"
                title="Refresh connected cameras"
              >
                <RefreshCw className="w-3 h-3" /> Refresh
              </button>
            </div>

            <select
              value={selectedHostDevice}
              onChange={(e) => handleHostDeviceSelect(e.target.value)}
              className="input-dark w-full text-xs font-semibold bg-navy-950 border-gold-500/40 text-slate-100"
            >
              <option value="">-- Select Virtual / Hardware Camera (OBS / Webcam) --</option>
              {cameraStream.devices.map((d) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.isObs ? '🎥 [OBS Virtual Camera] ' : '📹 '} {d.label}
                </option>
              ))}
            </select>

            {/* Target Lane Scope Selector */}
            <div className="pt-2 border-t border-navy-800/80 space-y-1.5">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-300 block">
                Stream Scope
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setStreamScope('lane')}
                  className={cn(
                    'p-2 rounded-lg border text-left text-xs font-semibold transition-all flex items-center gap-2',
                    streamScope === 'lane'
                      ? 'bg-gold-500/20 border-gold-500/60 text-gold-300 ring-1 ring-gold-500'
                      : 'bg-navy-950 border-navy-700 text-slate-400 hover:text-slate-200'
                  )}
                >
                  <Target className="w-3.5 h-3.5 text-gold-400 shrink-0" />
                  <div>
                    <p className="leading-tight">Only Lane {formData.lane}</p>
                    <p className="text-[10px] text-slate-400 font-normal">Independent feed</p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setStreamScope('all')}
                  className={cn(
                    'p-2 rounded-lg border text-left text-xs font-semibold transition-all flex items-center gap-2',
                    streamScope === 'all'
                      ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-300 ring-1 ring-emerald-500'
                      : 'bg-navy-950 border-navy-700 text-slate-400 hover:text-slate-200'
                  )}
                >
                  <Layers className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <div>
                    <p className="leading-tight">All Lanes (1 - {numLanes})</p>
                    <p className="text-[10px] text-slate-400 font-normal">Broadcast stream</p>
                  </div>
                </button>
              </div>
            </div>

            <label className="flex items-center gap-2 text-[11px] text-emerald-300 cursor-pointer pt-1">
              <input
                type="checkbox"
                checked={formData.startLive}
                onChange={(e) => setFormData((prev) => ({ ...prev, startLive: e.target.checked }))}
                className="rounded border-navy-700 text-emerald-500 focus:ring-0"
              />
              <span>Activate live stream immediately on Save</span>
            </label>
          </div>

          {/* 2. OBS Studio Quick Presets */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Quick Stream Presets
            </label>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => handleApplyPreset(`OBS Virtual Cam Lane ${formData.lane}`, 'USB', 'camera://0')}
                className="p-2 rounded bg-navy-900 border border-navy-700 hover:border-gold-500/60 text-slate-300 text-left transition-colors"
              >
                🎥 <span className="font-semibold text-slate-100">OBS Virtual Cam #0</span>
                <p className="text-[10px] text-slate-500 font-mono mt-0.5">camera://0</p>
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset(`OBS Virtual Cam Lane ${formData.lane}`, 'USB', 'camera://1')}
                className="p-2 rounded bg-navy-900 border border-navy-700 hover:border-gold-500/60 text-slate-300 text-left transition-colors"
              >
                🎥 <span className="font-semibold text-slate-100">OBS Virtual Cam #1</span>
                <p className="text-[10px] text-slate-500 font-mono mt-0.5">camera://1</p>
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset(`OBS RTSP Lane ${formData.lane}`, 'RTSP', 'rtsp://localhost:8554/live')}
                className="p-2 rounded bg-navy-900 border border-navy-700 hover:border-gold-500/60 text-slate-300 text-left transition-colors"
              >
                📡 <span className="font-semibold text-slate-100">OBS RTSP Stream</span>
                <p className="text-[10px] text-slate-500 font-mono mt-0.5">rtsp://localhost:8554/live</p>
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset(`HTTP Stream Lane ${formData.lane}`, 'HTTP', 'http://localhost:8080/video')}
                className="p-2 rounded bg-navy-900 border border-navy-700 hover:border-gold-500/60 text-slate-300 text-left transition-colors"
              >
                🌐 <span className="font-semibold text-slate-100">HTTP MJPEG Stream</span>
                <p className="text-[10px] text-slate-500 font-mono mt-0.5">http://localhost:8080/video</p>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">
              Camera / Stream Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="e.g. Lane 1 OBS Target Cam"
              className="input-dark w-full text-sm"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">
                Type *
              </label>
              <select
                required
                value={formData.camera_type}
                onChange={(e) => setFormData((prev) => ({ ...prev, camera_type: e.target.value as any }))}
                className="input-dark w-full text-sm"
              >
                <option value="USB">USB / Virtual Cam</option>
                <option value="RTSP">RTSP Stream</option>
                <option value="HTTP">HTTP (MJPEG)</option>
              </select>
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">
                Stream URL / Device Index *
              </label>
              <div className="flex gap-1.5">
                <input
                  type="text"
                  required
                  value={formData.url}
                  onChange={(e) => setFormData((prev) => ({ ...prev, url: e.target.value }))}
                  placeholder={formData.camera_type === 'USB' ? 'camera://0' : 'rtsp://...'}
                  className="input-dark flex-1 text-sm font-mono"
                />
                <button
                  type="button"
                  onClick={handleTestStream}
                  disabled={testingStream || !formData.url}
                  className="btn-ghost py-1.5 px-3 text-xs border border-navy-700 hover:border-gold-500/40 text-slate-300 flex items-center gap-1"
                  title="Test Stream Connectivity"
                >
                  {testingStream ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Radio className="w-3.5 h-3.5 text-emerald-400" />
                  )}
                  Test
                </button>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">
              Assign to Lane (1 - {numLanes})
            </label>
            <select
              value={formData.lane}
              onChange={(e) => setFormData((prev) => ({ ...prev, lane: parseInt(e.target.value) || 1 }))}
              className="input-dark w-full text-sm font-semibold"
            >
              {Array.from({ length: numLanes }, (_, i) => i + 1).map((laneNum) => (
                <option key={laneNum} value={laneNum}>
                  Lane {laneNum}
                </option>
              ))}
            </select>
          </div>

          {streamTestResult && (
            <div
              className={cn(
                'p-2.5 rounded-lg border text-xs flex items-center gap-2',
                streamTestResult.connected
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : 'bg-red-500/10 border-red-500/30 text-red-300'
              )}
            >
              {streamTestResult.connected ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
              )}
              <div>
                <p className="font-semibold">{streamTestResult.message}</p>
                {streamTestResult.resolution && (
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    Resolution: {streamTestResult.resolution}{' '}
                    {streamTestResult.fps ? `• ${streamTestResult.fps} FPS` : ''}
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-3 border-t border-navy-700">
            <button type="button" onClick={onClose} className="btn-ghost py-1.5 px-3 text-xs">
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="btn-primary py-1.5 px-4 text-xs font-bold flex items-center gap-1.5"
            >
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
              Save Configuration
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Main Cameras Page Component ─────────────────────────────────────────────
export default function CamerasPage() {
  const { cameras, setCameras, updateCameraStatus } = useCameraStore()
  const { activeSession } = useSessionStore()
  const { user } = useAuthStore()
  const canManageCameras = user?.role === 'admin' || user?.role === 'scorer'
  const [loading, setLoading] = useState(false)
  const [quickSettingObs, setQuickSettingObs] = useState(false)

  const numLanes = activeSession?.num_lanes || 6

  // Persistent Global Camera Stream Context
  const cameraStream = useCameraStream()

  // Drag & drop state
  const [draggedCamera, setDraggedCamera] = useState<CameraType | null>(null)
  const [dragOverCameraId, setDragOverCameraId] = useState<number | null>(null)
  const [dragOverLaneSlot, setDragOverLaneSlot] = useState<number | null>(null)

  // Edit camera state
  const [editingCamera, setEditingCamera] = useState<CameraType | null>(null)

  // Modals and global list state
  const [isAddCameraOpen, setIsAddCameraOpen] = useState(false)
  const [globalCameras, setGlobalCameras] = useState<CameraType[]>([])
  const [selectedGlobalCameraId, setSelectedGlobalCameraId] = useState<number | string>('')
  const [assignedLane, setAssignedLane] = useState<number>(1)

  // Subform for registering a new camera globally
  const [showRegisterForm, setShowRegisterForm] = useState(false)
  const [newCameraData, setNewCameraData] = useState({
    name: '',
    camera_type: 'USB',
    url: 'camera://0',
  })
  const [testingStream, setTestingStream] = useState(false)
  const [streamTestResult, setStreamTestResult] = useState<CameraTestResponse | null>(null)

  // Auto-discovery state
  const [discoveredDevices, setDiscoveredDevices] = useState<CameraDiscoveryItem[]>([])
  const [discovering, setDiscovering] = useState(false)

  // OBS Guide Drawer
  const [showObsGuide, setShowObsGuide] = useState(false)

  const loadCameras = async () => {
    if (!activeSession) return
    setLoading(true)
    try {
      const res = await camerasApi.listForSession(activeSession.id)
      const list = Array.isArray(res)
        ? res
        : res && Array.isArray((res as any).items)
        ? (res as any).items
        : []
      setCameras(list)
    } catch {
      toast.error('Failed to load cameras')
    } finally {
      setLoading(false)
    }
  }

  const loadGlobalCameras = async () => {
    try {
      const res = await camerasApi.listGlobal()
      setGlobalCameras(res || [])
    } catch {
      toast.error('Failed to load global cameras list')
    }
  }

  const handleOpenAddModal = (targetLane?: number) => {
    setIsAddCameraOpen(true)
    setStreamTestResult(null)
    if (targetLane) setAssignedLane(targetLane)
    loadGlobalCameras()
  }

  const handleQuickSetupObs = async () => {
    if (!activeSession) return
    setQuickSettingObs(true)
    try {
      const res = await camerasApi.quickSetupObs(activeSession.id)
      toast.success(res.message || 'OBS Virtual Cameras configured across lanes!')
      if (!cameraStream.isStreaming && cameraStream.selectedDeviceId) {
        await cameraStream.startStream(cameraStream.selectedDeviceId, 'all')
      }
      await loadCameras()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'OBS quick setup failed')
    } finally {
      setQuickSettingObs(false)
    }
  }

  const handleDiscoverDevices = async () => {
    setDiscovering(true)
    try {
      const devices = await camerasApi.discover()
      setDiscoveredDevices(devices || [])
      if (devices.length > 0) {
        toast.success(`Found ${devices.length} local camera/OBS video sources!`)
      } else {
        toast.error('No hardware camera or OBS Virtual Camera detected.')
      }
    } catch {
      toast.error('Failed to probe local cameras')
    } finally {
      setDiscovering(false)
    }
  }

  const handleApplyPreset = (name: string, type: 'USB' | 'RTSP' | 'HTTP', url: string) => {
    setNewCameraData({
      name,
      camera_type: type,
      url,
    })
    setStreamTestResult(null)
  }

  const handleTestStream = async () => {
    if (!newCameraData.url) {
      toast.error('Please enter a Stream URL or device index first')
      return
    }
    setTestingStream(true)
    try {
      const res = await camerasApi.testStream({
        url: newCameraData.url,
        camera_type: newCameraData.camera_type,
      })
      setStreamTestResult(res)
      if (res.connected) {
        toast.success(`Stream Online! Resolution: ${res.resolution || 'Standard'}`)
      } else {
        toast.error(res.message || 'Stream connection test failed')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Test stream request failed')
    } finally {
      setTestingStream(false)
    }
  }

  const handleAssignCamera = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeSession) return
    const camId = parseInt(selectedGlobalCameraId as string)
    if (!camId) {
      toast.error('Please select a camera')
      return
    }
    try {
      await camerasApi.assign(activeSession.id, {
        camera_id: camId,
        lane: assignedLane,
      })
      toast.success(`Camera assigned successfully to Lane ${assignedLane}!`)
      setIsAddCameraOpen(false)
      setSelectedGlobalCameraId('')
      loadCameras()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to assign camera')
    }
  }

  const handleRegisterCamera = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeSession) return
    if (!newCameraData.name || !newCameraData.url) {
      toast.error('Please fill in required fields')
      return
    }
    try {
      const newCam = await camerasApi.create(newCameraData)
      toast.success('Camera registered! Assigning to lane...')
      await camerasApi.assign(activeSession.id, {
        camera_id: newCam.id,
        lane: assignedLane,
      })
      toast.success(`Connected and assigned to Lane ${assignedLane}!`)
      setNewCameraData({ name: '', camera_type: 'USB', url: 'camera://0' })
      setShowRegisterForm(false)
      setIsAddCameraOpen(false)
      setStreamTestResult(null)
      loadCameras()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to register camera')
    }
  }

  const handleLaneChange = async (cameraId: number, newLane: number) => {
    if (!activeSession) return
    try {
      await camerasApi.assign(activeSession.id, {
        camera_id: cameraId,
        lane: newLane,
      })
      toast.success(`Camera reassigned to Lane ${newLane}!`)
      loadCameras()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to reassign lane')
    }
  }

  // ─── Drag & Drop Event Handlers ─────────────────────────────────────────────
  const handleDragStart = (e: React.DragEvent, cam: CameraType) => {
    setDraggedCamera(cam)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', cam.id.toString())
  }

  const handleDragOverCard = (e: React.DragEvent, targetCam: CameraType) => {
    e.preventDefault()
    if (draggedCamera && draggedCamera.id !== targetCam.id) {
      setDragOverCameraId(targetCam.id)
    }
  }

  const handleDragLeave = () => {
    setDragOverCameraId(null)
  }

  const handleDropOnCard = async (e: React.DragEvent, targetCam: CameraType) => {
    e.preventDefault()
    setDragOverCameraId(null)
    if (!draggedCamera || !activeSession || draggedCamera.id === targetCam.id) return

    const sourceLane = draggedCamera.lane
    const targetLane = targetCam.lane

    if (!sourceLane || !targetLane) {
      if (targetLane) {
        await handleLaneChange(draggedCamera.id, targetLane)
      }
      return
    }

    try {
      await camerasApi.assign(activeSession.id, {
        camera_id: draggedCamera.id,
        lane: targetLane,
      })
      await camerasApi.assign(activeSession.id, {
        camera_id: targetCam.id,
        lane: sourceLane,
      })
      toast.success(`Swapped Lane ${sourceLane} ↔ Lane ${targetLane}!`)
      loadCameras()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to swap camera lanes')
    } finally {
      setDraggedCamera(null)
    }
  }

  const handleDropOnLaneSlot = async (targetLane: number) => {
    setDragOverLaneSlot(null)
    if (!draggedCamera || !activeSession) return
    if (draggedCamera.lane === targetLane) return

    try {
      await camerasApi.assign(activeSession.id, {
        camera_id: draggedCamera.id,
        lane: targetLane,
      })
      toast.success(`Camera moved to Lane ${targetLane}!`)
      loadCameras()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to move camera')
    } finally {
      setDraggedCamera(null)
    }
  }

  const handleSaveCameraConfig = async (updatedData: {
    name: string
    camera_type: string
    url: string
    lane?: number
  }) => {
    if (!editingCamera || !activeSession) return
    await camerasApi.update(editingCamera.id, {
      name: updatedData.name,
      camera_type: updatedData.camera_type,
      url: updatedData.url,
    })
    if (updatedData.lane && updatedData.lane !== editingCamera.lane) {
      await camerasApi.assign(activeSession.id, {
        camera_id: editingCamera.id,
        lane: updatedData.lane,
      })
    }
    loadCameras()
  }

  const handleUnassignCamera = async (cameraId: number) => {
    if (!activeSession) return
    if (!window.confirm('Are you sure you want to remove this camera from this session?')) return
    try {
      await camerasApi.unassign(activeSession.id, cameraId)
      toast.success('Camera removed from session')
      loadCameras()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to unassign camera')
    }
  }

  const handleReconnect = async (cameraId: number) => {
    try {
      updateCameraStatus(cameraId, 'disconnected')
      await camerasApi.reconnect(cameraId)
      toast.success('Reconnection initiated')
      setTimeout(loadCameras, 2000)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to reconnect camera')
    }
  }

  useEffect(() => {
    loadCameras()
  }, [activeSession])

  if (!activeSession) {
    return (
      <div className="p-6 h-full flex items-center justify-center">
        <div className="glass-card max-w-md w-full p-8 text-center rounded-2xl border border-navy-700">
          <CameraIcon className="w-12 h-12 text-gold-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-slate-100 mb-2">No Active Session</h2>
          <p className="text-slate-400 text-sm">Please select an active tournament session to manage cameras.</p>
        </div>
      </div>
    )
  }

  // Create lane map for Lane Slots ribbon
  const laneMap = new Map<number, CameraType>()
  cameras.forEach((c) => {
    if (c.lane) laneMap.set(c.lane, c)
  })

  // Sort cameras neatly by lane number
  const sortedCameras = [...cameras].sort((a, b) => (a.lane || 999) - (b.lane || 999))

  return (
    <div className="p-6 h-full flex flex-col animate-in space-y-6">
      {!canManageCameras && (
        <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-300 text-sm flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 shrink-0 text-amber-400" />
          <span>Spectator Mode: View camera list and connection statuses (Camera management is restricted to Admin & Scorer).</span>
        </div>
      )}

      {/* Header & Main Control Hub */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 glass-card p-5 border border-navy-700/80 rounded-2xl bg-gradient-to-r from-navy-900 via-navy-850 to-navy-900 shadow-2xl">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gold-500/10 border border-gold-500/30 text-gold-400 shadow-inner">
              <CameraIcon className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-black text-slate-100 tracking-tight">Camera & OBS Stream Hub</h1>
                {cameraStream.isStreaming ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    {cameraStream.activeLane === 'all' ? 'LIVE OBS STREAM (ALL LANES)' : `LIVE STREAM (LANE ${cameraStream.activeLane})`}
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-navy-800 text-slate-400 border border-navy-700">
                    IDLE
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Session: <strong className="text-slate-200">{activeSession.name}</strong> • Assigned Lanes: <span className="font-bold text-gold-400">{cameras.length}</span> / {numLanes} • <span className="text-slate-400 italic">Drag cards to re-arrange lanes</span>
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Quick Stream Start/Stop Toggle in Header */}
          {canManageCameras && (
            cameraStream.isStreaming ? (
              <button
                onClick={() => cameraStream.stopStream()}
                className="btn-ghost flex items-center gap-1.5 text-xs px-3 py-2 border border-red-500/40 bg-red-500/10 text-red-300 hover:bg-red-500/20 font-bold"
                title="Stop OBS Virtual Camera stream"
              >
                <Square className="w-3.5 h-3.5 fill-current" /> Stop Stream
              </button>
            ) : (
              <button
                onClick={() => cameraStream.startStream(undefined, 'all')}
                className="btn-primary flex items-center gap-1.5 text-xs px-3.5 py-2 font-bold shadow-lg bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500"
                title="Start OBS Virtual Camera stream across all session lanes"
              >
                <Play className="w-3.5 h-3.5 fill-current" /> Start OBS Stream
              </button>
            )
          )}

          <button
            onClick={() => setShowObsGuide(!showObsGuide)}
            className="btn-ghost flex items-center gap-1.5 text-xs px-3 py-2 border border-navy-700 text-slate-300 hover:border-gold-500/40"
          >
            <HelpCircle className="w-3.5 h-3.5 text-gold-400" /> OBS Setup Guide
          </button>

          {canManageCameras && (
            <>
              <button
                onClick={handleQuickSetupObs}
                disabled={quickSettingObs}
                className="btn-ghost flex items-center gap-1.5 text-xs px-3 py-2 border border-gold-500/40 bg-gold-500/10 text-gold-300 hover:bg-gold-500/20 font-bold shadow-lg"
                title="Auto-assign local OBS Virtual Cameras across all lanes"
              >
                {quickSettingObs ? <Loader2 className="w-3.5 h-3.5 animate-spin text-gold-400" /> : <Zap className="w-3.5 h-3.5 text-gold-400" />}
                1-Click OBS Auto-Setup
              </button>

              <button
                onClick={() => handleOpenAddModal()}
                className="btn-primary flex items-center gap-2 text-xs px-4 py-2 font-bold shadow-lg shadow-gold-500/10"
              >
                <Plus className="w-4 h-4" /> Add / Connect Camera
              </button>
            </>
          )}

          <button
            onClick={loadCameras}
            disabled={loading}
            className="btn-ghost p-2 border border-navy-700 text-slate-300 hover:border-slate-500"
            title="Refresh Camera Statuses"
          >
            <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* OBS Studio Step-by-Step Guide Drawer */}
      {showObsGuide && (
        <div className="glass-card p-5 border border-gold-500/30 rounded-2xl bg-navy-950/90 animate-in space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-navy-800">
            <h3 className="text-sm font-bold text-gold-400 flex items-center gap-2">
              <Video className="w-4 h-4" /> OBS Studio & Camera Stream Setup Instructions
            </h3>
            <button onClick={() => setShowObsGuide(false)} className="text-slate-400 hover:text-slate-200">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-3 rounded-xl bg-navy-900 border border-navy-800 space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-slate-200">
                <span className="w-5 h-5 rounded-full bg-gold-500/20 text-gold-400 flex items-center justify-center text-[10px]">1</span>
                OBS Virtual Camera (Direct in Config)
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                In OBS Studio, click <strong>"Start Virtual Camera"</strong>. Then in any camera card, click <strong>"Configure"</strong>, choose <strong>"OBS Virtual Camera"</strong> from the dropdown, and save! It will immediately flow into both Cameras and Scoring.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-navy-900 border border-navy-800 space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-slate-200">
                <span className="w-5 h-5 rounded-full bg-gold-500/20 text-gold-400 flex items-center justify-center text-[10px]">2</span>
                Unified Camera & Scoring Feeds
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Any camera stream you configure or start here will seamlessly appear in the <strong>Scoring Page</strong>. AI Target Vision will auto-detect target arrows directly from this stream.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-navy-900 border border-navy-800 space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-slate-200">
                <span className="w-5 h-5 rounded-full bg-gold-500/20 text-gold-400 flex items-center justify-center text-[10px]">3</span>
                Drag & Drop Lane Rearranging
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                You can drag any camera card and drop it onto another camera card to instantly <strong>swap their assigned lanes</strong>, or drop onto any top lane slot!
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Lane Slots Ribbon (Lane 1 to N) - Drop Target */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-400 px-1">
          <span className="font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <Target className="w-3.5 h-3.5 text-gold-400" />
            Session Lane Assignments ({cameras.length} / {numLanes} Assigned)
          </span>
          <span className="flex items-center gap-1 text-[11px] text-gold-400/80">
            <Layers className="w-3.5 h-3.5" /> Drag & drop cards to swap or move lanes
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          {Array.from({ length: numLanes }, (_, i) => i + 1).map((laneNum) => {
            const assignedCam = laneMap.get(laneNum)
            const isLaneStreamingLive = cameraStream.isLaneActive(laneNum)
            const isSlotDropTarget = dragOverLaneSlot === laneNum

            return (
              <div
                key={laneNum}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragOverLaneSlot(laneNum)
                }}
                onDragLeave={() => setDragOverLaneSlot(null)}
                onDrop={() => handleDropOnLaneSlot(laneNum)}
                onClick={() => {
                  if (assignedCam) {
                    setEditingCamera(assignedCam)
                  } else if (canManageCameras) {
                    handleOpenAddModal(laneNum)
                  }
                }}
                className={cn(
                  'p-3 rounded-xl border transition-all cursor-pointer flex flex-col justify-between text-left group relative',
                  isSlotDropTarget && 'ring-2 ring-gold-400 scale-105 bg-gold-500/20 border-gold-400',
                  !isSlotDropTarget && isLaneStreamingLive && 'bg-emerald-950/40 border-emerald-500 shadow-md shadow-emerald-500/10 ring-1 ring-emerald-500/40',
                  !isSlotDropTarget && !isLaneStreamingLive && assignedCam && 'bg-navy-900/90 border-gold-500/40 hover:border-gold-400 shadow-md shadow-gold-500/5',
                  !isSlotDropTarget && !isLaneStreamingLive && !assignedCam && 'bg-navy-950/60 border-dashed border-navy-700 hover:border-gold-500/60 hover:bg-navy-900/40'
                )}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-black text-slate-100 flex items-center gap-1">
                    <Target className="w-3 h-3 text-gold-400" />
                    LANE {laneNum}
                  </span>
                  {isLaneStreamingLive ? (
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  ) : assignedCam ? (
                    <span
                      className={cn(
                        'w-2 h-2 rounded-full',
                        assignedCam.status === 'connected' ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
                      )}
                    />
                  ) : (
                    <span className="text-[10px] text-slate-500">Empty</span>
                  )}
                </div>

                {isLaneStreamingLive ? (
                  <div className="space-y-0.5">
                    <p className="text-[11px] font-bold text-emerald-300 truncate">
                      🎥 LIVE OBS STREAM
                    </p>
                    <p className="text-[9px] font-mono text-emerald-400 truncate">
                      Synchronized
                    </p>
                  </div>
                ) : assignedCam ? (
                  <div className="space-y-0.5">
                    <p className="text-[11px] font-bold text-slate-200 truncate group-hover:text-gold-300 transition-colors">
                      {assignedCam.name}
                    </p>
                    <p className="text-[9px] font-mono text-slate-400 truncate">
                      {assignedCam.url || assignedCam.camera_type}
                    </p>
                  </div>
                ) : (
                  <div className="flex items-center gap-1 text-[11px] font-semibold text-gold-400/80 group-hover:text-gold-300">
                    <Plus className="w-3 h-3" /> Assign Stream
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Camera Grid with Live Previews (Sorted by Lane & Supports Drag and Drop) */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {sortedCameras.map((camera) => (
          <LiveCameraCard
            key={camera.id}
            camera={camera}
            numLanes={numLanes}
            canManage={canManageCameras}
            browserStream={cameraStream.activeStream}
            isBridgeActiveForLane={cameraStream.isLaneActive(camera.lane)}
            isDragging={draggedCamera?.id === camera.id}
            isDragOver={dragOverCameraId === camera.id}
            onDragStart={handleDragStart}
            onDragOver={handleDragOverCard}
            onDragLeave={handleDragLeave}
            onDrop={handleDropOnCard}
            onEdit={(cam) => setEditingCamera(cam)}
            onUnassign={handleUnassignCamera}
            onReconnect={handleReconnect}
            onLaneChange={handleLaneChange}
          />
        ))}

        {cameras.length === 0 && !loading && (
          <div className="col-span-full py-16 text-center text-slate-500 border border-dashed border-navy-800 rounded-2xl max-w-lg mx-auto p-8 glass-card">
            <Radio className="w-12 h-12 mx-auto mb-3 opacity-30 text-gold-500" />
            <h3 className="text-base font-bold text-slate-300 mb-1">No Cameras Assigned</h3>
            <p className="text-xs text-slate-500 mb-4">
              Connect your OBS Studio stream (Virtual Camera, RTSP, or HTTP) to lanes to enable real-time target arrow vision.
            </p>
            {canManageCameras && (
              <div className="flex justify-center gap-2">
                <button onClick={handleQuickSetupObs} className="btn-ghost text-xs px-3 py-2 border border-gold-500/40 text-gold-400">
                  <Zap className="w-3.5 h-3.5 mr-1" /> 1-Click OBS Setup
                </button>
                <button onClick={() => handleOpenAddModal()} className="btn-primary text-xs px-4 py-2">
                  <Plus className="w-3.5 h-3.5 mr-1" /> Connect OBS / Camera Feed
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Edit Camera Modal */}
      {editingCamera && (
        <EditCameraModal
          camera={editingCamera}
          numLanes={numLanes}
          onClose={() => setEditingCamera(null)}
          onSave={handleSaveCameraConfig}
        />
      )}

      {/* Add / Register Camera Modal */}
      {isAddCameraOpen && (
        <div className="fixed inset-0 bg-navy-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card max-w-lg w-full p-6 space-y-4 animate-in border border-navy-700 shadow-2xl rounded-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-2 border-b border-navy-700">
              <div>
                <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <Video className="w-5 h-5 text-gold-400" />
                  {showRegisterForm ? 'Register Virtual / Device Camera' : `Assign Camera to Lane ${assignedLane}`}
                </h3>
                <p className="text-xs text-slate-400">
                  {showRegisterForm
                    ? 'Configure OBS Virtual Camera, RTSP, or HTTP stream'
                    : `Assign target camera to session lanes (1 - ${numLanes})`}
                </p>
              </div>
              <button
                onClick={() => {
                  setIsAddCameraOpen(false)
                  setShowRegisterForm(false)
                }}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {!showRegisterForm ? (
              <form onSubmit={handleAssignCamera} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                    Select Registered Camera *
                  </label>
                  <select
                    required
                    value={selectedGlobalCameraId}
                    onChange={(e) => setSelectedGlobalCameraId(e.target.value)}
                    className="input-dark w-full text-sm"
                  >
                    <option value="">-- Choose camera / OBS feed --</option>
                    {globalCameras.map((gc) => (
                      <option key={gc.id} value={gc.id}>
                        {gc.name} ({gc.camera_type}) - {gc.url || 'Live Stream'}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                    Assign to Lane (1 - {numLanes}) *
                  </label>
                  <input
                    type="number"
                    required
                    min="1"
                    max={numLanes}
                    value={assignedLane}
                    onChange={(e) => setAssignedLane(parseInt(e.target.value) || 1)}
                    className="input-dark w-full text-sm font-semibold"
                  />
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-navy-700">
                  <button
                    type="button"
                    onClick={() => setShowRegisterForm(true)}
                    className="text-xs text-gold-400 hover:text-gold-300 font-bold flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" /> Register New Virtual / Device Camera
                  </button>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setIsAddCameraOpen(false)}
                      className="btn-ghost py-1.5 px-3 text-xs"
                    >
                      Cancel
                    </button>
                    <button type="submit" className="btn-primary py-1.5 px-4 text-xs font-bold">
                      Assign Camera
                    </button>
                  </div>
                </div>
              </form>
            ) : (
              <form onSubmit={handleRegisterCamera} className="space-y-4">
                {/* Host Video Device / Virtual Camera Direct Dropdown */}
                <div className="p-3 rounded-xl bg-navy-900/90 border border-gold-500/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold uppercase tracking-wider text-gold-300 flex items-center gap-1.5">
                      <Video className="w-4 h-4 text-gold-400" />
                      Host Video Device / Virtual Camera
                    </label>
                    <button
                      type="button"
                      onClick={() => cameraStream.refreshDevices()}
                      className="text-[10px] text-slate-400 hover:text-gold-400 flex items-center gap-1"
                      title="Refresh connected cameras"
                    >
                      <RefreshCw className="w-3 h-3" /> Refresh
                    </button>
                  </div>

                  <select
                    value={cameraStream.selectedDeviceId}
                    onChange={(e) => {
                      const devId = e.target.value
                      cameraStream.setSelectedDeviceId(devId)
                      const dev = cameraStream.devices.find((d) => d.deviceId === devId)
                      if (dev) {
                        setNewCameraData({
                          name: dev.isObs ? `OBS Virtual Camera Lane ${assignedLane}` : `${dev.label} Lane ${assignedLane}`,
                          camera_type: 'USB',
                          url: 'camera://0',
                        })
                      }
                    }}
                    className="input-dark w-full text-xs font-semibold bg-navy-950 border-gold-500/40 text-slate-100"
                  >
                    <option value="">-- Choose Host Video Device / OBS Virtual Camera --</option>
                    {cameraStream.devices.map((d) => (
                      <option key={d.deviceId} value={d.deviceId}>
                        {d.isObs ? '🎥 [OBS Virtual Camera] ' : '📹 '} {d.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* OBS Presets Ribbon */}
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Quick Presets
                  </label>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <button
                      type="button"
                      onClick={() => handleApplyPreset(`OBS Virtual Cam Lane ${assignedLane}`, 'USB', 'camera://0')}
                      className="p-2 rounded bg-navy-900 border border-navy-700 hover:border-gold-500/60 text-slate-300 text-left transition-colors"
                    >
                      🎥 <span className="font-semibold text-slate-100">OBS Virtual Cam #0</span>
                      <p className="text-[10px] text-slate-500 font-mono mt-0.5">camera://0</p>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApplyPreset(`OBS Virtual Cam Lane ${assignedLane}`, 'USB', 'camera://1')}
                      className="p-2 rounded bg-navy-900 border border-navy-700 hover:border-gold-500/60 text-slate-300 text-left transition-colors"
                    >
                      🎥 <span className="font-semibold text-slate-100">OBS Virtual Cam #1</span>
                      <p className="text-[10px] text-slate-500 font-mono mt-0.5">camera://1</p>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApplyPreset(`OBS RTSP Stream Lane ${assignedLane}`, 'RTSP', 'rtsp://localhost:8554/live')}
                      className="p-2 rounded bg-navy-900 border border-navy-700 hover:border-gold-500/60 text-slate-300 text-left transition-colors"
                    >
                      📡 <span className="font-semibold text-slate-100">OBS RTSP Stream</span>
                      <p className="text-[10px] text-slate-500 font-mono mt-0.5">rtsp://localhost:8554/live</p>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApplyPreset(`HTTP MJPEG Lane ${assignedLane}`, 'HTTP', 'http://localhost:8080/video')}
                      className="p-2 rounded bg-navy-900 border border-navy-700 hover:border-gold-500/60 text-slate-300 text-left transition-colors"
                    >
                      🌐 <span className="font-semibold text-slate-100">HTTP MJPEG Stream</span>
                      <p className="text-[10px] text-slate-500 font-mono mt-0.5">http://localhost:8080/video</p>
                    </button>
                  </div>
                </div>

                {/* Auto Discover Devices */}
                <div>
                  <button
                    type="button"
                    onClick={handleDiscoverDevices}
                    disabled={discovering}
                    className="w-full py-1.5 px-3 rounded bg-navy-900 border border-navy-700 hover:border-slate-500 text-xs text-slate-300 flex items-center justify-center gap-1.5 transition-colors"
                  >
                    {discovering ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-gold-400" />
                    ) : (
                      <Sparkles className="w-3.5 h-3.5 text-gold-400" />
                    )}
                    Auto-Discover Connected Video Devices
                  </button>

                  {discoveredDevices.length > 0 && (
                    <div className="mt-2 space-y-1 max-h-32 overflow-y-auto bg-navy-950 p-2 rounded border border-navy-800">
                      {discoveredDevices.map((dev) => (
                        <button
                          key={dev.device_index}
                          type="button"
                          onClick={() => handleApplyPreset(dev.name, 'USB', dev.url)}
                          className="w-full text-left p-1 rounded hover:bg-navy-800 text-[11px] text-slate-200 flex items-center justify-between font-mono"
                        >
                          <span>{dev.name}</span>
                          <span className="text-gold-400 text-[10px]">Select</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">
                    Camera / Stream Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={newCameraData.name}
                    onChange={(e) => setNewCameraData((prev) => ({ ...prev, name: e.target.value }))}
                    placeholder={`e.g. Lane ${assignedLane} OBS Cam`}
                    className="input-dark w-full text-sm"
                  />
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">
                      Type *
                    </label>
                    <select
                      required
                      value={newCameraData.camera_type}
                      onChange={(e) => setNewCameraData((prev) => ({ ...prev, camera_type: e.target.value }))}
                      className="input-dark w-full text-sm"
                    >
                      <option value="USB">USB / Virtual Cam</option>
                      <option value="RTSP">RTSP Stream</option>
                      <option value="HTTP">HTTP (MJPEG)</option>
                    </select>
                  </div>
                  <div className="col-span-2">
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">
                      Stream URL / Device Index *
                    </label>
                    <div className="flex gap-1.5">
                      <input
                        type="text"
                        required
                        value={newCameraData.url}
                        onChange={(e) => setNewCameraData((prev) => ({ ...prev, url: e.target.value }))}
                        placeholder={newCameraData.camera_type === 'USB' ? 'camera://0' : 'rtsp://...'}
                        className="input-dark flex-1 text-sm font-mono"
                      />
                      <button
                        type="button"
                        onClick={handleTestStream}
                        disabled={testingStream || !newCameraData.url}
                        className="btn-ghost py-1.5 px-3 text-xs border border-navy-700 hover:border-gold-500/40 text-slate-300 flex items-center gap-1"
                        title="Test Stream Connectivity"
                      >
                        {testingStream ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Radio className="w-3.5 h-3.5 text-emerald-400" />
                        )}
                        Test
                      </button>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1">
                    Assign to Lane (1 - {numLanes})
                  </label>
                  <input
                    type="number"
                    min="1"
                    max={numLanes}
                    value={assignedLane}
                    onChange={(e) => setAssignedLane(parseInt(e.target.value) || 1)}
                    className="input-dark w-full text-sm font-semibold"
                  />
                </div>

                {streamTestResult && (
                  <div
                    className={cn(
                      'p-2.5 rounded-lg border text-xs flex items-center gap-2',
                      streamTestResult.connected
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                        : 'bg-red-500/10 border-red-500/30 text-red-300'
                    )}
                  >
                    {streamTestResult.connected ? (
                      <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                    ) : (
                      <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
                    )}
                    <div>
                      <p className="font-semibold">{streamTestResult.message}</p>
                      {streamTestResult.resolution && (
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          Resolution: {streamTestResult.resolution}{' '}
                          {streamTestResult.fps ? `• ${streamTestResult.fps} FPS` : ''}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                <div className="flex justify-end gap-3 pt-3 border-t border-navy-700">
                  <button
                    type="button"
                    onClick={() => setShowRegisterForm(false)}
                    className="btn-ghost py-1.5 px-3 text-xs"
                  >
                    Back to Assignment
                  </button>
                  <button type="submit" className="btn-primary py-1.5 px-4 text-xs font-bold">
                    Register & Assign Camera
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
