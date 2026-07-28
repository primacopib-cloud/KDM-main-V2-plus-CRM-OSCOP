import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Loader2, ReceiptText } from 'lucide-react';

const PAY = { CARD: 'Carte bancaire', UC: "UC — CREDI'SCOP", MIXED: 'UC + complément', CASH: 'Espèces' };

// Page publique de détail d'une vente au comptoir (cible du QR code du ticket PDF)
export default function TicketPublicPage() {
  const { orderId } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/ticket/${orderId}/public`)
      .then(async (r) => { if (!r.ok) throw new Error((await r.json()).detail); return r.json(); })
      .then(setData)
      .catch((e) => setError(e.message || 'Ticket introuvable'));
  }, [orderId]);

  if (error) {
    return (
      <div className="min-h-screen bg-[#0d0d12] text-white flex items-center justify-center p-6">
        <p className="text-white/60" data-testid="ticket-public-error">❌ {error}</p>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="min-h-screen bg-[#0d0d12] text-white flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" />
      </div>
    );
  }
  const { order, point } = data;
  const lines = (order.items || []).map((l) => {
    const ttc = l.unit_cents * l.qty;
    const rate = l.tva_rate ?? 8.5;
    const ht = Math.round(ttc / (1 + rate / 100));
    return { ...l, ttc, ht, rate, tva: ttc - ht };
  });
  const totalHt = lines.reduce((a, l) => a + l.ht, 0);
  const tvaByRate = Object.entries(lines.reduce((m, l) => { m[l.rate] = (m[l.rate] || 0) + l.tva; return m; }, {}))
    .sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]));

  return (
    <div className="min-h-screen bg-[#0d0d12] text-white flex items-start justify-center p-4 sm:p-8">
      <div className="w-full max-w-md rounded-2xl bg-white/[0.03] border border-white/[0.09] p-5 font-mono text-xs" data-testid="ticket-public-page">
        <div className="text-center mb-3">
          <ReceiptText className="w-6 h-6 mx-auto text-[#D9B35A] mb-1" />
          <div className="font-bold text-sm">{point.name || 'Relais LOLODRIVE'}</div>
          <div className="text-white/40 text-[10px]">
            {point.siret ? `SIRET ${point.siret}` : ''}{point.siret && point.vat_number ? ' · ' : ''}{point.vat_number ? `N° TVA ${point.vat_number}` : ''}
          </div>
          <div className="text-white/50 mt-1" data-testid="ticket-public-number">{order.order_number}</div>
          <div className="text-white/40 text-[10px]">{order.created_at ? new Date(order.created_at).toLocaleString('fr-FR') : ''}</div>
        </div>
        <div className="border-t border-dashed border-white/20 pt-2 space-y-1">
          {lines.map((l, i) => (
            <div key={i} className="flex justify-between">
              <span className="truncate">{l.qty} × {l.name}{l.promo_percent ? ` (-${l.promo_percent}%)` : ''} · TVA {l.rate}%</span>
              <span className="shrink-0 ml-2">{(l.ht / 100).toFixed(2)} € HT <span className="text-[#D9B35A]">· {+(l.ttc / 10).toFixed(1)} UC</span></span>
            </div>
          ))}
        </div>
        <div className="border-t border-dashed border-white/20 mt-2 pt-2 space-y-1">
          <div className="flex justify-between font-bold"><span>Sous-total HT</span><span>{(totalHt / 100).toFixed(2)} €</span></div>
          {tvaByRate.map(([rate, tva]) => (
            <div key={rate} className="flex justify-between text-white/55"><span>TVA {parseFloat(rate).toFixed(2).replace('.', ',')} %</span><span>{(tva / 100).toFixed(2)} €</span></div>
          ))}
          {order.promo_discount_cents > 0 && (
            <div className="flex justify-between text-[#FF9E7A]"><span>⚡ Remise promo (déjà déduite)</span><span>−{(order.promo_discount_cents / 100).toFixed(2)} €</span></div>
          )}
          <div className="flex justify-between font-bold border-t border-dashed border-white/20 pt-1" data-testid="ticket-public-total">
            <span>MONTANT TTC ({PAY[order.payment_method] || PAY.CASH})</span>
            <span>{(order.total_cents / 100).toFixed(2)} € <span className="text-[#D9B35A]">· {+(order.total_cents / 10).toFixed(1)} UC</span></span>
          </div>
          {order.uc_paid ? <div className="text-[#D9B35A] text-[10px]">🪙 Payé en UC : {order.uc_paid} UC</div> : null}
          {order.operator_name && <div className="text-white/40 text-[10px]">Encaissé par : {order.operator_name}</div>}
        </div>
        <div className="text-center text-white/35 text-[10px] mt-3">Merci de votre visite — LOLODRIVE by O'SCOP</div>
      </div>
    </div>
  );
}
