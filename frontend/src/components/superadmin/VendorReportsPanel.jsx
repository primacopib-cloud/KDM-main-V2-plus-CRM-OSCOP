import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Mail, RefreshCw, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const VendorReportsPanel = () => {
  const [reports, setReports] = useState([]);
  const [resending, setResending] = useState('');
  const [sendingAll, setSendingAll] = useState(false);

  const refresh = useCallback(async () => {
    const r = await fetch(`${API}/admin/vendor-reports/history`, { credentials: 'include' });
    if (r.ok) setReports((await r.json()).reports || []);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const resend = async (vendorId) => {
    setResending(vendorId);
    try {
      const r = await fetch(`${API}/admin/vendor-reports/resend/${vendorId}`, { method: 'POST', credentials: 'include' });
      const d = await r.json();
      if (r.ok) { toast.success(`Rapport renvoyé à ${d.email}`); refresh(); }
      else toast.error(d.detail || 'Erreur');
    } finally {
      setResending('');
    }
  };

  const sendAll = async () => {
    setSendingAll(true);
    try {
      const r = await fetch(`${API}/admin/vendor-reports/send?force=true`, { method: 'POST', credentials: 'include' });
      const d = await r.json();
      toast.success(`${d.sent} rapport(s) envoyé(s)`);
      refresh();
    } finally {
      setSendingAll(false);
    }
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="vendor-reports-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-display text-lg text-[#1F2A3A] flex items-center gap-2">
          <Mail size={15} className="text-[#5B2E8C]" /> Rapports mensuels vendeurs
        </h3>
        <button type="button" onClick={sendAll} disabled={sendingAll}
          data-testid="reports-send-all-btn"
          className="btn-gold h-8 px-3 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 disabled:opacity-40">
          {sendingAll ? <Loader2 size={12} className="animate-spin" /> : <Mail size={12} />} Envoyer à tous
        </button>
      </div>
      <p className="text-[11px] opacity-50 mb-3">
        Envoi automatique le 1er de chaque mois (vues des spots, meilleur spot, commandes, CA).
      </p>
      <div className="divide-y divide-black/5 max-h-72 overflow-y-auto">
        {reports.map((r) => (
          <div key={r.id} className="flex items-center justify-between gap-2 py-2" data-testid={`report-row-${r.id}`}>
            <div className="min-w-0">
              <p className="text-sm font-medium text-[#1F2A3A] truncate">
                {r.vendor_name || r.email} <span className="text-[10px] opacity-50">— {r.month}</span>
                {r.resent && <span className="text-[9px] uppercase ml-1.5 px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-600">renvoyé</span>}
              </p>
              <p className="text-[11px] opacity-50">
                {new Date(r.sent_at).toLocaleString('fr-FR')} · {r.stats?.spots ?? 0} spots · {r.stats?.total_views ?? 0} vues · {r.stats?.revenue ?? 0} € HT
              </p>
            </div>
            <button type="button" onClick={() => resend(r.vendor_id)} disabled={resending === r.vendor_id}
              data-testid={`report-resend-${r.vendor_id}`}
              className="shrink-0 h-8 px-3 rounded-lg text-xs border border-black/10 hover:border-[#5B2E8C]/40 hover:text-[#5B2E8C] inline-flex items-center gap-1.5 disabled:opacity-40">
              {resending === r.vendor_id ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />} Renvoyer
            </button>
          </div>
        ))}
        {reports.length === 0 && <p className="text-sm opacity-50 py-3">Aucun rapport envoyé pour le moment.</p>}
      </div>
    </div>
  );
};
