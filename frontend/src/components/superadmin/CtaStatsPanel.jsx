import { useEffect, useState } from 'react';
import { MousePointerClick } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

export const CtaStatsPanel = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/admin/cta-stats`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data) return null;
  const max = Math.max(...data.stats.map((s) => s.total), 1);

  const exportCsv = async () => {
    try {
      const r = await fetch(`${API}/admin/cta-stats/export`, { headers: getAuthHeaders(), credentials: 'include' });
      if (!r.ok) throw new Error('Export impossible');
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `conversion-cta-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mb-4" data-testid="cta-stats-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#D9B35A] flex items-center gap-2">
          <MousePointerClick className="w-4 h-4" /> Clics sur les boutons d'adhésion
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-white/45" data-testid="cta-total-clicks">{data.total_clicks} clics · {data.total_paid} adhésion(s) payée(s)</span>
          <button type="button" onClick={exportCsv} data-testid="export-cta-csv-btn"
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10.5px] font-bold bg-white/10 text-[#E9CF8E] hover:bg-white/15 transition-colors">
            <Download className="w-3 h-3" /> Export CSV
          </button>
        </div>
      </div>
      {data.total_clicks === 0 ? (
        <p className="text-xs text-white/45">Aucun clic enregistré pour le moment.</p>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center gap-3 text-[10px] uppercase tracking-wider text-white/35">
            <span className="flex-1">Bouton</span>
            <span className="w-10 text-right">7 j</span>
            <span className="w-10 text-right">30 j</span>
            <span className="w-12 text-right">Clics</span>
            <span className="w-14 text-right">Payées</span>
            <span className="w-12 text-right">Taux</span>
          </div>
          {data.stats.map((s) => (
            <div key={s.cta_id} className="flex items-center gap-3" data-testid={`cta-stat-${s.cta_id}`}>
              <div className="flex-1 min-w-0">
                <div className="text-[11px] text-white/70 truncate">{s.label}</div>
                <div className="h-1.5 rounded bg-white/[0.05] mt-1 overflow-hidden">
                  <div className="h-full rounded" style={{ width: `${Math.max((s.total / max) * 100, 2)}%`, background: 'linear-gradient(90deg,#D9B35A,#b8933e)' }} />
                </div>
              </div>
              <span className="w-10 text-right text-[11px] text-white/55">{s.last7}</span>
              <span className="w-10 text-right text-[11px] text-white/55">{s.last30}</span>
              <span className="w-12 text-right text-[12px] font-bold text-[#E9CF8E]">{s.total}</span>
              <span className="w-14 text-right text-[12px] font-bold text-[#7BC94E]" data-testid={`cta-paid-${s.cta_id}`}>{s.paid}</span>
              <span className="w-12 text-right text-[11px] text-white/70">{s.rate === null ? '—' : `${s.rate} %`}</span>
            </div>
          ))}
          <p className="text-[10px] text-white/35 pt-1">
            « Payées » = adhésions au paiement confirmé attribuées au dernier bouton cliqué (fenêtre de 24 h).
          </p>
        </div>
      )}
    </div>
  );
};
