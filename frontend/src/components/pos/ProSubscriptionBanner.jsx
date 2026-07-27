import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, ShieldCheck } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

export const ProSubscriptionBanner = () => {
  const [status, setStatus] = useState(null);
  useEffect(() => {
    lolodriveAPI.managerProStatus().then(setStatus).catch(() => {});
  }, []);
  if (!status) return null;
  if (status.operator_exempt) return null;
  if (status.pro_active) {
    return (
      <div className="mb-4 flex items-center gap-2 text-[11px] text-emerald-300/80" data-testid="pro-status-ok">
        <ShieldCheck className="w-3.5 h-3.5" />
        Abonnement Acheteur Pro actif — {status.org_name}
      </div>
    );
  }
  return (
    <div className="mb-4 rounded-2xl border border-red-400/45 bg-red-400/[0.08] p-4 flex flex-wrap items-center gap-3"
      data-testid="pro-status-warning">
      <ShieldAlert className="w-5 h-5 text-red-400 shrink-0" />
      <div className="flex-1 min-w-[220px]">
        <div className="font-semibold text-red-300">Abonnement Acheteur Pro requis</div>
        <div className="text-xs text-white/60">
          Tout gérant de relais LOLODRIVE doit disposer d'un abonnement Acheteur Pro actif.
          {status.org_name ? ' Votre abonnement n\'est plus actif — régularisez pour conserver votre statut de gérant.'
            : ' Votre compte n\'est rattaché à aucune organisation acheteuse — finalisez votre adhésion Acheteur Pro.'}
        </div>
      </div>
      <Link to="/tarifs" data-testid="pro-status-subscribe-link"
        className="px-4 py-2 rounded-xl text-xs font-bold text-black shrink-0"
        style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)' }}>
        Souscrire / régulariser
      </Link>
    </div>
  );
};
