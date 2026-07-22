import { useEffect, useState } from 'react';
import { KanbanSquare, Lightbulb, TrendingUp } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const ProspectiaPipeline = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/admin/prospectia/pipeline`, { credentials: 'include' })
      .then((r) => r.json()).then(setData).catch(() => {});
  }, []);

  if (!data || !data.total) return null;
  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="prospectia-pipeline">
      <div className="flex items-center gap-3 flex-wrap mb-3">
        <h3 className="font-display text-base text-white flex items-center gap-2">
          <KanbanSquare size={15} style={{ color: '#D9B35A' }} /> Pipeline de vente PROSPECT'IA
        </h3>
        <span className="text-xs text-white/50">{data.total} prospect(s)</span>
        <span className="px-2 py-0.5 rounded bg-emerald-400/15 text-emerald-300 text-xs font-semibold inline-flex items-center gap-1">
          <TrendingUp size={10} /> {data.conversion_rate}% de conversion
        </span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {data.stages.map((s) => (
          <div key={s.key} className="rounded-xl bg-white/[0.04] border border-white/10 p-3 flex flex-col" data-testid={`pipeline-col-${s.key}`}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-white">{s.label}</p>
              <span className="px-1.5 py-0.5 rounded bg-[#D9B35A]/15 text-[#E9CF8E] text-xs font-bold">{s.count}</span>
            </div>
            <div className="space-y-1.5 max-h-44 overflow-y-auto flex-1">
              {s.prospects.map((p, i) => (
                <div key={`${p.email}-${i}`} className="p-1.5 rounded-lg bg-black/25 border border-white/[0.06]">
                  <p className="text-[11px] text-white/85 truncate">{p.first_name || p.email.split('@')[0]}{p.company ? ` · ${p.company}` : ''}</p>
                  <p className="text-[10px] text-white/40 truncate">{p.campaign}{p.variant ? ` (${p.variant})` : ''}</p>
                </div>
              ))}
              {!s.count && <p className="text-[10px] text-white/30 italic">Vide</p>}
            </div>
            <p className="mt-2 pt-2 border-t border-white/[0.08] text-[10px] text-white/45 flex items-start gap-1">
              <Lightbulb size={10} className="text-[#E9CF8E] flex-shrink-0 mt-0.5" /> {s.suggestion}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
