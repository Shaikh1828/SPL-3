/**
 * Resolves the WebSocket URL dynamically based on environment,
 * proxy configuration, or window.location.
 */
export function getWebSocketUrl(path: string): string {
  const envUrl = import.meta.env.VITE_WS_URL
  if (envUrl) {
    const base = envUrl.replace(/\/$/, '')
    const cleanPath = path.startsWith('/') ? path : `/${path}`
    return `${base}${cleanPath}`
  }

  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const cleanPath = path.startsWith('/') ? path : `/${path}`
    return `${protocol}//${window.location.host}${cleanPath}`
  }

  return `ws://localhost:8000${path.startsWith('/') ? path : `/${path}`}`
}
