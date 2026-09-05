import { useState, useEffect } from 'react';
import { Landmark, Eye, EyeOff, Trash2, Save } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Gestion des plans d'abonnement investisseur (ULTIMATE/VIP/ELITE)
export const InvestorPlansAdminPanel = () => {
  const [plans, setPlans] = useState([]);
  const load = () => {
    fetch(`${API_URL}/api/investor-plans/admin`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then((d) => setPlans(d.plans || [])).catch(() => {});
  };
  useEffect(load, []);

  const update = async (id, payload, msg) => {
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/admin/${id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Erreur');
      toast.success(msg);
      load();
    } catch (e) { toast.error(e.message); }
  };

  const remove = async (p) => {
    if (!window.confirm(`Supprimer le plan ${p.name} ?`)) return;
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/admin/${p.id}`, { method: 'DELETE', headers: getAuthHeaders() });
      if (!res.ok) throw new Error((await res.json()).detail || 'Erreur');
      toast.success(`Plan ${p.name} supprimé`);
      load();
    } catch (e) { toast.error(e.message); }
  };

  const edit = (i, field, value) => setPlans((prev) => prev.map((p, j) => (j === i ? { ...p, [field]: value } : p)));

  return (
    <div className="rounded-2xl bg-white/[0.03] border border-white/[0.08] p-5 mt-6" data-testid="investor-plans-admin">
      <h3 className="text-sm font-bold text-[#E9CF8E] flex items-center gap-2 m-0 mb-3">
        <Landmark className="w-4 h-4" /> Plans abonnement investisseur (formulaire FINANCER)
      </h3>
      <div className="space-y-3">
        {plans.map((p, i) => (
          <div key={p.id} className="rounded-xl p-3 bg-white/[0.02] border border-white/[0.08]" data-testid={`investor-plan-row-${p.code}`}>
            <div className="flex items-center gap-2 flex-wrap">
              <input value={p.name} onChange={(e) => edit(i, 'name', e.target.value)}
                data-testid={`plan-name-${p.code}`}
                className="h-8 w-32 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs font-bold" />
              <label className="text-[11px] text-white/50 flex items-center gap-1">Prix €/mois
                <input type="number" value={p.price_eur} onChange={(e) => edit(i, 'price_eur', Number(e.target.value))}
                  data-testid={`plan-price-${p.code}`}
                  className="h-8 w-28 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs" />
              </label>
              <label className="text-[11px] text-white/50 flex items-center gap-1">Quota uc/mois
                <input type="number" value={p.monthly_invest_uc} onChange={(e) => edit(i, 'monthly_invest_uc', Number(e.target.value))}
                  data-testid={`plan-quota-${p.code}`}
                  className="h-8 w-32 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs" />
              </label>
              <div className="ml-auto flex items-center gap-1.5">
                <button type="button" title={p.visible ? 'Masquer' : 'Afficher'} data-testid={`plan-toggle-${p.code}`}
                  onClick={() => update(p.id, { visible: !p.visible }, p.visible ? `Plan ${p.name} masqué` : `Plan ${p.name} affiché`)}
                  className={`p-1.5 rounded-md border ${p.visible ? 'text-[#8CC63E] border-[#8CC63E]/40 bg-[#8CC63E]/10' : 'text-white/40 border-white/15 bg-white/[0.04]'}`}>
                  {p.visible ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                </button>
                <button type="button" title="Enregistrer" data-testid={`plan-save-${p.code}`}
                  onClick={() => update(p.id, { name: p.name, price_eur: p.price_eur, monthly_invest_uc: p.monthly_invest_uc, description: p.description }, `Plan ${p.name} mis à jour`)}
                  className="p-1.5 rounded-md text-black bg-[#D9B35A] hover:bg-[#c9a34a]"><Save className="w-3.5 h-3.5" /></button>
                <button type="button" title="Supprimer" data-testid={`plan-delete-${p.code}`}
                  onClick={() => remove(p)}
                  className="p-1.5 rounded-md text-red-300 border border-red-400/30 bg-red-500/10 hover:bg-red-500/20"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            </div>
            <textarea value={p.description} onChange={(e) => edit(i, 'description', e.target.value)}
              data-testid={`plan-desc-${p.code}`} rows={2}
              className="mt-2 w-full px-2 py-1.5 rounded-md bg-white/[0.04] border border-white/10 text-white/80 text-[11px]" />
          </div>
        ))}
      </div>
    </div>
  );
};
