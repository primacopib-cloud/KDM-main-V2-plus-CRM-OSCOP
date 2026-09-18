import { useEffect, useState } from 'react';
import { TrendingDown } from 'lucide-react';
import i18n from '@/i18n';
import { API } from '../../services/http';

// Bandeau défilant : dernières baisses de prix réelles de la salle
export const PriceDropTicker = () => {
  const [drops, setDrops] = useState([]);
  useEffect(() => {
    let stop = false;
    const load = () => fetch(`${API}/auctions/recent-drops`)
      .then((r) => (r.ok ? r.json() : { drops: [] }))
      .then((d) => { if (!stop) setDrops(d.drops || []); })
      .catch(() => {});
    load();
    const id = setInterval(load, 60000);
    return () => { stop = true; clearInterval(id); };
  }, []);
  if (drops.length === 0) return null;
  const items = [...drops, ...drops]; // doublé pour une boucle continue
  return (
    <div className="mb-4 rounded-full border border-emerald-400/25 bg-emerald-500/[0.06] overflow-hidden"
      data-testid="price-drop-ticker">
      <div className="flex items-center">
        <span className="shrink-0 inline-flex items-center gap-1.5 pl-3.5 pr-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-emerald-300 border-r border-emerald-400/25 bg-emerald-500/10">
          <TrendingDown className="w-3.5 h-3.5" /> {i18n.t('auction.ticker_label')}
        </span>
        <div className="overflow-hidden flex-1" style={{ maskImage: 'linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent)' }}>
          <div className="ticker-track inline-flex whitespace-nowrap py-1.5" data-testid="price-drop-ticker-track">
            {items.map((d, i) => (
              <span key={`${d.reference}-${d.at}-${i}`}
                className="inline-flex items-center gap-1.5 px-4 text-[11px] text-white/70"
                data-testid={i < drops.length ? `ticker-drop-${d.reference}` : undefined}>
                <b className="text-white/90">{d.title}</b>
                <s className="text-white/35">{d.from_eur.toFixed(2)} €</s>
                <span className="text-emerald-300 font-bold">→ {d.to_eur.toFixed(2)} €</span>
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
