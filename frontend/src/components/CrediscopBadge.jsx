import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Coins, Clapperboard } from 'lucide-react';
import { apiCall } from '../services/http';

export const CrediscopBadge = ({ className = '' }) => {
  const [data, setData] = useState(null);
  const isLoggedIn = !!localStorage.getItem('user');

  useEffect(() => {
    if (!isLoggedIn) return undefined;
    let active = true;
    const load = () => apiCall('/me/crediscop').then((d) => active && setData(d)).catch(() => {});
    load();
    const interval = setInterval(load, 60000);
    return () => { active = false; clearInterval(interval); };
  }, [isLoggedIn]);

  if (!isLoggedIn) {
    return (
      <Link
        to="/kdmarche"
        data-testid="crediscop-nav-badge-public"
        title="Découvrez la galerie des spots vidéo KDMARCHÉ"
        className={`inline-flex items-center gap-1.5 h-8 px-2.5 rounded-full text-xs font-semibold transition-colors hover:brightness-110 ${className}`}
        style={{ background: 'rgba(217,179,90,0.14)', border: '1px solid rgba(217,179,90,0.45)', color: '#B8860B' }}
      >
        <Clapperboard className="w-3.5 h-3.5" />
        <span className="hidden xl:inline text-[10px] font-bold tracking-wide">GALERIE SPOTS</span>
        <span className="xl:hidden text-[10px] font-bold tracking-wide">SPOTS</span>
      </Link>
    );
  }

  if (!data || data.balance === null || data.balance === undefined) return null;

  const rechargeHref = '/mon-crediscop';

  return (
    <Link
      to={rechargeHref}
      data-testid="crediscop-nav-badge"
      title="Mon CREDI'SCOP — cliquez pour voir votre relevé unifié"
      className={`inline-flex items-center gap-1.5 h-8 px-2.5 rounded-full text-xs font-semibold transition-colors hover:brightness-110 ${className}`}
      style={{ background: 'rgba(217,179,90,0.14)', border: '1px solid rgba(217,179,90,0.45)', color: '#B8860B' }}
    >
      <Coins className="w-3.5 h-3.5" />
      <span data-testid="crediscop-nav-balance">{data.balance}</span>
      <span className="hidden xl:inline text-[10px] font-bold tracking-wide">CREDI&rsquo;SCOP</span>
    </Link>
  );
};
