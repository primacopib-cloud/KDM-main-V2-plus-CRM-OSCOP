import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Gavel, ArrowRight, Coins } from 'lucide-react';
import i18n from '@/i18n';
import { Countdown } from './AuctionCard';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Enchère vedette : la LIVE qui se termine le plus tôt, mise en avant sur l'accueil LOLODRIVE
export const FeaturedAuctionBanner = ({ className = '' }) => {
  const [auction, setAuction] = useState(null);

  useEffect(() => {
    fetch(`${API}/auctions/public`)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => {
        const live = (d.items || []).filter((a) => a.status === 'LIVE')
          .sort((a, b) => new Date(a.ends_at) - new Date(b.ends_at));
        setAuction(live[0] || null);
      })
      .catch(() => {});
  }, []);

  if (!auction) return null;
  return (
    <Link to="/encheres" data-testid="featured-auction-banner"
      className={`block rounded-2xl border border-[#D9B35A]/45 p-4 transition-transform hover:scale-[1.01] ${className}`}
      style={{ background: 'linear-gradient(135deg, rgba(217,179,90,0.16), rgba(124,58,237,0.14))' }}>
      <div className="flex items-center gap-4 flex-wrap">
        <div className="w-16 h-16 rounded-xl bg-white/90 overflow-hidden shrink-0 flex items-center justify-center">
          {auction.image_url
            ? <img src={auction.image_url} alt={auction.title} className="w-full h-full object-contain p-1" />
            : <Gavel className="w-7 h-7 text-black/20" />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] uppercase tracking-[0.18em] text-[#E9CF8E] font-bold">
            🔨 {i18n.t('auction.featured_kicker')}
          </p>
          <p className="text-sm font-bold text-white truncate">{auction.title}</p>
          <p className="text-xs text-white/60 flex items-center gap-2 flex-wrap">
            <span className="text-[#E9CF8E] font-bold">{Number(auction.price_eur).toFixed(2)} €</span>
            <span className="inline-flex items-center gap-1"><Coins className="w-3 h-3" /> {auction.price_credits} {i18n.t('auction.credits')}</span>
            <span className="text-red-300 font-semibold" data-testid="featured-auction-countdown">
              <Countdown target={auction.ends_at} prefix={i18n.t('auction.ends_in')} />
            </span>
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold text-[#2A1045] shrink-0"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
          {i18n.t('auction.featured_cta')} <ArrowRight className="w-3.5 h-3.5" />
        </span>
      </div>
    </Link>
  );
};
