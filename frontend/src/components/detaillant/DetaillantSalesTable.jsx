import { useEffect, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import { detaillantAPI } from '../../services/api.detaillant';

const ST = { LIVE: '#4ade80', SCHEDULED: '#fbbf24', WON: '#D9B35A', EXPIRED: '#94a3b8', CANCELLED: '#f87171' };
const ST_FR = { LIVE: 'En salle', SCHEDULED: 'Programmé', WON: 'Remporté', EXPIRED: 'Expiré', CANCELLED: 'Annulé' };

export const DetaillantSalesTable = () => {
  const [data, setData] = useState(null);
  useEffect(() => { detaillantAPI.sales().then(setData).catch(() => setData({ sales: [], totals: {} })); }, []);
  if (!data) return null;
  const { sales, totals } = data;
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="dt-sales-table">
      <h3 className="text-sm font-bold text-[#E9CF8E] mb-3 flex items-center gap-2">
        <TrendingUp className="w-4 h-4" /> Mes ventes en salle
      </h3>
      <div className="grid grid-cols-4 gap-2 mb-3 text-center">
        {[['Lots en salle', totals.lots], ['Mises', totals.bids], ['Remportés', totals.won],
          ['Montant gagné', `${(totals.revenue_eur || 0).toFixed(2)} €`]].map(([l, v]) => (
          <div key={l} className="rounded-xl bg-white/[0.04] border border-white/10 py-2">
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
