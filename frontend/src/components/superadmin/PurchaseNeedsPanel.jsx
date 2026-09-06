import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ShoppingCart, UserPlus, Globe } from 'lucide-react';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const STATUS = {
  NEW: ['Nouveau', 'text-amber-300 bg-amber-500/10 border-amber-400/40'],
  ASSIGNED: ['Assigné', 'text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/30'],
  VENDOR_ACCEPTED: ['Accepté vendeur', 'text-[#8CC63E] bg-[#8CC63E]/15 border-[#8CC63E]/50'],
  VENDOR_DECLINED: ['Décliné vendeur', 'text-red-300 bg-red-500/10 border-red-400/40'],
};

// Superadmin : besoins d'achat déposés par les visiteurs
export const PurchaseNeedsPanel = () => {
  const [needs, setNeeds] = useState([]);
  const load = () => {
    fetch(`${API_URL}/api/admin/purchase-needs`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { needs: [] })).then((d) => setNeeds(d.needs || [])).catch(() => {});
  };
  useEffect(load, []);

  const post = async (url, body, okMsg) => {
    try {
      const res = await fetch(url, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: body ? JSON.stringify(body) : undefined,
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(okMsg);
      load();
    } catch (e) { toast.error(e.message); }
  };

  const assign = (n) => {
    const email = window.prompt(`Email du vendeur à qui assigner « ${n.product} » :`, n.assigned_vendor || '');
    if (email) post(`${API_URL}/api/admin/purchase-needs/${n.id}/assign`, { vendor_email: email.trim() }, 'Besoin assigné — vendeur notifié par email');
  };

  return (
    <div className="rounded-2xl p-5 mt-6 bg-white/[0.03] border border-white/[0.08]" data-testid="purchase-needs-panel">
      <div className="flex items-center gap-2 mb-3">
        <ShoppingCart className="w-4 h-4 text-[#D9B35A]" />
        <h3 className="text-sm font-bold text-[#E9CF8E] m-0">Besoins d'achat visiteurs ({needs.length})</h3>
      </div>
      {!needs.length ? (
        <p className="text-[11px] text-white/40 m-0">Aucun besoin d'achat déposé pour le moment.</p>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {needs.map((n) => {
            const [label, cls] = STATUS[n.status] || STATUS.NEW;
            return (
              <div key={n.id} className="rounded-xl px-3 py-2.5 bg-white/[0.02] border border-white/[0.06] text-[11px] text-white/70" data-testid={`need-row-${n.id}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-white font-semibold">{n.reference ? `${n.reference} · ` : ''}{n.product}</span>
                  <span className="text-white/40">qté {n.quantity} · {n.territory}</span>
                  {n.budget_eur ? <span className="font-mono text-[#D9B35A]">{Number(n.budget_eur).toLocaleString('fr-FR')} €</span> : null}
                  {n.vendor_price_eur ? <span className="font-mono text-[#8CC63E]">offre {Number(n.vendor_price_eur).toLocaleString('fr-FR')} €</span> : null}
                  <span className={`px-2 py-0.5 rounded-full border font-semibold ${cls}`}>{label}</span>
                  {n.communityplace && (
                    <span className="px-2 py-0.5 rounded-full border font-semibold text-sky-300 bg-sky-500/10 border-sky-400/40">
                      CommunityPlace {n.communityplace_payment_status === 'PENDING' ? `· paiement ${Number(n.communityplace_fee_eur || 0).toLocaleString('fr-FR')} € en attente` : ''}
                    </span>
                  )}
                  <span className="ml-auto flex gap-1.5">
                    <button type="button" onClick={() => assign(n)} data-testid={`need-assign-${n.id}`}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-bold text-black bg-[#8CC63E] hover:bg-[#7ab52f] transition-colors">
                      <UserPlus className="w-3 h-3" /> Assigner
                    </button>
                    {!n.communityplace && (
                      <button type="button" data-testid={`need-community-${n.id}`}
                        onClick={() => {
                          const fee = window.prompt('Frais de publication CommunityPlace (€) facturés au demandeur :', '50');
                          if (fee && Number(fee) > 0) post(`${API_URL}/api/admin/purchase-needs/${n.id}/communityplace`, { fee_eur: Number(fee) }, 'Publié — lien de paiement Stripe envoyé au demandeur');
                        }}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-semibold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30 hover:bg-white/[0.1] transition-colors">
                        <Globe className="w-3 h-3" /> CommunityPlace
                      </button>
                    )}
                  </span>
                </div>
                <p className="m-0 mt-1 text-white/45">
                  {n.company} — {n.contact_name} · {n.email} · {n.phone}
                  {n.deadline ? ` · échéance ${n.deadline}` : ''}
                  {n.assigned_vendor ? ` · vendeur : ${n.assigned_vendor}` : ''}
                </p>
                {n.description && <p className="m-0 mt-0.5 text-white/50 italic">{n.description}</p>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
