import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCheck } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders, getSessionToken } from '../services/http';

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const fmt = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '');

export const NotificationsBell = ({ className = '' }) => {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const wsRef = useRef(null);
  const navigate = useNavigate();
  const rawUser = localStorage.getItem('user');
  const userId = (() => { try { return JSON.parse(rawUser || 'null')?.id; } catch { return null; } })();

  const load = () => fetch(`${BACKEND}/api/notifications/mine?limit=15`,
    { credentials: 'include', headers: getAuthHeaders() })
    .then((r) => (r.ok ? r.json() : null)).then((d) => d && setData(d)).catch(() => {});

  useEffect(() => {
    if (!rawUser) return undefined;
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rawUser]);

  // Temps réel : nouvelle notification → badge + toast sans recharger
  useEffect(() => {
    if (!userId) return undefined;
    let closedByUs = false;
    const connect = () => {
      const token = getSessionToken() || '';
      const ws = new WebSocket(`${BACKEND.replace(/^http/, 'ws')}/api/notifications/ws/${userId}${token ? `?token=${token}` : ''}`);
      wsRef.current = ws;
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'notification') {
            const n = msg.data || msg.notification || {};
            toast(n.title || 'Nouvelle notification', {
              description: n.message, duration: 8000,
              action: { label: 'Voir', onClick: () => navigate('/notifications') },
            });
            load();
          }
        } catch { /* ping/pong */ }
      };
      ws.onclose = () => { if (!closedByUs) setTimeout(connect, 15000); };
    };
    connect();
    return () => { closedByUs = true; wsRef.current?.close(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  useEffect(() => {
    const onClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  if (!rawUser || !data) return null;
  const unread = data.unread_count || 0;
  const items = data.items || [];

  const markAllRead = () => {
    fetch(`${BACKEND}/api/notifications/mine-read-all`, { method: 'PUT', credentials: 'include', headers: getAuthHeaders() })
      .then(load)
      .then(() => toast.success('Toutes les notifications sont marquées comme lues'))
      .catch(() => {});
  };

  return (
    <div className={`relative ${className}`} ref={ref}>
      <button type="button" onClick={() => setOpen((o) => !o)} data-testid="notifications-bell"
        className="relative p-2 rounded-lg hover:bg-white/[0.06] transition-colors"
        title="Notifications">
        <Bell className="w-4 h-4 text-white/70" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center" data-testid="notifications-bell-count">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto rounded-xl border border-white/15 bg-[#2c1247] shadow-2xl z-[70] p-2"
          data-testid="notifications-bell-dropdown">
          <div className="flex items-center justify-between px-2 py-1.5">
            <p className="text-xs font-bold text-white/80">Notifications</p>
            {unread > 0 && (
              <button type="button" onClick={markAllRead} data-testid="notifications-bell-mark-all"
                className="inline-flex items-center gap-1 text-[10px] font-bold text-[#D9B35A] hover:underline">
                <CheckCheck className="w-3.5 h-3.5" /> Tout lu
              </button>
            )}
          </div>
          {items.length === 0 ? (
            <p className="text-xs text-white/40 px-2 py-4 text-center">Aucune notification.</p>
          ) : items.slice(0, 8).map((n) => (
            <button key={n.id} type="button"
              onClick={() => { setOpen(false); navigate('/notifications'); }}
              className={`w-full text-left rounded-lg px-2 py-2 text-xs transition-colors ${n.is_read ? 'text-white/45 hover:bg-white/5' : 'text-white bg-[#D9B35A]/[0.08] hover:bg-[#D9B35A]/[0.14]'}`}>
              <p className="font-semibold line-clamp-1">{n.title}</p>
              <p className="line-clamp-2 mt-0.5 opacity-80">{n.message}</p>
              <p className="text-[9px] text-white/30 mt-1">{fmt(n.created_at)}</p>
            </button>
          ))}
          <button type="button" onClick={() => { setOpen(false); navigate('/notifications'); }}
            data-testid="notifications-bell-see-all"
            className="w-full mt-1 py-2 rounded-lg text-xs font-bold text-[#1F0A33]" style={{ background: '#D9B35A' }}>
            Voir toutes mes notifications
          </button>
        </div>
      )}
    </div>
  );
};
