import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Bell, BellOff, Check, CheckCheck, Loader2, PhoneCall } from 'lucide-react';
import { toast } from 'sonner';
import { lolodriveAPI } from '../services/api';
import { BackLink } from '../components/BackLink';
import { NOTIF_CATEGORIES, classifyNotif } from '../utils/notifCategories';

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' }) : '');

const FILTERS = [{ key: 'all', label: 'Toutes' }, ...NOTIF_CATEGORIES];
const classify = (n) => classifyNotif(n.type);

export default function NotificationsPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState('all');

  const load = useCallback(() => {
    fetch(`${API}/api/notifications/mine`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { items: [], unread_count: 0 }))
      .then(setData)
      .catch(() => setData({ items: [], unread_count: 0 }));
  }, []);
  useEffect(() => { load(); }, [load]);

  const markRead = async (id) => {
    await fetch(`${API}/api/notifications/mine/${id}/read`, { method: 'PUT', credentials: 'include' });
    load();
  };
  const markAll = async () => {
    const r = await fetch(`${API}/api/notifications/mine-read-all`, { method: 'PUT', credentials: 'include' });
    const d = await r.json();
    toast.success(`${d.count} notification(s) marquée(s) comme lue(s)`);
    load();
  };
  const open = async (n) => {
    if (!n.is_read) await markRead(n.id);
    if (n.data?.link) navigate(n.data.link);
  };

  return (
    <div className="min-h-screen bg-[#1F0A33] text-white">
      <header className="max-w-3xl mx-auto px-5 pt-6 flex items-center justify-between">
        <BackLink data-testid="notifications-back-link">
          <ArrowLeft className="w-3.5 h-3.5" /> Retour
        </BackLink>
        {data?.unread_count > 0 && (
          <button type="button" onClick={markAll} data-testid="notifications-mark-all-btn"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-[#D9B35A] text-[#1F0A33]">
            <CheckCheck className="w-4 h-4" /> Tout marquer comme lu
          </button>
        )}
      </header>
      <main className="max-w-3xl mx-auto px-5 py-6">
        <h1 className="text-2xl font-bold mb-1 flex items-center gap-2" data-testid="notifications-title">
          <Bell className="w-6 h-6 text-[#D9B35A]" /> Mes notifications
          {data?.unread_count > 0 && (
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-red-500/20 text-red-300" data-testid="notifications-unread-count">
              {data.unread_count} non lue{data.unread_count > 1 ? 's' : ''}
            </span>
          )}
        </h1>
        <p className="text-sm text-white/50 mb-4">Coop'Acts battus, stock bas, promos, retours en stock…</p>
        <div className="flex flex-wrap gap-2 mb-6" data-testid="notifications-filters">
          {FILTERS.map((f) => {
            const count = f.key === 'all'
              ? (data?.items.length || 0)
              : (data?.items || []).filter((n) => classify(n) === f.key).length;
            return (
              <button key={f.key} type="button" onClick={() => setFilter(f.key)}
                data-testid={`notifications-filter-${f.key}`}
                className={`px-3 py-1.5 rounded-full text-xs font-bold transition-colors ${filter === f.key
                  ? 'bg-[#D9B35A] text-[#1F0A33]'
                  : 'bg-white/[0.06] text-white/60 hover:bg-white/[0.12]'}`}>
                {f.label}{count > 0 ? ` (${count})` : ''}
              </button>
            );
          })}
        </div>
        {!data ? (
          <Loader2 className="w-6 h-6 animate-spin text-white/40" />
        ) : data.items.length === 0 ? (
          <div className="text-center py-16 text-white/40" data-testid="notifications-empty">
            <BellOff className="w-12 h-12 mx-auto mb-3 opacity-40" />
            <p>Aucune notification pour le moment.</p>
          </div>
        ) : (() => {
          const filtered = data.items.filter((n) => filter === 'all' || classify(n) === filter);
          return filtered.length === 0 ? (
            <div className="text-center py-16 text-white/40" data-testid="notifications-filter-empty">
              <BellOff className="w-12 h-12 mx-auto mb-3 opacity-40" />
              <p>Aucune notification dans cette catégorie.</p>
            </div>
          ) : (
          <div className="space-y-2" data-testid="notifications-list">
            {filtered.map((n) => (
              <button key={n.id} type="button" onClick={() => open(n)}
                data-testid={`notification-item-${n.id}`}
                className={`w-full text-left rounded-xl border p-4 transition-colors ${n.is_read
                  ? 'border-white/[0.06] bg-white/[0.02] text-white/55'
                  : 'border-[#D9B35A]/30 bg-[#D9B35A]/[0.06] text-white hover:bg-[#D9B35A]/[0.1]'}`}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold flex items-center gap-2">
                      {!n.is_read && <span className="w-2 h-2 rounded-full bg-[#D9B35A] shrink-0" />}
                      {n.title}
                    </p>
                    <p className="text-xs mt-1 leading-relaxed">{n.message}</p>
                    {n.type === 'lolodrive_ready_sms_failed' && !n.is_read && n.data?.order_id && (
                      <span
                        onClick={async (e) => {
                          e.stopPropagation();
                          try {
                            await lolodriveAPI.managerSmsFollowupDone(n.data.order_id);
                            toast.success('Suivi clôturé : client appelé ✓');
                            markRead(n.id);
                          } catch (err) {
                            toast.error(err.message);
                          }
                        }}
                        data-testid={`sms-followup-done-${n.data.order_id}`}
                        className="mt-2 inline-flex items-center gap-1 px-2.5 h-6 rounded-full text-[10px] font-bold text-emerald-300 border border-emerald-400/40 bg-emerald-500/10 hover:bg-emerald-500/20 cursor-pointer">
                        <PhoneCall className="w-3 h-3" /> Client appelé — clore le suivi
                      </span>
                    )}
                    <p className="text-[10px] text-white/35 mt-2">{fmt(n.created_at)}</p>
                  </div>
                  {!n.is_read && (
                    <span onClick={(e) => { e.stopPropagation(); markRead(n.id); }}
                      data-testid={`notification-read-btn-${n.id}`} title="Marquer comme lu"
                      className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 shrink-0 cursor-pointer">
                      <Check className="w-4 h-4" />
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
          );
        })()}
      </main>
    </div>
  );
}
