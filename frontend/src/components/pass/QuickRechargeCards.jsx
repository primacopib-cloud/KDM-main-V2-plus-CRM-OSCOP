import { useState } from 'react';
import { Loader2, Zap, Sparkles, CreditCard } from 'lucide-react';
import { toast } from 'sonner';
import { SectionCard, Badge } from '../LolodriveLayout';
import { lolodriveAPI } from '../../services/api';

const PACKS = [
  { id: 'P10', eur: 10, uc: 100, bonus: 0 },
  { id: 'P25', eur: 25, uc: 250, bonus: 0 },
  { id: 'P100', eur: 100, uc: 1000, bonus: 200 },
];

export default function QuickRechargeCards() {
  const [busy, setBusy] = useState(null);

  const pay = async (packId) => {
    setBusy(packId);
    try {
      const r = await lolodriveAPI.checkoutRecharge(window.location.origin, packId);
      if (r?.url) {
        window.location.href = r.url;
      } else {
        toast.error('Erreur Stripe');
        setBusy(null);
      }
    } catch (e) {
      toast.error(e.message);
      setBusy(null);
    }
  };

  return (
    <SectionCard
      title={
        <span className="flex items-center gap-2">
          <img src="/lolodrive-logo.jpg" alt="LOLODRIVE" className="w-7 h-7 rounded-lg bg-white object-contain" />
          Recharge express — 1 clic
        </span>
      }
      action={<span className="text-[11px] text-white/40 flex items-center gap-1"><CreditCard className="w-3 h-3" /> Paiement Stripe immédiat</span>}
      className="mb-6"
      data-testid="quick-recharge-section"
    >
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {PACKS.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => pay(p.id)}
            disabled={busy !== null}
            data-testid={`quick-recharge-${p.eur}`}
            className={`relative rounded-xl p-4 pt-5 text-center border transition-all hover:-translate-y-0.5 disabled:opacity-60 ${
              p.bonus > 0
                ? 'border-[#D9B35A]/60 shadow-[0_0_24px_rgba(217,179,90,0.15)]'
                : 'border-white/10 hover:border-[#D9B35A]/50'
            }`}
            style={p.bonus > 0
              ? { background: 'linear-gradient(180deg, rgba(217,179,90,0.12), rgba(255,255,255,0.03))' }
              : { background: 'rgba(255,255,255,0.03)' }}
          >
            {p.bonus > 0 && (
              <span className="absolute -top-[12px] left-1/2 -translate-x-1/2 whitespace-nowrap inline-flex items-center gap-1 px-3 py-[3px] rounded-full text-[9px] font-bold uppercase tracking-[0.14em]"
                style={{
                  background: 'linear-gradient(135deg, #F5E2A5 0%, #D9B35A 45%, #A67C2E 100%)',
                  color: '#2A1045',
                }}>
                <Sparkles className="w-2.5 h-2.5" /> +{p.bonus} UC offertes
              </span>
            )}
            <p className="text-2xl font-bold text-[#E9CF8E]">{p.eur} €</p>
            <p className="text-sm text-white/75 mt-0.5">{p.uc + p.bonus} UC</p>
            <span className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-bold text-black"
              style={{ background: 'linear-gradient(135deg, #D9B35A, #c9a34a)' }}>
              {busy === p.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
              Payer en 1 clic
            </span>
          </button>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2 text-[11px] text-white/40">
        <Badge color="#10b981">Sécurisé</Badge>
        Redirection immédiate vers le paiement Stripe — vos UC sont crédités dès la confirmation.
      </div>
    </SectionCard>
  );
}
