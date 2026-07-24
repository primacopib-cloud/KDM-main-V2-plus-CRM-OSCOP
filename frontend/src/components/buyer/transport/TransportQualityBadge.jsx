import { useEffect, useState } from 'react';
import { Star } from 'lucide-react';
import { API, getAuthHeaders, getSessionToken } from '../../../services/http';

export const TransportQualityBadge = () => {
  const [q, setQ] = useState(null);

  useEffect(() => {
    fetch(`${API}/logiscop-transport/service-quality`, {
      credentials: 'include',
      headers: { Authorization: `Bearer ${getSessionToken()}`, ...getAuthHeaders() },
    }).then((r) => (r.ok ? r.json() : null)).then(setQ).catch(() => {});
  }, []);

  if (!q || !q.delivered) return null;
  return (
    <div className="rounded-xl px-4 py-2.5 bg-[#D9B35A]/[0.08] border border-[#D9B35A]/25 flex flex-wrap items-center gap-x-4 gap-y-1"
      data-testid="transport-quality-badge">
      <span className="text-[11px] font-bold text-[#E9CF8E] inline-flex items-center gap-1.5">
        Qualité de service LOGI'SCOP
      </span>
      {q.avg_rating !== null && (
        <span className="inline-flex items-center gap-1 text-[12px] font-bold text-[#E9CF8E]" data-testid="quality-avg-rating">
          <Star size={13} fill="currentColor" /> {q.avg_rating}/5
          <span className="font-normal text-white/40 text-[10px]">({q.ratings_count} avis)</span>
        </span>
      )}
      <span className="text-[11px] text-white/60">{q.delivered} livraison(s) réalisée(s)</span>
      {q.on_time_rate !== null && (
        <span className="text-[11px] text-emerald-300 font-semibold">{q.on_time_rate} % à l'heure</span>
      )}
    </div>
  );
};
