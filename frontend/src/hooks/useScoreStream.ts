import { useCallback, useState } from 'react'
import { useWebSocket } from './useWebSocket'
import type { WSEvent } from '@/types'

export function useScoreStream(sessionId: number | null) {
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null)

  const handleMessage = useCallback((event: MessageEvent) => {
    if (typeof event.data === 'string') {
      try {
        const parsed: WSEvent = JSON.parse(event.data)
        setLastEvent(parsed)
      } catch {
        // ignore malformed
      }
    }
  }, [])

  useWebSocket({
    url: sessionId ? `ws://localhost:8000/api/ws/${sessionId}` : '',
    onMessage: handleMessage,
    enabled: !!sessionId,
  })

  return { lastEvent }
}
