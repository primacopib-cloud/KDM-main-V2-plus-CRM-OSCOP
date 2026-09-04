import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Loader2, CheckCircle2, Clock } from 'lucide-react';
import { API } from '../services/http';
import Header from '../components/Header';

export default function OscopCheckoutReturnPage() {
  const [params] = useSearchParams();
  const orderId = params.get('order_id');
  const [order, setOrder] = useState(null);
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    if (!orderId || attempts > 8) return undefined;
    const t = setTimeout(async () => {
      try {
        const res = await fetch(`${API}/oscop-checkout/status/${orderId}`);
        const data = await res.json();
        setOrder(data);
        if (data.status !== 'paid') setAttempts((a) => a + 1);
      } catch {
        setAttempts((a) => a + 1);
      }
    }, attempts === 0 ? 300 : 2500);
    return () => clearTimeout(t);
  }, [orderId, attempts]);

  const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;

  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }}>
      <Header />
      <main className="max-w-[640px] mx-auto px-5 py-16 text-center" data-testid="oscop-checkout-return">
        {!order ? (
          <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A] mx-auto" />
        ) : order.status === 'paid' ? (
          <div className="glass-panel-soft rounded-[22px] p-8">
            <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
            <h1 className="text-2xl font-bold mb-2">Paiement confirmé</h1>
            <p className="text-white/70 text-sm mb-4">
              Votre commande <b>{order.order_number}</b> est réglée à la SCIC SAS OBJECTIF SCOP OUTREMER.
            </p>
            <div className="text-sm text-white/80 space-y-1 text-left max-w-xs mx-auto">
              <p>Facture O'SCOP : <b data-testid="oscop-invoice-number">{order.invoice_number}</b></p>
              <p>Marchandises HT : {eur(order.goods_ht_cents)}</p>
              {order.include_logistics && <p>Logistique LOGI'SCOP HT : {eur(order.logistics_ht_cents)}</p>}
              <p>Total TTC : <b>{eur(order.total_ttc_cents)}</b></p>
            </div>
            <p className="text-white/45 text-xs mt-4">
              Vendeur, émetteur de la facture et bénéficiaire du paiement : SCIC SAS OBJECTIF SCOP OUTREMER.
            </p>
          </div>
        ) : (
          <div className="glass-panel-soft rounded-[22px] p-8">
            <Clock className="w-10 h-10 text-[#D9B35A] mx-auto mb-3" />
            <h1 className="text-xl font-bold mb-2">Vérification du paiement…</h1>
            <p className="text-white/60 text-sm">
              {attempts > 8 ? "Le paiement n'est pas encore confirmé. Il sera enregistré automatiquement dès validation par Stripe." : 'Merci de patienter quelques secondes.'}
            </p>
          </div>
        )}
        <Link to="/catalogue" className="inline-block mt-6 text-[#D9B35A] underline text-sm">Retour au catalogue</Link>
      </main>
    </div>
  );
}
