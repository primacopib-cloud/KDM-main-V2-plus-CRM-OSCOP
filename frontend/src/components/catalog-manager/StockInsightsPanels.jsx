import { useState, useEffect } from 'react';
import { AlertTriangle, ShoppingCart, Download } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—');

const ExportCsvButton = ({ path, filename, testid }) => {
  const exportCsv = async () => {
    try {
      const res = await fetch(`${API_URL}${path}`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${filename}_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Export CSV téléchargé');
    } catch {
      toast.error("Échec de l'export CSV");
    }
  };
  return (
    <button type="button" onClick={exportCsv} data-testid={testid}
      className="inline-flex items-center gap-1.5 h-8 px-2.5 mb-2 rounded-lg text-[11px] font-semibold text-[#E9CF8E] bg-[#D9B35A]/10 border border-[#D9B35A]/30 hover:bg-[#D9B35A]/20 transition-colors">
      <Download className="w-3 h-3" /> Export CSV
    </button>
  );
};

const CollapsePanel = ({ icon: Icon, title, testid, children }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl bg-white/[0.02] border border-white/[0.08] mb-4" data-testid={testid}>
      <button type="button" onClick={() => setOpen(!open)} data-testid={`${testid}-toggle`}
        className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm font-semibold text-[#E9CF8E] hover:bg-white/[0.03] rounded-xl transition-colors">
        <Icon className="w-4 h-4" /> {title}
        <span className="ml-auto text-xs text-white/40">{open ? 'Réduire' : 'Ouvrir'}</span>
      </button>
      {open && <div className="px-4 pb-4">{children(open)}</div>}
    </div>
  );
};

export const StockoutStatsPanel = () => {
  const [stats, setStats] = useState(null);
  const load = () => {
    fetch(`${API_URL}/api/catalog/admin/stockout-stats`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then((d) => setStats(d.stats || [])).catch(() => setStats([]));
  };
  return (
    <CollapsePanel icon={AlertTriangle} title="Ruptures par territoire (produits les plus touchés)" testid="stockout-stats-panel">
      {() => {
        if (stats === null) { load(); return <p className="text-xs text-white/40">Chargement…</p>; }
        if (!stats.length) return <p className="text-xs text-white/40 py-1">Aucune rupture enregistrée.</p>;
        return (
          <>
          <ExportCsvButton path="/api/catalog/admin/stockout-stats/export" filename="ruptures_territoires" testid="stockout-export-csv" />
          <table className="w-full text-left">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-white/40">
                <th className="py-1.5 pr-2">Produit</th><th className="py-1.5 pr-2">Territoire</th>
                <th className="py-1.5 pr-2 text-center">Nb ruptures</th><th className="py-1.5 pr-2">Dernière rupture</th><th className="py-1.5">État</th>
              </tr>
            </thead>
            <tbody>
              {stats.map((s) => (
                <tr key={`${s.product_id}-${s.zone_code}`} className="border-t border-white/[0.06] text-xs" data-testid="stockout-row">
                  <td className="py-2 pr-2 text-white/85">{s.product_name}</td>
                  <td className="py-2 pr-2 text-white/60">{s.zone_code}</td>
                  <td className="py-2 pr-2 text-center font-mono text-amber-300">{s.stockout_count}</td>
                  <td className="py-2 pr-2 text-white/50 font-mono">{fmtDate(s.last_stockout_at)}</td>
                  <td className="py-2">
                    {s.currently_out
                      ? <span className="px-1.5 py-0.5 rounded text-[9px] font-bold text-red-300 bg-red-500/15 border border-red-400/40">EN RUPTURE</span>
                      : <span className="px-1.5 py-0.5 rounded text-[9px] font-bold text-emerald-300 bg-emerald-500/10 border border-emerald-400/30">Disponible</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </>
        );
      }}
    </CollapsePanel>
  );
};

export const AbandonedCartsPanel = () => {
  const [data, setData] = useState(null);
  const load = () => {
    fetch(`${API_URL}/api/catalog/admin/abandoned-reservations`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then(setData).catch(() => setData({ entries: [], total: 0 }));
  };
  return (
    <CollapsePanel icon={ShoppingCart} title="Paniers abandonnés (réservations expirées sans commande)" testid="abandoned-carts-panel">
      {() => {
        if (data === null) { load(); return <p className="text-xs text-white/40">Chargement…</p>; }
        if (!data.entries?.length) return <p className="text-xs text-white/40 py-1">Aucune réservation expirée tracée pour l'instant.</p>;
        return (
          <>
            <div className="flex items-center justify-between">
              <p className="text-[11px] text-white/50 mb-2">{data.total} réservation(s) expirée(s) au total — relance email automatique (max 1/24 h par organisation)</p>
              <ExportCsvButton path="/api/catalog/admin/abandoned-reservations/export" filename="paniers_abandonnes" testid="abandoned-export-csv" />
            </div>
            <table className="w-full text-left">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-white/40">
                  <th className="py-1.5 pr-2">Organisation</th><th className="py-1.5 pr-2">Produit</th>
                  <th className="py-1.5 pr-2">Territoire</th><th className="py-1.5 pr-2 text-center">Qté</th>
                  <th className="py-1.5 pr-2 text-center">Prolong.</th><th className="py-1.5 pr-2">Expirée le</th>
                  <th className="py-1.5">Relancé</th>
                </tr>
              </thead>
              <tbody>
                {data.entries.map((e) => (
                  <tr key={e.id} className="border-t border-white/[0.06] text-xs" data-testid="abandoned-row">
                    <td className="py-2 pr-2 text-white/85">{e.org_name}</td>
                    <td className="py-2 pr-2 text-white/70">{e.product_name}</td>
                    <td className="py-2 pr-2 text-white/60">{e.zone_code}</td>
                    <td className="py-2 pr-2 text-center font-mono text-white/80">{e.quantity}</td>
                    <td className="py-2 pr-2 text-center font-mono text-white/50">{e.extend_count}</td>
                    <td className="py-2 pr-2 text-white/50 font-mono">{fmtDate(e.expired_at)}</td>
                    <td className="py-2">
                      {e.reminded
                        ? <span className="px-1.5 py-0.5 rounded text-[9px] font-bold text-emerald-300 bg-emerald-500/10 border border-emerald-400/30">✉ OUI</span>
                        : <span className="text-[9px] text-white/35">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        );
      }}
    </CollapsePanel>
  );
};
