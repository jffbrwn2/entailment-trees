import { useEffect, useRef, useCallback } from 'react'

export interface WebSocketOptions {
  /** Called when a message is received (excluding ping) */
  onMessage?: (data: unknown) => void
  /** Called when connection opens */
  onOpen?: () => void
  /** Called when connection closes */
  onClose?: () => void
  /** Called on error */
  onError?: (error: Event) => void
  /** Whether the connection should be active */
  enabled?: boolean
}

/**
 * Custom hook for WebSocket connections with automatic reconnection
 * and ping handling.
 *
 * @param path - WebSocket path (e.g., '/ws/hypergraph/my-folder')
 * @param options - Configuration options
 */
export function useWebSocket(path: string | null, options: WebSocketOptions = {}) {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    enabled = true,
  } = options

  const wsRef = useRef<WebSocket | null>(null)

  // Build full WebSocket URL
  const getWsUrl = useCallback(() => {
    if (!path) return null
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsProtocol}//${window.location.host}${path}`
  }, [path])

  useEffect(() => {
    if (!enabled || !path) {
      // Clean up existing connection if disabled
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      return
    }

    const url = getWsUrl()
    if (!url) return

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      onOpen?.()
    }

    ws.onmessage = (event) => {
      // Handle ping messages silently
      if (event.data === 'ping') {
        return
      }

      try {
        const data = JSON.parse(event.data)
        onMessage?.(data)
      } catch (e) {
        console.error('WebSocket message parse error:', e)
      }
    }

    ws.onclose = () => {
      onClose?.()
    }

    ws.onerror = (error) => {
      onError?.(error)
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [path, enabled, getWsUrl, onMessage, onOpen, onClose, onError])

  // Return the WebSocket ref for direct access if needed
  return wsRef
}

export default useWebSocket
