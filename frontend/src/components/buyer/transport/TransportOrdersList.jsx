import { Fragment, useEffect, useState } from 'react';
import { FileDown, Receipt, PenLine, Thermometer, CreditCard, Camera, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders, getSessionToken } from '../../../services/http';
import { downloadTransportPdf } from './LogiscopSubscribeCard';
import { TransportEpodForm } from './TransportEpodForm';
import { TransportRating } from './TransportRating';
import { CargoMediaList } from './CargoMediaList';

const STATUS = {
  PROPOSE: ['Proposé — en attente LOGI\'SCOP', '#FBBF24'],
  ACCEPTE: ['Accepté', '#7BC94E'],
  REFUSE: ['Refusé', '#F87171'],
  LIVRE_CONFORME: ['Livré conforme ✓', '#7BC94E'],
  LIVRE_AVEC_RESERVES: ['Livré avec réserves', '#FBBF24'],
  PARTIEL: ['Livraison partielle', '#F0ABFC'],
  REFUSE_LIVRAISON: ['Refusé à livraison', '#F87171'],
};
const CLOSED = ['LIVRE_CONFORME', 'LIVRE_AVEC_RESERVES', 'PARTIEL', 'REFUSE_LIVRAISON'];

const ExecBadge = ({ execution }) => {
  if (!execution) return null;
  return execution.status === 'LIVREE' ? (
    <span className="block font-normal text-emerald-300/80">✓ Livré par {execution.operator_name} — clôturez l'ePOD</span>
  ) : (
    <span className="block font-normal text-[#93C5FD]/80">En acheminement — {execution.operator_name}</span>
  );
};

export const TransportOrdersList = ({ orders, invoicesByOt = {}, disputesByOt = {}, onChanged }) => {
  const [epodFor, setEpodFor] = useState(null);
  const [mediaFor, setMediaFor] = useState(null);
  const [paying, setPaying] = useState(null);
  const [creditsByOt, setCreditsByOt] = useState({});

  useEffect(() => {
    fetch(`${API}/logiscop-transport/credits`, {
      credentials: 'include',
      headers: { Authorization: `Bearer ${getSessionToken()}`, ...getAuthHeaders() },
    }).then((r) => (r.ok ? r.json() : []))
      .then((list) => {
        const map = {};
        (Array.isArray(list) ? list : []).forEach((c) => { map[c.ot_id] = c; });
        setCreditsByOt(map);
      }).catch(() => {});
  }, [orders]);

  const pay = async (inv) => {
    setPaying(inv.id);
    try {
      const r = await fetch(`${API}/logiscop-transport/invoices/${inv.id}/pay`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getSessionToken()}`, ...getAuthHeaders() },
        body: JSON.stringify({ origin_url: window.location.origin }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Paiement indisponible');
      if (d.paid_without_charge) {
        toast.success('Facture intégralement soldée par votre avoir de service — rien à payer !');
        setPaying(null);
        onChanged?.();
        return;
      }
      window.location.href = d.checkout_url;
    } catch (e) { toast.error(e.message); setPaying(null); }
  };

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
            const dispute = disputesByOt[o.id];
            const credit = creditsByOt[o.id];
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
                    {o.status === 'ACCEPTE' && <ExecBadge execution={o.execution} />}
                    {o.status === 'REFUSE' && o.refusal_reason && (
                      <span className="block font-normal text-white/40">{o.refusal_reason.slice(0, 50)}</span>
                    )}
                    {o.epod?.reserves && (
                      <span className="block font-normal text-white/40">Réserves : {o.epod.reserves.slice(0, 45)}</span>
                    )}
                    {o.epod?.temperature_incident && (
                      <span className="block font-bold text-red-300" data-testid={`temp-incident-${o.ref.replace(/\//g, '-')}`}>
                        ⚠ Incident température{dispute ? ` — litige ${dispute.ref}` : ''}
                      </span>
                    )}
                  </td>
                  <td className="py-1.5 pr-3">{o.price_ht_cents ? `${(o.price_ht_cents / 100).toFixed(2)} €` : '—'}</td>
                  <td className="py-1.5 pr-3">
                    {inv ? (
                      <span>
                        <button type="button" data-testid={`invoice-pdf-${inv.ref}`}
                          onClick={() => downloadTransportPdf(`/logiscop-transport/invoices/${inv.id}/pdf`, `${inv.ref}.pdf`)}
                          className="inline-flex items-center gap-1 text-[#93C5FD] hover:text-[#E9CF8E]">
                          <Receipt size={12} /> {inv.ref}
                        </button>
                        {credit && (
                          <button type="button" data-testid={`credit-pdf-${credit.ref}`}
                            title={`Avoir de service (article 22) — ${credit.reasons.join(' + ')}`}
                            onClick={() => downloadTransportPdf(`/logiscop-transport/credits/${credit.id}/pdf`, `${credit.ref}.pdf`)}
                            className="block text-[10px] font-bold text-[#F0ABFC] hover:text-[#E9CF8E]">
                            Avoir {credit.ref} : −{(credit.total_ttc_cents / 100).toFixed(2)} €
                          </button>
                        )}
                        {inv.status === 'PAID' ? (
                          <span className="block text-[10px] font-bold text-emerald-400">✓ Payée</span>
                        ) : (
                          <button type="button" data-testid={`invoice-pay-${inv.ref}`} disabled={paying === inv.id}
                            onClick={() => pay(inv)}
                            className="mt-0.5 inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-bold bg-[#635BFF]/25 text-[#B3AFFF] hover:bg-[#635BFF]/40 disabled:opacity-50">
                            {paying === inv.id ? <Loader2 size={10} className="animate-spin" /> : <CreditCard size={10} />}
                            Payer {(Math.max(0, inv.total_ttc_cents - (credit?.total_ttc_cents || 0)) / 100).toFixed(2)} €
                          </button>
                        )}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="py-1.5">
                    <span className="inline-flex items-center gap-2">
                      <button type="button" data-testid={`ot-pdf-${o.ref.replace(/\//g, '-')}`}
                        onClick={() => downloadTransportPdf(`/logiscop-transport/orders/${o.id}/pdf`,
                          `ot-logiscop-${o.ref.replace(/\//g, '-')}.pdf`)}
                        className="text-white/50 hover:text-[#E9CF8E]"><FileDown size={14} /></button>
                      {['ACCEPTE', ...CLOSED].includes(o.status) && (
                        <button type="button" data-testid={`media-open-${o.ref.replace(/\//g, '-')}`}
                          title="Photos / vidéos de la cargaison"
                          onClick={() => setMediaFor(mediaFor === o.id ? null : o.id)}
                          className="text-white/50 hover:text-[#93C5FD]"><Camera size={14} /></button>
                      )}
                      {o.epod?.temperature_file && (
                        <button type="button" data-testid={`temp-file-${o.ref.replace(/\//g, '-')}`}
                          title={`Relevé de température : ${o.epod.temperature_file.name}`}
                          onClick={() => downloadTransportPdf(`/logiscop-transport/orders/${o.id}/temperature-file`,
                            o.epod.temperature_file.name)}
                          className="text-[#93C5FD] hover:text-[#E9CF8E]"><Thermometer size={14} /></button>
                      )}
                      {CLOSED.includes(o.status) && <TransportRating ot={o} onChanged={onChanged} />}
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
                {mediaFor === o.id && (
                  <tr><td colSpan={6}><CargoMediaList otId={o.id} /></td></tr>
                )}
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
