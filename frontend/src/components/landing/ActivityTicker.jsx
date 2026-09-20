import { useEffect, useState } from 'react';
import { ShoppingCart, HeartHandshake } from 'lucide-react';
import i18n from '@/i18n';
import { fmtMoney } from '@/i18n/fmt';

const API = process.env.REACT_APP_BACKEND_URL;

const ZONES = {
  GUADELOUPE: 'Guadeloupe', MARTINIQUE: 'Martinique', GUYANE: 'Guyane',
  REUNION: 'La Réunion', MAYOTTE: 'Mayotte', CARIBBEAN: 'Îles du Nord',
};

const ago = (iso) => {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (Number.isNaN(diff)) return '';
  if (diff < 3600) return i18n.t('home.ticker.ago_min', { n: Math.max(1, Math.round(diff / 60)) });
  if (diff < 86400) return i18n.t('home.ticker.ago_h', { n: Math.round(diff / 3600) });
  return i18n.t('home.ticker.ago_d', { n: Math.round(diff / 86400) });
};

const Item = ({ it }) => (
  <span className="inline-flex items-center gap-2 text-[12.5px] whitespace-nowrap">
    {it.type === 'order'
      ? <ShoppingCart className="w-3.5 h-3.5 text-[#8CC63E]" />
      : <HeartHandshake className="w-3.5 h-3.5 text-[#D9B35A]" />}
    <span className="text-white/80 font-medium">
      {it.type === 'order' ? i18n.t('home.ticker.order') : i18n.t('home.ticker.new_org')}
    </span>
    {it.zone && <span className="text-[#E9CF8E]">• {ZONES[it.zone] || it.zone}</span>}
    {it.type === 'order' && it.amount_cents > 0 && (
      <span className="text-white/60">• {fmtMoney(it.amount_cents / 100)}</span>
    )}
    <span className="text-white/35">{ago(it.at)}</span>
  </span>
);

export const ActivityTicker = () => {
  const [items, setItems] = useState([]);

  useEffect(() => {
    const load = () => fetch(`${API}/api/public/activity-ticker`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setItems(d.items || []))
      .catch(() => {});
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, []);

  if (items.length === 0) return null;

  return (
    <div className="py-2 px-5" data-testid="activity-ticker">
      <div className="max-w-[1160px] mx-auto overflow-hidden rounded-full"
        style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(217,179,90,0.2)' }}>
        <div className="flex items-center gap-2 py-2 px-3">
          <span className="shrink-0 inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.18em] font-bold text-[#8CC63E] pr-3 border-r border-white/10">
            <span className="w-1.5 h-1.5 rounded-full bg-[#8CC63E] animate-pulse" /> {i18n.t('home.ticker.live')}
          </span>
          <div className="overflow-hidden flex-1">
            <div className="ticker-track">
              {[0, 1].map((dup) => (
                <div key={dup} className="flex items-center gap-10 pr-10" aria-hidden={dup === 1}>
                  {items.map((it, i) => <Item key={`${dup}-${i}`} it={it} />)}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
