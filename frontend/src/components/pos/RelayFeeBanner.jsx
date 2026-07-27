import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Coins, CreditCard, Loader2, ListOrdered } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';
import { UcDebitsDialog } from './UcDebitsDialog';

const PACKS = [
  { key: 'P10', eur: 10, uc: 100 },
  { key: 'MINI', eur: 20, uc: 200 },
  { key: 'STANDARD', eur: 40, uc: 400 },
];

export const RelayFeeBanner = ({ refreshKey }) => {
  const [info, setInfo] = useState(null);
  const [showPacks, setShowPacks] = useState(false);
  const [showDebits, setShowDebits] = useState(false);
  const [paying, setPaying] = useState(null);
  useEffect(() => {
    lolodriveAPI.posRelayFee().then(setInfo).catch(() => {});
  }, [refreshKey]);
  if (!info) return null;
  const negative = info.balance_uc < 0;

  const recharge = async (pack) => {
    setPaying(pack);
    try {
      const r = await lolodriveAPI.posCrediScopRecharge(pack);
      window.location.href = r.url;
    } catch (e) { toast.error(e.message); setPaying(null); }
  };

  return (
    <div className="mb-3 rounded-xl border border-[#7c3aed]/35 bg-[#7c3aed]/[0.07] px-4 py-2.5" data-testid="relay-fee-banner">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        <span className="flex items-center gap-1.5 font-bold text-[#c4b5fd]">
          <Coins className="w-3.5 h-3.5" /> Règle réseau
        </span>
        <span className="text-white/70">
          Chaque produit <b className="text-[#D9B35A]">relais</b> (hors catalogue KDMARCHÉ) vendu au comptoir débite{' '}
          <b className="text-[#c4b5fd]" data-testid="relay-fee-value">{info.fee_uc} UC × quantité</b> de votre CREDI'SCOP, instantanément.
        </span>
        <span className="ml-auto flex items-center gap-2 shrink-0">
          <span className="font-mono" data-testid="credi-scop-balance">
            Solde CREDI'SCOP : <b className={negative ? 'text-red-300' : 'text-emerald-300'}>{info.balance_uc} UC</b>
          </span>
          <button type="button" onClick={() => setShowDebits(true)} data-testid="uc-debits-btn"
            className="flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-bold text-white/70 bg-white/[0.06] border border-white/15 hover:text-[#c4b5fd] hover:border-[#7c3aed]/50">
            <ListOrdered className="w-3 h-3" /> Détail débits
          </button>
          <button type="button" onClick={() => setShowPacks((v) => !v)} data-testid="recharge-toggle-btn"
            className={`flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-bold border ${
              negative ? 'text-red-200 bg-red-500/15 border-red-400/40 animate-pulse' : 'text-[#c4b5fd] bg-[#7c3aed]/15 border-[#7c3aed]/45'
            } hover:brightness-125`}>
            <CreditCard className="w-3 h-3" /> Recharger
          </button>
        </span>
      </div>
      {showPacks && (
        <div className="mt-2 pt-2 border-t border-[#7c3aed]/25 flex flex-wrap items-center gap-2" data-testid="recharge-packs">
          <span className="text-[10px] uppercase tracking-wider text-white/40">Recharge CREDI'SCOP par carte (Stripe) :</span>
          {PACKS.map((p) => (
            <button key={p.key} type="button" disabled={!!paying} onClick={() => recharge(p.key)}
              data-testid={`recharge-pack-${p.key}`}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold text-white bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50">
              {paying === p.key ? <Loader2 className="w-3 h-3 animate-spin" /> : <Coins className="w-3 h-3" />}
              {p.eur} € → {p.uc} UC
            </button>
          ))}
        </div>
      )}
      {showDebits && <UcDebitsDialog onClose={() => setShowDebits(false)} />}
    </div>
  );
};
