import { useEffect, useState } from 'react';
import { Languages } from 'lucide-react';
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
    </div>
  );
};
