import { useEffect, useRef, useState } from 'react';

const PING_INTERVAL_MS = 25000;
const RECONNECT_DELAY_MS = 3000;

/**
 * Connect to the backend WebSocket /api/ws/notifications endpoint.
 * onMessage receives parsed JSON messages.
 * `enabled=false` disconnects.
 */
export default function useLolodriveWebSocket({ isAdmin = false, userId = null, enabled = true, onMessage }) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const pingTimerRef = useRef(null);
  const onMessageRef = useRef(onMessage);

  useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      const httpUrl = process.env.REACT_APP_BACKEND_URL || window.location.origin;
      const wsBase = httpUrl.replace(/^http/, 'ws');
      const params = new URLSearchParams();
      if (userId) params.append('user_id', userId);
      if (isAdmin) params.append('is_admin', 'true');
      const url = `${wsBase}/api/ws/notifications?${params.toString()}`;

      let ws;
      try {
        ws = new WebSocket(url);
      } catch {
        scheduleReconnect();
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        // Periodic ping
        pingTimerRef.current = setInterval(() => {
          try { ws.send(JSON.stringify({ type: 'ping' })); } catch { /* ignore */ }
        }, PING_INTERVAL_MS);
      };
      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          onMessageRef.current?.(data);
        } catch { /* ignore */ }
      };
      ws.onerror = () => {
        // Will trigger onclose
      };
      ws.onclose = () => {
        setConnected(false);
        if (pingTimerRef.current) clearInterval(pingTimerRef.current);
        scheduleReconnect();
      };
    };

    const scheduleReconnect = () => {
      if (cancelled) return;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
    };

    connect();

    return () => {
      cancelled = true;
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        try { wsRef.current.close(); } catch { /* ignore */ }
      }
    };
  }, [enabled, isAdmin, userId]);

  return { connected };
}
