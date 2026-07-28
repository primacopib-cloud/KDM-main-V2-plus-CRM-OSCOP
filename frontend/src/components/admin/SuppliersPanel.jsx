import { useState } from 'react';
import { Factory, ChevronDown, ChevronUp } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

const badge = (s) => {
  if (!s.orders) return <span className="px-1.5 py-0.5 rounded bg-white/[0.08] text-white/50 font-bold text-[10px]">— nouveau</span>;
  if (s.late === 0 && s.missing_qty === 0) return <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-bold text-[10px]">🟢 Fiable</span>;
  if (s.late >= 2 || s.missing_qty >= 5) return <span className="px-1.5 py-0.5 rounded bg-red-500/15 text-red-300 font-bold text-[10px]">🔴 À surveiller</span>;
  return <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 font-bold text-[10px]">🟠 Moyen</span>;
};

// Super admin : fiche fournisseur — produits, bons, écarts, retards → fiabilité
export const SuppliersPanel = () => {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);

  const toggle = () => {
    if (!open && data === null) lolodriveAPI.adminSuppliers().then(setData).catch(() => setData({ suppliers: [] }));
    setOpen(!open);
  };

  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="suppliers-panel">
      <button type="button" onClick={toggle} data-testid="suppliers-toggle"
        className="w-full flex items-center justify-between text-left">
        <span className="font-semibold flex items-center gap-2">
          <Factory className="w-4 h-4 text-[#D9B35A]" /> Fiches fournisseurs
          {data && <span className="text-xs font-normal text-white/40">({data.suppliers.length})</span>}
        </span>
        {open ? <ChevronUp className="w-4 h-4 text-white/40" /> : <ChevronDown className="w-4 h-4 text-white/40" />}
      </button>
      {open && (
        <div className="mt-3 space-y-2 max-h-96 overflow-y-auto">
          {data && data.suppliers.some((s) => s.orders > 0) && (
            <div className="flex flex-wrap items-center gap-2 pb-1" data-testid="suppliers-podium">
              <span className="text-[10px] uppercase tracking-wide text-white/35 font-bold">Top fiabilité réseau :</span>
              {[...data.suppliers].filter((s) => s.orders > 0).sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).slice(0, 3).map((s, i) => (
                <span key={s.supplier} data-testid={`podium-${i + 1}`}
                  className="px-2 py-1 rounded-lg bg-[#D9B35A]/10 border border-[#D9B35A]/30 text-[11px] font-bold text-[#D9B35A]">
                  {['🥇', '🥈', '🥉'][i]} {s.supplier} — {s.score}/100
                </span>
              ))}
            </div>
          )}
          {data === null && <p className="text-[11px] text-white/30">Chargement…</p>}
          {data?.suppliers.length === 0 && <p className="text-[11px] text-white/30">Aucun fournisseur renseigné sur les fiches produits.</p>}
          {data?.suppliers.map((s) => (
            <div key={s.supplier} className="rounded-lg bg-white/[0.03] border border-white/[0.06] px-3 py-2.5" data-testid={`supplier-card-${s.supplier}`}>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <b>{s.supplier}</b>
                {s.supplier_email && <span className="text-white/35">{s.supplier_email}</span>}
                {s.score != null && <span className="text-white/40 font-mono text-[10px]" data-testid={`score-${s.supplier}`}>{s.score}/100</span>}
                <span className="ml-auto">{badge(s)}</span>
              </div>
              <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-white/50">
                <span>{s.products.length} produit(s)</span>
                <span>{s.orders} bon(s) · {s.received} reçu(s)</span>
                <span className={s.late > 0 ? 'text-red-300 font-bold' : ''}>{s.late} retard(s)</span>
                <span className={s.missing_qty > 0 ? 'text-amber-300 font-bold' : ''}>{s.missing_qty} manquant(s)</span>
                {s.total_cents > 0 && <span className="text-emerald-300/80">achats : {(s.total_cents / 100).toFixed(2)} €</span>}
              </div>
              <p className="mt-1 text-[10px] text-white/30 truncate">{s.products.join(', ')}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
