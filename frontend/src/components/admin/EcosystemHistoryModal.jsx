import i18n from '@/i18n';
import { useState, useEffect, useCallback } from 'react';
import { X, History, ArrowDownCircle, ArrowUpCircle, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmtDate = (iso) => {
  try {
    return new Date(iso).toLocaleString(i18n.language, { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch (_e) { return iso; }
};

export const EcosystemHistoryModal = ({ app, onClose }) => {
  const [events, setEvents] = useState(null);

  const fetchHistory = useCallback(async () => {
    const r = await fetch(`${API}/connectors/health-history?name=${encodeURIComponent(app.name)}&limit=50`, { credentials: 'include' });
    setEvents(r.ok ? (await r.json()).events || [] : []);
  }, [app.name]);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
      data-testid="eco-history-modal"
    >
      <div
        className="rounded-[20px] p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        style={{ background: '#FFFFFF', boxShadow: '0 24px 64px rgba(76,42,110,0.25)' }}
      >
        <div className="flex items-start justify-between mb-1">
          <h3 className="font-display text-lg flex items-center gap-2 text-[#1F2A3A]">
            <History size={16} style={{ color: '#D9B35A' }} />
            {i18n.t('adm.eco_history_title')}
          </h3>
          <button type="button" onClick={onClose} data-testid="eco-history-close" className="opacity-50 hover:opacity-100 p-1">
            <X size={18} />
          </button>
        </div>
        <p className="text-xs opacity-60 mb-4">{app.label}</p>

        {events === null ? (
          <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-[#D9B35A]" /></div>
        ) : events.length === 0 ? (
          <p className="text-sm opacity-50 text-center py-6" data-testid="eco-history-empty">{i18n.t('adm.eco_history_empty')}</p>
        ) : (
          <div className="relative pl-5" data-testid="eco-history-timeline">
            <div className="absolute left-[7px] top-1 bottom-1 w-px bg-black/10" />
            {events.map((e) => {
              const down = e.to_status === 'ERROR';
              const color = down ? '#E64432' : '#6FA82E';
              const Icon = down ? ArrowDownCircle : ArrowUpCircle;
              return (
                <div key={e.id} className="relative mb-4" data-testid={`eco-history-event-${e.id}`}>
                  <Icon size={15} className="absolute -left-5 top-0.5 bg-white rounded-full" style={{ color }} />
                  <p className="text-sm font-medium" style={{ color }}>
                    {down ? i18n.t('adm.eco_down') : i18n.t('adm.eco_recovered')}
                  </p>
                  <p className="text-xs opacity-60">{fmtDate(e.at)}</p>
                  {e.error && <p className="text-[11px] opacity-50 mt-0.5 break-all">{e.error}</p>}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
