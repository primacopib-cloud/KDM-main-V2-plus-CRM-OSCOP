import { useEffect, useState } from 'react';
import { CreditCard, Coins, Loader2, Lock, X } from 'lucide-react';
import { toast } from 'sonner';
import { zoneAddonAPI } from '../../services/api';

export const ZoneAddonDialog = ({ zone, onClose, onActivated }) => {
  const [pricing, setPricing] = useState(null);
  const [busy, setBusy] = useState('');

  useEffect(() => {
    if (zone) zoneAddonAPI.pricing().then(setPricing).catch(() => setPricing(null));
  }, [zone]);

  if (!zone) return null;
  const priceEur = pricing ? (pricing.price_eur_cents / 100).toFixed(2) : null;

  const payCredits = async () => {
    setBusy('credits');
    try {
      const d = await zoneAddonAPI.purchaseCredits(zone.code);
      toast.success(`Zone ${d.zone_name} activée !`, {
        description: `${d.credits_spent} crédits débités — nouveau solde : ${d.new_credits} crédits`,
      });
      onActivated(zone.code);
      onClose();
    } catch (e) { toast.error(e.message || 'Achat impossible'); }
    setBusy('');
  };

  const payCard = async () => {
    setBusy('card');
    try {
      const d = await zoneAddonAPI.checkout(zone.code, window.location.origin);
      window.location.href = d.checkout_url;
    } catch (e) {
      toast.error(e.message || 'Paiement indisponible');
      setBusy('');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose} data-testid="zone-addon-dialog">
      <div className="w-full max-w-[440px] rounded-2xl bg-[#2A1045] border border-[#D9B35A]/30 shadow-2xl p-6"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#D9B35A]/15 border border-[#D9B35A]/30 flex items-center justify-center">
              <Lock size={18} className="text-[#E9CF8E]" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Zone {zone.name}</h3>
              <p className="text-xs text-white/50">Non incluse dans votre abonnement</p>
            </div>
          </div>
          <button type="button" onClick={onClose} data-testid="zone-addon-close"
            className="p-1.5 rounded-lg text-white/50 hover:text-white border border-white/15">
            <X size={14} />
          </button>
        </div>

        <p className="mt-4 text-sm text-white/70 leading-relaxed">
          Ajoutez la zone <b className="text-white">{zone.name}</b> à votre abonnement pour
          accéder immédiatement à ses tarifs mutualisés et commander dans cette zone.
        </p>

        {!pricing ? (
          <div className="mt-5 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-[#D9B35A]" /></div>
        ) : (
          <div className="mt-5 space-y-2.5">
            <button type="button" onClick={payCredits} disabled={!!busy} data-testid="zone-addon-pay-credits"
              className="w-full flex items-center justify-between px-4 py-3 rounded-xl font-bold text-sm transition-colors disabled:opacity-50"
              style={{ background: '#D4AF37', color: '#1F0A33' }}>
              <span className="inline-flex items-center gap-2">
                {busy === 'credits' ? <Loader2 size={16} className="animate-spin" /> : <Coins size={16} />}
                Payer en crédits CREDI'SCOP
              </span>
              <span>{pricing.credits} crédits</span>
            </button>
            <button type="button" onClick={payCard} disabled={!!busy} data-testid="zone-addon-pay-card"
              className="w-full flex items-center justify-between px-4 py-3 rounded-xl font-bold text-sm border border-white/20 text-white hover:bg-white/[0.06] transition-colors disabled:opacity-50">
              <span className="inline-flex items-center gap-2">
                {busy === 'card' ? <Loader2 size={16} className="animate-spin" /> : <CreditCard size={16} />}
                Payer par carte bancaire
              </span>
              <span>{priceEur} € HT</span>
            </button>
            <p className="text-[10px] text-white/40 text-center pt-1">
              Activation immédiate après paiement — accès permanent à la zone.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
