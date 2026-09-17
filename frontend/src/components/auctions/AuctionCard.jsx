import { useEffect, useState } from 'react';
import { Gavel, Coins, Timer, Share2, Images, BadgeCheck, BellRing, Facebook, Target } from 'lucide-react';
import { toast } from 'sonner';
import i18n from '@/i18n';
import { API, getAuthHeaders } from '../../services/http';
import { AuctionPhotoGallery } from './AuctionPhotoGallery';
import { Flag } from '../Flag';

const cardImg = (u) => (u?.startsWith('/api/') ? `${API}${u.slice(4)}` : u);

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

// Contrôle « prix cible » : cloche + email quand le prix dégressif atteint la cible du membre
const PriceAlertControl = ({ a, target, onSet }) => {
  const [open, setOpen] = useState(false);
  const [val, setVal] = useState('');
  if (target != null) {
    return (
      <button type="button" onClick={() => onSet(a.id, 0)} data-testid={`auction-price-alert-active-${a.reference}`}
        title="Retirer l'alerte prix"
        className="self-start inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-400/40 hover:bg-amber-500/25 transition-colors">
        <Target className="w-2.5 h-2.5" /> Alerte ≤ {Number(target).toFixed(2)} € ✕
      </button>
    );
  }
  if (open) {
    return (
      <form className="flex items-center gap-1"
        onSubmit={(e) => { e.preventDefault(); const t = parseFloat(val); if (t > 0) { onSet(a.id, t); setOpen(false); setVal(''); } }}>
        <input type="number" step="0.01" min="0.01" autoFocus value={val} onChange={(e) => setVal(e.target.value)}
          placeholder="Prix cible €" data-testid={`auction-price-alert-input-${a.reference}`}
          className="w-24 h-6 px-2 rounded-md bg-white/[0.07] border border-amber-400/40 text-[10px] text-white placeholder-white/30 outline-none" />
        <button type="submit" data-testid={`auction-price-alert-save-${a.reference}`}
          className="h-6 px-2 rounded-md text-[10px] font-bold bg-amber-400 text-[#2A1045]">OK</button>
        <button type="button" onClick={() => setOpen(false)} className="text-[10px] text-white/45 hover:text-white">✕</button>
      </form>
    );
  }
  return (
    <button type="button" onClick={() => setOpen(true)} data-testid={`auction-price-alert-btn-${a.reference}`}
      title="Être alerté (cloche + email) quand le prix atteint votre cible"
      className="self-start inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold text-white/55 border border-white/20 hover:border-amber-400/50 hover:text-amber-300 transition-colors">
      <Target className="w-2.5 h-2.5" /> Alerte prix cible
    </button>
  );
};

export const AuctionCard = ({ auction, canBid, onChanged, follows = null, onToggleFollow = () => {}, priceAlerts = null, onSetPriceAlert = () => {}, suggested = false }) => {
  const [busy, setBusy] = useState(false);
  const [gallery, setGallery] = useState(false);
  const a = auction;
  const photos = a.photos && a.photos.length > 0 ? a.photos : (a.image_url ? [a.image_url] : []);

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

  const lotUrl = `${window.location.origin}/api/auctions/share/${a.reference}`;
  const shareText = i18n.t('auction.share_text', {
    title: a.title, price: Number(a.price_eur).toFixed(2), credits: a.price_credits,
  }) + ` ${lotUrl}`;

  return (
    <div className="rounded-2xl overflow-hidden bg-white/[0.03] border border-white/[0.08] flex flex-col"
      data-testid={`auction-card-${a.reference}`}>
      <div className="relative h-36 product-thumb-light">
        {a.image_url ? (
          <img src={cardImg(a.image_url)} alt={a.title} loading="lazy"
            onClick={() => photos.length > 0 && setGallery(true)}
            className={`w-full h-full object-contain p-1 ${photos.length > 0 ? 'cursor-zoom-in' : ''}`}
            data-testid={`auction-image-${a.reference}`} />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-black/15"><Gavel className="w-9 h-9" /></div>
        )}
        {photos.length > 1 && (
          <button onClick={() => setGallery(true)} data-testid={`auction-gallery-btn-${a.reference}`}
            className="absolute bottom-1.5 left-1/2 -translate-x-1/2 z-10 px-2 h-5 rounded-full text-[9px] font-bold bg-black/60 text-white inline-flex items-center gap-1 hover:bg-black/80">
            <Images className="w-2.5 h-2.5" /> {photos.length}
          </button>
        )}
        {a.featured && (
          <span className="absolute bottom-1.5 left-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold bg-[#D9B35A] text-[#2A1045] on-gold shadow-md"
            data-testid={`auction-featured-badge-${a.reference}`}>
            ⭐ {i18n.t('auction.featured_badge')}
          </span>
        )}
        <a href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(lotUrl)}&quote=${encodeURIComponent(shareText)}`}
          target="_blank" rel="noopener noreferrer"
          title="Partager sur Facebook" data-testid={`auction-share-fb-btn-${a.reference}`}
          className="absolute bottom-1.5 right-10 w-7 h-7 rounded-full flex items-center justify-center bg-[#1877F2] text-white shadow-md transition-transform hover:scale-110">
          <Facebook className="w-3.5 h-3.5" />
        </a>
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
        {suggested && (
          <span data-testid={`auction-suggested-badge-${a.reference}`}
            className="self-start inline-flex items-center px-1.5 py-0.5 rounded-full text-[8px] font-black bg-[#D9B35A]/15 text-[#F2D07A] border border-[#D9B35A]/50"
            title="Correspond à vos marques ou boutiques suivies">
            ★ Pour vous
          </span>
        )}
        {a.brand && (
          <div className="text-[10px] text-white/50 truncate flex items-center gap-1.5" data-testid={`auction-brand-${a.reference}`}>
            {a.brand_logo && (
              <img src={cardImg(a.brand_logo)} alt={a.brand} className="h-4 w-auto max-w-[48px] object-contain rounded-[2px] bg-white/90 px-0.5"
                data-testid={`auction-brand-logo-${a.reference}`} />
            )}
            <span>Marque : {a.brand}</span>
          </div>
        )}
        {a.retailer && (
          <div className="text-[11px] text-[#E9CF8E] truncate flex items-center gap-1" data-testid={`auction-retailer-${a.reference}`}>
            {a.retailer.gold && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[8px] font-black bg-gradient-to-r from-[#FFD700] to-[#D9B35A] text-[#1F0A33] shrink-0"
                data-testid={`auction-gold-badge-${a.reference}`} title="POP'S n°1 du palmarès des boutiques les mieux notées">
                🏆 POP'S d'Or
              </span>
            )}
            <span className="truncate inline-flex items-center gap-1">
              {a.retailer.country_code && <Flag code={a.retailer.country_code} />} {a.retailer.company_name}
              {a.retailer.locality ? ` · ${a.retailer.locality}` : ''}
            </span>
            {a.retailer.rating_avg && (
              <span className="text-[9px] font-bold text-amber-300 shrink-0" data-testid={`auction-shop-rating-${a.reference}`}>
                ★ {Number(a.retailer.rating_avg).toFixed(1)} ({a.retailer.rating_count})
              </span>
            )}
            {a.retailer.detaillant_user_id && follows && (
              <button onClick={() => onToggleFollow(a.retailer.detaillant_user_id)}
                data-testid={`auction-follow-shop-${a.reference}`}
                title={follows.includes(a.retailer.detaillant_user_id) ? 'Ne plus suivre ce POP\'S' : 'Suivre ce POP\'S — alerte à chaque nouveau lot'}
                className={`shrink-0 inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[8px] font-bold border transition-colors ${
                  follows.includes(a.retailer.detaillant_user_id)
                    ? 'text-emerald-300 border-emerald-400/50 bg-emerald-500/15'
                    : 'text-white/55 border-white/25 hover:border-emerald-400/50 hover:text-emerald-300'}`}>
                <BellRing className="w-2.5 h-2.5" /> {follows.includes(a.retailer.detaillant_user_id) ? 'Suivi ✓' : 'Suivre'}
              </button>
            )}
            {a.retailer.verified && (
              <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[8px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-400/40 shrink-0"
                data-testid={`auction-verified-badge-${a.reference}`} title="Boutique abonnée depuis plus de 3 mois">
                <BadgeCheck className="w-2.5 h-2.5" /> Boutique vérifiée
              </span>
            )}
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
        {a.status === 'LIVE' && priceAlerts && (
          <PriceAlertControl a={a} target={priceAlerts[a.id]} onSet={onSetPriceAlert} />
        )}
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
      {gallery && photos.length > 0 && (
        <AuctionPhotoGallery photos={photos} title={a.title} labels={a.photo_labels} onClose={() => setGallery(false)} />
      )}
    </div>
  );
};
