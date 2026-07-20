import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus, BrainCircuit } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const panel = 'bg-white/[0.04] border border-white/[0.08] rounded-2xl';

const TREND = {
  up: { icon: TrendingUp, cls: 'text-emerald-400', label: 'En hausse' },
  down: { icon: TrendingDown, cls: 'text-red-400', label: 'En baisse' },
  stable: { icon: Minus, cls: 'text-white/50', label: 'Stable' },
};

export const DemandForecast = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/buyer-tools/demand-forecast`, { credentials: 'include' })
      .then((r) => r.json()).then(setData).catch(() => {});
  }, []);

  const cats = data?.categories || [];
  return (
    <div className={`${panel} p-5`} data-testid="demand-forecast">
      <h3 className="font-semibold text-white mb-1 flex items-center gap-2">
        <BrainCircuit className="w-4 h-4 text-[#D9B35A]" /> Prévision de demande par catégorie
      </h3>
      <p className="text-[11px] text-white/40 mb-4">{data?.method || 'Basée sur les consultations lancées ces 6 derniers mois.'}</p>
      {!cats.length && <p className="text-xs text-white/40">Pas encore assez d'historique de consultations pour établir une prévision.</p>}
      <div className="space-y-3">
        {cats.map((cat) => {
          const T = TREND[cat.trend] || TREND.stable;
          const max = Math.max(...cat.series, cat.forecast_next_month, 1);
          return (
            <div key={cat.category} className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]" data-testid={`forecast-cat-${cat.category}`}>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className="text-sm font-bold text-white capitalize flex-1 min-w-[120px]">{cat.category}</span>
                <span className={`inline-flex items-center gap-1 text-[11px] font-bold ${T.cls}`}><T.icon className="w-3.5 h-3.5" /> {T.label}</span>
                <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold bg-[#D9B35A]/15 text-[#E9CF8E]" data-testid={`forecast-next-${cat.category}`}>
                  Prévision mois prochain : {cat.forecast_next_month} lot(s)
                </span>
              </div>
              <div className="flex items-end gap-1.5 h-16">
                {cat.series.map((v, i) => (
                  <div key={cat.months[i]} className="flex-1 flex flex-col items-center gap-0.5">
                    <span className="text-[9px] text-white/50">{v}</span>
                    <div className="w-full rounded-t bg-white/15" style={{ height: `${Math.max(4, (v / max) * 44)}px` }} />
                    <span className="text-[8px] text-white/35">{cat.months[i].slice(5)}</span>
                  </div>
                ))}
                <div className="flex-1 flex flex-col items-center gap-0.5">
                  <span className="text-[9px] font-bold text-[#E9CF8E]">{cat.forecast_next_month}</span>
                  <div className="w-full rounded-t border border-dashed border-[#D9B35A]/60 bg-[#D9B35A]/20"
                    style={{ height: `${Math.max(4, (cat.forecast_next_month / max) * 44)}px` }} />
                  <span className="text-[8px] text-[#E9CF8E]">prévu</span>
                </div>
              </div>
              <p className="text-[10px] text-white/40 mt-1.5">{cat.total_6m} lot(s) sur 6 mois · {cat.avg_participants} participant(s) en moyenne par lot</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
