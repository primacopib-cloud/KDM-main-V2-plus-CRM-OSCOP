import { useCallback, useEffect, useState } from 'react';
import { Repeat } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const opts = () => ({ headers: getAuthHeaders(), credentials: 'include' });
const jsonOpts = (method, body) => ({ method, headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, credentials: 'include', body: JSON.stringify(body) });
const inp = 'h-9 rounded-lg px-2.5 text-xs text-white bg-white/[0.05] border border-white/15';

export const CpcPlansAdminPanel = () => {
  const [plans, setPlans] = useState([]);
  const [subs, setSubs] = useState([]);
  const [edit, setEdit] = useState({});

  const load = useCallback(() => {
    fetch(`${API}/admin/cpc/plans`, opts()).then((r) => r.json())
      .then((d) => { setPlans(d.items || []); setSubs(d.subscriptions || []); }).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async (p) => {
    const e = edit[p.id] || {};
    const body = {
      label: e.label ?? p.label,
      price_ht_cents: Math.round(parseFloat(e.price ?? p.price_ht_cents / 100) * 100),
      monthly_cpc: parseInt(e.cpc ?? p.monthly_cpc, 10),
      active: e.active ?? p.active,
    };
    const r = await fetch(`${API}/admin/cpc/plans/${p.id}`, jsonOpts('PUT', body));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success('Formule mise à jour (sans effet rétroactif sur les abonnés en cours)');
    setEdit((s) => ({ ...s, [p.id]: undefined }));
    load();
  };

  return (
    <div className="glass-panel-soft rounded-[14px] p-4" data-testid="cpc-plans-admin-panel">
      <h3 className="text-xs font-bold text-white/70 uppercase mb-3 flex items-center gap-1.5">
        <Repeat className="w-3.5 h-3.5" /> Abonnements CPC (formules mensuelles — CPC inclus, validité 3 mois)
      </h3>
      <div className="space-y-2">
        {plans.map((p) => {
          const e = edit[p.id] || {};
          return (
            <div key={p.id} className="flex flex-wrap items-center gap-2" data-testid={`cpc-plan-${p.id}`}>
              <input className={`${inp} w-32`} value={e.label ?? p.label} onChange={(ev) => setEdit((s) => ({ ...s, [p.id]: { ...e, label: ev.target.value } }))} />
              <input className={`${inp} w-24`} type="number" step="0.01" value={e.price ?? (p.price_ht_cents / 100)} onChange={(ev) => setEdit((s) => ({ ...s, [p.id]: { ...e, price: ev.target.value } }))} data-testid={`cpc-plan-price-${p.id}`} />
              <span className="text-[10px] text-white/40">€ HT/mois</span>
              <input className={`${inp} w-20`} type="number" value={e.cpc ?? p.monthly_cpc} onChange={(ev) => setEdit((s) => ({ ...s, [p.id]: { ...e, cpc: ev.target.value } }))} />
              <span className="text-[10px] text-white/40">CPC/mois</span>
              <button type="button" onClick={() => setEdit((s) => ({ ...s, [p.id]: { ...e, active: !(e.active ?? p.active) } }))}
                className={`px-2 py-1 rounded text-[10px] font-bold ${(e.active ?? p.active) ? 'bg-[#7BC94E]/15 text-[#7BC94E]' : 'bg-red-500/15 text-red-400'}`}>
                {(e.active ?? p.active) ? 'ACTIF' : 'INACTIF'}
              </button>
              <button type="button" onClick={() => save(p)} data-testid={`cpc-plan-save-${p.id}`}
                className="px-3 py-1.5 rounded-lg text-[10.5px] font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }}>
                Enregistrer
              </button>
            </div>
          );
        })}
      </div>
      {subs.length > 0 && (
        <div className="mt-3 pt-3 border-t border-white/10">
          <p className="text-[10px] text-white/50 uppercase font-bold mb-1.5">Abonnés ({subs.length})</p>
          {subs.map((s) => (
            <div key={s.id} className="flex items-center gap-2 text-[11px] py-1 border-b border-white/5 last:border-0">
              <span className="flex-1 text-white/75">{s.email}</span>
              <span className="text-[#E9CF8E] font-bold">{s.plan_label} · {s.monthly_cpc} CPC/mois</span>
              <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${s.status === 'ACTIVE' ? 'bg-[#7BC94E]/15 text-[#7BC94E]' : 'bg-amber-500/15 text-amber-400'}`}>{s.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
