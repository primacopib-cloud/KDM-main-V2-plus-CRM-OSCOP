import { useCallback, useEffect, useState } from 'react';
import { HandCoins, CheckCircle2, PenLine, Camera, Truck } from 'lucide-react';
import { toast } from 'sonner';
import { CodSignatureDialog } from './CodSignatureDialog';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const eur = (c) => `${((c || 0) / 100).toFixed(2)} €`;

export const CodCollectionPanel = () => {
  const [data, setData] = useState(null);
  const [signOrder, setSignOrder] = useState(null);
  const [marking, setMarking] = useState(false);
  const [courierLink, setCourierLink] = useState('');

  const createCourierLink = async () => {
    const r = await fetch(`${API}/admin/courier/tokens`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'Livreur' }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Génération impossible');
    setCourierLink(`${window.location.origin}${d.path}`);
    toast.success('Lien livreur généré (valable 24h)');
  };

  const load = useCallback(() => {
    fetch(`${API}/admin/cod/orders`, { credentials: 'include' })
      .then((r) => r.json()).then(setData).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const collect = async ({ signature, signer_name, photo }) => {
    setMarking(true);
    const r = await fetch(`${API}/admin/cod/orders/${signOrder.id}/collected`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ signature, signer_name, photo }),
    });
    const d = await r.json();
    setMarking(false);
    if (!r.ok) return toast.error(d.detail || 'Encaissement impossible');
    setSignOrder(null);
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
              <>
                <span className="px-2 py-0.5 rounded bg-emerald-400/15 text-emerald-300 font-semibold inline-flex items-center gap-1">
                  <CheckCircle2 size={11} /> Encaissé
                </span>
                {o.cod_signer_name && (
                  <span className="px-2 py-0.5 rounded bg-white/10 text-white/60 inline-flex items-center gap-1">
                    <PenLine size={10} /> Signé par {o.cod_signer_name}
                  </span>
                )}
                {o.cod_photo_url && (
                  <a href={`${process.env.REACT_APP_BACKEND_URL}${o.cod_photo_url}`} target="_blank" rel="noreferrer"
                    className="px-2 py-0.5 rounded bg-blue-400/15 text-blue-300 inline-flex items-center gap-1 hover:bg-blue-400/25"
                    data-testid={`cod-photo-link-${o.id}`}>
                    <Camera size={10} /> Photo colis
                  </a>
                )}
              </>
            ) : (
              <>
                <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 font-semibold">À encaisser</span>
                {o.cod_reminder_sent && <span className="px-2 py-0.5 rounded bg-red-400/15 text-red-300">Relancé J+7</span>}
                <button onClick={() => setSignOrder(o)} data-testid={`cod-collect-btn-${o.id}`}
                  className="ml-auto h-8 px-3 rounded-lg text-xs font-semibold text-[#1A092D] inline-flex items-center gap-1.5"
                  style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
                  <PenLine size={12} /> Encaisser + signature
                </button>
              </>
            )}
          </div>
        ))}
      </div>
      <CodSignatureDialog open={!!signOrder} onClose={() => setSignOrder(null)} order={signOrder}
        onConfirm={collect} loading={marking} />
      <div className="mt-3 pt-3 border-t border-white/[0.06] flex items-center gap-2 flex-wrap text-xs" data-testid="courier-access-block">
        <span className="text-white/50">Accès livreur mobile :</span>
        <button onClick={createCourierLink} data-testid="courier-link-btn"
          className="h-8 px-3 rounded-lg border border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/10 inline-flex items-center gap-1.5">
          <Truck size={12} /> Générer un lien livreur (24h)
        </button>
        {courierLink && (
          <>
            <button onClick={() => { navigator.clipboard.writeText(courierLink); toast.success('Lien copié'); }}
              className="h-8 px-3 rounded-lg border border-white/15 text-white/70 hover:bg-white/10">Copier le lien</button>
            <a href={`https://wa.me/?text=${encodeURIComponent('Voici votre accès livreur KDMARCHÉ (valable 24h) : ' + courierLink)}`}
              target="_blank" rel="noreferrer"
              className="h-8 px-3 rounded-lg bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 inline-flex items-center">
              Envoyer sur WhatsApp
            </a>
          </>
        )}
      </div>
    </div>
  );
};
