import { useCallback, useEffect, useState } from 'react';
import { Truck, FileDown, Check, X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const CONV_STATUS = { PENDING_SIGNATURE: ['En attente signature', '#FBBF24'], SIGNED: ['Signée', '#7BC94E'] };
const OT_STATUS = { PROPOSE: ['Proposé', '#FBBF24'], ACCEPTE: ['Accepté', '#7BC94E'], REFUSE: ['Refusé', '#F87171'] };

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

  const act = async (otId, action, body) => {
    try {
      const r = await fetch(`${API}/logiscop-transport/admin/orders/${otId}/${action}`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Action impossible');
      toast.success(action === 'accept' ? `OT ${d.ref} accepté` : `OT ${d.ref} refusé`);
      load();
    } catch (e) { toast.error(e.message); }
  };

  const refuse = (ot) => {
    const reason = window.prompt(`Motif du refus de l'OT ${ot.ref} :`);
    if (reason && reason.trim().length >= 3) act(ot.id, 'refuse', { reason: reason.trim() });
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
        <p className="text-[11px] text-white/45">Aucun OT émis.</p>
      ) : (
        <table className="w-full text-[11px]">
          <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
            <th className="py-1 pr-3">Référence</th><th className="py-1 pr-3">Donneur d'Ordre</th>
            <th className="py-1 pr-3">Trajet</th><th className="py-1 pr-3">Statut</th>
            <th className="py-1 pr-3">Prix HT</th><th className="py-1">Actions</th></tr></thead>
          <tbody>
            {data.orders.map((o) => {
              const [label, color] = OT_STATUS[o.status] || [o.status, '#999'];
              return (
                <tr key={o.id} className="border-b border-white/[0.04] text-white/75" data-testid={`admin-ot-${o.id}`}>
                  <td className="py-1.5 pr-3 font-semibold">{o.ref}</td>
                  <td className="py-1.5 pr-3">{o.company_name}</td>
                  <td className="py-1.5 pr-3">{o.pickup?.zone_code} → {o.delivery?.zone_code}</td>
                  <td className="py-1.5 pr-3 font-bold" style={{ color }}>{label}</td>
                  <td className="py-1.5 pr-3">{o.price_ht_cents ? `${(o.price_ht_cents / 100).toFixed(2)} €` : '—'}</td>
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
                            onClick={() => act(o.id, 'accept',
                              { price_ht_eur: prices[o.id] ? Number(prices[o.id]) : null })}
                            className="px-2 py-1 rounded-lg text-[10px] font-bold bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 inline-flex items-center gap-1">
                            <Check size={11} /> Accepter
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
    </div>
  );
};
