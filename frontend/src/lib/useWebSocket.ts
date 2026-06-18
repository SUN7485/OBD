'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import { useAuthStore, useTelemetryStore, useAlertStore } from './store'

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null)
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const { token, user } = useAuthStore()
  const { updateTelemetry } = useTelemetryStore()
  const { addAlert } = useAlertStore()

  const connect = useCallback(() => {
    if (!token || !user) return

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const ws = new WebSocket(`${WS_URL}/api/v1/ws?token=${token}`)

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      
      ws.send(JSON.stringify({ type: 'subscribe', room: `org:${user.organization_id}` }))
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'telemetry' && data.data?.car_id) {
          updateTelemetry(data.data.car_id, data.data)
        }
        
        if (data.type === 'alert') {
          addAlert({
            id: data.data.id,
            car_id: data.data.car_id,
            car_name: data.data.car_name,
            severity: data.data.severity,
            message: data.data.message,
            is_read: false,
            is_resolved: false,
            created_at: data.data.created_at,
          })
        }

        if (data.type === 'pong') {
          // Heartbeat response received
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    ws.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason)
      setIsConnected(false)
      
      // Attempt reconnect after 3 seconds
      if (!event.wasClean && token && user) {
        reconnectTimerRef.current = setTimeout(() => {
          connect()
        }, 3000)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    wsRef.current = ws

    // Setup heartbeat ping every 25 seconds
    heartbeatIntervalRef.current = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 25000)
  }, [token, user, updateTelemetry, addAlert])

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
      heartbeatIntervalRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnecting')
      wsRef.current = null
    }
    
    setIsConnected(false)
  }, [])

  const subscribeToCar = useCallback((carId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', room: `car:${carId}` }))
    }
  }, [])

  const unsubscribeFromCar = useCallback((carId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'unsubscribe', room: `car:${carId}` }))
    }
  }, [])

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return {
    socket: wsRef.current,
    isConnected,
    subscribeToCar,
    unsubscribeFromCar,
  }
}