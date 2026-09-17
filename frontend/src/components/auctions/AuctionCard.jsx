import { useEffect, useState } from 'react';
import { Gavel, Coins, Timer, Share2 } from 'lucide-react';
import { toast } from 'sonner';
import i18n from '@/i18n';
import { API, getAuthHeaders } from '../../services/http';

const countryFlag = (code) =>
  code && /^[A-Z]{2}$/i.test(code)
    ? String.fromCodePoint(...[...code.toUpperCase()].map((c) => 127397 + c.charCodeAt(0)))
    : '';

// Compte à rebours réutilisable
export const Countdown = ({ target, prefix }) => {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const ms = new Date(target).getTime() - now;
  if (ms <= 0) return <span>{i18n.t('auction.ended')}</span>;
  const d = Math.floor(ms / 86400000);
  const h = Math.floor((ms % 86400000) / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  const dAbbr = i18n.t('auction.day_abbr');
  const txt = d > 0 ? `${dAbbr}-${d} ${h}h${String(m).padStart(2, '0')}` : `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return <span>{prefix ? `${prefix} ` : ''}{txt}</span>;
};

const STATUS_STYLE = {
  LIVE: 'bg-emerald-600 text-white',
  SCHEDULED: 'bg-sky-600 text-white',
  WON: 'bg-[#D9B35A] text-[#2A1045] on-gold',
  EXPIRED: 'bg-white/20 text-white/80',
};

export const AuctionCard = ({ auction, canBid, onChanged }) => {
  const [busy, setBusy] = useState(false);
  const a = auction;

  const act = async (action) => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/auctions/${a.id}/${action}`, {
        method: 'POST', headers: getAuthHeaders(), credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erreur');
      if (action === 'accept') toast.success(i18n.t('auction.you_won'));
      else toast.success(`${data.price_eur.toFixed(2)} € · ${data.price_credits} ${i18n.t('auction.credits')}`);
      onChanged?.();
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  const shareText = i18n.t('auction.share_text', {
    title: a.title, price: Number(a.price_eur).toFixed(2), credits: a.price_credits,
  }) + ` ${window.location.origin}/encheres`;

  return (
    <div className="rounded-2xl overflow-hidden bg-white/[0.03] border border-white/[0.08] flex flex-col"
      data-testid={`auction-card-${a.reference}`}>
      <div className="relative h-36 product-thumb-light">
        {a.image_url ? (
          <img src={a.image_url} alt={a.title} loading="lazy" className="w-full h-full object-contain p-1" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-black/15"><Gavel className="w-9 h-9" /></div>
        )}
        {a.featured && (
          <span className="absolute bottom-1.5 left-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold bg-[#D9B35A] text-[#2A1045] on-gold shadow-md"
            data-testid={`auction-featured-badge-${a.reference}`}>
            ⭐ {i18n.t('auction.featured_badge')}
          </span>
        )}
        <a href={`https://wa.me/?text=${encodeURIComponent(shareText)}`} target="_blank" rel="noopener noreferrer"
          title={i18n.t('auction.share')} data-testid={`auction-share-btn-${a.reference}`}
          className="absolute bottom-1.5 right-1.5 w-7 h-7 rounded-full flex items-center justify-center bg-[#25D366] text-white shadow-md transition-transform hover:scale-110">
          <Share2 className="w-3.5 h-3.5" />
        </a>
        <span className={`absolute top-1.5 left-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold tracking-wide shadow-md ${STATUS_STYLE[a.status] || 'bg-white/10 text-white/60'}`}>
          {i18n.t(`auction.filter_${a.status === 'LIVE' ? 'live' : a.status === 'SCHEDULED' ? 'scheduled' : 'finished'}`)}
        </span>
        {a.source_label && (
          <span className="absolute top-1.5 right-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold bg-[#2A1045] text-[#F2D07A] border border-[#D9B35A]/60 shadow-md"
            data-testid={`auction-source-${a.reference}`}>
            {a.source_label}
          </span>
        )}
      </div>
      <div className="p-3 flex flex-col gap-1.5 flex-1">
        <div className="text-sm font-semibold text-white truncate" title={a.title}>{a.title}</div>
        {a.retailer && (
          <div className="text-[11px] text-[#E9CF8E] truncate" data-testid={`auction-retailer-${a.reference}`}>
            {countryFlag(a.retailer.country_code)} {a.retailer.company_name}
            {a.retailer.locality ? ` · ${a.retailer.locality}` : ''}
          </div>
        )}
        <div className="flex items-center gap-2 text-[11px] text-white/60">
          {a.category_label && <span>{a.category_label}</span>}
          {a.type_label && <span>· {a.type_label}</span>}
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-lg font-bold text-[#E9CF8E]" data-testid={`auction-price-${a.reference}`}>
            {Number(a.price_eur).toFixed(2)} €
          </span>
          <span className="text-[11px] text-white/55 inline-flex items-center gap-1">
            <Coins className="w-3 h-3" /> {a.price_credits} {i18n.t('auction.credits')}
          </span>
        </div>
        <div className="text-[11px] text-white/55">
          {i18n.t('auction.value')} : {Number(a.value_eur).toFixed(2)} € · {i18n.t('auction.bids_count', { count: a.bids_count })}
        </div>
        <div className="text-[11px] font-semibold text-red-300 inline-flex items-center gap-1" data-testid={`auction-countdown-${a.reference}`}>
          <Timer className="w-3 h-3" />
          {a.status === 'SCHEDULED' && <Countdown target={a.starts_at} prefix={i18n.t('auction.starts_in')} />}
          {a.status === 'LIVE' && <Countdown target={a.ends_at} prefix={i18n.t('auction.ends_in')} />}
          {(a.status === 'WON' || a.status === 'EXPIRED') && <span>{i18n.t('auction.ended')}</span>}
        </div>
        {a.status === 'WON' && a.winner_name && (
          <div className="text-[10px] text-[#E9CF8E]">{i18n.t('auction.won_by')} {a.winner_name} — {Number(a.winner_price_eur).toFixed(2)} €</div>
        )}
        {a.status === 'LIVE' && (
          <div className="mt-auto pt-2 flex gap-2">
            <button type="button" disabled={!canBid || busy} onClick={() => act('bid')}
              data-testid={`auction-bid-btn-${a.reference}`}
              className="flex-1 h-8 rounded-lg text-[11px] font-bold bg-white/10 text-white hover:bg-white/20 disabled:opacity-40 transition-colors">
              {i18n.t('auction.bid', { cost: a.bid_cost_credits })}
            </button>
            <button type="button" disabled={!canBid || busy} onClick={() => act('accept')}
              data-testid={`auction-accept-btn-${a.reference}`}
              className="flex-1 h-8 rounded-lg text-[11px] font-bold text-[#2A1045] on-gold disabled:opacity-40 transition-colors"
              style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
              {i18n.t('auction.accept')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
