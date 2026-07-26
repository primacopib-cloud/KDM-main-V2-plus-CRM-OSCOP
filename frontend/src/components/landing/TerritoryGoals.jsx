import { useState, useEffect } from 'react';
import { Users } from 'lucide-react';
import i18n from '@/i18n';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const LABELS = { GUADELOUPE: 'Guadeloupe', MARTINIQUE: 'Martinique', GUYANE: 'Guyane', REUNION: 'Réunion', MAYOTTE: 'Mayotte' };

// Barres de progression « X adhérents sur l'objectif » par territoire
export const TerritoryGoals = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/v2/catalog/zones-stats`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setStats)
      .catch(() => {});
  }, []);

  if (!stats) return null;

  return (
    <div className="glass-panel rounded-2xl p-5" data-testid="territory-goals">
      <p className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: '#F7F2E9' }}>
        <Users className="w-4 h-4" style={{ color: '#D9B35A' }} />
        {i18n.t('landing.goals_title', 'Objectif adhérents par territoire')}
      </p>
      <div className="space-y-3">
        {Object.keys(LABELS).map((code) => {
          const s = stats[code] || { members: 0, target: 20 };
          const target = s.target || 20;
          const pct = Math.min(100, Math.round((s.members / target) * 100));
          return (
            <div key={code} data-testid={`territory-goal-${code}`}>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="font-medium" style={{ color: 'rgba(247,242,233,0.85)' }}>{LABELS[code]}</span>
                <span style={{ color: pct >= 100 ? '#6FA82E' : '#D9B35A' }}>
                  {s.members} / {target} {i18n.t('landing.map_adherents', 'adhérents')}{pct >= 100 ? ' ✓' : ''}
                </span>
              </div>
              <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.07)' }}>
                <div className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${Math.max(pct, 2)}%`,
                    background: pct >= 100
                      ? 'linear-gradient(90deg, #6FA82E, #8BC34A)'
                      : 'linear-gradient(90deg, #b8933e, #D9B35A)',
                  }} />
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-[11px] mt-4" style={{ color: 'rgba(247,242,233,0.45)' }}>
        {i18n.t('landing.goals_cta', 'Chaque nouvelle adhésion renforce le pouvoir de négociation de votre territoire.')}
      </p>
    </div>
  );
};
