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
  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mb-4" data-testid="cta-stats-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#D9B35A] flex items-center gap-2">
          <MousePointerClick className="w-4 h-4" /> Clics sur les boutons d'adhésion
        </h3>
        <span className="text-[11px] text-white/45" data-testid="cta-total-clicks">{data.total_clicks} clics au total</span>
      </div>
      {data.total_clicks === 0 ? (
        <p className="text-xs text-white/45">Aucun clic enregistré pour le moment.</p>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center gap-3 text-[10px] uppercase tracking-wider text-white/35">
            <span className="flex-1">Bouton</span>
            <span className="w-12 text-right">7 j</span>
            <span className="w-12 text-right">30 j</span>
            <span className="w-14 text-right">Total</span>
          </div>
          {data.stats.map((s) => (
            <div key={s.cta_id} className="flex items-center gap-3" data-testid={`cta-stat-${s.cta_id}`}>
              <div className="flex-1 min-w-0">
                <div className="text-[11px] text-white/70 truncate">{s.label}</div>
                <div className="h-1.5 rounded bg-white/[0.05] mt-1 overflow-hidden">
                  <div className="h-full rounded" style={{ width: `${Math.max((s.total / max) * 100, 2)}%`, background: 'linear-gradient(90deg,#D9B35A,#b8933e)' }} />
                </div>
              </div>
              <span className="w-12 text-right text-[11px] text-white/55">{s.last7}</span>
              <span className="w-12 text-right text-[11px] text-white/55">{s.last30}</span>
              <span className="w-14 text-right text-[12px] font-bold text-[#E9CF8E]">{s.total}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
