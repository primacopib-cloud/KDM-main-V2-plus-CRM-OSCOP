import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ShoppingCart, Check, X } from 'lucide-react';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const BADGE = {
  ASSIGNED: ['À traiter', 'text-amber-300 bg-amber-500/10 border-amber-400/40'],
  VENDOR_ACCEPTED: ['Accepté', 'text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/30'],
  VENDOR_DECLINED: ['Décliné', 'text-red-300 bg-red-500/10 border-red-400/40'],
};

// Espace vendeur : besoins d'achat assignés par la Centrale (accepter avec prix / décliner)
export const VendorNeedsPanel = () => {
  const [needs, setNeeds] = useState(null);
  const load = () => {
    fetch(`${API_URL}/api/vendor/purchase-needs`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { needs: [] })).then((d) => setNeeds(d.needs || [])).catch(() => setNeeds([]));
  };
  useEffect(load, []);

  const respond = async (n, decision) => {
    let price = null;
    let note = null;
    if (decision === 'accept') {
      price = window.prompt(`Proposition de prix (€) pour « ${n.product} » (qté ${n.quantity}) :`, n.budget_eur || '');
      if (!price || !Number(price)) return;
      note = window.prompt('Commentaire (optionnel) :') || null;
    } else {
      note = window.prompt('Motif du refus (optionnel) :') || null;
    }
    try {
      const res = await fetch(`${API_URL}/api/vendor/purchase-needs/${n.id}/respond`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ decision, price_eur: price ? Number(price) : null, note }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(decision === 'accept' ? `Besoin accepté à ${Number(price).toLocaleString('fr-FR')} € — Centrale notifiée` : 'Besoin décliné');
      load();
    } catch (e) { toast.error(e.message); }
  };

  if (!needs?.length) return null;
  return (
    <div className="rounded-[20px] p-5 mb-5 bg-white/[0.03] border border-[#D9B35A]/25" data-testid="vendor-needs-panel">
      <div className="flex items-center gap-2 mb-3">
        <ShoppingCart className="w-4 h-4 text-[#D9B35A]" />
        <h3 className="text-sm font-bold text-[#E9CF8E] m-0">Besoins d'achat assignés par la Centrale ({needs.length})</h3>
      </div>
      <div className="space-y-2">
        {needs.map((n) => {
          const [label, cls] = BADGE[n.status] || BADGE.ASSIGNED;
          return (
            <div key={n.id} className="rounded-xl px-3 py-2.5 bg-white/[0.02] border border-white/[0.06] text-[11px] text-white/70" data-testid={`vendor-need-${n.id}`}>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-white font-semibold">{n.reference ? `${n.reference} · ` : ''}{n.product}</span>
                <span className="text-white/40">qté {n.quantity} · {n.territory}</span>
                {n.budget_eur ? <span className="font-mono text-[#D9B35A]">budget {Number(n.budget_eur).toLocaleString('fr-FR')} €</span> : null}
                {n.vendor_price_eur ? <span className="font-mono text-[#8CC63E]">mon offre {Number(n.vendor_price_eur).toLocaleString('fr-FR')} €</span> : null}
                <span className={`px-2 py-0.5 rounded-full border font-semibold ${cls}`}>{label}</span>
                {n.status === 'ASSIGNED' && (
                  <span className="ml-auto flex gap-1.5">
                    <button type="button" onClick={() => respond(n, 'accept')} data-testid={`vendor-need-accept-${n.id}`}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-bold text-black bg-[#8CC63E] hover:bg-[#7ab52f] transition-colors">
                      <Check className="w-3 h-3" /> Accepter + prix
                    </button>
                    <button type="button" onClick={() => respond(n, 'decline')} data-testid={`vendor-need-decline-${n.id}`}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-bold text-white bg-red-500/70 hover:bg-red-500 transition-colors">
                      <X className="w-3 h-3" /> Décliner
                    </button>
                  </span>
                )}
              </div>
              <p className="m-0 mt-1 text-white/45">{n.company} — {n.contact_name}{n.deadline ? ` · échéance ${n.deadline}` : ''}{n.description ? ` · ${n.description}` : ''}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
