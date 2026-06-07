import { useEffect, useRef, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'

export function useCameraPreview(
  cameraId: number | null,
  imgRef: React.RefObject<HTMLImageElement | null>
) {
  const wsRef = useRef<WebSocket | null>(null)
  const prevUrl = useRef<string | null>(null)
  const token = useAuthStore((s) => s.token)

  const cleanup = useCallback(() => {
    wsRef.current?.close()
    if (prevUrl.current) URL.revokeObjectURL(prevUrl.current)
  }, [])

  useEffect(() => {
    if (!cameraId || !token) return
    const ws = new WebSocket(
      `ws://localhost:8000/api/ws/camera/${cameraId}/preview?token=${token}`
    )
    ws.binaryType = 'blob'
    wsRef.current = ws

    ws.onmessage = (e) => {
      if (e.data instanceof Blob) {
        const url = URL.createObjectURL(e.data)
        if (imgRef.current) imgRef.current.src = url
        if (prevUrl.current) URL.revokeObjectURL(prevUrl.current)
        prevUrl.current = url
      }
    }

    return cleanup
  }, [cameraId, token, imgRef, cleanup])
}
