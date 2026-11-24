// JARVIS WebSocket Hook — real-time events from the backend
import { useEffect, useRef, useCallback } from 'react'
import { useJarvisStore } from '../stores/jarvisStore'
import type { VoiceState } from '../stores/jarvisStore'

const getWsUrl = () => {
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.host}/ws`
  }
  return 'ws://127.0.0.1:8765/ws'
}
const RECONNECT_DELAY = 3000
const MAX_RECONNECT_ATTEMPTS = 10

export function useJarvisWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const attemptsRef = useRef(0)
  const { setConnected, setBackendOnline, setVoiceState, setEmergencyStopped, setSafeMode, addMessage } = useJarvisStore()

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const msg = JSON.parse(event.data)
      const { event: evtName, data } = msg

      switch (evtName) {
        case 'connected':
          if (data.voice_state) setVoiceState(data.voice_state as VoiceState)
          if (data.emergency_stopped !== undefined) setEmergencyStopped(data.emergency_stopped)
          if (typeof data.safe_mode === 'boolean') setSafeMode(data.safe_mode)
          break

        case 'voice_state':
          if (data.new) setVoiceState(data.new as VoiceState)
          break

        case 'transcript':
          if (data.role && data.text) {
            addMessage({ role: data.role, text: data.text })
          }
          break

        case 'emergency_stop':
          setEmergencyStopped(data.active ?? false)
          break

        case 'provider_fallback':
          if (data && data.to_provider) {
            addMessage({
              role: 'assistant',
              text: `⚠️ [Automatic Fallback] Switched to ${data.to_provider.toUpperCase()} (${data.reason || 'Primary provider error'}).`,
            })
          }
          break

        case 'permission_update':
          // Handled by polling status
          break

        case 'heartbeat':
        case 'pong':
          break

        default:
          break
      }
    } catch {
      // Non-JSON message, ignore
    }
  }, [setVoiceState, setEmergencyStopped, addMessage])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    try {
      const ws = new WebSocket(getWsUrl())
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[JARVIS WS] Connected')
        setConnected(true)
        setBackendOnline(true)
        attemptsRef.current = 0
      }

      ws.onmessage = handleMessage

      ws.onerror = () => {
        console.warn('[JARVIS WS] Connection error')
      }

      ws.onclose = () => {
        console.warn('[JARVIS WS] Disconnected')
        setConnected(false)
        setBackendOnline(false)
        wsRef.current = null

        if (attemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          attemptsRef.current++
          reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY)
        }
      }
    } catch (err) {
      console.error('[JARVIS WS] Failed to create WebSocket:', err)
    }
  }, [handleMessage, setConnected, setBackendOnline])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((type: string, payload: Record<string, unknown> = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...payload }))
    }
  }, [])

  return { sendMessage }
}
