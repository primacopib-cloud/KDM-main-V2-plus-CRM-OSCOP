import { useCallback, useEffect, useState } from 'react';
import { BookLock, Loader2, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const eur = (c) => ((c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €';
const KIND = {
  CONSTITUTION: ['Constitution', '#7BC94E'],
  EXTOURNE: ['Extourne', '#F87171'],
  REMBOURSEMENT: ['Remboursement', '#60A5FA'],
};

export const RcrFiscalPanel = () => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    fetch(`${API}/convention/admin/rcr-fiscal-register?limit=8`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const sync = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/convention/admin/rcr-fiscal-register/sync`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Synchronisation impossible');
      toast.success(`Registre fiscal synchronisé — ${d.added} écriture(s), ${d.reversed} extourne(s)`);
      load();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  if (!data) return null;

  return (
    <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
      data-testid="rcr-fiscal-panel">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <p className="flex items-center gap-2 text-sm font-semibold text-white/85">
          <BookLock className="w-4 h-4 text-[#7BC94E]" /> Registre fiscal RCR (continu, append-only)
        </p>
        <span className="inline-flex items-center gap-3">
          <span className="text-[11px] text-white/50">
            {data.count} écriture(s) · constitué <b className="text-[#A5E27E]">{eur(data.totals.CONSTITUTION)}</b>
            {data.totals.EXTOURNE !== 0 && <> · extourné <b className="text-red-300">{eur(data.totals.EXTOURNE)}</b></>}
            {' '}· remboursé <b className="text-[#93C5FD]">{eur(data.totals.REMBOURSEMENT)}</b>
            {' '}· solde <b className="text-[#E9CF8E]">{eur(data.solde_cents)}</b>
          </span>
          <button type="button" disabled={busy} onClick={sync} data-testid="rcr-fiscal-sync-btn"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-white/[0.06] text-white/75 hover:text-[#E9CF8E] border border-white/15 disabled:opacity-50">
            {busy ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />} Synchroniser
          </button>
        </span>
      </div>
      {data.entries.length === 0 ? (
        <p className="text-[11px] text-white/45">Aucune écriture — les constitutions, extournes et remboursements RCR y sont enregistrés automatiquement en continu.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
              <th className="py-1 pr-3">Date</th><th className="py-1 pr-3">Type</th>
              <th className="py-1 pr-3">Pièce</th><th className="py-1 pr-3">Libellé</th>
              <th className="py-1 pr-3">Comptes</th><th className="py-1">Montant</th></tr></thead>
            <tbody>
              {data.entries.map((e) => {
                const [label, color] = KIND[e.kind] || [e.kind, '#999'];
                return (
                  <tr key={e.id} className={`border-b border-white/[0.04] text-white/75 ${e.reversed_at ? 'opacity-50 line-through' : ''}`}
                    data-testid={`fiscal-entry-${e.id}`}>
                    <td className="py-1 pr-3">{e.date}</td>
                    <td className="py-1 pr-3 font-bold" style={{ color }}>{label}</td>
                    <td className="py-1 pr-3">{e.piece}</td>
                    <td className="py-1 pr-3 text-white/60">{(e.label || '').slice(0, 60)}</td>
                    <td className="py-1 pr-3 text-white/45">{e.debit_account} / {e.credit_account}</td>
                    <td className="py-1 font-bold" style={{ color }}>{eur(e.amount_cents)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
