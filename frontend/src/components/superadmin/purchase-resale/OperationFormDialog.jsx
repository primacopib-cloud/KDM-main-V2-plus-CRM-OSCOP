import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../../services/http';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../ui/dialog';

const COST_LABELS = {
  pickup_precarriage: 'Enlèvement & pré-acheminement',
  main_freight: 'Fret principal',
  grouping_last_mile: 'Groupage & dernier km',
  transport_insurance: 'Assurance transport',
  duties_taxes: 'Droits & taxes non récupérables',
  octroi_mer: 'Octroi de mer',
  customs_transit: 'Transit & dédouanement',
  handling: 'Manutention',
  warehousing: 'Stockage & entreposage',
  order_preparation: 'Préparation de commandes',
  quality_control: 'Contrôle qualité',
  external_logistics_fees: 'Prestataires logistiques externes',
  internal_logiscop_cost: "Coût interne analytique LOGI'SCOP",
  fx_hedge: 'Couverture de change',
  goods_financing_cost: 'Coût financement marchandises',
  logistics_financing_cost: 'Coût financement logistique',
  other_direct_costs: 'Autres coûts directs',
};

const MODES = [
  ['CUSTOMER_HANDLED', 'Retrait / logistique client'],
  ['INTERNAL_LOGISCOP', "Interne LOGI'SCOP"],
  ['EXTERNAL_PROVIDER', 'Prestataires externes'],
  ['HYBRID', 'Hybride'],
];

export const OperationFormDialog = ({ open, onClose, onCreated }) => {
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    client_name: '', supplier_name: '', supplier_email: '', investor_name: '',
    purchase_amount_ex_vat: '', resale_amount_ex_vat: '', vat_rate: '8.5',
    logistics_mode: 'CUSTOMER_HANDLED', logistics_budget_ex_vat: '',
    logistics_resale_price_ex_vat: '', min_margin_rate: '0',
  });
  const [costs, setCosts] = useState({});

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const num = (v) => parseFloat(String(v).replace(',', '.')) || 0;

  const submit = async () => {
    if (!form.client_name || !form.supplier_name) {
      toast.error('Client et fournisseur requis');
      return;
    }
    setSaving(true);
    try {
      const res = await fetch(`${API}/admin/purchase-resale/operations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          client_name: form.client_name,
          supplier_name: form.supplier_name,
          supplier_email: form.supplier_email ? form.supplier_email.toLowerCase() : null,
          investor_name: form.investor_name || null,
          purchase_amount_ex_vat: num(form.purchase_amount_ex_vat),
          resale_amount_ex_vat: num(form.resale_amount_ex_vat),
          vat_rate: num(form.vat_rate),
          logistics_mode: form.logistics_mode,
          logistics_budget_ex_vat: num(form.logistics_budget_ex_vat),
          logistics_resale_price_ex_vat: num(form.logistics_resale_price_ex_vat),
          min_margin_rate: num(form.min_margin_rate),
          cost_lines: Object.fromEntries(Object.entries(costs).map(([k, v]) => [k, num(v)])),
        }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Erreur');
      const op = await res.json();
      toast.success(`Opération ${op.reference} créée`);
      onCreated(op);
      onClose();
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setSaving(false);
    }
  };

  const field = (label, key, ph = '0,00') => (
    <div>
      <label className="text-xs text-white/60">{label}</label>
      <Input value={form[key]} onChange={set(key)} placeholder={ph}
        data-testid={`op-form-${key}`} className="bg-white/5 border-white/15 text-white" />
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto bg-[#2A1045] border-white/15 text-white">
        <DialogHeader>
          <DialogTitle>Nouvelle opération d'achat-revente O'SCOP</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          {field('Client', 'client_name', 'Nom du client')}
          {field('Fournisseur', 'supplier_name', 'Nom du fournisseur')}
          {field('Email fournisseur (espace fournisseur)', 'supplier_email', 'fournisseur@exemple.fr')}
          {field('Investisseur (optionnel)', 'investor_name', 'Nom')}
          {field('Prix fournisseur HT (€)', 'purchase_amount_ex_vat')}
          {field('Prix de revente marchandises HT (€)', 'resale_amount_ex_vat')}
          {field('TVA (%)', 'vat_rate')}
          <div>
            <label className="text-xs text-white/60">Mode logistique</label>
            <select value={form.logistics_mode} onChange={set('logistics_mode')}
              data-testid="op-form-logistics-mode"
              className="w-full bg-white/5 border border-white/15 rounded-md px-3 py-2 text-sm text-white">
              {MODES.map(([v, l]) => <option key={v} value={v} className="bg-[#2A1045]">{l}</option>)}
            </select>
          </div>
          {field('Budget logistique HT (€)', 'logistics_budget_ex_vat')}
          {field('Prix de revente logistique HT (€)', 'logistics_resale_price_ex_vat')}
          {field('Seuil de marge minimal (%)', 'min_margin_rate')}
        </div>
        <p className="text-xs text-white/50 font-semibold uppercase tracking-wide mt-2">Coûts directs (coût de revient complet)</p>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(COST_LABELS).map(([k, label]) => (
            <div key={k}>
              <label className="text-[10px] text-white/50">{label}</label>
              <Input value={costs[k] || ''} onChange={(e) => setCosts({ ...costs, [k]: e.target.value })}
                placeholder="0,00" data-testid={`op-cost-${k}`} className="bg-white/5 border-white/15 text-white h-8 text-sm" />
            </div>
          ))}
        </div>
        <Button onClick={submit} disabled={saving} data-testid="op-form-submit"
          className="bg-[#D9B35A] text-[#2A1045] hover:bg-[#F2D07A] font-semibold mt-2">
          {saving && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
          Créer l'opération
        </Button>
      </DialogContent>
    </Dialog>
  );
};

export { COST_LABELS, MODES };
