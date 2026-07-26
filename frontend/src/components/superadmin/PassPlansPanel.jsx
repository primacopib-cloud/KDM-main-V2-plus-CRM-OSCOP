import { useEffect, useState } from 'react';
import { BatteryCharging, Plus, Trash2, Save } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const numCls = 'w-20 h-8 rounded-md px-2 text-[11.5px] text-white bg-white/[0.06] border border-white/15 focus:outline-none text-right';

const PlanRow = ({ plan, onSave, onDelete }) => {
  const [p, setP] = useState(plan);
  const set = (k) => (e) => setP({ ...p, [k]: e.target.value });
  return (
    <div className="flex flex-wrap items-center gap-2 py-1.5 border-b border-white/5 last:border-0" data-testid={`pass-plan-${plan.id}`}>
      <span className={`flex-1 min-w-[140px] text-[11.5px] font-semibold ${plan.kind === 'adhesion' ? 'text-[#E9CF8E]' : 'text-white/75'}`}>
        {plan.label}{plan.kind === 'adhesion' && <span className="ml-1.5 text-[9px] uppercase text-[#D9B35A]">Adhésion</span>}
      </span>
      <label className="text-[10px] text-white/40">€ <input type="number" step="0.5" value={p.price_eur} onChange={set('price_eur')} className={numCls} data-testid={`plan-price-${plan.id}`} /></label>
      <label className="text-[10px] text-white/40">UC <input type="number" value={p.uc} onChange={set('uc')} className={numCls} data-testid={`plan-uc-${plan.id}`} /></label>
      <label className="text-[10px] text-white/40">Bonus <input type="number" value={p.bonus_uc} onChange={set('bonus_uc')} className={numCls} data-testid={`plan-bonus-${plan.id}`} /></label>
      <label className="flex items-center gap-1 text-[10.5px] text-white/55">
        <input type="checkbox" checked={!!p.active} onChange={(e) => setP({ ...p, active: e.target.checked })} data-testid={`plan-active-${plan.id}`} /> actif
      </label>
      <button type="button" onClick={() => onSave(plan.id, p)} data-testid={`plan-save-${plan.id}`}
        className="p-1.5 rounded-md bg-white/10 text-[#E9CF8E] hover:bg-white/15" title="Enregistrer"><Save className="w-3.5 h-3.5" /></button>
      {plan.kind !== 'adhesion' && (
        <button type="button" onClick={() => onDelete(plan.id)} data-testid={`plan-delete-${plan.id}`}
          className="p-1.5 rounded-md bg-white/10 text-red-400 hover:bg-white/15" title="Supprimer"><Trash2 className="w-3.5 h-3.5" /></button>
      )}
    </div>
  );
};

export const PassPlansPanel = () => {
  const [plans, setPlans] = useState(null);
  const opts = { headers: getAuthHeaders(), credentials: 'include' };
  const jsonOpts = { ...opts, headers: { ...opts.headers, 'Content-Type': 'application/json' } };

  const load = () => {
    fetch(`${API}/admin/pass-plans`, opts).then((r) => (r.ok ? r.json() : null)).then((d) => setPlans(d?.plans || [])).catch(() => {});
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, []);

  const call = async (url, method, body) => {
    const r = await fetch(url, { ...jsonOpts, method, body: body ? JSON.stringify(body) : undefined });
    if (r.ok) { load(); return true; }
    toast.error((await r.json()).detail || 'Erreur');
    return false;
  };

  const save = async (id, p) => {
    if (await call(`${API}/admin/pass-plans/${id}`, 'PATCH', {
      label: p.label || '', price_eur: Number(p.price_eur), uc: Number(p.uc),
      bonus_uc: Number(p.bonus_uc || 0), active: !!p.active,
    })) toast.success('Plan mis à jour');
  };
  const del = async (id) => { if (await call(`${API}/admin/pass-plans/${id}`, 'DELETE')) toast.success('Plan supprimé'); };
  const add = async () => {
    if (await call(`${API}/admin/pass-plans`, 'POST', { price_eur: 50, uc: 500, bonus_uc: 0, active: true })) {
      toast.success('Plan de recharge ajouté — ajustez ses valeurs');
    }
  };

  if (!plans) return null;
  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mt-6" data-testid="pass-plans-panel">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold text-[#D9B35A] flex items-center gap-2">
          <BatteryCharging className="w-4 h-4" /> Plans PASS LOLODRIVE (adhésion & recharges UC)
        </h3>
        <button type="button" onClick={add} data-testid="pass-plan-add-btn"
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10.5px] font-bold bg-white/10 text-[#E9CF8E] hover:bg-white/15 transition-colors">
          <Plus className="w-3 h-3" /> Ajouter une recharge
        </button>
      </div>
      <p className="text-[10.5px] text-white/40 mb-3">UC = Unités de consommation. Les plans actifs sont affichés sur la page publique PASS LOLODRIVE.</p>
      {plans.map((p) => <PlanRow key={p.id + String(p.updated_at || '')} plan={p} onSave={save} onDelete={del} />)}
    </div>
  );
};
