import { useEffect, useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp, Download } from 'lucide-react';
import { toast } from 'sonner';
import { lolodriveAPI } from '../../services/api';

const fmtDate = (d) => (d ? new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—');

// Super admin : historique des commandes pénalisées (non retirées) + total UC par relais
export const PenaltiesHistory = () => {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));

  useEffect(() => {
    lolodriveAPI.adminPenalties().then(setData).catch(() => {});
  }, []);
  if (!data) return null;

  const exportCsv = async (e) => {
    e.stopPropagation();
    try {
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/admin/penalties-export?month=${month}`,
        { credentials: 'include' });
      if (!r.ok) { toast.error('Export impossible'); return; }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `penalites-${month}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Pénalités exportées en CSV ✓');
    } catch { toast.error('Erreur de connexion'); }
  };

  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="penalties-history">
      <button type="button" onClick={() => setOpen(!open)} data-testid="penalties-toggle"
        className="w-full flex flex-wrap items-center justify-between gap-3 text-left">
        <div className="font-semibold flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-400" /> Historique des pénalités de non-retrait
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-white/50">{data.orders.length} commande(s)</span>
          <span className="font-bold text-red-400" data-testid="penalties-total">{data.total_uc} UC ({(data.total_uc / 10).toFixed(2)} €)</span>
          {open ? <ChevronUp className="w-4 h-4 text-white/40" /> : <ChevronDown className="w-4 h-4 text-white/40" />}
        </div>
      </button>
      {open && (
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <input type="month" value={month} onChange={(e) => setMonth(e.target.value)}
              data-testid="penalties-month-input"
              className="bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-xs text-white" />
            <button type="button" onClick={exportCsv} data-testid="penalties-export-btn"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-cyan-300 bg-cyan-500/10 border border-cyan-500/30 hover:bg-cyan-500/20">
              <Download className="w-3 h-3" /> Export CSV comptable
            </button>
          </div>
          <div className="flex flex-wrap gap-2" data-testid="penalties-by-point">
            {data.by_point.map((p) => (
              <div key={p.code} data-testid={`penalties-point-${p.code}`}
                className="rounded-lg bg-red-500/[0.06] border border-red-500/20 px-3 py-2 text-xs">
                <div className="font-semibold">{p.name} <span className="text-white/40">({p.code})</span></div>
                <div className="text-red-400 font-bold">{p.total_uc} UC <span className="text-white/40 font-normal">· {p.count} cde(s)</span></div>
              </div>
            ))}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs" data-testid="penalties-table">
              <thead>
                <tr className="text-white/40 uppercase text-[10px] tracking-wider text-left">
                  <td className="py-1.5 pr-2">N° commande</td>
                  <td className="py-1.5 px-2">Date pénalité</td>
                  <td className="py-1.5 px-2">Client</td>
                  <td className="py-1.5 px-2">Relais</td>
                  <td className="py-1.5 px-2">Articles</td>
                  <td className="py-1.5 px-2">Pénalité</td>
                  <td className="py-1.5 px-2">Statut</td>
                </tr>
              </thead>
              <tbody>
                {data.orders.map((o, i) => (
                  <tr key={o.order_number || i} className="border-t border-white/[0.05]" data-testid={`penalty-row-${i}`}>
                    <td className="py-1.5 pr-2 font-mono">{o.order_number}</td>
                    <td className="py-1.5 px-2 text-white/60">{fmtDate(o.penalized_at)}</td>
                    <td className="py-1.5 px-2">{o.customer}</td>
                    <td className="py-1.5 px-2 text-white/60">{o.point_code || '—'}</td>
                    <td className="py-1.5 px-2 text-white/60">{o.items_count}</td>
                    <td className="py-1.5 px-2 font-bold text-red-400">{o.penalty_uc} UC</td>
                    <td className="py-1.5 px-2">
                      {o.refunded
                        ? <span className="text-cyan-300 font-semibold">Remboursée (retrait tardif)</span>
                        : o.auto_cancelled
                          ? <span className="text-red-400 font-semibold">Annulée auto</span>
                          : o.status === 'FULFILLED'
                            ? <span className="text-emerald-400">Retirée</span>
                            : <span className="text-amber-400">{o.status === 'READY' ? 'En attente' : o.status}</span>}
                    </td>
                  </tr>
                ))}
                {!data.orders.length && (
                  <tr><td colSpan="7" className="py-3 text-white/40 text-center">Aucune pénalité enregistrée.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-white/40">
            Les commandes prêtes non retirées 48 h après leur mise à disposition sont annulées automatiquement,
            leurs articles remis en stock et le client prévenu par email + SMS.
          </p>
        </div>
      )}
    </div>
  );
};
