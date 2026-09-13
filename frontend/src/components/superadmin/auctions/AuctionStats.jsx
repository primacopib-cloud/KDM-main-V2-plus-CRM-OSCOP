import { useEffect, useState } from 'react';
import { Coins, Euro, Gavel, Users, TrendingUp, RefreshCw } from 'lucide-react';
import { API, getAuthHeaders } from '../../../services/http';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;

const Kpi = ({ icon: Icon, label, value, sub, testId }) => (
  <div className="rounded-[14px] bg-white/[0.03] border border-white/[0.08] p-3" data-testid={testId}>
    <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-white/45">
      <Icon className="w-3.5 h-3.5 text-[#D9B35A]" /> {label}
    </div>
    <div className="text-xl font-bold text-white mt-1">{value}</div>
    {sub && <div className="text-[10px] text-white/40 mt-0.5">{sub}</div>}
  </div>
);

// Tableau de bord des enchères : crédits collectés, mises par enchère, conversion des plans
export const AuctionStats = ({ refreshKey }) => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch(`${API}/admin/auctions/stats`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setStats).catch(() => {});
  }, [refreshKey]);

  if (!stats) return null;
  const totalPurchases = stats.plans.reduce((s, p) => s + p.active + p.pending, 0);
  const globalConversion = totalPurchases
    ? Math.round(1000 * stats.plans.reduce((s, p) => s + p.active, 0) / totalPurchases) / 10 : 0;

  return (
    <div className="mt-4" data-testid="auction-stats-panel">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Kpi icon={Coins} label="Crédits collectés" value={stats.credits_collected.toLocaleString('fr-FR')}
          sub="mises + prix acceptés" testId="stat-credits-collected" />
        <Kpi icon={Euro} label="Plans vendus" value={eur(stats.revenue_eur)}
          sub={`${stats.active_plan_accounts} compte(s) plan actif`} testId="stat-plans-revenue" />
        <Kpi icon={Gavel} label="Mises" value={stats.total_bids}
          sub={`${stats.total_auctions} enchère(s) · ${stats.live_auctions} en cours`} testId="stat-total-bids" />
        <Kpi icon={TrendingUp} label="Conversion plans" value={`${globalConversion} %`}
          sub={`${stats.won_auctions} enchère(s) remportée(s)`} testId="stat-plan-conversion" />
      </div>

      <div className="grid md:grid-cols-2 gap-3 mt-3">
        <div className="rounded-[14px] bg-white/[0.03] border border-white/[0.08] p-3" data-testid="stat-per-auction">
          <h4 className="text-[11px] font-bold text-white/50 uppercase mb-2 flex items-center gap-1">
            <Gavel className="w-3 h-3" /> Mises par enchère
          </h4>
          {stats.per_auction.length === 0 ? <p className="text-xs text-white/35">—</p> : stats.per_auction.map((a) => (
            <div key={a.id} className="flex items-center gap-2 text-[11px] py-1 border-b border-white/[0.05]"
              data-testid={`stat-row-${a.reference}`}>
              <span className="text-white/75 truncate flex-1">{a.title}</span>
              <span className="text-white/40">{a.bids} mise(s)</span>
              <span className="text-[#E9CF8E] font-bold shrink-0">{a.total_credits.toLocaleString('fr-FR')} cr</span>
            </div>
          ))}
        </div>
        <div className="rounded-[14px] bg-white/[0.03] border border-white/[0.08] p-3" data-testid="stat-per-plan">
          <h4 className="text-[11px] font-bold text-white/50 uppercase mb-2 flex items-center gap-1">
            <Users className="w-3 h-3" /> Conversion des plans
          </h4>
          {stats.plans.length === 0 ? <p className="text-xs text-white/35">Aucun achat de plan pour le moment</p>
            : stats.plans.map((p) => (
              <div key={p._id} className="flex items-center gap-2 text-[11px] py-1 border-b border-white/[0.05]"
                data-testid={`stat-plan-${p._id}`}>
                <span className="text-white/75 truncate flex-1">{p.label}</span>
                <span className="text-white/40">{p.active} payé(s) / {p.pending} abandonné(s)</span>
                <span className="text-[#E9CF8E] font-bold shrink-0">{p.conversion_pct} %</span>
              </div>
            ))}
          {stats.plans.length === 0 && (
            <p className="text-[10px] text-white/30 mt-1 flex items-center gap-1">
              <RefreshCw className="w-3 h-3" /> Le taux = paiements réussis / sessions Stripe créées
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
