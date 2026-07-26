import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Receipt, Download, TrendingUp } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

export const PosCounterJournal = ({ refreshKey }) => {
  const [journal, setJournal] = useState(null);
  const [top, setTop] = useState([]);
  useEffect(() => {
    lolodriveAPI.posCounterJournal().then(setJournal).catch(() => {});
    lolodriveAPI.posTopProducts(30).then((d) => setTop(d.top || [])).catch(() => {});
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

  if ((!journal || journal.count === 0) && top.length === 0) return null;
  const maxQty = Math.max(...top.map((t) => t.qty), 1);
  return (
    <div className="mb-4 space-y-2">
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
