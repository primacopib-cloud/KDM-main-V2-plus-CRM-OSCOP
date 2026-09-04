import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { API, getAuthHeaders, getSessionToken } from '../../services/http';
import { Button } from '../ui/button';

export const FreightToOperation = ({ quote }) => {
  const [ops, setOps] = useState(null);
  const [selected, setSelected] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!getSessionToken()) return;
    fetch(`${API}/admin/purchase-resale/operations`, { headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => setOps(d.operations || []))
      .catch(() => {});
  }, []);

  if (!ops || !quote) return null;

  const inject = async () => {
    if (!selected) { toast.error('Choisissez une opération'); return; }
    setBusy(true);
    try {
      const det = await fetch(`${API}/admin/purchase-resale/operations/${selected}`, { headers: getAuthHeaders() }).then((r) => r.json());
      const costLines = { ...(det.operation.cost_lines || {}), main_freight: quote.total_ex_vat };
      if (quote.breakdown.transport_insurance > 0) {
        costLines.main_freight = quote.total_ex_vat - quote.breakdown.transport_insurance;
        costLines.transport_insurance = (det.operation.cost_lines?.transport_insurance || 0) + quote.breakdown.transport_insurance;
      }
      const res = await fetch(`${API}/admin/purchase-resale/operations/${selected}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ cost_lines: costLines }),
      });
      if (!res.ok) throw new Error('Injection impossible');
      const op = await res.json();
      toast.success(`Fret injecté dans ${op.reference} — coût de revient recalculé : ${Number(op.full_cost_price_ex_vat).toLocaleString('fr-FR')} €`);
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-3 pt-3 border-t border-white/10" data-testid="freight-to-operation">
      <p className="text-[10px] text-white/50 uppercase tracking-wide mb-1.5">Injecter dans une opération d'achat-revente</p>
      <div className="flex gap-1.5">
        <select value={selected} onChange={(e) => setSelected(e.target.value)} data-testid="freight-op-select"
          className="flex-1 bg-white/5 border border-white/15 rounded px-2 py-1.5 text-xs text-white">
          <option value="" className="bg-[#2A1045]">— opération —</option>
          {ops.map((o) => <option key={o.id} value={o.id} className="bg-[#2A1045]">{o.reference} · {o.client_name}</option>)}
        </select>
        <Button size="sm" onClick={inject} disabled={busy} data-testid="freight-inject-btn"
          className="bg-[#D9B35A] text-[#2A1045] hover:bg-[#F2D07A] h-8 text-xs">
          Injecter le fret
        </Button>
      </div>
    </div>
  );
};
