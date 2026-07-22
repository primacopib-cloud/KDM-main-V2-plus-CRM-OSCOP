import { useCallback, useEffect, useState } from 'react';
import { HandCoins, Loader2, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const eur = (c) => `${((c || 0) / 100).toFixed(2)} €`;

export const CodCollectionPanel = () => {
  const [data, setData] = useState(null);
  const [marking, setMarking] = useState(null);

  const load = useCallback(() => {
    fetch(`${API}/admin/cod/orders`, { credentials: 'include' })
      .then((r) => r.json()).then(setData).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const collect = async (o) => {
    setMarking(o.id);
    const r = await fetch(`${API}/admin/cod/orders/${o.id}/collected`, { method: 'POST', credentials: 'include' });
    const d = await r.json();
    setMarking(null);
    if (!r.ok) return toast.error(d.detail || 'Encaissement impossible');
    toast.success(`Commande ${d.order_number} encaissée (${eur(d.amount_paid_cents)})${d.invoice_number ? ` — facture ${d.invoice_number}` : ''}`);
    load();
  };

  if (!data || !data.items?.length) return null;
  return (
    <div className="mb-6 p-4 rounded-xl bg-white/[0.03] border border-white/[0.08]" data-testid="cod-collection-panel">
      <div className="flex items-center gap-3 flex-wrap mb-3">
        <p className="text-sm font-semibold text-white flex items-center gap-2">
          <HandCoins className="w-4 h-4 text-[#D9B35A]" /> Encaissements à la livraison
        </p>
        {data.pending_count > 0 && (
          <span className="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 text-xs font-semibold">
            {data.pending_count} à encaisser · {eur(data.pending_due_cents)}
          </span>
        )}
      </div>
      <div className="space-y-2 max-h-72 overflow-y-auto">
        {data.items.map((o) => (
          <div key={o.id} className="p-2.5 rounded-lg bg-white/[0.03] border border-white/[0.06] flex items-center gap-3 flex-wrap text-xs" data-testid={`cod-order-${o.id}`}>
            <span className="text-white font-medium">{o.order_number}</span>
            {o.org_name && <span className="text-white/50">{o.org_name}</span>}
            <span className="text-[#E9CF8E] font-semibold">{eur(o.cod_amount_due_cents || o.total_ttc_cents)}</span>
            {o.payment_status === 'succeeded' ? (
              <span className="px-2 py-0.5 rounded bg-emerald-400/15 text-emerald-300 font-semibold inline-flex items-center gap-1">
                <CheckCircle2 size={11} /> Encaissé
              </span>
            ) : (
              <>
                <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 font-semibold">À encaisser</span>
                {o.cod_reminder_sent && <span className="px-2 py-0.5 rounded bg-red-400/15 text-red-300">Relancé J+7</span>}
                <button onClick={() => collect(o)} disabled={marking === o.id} data-testid={`cod-collect-btn-${o.id}`}
                  className="ml-auto h-8 px-3 rounded-lg text-xs font-semibold text-[#1A092D] inline-flex items-center gap-1.5 disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
                  {marking === o.id ? <Loader2 size={12} className="animate-spin" /> : <HandCoins size={12} />} Marquer comme encaissé
                </button>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
