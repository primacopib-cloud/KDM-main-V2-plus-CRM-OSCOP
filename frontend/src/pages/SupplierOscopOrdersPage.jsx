import { useEffect, useState } from 'react';
import { Loader2, Building2 } from 'lucide-react';
import { API, getAuthHeaders } from '../services/http';
import { Badge } from '../components/ui/badge';
import Header from '../components/Header';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

export default function SupplierOscopOrdersPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/supplier/oscop-orders`, { headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setData)
      .catch(setError);
  }, []);

  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }}>
      <Header />
      <main className="max-w-[1000px] mx-auto px-5 py-10" data-testid="supplier-oscop-orders-page">
        <h1 className="text-3xl font-bold tracking-tight mb-1 flex items-center gap-2">
          <Building2 className="w-7 h-7 text-[#D9B35A]" /> Commandes d'achat O'SCOP
        </h1>
        <p className="text-white/60 text-sm mb-6">
          Acheteur : <b className="text-[#D9B35A]">SCIC SAS OBJECTIF SCOP OUTREMER</b> — vos factures sont
          à établir au nom de cette entité.
        </p>
        {error && <p className="text-amber-300 text-sm">Connectez-vous avec votre compte fournisseur pour voir vos commandes O'SCOP.</p>}
        {!data && !error && <Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" />}
        {data && data.orders.length === 0 && (
          <p className="text-white/50" data-testid="supplier-no-orders">Aucune commande d'achat O'SCOP associée à votre compte.</p>
        )}
        {data && data.orders.map((o) => (
          <div key={o.id} className="glass-panel-soft rounded-[16px] p-4 mb-2" data-testid={`supplier-order-${o.reference}`}>
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-3">
                <span className="font-semibold text-white/90">{o.reference}</span>
                <Badge className="bg-white/10 text-white/70 border-0 text-[10px]">{o.status}</Badge>
              </div>
              <span className="text-[#D9B35A] font-semibold text-sm">{eur(o.purchase_amount_ex_vat)} HT</span>
            </div>
            <div className="grid sm:grid-cols-3 gap-2 mt-2 text-[11px] text-white/60">
              <p>Acheteur : <span className="text-white/85" data-testid={`buyer-mention-${o.reference}`}>{o.buyer}</span></p>
              <p>Payeur matériel : <span className="text-white/85">{o.payer_mention}</span></p>
              <p>Destinataire : <span className="text-white/85">{o.recipient}</span></p>
            </div>
            <p className="text-white/40 text-[11px] mt-1">
              Payé à ce jour : {eur(o.supplier_paid_amount)} · Logistique : {o.logistics_mode} · Créée le {o.created_at?.slice(0, 10)}
            </p>
          </div>
        ))}
      </main>
    </div>
  );
}
