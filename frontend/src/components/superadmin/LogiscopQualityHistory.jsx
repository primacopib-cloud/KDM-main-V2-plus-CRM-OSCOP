import { useEffect, useState } from 'react';
import { TrendingUp, Star } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const pct = (v) => (v === null || v === undefined ? '—' : `${v} %`);

export const LogiscopQualityHistory = () => {
  const [months, setMonths] = useState(null);

  useEffect(() => {
    fetch(`${API}/logiscop-transport/admin/quality-history`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : { months: [] }))
      .then((d) => setMonths(d.months || [])).catch(() => setMonths([]));
  }, []);

  if (!months || !months.length) return null;

  return (
    <div className="mb-4 rounded-lg p-3 bg-white/[0.04] border border-white/[0.08]" data-testid="quality-history">
      <p className="flex items-center gap-2 text-[11px] font-bold text-white/60 mb-2">
        <TrendingUp size={12} className="text-[#93C5FD]" /> Historique qualité mensuel (ponctualité · réserves · notes par opérateur)
      </p>
      <table className="w-full text-[11px]">
        <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
          <th className="py-1 pr-3">Mois</th><th className="py-1 pr-3">Opérateur</th>
          <th className="py-1 pr-3">Livrés</th><th className="py-1 pr-3">Ponctualité</th>
          <th className="py-1 pr-3">Réserves</th><th className="py-1">Note</th></tr></thead>
        <tbody>
          {months.map((m) => (
            <>
              <tr key={m.month} className="border-b border-white/[0.06] text-white/85 bg-white/[0.03]"
                data-testid={`quality-month-${m.month}`}>
                <td className="py-1 pr-3 font-bold">{m.month}</td>
                <td className="py-1 pr-3 text-white/50 italic">Tous opérateurs</td>
                <td className="py-1 pr-3 font-bold">{m.delivered}</td>
                <td className="py-1 pr-3 font-bold text-[#93C5FD]">{pct(m.on_time_rate)}</td>
                <td className="py-1 pr-3">{pct(m.reserves_rate)}</td>
                <td className="py-1">
                  {m.avg_rating === null ? '—' : (
                    <span className="inline-flex items-center gap-1 text-[#E9CF8E] font-bold">
                      <Star size={10} fill="currentColor" /> {m.avg_rating}
                    </span>
                  )}
                </td>
              </tr>
              {m.operators.map((o) => (
                <tr key={`${m.month}-${o.operator_name}`} className="border-b border-white/[0.03] text-white/60">
                  <td className="py-1 pr-3" />
                  <td className="py-1 pr-3">{o.operator_name}</td>
                  <td className="py-1 pr-3">{o.delivered}</td>
                  <td className="py-1 pr-3">{pct(o.on_time_rate)}</td>
                  <td className="py-1 pr-3">{pct(o.reserves_rate)}</td>
                  <td className="py-1">{o.avg_rating === null ? '—' : `★ ${o.avg_rating}`}</td>
                </tr>
              ))}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
};
