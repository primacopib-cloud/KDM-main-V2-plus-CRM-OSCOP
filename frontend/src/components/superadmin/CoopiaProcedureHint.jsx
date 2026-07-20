import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

export const CoopiaProcedureHint = ({ category, onApply }) => {
  const [sug, setSug] = useState(null);
  const [loading, setLoading] = useState(false);

  const ask = async () => {
    if (!category?.trim()) return toast.error('Renseignez d\'abord la catégorie');
    setLoading(true);
    try {
      const r = await fetch(`${API}/buyer-tools/procedure-suggestion?category=${encodeURIComponent(category.trim().toLowerCase())}`,
        { credentials: 'include', headers: getAuthHeaders() });
      const d = await r.json();
      if (!r.ok) return toast.error(d.detail || 'Pas de données de risque pour cette catégorie');
      setSug(d);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-2.5 rounded-xl bg-[#C9A8F0]/[0.06] border border-[#C9A8F0]/20 space-y-1.5" data-testid="coopia-hint">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-[10px] font-bold text-[#C9A8F0] flex items-center gap-1.5 flex-1">
          <Sparkles className="w-3 h-3" /> COOP'IA — quelle procédure choisir ?
        </p>
        <button type="button" onClick={ask} disabled={loading} data-testid="coopia-hint-btn"
          className="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-[#C9A8F0]/15 text-[#C9A8F0] border border-[#C9A8F0]/30 hover:bg-[#C9A8F0]/25 transition-colors disabled:opacity-50">
          {loading ? 'Analyse…' : 'Analyser la catégorie'}
        </button>
      </div>
      {sug && (
        <div data-testid="coopia-hint-result">
          <p className="text-[11px] text-white/80">
            <b className="text-[#E9CF8E]">{sug.procedure === 'ENCHERE_INVERSEE' ? 'Enchère inversée' : 'Offres scellées'}</b>
            <span className="text-white/45"> · risque {sug.risk_score}/100 ({sug.risk_level}) · {sug.eligible_vendors} fournisseur(s)</span>
          </p>
          <p className="text-[10.5px] text-white/55 mt-0.5">{sug.rationale}</p>
          <button type="button" onClick={() => { onApply(sug.procedure); toast.success(`Procédure ${sug.procedure === 'ENCHERE_INVERSEE' ? 'Enchère inversée' : 'Offres scellées'} appliquée`); }}
            data-testid="coopia-hint-apply"
            className="mt-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }}>
            Appliquer cette procédure
          </button>
        </div>
      )}
    </div>
  );
};
