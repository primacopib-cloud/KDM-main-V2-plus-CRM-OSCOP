import { useEffect, useState } from 'react';
import { PromoCountdown } from './ZoneProductsShowcase';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Bandeau global : compte à rebours de la promo PASS (catalogue, page PASS)
export const PromoPassBanner = () => {
  const [cfg, setCfg] = useState(null);
  useEffect(() => {
    fetch(`${API_URL}/api/public/lolodrive-carousel`)
      .then((r) => (r.ok ? r.json() : null)).then(setCfg).catch(() => {});
  }, []);
  if (!cfg?.promo_percent || !cfg?.promo_ends_at) return null;
  return (
    <div className="flex justify-center pt-4" data-testid="promo-pass-banner">
      <PromoCountdown endsAt={cfg.promo_ends_at} percent={cfg.promo_percent} />
    </div>
  );
};
