import { useEffect, useState } from 'react';
import { Gavel } from 'lucide-react';
import { TabsContent } from '../ui/tabs';

const API = process.env.REACT_APP_BACKEND_URL;
const eur = (c) => (c == null ? '—' : `${(c / 100).toFixed(2).replace('.', ',')} €`);
const S_STYLE = {
  PUBLIEE: 'bg-emerald-500/15 text-emerald-400', INSCRIPTIONS_OUVERTES: 'bg-emerald-500/15 text-emerald-400',
  EN_COURS: 'bg-[#D9B35A]/20 text-[#E9CF8E]', CLOTUREE: 'bg-white/10 text-white/60',
  EN_EVALUATION: 'bg-blue-500/15 text-blue-400', ATTRIBUEE: 'bg-emerald-500/15 text-emerald-400',
  ANNULEE: 'bg-red-500/15 text-red-400',
};

export const BuyerConsultationsTab = () => {
  const [items, setItems] = useState([]);

  useEffect(() => {
    fetch(`${API}/api/consultations/tracking`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => setItems(d.items || []))
      .catch(() => {});
  }, []);

  return (
    <TabsContent value="consultations" className="space-y-3" data-testid="buyer-consultations-tab">
      <p className="text-[11px] text-white/40">
        Suivi organisateur KDMARCHÉ PRO — participation et résultats. Les montants ne sont visibles qu'après la clôture.
        La gestion complète (création, validation, attribution) reste dans le Super Admin.
      </p>
      {!items.length && (
        <div className="text-center py-10 bg-white/[0.03] rounded-2xl border border-white/[0.06]">
          <Gavel className="w-10 h-10 mx-auto text-white/20 mb-3" />
          <p className="text-white/40 text-sm">Aucune consultation.</p>
        </div>
      )}
      {items.map((c) => (
        <div key={c.id} className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-4" data-testid={`buyer-cons-${c.id}`}>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold text-[#E9CF8E]">{c.ref}</span>
            <span className="text-sm font-bold text-white flex-1 min-w-[150px]">{c.title}</span>
            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-white/10 text-white/60">{c.procedure === 'SCELLEE' ? 'OFFRES SCELLÉES' : 'ENCHÈRE INVERSÉE'}</span>
            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${S_STYLE[c.status] || 'bg-white/10 text-white/50'}`}>{c.status.replace(/_/g, ' ')}</span>
          </div>
          <div className="flex flex-wrap gap-4 mt-2 text-[11px] text-white/55">
            <span>Catégorie : <b className="text-white/80">{c.category}</b></span>
            <span>Inscrits : <b className="text-white/80">{c.participants}</b></span>
            <span>Offres valides : <b className="text-white/80">{c.valid_bids}</b></span>
            <span>Meilleure offre : <b className="text-[#E9CF8E]">{c.best_offer_ht_cents != null ? `${eur(c.best_offer_ht_cents)} HT` : 'visible après clôture'}</b></span>
            {c.winner && <span>Attributaire : <b className="text-emerald-400">{c.winner}</b></span>}
            {c.closes_at && <span>Clôture : {String(c.closes_at).slice(0, 16).replace('T', ' ')}</span>}
          </div>
        </div>
      ))}
    </TabsContent>
  );
};
