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
      <RepaymentsJournal />
    </div>
  );
};

const STATUS_LABEL = { ACTIVE: ['À jour', 'text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/30'], PAST_DUE: ['Échec paiement', 'text-red-300 bg-red-500/10 border-red-400/40'] };
const fmtD = (iso) => new Date(iso).toLocaleDateString('fr-FR');

// Tableau des investisseurs abonnés : statut de paiement + prochaine échéance
const InvestorSubscribersTable = () => {
  const [subs, setSubs] = useState([]);
  const [dlg, setDlg] = useState(null);
  const [fiche, setFiche] = useState(null);
  useEffect(() => {
    fetch(`${API_URL}/api/investor-plans/admin/subscribers`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then((d) => setSubs(d.subscribers || [])).catch(() => {});
  }, []);

  const recordRepayment = async (s) => {
    let ops = [];
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/admin/repayment-prefill/${s.user_id}`, { headers: getAuthHeaders() });
      ops = (await res.json()).operations || [];
    } catch { /* saisie libre */ }
    setDlg({ sub: s, ops, amount: '', reference: '', operationRef: '' });
  };

  const openFiche = async (s) => {
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/admin/investor-360/${s.user_id}`, { headers: getAuthHeaders() });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      setFiche(d);
    } catch (e) { toast.error(e.message); }
  };

  const submitRepayment = async () => {
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/admin/repayments`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ user_id: dlg.sub.user_id, amount_eur: Number(dlg.amount), reference: dlg.reference, operation_ref: dlg.operationRef || null }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(d.message || `Remboursement de ${Number(dlg.amount).toLocaleString('fr-FR')} € tracé`);
      setDlg(null);
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
                    <span className="flex gap-1.5">
                      <button type="button" onClick={() => recordRepayment(s)} data-testid={`repayment-btn-${s.email}`}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-bold text-black bg-[#8CC63E] hover:bg-[#7ab52f] transition-colors">
                        <Euro className="w-3 h-3" /> Virement
                      </button>
                      <button type="button" onClick={() => openFiche(s)} data-testid={`fiche360-btn-${s.email}`}
                        className="px-2 py-1 rounded-md text-[10px] font-bold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30 hover:bg-white/[0.1] transition-colors">
                        Fiche 360
                      </button>
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {dlg && (
        <div className="mt-3 rounded-xl p-3 bg-white/[0.04] border border-[#D9B35A]/40" data-testid="repayment-dialog">
          <p className="text-xs font-bold text-[#E9CF8E] m-0 mb-2">Virement de remboursement — {dlg.sub.email}</p>
          {dlg.ops.length > 0 && (
            <select data-testid="repayment-op-select" defaultValue=""
              onChange={(e) => {
                const op = dlg.ops.find((o) => o.ledger_id === e.target.value);
                if (op) setDlg({ ...dlg, amount: String(op.amount_eur), operationRef: op.operation_ref });
              }}
              className="mb-2 w-full h-8 px-2 rounded-md bg-[#2A1E4E] border border-white/15 text-white text-xs">
              <option value="">Pré-remplir depuis une opération financée…</option>
              {dlg.ops.map((o) => (
                <option key={o.ledger_id} value={o.ledger_id}>
                  {o.operation_ref} — {o.amount_eur.toLocaleString('fr-FR')} € ({new Date(o.financed_at).toLocaleDateString('fr-FR')})
                </option>
              ))}
            </select>
          )}
          <div className="flex gap-2 flex-wrap">
            <input type="number" placeholder="Montant €" value={dlg.amount} data-testid="repayment-amount-input"
              onChange={(e) => setDlg({ ...dlg, amount: e.target.value })}
              className="h-8 w-32 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs" />
            <input placeholder="Référence virement" value={dlg.reference} data-testid="repayment-reference-input"
              onChange={(e) => setDlg({ ...dlg, reference: e.target.value })}
              className="h-8 w-40 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs" />
            <input placeholder="Opération (optionnel)" value={dlg.operationRef} data-testid="repayment-operation-input"
              onChange={(e) => setDlg({ ...dlg, operationRef: e.target.value })}
              className="h-8 w-40 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs" />
            <button type="button" onClick={submitRepayment} disabled={!Number(dlg.amount) || !dlg.reference}
              data-testid="repayment-submit-btn"
              className="px-3 py-1.5 rounded-md text-xs font-bold text-black bg-[#8CC63E] hover:bg-[#7ab52f] disabled:opacity-40 transition-colors">
              Enregistrer le virement
            </button>
            <button type="button" onClick={() => setDlg(null)} data-testid="repayment-cancel-btn"
              className="px-3 py-1.5 rounded-md text-xs font-semibold text-white/60 bg-white/[0.05] border border-white/15 hover:bg-white/[0.1] transition-colors">
              Annuler
            </button>
          </div>
        </div>
      )}
      {fiche && (
        <div className="mt-3 rounded-xl p-4 bg-white/[0.04] border border-[#D9B35A]/40" data-testid="investor-360-card">
          <div className="flex items-center gap-2 mb-3">
            <p className="text-sm font-bold text-[#E9CF8E] m-0">Fiche investisseur 360 — {fiche.investor.name || fiche.investor.email}</p>
            <span className="text-[11px] text-white/40">{fiche.investor.email}</span>
            <button type="button" data-testid="fiche360-pdf-btn"
              onClick={async () => {
                try {
                  const res = await fetch(`${API_URL}/api/investor-plans/admin/investor-360/${fiche.investor.user_id}/pdf`, { headers: getAuthHeaders() });
                  if (!res.ok) throw new Error('Export impossible');
                  const blob = await res.blob();
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url; a.download = 'fiche-investisseur-360.pdf'; a.click();
                  URL.revokeObjectURL(url);
                } catch (e) { toast.error(e.message); }
              }}
              className="ml-auto px-2.5 py-1 rounded-md text-[10px] font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] transition-colors">
              Télécharger en PDF
            </button>
            <button type="button" data-testid="fiche360-committee-btn"
              onClick={async () => {
                try {
                  const cur = await fetch(`${API_URL}/api/investor-plans/admin/committee-emails`, { headers: getAuthHeaders() }).then((r) => r.json()).catch(() => ({ emails: [] }));
                  const input = window.prompt('Emails des membres du comité (séparés par des virgules) :', (cur.emails || []).join(', '));
                  if (!input) return;
                  const res = await fetch(`${API_URL}/api/investor-plans/admin/investor-360/${fiche.investor.user_id}/send-committee`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
                    body: JSON.stringify({ emails: input.split(',') }),
                  });
                  const d = await res.json();
                  if (!res.ok) throw new Error(d.detail || 'Erreur');
                  toast.success(`Fiche 360 envoyée à ${d.sent} membre(s) du comité`);
                } catch (e) { toast.error(e.message); }
              }}
              className="px-2.5 py-1 rounded-md text-[10px] font-bold text-black bg-[#8CC63E] hover:bg-[#7ab52f] transition-colors">
              Envoyer au comité
            </button>
            <button type="button" onClick={() => setFiche(null)} data-testid="fiche360-close"
              className="px-2 py-1 rounded-md text-[10px] font-semibold text-white/60 bg-white/[0.05] border border-white/15 hover:bg-white/[0.1] transition-colors">Fermer</button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 text-[11px] text-white/70">
            <div className="rounded-lg p-3 bg-white/[0.02] border border-white/[0.06]">
              <p className="font-bold text-white/90 m-0 mb-1">Abonnement</p>
              {fiche.subscription ? (<>
                <p className="m-0">Plan <b className="text-[#D9B35A]">{fiche.subscription.plan_code}</b> · statut <b>{fiche.subscription.status}</b></p>
                <p className="m-0 text-white/40">Période depuis {fmtD(fiche.subscription.period_start)}</p>
              </>) : <p className="m-0 text-white/40">Aucun abonnement</p>}
            </div>
            <div className="rounded-lg p-3 bg-white/[0.02] border border-white/[0.06]">
              <p className="font-bold text-white/90 m-0 mb-1">CREDI'SCOP-INVEST</p>
              <p className="m-0">Solde <b className="text-[#8CC63E]">{(fiche.credits.balance_uc ?? 0).toLocaleString('fr-FR')} uc</b> / quota {(fiche.credits.quota_uc ?? 0).toLocaleString('fr-FR')} uc</p>
              <p className="m-0 text-white/40">Consommé : {(fiche.credits.consumed_uc ?? 0).toLocaleString('fr-FR')} uc · {fiche.credits.entries} mouvement(s)</p>
            </div>
            <div className="rounded-lg p-3 bg-white/[0.02] border border-white/[0.06]">
              <p className="font-bold text-white/90 m-0 mb-1">RIB</p>
              {fiche.bank ? (<>
                <p className="m-0">{fiche.bank.holder} · IBAN …{(fiche.bank.iban || '').slice(-4)}</p>
                <p className="m-0">Statut : <b className={fiche.bank.rib_status === 'APPROVED' ? 'text-[#8CC63E]' : fiche.bank.rib_status === 'REJECTED' ? 'text-red-300' : 'text-amber-300'}>{fiche.bank.rib_status || (fiche.bank.rib_filename ? 'PENDING' : 'NON TÉLÉVERSÉ')}</b></p>
              </>) : <p className="m-0 text-amber-300">Coordonnées bancaires non renseignées</p>}
            </div>
            <div className="rounded-lg p-3 bg-white/[0.02] border border-white/[0.06]">
              <p className="font-bold text-white/90 m-0 mb-1">Financements ({fiche.financings.count})</p>
              <p className="m-0">Total : <b>{(fiche.financings.total_uc ?? 0).toLocaleString('fr-FR')} uc</b></p>
              {fiche.financings.items.slice(0, 3).map((f) => (
                <p key={f.id} className="m-0 text-white/40 truncate">{f.created_at.slice(0, 10)} · {f.label} · {(-f.amount_uc).toLocaleString('fr-FR')} uc</p>
              ))}
            </div>
            <div className="rounded-lg p-3 bg-white/[0.02] border border-white/[0.06]">
              <p className="font-bold text-white/90 m-0 mb-1">Virements de remboursement ({fiche.repayments.count})</p>
              <p className="m-0">Total confirmé : <b className="text-[#8CC63E]">{(fiche.repayments.total_eur ?? 0).toLocaleString('fr-FR')} €</b></p>
              {fiche.repayments.items.slice(0, 3).map((r) => (
                <p key={r.id} className="m-0 text-white/40 truncate">{(r.paid_at || '').slice(0, 10)} · réf. {r.reference} · {(r.amount_eur ?? 0).toLocaleString('fr-FR')} € {r.reconciled ? '✓' : ''}</p>
              ))}
            </div>
            <div className="rounded-lg p-3 bg-white/[0.02] border border-white/[0.06]">
              <p className="font-bold text-white/90 m-0 mb-1">Factures d'abonnement ({fiche.invoices.count})</p>
              <p className="m-0">Total encaissé : <b>{(fiche.invoices.total_eur ?? 0).toLocaleString('fr-FR')} €</b></p>
              {fiche.invoices.items.slice(0, 3).map((i) => (
                <p key={i.id} className="m-0 text-white/40 truncate">{i.period_label} · {i.number} · {(i.amount_eur ?? 0).toLocaleString('fr-FR')} €</p>
              ))}
            </div>
          </div>
        </div>
      )}
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


// Journal global des virements de remboursement + double validation + export CSV
const RepaymentsJournal = () => {
  const [reps, setReps] = useState([]);
  const [threshold, setThreshold] = useState('');
  const [budget, setBudget] = useState('');
  const load = () => {
    fetch(`${API_URL}/api/investor-plans/admin/repayments`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then((d) => setReps(d.repayments || [])).catch(() => {});
    fetch(`${API_URL}/api/investor-plans/admin/repayment-settings`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then((d) => { setThreshold(String(d.double_approval_threshold_eur)); if (d.monthly_budget_eur) setBudget(String(d.monthly_budget_eur)); }).catch(() => {});
  };
  useEffect(load, []);

  const saveSettings = async (payload, msg) => {
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/admin/repayment-settings`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Erreur');
      toast.success(msg);
    } catch (e) { toast.error(e.message); }
  };
  const saveThreshold = () => saveSettings({ double_approval_threshold_eur: Number(threshold) }, 'Seuil de double validation enregistré');
  const saveBudget = () => saveSettings({ monthly_budget_eur: Number(budget) }, 'Budget mensuel enregistré');

  const reconcile = async (r) => {
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/admin/repayments/${r.id}/reconcile`, {
        method: 'POST', headers: getAuthHeaders(),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(d.reconciled ? 'Virement rapproché avec le relevé bancaire' : 'Rapprochement annulé');
      load();
    } catch (e) { toast.error(e.message); }
  };

  const approve = async (r) => {
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/admin/repayments/${r.id}/approve`, {
        method: 'POST', headers: getAuthHeaders(),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success('Virement confirmé — investisseur notifié');
      load();
    } catch (e) { toast.error(e.message); }
  };

  const exportCsv = async () => {
    try {
      const res = await fetch(`${API_URL}/api/investor-plans/admin/repayments/export.csv`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Export impossible');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'journal-virements-remboursements.csv'; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="mt-5" data-testid="repayments-journal">
      <div className="flex items-center gap-2 flex-wrap mb-2">
        <h4 className="text-xs font-bold text-[#E9CF8E] flex items-center gap-1.5 m-0">
          <Euro className="w-3.5 h-3.5" /> Journal des virements de remboursement ({reps.length})
        </h4>
        <label className="ml-auto text-[10px] text-white/50 flex items-center gap-1">
          Double validation au-delà de
          <input type="number" value={threshold} onChange={(e) => setThreshold(e.target.value)}
            data-testid="repayment-threshold-input"
            className="h-7 w-24 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs" /> €
          <button type="button" onClick={saveThreshold} data-testid="repayment-threshold-save"
            className="px-2 py-1 rounded-md font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] transition-colors">OK</button>
        </label>
        <label className="text-[10px] text-white/50 flex items-center gap-1">
          Budget mensuel
          <input type="number" value={budget} onChange={(e) => setBudget(e.target.value)}
            data-testid="repayment-budget-input" placeholder="ex. 500000"
            className="h-7 w-24 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs" /> €
          <button type="button" onClick={saveBudget} data-testid="repayment-budget-save"
            className="px-2 py-1 rounded-md font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] transition-colors">OK</button>
        </label>
        <button type="button" onClick={exportCsv} data-testid="repayments-export-csv"
          className="px-2.5 py-1 rounded-md text-[10px] font-semibold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30 hover:bg-white/[0.1] transition-colors">
          Export CSV comptable
        </button>
      </div>
      {(() => {
        const month = new Date().toISOString().slice(0, 7);
        const monthTotal = reps.filter((r) => r.status !== 'PENDING_SECOND_APPROVAL' && (r.paid_at || '').startsWith(month))
          .reduce((s, r) => s + (r.amount_eur || 0), 0);
        const over = budget && monthTotal > Number(budget);
        return (
          <p className={`text-[11px] m-0 mb-2 ${over ? 'text-red-300 font-bold' : 'text-white/40'}`} data-testid="monthly-total-line">
            Total du mois : {monthTotal.toLocaleString('fr-FR')} €{budget ? ` / budget ${Number(budget).toLocaleString('fr-FR')} €` : ''}{over ? ' — PLAFOND DÉPASSÉ (superadmin alerté par email)' : ''}
          </p>
        );
      })()}
      {!reps.length ? (
        <p className="text-[11px] text-white/40 m-0">Aucun virement enregistré.</p>
      ) : (
        <div className="space-y-1.5 max-h-56 overflow-y-auto">
          {reps.map((r) => (
            <div key={r.id} className="flex items-center gap-2 flex-wrap text-[11px] text-white/70 rounded-lg px-3 py-2 bg-white/[0.02] border border-white/[0.06]" data-testid={`journal-row-${r.reference}`}>
              <span className="font-mono text-white/40">{(r.paid_at || '').slice(0, 10)}</span>
              <span className="text-white/60">{r.investor_email}</span>
              <span className="font-mono font-bold text-[#8CC63E]">{(r.amount_eur ?? 0).toLocaleString('fr-FR')} €</span>
              <span className="text-white/40">réf. {r.reference}{r.operation_ref ? ` — ${r.operation_ref}` : ''}</span>
              {r.status === 'PENDING_SECOND_APPROVAL' ? (
                <span className="ml-auto flex items-center gap-1.5">
                  <span className="px-2 py-0.5 rounded-full border text-[10px] font-semibold text-amber-300 bg-amber-500/10 border-amber-400/40">Attente 2e admin (créé par {r.created_by})</span>
                  <button type="button" onClick={() => approve(r)} data-testid={`repayment-approve-${r.reference}`}
                    className="px-2 py-1 rounded-md text-[10px] font-bold text-black bg-[#8CC63E] hover:bg-[#7ab52f] transition-colors">Confirmer</button>
                </span>
              ) : (
                <span className="ml-auto flex items-center gap-1.5">
                  <span className="px-2 py-0.5 rounded-full border text-[10px] font-semibold text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/30">Confirmé</span>
                  {r.reconciled ? (
                    <button type="button" onClick={() => reconcile(r)} data-testid={`repayment-reconciled-${r.reference}`}
                      title={`Rapproché par ${r.reconciled_by || ''} — cliquer pour annuler`}
                      className="px-2 py-0.5 rounded-full border text-[10px] font-semibold text-sky-300 bg-sky-500/10 border-sky-400/40 hover:bg-sky-500/20 transition-colors">✓ Rapproché</button>
                  ) : (
                    <button type="button" onClick={() => reconcile(r)} data-testid={`repayment-reconcile-${r.reference}`}
                      className="px-2 py-1 rounded-md text-[10px] font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] transition-colors">Rapprocher</button>
                  )}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
