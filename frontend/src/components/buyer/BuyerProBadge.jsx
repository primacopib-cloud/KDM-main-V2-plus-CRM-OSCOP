import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BadgeCheck, Store } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

export const BuyerProBadge = () => {
  const [point, setPoint] = useState(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    lolodriveAPI.managerMyPoint()
      .then(setPoint)
      .catch(() => setPoint(null))
      .finally(() => setLoaded(true));
  }, []);

  if (!loaded) return null;
  return point ? (
    <span className="inline-flex items-center gap-1.5 flex-wrap">
      <span
        data-testid="buyer-badge-relais"
        title={`Relais : ${point.name}${point.code ? ` (${point.code})` : ''}`}
        className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide text-[#E9CF8E] border border-[#D9B35A]/50 bg-[#D9B35A]/10 whitespace-nowrap"
      >
        <img src="/lolodrive-logo.jpg" alt="" className="w-4 h-4 rounded-full bg-white object-contain" />
        Acheteur PRO · Relais LOLODRIVE
      </span>
      <Link
        to="/pos-lolodrive"
        data-testid="pos-shortcut-btn"
        title="Ouvrir le POS LOLODRIVE de mon relais"
        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide text-black whitespace-nowrap transition-transform hover:scale-105"
        style={{ background: 'linear-gradient(135deg, #D9B35A, #c9a34a)' }}
      >
        <Store className="w-3.5 h-3.5" /> POS LOLODRIVE
      </Link>
    </span>
  ) : (
    <span
      data-testid="buyer-badge-pro"
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide text-white/70 border border-white/25 bg-white/5 whitespace-nowrap"
    >
      <BadgeCheck className="w-3.5 h-3.5 text-[#D9B35A]" /> Acheteur PRO
    </span>
  );
};
