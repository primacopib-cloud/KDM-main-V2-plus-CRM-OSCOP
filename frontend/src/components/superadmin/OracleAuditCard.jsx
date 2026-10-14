import { useEffect, useState } from 'react';
import { ShieldCheck, RefreshCw } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const STATUS_STYLE = {
  EXECUTED: 'text-emerald-300 bg-emerald-500/15 border-emerald-400/40',
  FAILED: 'text-red-300 bg-red-500/15 border-red-400/40',
};

export const OracleAuditCard = () => {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = () => {
    setBusy(true);
    fetch(`${API}/oracle-admin/audit`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setItems(d?.audit || []))
      .catch(() => {})
      .finally(() => setBusy(false));
  };
  useEffect(load, []);

  return (
    <div className="rounded-2xl border border-[#D9B35A]/25 bg-white/[0.02] p-4 mt-4" data-testid="oracle-audit-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-[#E9CF8E] flex items-center gap-2">
          <ShieldCheck size={15} /> Journal d'audit — Oracle Admin exécutif
        </h3>
        <button type="button" onClick={load} data-testid="oracle-audit-refresh"
          className="p-1.5 rounded-lg text-white/40 hover:text-[#E9CF8E] transition-colors">
          <RefreshCw size={13} className={busy ? 'animate-spin' : ''} />
        </button>
      </div>
      {items.length === 0 ? (
        <p className="text-[11px] text-white/40" data-testid="oracle-audit-empty">
          Aucune action exécutée par Oracle pour le moment — dictez une commande depuis le panneau Oracle.
        </p>
      ) : (
        <div className="space-y-1.5 max-h-72 overflow-y-auto">
          {items.map((a) => (
            <div key={a.id} className="rounded-lg border border-white/[0.07] bg-white/[0.02] px-3 py-2"
              data-testid={`oracle-audit-row-${a.id}`}>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${STATUS_STYLE[a.status] || 'text-white/60 border-white/20'}`}>
                  {a.status === 'EXECUTED' ? 'Exécutée' : 'Échec'}
                </span>
                <span className="text-[11px] font-semibold text-white/80">{a.label}</span>
                <span className="ml-auto text-[9.5px] text-white/35">
                  {new Date(a.created_at).toLocaleString('fr-FR')} · {a.admin_email}
                </span>
              </div>
              <p className="text-[10.5px] text-white/55 mt-0.5">{a.summary}</p>
              {a.result && <p className="text-[10px] text-white/40 italic">{a.result}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
