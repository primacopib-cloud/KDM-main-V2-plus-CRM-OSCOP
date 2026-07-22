import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Truck, PenLine, RefreshCw, CheckCircle2, KeyRound } from 'lucide-react';
import { toast } from 'sonner';
import { CodSignatureDialog } from '../components/superadmin/CodSignatureDialog';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const eur = (c) => `${((c || 0) / 100).toFixed(2)} €`;

export default function CourierPage() {
  const [params] = useSearchParams();
  const [token, setToken] = useState(params.get('token') || localStorage.getItem('courier_token') || '');
  const [courier, setCourier] = useState('');
  const [items, setItems] = useState(null);
  const [signOrder, setSignOrder] = useState(null);
  const [marking, setMarking] = useState(false);
  const [done, setDone] = useState([]);

  const load = useCallback(async (tk) => {
    if (!tk) return;
    const r = await fetch(`${API}/courier/orders?token=${encodeURIComponent(tk)}`);
    const d = await r.json();
    if (!r.ok) {
      setItems(null);
      return toast.error(d.detail || 'Accès invalide');
    }
    localStorage.setItem('courier_token', tk);
    setCourier(d.courier);
    setItems(d.items || []);
  }, []);
  useEffect(() => { if (token) load(token); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const collect = async ({ signature, signer_name, photo }) => {
    setMarking(true);
    const r = await fetch(`${API}/courier/orders/${signOrder.id}/collected?token=${encodeURIComponent(token)}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ signature, signer_name, photo }),
    });
    const d = await r.json();
    setMarking(false);
    if (!r.ok) return toast.error(d.detail || 'Encaissement impossible');
    setDone((prev) => [...prev, signOrder.id]);
    setSignOrder(null);
    toast.success(`${d.order_number} encaissée (${eur(d.amount_paid_cents)}) — reçu envoyé au client`);
    load(token);
  };

  return (
    <div className="min-h-screen text-white px-4 py-6" style={{ background: 'linear-gradient(160deg, #2A1045, #451F6B)' }} data-testid="courier-page">
      <div className="max-w-md mx-auto">
        <h1 className="text-xl font-display font-bold flex items-center gap-2 mb-1">
          <Truck size={20} className="text-[#D9B35A]" /> Espace livreur
        </h1>
        <p className="text-xs text-white/55 mb-5">
          {courier ? `Bonjour ${courier} — encaissements du jour à faire signer.` : 'Tournée du jour — paiements à la livraison.'}
        </p>

        {items === null ? (
          <div className="rounded-2xl p-5 bg-white/[0.05] border border-white/10 space-y-3">
            <p className="text-sm text-white/70 flex items-center gap-2"><KeyRound size={14} className="text-[#D9B35A]" /> Entrez votre code d'accès livreur (fourni par l'équipe)</p>
            <input value={token} onChange={(e) => setToken(e.target.value)} placeholder="Code d'accès"
              data-testid="courier-token-input"
              className="w-full h-11 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35 focus:outline-none focus:border-[#D9B35A]/60" />
            <button onClick={() => load(token)} data-testid="courier-token-submit"
              className="w-full h-11 rounded-lg text-sm font-semibold text-[#1A092D]"
              style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
              Accéder à ma tournée
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-3">
              <span className="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 text-xs font-semibold" data-testid="courier-pending-count">
                {items.length} encaissement(s) à faire
              </span>
              <button onClick={() => load(token)} className="p-2 rounded-lg bg-white/[0.06] border border-white/10" title="Actualiser">
                <RefreshCw size={14} />
              </button>
            </div>
            <div className="space-y-3">
              {items.map((o) => (
                <div key={o.id} className="rounded-2xl p-4 bg-white/[0.05] border border-white/10" data-testid={`courier-order-${o.id}`}>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-semibold">{o.order_number}</p>
                    <p className="text-lg font-bold text-[#E9CF8E]">{eur(o.cod_amount_due_cents || o.total_ttc_cents)}</p>
                  </div>
                  {o.org_name && <p className="text-xs text-white/55 mb-3">{o.org_name}</p>}
                  <button onClick={() => setSignOrder(o)} data-testid={`courier-collect-btn-${o.id}`}
                    className="w-full h-11 rounded-xl text-sm font-semibold text-[#1A092D] inline-flex items-center justify-center gap-2"
                    style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
                    <PenLine size={15} /> Encaisser + faire signer
                  </button>
                </div>
              ))}
              {!items.length && (
                <div className="rounded-2xl p-8 bg-white/[0.04] border border-white/10 text-center" data-testid="courier-empty">
                  <CheckCircle2 size={36} className="mx-auto text-emerald-300 mb-2" />
                  <p className="text-sm text-white/70">Tournée terminée — aucun encaissement en attente. Bravo !</p>
                  {done.length > 0 && <p className="text-xs text-white/45 mt-1">{done.length} encaissement(s) réalisés dans cette session.</p>}
                </div>
              )}
            </div>
          </>
        )}
      </div>
      <CodSignatureDialog open={!!signOrder} onClose={() => setSignOrder(null)} order={signOrder}
        onConfirm={collect} loading={marking} />
    </div>
  );
}
