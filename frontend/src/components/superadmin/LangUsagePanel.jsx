import { useEffect, useState } from 'react';
import { Languages, TrendingUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { API, getAuthHeaders } from '../../services/http';

const LANGS = [
  { code: 'fr', flag: '🇫🇷', label: 'Français', color: '#5B9BD5' },
  { code: 'en', flag: '🇬🇧', label: 'English', color: '#8CC63E' },
  { code: 'es', flag: '🇪🇸', label: 'Español', color: '#D9B35A' },
  { code: 'gcf', flag: '🇬🇵', label: 'Kréyòl', color: '#B58CD9' },
  { code: 'ar', flag: '🇸🇦', label: 'العربية', color: '#E97B7B' },
];

// Répartition des langues réellement utilisées par les visiteurs (30 derniers jours)
export const LangUsagePanel = () => {
  const [stats, setStats] = useState(null);
  const [showTrend, setShowTrend] = useState(false);

  useEffect(() => {
    fetch(`${API}/admin/lang-usage/stats?days=30`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then(setStats)
      .catch(() => {});
  }, []);

  if (!stats) return null;

  return (
    <div className="bg-white rounded-2xl border border-[#EDE1C6] p-5" data-testid="lang-usage-panel">
      <h3 className="text-sm font-bold text-[#3D2E1E] flex items-center gap-2 m-0 mb-1">
        <Languages className="w-4 h-4 text-[#D9B35A]" /> Langues des visiteurs (30 jours)
      </h3>
      <p className="text-[11px] text-[#8A785F] m-0 mb-3" data-testid="lang-usage-total">
        {stats.total} visite(s) linguistique(s) enregistrée(s)
      </p>
      <div className="space-y-2.5">
        {LANGS.map((l) => (
          <div key={l.code} data-testid={`lang-usage-row-${l.code}`}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-[#3D2E1E] font-medium">{l.flag} {l.label}</span>
              <span className="text-[#8A785F]">
                {stats.totals[l.code] || 0} · <b className="text-[#3D2E1E]">{stats.shares[l.code] || 0}%</b>
              </span>
            </div>
            <div className="h-2 rounded-full bg-[#F3E9D2] overflow-hidden">
              <div className="h-full rounded-full transition-[width]"
                style={{ width: `${stats.shares[l.code] || 0}%`, background: l.color }} />
            </div>
          </div>
        ))}
      </div>
      <button type="button" onClick={() => setShowTrend((v) => !v)} data-testid="lang-trend-toggle"
        className="mt-3 inline-flex items-center gap-1.5 text-[11px] font-semibold text-[#8A5A18] hover:text-[#5B2E8C] transition-colors">
        <TrendingUp className="w-3.5 h-3.5" />
        {showTrend ? 'Masquer la tendance' : 'Voir la tendance jour par jour'}
      </button>
      {showTrend && (
        <div className="mt-2 h-44" data-testid="lang-trend-chart">
          {(stats.daily || []).length ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats.daily} margin={{ top: 5, right: 8, left: -22, bottom: 0 }}>
                <XAxis dataKey="day" tick={{ fontSize: 9, fill: '#8A785F' }}
                  tickFormatter={(d) => d.slice(5)} />
                <YAxis allowDecimals={false} tick={{ fontSize: 9, fill: '#8A785F' }} />
                <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8 }} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                {LANGS.map((l) => (
                  <Line key={l.code} type="monotone" dataKey={l.code} name={`${l.flag} ${l.label}`}
                    stroke={l.color} strokeWidth={2} dot={{ r: 2 }} connectNulls />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-[11px] text-[#8A785F]">Pas encore de données journalières.</p>
          )}
        </div>
      )}
    </div>
  );
};
