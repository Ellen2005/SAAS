import { useEffect, useRef, useCallback, useState } from 'react';

/**
 * Hook for real-time data streaming via Server-Sent Events (SSE)
 * Provides live KPI updates without polling
 */
export function useRealTimeData(userId, options = {}) {
  const {
    endpoint = '/api/realtime/stream',
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    onData = () => {},
    onError = () => {},
    onConnect = () => {},
    onDisconnect = () => {},
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const eventSourceRef = useRef(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    if (!userId) return;

    try {
      // Close existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const url = `${import.meta.env.VITE_API_URL || ''}${endpoint}?user_id=${userId}`;
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        reconnectCountRef.current = 0;
        onConnect?.();
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastUpdate(new Date());
          onData?.(data);
        } catch (err) {
          console.error('Failed to parse SSE data:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('SSE connection error:', err);
        setIsConnected(false);
        onError?.(err);
        eventSource.close();

        // Auto-reconnect with exponential backoff
        if (reconnectCountRef.current < maxReconnectAttempts) {
          const delay = reconnectInterval * Math.pow(1.5, reconnectCountRef.current);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectCountRef.current++;
            connect();
          }, delay);
        } else {
          onDisconnect?.();
        }
      };

      // Handle custom event types
      eventSource.addEventListener('kpi-update', (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastUpdate(new Date());
          onData?.({ type: 'kpi-update', ...data });
        } catch (err) {
          console.error('Failed to parse KPI update:', err);
        }
      });

      eventSource.addEventListener('anomaly-alert', (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastUpdate(new Date());
          onData?.({ type: 'anomaly-alert', ...data });
        } catch (err) {
          console.error('Failed to parse anomaly alert:', err);
        }
      });

      eventSource.addEventListener('report-generated', (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastUpdate(new Date());
          onData?.({ type: 'report-generated', ...data });
        } catch (err) {
          console.error('Failed to parse report event:', err);
        }
      });

    } catch (err) {
      console.error('Failed to establish SSE connection:', err);
      onError?.(err);
    }
  }, [userId, endpoint, reconnectInterval, maxReconnectAttempts, onData, onError, onConnect, onDisconnect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
    onDisconnect?.();
  }, [onDisconnect]);

  useEffect(() => {
    if (userId) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [userId, connect, disconnect]);

  return {
    isConnected,
    lastUpdate,
    connect,
    disconnect,
  };
}

/**
 * Hook for WebSocket connections (alternative to SSE)
 */
export function useWebSocket(url, options = {}) {
  const {
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    onMessage = () => {},
    onError = () => {},
    onConnect = () => {},
    onDisconnect = () => {},
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const wsRef = useRef(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    try {
      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectCountRef.current = 0;
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          onMessage?.(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        setIsConnected(false);
        onError?.(err);
      };

      ws.onclose = () => {
        setIsConnected(false);
        onDisconnect?.();

        // Auto-reconnect
        if (reconnectCountRef.current < maxReconnectAttempts) {
          const delay = reconnectInterval * Math.pow(1.5, reconnectCountRef.current);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectCountRef.current++;
            connect();
          }, delay);
        }
      };
    } catch (err) {
      console.error('Failed to establish WebSocket connection:', err);
      onError?.(err);
    }
  }, [url, reconnectInterval, maxReconnectAttempts, onMessage, onError, onConnect, onDisconnect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    onDisconnect?.();
  }, [onDisconnect]);

  const send = useCallback((data) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    if (url) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [url, connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    send,
    connect,
    disconnect,
  };
}