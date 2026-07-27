import { useEffect, useState } from 'react';
import { Coins, ChevronDown, ChevronUp } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

const monthLabel = (ym) =>
  new Date(`${ym}-01`).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });

export const UcFeesSummary = () => {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    lolodriveAPI.adminUcFeesSummary(6).then(setData).catch(() => {});
  }, []);
  if (!data || data.rows.length === 0) return null;
  return (
    <div className="mb-6 rounded-2xl border border-[#D9B35A]/30 bg-[#D9B35A]/[0.04] p-4" data-testid="uc-fees-summary">
      <button type="button" onClick={() => setOpen((v) => !v)} data-testid="uc-fees-toggle"
        className="w-full flex items-center gap-2 text-sm font-semibold text-[#D9B35A]">
        <Coins className="w-4 h-4" /> Revenus UC — frais produits relais
        <span className="ml-auto font-mono text-base" data-testid="uc-fees-total">{data.total_uc} UC</span>
        <span className="text-white/40 text-xs font-normal">({data.months} derniers mois)</span>
        {open ? <ChevronUp className="w-4 h-4 text-white/40" /> : <ChevronDown className="w-4 h-4 text-white/40" />}
      </button>
      {open && (
        <div className="mt-3 space-y-1" data-testid="uc-fees-rows">
          <div className="grid grid-cols-[1fr_5rem_5rem] gap-2 text-[10px] uppercase tracking-wider text-white/35 px-2">
            <span>Mois · Relais</span><span className="text-right">Ventes</span><span className="text-right">UC</span>
          </div>
          {data.rows.map((r, i) => (
            <div key={i} className="grid grid-cols-[1fr_5rem_5rem] gap-2 text-xs px-2 py-1.5 rounded-lg bg-white/[0.03]"
              data-testid={`uc-fees-row-${i}`}>
              <span className="truncate capitalize">{monthLabel(r.month)} — <b>{r.point_code}</b> <span className="text-white/40">{r.point_name}</span></span>
              <span className="text-right font-mono text-white/60">{r.count}</span>
              <span className="text-right font-mono font-bold text-[#D9B35A]">{r.total_uc} UC</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
