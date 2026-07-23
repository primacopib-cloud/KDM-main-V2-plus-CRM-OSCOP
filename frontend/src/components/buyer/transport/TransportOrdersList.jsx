import { FileDown } from 'lucide-react';
import { downloadTransportPdf } from './LogiscopSubscribeCard';

const STATUS = {
  PROPOSE: ['Proposé — en attente LOGI\'SCOP', '#FBBF24'],
  ACCEPTE: ['Accepté', '#7BC94E'],
  REFUSE: ['Refusé', '#F87171'],
};

export const TransportOrdersList = ({ orders }) => {
  if (!orders.length) {
    return (
      <p className="text-[11px] text-white/45" data-testid="transport-orders-empty">
        Aucun Ordre de Transport émis pour le moment.
      </p>
    );
  }
  return (
    <div className="rounded-xl p-4 bg-white/[0.03] border border-white/[0.08]" data-testid="transport-orders-list">
      <p className="text-sm font-semibold text-white/85 mb-2">Mes Ordres de Transport ({orders.length})</p>
      <table className="w-full text-[11px]">
        <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
          <th className="py-1 pr-3">Référence</th><th className="py-1 pr-3">Trajet</th>
          <th className="py-1 pr-3">Marchandises</th><th className="py-1 pr-3">Statut</th>
          <th className="py-1 pr-3">Prix HT</th><th className="py-1">PDF</th></tr></thead>
        <tbody>
          {orders.map((o) => {
            const [label, color] = STATUS[o.status] || [o.status, '#999'];
            return (
              <tr key={o.id} className="border-b border-white/[0.04] text-white/75" data-testid={`transport-order-${o.ref.replace(/\//g, '-')}`}>
                <td className="py-1.5 pr-3 font-semibold">{o.ref}</td>
                <td className="py-1.5 pr-3">{o.pickup?.zone_code} → {o.delivery?.zone_code}</td>
                <td className="py-1.5 pr-3 text-white/55">
                  {(o.goods || []).map((g) => g.designation).join(', ').slice(0, 40)}
                </td>
                <td className="py-1.5 pr-3 font-bold" style={{ color }}>{label}
                  {o.status === 'REFUSE' && o.refusal_reason && (
                    <span className="block font-normal text-white/40">{o.refusal_reason.slice(0, 50)}</span>
                  )}
                </td>
                <td className="py-1.5 pr-3">{o.price_ht_cents ? `${(o.price_ht_cents / 100).toFixed(2)} €` : '—'}</td>
                <td className="py-1.5">
                  <button type="button" data-testid={`ot-pdf-${o.ref.replace(/\//g, '-')}`}
                    onClick={() => downloadTransportPdf(`/logiscop-transport/orders/${o.id}/pdf`,
                      `ot-logiscop-${o.ref.replace(/\//g, '-')}.pdf`)}
                    className="text-white/50 hover:text-[#E9CF8E]"><FileDown size={14} /></button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
