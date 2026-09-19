import { useEffect, useState } from 'react';
import { Crown, FileDown, Search, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const fmtEur = (n) => `${Number(n).toLocaleString('fr-FR')} €`;
const fmt = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—');
const STATUSES = [['', 'Tous'], ['ACTIVE', 'Actifs'], ['PENDING_TRANSFER', 'Virements en attente'], ['PENDING', 'Paiements en attente']];

// Registre superadmin des abonnements Privilège Investisseur (packs FCRL)
export const PrivilegePacksRegistry = () => {
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);

  const load = () => {
    const qs = new URLSearchParams();
    if (q) qs.set('q', q);
    if (status) qs.set('status', status);
    fetch(`${API}/investor/privilege/admin/registry?${qs}`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { subscriptions: [] }))
      .then((d) => { setItems(d.subscriptions || []); setStats(d.stats || null); }).catch(() => {});
  };
  useEffect(() => { load(); }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  const activate = async (id) => {
    const r = await fetch(`${API}/investor/privilege/admin/${id}/activate`, {
      method: 'POST', headers: getAuthHeaders(), credentials: 'include' });
    if (r.ok) { toast.success('Pack activé — crédits bonifiés attribués'); load(); }
    else toast.error('Activation impossible');
  };

  const pdf = async (id, ref) => {
    const r = await fetch(`${API}/investor/privilege/admin/${id}/convention/pdf`, { headers: getAuthHeaders(), credentials: 'include' });
    if (!r.ok) { toast.error('PDF indisponible'); return; }
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `convention-fcrl-${ref}.pdf`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 mt-6" data-testid="privilege-registry">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h3 className="text-sm font-bold flex items-center gap-2">
          <Crown className="w-4 h-4 text-[#D9B35A]" /> Registre — Abonnements Privilège Investisseur (FCRL)
        </h3>
        {stats && (
          <div className="flex gap-4 text-[11px]" data-testid="privilege-registry-stats">
            <span className="text-emerald-300 font-bold">{stats.active} actif(s)</span>
            <span className="text-amber-300 font-bold">{stats.pending_transfer} virement(s) en attente</span>
            <span className="text-[#F2D07A] font-bold">Collecté : {fmtEur(stats.collected_eur)}</span>
            <span className="text-white/60">Crédits émis : {fmtEur(stats.credits_issued_eur)}</span>
          </div>
        )}
      </div>
      <div className="flex gap-2 mt-3 flex-wrap">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-white/35" />
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && load()}
            placeholder="Référence, société, signataire…" data-testid="privilege-registry-search"
            className="h-8 pl-8 pr-3 rounded-lg bg-white/[0.06] border border-white/15 text-xs placeholder:text-white/35 outline-none focus:border-[#D9B35A]/60" />
        </div>
        {STATUSES.map(([v, label]) => (
          <button key={v} onClick={() => setStatus(v)} data-testid={`privilege-registry-filter-${v || 'all'}`}
            className={`px-3 h-8 rounded-full text-[11px] font-bold border transition-colors ${
              status === v ? 'bg-[#D9B35A] text-black border-[#D9B35A]' : 'border-white/20 text-white/60 hover:bg-white/5'}`}>
            {label}
          </button>
        ))}
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-white/40 mt-4" data-testid="privilege-registry-empty">Aucune souscription.</p>
      ) : (
        <div className="mt-3 space-y-2">
          {items.map((s) => (
            <div key={s.id} className="rounded-xl border border-white/10 bg-white/[0.02] p-3 flex items-center gap-3 flex-wrap"
              data-testid={`privilege-registry-row-${s.reference}`}>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold">
                  {s.convention?.company_name} <span className="text-white/40 font-mono">· {s.reference}</span>
                </p>
                <p className="text-[10.5px] text-white/50">
                  {s.pack_name} ({s.tier}) · {fmtEur(s.amount_eur)} → {fmtEur(s.credits_eur)} (+{s.bonus_pct} %) ·
                  {s.payment_method === 'STRIPE' ? ' Carte' : ' Virement'} · signée {fmt(s.convention?.signed_at)} par {s.convention?.signer_name} · {s.email}
                </p>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                s.status === 'ACTIVE' ? 'text-emerald-300 border-emerald-400/40'
                  : s.status === 'PENDING_TRANSFER' ? 'text-amber-300 border-amber-400/40' : 'text-white/45 border-white/20'}`}>
                {s.status === 'ACTIVE' ? 'Actif' : s.status === 'PENDING_TRANSFER' ? 'Virement attendu' : 'Paiement attendu'}
              </span>
              {s.status === 'PENDING_TRANSFER' && (
                <button onClick={() => activate(s.id)} data-testid={`privilege-registry-activate-${s.reference}`}
                  className="inline-flex items-center gap-1 px-3 h-7 rounded-full bg-emerald-500 text-white text-[10px] font-bold hover:brightness-110 transition-all">
                  <CheckCircle2 className="w-3 h-3" /> Fonds reçus — activer
                </button>
              )}
              <button onClick={() => pdf(s.id, s.reference)} data-testid={`privilege-registry-pdf-${s.reference}`}
                className="inline-flex items-center gap-1 px-3 h-7 rounded-full border border-white/25 text-[10px] font-bold hover:bg-white/10 transition-colors">
                <FileDown className="w-3 h-3" /> PDF
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
