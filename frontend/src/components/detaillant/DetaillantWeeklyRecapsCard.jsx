import { useEffect, useState } from 'react';
import { CalendarRange } from 'lucide-react';
import { detaillantAPI } from '../../services/api.detaillant';

// Historique des récaps hebdo du POP'S (ventes, followers, avis) semaine par semaine
export const DetaillantWeeklyRecapsCard = () => {
  const [recaps, setRecaps] = useState(null);
  useEffect(() => {
    detaillantAPI.weeklyRecaps().then((d) => setRecaps(d.recaps || [])).catch(() => setRecaps([]));
  }, []);
  if (!recaps || recaps.length === 0) return null;
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="dt-weekly-recaps-card">
      <h3 className="text-sm font-bold text-[#E9CF8E] mb-3 flex items-center gap-2">
        <CalendarRange className="w-4 h-4" /> Mes récaps hebdo ({recaps.length})
      </h3>
      <div className="space-y-1.5">
        {recaps.map((r) => (
          <div key={r.week_key} data-testid={`dt-recap-row-${r.week_key}`}
            className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-white/75 rounded-lg bg-white/[0.03] px-3 py-2">
            <span className="font-bold text-white/90 min-w-[110px]">Semaine {r.week_key}</span>
            <span>{r.sales_count} vente{r.sales_count > 1 ? 's' : ''}</span>
            <span className="font-bold text-[#E9CF8E]">{Number(r.revenue_eur || 0).toFixed(2)} €</span>
            <span>+{r.new_followers} follower{r.new_followers > 1 ? 's' : ''}</span>
            <span>{r.reviews_count} avis{r.rating_avg ? ` (★ ${r.rating_avg})` : ''}</span>
          </div>
        ))}
      </div>
      <p className="text-[10px] text-white/35 mt-2">Un email récap vous est envoyé chaque lundi.</p>
    </div>
  );
};
