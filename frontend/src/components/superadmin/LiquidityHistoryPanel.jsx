import { useEffect, useState } from 'react';
import { Activity, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

export const LiquidityHistoryPanel = () => {
  const [items, setItems] = useState([]);

  useEffect(() => {
    fetch(`${API}/admin/liquidity/history`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);

  if (!items.length) return null;
  return (
    <div className="glass-panel-soft rounded-[14px] p-4" data-testid="liquidity-history-panel">
      <h3 className="text-xs font-bold text-white/70 uppercase mb-3 flex items-center gap-1.5">
        <Activity className="w-3.5 h-3.5" /> Historique de liquidité — fournisseurs éligibles par catégorie
      </h3>
      <div className="space-y-1.5">
        {items.map((it) => {
          const Trend = it.trend > 0 ? TrendingUp : it.trend < 0 ? TrendingDown : Minus;
          const color = it.trend > 0 ? 'text-emerald-400' : it.trend < 0 ? 'text-red-400' : 'text-white/40';
          const max = Math.max(...it.series.map((s) => s.eligible_vendors), 1);
          return (
            <div key={it.category} className="flex flex-wrap items-center gap-2 text-xs py-1.5 border-b border-white/5 last:border-0" data-testid={`liquidity-row-${it.category}`}>
              <span className="w-40 truncate text-white/85 font-semibold">{it.category}</span>
              <span className="font-bold text-[#E9CF8E] w-8 text-right">{it.current}</span>
              <span className={`inline-flex items-center gap-0.5 font-bold w-14 ${color}`}>
                <Trend className="w-3 h-3" /> {it.trend > 0 ? `+${it.trend}` : it.trend}
              </span>
              <span className="flex items-end gap-[2px] h-6 flex-1 min-w-[120px]" title={it.series.map((s) => `${s.day}: ${s.eligible_vendors}`).join('\n')}>
                {it.series.map((s) => (
                  <span key={s.day} className="w-1.5 rounded-t-sm bg-[#D9B35A]/60"
                    style={{ height: `${Math.max(15, (s.eligible_vendors / max) * 100)}%` }} />
                ))}
              </span>
              <span className="text-white/40">
                {it.current <= 1 ? 'Négociation directe' : it.current === 2 ? 'Offre scellée' : 'Enchère possible'}
              </span>
            </div>
          );
        })}
      </div>
      <p className="text-[10px] text-white/35 mt-2">Un relevé automatique par jour — planifiez vos campagnes quand la concurrence est suffisante.</p>
    </div>
  );
};
