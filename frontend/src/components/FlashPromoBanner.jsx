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

const IMG_SIZE = { s: 'w-8 h-8', m: 'w-12 h-12', l: 'w-16 h-16' };
const IMG_SHAPE = { round: 'rounded-full', square: 'rounded-lg', banner: 'rounded-md' };

const BlinkLabels = ({ labels, images, alert }) => {
  const [idx, setIdx] = useState(0);
  const count = Math.max(labels.length, (images || []).length, 1);
  useEffect(() => {
    if (count <= 1) return undefined;
    const id = setInterval(() => setIdx((i) => (i + 1) % count), 2500);
    return () => clearInterval(id);
  }, [count]);
  if (!labels.length && !(images || []).length) return null;
  const label = labels.length ? labels[idx % labels.length] : '';
  const custom = (images || []).length ? images[idx % images.length] : null;
  const { img, Icon } = labelVisual(label);
  const glow = {
    border: alert ? '1.5px solid rgba(255,77,77,0.7)' : '1.5px solid rgba(217,179,90,0.7)',
    boxShadow: alert ? '0 0 12px rgba(255,77,77,0.5)' : '0 0 12px rgba(217,179,90,0.45)',
  };
  return (
    <span className="flex items-center gap-2">
      {custom ? (
        <img src={custom.url} alt="" data-testid="promo-blink-visual"
          className={`${custom.shape === 'banner' ? 'h-10 w-auto max-w-[130px]' : IMG_SIZE[custom.size] || IMG_SIZE.m} ${IMG_SHAPE[custom.shape] || 'rounded-full'} object-cover shrink-0`}
          style={glow} />
      ) : (
        <img src={img} alt="" data-testid="promo-blink-visual"
          className="w-8 h-8 rounded-full object-cover shrink-0" style={glow} />
      )}
      {label && (
        <span data-testid="promo-blink-label"
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-[11px] font-black uppercase tracking-[0.18em] promo-blink"
          style={alert
            ? { background: 'rgba(255,77,77,0.15)', color: '#FF4D4D', border: '1px solid rgba(255,77,77,0.6)', textShadow: '0 0 10px rgba(255,77,77,0.8)' }
            : { background: 'rgba(217,179,90,0.15)', color: '#E9CF8E', border: '1px solid rgba(217,179,90,0.55)', textShadow: '0 0 10px rgba(233,207,142,0.7)' }}>
          <Icon className="w-3.5 h-3.5 shrink-0" />
          {label}
        </span>
      )}
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

const WhatsAppIcon = (props) => (
  <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
  </svg>
);

const shareWhatsApp = (promo, daysLeft) => {
  const offer = promo.promo_type === 'bonus_purchase'
    ? `+${promo.discount_pct} % de BONUS UC / CREDI'SCOP`
    : (promo.discount_pct ? `-${promo.discount_pct} % de réduction` : 'Offre flash');
  const link = promo.id ? `${window.location.origin}/api/share/promo/${promo.id}` : window.location.origin;
  const msg = `⚡ ${promo.title} — ${offer}\n⏳ Plus que ${daysLeft} jour(s) pour en profiter !\n${link}`;
  window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, '_blank', 'noopener');
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
          <BlinkLabels labels={labels} images={promo.images} alert={alert} />
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
        <button type="button" onClick={() => shareWhatsApp(promo, d)} data-testid="promo-whatsapp-share"
          title="Partager cette offre sur WhatsApp"
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-[11px] font-bold text-white transition-transform hover:scale-105"
          style={{ background: 'linear-gradient(135deg, #25D366 0%, #128C7E 100%)', boxShadow: '0 0 14px rgba(37,211,102,0.35)' }}>
          <WhatsAppIcon className="w-3.5 h-3.5" /> Partager
        </button>
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
