import { useCallback, useEffect, useState } from 'react';
import { Ticket, Gift, Wrench, Unlock } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { CpcPlansAdminPanel } from './CpcPlansAdminPanel';
import { ReferralAdminPanel } from './ReferralAdminPanel';

const opts = () => ({ headers: getAuthHeaders(), credentials: 'include' });
const jsonOpts = (method, body) => ({ method, headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, credentials: 'include', body: JSON.stringify(body) });
const inp = 'h-9 rounded-lg px-2.5 text-xs text-white bg-white/[0.05] border border-white/15';

export const CpcAdminTab = () => {
  const [packs, setPacks] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [grant, setGrant] = useState({ user_email: '', credits: 10, kind: 'promo', reason: '' });
  const [corr, setCorr] = useState({ user_email: '', qty: 0, reason: '', reference: '' });
  const [edit, setEdit] = useState({});

  const load = useCallback(() => {
    fetch(`${API}/admin/cpc/packs`, opts()).then((r) => r.json()).then((d) => setPacks(d.items || [])).catch(() => {});
    fetch(`${API}/admin/cpc/accounts`, opts()).then((r) => r.json()).then((d) => setAccounts(d.items || [])).catch(() => {});
    fetch(`${API}/admin/cpc/ledger`, opts()).then((r) => r.json()).then((d) => setLedger(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const savePack = async (p) => {
    const e = edit[p.id] || {};
    const body = {
      label: e.label ?? p.label, credits: parseInt(e.credits ?? p.credits, 10),
      price_ht_cents: Math.round(parseFloat(e.price ?? p.price_ht_cents / 100) * 100),
      validity_months: parseInt(e.validity ?? p.validity_months, 10), active: e.active ?? p.active,
    };
    const r = await fetch(`${API}/admin/cpc/packs/${p.id}`, jsonOpts('PUT', body));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success('Pack mis à jour (sans effet rétroactif)');
    setEdit((s) => ({ ...s, [p.id]: undefined }));
    load();
  };

  const doGrant = async () => {
    const r = await fetch(`${API}/admin/cpc/grant`, jsonOpts('POST', { ...grant, credits: parseInt(grant.credits, 10) }));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`CREDI'SCOP attribués — nouveau solde : ${d.balance}`);
    setGrant({ user_email: '', credits: 10, kind: 'promo', reason: '' });
    load();
  };

  const doCorr = async () => {
    const r = await fetch(`${API}/admin/cpc/correction`, jsonOpts('POST', { ...corr, qty: parseInt(corr.qty, 10) }));
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Correction enregistrée — nouveau solde : ${d.balance}`);
    setCorr({ user_email: '', qty: 0, reason: '', reference: '' });
    load();
  };

  const unfreeze = async (email) => {
    const r = await fetch(`${API}/admin/cpc/unfreeze/${encodeURIComponent(email)}`, { method: 'POST', ...opts() });
    if (!r.ok) return toast.error('Erreur');
    toast.success('Compte réactivé');
    load();
  };

  return (
    <div className="space-y-6" data-testid="cpc-admin-tab">
      <h2 className="text-base font-semibold text-white flex items-center gap-2">
        <Ticket className="w-4 h-4 text-[#D9B35A]" /> CREDI'SCOP — Crédits de Participation aux Consultations
      </h2>

      <div className="glass-panel-soft rounded-[14px] p-4">
        <h3 className="text-xs font-bold text-white/70 uppercase mb-3">Packs (tarifs HT — modifiables sans effet rétroactif)</h3>
        <div className="space-y-2">
          {packs.map((p) => {
            const e = edit[p.id] || {};
            return (
              <div key={p.id} className="flex flex-wrap items-center gap-2" data-testid={`cpc-admin-pack-${p.id}`}>
                <input className={`${inp} w-40`} value={e.label ?? p.label} onChange={(ev) => setEdit((s) => ({ ...s, [p.id]: { ...e, label: ev.target.value } }))} />
                <input className={`${inp} w-20`} type="number" value={e.credits ?? p.credits} onChange={(ev) => setEdit((s) => ({ ...s, [p.id]: { ...e, credits: ev.target.value } }))} />
                <span className="text-[10px] text-white/40">CREDI'SCOP</span>
                <input className={`${inp} w-24`} type="number" step="0.01" value={e.price ?? (p.price_ht_cents / 100)} onChange={(ev) => setEdit((s) => ({ ...s, [p.id]: { ...e, price: ev.target.value } }))} data-testid={`cpc-pack-price-${p.id}`} />
                <span className="text-[10px] text-white/40">€ HT</span>
                <input className={`${inp} w-16`} type="number" value={e.validity ?? p.validity_months} onChange={(ev) => setEdit((s) => ({ ...s, [p.id]: { ...e, validity: ev.target.value } }))} />
                <span className="text-[10px] text-white/40">mois</span>
                <button type="button" onClick={() => setEdit((s) => ({ ...s, [p.id]: { ...e, active: !(e.active ?? p.active) } }))}
                  className={`px-2 py-1 rounded text-[10px] font-bold ${(e.active ?? p.active) ? 'bg-[#7BC94E]/15 text-[#7BC94E]' : 'bg-red-500/15 text-red-400'}`}>
                  {(e.active ?? p.active) ? 'ACTIF' : 'INACTIF'}
                </button>
                <button type="button" onClick={() => savePack(p)} data-testid={`cpc-pack-save-${p.id}`}
                  className="px-3 py-1.5 rounded-lg text-[10.5px] font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }}>
                  Enregistrer
                </button>
              </div>
            );
          })}
        </div>
      </div>

      <CpcPlansAdminPanel />

      <ReferralAdminPanel />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-panel-soft rounded-[14px] p-4 space-y-2">
          <h3 className="text-xs font-bold text-white/70 uppercase flex items-center gap-1.5"><Gift className="w-3.5 h-3.5" /> Attribution promo / solidaire</h3>
          <input className={`${inp} w-full`} placeholder="Email du vendeur" value={grant.user_email} onChange={(e) => setGrant({ ...grant, user_email: e.target.value })} data-testid="cpc-grant-email" />
          <div className="flex gap-2">
            <input className={`${inp} w-24`} type="number" value={grant.credits} onChange={(e) => setGrant({ ...grant, credits: e.target.value })} data-testid="cpc-grant-credits" />
            <select className={`${inp} flex-1`} value={grant.kind} onChange={(e) => setGrant({ ...grant, kind: e.target.value })}>
              <option value="promo">Promotionnel</option>
              <option value="solidaire">Solidaire (petite structure locale)</option>
            </select>
          </div>
          <input className={`${inp} w-full`} placeholder="Motif (obligatoire, tracé au registre)" value={grant.reason} onChange={(e) => setGrant({ ...grant, reason: e.target.value })} data-testid="cpc-grant-reason" />
          <button type="button" onClick={doGrant} className="w-full py-2 rounded-lg text-xs font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }} data-testid="cpc-grant-btn">Attribuer</button>
        </div>

        <div className="glass-panel-soft rounded-[14px] p-4 space-y-2">
          <h3 className="text-xs font-bold text-white/70 uppercase flex items-center gap-1.5"><Wrench className="w-3.5 h-3.5" /> Correction administrative</h3>
          <input className={`${inp} w-full`} placeholder="Email du vendeur" value={corr.user_email} onChange={(e) => setCorr({ ...corr, user_email: e.target.value })} data-testid="cpc-corr-email" />
          <div className="flex gap-2">
            <input className={`${inp} w-24`} type="number" placeholder="± qté" value={corr.qty} onChange={(e) => setCorr({ ...corr, qty: e.target.value })} data-testid="cpc-corr-qty" />
            <input className={`${inp} flex-1`} placeholder="Référence de l'opération" value={corr.reference} onChange={(e) => setCorr({ ...corr, reference: e.target.value })} data-testid="cpc-corr-ref" />
          </div>
          <input className={`${inp} w-full`} placeholder="Motif (obligatoire)" value={corr.reason} onChange={(e) => setCorr({ ...corr, reason: e.target.value })} data-testid="cpc-corr-reason" />
          <button type="button" onClick={doCorr} className="w-full py-2 rounded-lg text-xs font-bold bg-white/10 text-white" data-testid="cpc-corr-btn">Corriger</button>
        </div>
      </div>

      <div className="glass-panel-soft rounded-[14px] p-4">
        <h3 className="text-xs font-bold text-white/70 uppercase mb-2">Comptes CREDI'SCOP</h3>
        {!accounts.length && <p className="text-xs text-white/40">Aucun compte CREDI'SCOP.</p>}
        {accounts.map((a) => (
          <div key={a.user_id} className="flex items-center gap-3 text-xs py-1.5 border-b border-white/5 last:border-0">
            <span className="flex-1 text-white/80">{a.email || a.user_id}</span>
            <span className="font-bold text-[#E9CF8E]">{a.cpc_balance} CREDI'SCOP</span>
            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${a.status === 'GELE' ? 'bg-red-500/15 text-red-400' : 'bg-[#7BC94E]/15 text-[#7BC94E]'}`}>{a.status}</span>
            {a.status === 'GELE' && (
              <button type="button" onClick={() => unfreeze(a.email)} className="p-1 rounded bg-white/10 text-white/60 hover:text-white" title="Réactiver">
                <Unlock className="w-3 h-3" />
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="glass-panel-soft rounded-[14px] p-4">
        <h3 className="text-xs font-bold text-white/70 uppercase mb-2">Registre (append-only — 100 derniers mouvements)</h3>
        {ledger.map((m) => (
          <div key={m.id} className="flex items-center gap-2 text-[11px] py-1 border-b border-white/5 last:border-0">
            <span className={`font-bold w-12 text-right ${m.qty > 0 ? 'text-[#7BC94E]' : 'text-red-400'}`}>{m.qty > 0 ? '+' : ''}{m.qty}</span>
            <span className="text-white/50 w-36">{m.type}</span>
            <span className="flex-1 text-white/70 truncate">{m.reason}</span>
            <span className="text-white/35">solde {m.balance_after}</span>
            <span className="text-white/35">{String(m.created_at).slice(0, 16).replace('T', ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
