import { useCallback, useEffect, useState } from 'react';
import { HandCoins, FileDown, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const eur = (c) => ((c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €';
const fdate = (d) => (d ? new Date(d).toLocaleDateString('fr-FR') : '—');

export const RcrReimbursements = () => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState('');

  const load = useCallback(() => {
    fetch(`${API}/attestations/admin/rcr-closures`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const reimburse = async (att) => {
    if (!window.confirm(`Rembourser ${eur(att.solde_cents)} de RCR à ${att.vendor_name} et clôturer l'attestation ${att.ref} ?`)) return;
    setBusy(att.id);
    try {
      const r = await fetch(`${API}/attestations/${att.id}/reimburse`, {
        method: 'POST', credentials: 'include',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' }, body: JSON.stringify({}),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Remboursement impossible');
      toast.success(`Remboursement ${d.reimbursement.ref} enregistré — attestation clôturée`);
      load();
    } catch (e) { toast.error(e.message); }
    setBusy('');
  };

  const receipt = async (r) => {
    try {
      const res = await fetch(`${API}/attestations/reimbursements/${r.id}/receipt.pdf`, { credentials: 'include', headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Téléchargement impossible');
      const blob = await res.blob();
      const u = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = u; a.download = `${r.ref}.pdf`; a.click();
      URL.revokeObjectURL(u);
    } catch (e) { toast.error(e.message); }
  };

  if (!data) return null;
  if (data.expired.length === 0 && data.reimbursements.length === 0) return null;

  return (
    <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
      data-testid="rcr-reimbursements-panel">
      <p className="flex items-center gap-2 text-sm font-semibold text-white/85 mb-3">
        <HandCoins className="w-4 h-4 text-[#D9B35A]" /> Remboursements RCR — clôture des attestations expirées
      </p>
      {data.expired.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] uppercase tracking-wide text-[#FBBF24] mb-1.5">Attestations expirées à clôturer ({data.expired.length})</p>
          <div className="space-y-1.5">
            {data.expired.map((a) => (
              <div key={a.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-lg bg-white/[0.04] text-xs"
                data-testid={`rcr-expired-${a.id}`}>
                <span className="text-white/85">
                  <b>{a.ref}</b> — {a.vendor_name} · {a.product_name}
                  <span className="text-white/45"> · expirée le {fdate(a.date_expiration)} · solde RCR <b className="text-[#E9CF8E]">{eur(a.solde_cents)}</b></span>
                </span>
                <button type="button" disabled={busy === a.id} onClick={() => reimburse(a)}
                  data-testid={`rcr-reimburse-btn-${a.id}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold disabled:opacity-50"
                  style={{ background: '#D9B35A', color: '#070A10' }}>
                  {busy === a.id ? <Loader2 size={11} className="animate-spin" /> : <HandCoins size={11} />} Rembourser & clôturer
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
      {data.reimbursements.length > 0 && (
        <div className="overflow-x-auto">
          <p className="text-[11px] uppercase tracking-wide text-white/40 mb-1.5">Historique des remboursements ({data.reimbursements.length})</p>
          <table className="w-full text-xs">
            <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
              <th className="py-1.5 pr-3">Référence</th><th className="py-1.5 pr-3">Date</th>
              <th className="py-1.5 pr-3">Attestation</th><th className="py-1.5 pr-3">Fournisseur</th>
              <th className="py-1.5 pr-3">Montant</th><th className="py-1.5">Reçu</th></tr></thead>
            <tbody>
              {data.reimbursements.map((r) => (
                <tr key={r.id} className="border-b border-white/[0.04] text-white/75" data-testid={`rcr-rbt-row-${r.id}`}>
                  <td className="py-1.5 pr-3 font-semibold text-white/90">{r.ref}</td>
                  <td className="py-1.5 pr-3">{fdate(r.created_at)}</td>
                  <td className="py-1.5 pr-3">{r.attestation_ref}</td>
                  <td className="py-1.5 pr-3">{r.vendor_name}</td>
                  <td className="py-1.5 pr-3 font-bold text-[#E9CF8E]">{eur(r.amount_cents)}</td>
                  <td className="py-1.5">
                    <button type="button" onClick={() => receipt(r)} data-testid={`rcr-receipt-btn-${r.id}`}
                      className="text-white/50 hover:text-[#E9CF8E]"><FileDown size={13} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
