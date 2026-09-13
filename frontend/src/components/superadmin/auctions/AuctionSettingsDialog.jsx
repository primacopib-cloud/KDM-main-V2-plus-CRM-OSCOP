import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../../services/http';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../ui/dialog';
import { Input } from '../../ui/input';
import { Button } from '../../ui/button';

const hAuth = () => ({ 'Content-Type': 'application/json', ...getAuthHeaders() });

const Row = ({ item, onToggle, onDelete }) => (
  <div className="flex items-center gap-2 text-xs py-1 border-b border-white/[0.06]">
    <span className={item.active ? 'text-white/80' : 'text-white/35 line-through'}>{item.label}</span>
    {item.bid_cost_credits != null && (
      <span className="text-white/40">({item.bid_cost_credits} cr. / −{item.price_drop_eur} €)</span>
    )}
    {item.credits != null && (
      <span className="text-white/40">({(item.price_ht_cents / 100).toFixed(2)} € HT · {item.credits} cr. · {item.validity_days} j)</span>
    )}
    <div className="ml-auto flex gap-1">
      <button type="button" onClick={onToggle} className="px-1.5 py-0.5 rounded text-[10px] bg-white/10 text-white/60 hover:bg-white/20">
        {item.active ? 'Désactiver' : 'Activer'}
      </button>
      {onDelete && (
        <button type="button" onClick={onDelete} className="px-1.5 py-0.5 rounded text-[10px] bg-red-500/15 text-red-300 hover:bg-red-500/25">
          Suppr.
        </button>
      )}
    </div>
  </div>
);

// Gestion des catégories, types d'enchères et plans CREDI'SCOP-Enchères
export const AuctionSettingsDialog = ({ onClose, onChanged }) => {
  const [cats, setCats] = useState([]);
  const [types, setTypes] = useState([]);
  const [plans, setPlans] = useState([]);
  const [catLabel, setCatLabel] = useState('');
  const [typeForm, setTypeForm] = useState({ label: '', bid_cost_credits: 10, price_drop_eur: 1 });
  const [planForm, setPlanForm] = useState({ label: '', price_ht_cents: '', credits: '', validity_days: 30 });

  const load = useCallback(async () => {
    const h = { headers: getAuthHeaders(), credentials: 'include' };
    const [c, t, p] = await Promise.all([
      fetch(`${API}/admin/auctions/taxonomy/categories`, h).then((r) => r.json()),
      fetch(`${API}/admin/auctions/taxonomy/types`, h).then((r) => r.json()),
      fetch(`${API}/admin/auctions/plans`, h).then((r) => r.json()),
    ]);
    setCats(c.items || []); setTypes(t.items || []); setPlans(p.items || []);
  }, []);

  useEffect(() => { load(); }, [load]);

  const post = async (url, body, okMsg) => {
    const res = await fetch(url, { method: 'POST', headers: hAuth(), credentials: 'include', body: JSON.stringify(body) });
    const d = await res.json();
    if (!res.ok) { toast.error(d.detail || 'Erreur'); return false; }
    toast.success(okMsg); load(); onChanged?.();
    return true;
  };

  const toggle = async (kind, item) => {
    const url = kind === 'plans'
      ? `${API}/admin/auctions/plans/${item.id}` : `${API}/admin/auctions/taxonomy/${kind}/${item.id}`;
    const body = kind === 'plans'
      ? { label: item.label, price_ht_cents: item.price_ht_cents, credits: item.credits, validity_days: item.validity_days, active: !item.active }
      : { active: !item.active };
    const res = await fetch(url, { method: 'PUT', headers: hAuth(), credentials: 'include', body: JSON.stringify(body) });
    if (res.ok) { load(); onChanged?.(); } else toast.error('Erreur');
  };

  const remove = async (kind, item) => {
    const res = await fetch(`${API}/admin/auctions/taxonomy/${kind}/${item.id}`, {
      method: 'DELETE', headers: getAuthHeaders(), credentials: 'include' });
    const d = await res.json();
    if (!res.ok) { toast.error(d.detail || 'Erreur'); return; }
    load(); onChanged?.();
  };

  const inputCls = 'bg-white/[0.05] border-white/15 text-white text-xs h-8';
  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#2A1045] border-[#D9B35A]/30 text-white max-w-xl max-h-[85vh] overflow-y-auto"
        data-testid="auction-settings-dialog">
        <DialogHeader>
          <DialogTitle className="text-[#E9CF8E]">Catégories · Types d'enchères · Plans</DialogTitle>
        </DialogHeader>

        <section data-testid="auction-categories-section">
          <h4 className="text-xs font-bold text-white/70 uppercase mb-1">Catégories</h4>
          {cats.map((c) => <Row key={c.id} item={c} onToggle={() => toggle('categories', c)} onDelete={() => remove('categories', c)} />)}
          <div className="flex gap-2 mt-2">
            <Input value={catLabel} onChange={(e) => setCatLabel(e.target.value)} placeholder="Nouvelle catégorie…"
              className={inputCls} data-testid="new-category-input" />
            <Button size="sm" disabled={!catLabel.trim()} data-testid="add-category-btn"
              onClick={async () => { if (await post(`${API}/admin/auctions/taxonomy/categories`, { label: catLabel.trim() }, 'Catégorie créée')) setCatLabel(''); }}
              className="bg-[#D9B35A] text-[#2A1045] h-8">+</Button>
          </div>
        </section>

        <section data-testid="auction-types-section">
          <h4 className="text-xs font-bold text-white/70 uppercase mb-1 mt-3">Types d'enchères (conditions de mise)</h4>
          {types.map((t) => <Row key={t.id} item={t} onToggle={() => toggle('types', t)} onDelete={() => remove('types', t)} />)}
          <div className="grid grid-cols-4 gap-2 mt-2">
            <Input value={typeForm.label} onChange={(e) => setTypeForm((f) => ({ ...f, label: e.target.value }))}
              placeholder="Libellé…" className={`${inputCls} col-span-2`} data-testid="new-type-label" />
            <Input type="number" value={typeForm.bid_cost_credits} title="Coût mise (crédits)"
              onChange={(e) => setTypeForm((f) => ({ ...f, bid_cost_credits: e.target.value }))}
              className={inputCls} data-testid="new-type-cost" />
            <Input type="number" step="0.1" value={typeForm.price_drop_eur} title="Baisse (€)"
              onChange={(e) => setTypeForm((f) => ({ ...f, price_drop_eur: e.target.value }))}
              className={inputCls} data-testid="new-type-drop" />
          </div>
          <Button size="sm" disabled={!typeForm.label.trim()} data-testid="add-type-btn"
            onClick={async () => {
              const ok = await post(`${API}/admin/auctions/taxonomy/types`, {
                label: typeForm.label.trim(), bid_cost_credits: parseInt(typeForm.bid_cost_credits, 10),
                price_drop_eur: parseFloat(typeForm.price_drop_eur) }, 'Type créé');
              if (ok) setTypeForm({ label: '', bid_cost_credits: 10, price_drop_eur: 1 });
            }}
            className="bg-[#D9B35A] text-[#2A1045] h-8 mt-2">Ajouter le type</Button>
        </section>

        <section data-testid="auction-plans-section">
          <h4 className="text-xs font-bold text-white/70 uppercase mb-1 mt-3">Plans CREDI'SCOP-Enchères (obligatoires pour enchérir)</h4>
          {plans.map((p) => <Row key={p.id} item={p} onToggle={() => toggle('plans', p)} />)}
          <div className="grid grid-cols-4 gap-2 mt-2">
            <Input value={planForm.label} onChange={(e) => setPlanForm((f) => ({ ...f, label: e.target.value }))}
              placeholder="Libellé…" className={inputCls} data-testid="new-plan-label" />
            <Input type="number" value={planForm.price_ht_cents} placeholder="Prix HT (cts)"
              onChange={(e) => setPlanForm((f) => ({ ...f, price_ht_cents: e.target.value }))}
              className={inputCls} data-testid="new-plan-price" />
            <Input type="number" value={planForm.credits} placeholder="Crédits"
              onChange={(e) => setPlanForm((f) => ({ ...f, credits: e.target.value }))}
              className={inputCls} data-testid="new-plan-credits" />
            <Input type="number" value={planForm.validity_days} placeholder="Jours"
              onChange={(e) => setPlanForm((f) => ({ ...f, validity_days: e.target.value }))}
              className={inputCls} data-testid="new-plan-days" />
          </div>
          <Button size="sm" disabled={!planForm.label.trim() || !planForm.price_ht_cents || !planForm.credits}
            data-testid="add-plan-btn"
            onClick={async () => {
              const ok = await post(`${API}/admin/auctions/plans`, {
                label: planForm.label.trim(), price_ht_cents: parseInt(planForm.price_ht_cents, 10),
                credits: parseInt(planForm.credits, 10), validity_days: parseInt(planForm.validity_days, 10) }, 'Plan créé');
              if (ok) setPlanForm({ label: '', price_ht_cents: '', credits: '', validity_days: 30 });
            }}
            className="bg-[#D9B35A] text-[#2A1045] h-8 mt-2">Ajouter le plan</Button>
        </section>
      </DialogContent>
    </Dialog>
  );
};
