import { useEffect, useState } from 'react';
import { Zap, TreePine, Cake, Gift, PartyPopper } from 'lucide-react';
import { API } from '../services/http';

const pad = (n) => String(n).padStart(2, '0');

const labelVisual = (label) => {
  const l = (label || '').toLowerCase();
  if (/no[eë]l|christmas|f[eê]te|hiver/.test(l)) return { img: '/promo-icons/christmas.jpg', Icon: TreePine };
  if (/anniversaire|birthday|\bans\b/.test(l)) return { img: '/promo-icons/birthday.jpg', Icon: Cake };
  if (/cadeau|exclu|flash|solde|promo|offre|remise/.test(l)) return { img: '/promo-icons/gift.jpg', Icon: Gift };
  return { img: '/promo-icons/party.jpg', Icon: PartyPopper };
};

const DigitRing = ({ value, max, label, alert }) => {
  const R = 26;
  const C = 2 * Math.PI * R;
  const frac = max > 0 ? Math.min(value / max, 1) : 0;
  const color = alert ? '#FF4D4D' : '#4DE8FF';
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-[62px] h-[62px]">
        <svg width="62" height="62" viewBox="0 0 62 62" className="absolute inset-0 -rotate-90">
          <circle cx="31" cy="31" r={R} fill="none" stroke={alert ? 'rgba(255,77,77,0.18)' : 'rgba(77,232,255,0.15)'}
            strokeWidth="3" strokeDasharray="2 3.4" />
          <circle cx="31" cy="31" r={R} fill="none" stroke={color} strokeWidth="3"
            strokeDasharray={`${C * frac} ${C}`} strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 0.9s linear', filter: `drop-shadow(0 0 4px ${color})` }} />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center font-mono text-[19px] font-bold tabular-nums"
          style={{ color, textShadow: `0 0 8px ${color}, 0 0 18px ${color}66` }}>
          {pad(value)}
        </span>
      </div>
      <span className="text-[8px] font-bold uppercase tracking-[0.22em]"
        style={{ color: alert ? 'rgba(255,77,77,0.75)' : 'rgba(77,232,255,0.65)' }}>{label}</span>
    </div>
  );
};

const BlinkLabels = ({ labels, alert }) => {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    if (labels.length <= 1) return undefined;
    const id = setInterval(() => setIdx((i) => (i + 1) % labels.length), 2500);
    return () => clearInterval(id);
  }, [labels.length]);
  if (!labels.length) return null;
  const { img, Icon } = labelVisual(labels[idx]);
  return (
    <span className="flex items-center gap-2">
      <img src={img} alt="" data-testid="promo-blink-visual"
        className="w-8 h-8 rounded-full object-cover shrink-0"
        style={{
          border: alert ? '1.5px solid rgba(255,77,77,0.7)' : '1.5px solid rgba(217,179,90,0.7)',
          boxShadow: alert ? '0 0 12px rgba(255,77,77,0.5)' : '0 0 12px rgba(217,179,90,0.45)',
        }} />
      <span data-testid="promo-blink-label"
        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-[11px] font-black uppercase tracking-[0.18em] promo-blink"
        style={alert
          ? { background: 'rgba(255,77,77,0.15)', color: '#FF4D4D', border: '1px solid rgba(255,77,77,0.6)', textShadow: '0 0 10px rgba(255,77,77,0.8)' }
          : { background: 'rgba(217,179,90,0.15)', color: '#E9CF8E', border: '1px solid rgba(217,179,90,0.55)', textShadow: '0 0 10px rgba(233,207,142,0.7)' }}>
        <Icon className="w-3.5 h-3.5 shrink-0" />
        {labels[idx]}
      </span>
    </span>
  );
};

const useLeft = (ends) => {
  const [left, setLeft] = useState(Math.max(0, new Date(ends) - Date.now()));
  useEffect(() => {
    const id = setInterval(() => setLeft(Math.max(0, new Date(ends) - Date.now())), 1000);
    return () => clearInterval(id);
  }, [ends]);
  return left;
};

const PremiumCountdown = ({ promo, placement }) => {
  const left = useLeft(promo.ends_at);
  const d = Math.floor(left / 86400000);
  const h = Math.floor((left % 86400000) / 3600000);
  const m = Math.floor((left % 3600000) / 60000);
  const s = Math.floor((left % 60000) / 1000);
  const alert = d < (promo.alert_days ?? 10);
  const labels = promo.labels?.length ? promo.labels : ['OFFRE FLASH'];
  return (
    <div className="w-full py-3 px-4" data-testid={`flash-promo-banner-${placement}`}
      style={{
        background: 'radial-gradient(ellipse at 50% 120%, #16203a 0%, #05060f 65%)',
        borderBottom: alert ? '1px solid rgba(255,77,77,0.5)' : '1px solid rgba(77,232,255,0.35)',
        boxShadow: alert ? 'inset 0 -20px 40px -30px rgba(255,77,77,0.5)' : 'inset 0 -20px 40px -30px rgba(77,232,255,0.4)',
      }}>
      <style>{`
        @keyframes promoBlink { 0%,100%{opacity:1} 50%{opacity:0.25} }
        .promo-blink { animation: promoBlink 1.2s ease-in-out infinite; }
        @keyframes promoAlertPulse { 0%,100%{opacity:1} 50%{opacity:0.6} }
        .promo-alert-pulse { animation: promoAlertPulse 1s ease-in-out infinite; }
      `}</style>
      <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-white">
        <div className="flex flex-col items-center sm:items-start gap-1.5">
          <BlinkLabels labels={labels} alert={alert} />
          <span className="text-sm font-bold text-white/90">
            <Zap className="inline w-3.5 h-3.5 mr-1 text-[#E9CF8E]" />
            {promo.title}{promo.discount_pct ? ` — -${promo.discount_pct} %` : ''}
          </span>
          {alert && (
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-[#FF4D4D] promo-alert-pulse" data-testid="promo-alert-red">
              ⚠ Derniers jours — plus que {d} j
            </span>
          )}
        </div>
        <div className="flex items-end gap-3" data-testid="promo-countdown">
          <DigitRing value={d} max={30} label="Jours" alert={alert} />
          <DigitRing value={h} max={24} label="Heures" alert={alert} />
          <DigitRing value={m} max={60} label="Minutes" alert={alert} />
          <DigitRing value={s} max={60} label="Secondes" alert={alert} />
        </div>
        {promo.cta_url && (
          <a href={promo.cta_url} data-testid="promo-cta"
            className="px-4 py-1.5 rounded-full text-[11px] font-bold"
            style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)', color: '#1F0A33' }}>
            J'en profite
          </a>
        )}
      </div>
    </div>
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
  return <PremiumCountdown promo={promos[0]} placement={placement} />;
};
