import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCheck } from 'lucide-react';
import { toast } from 'sonner';
import { apiCall } from '../services/http';

export const NotificationsBell = ({ className = '' }) => {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();
  const isLoggedIn = !!localStorage.getItem('user');

  useEffect(() => {
    if (!isLoggedIn) return undefined;
    let active = true;
    const load = () => apiCall('/notifications?limit=15').then((d) => {
      if (!active) return;
      setData((prev) => {
        if (prev) {
          const known = new Set((prev.notifications || []).map((n) => n.id));
          (d.notifications || []).filter((n) => !n.is_read && !known.has(n.id)).forEach((n) => {
            toast(n.title, { description: n.message, duration: 8000 });
          });
        }
        return d;
      });
    }).catch(() => {});
    load();
    const interval = setInterval(load, 60000);
    return () => { active = false; clearInterval(interval); };
  }, [isLoggedIn]);

  useEffect(() => {
    const onClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  if (!isLoggedIn || !data) return null;
  const unread = data.unread_count || 0;

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next && unread > 0) {
      apiCall('/notifications/read-all', { method: 'POST' })
        .then(() => apiCall('/notifications?limit=15').then(setData))
        .catch(() => {});
    }
  };

  return (
    <div className={`relative ${className}`} ref={ref}>
      <button type="button" onClick={toggle} data-testid="notifications-bell"
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
        <div className="absolute right-0 top-full mt-2 w-80 max-h-96 overflow-y-auto rounded-2xl z-50 shadow-2xl"
          style={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.3)' }} data-testid="notifications-dropdown">
          <div className="px-4 py-2.5 border-b border-white/10 flex items-center justify-between">
            <p className="text-xs font-bold text-white">Notifications</p>
            <CheckCheck className="w-3.5 h-3.5 text-white/40" />
          </div>
          {!(data.notifications || []).length && (
            <p className="px-4 py-6 text-xs text-white/40 text-center">Aucune notification.</p>
          )}
          {(data.notifications || []).map((n) => (
            <button key={n.id} type="button" data-testid={`notification-item-${n.id}`}
              onClick={() => { setOpen(false); if (n.data?.link) navigate(n.data.link); }}
              className={`w-full text-left px-4 py-2.5 border-b border-white/5 last:border-0 hover:bg-white/[0.05] transition-colors ${n.is_read ? 'opacity-60' : ''}`}>
              <p className="text-xs font-semibold text-[#E9CF8E]">{n.title}</p>
              <p className="text-[11px] text-white/65 mt-0.5">{n.message}</p>
              <p className="text-[10px] text-white/35 mt-0.5">{String(n.created_at || '').slice(0, 16).replace('T', ' ')}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
