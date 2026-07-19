import { useEffect, useState } from 'react';
import { Zap, Clock } from 'lucide-react';
import { API } from '../services/http';

const pad = (n) => String(n).padStart(2, '0');

const Countdown = ({ ends }) => {
  const [left, setLeft] = useState(Math.max(0, new Date(ends) - Date.now()));
  useEffect(() => {
    const id = setInterval(() => setLeft(Math.max(0, new Date(ends) - Date.now())), 1000);
    return () => clearInterval(id);
  }, [ends]);
  const d = Math.floor(left / 86400000);
  const h = Math.floor((left % 86400000) / 3600000);
  const m = Math.floor((left % 3600000) / 60000);
  const s = Math.floor((left % 60000) / 1000);
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-sm font-bold" data-testid="promo-countdown">
      <Clock className="w-3.5 h-3.5" />
      {d > 0 && `${d}j `}{pad(h)}:{pad(m)}:{pad(s)}
    </span>
  );
};

export const FlashPromoBanner = ({ placement = 'landing' }) => {
  const [promos, setPromos] = useState([]);

  useEffect(() => {
    fetch(`${API}/public/flash-promos?placement=${placement}`)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => setPromos(d.items || []))
      .catch(() => {});
  }, [placement]);

  if (!promos.length) return null;
  const p = promos[0];
  return (
    <div className="w-full py-2.5 px-4" data-testid={`flash-promo-banner-${placement}`}
      style={{ background: 'linear-gradient(90deg, #451F6B 0%, #6b2fa3 50%, #451F6B 100%)', borderBottom: '1px solid rgba(217,179,90,0.5)' }}>
      <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-white">
        <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#E9CF8E] uppercase tracking-wide">
          <Zap className="w-4 h-4" /> Promo flash
        </span>
        <span className="text-sm font-semibold">
          {p.title}{p.discount_pct ? ` — -${p.discount_pct} %` : ''}
        </span>
        {p.description && <span className="text-xs text-white/70 hidden sm:inline">{p.description}</span>}
        <span className="text-[#E9CF8E]"><Countdown ends={p.ends_at} /></span>
        {p.cta_url && (
          <a href={p.cta_url} data-testid="promo-cta"
            className="px-3 py-1 rounded-full text-[11px] font-bold"
            style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
            J'en profite
          </a>
        )}
      </div>
    </div>
  );
};
