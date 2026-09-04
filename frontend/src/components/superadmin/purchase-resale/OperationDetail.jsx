import { useCallback, useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../../services/http';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

const Row = ({ label, value, accent }) => (
  <div className="flex justify-between text-xs py-0.5">
    <span className="text-white/55">{label}</span>
    <span className={accent || 'text-white/85'}>{value}</span>
  </div>
);

export const OperationDetail = ({ operationId, meta, onChanged }) => {
  const [detail, setDetail] = useState(null);
  const [tranche, setTranche] = useState({ financing_tranche: 'GOODS', investor_name: '', approved_amount: '' });
  const [disb, setDisb] = useState({ financing_tranche: 'GOODS', payee_category: 'SUPPLIER_GOODS', payee_name: '', amount: '', method: 'OSCOP_BANK_TRANSFER' });

  const load = useCallback(async () => {
    const res = await fetch(`${API}/admin/purchase-resale/operations/${operationId}`, { headers: getAuthHeaders() });
    if (res.ok) setDetail(await res.json());
  }, [operationId]);

  useEffect(() => { load(); }, [load]);

  const post = async (path, body, okMsg) => {
    try {
      const res = await fetch(`${API}/admin/purchase-resale/operations/${operationId}/${path}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify(body),
      });
      const json = await res.json();
      if (!res.ok) {
        const d = json.detail;
        throw new Error(typeof d === 'object' ? `${d.message} : ${(d.blockers || []).join(' • ')}` : d);
      }
      toast.success(okMsg);
      await load();
      onChanged();
    } catch (e) {
      toast.error(String(e.message || e));
    }
  };

  if (!detail) return <div className="p-4"><Loader2 className="w-4 h-4 animate-spin text-[#D9B35A]" /></div>;

  const op = detail.operation;
  const num = (v) => parseFloat(String(v).replace(',', '.')) || 0;

  return (
    <div className="mx-2 mb-3 mt-1 p-4 rounded-[14px] bg-black/25 border border-white/10 grid md:grid-cols-3 gap-4" data-testid={`operation-detail-${op.reference}`}>
      <div>
        <p className="text-[11px] font-semibold text-white/70 uppercase mb-1.5">Coût de revient & marge</p>
        <Row label="Prix fournisseur HT" value={eur(op.purchase_amount_ex_vat)} />
        <Row label="Coûts directs" value={eur(op.direct_costs_ex_vat)} />
        <Row label="Coût de revient complet" value={eur(op.full_cost_price_ex_vat)} />
        <Row label="Revente totale HT" value={eur(op.resale_total_ex_vat)} />
        <Row label="Marge marchandises" value={eur(op.expected_goods_margin_ex_vat)} />
        <Row label="Marge logistique" value={eur(op.expected_logistics_margin_ex_vat)} />
        <Row label="Marge consolidée" accent={op.expected_margin_ex_vat >= 0 ? 'text-emerald-300' : 'text-red-300'}
          value={`${eur(op.expected_margin_ex_vat)} (${op.expected_margin_rate}%)`} />
        <Row label="Taux de majoration sur coût" value={`${op.markup_rate}%`} />
        {op.blockers?.length > 0 && (
          <div className="mt-2 p-2 rounded bg-amber-500/10 border border-amber-400/25" data-testid="operation-blockers">
            {op.blockers.map((b) => <p key={b} className="text-amber-200 text-[11px]">• {b}</p>)}
          </div>
        )}
        <div className="mt-2">
          <label className="text-[10px] text-white/50">Changer le statut</label>
          <select
            data-testid="op-status-select"
            className="w-full bg-white/5 border border-white/15 rounded-md px-2 py-1.5 text-xs text-white"
            value={op.status}
            onChange={(e) => post('status', { status: e.target.value }, `Statut : ${e.target.value}`)}
          >
            {meta.statuses.map((s) => <option key={s} value={s} className="bg-[#2A1045]">{s}</option>)}
          </select>
        </div>
      </div>

      <div>
        <p className="text-[11px] font-semibold text-white/70 uppercase mb-1.5">Tranches de financement</p>
        {detail.tranches.length === 0 && <p className="text-white/40 text-xs">Aucune tranche approuvée.</p>}
        {detail.tranches.map((t) => (
          <div key={t.id} className="p-2 rounded bg-white/5 mb-1.5 text-[11px]">
            <div className="flex justify-between text-white/85"><span>{t.financing_tranche} — {t.investor_name}</span><span>{eur(t.approved_amount)}</span></div>
            <div className="flex justify-between text-white/50">
              <span>Décaissé ext. {eur(t.external_disbursed_amount)} · Alloué int. {eur(t.internal_allocated_amount)}</span>
              <span>Restant {eur(t.remaining_amount)}</span>
            </div>
          </div>
        ))}
        <div className="space-y-1.5 mt-2">
          <select value={tranche.financing_tranche} onChange={(e) => setTranche({ ...tranche, financing_tranche: e.target.value })}
            data-testid="tranche-type-select" className="w-full bg-white/5 border border-white/15 rounded-md px-2 py-1.5 text-xs text-white">
            {meta.tranches.map((t) => <option key={t} value={t} className="bg-[#2A1045]">{t}</option>)}
          </select>
          <Input placeholder="Investisseur" value={tranche.investor_name} data-testid="tranche-investor-input"
            onChange={(e) => setTranche({ ...tranche, investor_name: e.target.value })} className="bg-white/5 border-white/15 text-white h-8 text-xs" />
          <Input placeholder="Montant approuvé €" value={tranche.approved_amount} data-testid="tranche-amount-input"
            onChange={(e) => setTranche({ ...tranche, approved_amount: e.target.value })} className="bg-white/5 border-white/15 text-white h-8 text-xs" />
          <Button size="sm" data-testid="tranche-submit-btn" className="w-full bg-white/10 hover:bg-white/20 text-white text-xs"
            onClick={() => post('tranches', { ...tranche, approved_amount: num(tranche.approved_amount) }, 'Tranche approuvée')}>
            Approuver la tranche
          </Button>
        </div>
      </div>

      <div>
        <p className="text-[11px] font-semibold text-white/70 uppercase mb-1.5">Décaissements</p>
        {detail.disbursements.map((d) => (
          <div key={d.id} className="p-2 rounded bg-white/5 mb-1.5 text-[11px]">
            <div className="flex justify-between text-white/85"><span>{d.payee_category}</span><span>{eur(d.amount)}</span></div>
            <p className="text-white/45">{d.method}{d.internal_allocation ? " · allocation analytique interne LOGI'SCOP (sans facture)" : ''}{d.on_behalf_of ? ` · pour le compte de ${d.on_behalf_of}` : ''}</p>
          </div>
        ))}
        <div className="space-y-1.5 mt-2">
          <select value={disb.financing_tranche} onChange={(e) => setDisb({ ...disb, financing_tranche: e.target.value })}
            data-testid="disb-tranche-select" className="w-full bg-white/5 border border-white/15 rounded-md px-2 py-1.5 text-xs text-white">
            {meta.tranches.map((t) => <option key={t} value={t} className="bg-[#2A1045]">{t}</option>)}
          </select>
          <select value={disb.payee_category} onChange={(e) => setDisb({ ...disb, payee_category: e.target.value })}
            data-testid="disb-payee-select" className="w-full bg-white/5 border border-white/15 rounded-md px-2 py-1.5 text-xs text-white">
            {meta.payee_categories.map((c) => <option key={c} value={c} className="bg-[#2A1045]">{c}</option>)}
          </select>
          <select value={disb.method} onChange={(e) => setDisb({ ...disb, method: e.target.value })}
            data-testid="disb-method-select" className="w-full bg-white/5 border border-white/15 rounded-md px-2 py-1.5 text-xs text-white">
            {meta.methods.map((m) => <option key={m} value={m} className="bg-[#2A1045]">{m}</option>)}
          </select>
          <Input placeholder="Montant €" value={disb.amount} data-testid="disb-amount-input"
            onChange={(e) => setDisb({ ...disb, amount: e.target.value })} className="bg-white/5 border-white/15 text-white h-8 text-xs" />
          <Button size="sm" data-testid="disb-submit-btn" className="w-full bg-white/10 hover:bg-white/20 text-white text-xs"
            onClick={() => post('disbursements', { ...disb, amount: num(disb.amount) }, 'Décaissement enregistré')}>
            Enregistrer le décaissement
          </Button>
        </div>
      </div>
    </div>
  );
};
