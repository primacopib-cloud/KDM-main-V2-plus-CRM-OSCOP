import { useEffect, useState } from 'react';
import { Coins, Euro, Gavel, Users, TrendingUp, RefreshCw, FileDown } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../../services/http';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;

const STATUS_FR = { SCHEDULED: 'Programmée', LIVE: 'En cours', WON: 'Remportée', EXPIRED: 'Expirée', CANCELLED: 'Annulée' };

const exportCsv = (stats) => {
  const esc = (v) => `"${String(v ?? '').replaceAll('"', '""')}"`;
  const rows = [
    ['Référence', "COOP'ACT", 'Statut', 'Mises', 'Crédits des mises', 'Crédits du gagnant', 'Total crédits'],
    ...stats.per_auction.map((a) => [
      a.reference, a.title, STATUS_FR[a.status] || a.status, a.bids, a.bid_credits, a.winner_credits, a.total_credits,
    ]),
  ];
  const csv = '﻿' + rows.map((r) => r.map(esc).join(';')).join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `coopact_mises_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
  toast.success('Export CSV téléchargé');
};

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
          sub={`${stats.total_auctions} COOP'ACT · ${stats.live_auctions} en cours`} testId="stat-total-bids" />
        <Kpi icon={TrendingUp} label="Conversion plans" value={`${globalConversion} %`}
          sub={`${stats.won_auctions} COOP'ACT remporté(s)`} testId="stat-plan-conversion" />
      </div>

      <div className="grid md:grid-cols-2 gap-3 mt-3">
        <div className="rounded-[14px] bg-white/[0.03] border border-white/[0.08] p-3" data-testid="stat-per-auction">
          <h4 className="text-[11px] font-bold text-white/50 uppercase mb-2 flex items-center gap-1">
            <Gavel className="w-3 h-3" /> Mises par COOP'ACT
            {stats.per_auction.length > 0 && (
              <button type="button" onClick={() => exportCsv(stats)} data-testid="auction-stats-export-csv"
                className="ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-semibold normal-case border border-[#D9B35A]/30 text-[#E9CF8E] hover:bg-[#D9B35A]/10 transition-colors">
                <FileDown className="w-3 h-3" /> Export CSV
              </button>
            )}
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
