import { useState } from 'react';
import { PackagePlus, ChevronDown, ChevronUp } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

const fmtDate = (iso) => new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' });

// Super admin : vue réseau des bons de commande fournisseur (tous relais) + retards
export const RestockAdminPanel = () => {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);

  const toggle = () => {
    if (!open && data === null) lolodriveAPI.adminRestockOrders().then(setData).catch(() => setData({ orders: [], pending: 0, late: 0 }));
    setOpen(!open);
  };

  const badge = (o) => {
    if (o.received_at) return <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-bold text-[10px]">✅ reçu le {fmtDate(o.received_at)}</span>;
    if ((o.days_pending ?? 0) >= 5) return <span className="px-1.5 py-0.5 rounded bg-red-500/15 text-red-300 font-bold text-[10px]">⚠️ retard {o.days_pending} j</span>;
    return <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 font-bold text-[10px]">⏳ en attente</span>;
  };

  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="restock-admin-panel">
      <button type="button" onClick={toggle} data-testid="restock-admin-toggle"
        className="w-full flex flex-wrap items-center justify-between gap-3 text-left">
        <div className="font-semibold flex items-center gap-2">
          <PackagePlus className="w-4 h-4 text-emerald-400" /> Réassort réseau — bons de commande fournisseur
          {data && (
            <span className="flex items-center gap-1.5 text-xs font-normal">
              <span className="px-1.5 py-0.5 rounded bg-white/[0.06] text-white/60" data-testid="restock-admin-total">{data.count} bon(s)</span>
              <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300" data-testid="restock-admin-pending">{data.pending} en attente</span>
              {data.late > 0 && <span className="px-1.5 py-0.5 rounded bg-red-500/15 text-red-300 font-bold" data-testid="restock-admin-late">{data.late} en retard</span>}
            </span>
          )}
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-white/40" /> : <ChevronDown className="w-4 h-4 text-white/40" />}
      </button>
      {open && (
        <div className="mt-3 space-y-1.5 max-h-80 overflow-y-auto" data-testid="restock-admin-list">
          {data === null && <p className="text-[11px] text-white/30">Chargement…</p>}
          {data?.orders.length === 0 && <p className="text-[11px] text-white/30">Aucun bon de commande sur le réseau.</p>}
          {data?.orders.map((o) => (
            <div key={o.id} className="flex flex-wrap items-center gap-x-2.5 gap-y-1 rounded-lg bg-white/[0.03] border border-white/[0.06] px-2.5 py-2 text-xs"
              data-testid={`restock-admin-row-${o.order_number}`}>
              <span className="text-white/35 font-mono">{fmtDate(o.created_at)}</span>
              <span className="px-1.5 py-0.5 rounded bg-[#D9B35A]/10 text-[#D9B35A] font-bold text-[10px]">{o.point_code || '—'}</span>
              <b className="font-mono">{o.order_number}</b>
              <span className="text-white/50 truncate">
                {o.lines.map((l) => `${l.name} ×${l.qty}`).join(', ')}
              </span>
              {(o.shortages || []).length > 0 && <span className="text-red-300 text-[10px] font-bold">écart : {o.shortages.reduce((a, s) => a + s.missing, 0)} manquant(s)</span>}
              <span className="ml-auto">{badge(o)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
