import { useEffect, useState } from 'react';
import { Coins } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

export const RelayFeeBanner = ({ refreshKey }) => {
  const [info, setInfo] = useState(null);
  useEffect(() => {
    lolodriveAPI.posRelayFee().then(setInfo).catch(() => {});
  }, [refreshKey]);
  if (!info) return null;
  const negative = info.balance_uc < 0;
  return (
    <div className="mb-3 rounded-xl border border-[#7c3aed]/35 bg-[#7c3aed]/[0.07] px-4 py-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs"
      data-testid="relay-fee-banner">
      <span className="flex items-center gap-1.5 font-bold text-[#c4b5fd]">
        <Coins className="w-3.5 h-3.5" /> Règle réseau
      </span>
      <span className="text-white/70">
        Chaque produit <b className="text-[#D9B35A]">relais</b> (hors catalogue KDMARCHÉ) vendu au comptoir débite{' '}
        <b className="text-[#c4b5fd]" data-testid="relay-fee-value">{info.fee_uc} UC × quantité</b> de votre CREDI'SCOP, instantanément.
      </span>
      <span className="ml-auto font-mono shrink-0" data-testid="credi-scop-balance">
        Solde CREDI'SCOP : <b className={negative ? 'text-red-300' : 'text-emerald-300'}>{info.balance_uc} UC</b>
      </span>
    </div>
  );
};
