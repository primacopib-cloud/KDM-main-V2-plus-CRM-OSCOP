import { useState, useEffect } from 'react';
import { Landmark, Eye, EyeOff, Trash2, Save, Users, FileCheck, Euro } from 'lucide-react';
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
      <InvestorSubscribersTable />
      <RibValidationSection />
    </div>
  );
};

const STATUS_LABEL = { ACTIVE: ['À jour', 'text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/30'], PAST_DUE: ['Échec paiement', 'text-red-300 bg-red-500/10 border-red-400/40'] };
const fmtD = (iso) => new Date(iso).toLocaleDateString('fr-FR');

// Tableau des investisseurs abonnés : statut de paiement + prochaine échéance
const InvestorSubscribersTable = () => {
  const [subs, setSubs] = useState([]);
  useEffect(() => {
    fetch(`${API_URL}/api/investor-plans/admin/subscribers`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then((d) => setSubs(d.subscribers || [])).catch(() => {});
  }, []);

  const recordRepayment = async (s) => {
    const amount = window.prompt(`Montant du remboursement versé à ${s.email} (en €) :`);
    if (!amount || !Number(amount)) return;
    const reference = window.prompt('Référence du virement bancaire :');
    if (!reference) return;
    const operationRef = window.prompt('Opération liée (optionnel) :') || null;
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/admin/repayments`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ user_id: s.user_id, amount_eur: Number(amount), reference, operation_ref: operationRef }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(`Remboursement de ${Number(amount).toLocaleString('fr-FR')} € tracé (réf. ${reference})`);
    } catch (e) { toast.error(e.message); }
  };
  if (!subs.length) return null;
  return (
    <div className="mt-5" data-testid="investor-subscribers-table">
      <h4 className="text-xs font-bold text-[#E9CF8E] flex items-center gap-1.5 m-0 mb-2">
        <Users className="w-3.5 h-3.5" /> Investisseurs abonnés ({subs.length})
      </h4>
      <div className="overflow-x-auto rounded-xl border border-white/[0.08]">
        <table className="w-full text-[11px] text-white/70">
          <thead>
            <tr className="bg-white/[0.04] text-white/45 text-left">
              <th className="px-3 py-2 font-semibold">Investisseur</th>
              <th className="px-3 py-2 font-semibold">Plan</th>
              <th className="px-3 py-2 font-semibold">Paiement</th>
              <th className="px-3 py-2 font-semibold text-right">Solde uc</th>
              <th className="px-3 py-2 font-semibold">Période en cours</th>
              <th className="px-3 py-2 font-semibold">Prochaine échéance</th>
              <th className="px-3 py-2 font-semibold">Remboursement</th>
            </tr>
          </thead>
          <tbody>
            {subs.map((s) => {
              const [label, cls] = STATUS_LABEL[s.status] || [s.status, 'text-white/50 bg-white/5 border-white/15'];
              return (
                <tr key={s.user_id} className="border-t border-white/[0.06]" data-testid={`subscriber-row-${s.email}`}>
                  <td className="px-3 py-2"><span className="text-white font-semibold">{s.name || '—'}</span><br /><span className="text-white/40">{s.email}</span></td>
                  <td className="px-3 py-2 font-bold text-[#D9B35A]">{s.plan_code}</td>
                  <td className="px-3 py-2"><span className={`px-2 py-0.5 rounded-full border font-semibold ${cls}`}>{label}</span></td>
                  <td className="px-3 py-2 text-right font-mono">{(s.balance_uc ?? 0).toLocaleString('fr-FR')}</td>
                  <td className="px-3 py-2">{fmtD(s.period_start)}</td>
                  <td className="px-3 py-2 font-semibold text-white">{fmtD(s.next_due)}</td>
                  <td className="px-3 py-2">
                    <button type="button" onClick={() => recordRepayment(s)} data-testid={`repayment-btn-${s.email}`}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-bold text-black bg-[#8CC63E] hover:bg-[#7ab52f] transition-colors">
                      <Euro className="w-3 h-3" /> Virement
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const RIB_BADGE = { PENDING: ['En attente', 'text-amber-300 bg-amber-500/10 border-amber-400/40'], APPROVED: ['Approuvé', 'text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/30'], REJECTED: ['Refusé', 'text-red-300 bg-red-500/10 border-red-400/40'] };

// Validation des RIB téléversés avant tout remboursement
const RibValidationSection = () => {
  const [ribs, setRibs] = useState([]);
  const load = () => {
    fetch(`${API_URL}/api/investor-plans/admin/rib-list`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then((d) => setRibs(d.ribs || [])).catch(() => {});
  };
  useEffect(load, []);

  const decide = async (r, decision) => {
    const note = decision === 'reject' ? window.prompt('Motif du refus (envoyé à l\'investisseur) :') || '' : null;
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/admin/rib/${r.user_id}/decision`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ decision, note }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(decision === 'approve' ? 'RIB approuvé' : 'RIB refusé');
      load();
    } catch (e) { toast.error(e.message); }
  };

  const viewRib = async (r) => {
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/admin/rib/${r.user_id}`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Consultation impossible');
      const blob = await res.blob();
      window.open(URL.createObjectURL(blob), '_blank');
    } catch (e) { toast.error(e.message); }
  };

  if (!ribs.length) return null;
  return (
    <div className="mt-5" data-testid="rib-validation-section">
      <h4 className="text-xs font-bold text-[#E9CF8E] flex items-center gap-1.5 m-0 mb-2">
        <FileCheck className="w-3.5 h-3.5" /> Validation des RIB investisseurs ({ribs.length})
      </h4>
      <div className="space-y-1.5">
        {ribs.map((r) => {
          const [label, cls] = RIB_BADGE[r.rib_status || 'PENDING'] || RIB_BADGE.PENDING;
          return (
            <div key={r.user_id} className="flex items-center gap-2 flex-wrap text-[11px] text-white/70 rounded-lg px-3 py-2 bg-white/[0.02] border border-white/[0.06]" data-testid={`rib-row-${r.email}`}>
              <span className="text-white font-semibold">{r.investor_name || '—'}</span>
              <span className="text-white/40">{r.email}</span>
              <span className="font-mono text-white/40">IBAN …{(r.iban || '').slice(-4)}</span>
              <span className={`px-2 py-0.5 rounded-full border font-semibold ${cls}`}>{label}</span>
              <span className="ml-auto flex gap-1.5">
                <button type="button" onClick={() => viewRib(r)} data-testid={`rib-view-${r.email}`}
                  className="px-2 py-1 rounded-md font-semibold text-white/70 bg-white/[0.05] border border-white/15 hover:bg-white/[0.1] transition-colors">Consulter</button>
                {r.rib_status !== 'APPROVED' && (
                  <button type="button" onClick={() => decide(r, 'approve')} data-testid={`rib-approve-${r.email}`}
                    className="px-2 py-1 rounded-md font-bold text-black bg-[#8CC63E] hover:bg-[#7ab52f] transition-colors">Approuver</button>
                )}
                {r.rib_status !== 'REJECTED' && (
                  <button type="button" onClick={() => decide(r, 'reject')} data-testid={`rib-reject-${r.email}`}
                    className="px-2 py-1 rounded-md font-bold text-white bg-red-500/70 hover:bg-red-500 transition-colors">Refuser</button>
                )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
