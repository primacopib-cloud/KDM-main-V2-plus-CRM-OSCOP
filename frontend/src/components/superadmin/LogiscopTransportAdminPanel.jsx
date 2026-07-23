import { useCallback, useEffect, useState } from 'react';
import { Truck, FileDown, Check, X, Receipt } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { LogiscopTransportKpis } from './LogiscopTransportKpis';
import { LogiscopDisputesPanel } from './LogiscopDisputesPanel';
import { LogiscopQualityHistory } from './LogiscopQualityHistory';

const CONV_STATUS = { PENDING_SIGNATURE: ['En attente signature', '#FBBF24'], SIGNED: ['Signée', '#7BC94E'] };
const OT_STATUS = {
  PROPOSE: ['Proposé', '#FBBF24'], ACCEPTE: ['Accepté', '#7BC94E'], REFUSE: ['Refusé', '#F87171'],
  LIVRE_CONFORME: ['Livré conforme ✓', '#7BC94E'], LIVRE_AVEC_RESERVES: ['Livré avec réserves', '#FBBF24'],
  PARTIEL: ['Partiel', '#F0ABFC'], REFUSE_LIVRAISON: ['Refusé à livraison', '#F87171'],
};
const eur = (c) => `${((c || 0) / 100).toFixed(2)} €`;

const invoiceState = (inv) => {
  if (inv.status === 'PAID') return ['PAYÉE ✓', 'text-emerald-400'];
  const overdue = Date.now() - new Date(inv.issued_at).getTime() > 30 * 864e5;
  return overdue ? ['EN RETARD (+30 j)', 'text-red-300'] : ['EN ATTENTE', 'text-amber-300'];
};

export const LogiscopTransportAdminPanel = () => {
  const [data, setData] = useState(null);
  const [prices, setPrices] = useState({});

  const load = useCallback(() => {
    fetch(`${API}/logiscop-transport/admin/overview`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const download = async (path, filename) => {
    const r = await fetch(`${API}${path}`, { credentials: 'include', headers: getAuthHeaders() });
    if (!r.ok) { toast.error('PDF indisponible'); return; }
    const url = window.URL.createObjectURL(await r.blob());
    const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
    window.URL.revokeObjectURL(url);
  };

  const post = async (path, body, okMsg) => {
    try {
      const r = await fetch(`${API}${path}`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Action impossible');
      toast.success(okMsg(d));
      load();
    } catch (e) { toast.error(e.message); }
  };

  const refuse = (ot) => {
    const reason = window.prompt(`Motif du refus de l'OT ${ot.ref} :`);
    if (reason && reason.trim().length >= 3)
      post(`/logiscop-transport/admin/orders/${ot.id}/refuse`, { reason: reason.trim() }, (d) => `OT ${d.ref} refusé`);
  };

  if (!data || (data.conventions.length === 0 && data.orders.length === 0)) return null;

  return (
    <div className="rounded-xl p-4 mt-4 bg-white/[0.03] border border-white/[0.08]" data-testid="logiscop-transport-admin-panel">
      <p className="flex items-center gap-2 text-sm font-semibold text-white/85 mb-3">
        <Truck className="w-4 h-4 text-[#D9B35A]" /> Transport LOGI'SCOP Mode D — Acheteurs Pro
        {data.pending_orders > 0 && (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300"
            data-testid="logiscop-pending-badge">{data.pending_orders} OT en attente</span>
        )}
      </p>

      <LogiscopTransportKpis />

      <LogiscopDisputesPanel />

      <LogiscopQualityHistory />

      <p className="text-[11px] font-bold text-white/60 mb-1">Conventions cadres ({data.conventions.length})</p>
      <table className="w-full text-[11px] mb-4">
        <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
          <th className="py-1 pr-3">Référence</th><th className="py-1 pr-3">Donneur d'Ordre</th>
          <th className="py-1 pr-3">Zones</th><th className="py-1 pr-3">Statut</th><th className="py-1">PDF</th></tr></thead>
        <tbody>
          {data.conventions.map((c) => {
            const [label, color] = CONV_STATUS[c.status] || [c.status, '#999'];
            return (
              <tr key={c.id} className="border-b border-white/[0.04] text-white/75" data-testid={`admin-conv-${c.id}`}>
                <td className="py-1.5 pr-3 font-semibold">{c.ref}</td>
                <td className="py-1.5 pr-3">{c.company_name || c.email}</td>
                <td className="py-1.5 pr-3 text-white/55">{(c.zones || []).join(', ')}</td>
                <td className="py-1.5 pr-3 font-bold" style={{ color }}>{label}</td>
                <td className="py-1.5">
                  <button type="button" onClick={() => download(`/logiscop-transport/convention/${c.id}/pdf`,
                    `convention-${c.ref.replace(/\//g, '-')}.pdf`)}
                    className="text-white/50 hover:text-[#E9CF8E]"><FileDown size={14} /></button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="text-[11px] font-bold text-white/60 mb-1">Ordres de Transport ({data.orders.length})</p>
      {data.orders.length === 0 ? (
        <p className="text-[11px] text-white/45 mb-4">Aucun OT émis.</p>
      ) : (
        <table className="w-full text-[11px] mb-4">
          <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
            <th className="py-1 pr-3">Référence</th><th className="py-1 pr-3">Donneur d'Ordre</th>
            <th className="py-1 pr-3">Trajet</th><th className="py-1 pr-3">Statut</th>
            <th className="py-1 pr-3">Prix HT</th><th className="py-1">Actions</th></tr></thead>
          <tbody>
            {data.orders.map((o) => {
              const [label, color] = OT_STATUS[o.status] || [o.status, '#999'];
              return (
                <tr key={o.id} className="border-b border-white/[0.04] text-white/75" data-testid={`admin-ot-${o.id}`}>
                  <td className="py-1.5 pr-3 font-semibold">{o.ref}
                    {o.ged_doc_id && <span className="block font-normal text-[10px] text-white/35">GED ✓</span>}
                  </td>
                  <td className="py-1.5 pr-3">{o.company_name}</td>
                  <td className="py-1.5 pr-3">{o.pickup?.zone_code} → {o.delivery?.zone_code}</td>
                  <td className="py-1.5 pr-3 font-bold" style={{ color }}>{label}
                    {o.status === 'ACCEPTE' && o.execution && (
                      <span className="block font-normal text-[#93C5FD]/80">
                        {o.execution.status === 'LIVREE' ? `Livré par ${o.execution.operator_name}` : `En acheminement — ${o.execution.operator_name}`}
                      </span>
                    )}
                    {o.epod?.reserves && (
                      <span className="block font-normal text-white/40">Réserves : {o.epod.reserves.slice(0, 40)}</span>
                    )}
                  </td>
                  <td className="py-1.5 pr-3">{o.price_ht_cents ? eur(o.price_ht_cents) : '—'}</td>
                  <td className="py-1.5">
                    <span className="inline-flex items-center gap-1.5">
                      <button type="button" onClick={() => download(`/logiscop-transport/orders/${o.id}/pdf`,
                        `ot-${o.ref.replace(/\//g, '-')}.pdf`)}
                        className="text-white/50 hover:text-[#E9CF8E]"><FileDown size={14} /></button>
                      {o.status === 'PROPOSE' && (
                        <>
                          <input placeholder="Prix € HT" type="number" value={prices[o.id] || ''}
                            data-testid={`admin-ot-price-${o.id}`}
                            onChange={(e) => setPrices({ ...prices, [o.id]: e.target.value })}
                            className="w-20 h-7 px-2 rounded bg-white/[0.06] border border-white/15 text-[10px] text-white" />
                          <button type="button" data-testid={`admin-ot-accept-${o.id}`}
                            disabled={!prices[o.id] || Number(prices[o.id]) <= 0}
                            onClick={() => post(`/logiscop-transport/admin/orders/${o.id}/accept`,
                              { price_ht_eur: Number(prices[o.id]) },
                              (d) => `OT ${d.ref} accepté — facture ${d.invoice?.ref} émise et envoyée`)}
                            className="px-2 py-1 rounded-lg text-[10px] font-bold bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 disabled:opacity-40 inline-flex items-center gap-1">
                            <Check size={11} /> Accepter + Facturer
                          </button>
                          <button type="button" data-testid={`admin-ot-refuse-${o.id}`} onClick={() => refuse(o)}
                            className="px-2 py-1 rounded-lg text-[10px] font-bold bg-red-500/15 text-red-300 hover:bg-red-500/25 inline-flex items-center gap-1">
                            <X size={11} /> Refuser
                          </button>
                        </>
                      )}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {(data.invoices || []).length > 0 && (
        <>
          <p className="text-[11px] font-bold text-white/60 mb-1 flex items-center gap-1.5">
            <Receipt size={12} className="text-[#93C5FD]" /> Factures transport ({data.invoices.length}) — relance auto à 30 jours
          </p>
          <table className="w-full text-[11px]" data-testid="admin-invoices-table">
            <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
              <th className="py-1 pr-3">Facture</th><th className="py-1 pr-3">OT</th><th className="py-1 pr-3">Client</th>
              <th className="py-1 pr-3">TTC</th><th className="py-1 pr-3">Émise le</th>
              <th className="py-1 pr-3">Règlement</th><th className="py-1">Actions</th></tr></thead>
            <tbody>
              {data.invoices.map((inv) => {
                const [st, cls] = invoiceState(inv);
                return (
                  <tr key={inv.id} className="border-b border-white/[0.04] text-white/75" data-testid={`admin-invoice-${inv.ref}`}>
                    <td className="py-1.5 pr-3 font-semibold">{inv.ref}
                      {inv.ged_doc_id && <span className="block font-normal text-[10px] text-white/35">GED ✓</span>}
                    </td>
                    <td className="py-1.5 pr-3">{inv.ot_ref}</td>
                    <td className="py-1.5 pr-3">{inv.company_name}</td>
                    <td className="py-1.5 pr-3 font-bold text-[#E9CF8E]">{eur(inv.total_ttc_cents)}
                      {(data.credits || []).filter((c) => c.invoice_id === inv.id).map((c) => (
                        <button key={c.id} type="button" data-testid={`admin-credit-${c.ref}`}
                          onClick={() => download(`/logiscop-transport/credits/${c.id}/pdf`, `${c.ref}.pdf`)}
                          title={`Avoir de service (article 22) — ${c.reasons.join(' + ')}`}
                          className="block font-normal text-[10px] text-[#F0ABFC] hover:text-[#E9CF8E]">
                          Avoir {c.ref} : −{eur(c.total_ttc_cents)}
                        </button>
                      ))}
                    </td>
                    <td className="py-1.5 pr-3 text-white/50">{(inv.issued_at || '').slice(0, 10)}</td>
                    <td className={`py-1.5 pr-3 font-bold ${cls}`}>{st}
                      {inv.reminder_sent_at && (
                        <span className="block font-normal text-[10px] text-white/40">
                          Relancée le {inv.reminder_sent_at.slice(0, 10)}
                        </span>
                      )}
                    </td>
                    <td className="py-1.5">
                      <span className="inline-flex items-center gap-1.5">
                        <button type="button" onClick={() => download(`/logiscop-transport/invoices/${inv.id}/pdf`, `${inv.ref}.pdf`)}
                          className="text-white/50 hover:text-[#E9CF8E]"><FileDown size={14} /></button>
                        {inv.status === 'PAID' ? (
                          <button type="button" data-testid={`admin-invoice-unpay-${inv.ref}`}
                            onClick={() => post(`/logiscop-transport/admin/invoices/${inv.id}/mark-paid`, { paid: false },
                              (d) => `Pointage annulé — ${d.ref}`)}
                            className="px-2 py-1 rounded-lg text-[10px] text-white/50 hover:text-white border border-white/15">
                            Annuler pointage
                          </button>
                        ) : (
                          <button type="button" data-testid={`admin-invoice-pay-${inv.ref}`}
                            onClick={() => post(`/logiscop-transport/admin/invoices/${inv.id}/mark-paid`, { paid: true },
                              (d) => `Facture ${d.ref} pointée payée`)}
                            className="px-2 py-1 rounded-lg text-[10px] font-bold bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 inline-flex items-center gap-1">
                            <Check size={11} /> Pointer payée
                          </button>
                        )}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
};
