import { useEffect, useState } from 'react';
import { Download, RotateCcw, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';
import { detaillantAPI } from '../../services/api.detaillant';

const ST = { LIVE: '#4ade80', SCHEDULED: '#fbbf24', WON: '#D9B35A', EXPIRED: '#94a3b8', CANCELLED: '#f87171' };
const ST_FR = { LIVE: 'En salle', SCHEDULED: 'Programmé', WON: 'Remporté', EXPIRED: 'Expiré', CANCELLED: 'Annulé' };

export const DetaillantSalesTable = () => {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState('');
  const load = () => detaillantAPI.sales().then(setData).catch(() => setData({ sales: [], totals: {} }));
  useEffect(() => { load(); }, []);
  if (!data) return null;
  const { sales, totals } = data;
  const exportCsv = () => {
    const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const rows = [['Référence', 'Lot', 'Statut', 'Mises', 'Gagnant', 'Montant (€)', 'Retiré', 'Début', 'Fin']
      .map(esc).join(';')];
    sales.forEach((s) => rows.push([s.reference, s.title, ST_FR[s.status] || s.status, s.bids_count,
      s.winner_name || '', s.won_price_eur != null ? Number(s.won_price_eur).toFixed(2) : '',
      s.picked_up ? 'oui' : 'non', (s.starts_at || '').slice(0, 10), (s.ends_at || '').slice(0, 10)].map(esc).join(';')));
    const blob = new Blob(['\ufeff' + rows.join('\r\n')], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `ventes-coopact-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
  const relist = async (ref) => {
    setBusy(ref);
    try {
      const r = await detaillantAPI.relist(ref);
      toast.success(`✓ Lot relancé — nouvelle opération ${r.reference}`);
      load();
    } catch (e) { toast.error(e.message); } finally { setBusy(''); }
  };
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="dt-sales-table">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-[#E9CF8E] flex items-center gap-2">
          <TrendingUp className="w-4 h-4" /> Mes ventes en salle
        </h3>
        {sales.length > 0 && (
          <button onClick={exportCsv} data-testid="dt-sales-export-csv"
            className="inline-flex items-center gap-1.5 px-3 h-7 rounded-full text-[10px] font-bold text-[#E9CF8E] border border-[#D9B35A]/40 hover:bg-[#D9B35A]/15">
            <Download className="w-3 h-3" /> Exporter CSV
          </button>
        )}
      </div>
      <div className="grid grid-cols-4 gap-2 mb-3 text-center">
        {[['Lots en salle', totals.lots, 'lots'], ['Mises', totals.bids, 'bids'], ['Remportés', totals.won, 'won'],
          ['Montant gagné', `${(totals.revenue_eur || 0).toFixed(2)} €`, 'revenue']].map(([l, v, k]) => (
          <div key={l} className="rounded-xl bg-white/[0.04] border border-white/10 py-2" data-testid={`dt-sales-kpi-${k}`}>
            <p className="text-sm font-bold text-[#E9CF8E]">{v ?? 0}</p>
            <p className="text-[9px] text-white/50">{l}</p>
          </div>
        ))}
      </div>
      {sales.length === 0 && <p className="text-xs text-white/40">Aucun lot programmé en salle pour l'instant.</p>}
      {sales.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="text-white/40 text-left">
                <th className="py-1 pr-2 font-medium">Lot</th>
                <th className="py-1 pr-2 font-medium">Statut</th>
                <th className="py-1 pr-2 font-medium text-right">Mises</th>
                <th className="py-1 pr-2 font-medium">Gagnant</th>
                <th className="py-1 font-medium text-right">Montant</th>
              </tr>
            </thead>
            <tbody>
              {sales.map((s) => (
                <tr key={s.reference} className="border-t border-white/5" data-testid={`dt-sale-${s.reference}`}>
                  <td className="py-1.5 pr-2 max-w-[180px] truncate">{s.reference} — {s.title}</td>
                  <td className="py-1.5 pr-2">
                    <span className="font-bold" style={{ color: ST[s.status] || '#fff' }}>{ST_FR[s.status] || s.status}</span>
                    {s.picked_up && <span className="text-emerald-400 ml-1">✓ retiré</span>}
                    {s.status === 'EXPIRED' && !s.relisted && (
                      <button onClick={() => relist(s.reference)} disabled={busy === s.reference}
                        data-testid={`dt-relist-${s.reference}`}
                        className="inline-flex items-center gap-1 ml-2 px-2 h-5 rounded-full text-[9px] font-bold text-amber-300 border border-amber-400/40 hover:bg-amber-400/10 disabled:opacity-40">
                        <RotateCcw className="w-2.5 h-2.5" /> Relancer
                      </button>
                    )}
                    {s.relisted && <span className="text-[9px] text-white/40 ml-2">relancé</span>}
                  </td>
                  <td className="py-1.5 pr-2 text-right">{s.bids_count}</td>
                  <td className="py-1.5 pr-2 truncate max-w-[120px]">{s.winner_name || '—'}</td>
                  <td className="py-1.5 text-right font-bold text-[#E9CF8E]">
                    {s.won_price_eur != null ? `${Number(s.won_price_eur).toFixed(2)} €` : '—'}
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
