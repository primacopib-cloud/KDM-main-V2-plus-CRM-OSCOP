import { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

export const GuidiaStatsPanel = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/ai-guide/admin/stats`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null)).then(setData).catch(() => {});
  }, []);

  if (!data) return null;
  return (
    <div className="glass-panel-soft rounded-[14px] p-3 mt-4" data-testid="guidia-stats-panel">
      <p className="text-[11px] font-semibold text-[#D9B35A] mb-2 flex items-center gap-1.5">
        <Sparkles className="w-3.5 h-3.5" /> GUID'IA — questions des membres (points de friction)
      </p>
      <div className="flex flex-wrap gap-2 mb-3">
        <span className="rounded-lg px-3 py-1.5 bg-white/[0.04] border border-white/[0.08] text-[11px] text-white/70">
          <b className="text-[#E9CF8E]">{data.total_questions}</b> questions posées
        </span>
        <span className="rounded-lg px-3 py-1.5 bg-white/[0.04] border border-white/[0.08] text-[11px] text-white/70">
          <b className="text-[#E9CF8E]">{data.unique_users}</b> utilisateur(s)
        </span>
        {Object.entries(data.by_space || {}).map(([s, n]) => (
          <span key={s} className="rounded-lg px-3 py-1.5 bg-white/[0.04] border border-white/[0.08] text-[11px] text-white/50">
            {s} : <b className="text-white/80">{n}</b>
          </span>
        ))}
      </div>
      {data.top_questions?.length > 0 && (
        <table className="w-full text-[11px]" data-testid="guidia-top-questions">
          <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
            <th className="py-1 pr-3">Question la plus posée</th>
            <th className="py-1 pr-3 text-right">Occurrences</th>
            <th className="py-1 text-right">Dernière fois</th></tr></thead>
          <tbody>
            {data.top_questions.map((q, i) => (
              <tr key={i} className="border-b border-white/[0.04] text-white/75">
                <td className="py-1.5 pr-3">{q.question}</td>
                <td className="py-1.5 pr-3 text-right font-bold text-[#E9CF8E]">{q.count}</td>
                <td className="py-1.5 text-right text-white/40">{(q.last_asked || '').slice(0, 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
