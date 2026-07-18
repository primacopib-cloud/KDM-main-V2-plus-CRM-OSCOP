import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Coins } from 'lucide-react';
import { apiCall } from '../services/http';

export const CrediscopBadge = ({ className = '' }) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    let active = true;
    const load = () => apiCall('/me/crediscop').then((d) => active && setData(d)).catch(() => {});
    load();
    const interval = setInterval(load, 60000);
    return () => { active = false; clearInterval(interval); };
  }, []);

  if (!data || data.balance === null || data.balance === undefined) return null;

  return (
    <Link
      to={data.href || '/wallet'}
      data-testid="crediscop-nav-badge"
      title="Mon CREDI'SCOP — Mes droits coopératifs mobilisables"
      className={`inline-flex items-center gap-1.5 h-8 px-2.5 rounded-full text-xs font-semibold transition-colors hover:brightness-110 ${className}`}
      style={{ background: 'rgba(217,179,90,0.14)', border: '1px solid rgba(217,179,90,0.45)', color: '#B8860B' }}
    >
      <Coins className="w-3.5 h-3.5" />
      <span data-testid="crediscop-nav-balance">{data.balance}</span>
      <span className="hidden xl:inline text-[10px] font-bold tracking-wide">CREDI&rsquo;SCOP</span>
    </Link>
  );
};
