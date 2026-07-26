import { useEffect, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const fmt = (c) => `${(c / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

export const PassRechargeStats = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch(`${API}/admin/pass-recharges/stats`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setStats).catch(() => {});
  }, []);

  if (!stats) return null;
  return (
    <div className="mt-4 pt-4 border-t border-white/[0.08]" data-testid="pass-recharge-stats">
      <h4 className="text-xs font-semibold text-[#D9B35A] flex items-center gap-1.5 mb-2">
        <TrendingUp className="w-3.5 h-3.5" /> Recharges encaissées (Stripe payées)
      </h4>
      {stats.packs.length === 0 ? (
        <p className="text-[11px] text-white/40">Aucune recharge payée pour le moment.</p>
      ) : (
        <>
          <div className="grid grid-cols-[1fr_auto_auto_auto] gap-x-4 gap-y-1 text-[11px]">
            <span className="text-white/40 uppercase text-[9px]">Pack</span>
            <span className="text-white/40 uppercase text-[9px] text-right">Nb</span>
            <span className="text-white/40 uppercase text-[9px] text-right">Encaissé</span>
            <span className="text-white/40 uppercase text-[9px] text-right">UC distribués</span>
            {stats.packs.map((p) => (
              <div key={p.pack} className="contents" data-testid={`recharge-stat-${p.pack}`}>
                <span className="text-white/80 font-medium">{p.label}</span>
                <span className="text-white/70 text-right">{p.count}</span>
                <span className="text-[#E9CF8E] font-semibold text-right">{fmt(p.amount_cents)}</span>
                <span className="text-emerald-400 text-right">+{p.uc_total} UC</span>
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-2 pt-2 border-t border-white/[0.06] text-[11.5px] font-bold" data-testid="recharge-stats-total">
            <span className="text-white/70">Total : {stats.total_count} recharge(s)</span>
            <span className="text-[#E9CF8E]">{fmt(stats.total_amount_cents)} · <span className="text-emerald-400">{stats.total_uc} UC</span></span>
          </div>
        </>
      )}
    </div>
  );
};
