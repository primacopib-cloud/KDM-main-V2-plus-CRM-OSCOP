import { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export const SuggestedPackCard = ({ onBuy }) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/cpc/me/suggested-pack`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data?.pack || data.monthly_spend <= 0) return null;
  const p = data.pack;
  return (
    <div className="rounded-2xl border border-[#D9B35A]/30 bg-[#D9B35A]/[0.06] p-4 flex flex-wrap items-center gap-4"
      data-testid="suggested-pack-card">
      <Sparkles className="w-6 h-6 text-[#D9B35A] shrink-0" />
      <div className="flex-1 min-w-[220px]">
        <p className="text-sm font-bold text-white">
          Pack conseillé : {p.label} — {p.credits} CREDI'SCOP ({(p.price_ht_cents / 100).toFixed(2).replace('.', ',')} € HT)
        </p>
        <p className="text-xs text-white/55 mt-0.5" data-testid="suggested-pack-reason">
          Basé sur votre consommation de {data.monthly_spend} crédit{data.monthly_spend > 1 ? 's' : ''} ce mois-ci.
        </p>
      </div>
      {onBuy && (
        <button type="button" onClick={() => onBuy(p)} data-testid="suggested-pack-buy-btn"
          className="px-4 py-2 rounded-xl text-xs font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }}>
          Acheter ce pack
        </button>
      )}
    </div>
  );
};
