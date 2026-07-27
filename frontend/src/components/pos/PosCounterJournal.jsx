import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Receipt, Download, TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

const monthLabel = (ym) => {
  const [y, m] = ym.split('-');
  return new Date(y, m - 1, 1).toLocaleDateString('fr-FR', { month: 'long' });
};

export const PosCounterJournal = ({ refreshKey }) => {
  const [journal, setJournal] = useState(null);
  const [top, setTop] = useState([]);
  const [compare, setCompare] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [seller, setSeller] = useState(null);
  useEffect(() => {
    lolodriveAPI.posCounterJournal().then(setJournal).catch(() => {});
    lolodriveAPI.posTopProducts(30).then((d) => setTop(d.top || [])).catch(() => {});
    lolodriveAPI.posMonthlyCompare().then(setCompare).catch(() => {});
    lolodriveAPI.posStockAlerts(30).then((d) => setAlerts(d.alerts || [])).catch(() => {});
    lolodriveAPI.posBestSeller().then(setSeller).catch(() => {});
  }, [refreshKey]);

  const exportCsv = async () => {
    try {
      const month = new Date().toISOString().slice(0, 7);
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/pos/counter-journal/export?month=${month}`,
        { credentials: 'include' });
      if (!r.ok) { toast.error('Export impossible'); return; }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `caisse-${month}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Journal de caisse du mois téléchargé ✓');
    } catch { toast.error('Erreur de connexion'); }
  };

  if ((!journal || journal.count === 0) && top.length === 0 && alerts.length === 0 && !(compare && compare.current.count > 0)) return null;
  const maxQty = Math.max(...top.map((t) => t.qty), 1);
  const TrendIcon = compare?.trend === 'up' ? TrendingUp : compare?.trend === 'down' ? TrendingDown : Minus;
  const trendColor = compare?.trend === 'up' ? 'text-emerald-300' : compare?.trend === 'down' ? 'text-red-300' : 'text-white/50';
  return (
    <div className="mb-4 space-y-2">
      {alerts.length > 0 && (
        <div className="rounded-xl border border-amber-400/40 bg-amber-400/[0.07] px-4 py-2.5" data-testid="stock-alerts">
          <p className="text-xs font-bold text-amber-300 flex items-center gap-1.5 mb-1">
            <AlertTriangle className="w-3.5 h-3.5" /> Alerte stock bas — produits du top ventes
          </p>
          <div className="space-y-0.5">
            {alerts.map((a) => (
              <p key={a.sku} className="text-xs text-white/70" data-testid={`stock-alert-${a.sku}`}>
                <b className={a.critical ? 'text-red-300' : 'text-amber-200'}>{a.name}</b>
                {' — '}{a.stock_qty} en stock · {a.sold_qty} vendus / 30 j
                {a.days_left !== null && <> · rupture estimée dans <b className={a.critical ? 'text-red-300' : 'text-amber-200'}>~{a.days_left} j</b></>}
                {a.critical && <span className="ml-1.5 px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 font-bold text-[10px]">RÉASSORT URGENT</span>}
              </p>
            ))}
          </div>
        </div>
      )}
      {compare && (compare.current.count > 0 || compare.previous_full.count > 0) && (
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs"
          data-testid="monthly-compare">
          <span className={`flex items-center gap-1.5 font-bold ${trendColor}`}>
            <TrendIcon className="w-3.5 h-3.5" /> Caisse {monthLabel(compare.current_month)} (J1→J{compare.day_of_month})
          </span>
          <span className="font-mono" data-testid="compare-current"><b>{(compare.current.total_cents / 100).toFixed(2)} €</b> ({compare.current.count} ventes)</span>
          <span className="text-white/40">vs {monthLabel(compare.previous_month)} même période :</span>
          <span className="font-mono text-white/60" data-testid="compare-previous">{(compare.previous_same_period.total_cents / 100).toFixed(2)} €</span>
          {compare.delta_percent !== null && (
            <span className={`font-bold font-mono ${trendColor}`} data-testid="compare-delta">
              {compare.delta_percent > 0 ? '▲ +' : compare.delta_percent < 0 ? '▼ ' : ''}{compare.delta_percent}%
            </span>
          )}
          <span className="ml-auto text-white/35">Total {monthLabel(compare.previous_month)} : {(compare.previous_full.total_cents / 100).toFixed(2)} €</span>
        </div>
      )}
      {journal && journal.count > 0 && (
        <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/[0.05] px-4 py-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs"
          data-testid="counter-journal">
          <span className="flex items-center gap-1.5 font-bold text-emerald-300">
            <Receipt className="w-3.5 h-3.5" /> Caisse du jour ({journal.date})
          </span>
          <span data-testid="journal-count">{journal.count} vente{journal.count > 1 ? 's' : ''}</span>
          <span className="font-mono" data-testid="journal-cash">💵 Espèces : <b>{(journal.cash_cents / 100).toFixed(2)} €</b></span>
          <span className="font-mono" data-testid="journal-card">💳 CB : <b>{(journal.card_cents / 100).toFixed(2)} €</b></span>
          <span className="font-mono text-emerald-300" data-testid="journal-total">Total : <b>{(journal.total_cents / 100).toFixed(2)} €</b></span>
          <button type="button" onClick={exportCsv} data-testid="export-csv-btn"
            className="ml-auto flex items-center gap-1 px-2.5 py-1 rounded-lg font-bold text-emerald-300 bg-emerald-400/10 border border-emerald-400/35 hover:bg-emerald-400/20">
            <Download className="w-3 h-3" /> Export CSV du mois
          </button>
        </div>
      )}
      {seller && (seller.last_week_winner || seller.current_week.length > 0) && (
        <div className="rounded-xl border border-[#D9B35A]/30 bg-[#D9B35A]/[0.05] px-4 py-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs"
          data-testid="best-seller-badge">
          {seller.last_week_winner && (
            <span data-testid="best-seller-winner">
              <span className="font-bold text-[#D9B35A]">🏆 Meilleur vendeur de la semaine passée :</span>{' '}
              <b>{seller.last_week_winner.name}</b>
              <span className="text-white/50"> ({seller.last_week_winner.count} vente{seller.last_week_winner.count > 1 ? 's' : ''} · {(seller.last_week_winner.total_cents / 100).toFixed(2)} €) — Félicitations ! 🎉</span>
            </span>
          )}
          {seller.current_week.length > 0 && (
            <span className="text-white/50" data-testid="best-seller-race">
              Course de la semaine : {seller.current_week.slice(0, 3).map((s, i) =>
                `${i + 1}. ${s.name} (${s.count})`).join(' · ')}
            </span>
          )}
        </div>
      )}
      {journal && journal.by_operator?.length > 0 && (
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs"
          data-testid="journal-by-operator">
          <span className="font-bold text-white/50 uppercase tracking-wider text-[10px]">Par opérateur</span>
          {journal.by_operator.map((op) => (
            <span key={op.name} className="font-mono" data-testid={`operator-sales-${op.name}`}>
              <b className="text-emerald-300">{op.name}</b>
              <span className="text-white/60"> : {op.count} vente{op.count > 1 ? 's' : ''} · {(op.total_cents / 100).toFixed(2)} €</span>
              <span className="text-white/35"> (💵 {(op.cash_cents / 100).toFixed(2)} · 💳 {(op.card_cents / 100).toFixed(2)})</span>
            </span>
          ))}
        </div>
      )}
      {top.length > 0 && (
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] px-4 py-3" data-testid="top-products">
          <p className="text-[11px] uppercase tracking-wider text-white/40 mb-2 flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-[#D9B35A]" /> Top produits comptoir (30 derniers jours)
          </p>
          <div className="space-y-1.5">
            {top.map((t, i) => (
              <div key={t.sku} className="flex items-center gap-2 text-xs" data-testid={`top-product-${i + 1}`}>
                <span className="w-4 font-black text-[#D9B35A]">{i + 1}</span>
                <span className="truncate w-48">{t.name}</span>
                <span className="flex-1 h-2 rounded-full bg-white/[0.05] overflow-hidden">
                  <span className="block h-full rounded-full" style={{ width: `${Math.max(6, (t.qty / maxQty) * 100)}%`, background: 'linear-gradient(90deg,#D9B35A,#F5A623)' }} />
                </span>
                <span className="font-mono shrink-0 text-white/70">×{t.qty} · {(t.revenue_cents / 100).toFixed(2)} €</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
