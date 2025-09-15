import { useEffect, useRef, useState } from 'react'
import { WS_BASE_URL } from '@/lib/constants'

interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
}

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(`${WS_BASE_URL}/ws`)
      
      ws.onopen = () => {
        setIsConnected(true)
        console.log('WebSocket connected')
      }
      
      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
      
      ws.onclose = () => {
        setIsConnected(false)
        console.log('WebSocket disconnected')
        // Reconnect after 5 seconds
        setTimeout(connect, 5000)
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsConnected(false)
      }
      
      wsRef.current = ws
    }

    connect()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const sendMessage = (message: any) => {
    if (wsRef.current && isConnected) {
      wsRef.current.send(JSON.stringify(message))
    }
  }

  return {
    isConnected,
    lastMessage,
    sendMessage,
  }
}
