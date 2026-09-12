import { useEffect, useState } from 'react';
import { MousePointerClick } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export const ClickCounterWidget = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/cpc/me/click-counter`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data) return null;
  const pct = Math.min(100, (data.count / data.threshold) * 100);
  const premium = data.count >= data.threshold;
  return (
    <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-4" data-testid="click-counter-widget">
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs text-white/50 flex items-center gap-1.5">
          <MousePointerClick className="w-3.5 h-3.5 text-[#D9B35A]" />
          Actions facturées ce mois-ci
        </p>
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${premium ? 'bg-red-500/20 text-red-300' : 'bg-emerald-500/15 text-emerald-300'}`}
          data-testid="click-counter-rate">
          Tarif en cours : {data.current_rate} CREDI'SCOP / action
        </span>
      </div>
      <p className="text-2xl font-bold text-white" data-testid="click-counter-count">
        {data.count} <span className="text-xs font-semibold text-white/40">/ {data.threshold} avant passage à {data.premium_rate} crédits</span>
      </p>
      <div className="mt-2 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div className={`h-full rounded-full ${premium ? 'bg-red-400' : 'bg-[#D9B35A]'}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};
