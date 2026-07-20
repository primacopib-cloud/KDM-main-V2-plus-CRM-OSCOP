import { useEffect, useState } from 'react';
import { ShieldAlert, FileDown, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

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
  const [ai, setAi] = useState({});
  const [loadingAi, setLoadingAi] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/buyer-tools/supply-risk`, { credentials: 'include' })
      .then((r) => r.json()).then(setData).catch(() => {});
  }, []);

  const exportPdf = async () => {
    const r = await fetch(`${API}/api/buyer-tools/supply-risk/pdf`, { credentials: 'include' });
    if (!r.ok) return toast.error('Export PDF impossible');
    const url = URL.createObjectURL(await r.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = `risque-approvisionnement-${new Date().toISOString().slice(0, 7)}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const askCoopia = async (cat) => {
    setLoadingAi(cat);
    try {
      const r = await fetch(`${API}/api/buyer-tools/procedure-suggestion?category=${encodeURIComponent(cat)}`, { credentials: 'include' });
      const d = await r.json();
      if (!r.ok) return toast.error(d.detail || 'Erreur');
      setAi((p) => ({ ...p, [cat]: d }));
    } finally {
      setLoadingAi(null);
    }
  };

  const cats = data?.categories || [];
  return (
    <div className={`${panel} p-5`} data-testid="supply-risk">
      <div className="flex flex-wrap items-center gap-2 mb-1">
        <h3 className="font-semibold text-white flex items-center gap-2 flex-1">
          <ShieldAlert className="w-4 h-4 text-[#D9B35A]" /> Risque d'approvisionnement par catégorie
        </h3>
        {cats.length > 0 && (
          <button type="button" onClick={exportPdf} data-testid="risk-export-pdf-btn"
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-bold bg-white/10 text-white/70 hover:text-white transition-colors">
            <FileDown className="w-3.5 h-3.5" /> Rapport PDF mensuel
          </button>
        )}
      </div>
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
              <div className="mt-2">
                {ai[c.category] ? (
                  <div className="p-2 rounded-lg bg-[#C9A8F0]/10 border border-[#C9A8F0]/25" data-testid={`coopia-result-${c.category}`}>
                    <p className="text-[10px] font-bold text-[#C9A8F0] flex items-center gap-1 mb-0.5">
                      <Sparkles className="w-3 h-3" /> COOP'IA recommande : {ai[c.category].procedure === 'ENCHERE_INVERSEE' ? 'Enchère inversée' : 'Offres scellées'}
                    </p>
                    <p className="text-[10.5px] text-white/65">{ai[c.category].rationale}</p>
                  </div>
                ) : (
                  <button type="button" onClick={() => askCoopia(c.category)} disabled={loadingAi === c.category} data-testid={`coopia-btn-${c.category}`}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold bg-[#C9A8F0]/15 text-[#C9A8F0] border border-[#C9A8F0]/30 hover:bg-[#C9A8F0]/25 transition-colors disabled:opacity-50">
                    <Sparkles className="w-3 h-3" /> {loadingAi === c.category ? "COOP'IA réfléchit…" : "Suggestion COOP'IA (procédure)"}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
