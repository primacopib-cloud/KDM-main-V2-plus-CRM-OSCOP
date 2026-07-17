import i18n from '@/i18n';
import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Network, CheckCircle2, XCircle, PowerOff, Loader2, ArrowUpRight } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS = {
  OK: { color: '#6FA82E', icon: CheckCircle2, label: 'OK' },
  ERROR: { color: '#E64432', icon: XCircle, label: 'ERROR' },
  DISABLED: { color: '#9CA3AF', icon: PowerOff, label: 'OFF' },
};

export const EcosystemPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchEcosystem = useCallback(async () => {
    try {
      const r = await fetch(`${API}/connectors/ecosystem`, { credentials: 'include' });
      if (r.ok) setData(await r.json());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEcosystem();
    const timer = setInterval(fetchEcosystem, 60000);
    return () => clearInterval(timer);
  }, [fetchEcosystem]);

  return (
    <div className="glass-panel-soft rounded-[18px] p-5" data-testid="ecosystem-panel">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display text-lg flex items-center gap-2 text-[#1F2A3A]">
          <Network className="w-5 h-5 text-[#D9B35A]" />
          {i18n.t('adm.eco_title')}
          {data && (
            <span className="text-xs font-normal opacity-60" data-testid="ecosystem-summary">
              {i18n.t('adm.eco_summary', { ok: data.ok, total: data.total })}
            </span>
          )}
        </h3>
        <Link
          to="/admin/connecteurs"
          data-testid="ecosystem-manage-link"
          className="text-xs font-medium inline-flex items-center gap-1 text-[#B8860B] hover:underline"
        >
          {i18n.t('adm.eco_manage')} <ArrowUpRight size={12} />
        </Link>
      </div>

      {loading && !data ? (
        <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-[#D9B35A]" /></div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {(data?.apps || []).map((app) => {
            const st = STATUS[app.health?.status] || STATUS.ERROR;
            const Icon = st.icon;
            const success = app.sync?.SUCCESS || 0;
            const errors = app.sync?.ERROR || 0;
            return (
              <div
                key={app.name}
                className="rounded-xl p-3 bg-white/50 border border-black/5"
                data-testid={`eco-app-${app.name}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-[#1F2A3A] leading-tight">{app.label.split('—')[0].trim()}</p>
                  <span
                    className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full shrink-0"
                    style={{ color: st.color, background: `${st.color}18` }}
                    data-testid={`eco-status-${app.name}`}
                  >
                    <Icon size={10} /> {st.label}
                  </span>
                </div>
                <p className="text-[11px] opacity-50 mt-1 truncate">{app.base_url?.replace('https://', '')}</p>
                {(success > 0 || errors > 0) && (
                  <p className="text-[11px] mt-1.5">
                    <span className="text-[#6FA82E]">{success} ✓</span>
                    {errors > 0 && <span className="text-[#E64432] ml-2">{errors} ✗</span>}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
