import { Fragment, useState } from 'react';
import { FileDown, Receipt, PenLine } from 'lucide-react';
import { downloadTransportPdf } from './LogiscopSubscribeCard';
import { TransportEpodForm } from './TransportEpodForm';

const STATUS = {
  PROPOSE: ['Proposé — en attente LOGI\'SCOP', '#FBBF24'],
  ACCEPTE: ['Accepté', '#7BC94E'],
  REFUSE: ['Refusé', '#F87171'],
  LIVRE_CONFORME: ['Livré conforme ✓', '#7BC94E'],
  LIVRE_AVEC_RESERVES: ['Livré avec réserves', '#FBBF24'],
  PARTIEL: ['Livraison partielle', '#F0ABFC'],
  REFUSE_LIVRAISON: ['Refusé à livraison', '#F87171'],
};

export const TransportOrdersList = ({ orders, invoicesByOt = {}, onChanged }) => {
  const [epodFor, setEpodFor] = useState(null);

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
          <th className="py-1 pr-3">Statut</th><th className="py-1 pr-3">Prix HT</th>
          <th className="py-1 pr-3">Facture</th><th className="py-1">Actions</th></tr></thead>
        <tbody>
          {orders.map((o) => {
            const [label, color] = STATUS[o.status] || [o.status, '#999'];
            const inv = invoicesByOt[o.id];
            return (
              <Fragment key={o.id}>
                <tr className="border-b border-white/[0.04] text-white/75" data-testid={`transport-order-${o.ref.replace(/\//g, '-')}`}>
                  <td className="py-1.5 pr-3 font-semibold">{o.ref}
                    <span className="block font-normal text-white/40">
                      {(o.goods || []).map((g) => g.designation).join(', ').slice(0, 38)}
                    </span>
                  </td>
                  <td className="py-1.5 pr-3">{o.pickup?.zone_code} → {o.delivery?.zone_code}</td>
                  <td className="py-1.5 pr-3 font-bold" style={{ color }}>{label}
                    {o.status === 'REFUSE' && o.refusal_reason && (
                      <span className="block font-normal text-white/40">{o.refusal_reason.slice(0, 50)}</span>
                    )}
                    {o.epod?.reserves && (
                      <span className="block font-normal text-white/40">Réserves : {o.epod.reserves.slice(0, 45)}</span>
                    )}
                  </td>
                  <td className="py-1.5 pr-3">{o.price_ht_cents ? `${(o.price_ht_cents / 100).toFixed(2)} €` : '—'}</td>
                  <td className="py-1.5 pr-3">
                    {inv ? (
                      <button type="button" data-testid={`invoice-pdf-${inv.ref}`}
                        onClick={() => downloadTransportPdf(`/logiscop-transport/invoices/${inv.id}/pdf`, `${inv.ref}.pdf`)}
                        className="inline-flex items-center gap-1 text-[#93C5FD] hover:text-[#E9CF8E]">
                        <Receipt size={12} /> {inv.ref}
                      </button>
                    ) : '—'}
                  </td>
                  <td className="py-1.5">
                    <span className="inline-flex items-center gap-2">
                      <button type="button" data-testid={`ot-pdf-${o.ref.replace(/\//g, '-')}`}
                        onClick={() => downloadTransportPdf(`/logiscop-transport/orders/${o.id}/pdf`,
                          `ot-logiscop-${o.ref.replace(/\//g, '-')}.pdf`)}
                        className="text-white/50 hover:text-[#E9CF8E]"><FileDown size={14} /></button>
                      {o.status === 'ACCEPTE' && (
                        <button type="button" data-testid={`epod-open-${o.ref.replace(/\//g, '-')}`}
                          onClick={() => setEpodFor(epodFor === o.id ? null : o.id)}
                          className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold bg-[#D9B35A]/20 text-[#E9CF8E] hover:bg-[#D9B35A]/30">
                          <PenLine size={11} /> Clôturer (ePOD)
                        </button>
                      )}
                    </span>
                  </td>
                </tr>
                {epodFor === o.id && (
                  <tr><td colSpan={6}>
                    <TransportEpodForm ot={o} onCancel={() => setEpodFor(null)}
                      onDone={() => { setEpodFor(null); onChanged?.(); }} />
                  </td></tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
