import { useEffect, useState } from 'react';
import { ShoppingCart, HeartHandshake } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const ZONES = {
  GUADELOUPE: 'Guadeloupe', MARTINIQUE: 'Martinique', GUYANE: 'Guyane',
  REUNION: 'La Réunion', MAYOTTE: 'Mayotte', CARIBBEAN: 'Îles du Nord',
};

const ago = (iso) => {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (Number.isNaN(diff)) return '';
  if (diff < 3600) return `il y a ${Math.max(1, Math.round(diff / 60))} min`;
  if (diff < 86400) return `il y a ${Math.round(diff / 3600)} h`;
  return `il y a ${Math.round(diff / 86400)} j`;
};

const Item = ({ it }) => (
  <span className="inline-flex items-center gap-2 text-[12.5px] whitespace-nowrap">
    {it.type === 'order'
      ? <ShoppingCart className="w-3.5 h-3.5 text-[#8CC63E]" />
      : <HeartHandshake className="w-3.5 h-3.5 text-[#D9B35A]" />}
    <span className="text-white/80 font-medium">
      {it.type === 'order' ? 'Commande mutualisée' : 'Nouvelle organisation adhérente'}
    </span>
    {it.zone && <span className="text-[#E9CF8E]">• {ZONES[it.zone] || it.zone}</span>}
    {it.type === 'order' && it.amount_cents > 0 && (
      <span className="text-white/60">• {(it.amount_cents / 100).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</span>
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
            <span className="w-1.5 h-1.5 rounded-full bg-[#8CC63E] animate-pulse" /> En direct
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
