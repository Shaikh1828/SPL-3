import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'
import { camerasApi } from '@/api/cameras'
import { useSessionStore } from '@/store/sessionStore'
import toast from 'react-hot-toast'

export interface HostVideoDevice {
  deviceId: string
  label: string
  isObs: boolean
}

export interface CameraStreamContextType {
  devices: HostVideoDevice[]
  selectedDeviceId: string
  activeStream: MediaStream | null
  isStreaming: boolean
  activeLane: number | 'all'
  isSyncing: boolean
  setSelectedDeviceId: (id: string) => void
  setActiveLane: (lane: number | 'all') => void
  refreshDevices: () => Promise<HostVideoDevice[]>
  startStream: (deviceIdToUse?: string, laneToUse?: number | 'all') => Promise<MediaStream | null>
  stopStream: () => void
  captureFrameBase64: () => string | null
  pushCurrentFrame: (targetLane?: number | 'all', camId?: number) => Promise<boolean>
  isLaneActive: (lane: number | undefined) => boolean
}

const CameraStreamContext = createContext<CameraStreamContextType | null>(null)

export function CameraStreamProvider({ children }: { children: React.ReactNode }) {
  const { activeSession } = useSessionStore()
  const totalLanes = activeSession?.num_lanes || 6

  const [devices, setDevices] = useState<HostVideoDevice[]>([])
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('')
  const [activeStream, setActiveStream] = useState<MediaStream | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [activeLane, setActiveLane] = useState<number | 'all'>(1)
  const [isSyncing, setIsSyncing] = useState(false)

  const videoElementRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const syncIntervalRef = useRef<any>(null)
  const activeStreamRef = useRef<MediaStream | null>(null)
  activeStreamRef.current = activeStream

  // 1. Enumerate all hardware and OBS virtual cameras from host browser
  const refreshDevices = useCallback(async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
        console.warn('MediaDevices API not supported in this browser environment')
        return []
      }

      // Prompt permission once to get device labels if not already provided
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

      // Auto-select OBS Virtual Camera if detected and none selected yet
      if (videoDevs.length > 0) {
        setSelectedDeviceId((prev) => {
          if (prev) return prev
          const obsDev = videoDevs.find((d) => d.isObs)
          return obsDev ? obsDev.deviceId : videoDevs[0].deviceId
        })
      }

      return videoDevs
    } catch (err) {
      console.error('Failed to enumerate host video devices:', err)
      return []
    }
  }, [])

  // 2. Start streaming selected device
  const startStream = useCallback(
    async (deviceIdToUse?: string, laneToUse?: number | 'all') => {
      const devId = deviceIdToUse || selectedDeviceId
      if (laneToUse !== undefined) {
        setActiveLane(laneToUse)
      }

      if (!devId) {
        toast.error('Please select a video input device (e.g. OBS Virtual Camera)')
        return null
      }

      try {
        // Stop previous stream tracks
        if (activeStreamRef.current) {
          activeStreamRef.current.getTracks().forEach((t) => t.stop())
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
        setSelectedDeviceId(devId)

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
    },
    [selectedDeviceId]
  )

  // 3. Stop stream
  const stopStream = useCallback(() => {
    if (activeStreamRef.current) {
      activeStreamRef.current.getTracks().forEach((t) => t.stop())
      setActiveStream(null)
    }
    setIsStreaming(false)
    if (syncIntervalRef.current) {
      clearInterval(syncIntervalRef.current)
      syncIntervalRef.current = null
    }
  }, [])

  // 4. Capture current JPEG Base64 frame
  const captureFrameBase64 = useCallback((): string | null => {
    let v = videoElementRef.current
    if (!v || v.readyState < 2 || !v.videoWidth) {
      const domVideos = Array.from(document.querySelectorAll('video'))
      const readyVid = domVideos.find((vid) => vid.readyState >= 2 && vid.videoWidth > 0 && !vid.paused)
      if (readyVid) {
        v = readyVid
        videoElementRef.current = readyVid
      }
    }

    if (!v || v.readyState < 2 || !v.videoWidth) return null

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

  // 5. Push current frame to backend
  const pushCurrentFrame = useCallback(
    async (targetLane?: number | 'all', camId?: number) => {
      const b64 = captureFrameBase64()
      if (!b64) return false

      try {
        const laneToUse = targetLane !== undefined ? targetLane : activeLane
        if (camId) {
          await camerasApi.pushFrame(camId, b64).catch(() => {})
        }
        if (activeSession?.id) {
          if (laneToUse === 'all') {
            const promises = []
            for (let l = 1; l <= totalLanes; l++) {
              promises.push(camerasApi.pushLaneFrame(activeSession.id, l, b64).catch(() => {}))
            }
            await Promise.all(promises)
          } else if (typeof laneToUse === 'number' && laneToUse > 0) {
            await camerasApi.pushLaneFrame(activeSession.id, laneToUse, b64).catch(() => {})
          }
        }
        return true
      } catch (err) {
        console.warn('Frame push failed:', err)
        return false
      }
    },
    [captureFrameBase64, activeLane, activeSession?.id, totalLanes]
  )

  // 6. Global Background synchronization loop when streaming
  useEffect(() => {
    if (isStreaming && activeSession?.id) {
      setIsSyncing(true)
      // Push first frame immediately
      pushCurrentFrame(activeLane)

      syncIntervalRef.current = setInterval(() => {
        pushCurrentFrame(activeLane)
      }, 1500)

      return () => {
        if (syncIntervalRef.current) {
          clearInterval(syncIntervalRef.current)
          syncIntervalRef.current = null
        }
        setIsSyncing(false)
      }
    }
  }, [isStreaming, activeSession?.id, activeLane, pushCurrentFrame])

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

  const value: CameraStreamContextType = {
    devices,
    selectedDeviceId,
    activeStream,
    isStreaming,
    activeLane,
    isSyncing,
    setSelectedDeviceId,
    setActiveLane,
    refreshDevices,
    startStream,
    stopStream,
    captureFrameBase64,
    pushCurrentFrame,
    isLaneActive,
  }

  return <CameraStreamContext.Provider value={value}>{children}</CameraStreamContext.Provider>
}

export function useCameraStream() {
  const context = useContext(CameraStreamContext)
  if (!context) {
    throw new Error('useCameraStream must be used within a CameraStreamProvider')
  }
  return context
}
