import { useCallback, useEffect, useState } from 'react';
import { CalendarRange, FileDown, Loader2, Send } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const eur = (c) => ((c || 0) / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €';

export const RcrStatements = () => {
  const [statements, setStatements] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    fetch(`${API}/convention/admin/rcr-statements`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setStatements(d.statements)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const run = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/convention/admin/rcr-statements/run`, {
        method: 'POST', credentials: 'include',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' }, body: JSON.stringify({}),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Génération impossible');
      toast.success(`Relevés du mois précédent : ${d.sent} email(s) envoyé(s)`);
      load();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  const download = async (s) => {
    try {
      const r = await fetch(`${API}/convention/admin/rcr-statements/${s.id}/pdf`, { credentials: 'include', headers: getAuthHeaders() });
      if (!r.ok) throw new Error('Téléchargement impossible');
      const blob = await r.blob();
      const u = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = u; a.download = `releve-rcr-${s.month}.pdf`; a.click();
      URL.revokeObjectURL(u);
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
      data-testid="rcr-statements-panel">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <p className="flex items-center gap-2 text-sm font-semibold text-white/85">
          <CalendarRange className="w-4 h-4 text-[#93C5FD]" /> Relevés RCR mensuels (envoi automatique aux fournisseurs)
        </p>
        <button type="button" disabled={busy} onClick={run} data-testid="rcr-statements-run-btn"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-white/[0.06] text-white/75 hover:text-[#E9CF8E] border border-white/15 disabled:opacity-50">
          {busy ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />} Générer & envoyer (mois précédent)
        </button>
      </div>
      {!statements || statements.length === 0 ? (
        <p className="text-[11px] text-white/45">Aucun relevé émis pour l'instant — le relevé du mois écoulé est envoyé automatiquement chaque début de mois.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
              <th className="py-1.5 pr-3">Mois</th><th className="py-1.5 pr-3">Fournisseur</th>
              <th className="py-1.5 pr-3">Constitué</th><th className="py-1.5 pr-3">Remboursé</th>
              <th className="py-1.5 pr-3">Email</th><th className="py-1.5">PDF</th></tr></thead>
            <tbody>
              {statements.map((s) => (
                <tr key={s.id} className="border-b border-white/[0.04] text-white/75" data-testid={`rcr-statement-row-${s.id}`}>
                  <td className="py-1.5 pr-3 font-semibold text-white/90">{s.month}</td>
                  <td className="py-1.5 pr-3">{s.vendor_name}</td>
                  <td className="py-1.5 pr-3 text-[#E9CF8E]">{eur(s.total_constitue_cents)}</td>
                  <td className="py-1.5 pr-3 text-[#93C5FD]">{eur(s.total_rembourse_cents)}</td>
                  <td className="py-1.5 pr-3">{s.email_sent ? <span className="text-[#7BC94E]">Envoyé</span> : <span className="text-white/40">—</span>}</td>
                  <td className="py-1.5">
                    <button type="button" onClick={() => download(s)} data-testid={`rcr-statement-pdf-${s.id}`}
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
