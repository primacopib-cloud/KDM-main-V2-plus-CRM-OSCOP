import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { detaillantAPI } from '../../../services/api.detaillant';
import { COUNTRIES } from '../../detaillant/detaillantI18n';

// Panneau superadmin : validation des offres de lots détaillants avant programmation COOP'ACT
export const DetaillantOffersPanel = () => {
  const [offers, setOffers] = useState([]);
  const [filter, setFilter] = useState('PENDING');
  const load = useCallback(() => {
    detaillantAPI.adminOffers(filter === 'ALL' ? '' : filter).then((r) => setOffers(r.offers || [])).catch(() => {});
  }, [filter]);
  useEffect(() => { load(); }, [load]);

  const review = async (o, action) => {
    let note = null;
    if (action === 'REJECT') note = window.prompt('Motif du refus (crédits remboursés) :') || '';
    try {
      await detaillantAPI.adminReview(o.id, action, note);
      toast.success(action === 'APPROVE' ? 'Offre validée — à programmer en salle COOP\'ACT' : 'Offre refusée, crédits remboursés');
      load();
    } catch (e) { toast.error(e.message); }
  };

  const flag = (code) => COUNTRIES.find((c) => c.code === code)?.flag || '';

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="detaillant-offers-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-[#E9CF8E]">Offres de lots Détaillants</h3>
        <select value={filter} onChange={(e) => setFilter(e.target.value)} data-testid="dt-admin-filter"
          className="h-8 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs">
          <option value="PENDING">En attente</option>
          <option value="APPROVED">Validées</option>
          <option value="REJECTED">Refusées</option>
          <option value="ALL">Toutes</option>
        </select>
      </div>
      {offers.length === 0 && <p className="text-xs text-white/40">Aucune offre.</p>}
      <div className="space-y-2">
        {offers.map((o) => (
          <div key={o.id} className="p-3 rounded-xl bg-white/[0.03] border border-white/10" data-testid={`dt-admin-offer-${o.id}`}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-bold">
                  {o.product_name} — {o.qty_lots} lot(s) ×3 {o.lot_type === 'COMPOSED' ? '(composé)' : '(même produit)'}
                </p>
                <p className="text-[10px] text-white/55">
                  {flag(o.country_code)} {o.company_name} · {o.locality} · {o.category} · {o.cost_credits} crédits{o.extra_offer ? ' (offre supplémentaire)' : ''}
                </p>
                <p className="text-[10px] text-white/45 mt-1">{o.description}</p>
                {o.composed_detail && <p className="text-[10px] text-white/45">Composition : {o.composed_detail}</p>}
              </div>
              {o.status === 'PENDING' ? (
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => review(o, 'APPROVE')} data-testid={`dt-approve-${o.id}`}
                    className="h-7 px-3 rounded-full text-[10px] font-bold text-emerald-300 border border-emerald-400/40 bg-emerald-500/10 hover:bg-emerald-500/20">
                    Valider
                  </button>
                  <button onClick={() => review(o, 'REJECT')} data-testid={`dt-reject-${o.id}`}
                    className="h-7 px-3 rounded-full text-[10px] font-bold text-red-300 border border-red-400/40 bg-red-500/10 hover:bg-red-500/20">
                    Refuser
                  </button>
                </div>
              ) : (
                <span className={`text-[10px] font-bold shrink-0 ${o.status === 'APPROVED' ? 'text-emerald-300' : 'text-red-300'}`}>
                  {o.status === 'APPROVED' ? 'VALIDÉE' : 'REFUSÉE'}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
