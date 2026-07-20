import { useEffect, useState } from 'react';
import { ShieldAlert } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const panel = 'bg-white/[0.04] border border-white/[0.08] rounded-2xl';

const LEVELS = {
  ELEVE: { label: 'ÉLEVÉ', cls: 'bg-red-500/15 text-red-400', bar: '#EF4444' },
  MODERE: { label: 'MODÉRÉ', cls: 'bg-amber-500/15 text-amber-400', bar: '#F59E0B' },
  FAIBLE: { label: 'FAIBLE', cls: 'bg-emerald-500/15 text-emerald-400', bar: '#34D399' },
};
const TRENDS = { up: 'demande en hausse', down: 'demande en baisse', stable: 'demande stable' };

export const SupplyRisk = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/buyer-tools/supply-risk`, { credentials: 'include' })
      .then((r) => r.json()).then(setData).catch(() => {});
  }, []);

  const cats = data?.categories || [];
  return (
    <div className={`${panel} p-5`} data-testid="supply-risk">
      <h3 className="font-semibold text-white mb-1 flex items-center gap-2">
        <ShieldAlert className="w-4 h-4 text-[#D9B35A]" /> Risque d'approvisionnement par catégorie
      </h3>
      <p className="text-[11px] text-white/40 mb-4">{data?.method || 'Liquidité fournisseurs croisée avec la tendance de demande.'}</p>
      {!cats.length && <p className="text-xs text-white/40">Aucune catégorie référencée pour l'instant.</p>}
      <div className="space-y-2.5">
        {cats.map((c) => {
          const L = LEVELS[c.risk_level] || LEVELS.MODERE;
          return (
            <div key={c.category} className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]" data-testid={`risk-cat-${c.category}`}>
              <div className="flex flex-wrap items-center gap-2 mb-1.5">
                <span className="text-sm font-bold text-white capitalize flex-1 min-w-[120px]">{c.category}</span>
                <span className="text-[11px] text-white/50">{c.eligible_vendors} fournisseur(s) éligible(s) · {TRENDS[c.demand_trend]} · {c.lots_6m} lot(s) / 6 mois</span>
                <span className={`px-2 py-0.5 rounded-lg text-[10px] font-bold ${L.cls}`} data-testid={`risk-level-${c.category}`}>
                  {L.label} · {c.risk_score}/100
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-white/10 overflow-hidden mb-1.5">
                <div className="h-full rounded-full transition-all" style={{ width: `${c.risk_score}%`, background: L.bar }} />
              </div>
              <p className="text-[10.5px] text-white/50">{c.recommendation}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
