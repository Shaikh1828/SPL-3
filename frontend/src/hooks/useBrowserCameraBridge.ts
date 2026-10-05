import { useState, useEffect, useRef, useCallback } from 'react'
import { camerasApi } from '@/api/cameras'
import toast from 'react-hot-toast'

export interface HostVideoDevice {
  deviceId: string
  label: string
  isObs: boolean
}

export function useBrowserCameraBridge(sessionId?: number, totalLanes: number = 6) {
  const [devices, setDevices] = useState<HostVideoDevice[]>([])
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('')
  const [activeStream, setActiveStream] = useState<MediaStream | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [activeLane, setActiveLane] = useState<number | 'all'>('all')
  const [isSyncing, setIsSyncing] = useState(false)

  const videoElementRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const syncIntervalRef = useRef<any>(null)

  // 1. Enumerate all hardware and OBS virtual cameras from host browser
  const refreshDevices = useCallback(async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
        console.warn('MediaDevices API not supported in this browser environment')
        return []
      }

      // Prompt permission once to get device labels
      try {
        const tempStream = await navigator.mediaDevices.getUserMedia({ video: true })
        tempStream.getTracks().forEach((t) => t.stop())
      } catch {
        // Permission might already be granted or denied
      }

      const allDevices = await navigator.mediaDevices.enumerateDevices()
      const videoDevs = allDevices
        .filter((d) => d.kind === 'videoinput')
        .map((d, index) => {
          const label = d.label || `Camera Device #${index + 1}`
          const isObs = label.toLowerCase().includes('obs') || label.toLowerCase().includes('virtual')
          return {
            deviceId: d.deviceId,
            label,
            isObs,
          }
        })

      setDevices(videoDevs)

      // Auto-select OBS Virtual Camera if detected
      if (!selectedDeviceId && videoDevs.length > 0) {
        const obsDev = videoDevs.find((d) => d.isObs)
        if (obsDev) {
          setSelectedDeviceId(obsDev.deviceId)
        } else {
          setSelectedDeviceId(videoDevs[0].deviceId)
        }
      }

      return videoDevs
    } catch (err) {
      console.error('Failed to enumerate host video devices:', err)
      return []
    }
  }, [selectedDeviceId])

  // 2. Start streaming selected device
  const startStream = useCallback(async (deviceIdToUse?: string) => {
    const devId = deviceIdToUse || selectedDeviceId
    if (!devId) {
      toast.error('Please select a video input device (e.g. OBS Virtual Camera)')
      return null
    }

    try {
      // Stop previous stream
      if (activeStream) {
        activeStream.getTracks().forEach((t) => t.stop())
      }

      const constraints: MediaStreamConstraints = {
        video: {
          deviceId: { exact: devId },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      setActiveStream(stream)
      setIsStreaming(true)

      if (!canvasRef.current) {
        canvasRef.current = document.createElement('canvas')
      }

      if (!videoElementRef.current) {
        const v = document.createElement('video')
        v.muted = true
        v.playsInline = true
        v.autoplay = true
        videoElementRef.current = v
      }
      videoElementRef.current.srcObject = stream
      await videoElementRef.current.play().catch(() => {})

      toast.success('Live OBS / Camera stream connected successfully!')
      return stream
    } catch (err: any) {
      console.error('Failed to open camera stream:', err)
      toast.error(`Could not open camera stream: ${err.message || 'Permission denied'}`)
      return null
    }
  }, [selectedDeviceId, activeStream])

  // 3. Stop stream
  const stopStream = useCallback(() => {
    if (activeStream) {
      activeStream.getTracks().forEach((t) => t.stop())
      setActiveStream(null)
    }
    setIsStreaming(false)
    if (syncIntervalRef.current) {
      clearInterval(syncIntervalRef.current)
      syncIntervalRef.current = null
    }
  }, [activeStream])

  // 4. Capture current JPEG Base64 frame
  const captureFrameBase64 = useCallback((): string | null => {
    const v = videoElementRef.current
    if (!v || v.readyState < 2) return null

    const canvas = canvasRef.current || document.createElement('canvas')
    canvasRef.current = canvas

    const w = v.videoWidth || 1280
    const h = v.videoHeight || 720
    canvas.width = w
    canvas.height = h

    const ctx = canvas.getContext('2d')
    if (!ctx) return null

    ctx.drawImage(v, 0, 0, w, h)
    return canvas.toDataURL('image/jpeg', 0.85)
  }, [])

  // 5. Push current frame to backend (supports single lane or broadcasting to all lanes)
  const pushCurrentFrame = useCallback(
    async (targetLane?: number | 'all', camId?: number) => {
      const b64 = captureFrameBase64()
      if (!b64) return false

      try {
        const laneToUse = targetLane !== undefined ? targetLane : activeLane
        if (camId) {
          await camerasApi.pushFrame(camId, b64)
        }
        if (sessionId) {
          if (laneToUse === 'all') {
            // Push to all lanes simultaneously
            const promises = []
            for (let l = 1; l <= totalLanes; l++) {
              promises.push(camerasApi.pushLaneFrame(sessionId, l, b64).catch(() => {}))
            }
            await Promise.all(promises)
          } else if (typeof laneToUse === 'number' && laneToUse > 0) {
            await camerasApi.pushLaneFrame(sessionId, laneToUse, b64)
          }
        }
        return true
      } catch (err) {
        console.warn('Frame push failed:', err)
        return false
      }
    },
    [captureFrameBase64, activeLane, sessionId, totalLanes]
  )

  // 6. Background synchronization loop when streaming
  useEffect(() => {
    if (isStreaming && sessionId) {
      setIsSyncing(true)
      // Push first frame immediately
      pushCurrentFrame(activeLane)

      syncIntervalRef.current = setInterval(() => {
        pushCurrentFrame(activeLane)
      }, 2000)

      return () => {
        if (syncIntervalRef.current) {
          clearInterval(syncIntervalRef.current)
          syncIntervalRef.current = null
        }
        setIsSyncing(false)
      }
    }
  }, [isStreaming, sessionId, activeLane, pushCurrentFrame])

  // Initial enumeration on mount
  useEffect(() => {
    refreshDevices()
  }, [refreshDevices])

  const isLaneActive = useCallback(
    (lane: number | undefined): boolean => {
      if (!isStreaming || !lane) return false
      if (activeLane === 'all') return true
      return activeLane === lane
    },
    [isStreaming, activeLane]
  )

  return {
    devices,
    selectedDeviceId,
    setSelectedDeviceId,
    activeStream,
    isStreaming,
    activeLane,
    setActiveLane,
    isSyncing,
    refreshDevices,
    startStream,
    stopStream,
    captureFrameBase64,
    pushCurrentFrame,
    isLaneActive,
  }
}
