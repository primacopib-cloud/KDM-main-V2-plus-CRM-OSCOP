import { useEffect, useState } from 'react';
import { TrendingDown } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const STEPS = [
  { key: 'started', label: 'Adhésions initiées', color: '#9CA3AF' },
  { key: 'paid', label: 'Paiement confirmé', color: '#60A5FA' },
  { key: 'signed', label: 'Convention signée', color: '#E9CF8E' },
  { key: 'activated', label: 'Espace activé', color: '#7BC94E' },
];

const PERIODS = [
  { days: 30, label: '30 jours' },
  { days: 90, label: '90 jours' },
  { days: 0, label: 'Tout' },
];

export const AdhesionFunnel = () => {
  const [data, setData] = useState(null);
  const [days, setDays] = useState(0);

  useEffect(() => {
    fetch(`${API}/vendor-onboarding/admin/funnel?days=${days}`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => {});
  }, [days]);

  if (!data) return null;
  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mb-4" data-testid="adhesion-funnel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#D9B35A] flex items-center gap-2">
          <TrendingDown className="w-4 h-4" /> Entonnoir de conversion des adhésions
        </h3>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button key={p.days} type="button" onClick={() => setDays(p.days)}
              data-testid={`funnel-period-${p.days}`}
              className={`px-2.5 py-1 rounded-lg text-[10.5px] font-bold transition-colors ${
                days === p.days ? 'bg-[#D9B35A] text-[#1F0A33]' : 'bg-white/10 text-white/55 hover:text-white/80'
              }`}>
              {p.label}
            </button>
          ))}
        </div>
      </div>
      {!data.started ? (
        <p className="text-xs text-white/45">Aucune adhésion sur cette période.</p>
      ) : (
        <>
          <div className="space-y-2">
            {STEPS.map((s, i) => {
              const val = data[s.key] || 0;
              const prev = i === 0 ? val : data[STEPS[i - 1].key] || 0;
              const widthPct = Math.max((val / data.started) * 100, 4);
              const convPct = i === 0 ? 100 : prev ? Math.round((val / prev) * 100) : 0;
              return (
                <div key={s.key} className="flex items-center gap-3" data-testid={`funnel-step-${s.key}`}>
                  <span className="w-40 shrink-0 text-[11px] text-white/60">{s.label}</span>
                  <div className="flex-1 h-6 rounded-lg bg-white/[0.05] overflow-hidden">
                    <div className="h-full rounded-lg flex items-center px-2 transition-all"
                      style={{ width: `${widthPct}%`, background: `${s.color}33`, borderLeft: `3px solid ${s.color}` }}>
                      <span className="text-[11px] font-bold" style={{ color: s.color }}>{val}</span>
                    </div>
                  </div>
                  <span className="w-14 shrink-0 text-right text-[10.5px] text-white/45">
                    {i === 0 ? '100 %' : `${convPct} %`}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="text-[10px] text-white/35 mt-2">
            Taux global initiées → activées : {Math.round(((data.activated || 0) / data.started) * 100)} %
          </p>
        </>
      )}
    </div>
  );
};
