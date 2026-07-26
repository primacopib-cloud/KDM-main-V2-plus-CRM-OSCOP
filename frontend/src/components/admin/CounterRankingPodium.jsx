import { useEffect, useState } from 'react';
import { Trophy } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

const RANK_STYLE = {
  1: { color: '#D9B35A', bg: 'rgba(217,179,90,0.15)', border: 'rgba(217,179,90,0.4)' },
  2: { color: '#c0c4cc', bg: 'rgba(192,196,204,0.12)', border: 'rgba(192,196,204,0.35)' },
  3: { color: '#cd8a4e', bg: 'rgba(205,138,78,0.12)', border: 'rgba(205,138,78,0.35)' },
};

export const CounterRankingPodium = () => {
  const [data, setData] = useState(null);
  useEffect(() => {
    lolodriveAPI.adminCounterRanking().then(setData).catch(() => {});
  }, []);
  if (!data || data.ranking.length === 0) return null;
  const label = new Date(`${data.month}-01`).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
  return (
    <div className="mt-3 rounded-xl border border-white/[0.08] bg-white/[0.02] px-3 py-2.5" data-testid="counter-ranking-podium">
      <p className="text-[11px] uppercase tracking-wider text-white/40 mb-2 flex items-center gap-1.5">
        <Trophy className="w-3.5 h-3.5 text-[#D9B35A]" /> Podium caisses relais — {label}
      </p>
      <div className="space-y-1">
        {data.ranking.slice(0, 5).map((r) => {
          const st = RANK_STYLE[r.rank] || { color: 'rgba(255,255,255,0.5)', bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.1)' };
          return (
            <div key={r.point_id} className="flex items-center gap-2 text-xs" data-testid={`podium-rank-${r.rank}`}>
              <span className="w-5 h-5 rounded-full flex items-center justify-center font-black text-[11px] shrink-0"
                style={{ color: st.color, background: st.bg, border: `1px solid ${st.border}` }}>
                {r.rank}
              </span>
              <span className="truncate">{r.code} — {r.name}{r.city ? ` (${r.city})` : ''}</span>
              <span className="ml-auto font-mono shrink-0 text-white/70">
                {r.count} vente{r.count > 1 ? 's' : ''} · <b style={{ color: st.color }}>{(r.total_cents / 100).toFixed(2)} €</b>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
