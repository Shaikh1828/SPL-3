import { useEffect, useRef, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'

interface UseWebSocketOptions {
  url: string
  onMessage?: (event: MessageEvent) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (event: Event) => void
  enabled?: boolean
}

export function useWebSocket({
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
  enabled = true,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const token = useAuthStore((s) => s.token)

  const connect = useCallback(() => {
    if (!enabled || !token) return

    const wsUrl = `${url}?token=${token}`
    const ws = new WebSocket(wsUrl)
    ws.binaryType = 'blob'
    wsRef.current = ws

    ws.onopen = () => onOpen?.()
    ws.onmessage = (e) => onMessage?.(e)
    ws.onclose = () => {
      onClose?.()
      // Auto-reconnect after 3s
      reconnectTimer.current = setTimeout(connect, 3000)
    }
    ws.onerror = (e) => onError?.(e)
  }, [url, token, enabled, onOpen, onMessage, onClose, onError])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const send = useCallback((data: string | ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data)
    }
  }, [])

  return { send, ws: wsRef }
}
