import { useEffect, useState } from 'react';
import { Ticket, Download, MapPin } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const STATUS_COLORS = { NEW: '#60A5FA', CONTACTED: '#D9B35A', ACTIVATED: '#7BC94E' };

export const PassRegistrationsPanel = () => {
  const [data, setData] = useState(null);
  const opts = { headers: getAuthHeaders(), credentials: 'include' };

  const load = () => {
    fetch(`${API}/admin/pass-registrations`, opts)
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => {});
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, []);

  const setStatus = async (id, status) => {
    const r = await fetch(`${API}/admin/pass-registrations/${id}`, {
      ...opts, method: 'PATCH',
      headers: { ...opts.headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (r.ok) { toast.success('Statut mis à jour'); load(); } else { toast.error('Mise à jour impossible'); }
  };

  const exportCsv = async () => {
    try {
      const r = await fetch(`${API}/admin/pass-registrations/export`, opts);
      if (!r.ok) throw new Error('Export impossible');
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement('a');
      a.href = url;
      a.download = `inscriptions-pass-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(e.message); }
  };

  if (!data) return null;
  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mt-6" data-testid="pass-registrations-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#D9B35A] flex items-center gap-2">
          <Ticket className="w-4 h-4" /> Inscriptions PASS LOLODRIVE
          <span className="text-[11px] text-white/45 font-normal">({data.registrations.length})</span>
        </h3>
        <button type="button" onClick={exportCsv} data-testid="export-pass-csv-btn"
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10.5px] font-bold bg-white/10 text-[#E9CF8E] hover:bg-white/15 transition-colors">
          <Download className="w-3 h-3" /> Export CSV
        </button>
      </div>
      {data.registrations.length === 0 ? (
        <p className="text-xs text-white/45">Aucune inscription PASS pour le moment.</p>
      ) : (
        <div className="space-y-1.5 max-h-[420px] overflow-y-auto pr-1">
          {data.registrations.map((r) => (
            <div key={r.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] py-1.5 border-b border-white/5 last:border-0" data-testid={`pass-reg-${r.id}`}>
              <span className="text-white/35 w-16">{String(r.created_at || '').slice(0, 10)}</span>
              <span className="font-semibold text-white/80 min-w-[120px]">{r.first_name} {r.last_name}</span>
              <span className="text-white/55">{r.email}</span>
              <span className="text-white/45">{r.phone}</span>
              <span className="text-white/45">{r.postal_code} {r.city}</span>
              {r.relay?.name && (
                <span className="inline-flex items-center gap-1 text-[#E9CF8E]"><MapPin className="w-3 h-3" />{r.relay.name}</span>
              )}
              <select value={r.status} onChange={(e) => setStatus(r.id, e.target.value)} data-testid={`pass-status-${r.id}`}
                className="ml-auto h-7 rounded-md px-1.5 text-[10.5px] font-bold bg-white/[0.06] border focus:outline-none"
                style={{ color: STATUS_COLORS[r.status] || '#fff', borderColor: `${STATUS_COLORS[r.status] || '#fff'}55`, colorScheme: 'dark' }}>
                {Object.entries(data.statuses).map(([k, v]) => (
                  <option key={k} value={k} style={{ background: '#2A1045', color: '#fff' }}>{v}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
