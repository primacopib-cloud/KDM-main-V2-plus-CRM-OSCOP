import { useEffect, useState } from 'react';
import { TrendingUp, Coins, CreditCard, Download } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../../services/http';

export const ZoneSalesTable = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/zone-addon/admin/sales`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);

  const exportCsv = async () => {
    try {
      const r = await fetch(`${API}/zone-addon/admin/sales/export`, { credentials: 'include', headers: getAuthHeaders() });
      if (!r.ok) throw new Error();
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'ventes-zones-additionnelles.csv'; a.click();
      URL.revokeObjectURL(url);
      toast.success('Ventes de zones exportées en CSV');
    } catch { toast.error('Export impossible'); }
  };

  if (!data || !data.sales?.length) return null;
  const { sales, totals } = data;

  return (
    <div className="mb-4 rounded-xl p-4"
      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
      data-testid="zone-sales-table">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <p className="flex items-center gap-2 text-white/80 text-sm font-semibold">
          <TrendingUp className="w-4 h-4 text-[#7BC94E]" /> Ventes de zones additionnelles
        </p>
        <div className="flex gap-2 text-[10px] font-bold">
          <span className="px-2 py-1 rounded-full text-white/70 bg-white/[0.06]">{totals.count} vente(s)</span>
          <span className="px-2 py-1 rounded-full text-[#E9CF8E] bg-[#D4AF37]/12 inline-flex items-center gap-1">
            <Coins size={10} /> {totals.credits_total} crédits
          </span>
          <span className="px-2 py-1 rounded-full text-[#93C5FD] bg-[#60A5FA]/12 inline-flex items-center gap-1">
            <CreditCard size={10} /> {(totals.eur_total_cents / 100).toFixed(2)} €
          </span>
          <button type="button" onClick={exportCsv} data-testid="zone-sales-export-btn"
            className="px-2 py-1 rounded-full border border-[#D9B35A]/40 text-[#E9CF8E] bg-[#D9B35A]/10 hover:bg-[#D9B35A]/20 inline-flex items-center gap-1 transition-colors">
            <Download size={10} /> Export CSV
          </button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-white/40 border-b border-white/[0.08]">
              <th className="py-1.5 pr-3">Date</th>
              <th className="py-1.5 pr-3">Membre</th>
              <th className="py-1.5 pr-3">Zone</th>
              <th className="py-1.5 pr-3">Moyen</th>
              <th className="py-1.5 text-right">Montant</th>
            </tr>
          </thead>
          <tbody>
            {sales.map((s) => (
              <tr key={s.id} className="border-b border-white/[0.04] text-white/75" data-testid={`zone-sale-${s.id}`}>
                <td className="py-1.5 pr-3 whitespace-nowrap">{new Date(s.created_at).toLocaleDateString('fr-FR')}</td>
                <td className="py-1.5 pr-3">{s.company_name || s.user_email || s.user_id}</td>
                <td className="py-1.5 pr-3 font-semibold text-white/90">{s.zone_name || s.zone_code}</td>
                <td className="py-1.5 pr-3">
                  {s.method === 'card'
                    ? <span className="text-[#93C5FD]">Carte</span>
                    : <span className="text-[#E9CF8E]">Crédits</span>}
                </td>
                <td className="py-1.5 text-right font-bold">
                  {s.method === 'card' ? `${(s.amount_cents / 100).toFixed(2)} €` : `${s.credits_spent} cr.`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
