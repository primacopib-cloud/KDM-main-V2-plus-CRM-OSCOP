import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Megaphone, CreditCard, Loader2 } from 'lucide-react';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const STATUS_FR = {
  NEW: ['Reçue — en étude', 'text-amber-300 bg-amber-500/10 border-amber-400/40'],
  ASSIGNED: ['Assignée', 'text-sky-300 bg-sky-500/10 border-sky-400/40'],
  VENDOR_ACCEPTED: ['Offre reçue', 'text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/40'],
  VENDOR_DECLINED: ['En recherche', 'text-white/60 bg-white/[0.05] border-white/20'],
  OFFER_ACCEPTED: ['Conclue', 'text-[#8CC63E] bg-[#8CC63E]/20 border-[#8CC63E]/60'],
};

// Espace vendeur : vitrine de mes publications CommunityPlace (offres & demandes) avec statut et paiement
export const VendorMyOffersPanel = () => {
  const [items, setItems] = useState(null);
  const [paying, setPaying] = useState(null);

  const load = () => {
    fetch(`${API_URL}/api/vendor/my-listings`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setItems(d.listings || []))
      .catch(() => {});
  };
  useEffect(load, []);

  const payFees = async (l) => {
    setPaying(l.id);
    try {
      const res = await fetch(`${API_URL}/api/vendor/my-listings/${l.id}/pay-link`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      window.location.href = d.checkout_url;
    } catch (e) { toast.error(e.message); setPaying(null); }
  };

  if (!items || items.length === 0) return null;

  const paymentBadge = (l) => {
    if (!l.communityplace) {
      return <span className="px-2 py-0.5 rounded-full border font-semibold text-white/50 bg-white/[0.04] border-white/15">Non publiée CommunityPlace</span>;
    }
    if (l.communityplace_payment_status === 'PAID') {
      return (
        <span className="px-2 py-0.5 rounded-full border font-semibold text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/40"
          data-testid={`my-listing-paid-${l.reference}`}>
          Publication payée ✓ {Number(l.communityplace_fee_eur || 0).toLocaleString('fr-FR')} €
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="px-2 py-0.5 rounded-full border font-semibold text-orange-300 bg-orange-500/10 border-orange-400/40">
          Frais {Number(l.communityplace_fee_eur || 0).toLocaleString('fr-FR')} € en attente
        </span>
        <button type="button" onClick={() => payFees(l)} disabled={paying === l.id}
          data-testid={`my-listing-pay-${l.reference}`}
          className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-bold text-[#1F0A33] bg-[#D9B35A] hover:brightness-110 disabled:opacity-60">
          {paying === l.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CreditCard className="w-3 h-3" />} Payer
        </button>
      </span>
    );
  };

  return (
    <div className="rounded-2xl p-5 mb-6 bg-white/[0.03] border border-white/[0.08]" data-testid="vendor-my-offers-panel">
      <div className="flex items-center gap-2 mb-3">
        <Megaphone className="w-4 h-4 text-[#8CC63E]" />
        <h3 className="text-sm font-bold text-[#E9CF8E] m-0">Mes publications CommunityPlace ({items.length})</h3>
      </div>
      <div className="space-y-2 max-h-72 overflow-y-auto">
        {items.map((l) => {
          const [label, cls] = STATUS_FR[l.status] || STATUS_FR.NEW;
          return (
            <div key={l.id || l.reference} className="rounded-xl px-3 py-2.5 bg-white/[0.02] border border-white/[0.06] text-[11px] text-white/70"
              data-testid={`my-listing-${l.reference}`}>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold uppercase border ${
                  l.listing_type === 'OFFRE'
                    ? 'text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/40'
                    : 'text-[#E9CF8E] bg-[#D9B35A]/10 border-[#D9B35A]/40'}`}>
                  {l.listing_type === 'OFFRE' ? 'Offre' : 'Demande'}
                </span>
                <span className="text-white font-semibold">{l.reference} · {l.product}</span>
                <span className="text-white/40">qté {l.quantity} · {l.territory}</span>
                <span className={`px-2 py-0.5 rounded-full border font-semibold ${cls}`} data-testid={`my-listing-status-${l.reference}`}>{label}</span>
                {paymentBadge(l)}
                {l.assigned_vendor && (
                  <span className="text-white/40">
                    {l.assigned_role === 'COOPER' ? "COOPER'S" : 'vendeur'} : {l.assigned_vendor}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
