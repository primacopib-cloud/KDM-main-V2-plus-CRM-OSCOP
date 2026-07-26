import { useEffect, useState } from 'react';
import { Zap } from 'lucide-react';

const pad = (n) => String(n).padStart(2, '0');

export const PromoCountdownStrip = ({ promos }) => {
  const promo = (promos || [])
    .filter((p) => p.promo_type === 'discount_action' && p.ends_at)
    .sort((a, b) => (a.ends_at > b.ends_at ? 1 : -1))[0];
  const [left, setLeft] = useState(0);
  useEffect(() => {
    if (!promo) return undefined;
    const tick = () => setLeft(Math.max(0, new Date(promo.ends_at) - Date.now()));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [promo && promo.ends_at]);
  if (!promo || left <= 0) return null;
  const d = Math.floor(left / 86400000);
  const h = Math.floor((left % 86400000) / 3600000);
  const m = Math.floor((left % 3600000) / 60000);
  const s = Math.floor((left % 60000) / 1000);
  const urgent = left < 48 * 3600 * 1000;
  return (
    <div data-testid="catalog-promo-countdown"
      className="mb-4 rounded-2xl border px-4 py-3 flex flex-wrap items-center justify-between gap-3"
      style={{
        borderColor: urgent ? 'rgba(255,77,77,0.5)' : 'rgba(217,179,90,0.4)',
        background: 'linear-gradient(90deg, rgba(255,77,77,0.08), rgba(217,179,90,0.10))',
      }}>
      <div className="flex items-center gap-2 text-sm font-bold text-white">
        <Zap className="w-4 h-4 text-[#FF9E7A]" fill="currentColor" />
        {promo.name} — <span className="text-[#FF9E7A]">-{promo.value_percent}%</span>
      </div>
      <div className="flex items-center gap-1.5 font-mono tabular-nums" data-testid="catalog-promo-timer">
        <span className="text-[10px] uppercase tracking-[0.2em] text-white/50 mr-1">Se termine dans</span>
        {[[d, 'j'], [h, 'h'], [m, 'm'], [s, 's']].map(([v, u]) => (
          <span key={u} className="px-2 py-1 rounded-lg text-sm font-bold"
            style={{
              background: 'rgba(0,0,0,0.35)',
              color: urgent ? '#FF4D4D' : '#E9CF8E',
              border: `1px solid ${urgent ? 'rgba(255,77,77,0.5)' : 'rgba(217,179,90,0.35)'}`,
            }}>
            {pad(v)}<span className="text-[10px] font-normal opacity-70">{u}</span>
          </span>
        ))}
      </div>
    </div>
  );
};
