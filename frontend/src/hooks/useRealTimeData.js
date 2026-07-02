import { useEffect, useRef, useCallback, useState } from 'react';
import { supabase } from '../lib/supabaseClient';

function _buildSseUrl(endpoint) {
  const apiUrl = import.meta.env.VITE_API_URL || '';
  return `${apiUrl}${endpoint}`;
}

export function useRealTimeData(userId, options = {}) {
  const {
    endpoint = '/api/realtime/stream',
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    onData,
    onError,
    onConnect,
    onDisconnect,
  } = options;

  const onDataRef = useRef(onData);
  const onErrorRef = useRef(onError);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);

  useEffect(() => {
    onDataRef.current = onData;
    onErrorRef.current = onError;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
  });

  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const eventSourceRef = useRef(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const connectWithTokenRef = useRef(null);

  const getToken = useCallback(async () => {
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token;
  }, []);

  const connectWithToken = useCallback(async () => {
    if (!userId) return;
    const token = await getToken();
    if (!token) return;

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    const url = `${_buildSseUrl(endpoint)}?token=${encodeURIComponent(token)}`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      reconnectCountRef.current = 0;
      onConnectRef.current?.();
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastUpdate(new Date());
        onDataRef.current?.(data);
      } catch (err) {
        console.error('Failed to parse SSE data:', err);
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      onErrorRef.current?.(new Error('SSE connection lost'));
      eventSource.close();

      if (reconnectCountRef.current < maxReconnectAttempts) {
        const delay = reconnectInterval * Math.pow(1.5, reconnectCountRef.current);
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectCountRef.current++;
          connectWithTokenRef.current?.();
        }, delay);
      } else {
        onDisconnectRef.current?.();
      }
    };
  }, [userId, endpoint, reconnectInterval, maxReconnectAttempts, getToken]);

  useEffect(() => {
    connectWithTokenRef.current = connectWithToken;
  });

  useEffect(() => {
    if (userId) {
      connectWithToken();
    }
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [userId, connectWithToken]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
    onDisconnectRef.current?.();
  }, []);

  return {
    isConnected,
    lastUpdate,
    connect: connectWithToken,
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

  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onErrorRef.current = onError;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
  });

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const wsRef = useRef(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const connectRef = useRef(null);

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
        onConnectRef.current?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          onMessageRef.current?.(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        setIsConnected(false);
        onErrorRef.current?.(err);
      };

      ws.onclose = () => {
        setIsConnected(false);
        onDisconnectRef.current?.();

        if (reconnectCountRef.current < maxReconnectAttempts) {
          const delay = reconnectInterval * Math.pow(1.5, reconnectCountRef.current);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectCountRef.current++;
            connectRef.current?.();
          }, delay);
        }
      };
    } catch (err) {
      console.error('Failed to establish WebSocket connection:', err);
      onErrorRef.current?.(err);
    }
  }, [url, reconnectInterval, maxReconnectAttempts]);

  useEffect(() => {
    connectRef.current = connect;
  });

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    onDisconnectRef.current?.();
  }, []);

  useEffect(() => {
    if (url) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [url, connect, disconnect]);

  const send = useCallback((data) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return {
    isConnected,
    lastMessage,
    send,
    connect,
    disconnect,
  };
}

