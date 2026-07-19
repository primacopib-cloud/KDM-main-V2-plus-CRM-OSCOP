import { useCallback, useEffect, useState } from 'react';
import {
  Network, CheckCircle2, XCircle, PowerOff, Loader2, RefreshCw, Activity, History, ExternalLink,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const STATUS = {
  OK: { color: '#7BC94E', icon: CheckCircle2, label: 'En ligne' },
  ERROR: { color: '#F87171', icon: XCircle, label: 'En panne' },
  DISABLED: { color: '#9CA3AF', icon: PowerOff, label: 'Désactivé' },
};

const fmtDate = (iso) => (iso
  ? new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
  : '—');

const sinceLabel = (iso) => {
  if (!iso) return null;
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 60) return `${mins} min`;
  if (mins < 1440) return `${Math.round(mins / 60)} h`;
  return `${Math.round(mins / 1440)} j`;
};

const AppCard = ({ app, watch }) => {
  const st = STATUS[app.health?.status] || STATUS.ERROR;
  const Icon = st.icon;
  const success = app.sync?.SUCCESS || 0;
  const errors = app.sync?.ERROR || 0;
  const since = sinceLabel(watch?.since);
  return (
    <div
      className="rounded-2xl p-4 bg-white/[0.05] border border-white/10 hover:border-[#D9B35A]/40 transition-colors"
      data-testid={`eco-health-card-${app.name}`}
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <p className="text-sm font-semibold text-white/90 leading-tight">{app.label.split('—')[0].trim()}</p>
        <span
          className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full shrink-0"
          style={{ color: st.color, background: `${st.color}20`, border: `1px solid ${st.color}45` }}
          data-testid={`eco-health-status-${app.name}`}
        >
          <Icon size={11} /> {st.label}
        </span>
      </div>
      <p className="text-[11px] text-white/40 truncate mb-2">{app.base_url?.replace('https://', '') || 'URL non configurée'}</p>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-white/55">
        {since && app.health?.status !== 'DISABLED' && (
          <span title={watch?.since}>
            {app.health?.status === 'OK' ? 'Stable depuis' : 'En panne depuis'} <b className="text-white/80">{since}</b>
          </span>
        )}
        {watch?.checked_at && <span>Vérifié : <b className="text-white/80">{fmtDate(watch.checked_at)}</b></span>}
        {(success > 0 || errors > 0) && (
          <span>
            Synchros : <b style={{ color: '#7BC94E' }}>{success} ✓</b>
            {errors > 0 && <b className="ml-1.5" style={{ color: '#F87171' }}>{errors} ✗</b>}
          </span>
        )}
      </div>
      {app.health?.error && (
        <p className="text-[11px] mt-2 px-2 py-1 rounded-lg truncate" style={{ color: '#FCA5A5', background: 'rgba(248,113,113,0.1)' }} title={app.health.error}>
          {app.health.error}
        </p>
      )}
    </div>
  );
};

export const EcosystemHealthTab = () => {
  const [data, setData] = useState(null);
  const [watchMap, setWatchMap] = useState({});
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);

  const opts = { headers: getAuthHeaders(), credentials: 'include' };

  const fetchAll = useCallback(async () => {
    try {
      const [eco, watch, hist] = await Promise.all([
        fetch(`${API}/connectors/ecosystem`, opts).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API}/connectors/health-status`, opts).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API}/connectors/health-history?limit=30`, opts).then((r) => (r.ok ? r.json() : null)),
      ]);
      if (eco) setData(eco);
      if (watch) setWatchMap(Object.fromEntries((watch.statuses || []).map((s) => [s.name, s])));
      if (hist) setEvents(hist.events || []);
      setLastRefresh(new Date());
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchAll();
    const timer = setInterval(fetchAll, 30000);
    return () => clearInterval(timer);
  }, [fetchAll]);

  const checkNow = async () => {
    setChecking(true);
    try {
      const r = await fetch(`${API}/connectors/health-check-now`, { method: 'POST', ...opts });
      if (!r.ok) throw new Error('Vérification impossible');
      const d = await r.json();
      toast.success(`${d.checked} application(s) vérifiée(s)${d.alerts_sent ? ` — ${d.alerts_sent} alerte(s) envoyée(s)` : ''}`);
      await fetchAll();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setChecking(false);
    }
  };

  if (loading && !data) {
    return <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" /></div>;
  }

  const apps = data?.apps || [];
  const okCount = apps.filter((a) => a.health?.status === 'OK').length;
  const errCount = apps.filter((a) => a.health?.status === 'ERROR').length;
  const offCount = apps.filter((a) => a.health?.status === 'DISABLED').length;

  return (
    <div className="space-y-5" data-testid="ecosystem-health-tab">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Network className="w-5 h-5 text-[#D9B35A]" /> Santé du Hub O'SCOP
          </h2>
          <p className="text-white/55 text-sm mt-1">
            État de connexion en temps réel de chaque application de l'écosystème · actualisation automatique toutes les 30 s
            {lastRefresh && <span className="text-white/35"> · dernier rafraîchissement : {lastRefresh.toLocaleTimeString('fr-FR')}</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/admin/connecteurs"
            data-testid="eco-health-manage-link"
            className="h-9 inline-flex items-center gap-1.5 px-3 rounded-lg text-xs font-semibold text-white/70 hover:text-white border border-white/15 hover:bg-white/5 transition-colors"
          >
            <ExternalLink size={13} /> Gérer les connecteurs
          </Link>
          <button
            type="button"
            onClick={checkNow}
            disabled={checking}
            data-testid="eco-health-check-now-btn"
            className="h-9 inline-flex items-center gap-1.5 px-4 rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
            style={{ background: '#D4AF37', color: '#1F0A33' }}
          >
            {checking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            Vérifier maintenant
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 max-w-xl" data-testid="eco-health-summary">
        {[
          { label: 'En ligne', value: okCount, color: '#7BC94E' },
          { label: 'En panne', value: errCount, color: '#F87171' },
          { label: 'Désactivées', value: offCount, color: '#9CA3AF' },
        ].map((s) => (
          <div key={s.label} className="rounded-xl px-4 py-3 bg-white/[0.05] border border-white/10">
            <p className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</p>
            <p className="text-[11px] text-white/50 uppercase tracking-wide">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {apps.map((app) => <AppCard key={app.name} app={app} watch={watchMap[app.name]} />)}
      </div>

      <div className="glass-panel-soft rounded-[18px] p-4" data-testid="eco-health-timeline">
        <h3 className="flex items-center gap-2 text-sm font-semibold mb-3 text-[#D9B35A]">
          <History className="w-4 h-4" /> Chronologie des pannes & rétablissements
        </h3>
        {events.length === 0 ? (
          <p className="text-xs text-white/40 flex items-center gap-2">
            <Activity className="w-3.5 h-3.5" /> Aucun incident détecté par la surveillance automatique (contrôle toutes les 10 min).
          </p>
        ) : (
          <div className="space-y-1.5 max-h-72 overflow-y-auto">
            {events.map((ev) => {
              const isDown = ev.to_status === 'ERROR';
              return (
                <div key={ev.id} className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg bg-white/[0.04] text-xs">
                  <span className="flex items-center gap-2 min-w-0">
                    {isDown
                      ? <XCircle className="w-3.5 h-3.5 shrink-0" style={{ color: '#F87171' }} />
                      : <CheckCircle2 className="w-3.5 h-3.5 shrink-0" style={{ color: '#7BC94E' }} />}
                    <span className="text-white/85 font-medium truncate">{(ev.label || ev.name).split('—')[0].trim()}</span>
                    <span className="text-white/50">{isDown ? 'est tombée en panne' : 'a été rétablie'}</span>
                    {ev.error && <span className="text-white/35 truncate" title={ev.error}>· {ev.error}</span>}
                  </span>
                  <span className="text-white/45 shrink-0">{fmtDate(ev.at)}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
