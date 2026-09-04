import { useEffect, useState } from 'react';
import { Loader2, X } from 'lucide-react';
import { API, getAuthHeaders } from '../../../services/http';
import { Badge } from '../../ui/badge';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

const Block = ({ title, children }) => (
  <div className="p-3 rounded-[12px] bg-white/5 border border-white/10">
    <p className="text-[10px] font-semibold text-[#D9B35A] uppercase tracking-wide mb-1.5">{title}</p>
    {children}
  </div>
);

const L = ({ k, v }) => (
  <div className="flex justify-between text-[11px] py-0.5">
    <span className="text-white/50">{k}</span>
    <span className="text-white/85 text-right">{v ?? '-'}</span>
  </div>
);

export const Operation360 = ({ operationId, onClose }) => {
  const [d, setD] = useState(null);

  useEffect(() => {
    fetch(`${API}/admin/purchase-resale/operations/${operationId}/view360`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then(setD).catch(() => {});
  }, [operationId]);

  if (!d) return <div className="p-6"><Loader2 className="w-5 h-5 animate-spin text-[#D9B35A]" /></div>;
  const op = d.operation;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-start justify-center overflow-y-auto p-4" onClick={onClose}>
      <div className="max-w-4xl w-full my-6 rounded-[20px] bg-[#2A1045] border border-white/15 p-5" onClick={(e) => e.stopPropagation()} data-testid="operation-360">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-white">Vue 360° — {op.reference}</h3>
          <button onClick={onClose} data-testid="close-360" className="text-white/50 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="grid md:grid-cols-3 gap-3">
          <Block title="Acteurs">
            <L k="Client" v={op.client_name} />
            <L k="Fournisseur" v={op.supplier_name} />
            <L k="Email fournisseur" v={op.supplier_email} />
            <L k="Investisseur" v={op.investor_name} />
            <L k="Statut" v={op.status} />
          </Block>
          <Block title="Marge & coûts">
            <L k="Achat HT" v={eur(op.purchase_amount_ex_vat)} />
            <L k="Coût de revient complet" v={eur(op.full_cost_price_ex_vat)} />
            <L k="Revente totale HT" v={eur(op.resale_total_ex_vat)} />
            <L k="Marge consolidée" v={`${eur(op.expected_margin_ex_vat)} (${op.expected_margin_rate}%)`} />
            <L k="Appui FOGEDOM-SCIC" v={eur(op.fogedom_support_amount)} />
            {op.blockers?.length > 0 && <p className="text-amber-300 text-[10px] mt-1">⚠ {op.blockers.join(' • ')}</p>}
          </Block>
          <Block title="Financement">
            {d.tranches.length === 0 && <p className="text-white/40 text-[11px]">Aucune tranche.</p>}
            {d.tranches.map((t) => <L key={t.id} k={`${t.financing_tranche} (${t.investor_name})`} v={`${eur(t.approved_amount)} · restant ${eur(t.remaining_amount)}`} />)}
            <L k="Fournisseur payé" v={eur(op.supplier_paid_amount)} />
            <L k="Prestataires externes" v={eur(op.logistics_external_paid_amount)} />
            <L k="Alloc. interne LOGI'SCOP" v={eur(op.logiscop_internal_allocated_amount)} />
          </Block>
          <Block title={`Logistique (${op.logistics_status})`}>
            {d.shipments.map((s) => <L key={s.id} k={s.shipment_number} v={`${s.origin}→${s.destination} · ${s.status}`} />)}
            {d.warehouse.map((w) => <L key={w.id} k={`Stock ${w.movement}`} v={`${w.quantity} · ${w.location}`} />)}
            {d.pods.map((p) => <L key={p.id} k={p.pod_number} v={`reçu par ${p.received_by}`} />)}
            {d.shipments.length + d.warehouse.length + d.pods.length === 0 && <p className="text-white/40 text-[11px]">Aucun événement.</p>}
          </Block>
          <Block title="Documents">
            {d.documents.length === 0 && <p className="text-white/40 text-[11px]">Aucun document.</p>}
            {d.documents.map((doc) => <L key={doc.id} k={doc.doc_number} v={doc.created_at?.slice(0, 10)} />)}
            {d.fogedom.map((f) => <L key={f.id} k={`FOGEDOM ${f.purpose}`} v={`${f.status} ${f.approved_amount ? eur(f.approved_amount) : ''}`} />)}
          </Block>
          <Block title="Audit (20 derniers)">
            <div className="max-h-44 overflow-y-auto">
              {d.audit.map((a) => (
                <p key={a.id} className="text-[10px] text-white/55 py-0.5">
                  {a.created_at?.slice(0, 16).replace('T', ' ')} — <Badge className="bg-white/10 text-white/70 border-0 text-[8px]">{a.action}</Badge> {a.by}
                </p>
              ))}
            </div>
          </Block>
        </div>
      </div>
    </div>
  );
};
