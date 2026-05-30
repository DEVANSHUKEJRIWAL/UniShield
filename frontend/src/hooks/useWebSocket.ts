"use client";

import { useEffect, useRef, useState } from "react";

interface UseWebSocketOptions {
  onMessage?: (data: unknown) => void;
  reconnectInterval?: number;
}

export function useWebSocket(url: string | null, options: UseWebSocketOptions = {}) {
  const { onMessage, reconnectInterval = 5000 } = options;
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!url) return;

    const connect = () => {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, reconnectInterval);
      };
      ws.onmessage = (event) => {
        try {
          onMessage?.(JSON.parse(event.data));
        } catch {
          onMessage?.(event.data);
        }
      };
    };

    connect();
    return () => wsRef.current?.close();
  }, [url, onMessage, reconnectInterval]);

  return { connected, ws: wsRef.current };
}
