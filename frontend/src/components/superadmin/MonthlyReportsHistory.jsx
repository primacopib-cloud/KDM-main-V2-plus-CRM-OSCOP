import { useEffect, useState } from 'react';
import { CalendarRange, FileDown } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const eur = (c) => `${((c || 0) / 100).toFixed(2)} €`;

export const MonthlyReportsHistory = () => {
  const [rows, setRows] = useState(null);

  useEffect(() => {
    fetch(`${API}/logiscop-transport/admin/monthly-reports`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setRows).catch(() => {});
  }, []);

  const download = async (month) => {
    try {
      const r = await fetch(`${API}/logiscop-transport/admin/monthly-report/pdf?month=${month}`,
        { credentials: 'include', headers: getAuthHeaders() });
      if (!r.ok) throw new Error('PDF indisponible');
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement('a');
      a.href = url; a.download = `synthese-transport-${month}.pdf`; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(e.message); }
  };

  if (!rows || !rows.length) return null;
  return (
    <div className="rounded-lg p-3 mt-3 bg-white/[0.04] border border-white/[0.08]" data-testid="monthly-reports-history">
      <p className="text-[11px] font-bold text-white/60 mb-1.5 flex items-center gap-1.5">
        <CalendarRange size={12} className="text-[#E9CF8E]" /> Historique des synthèses mensuelles transport
      </p>
      <table className="w-full text-[11px]">
        <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
          <th className="py-1 pr-3">Mois</th><th className="py-1 pr-3">OT créés / livrés</th>
          <th className="py-1 pr-3">CA facturé TTC</th><th className="py-1 pr-3">Encaissé</th>
          <th className="py-1 pr-3">Avoirs</th><th className="py-1 pr-3">Litiges</th>
          <th className="py-1 pr-3">Envoi / GED</th><th className="py-1">PDF</th></tr></thead>
        <tbody>
          {rows.map((m) => (
            <tr key={m.month} className="border-b border-white/[0.04] text-white/75" data-testid={`monthly-report-row-${m.month}`}>
              <td className="py-1.5 pr-3 font-semibold">{m.month}</td>
              <td className="py-1.5 pr-3">{m.ot_created} / {m.ot_delivered}</td>
              <td className="py-1.5 pr-3 text-[#E9CF8E] font-bold">{eur(m.invoiced_ttc_cents)}</td>
              <td className="py-1.5 pr-3 text-emerald-300">{eur(m.paid_ttc_cents)}</td>
              <td className="py-1.5 pr-3 text-[#F0ABFC]">{m.credits_count ? `${m.credits_count} (−${eur(m.credits_ttc_cents)})` : '—'}</td>
              <td className="py-1.5 pr-3">{m.disputes_opened ? `${m.disputes_opened} ouvert(s), ${m.disputes_resolved} résolu(s)` : '—'}</td>
              <td className="py-1.5 pr-3 text-[10px]">
                {m.sent_at ? <span className="text-emerald-300">Envoyée {m.sent_at.slice(0, 10)}</span> : <span className="text-white/35">Non envoyée</span>}
                {m.ged_doc_id && <span className="block text-white/40">GED ✓</span>}
              </td>
              <td className="py-1.5">
                <button type="button" data-testid={`monthly-report-pdf-${m.month}`} onClick={() => download(m.month)}
                  className="text-white/50 hover:text-[#E9CF8E]"><FileDown size={14} /></button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
