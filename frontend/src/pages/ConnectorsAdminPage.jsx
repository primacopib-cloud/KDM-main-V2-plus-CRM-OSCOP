import i18n from '@/i18n';
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft, RefreshCw, Send, Clapperboard } from 'lucide-react';
import NavBar from '../components/NavBar';
import { ConnectorCard } from '../components/connectors/ConnectorCard';
import { ConnectorSyncTable } from '../components/connectors/ConnectorSyncTable';
import { IaboisProjectsPanel } from '../components/connectors/IaboisProjectsPanel';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ConnectorsAdminPage() {
  const navigate = useNavigate();
  const [connectors, setConnectors] = useState([]);
  const [healths, setHealths] = useState({});
  const [checking, setChecking] = useState('');
  const [events, setEvents] = useState([]);
  const [counts, setCounts] = useState({});
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [retryingId, setRetryingId] = useState(null);
  const [pushOrderId, setPushOrderId] = useState('');
  const [pushing, setPushing] = useState(false);
  const [broadcasting, setBroadcasting] = useState(false);

  const fetchConnectors = useCallback(async () => {
    const r = await fetch(`${API}/connectors`, { credentials: 'include' });
    if (r.ok) setConnectors((await r.json()).connectors || []);
  }, []);

  const fetchEvents = useCallback(async () => {
    const params = new URLSearchParams({ limit: '50' });
    if (statusFilter) params.set('status', statusFilter);
    const r = await fetch(`${API}/connectors/sync-events?${params}`, { credentials: 'include' });
    if (r.ok) {
      const data = await r.json();
      setEvents(data.events || []);
      setCounts(data.counts || {});
    }
  }, [statusFilter]);

  const refresh = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchConnectors(), fetchEvents()]);
    setLoading(false);
  }, [fetchConnectors, fetchEvents]);

  useEffect(() => { refresh(); }, [refresh]);

  const checkHealth = async (name) => {
    setChecking(name);
    try {
      const r = await fetch(`${API}/connectors/${name}/health`, { credentials: 'include' });
      const data = await r.json();
      setHealths((h) => ({ ...h, [name]: data }));
      toast[data.status === 'OK' ? 'success' : 'error'](`${name}: ${data.status}`);
    } finally {
      setChecking('');
    }
  };

  const retryEvent = async (eventId) => {
    setRetryingId(eventId);
    try {
      const r = await fetch(`${API}/connectors/sync-events/${eventId}/retry`, { method: 'POST', credentials: 'include' });
      const data = await r.json();
      toast[data.status === 'SUCCESS' ? 'success' : 'error'](data.status === 'SUCCESS' ? i18n.t('adm.conn_retry_ok') : (data.error || 'ERROR'));
      await fetchEvents();
    } finally {
      setRetryingId(null);
    }
  };

  const pushOrder = async () => {
    if (!pushOrderId.trim()) return;
    setPushing(true);
    try {
      const r = await fetch(`${API}/connectors/push/order/${encodeURIComponent(pushOrderId.trim())}`, {
        method: 'POST', credentials: 'include',
      });
      const data = await r.json();
      const ok = data.ged?.status === 'SUCCESS' && data.finance?.status === 'SUCCESS';
      toast[ok ? 'success' : 'error'](
        `GED: ${data.ged?.status || '?'} · Finance: ${data.finance?.status || '?'}`
      );
      await fetchEvents();
    } finally {
      setPushing(false);
    }
  };

  const broadcastSpots = async () => {
    setBroadcasting(true);
    try {
      const r = await fetch(`${API}/connectors/broadcast-spots`, { method: 'POST', credentials: 'include' });
      const data = await r.json();
      if (data.status === 'EMPTY') { toast.info('Aucun spot vidéo à diffuser'); return; }
      const ok = (data.results || []).filter((x) => x.status === 'SUCCESS').length;
      const err = (data.results || []).filter((x) => x.status === 'ERROR').length;
      toast[err === 0 ? 'success' : 'warning'](
        `${data.spots} spot(s) diffusé(s) — ${ok} app(s) OK · ${err} en erreur`
      );
      await fetchEvents();
    } finally {
      setBroadcasting(false);
    }
  };

  return (
    <div className="min-h-screen" data-testid="connectors-admin-page">
      <NavBar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <button
              type="button"
              onClick={() => navigate('/admin')}
              data-testid="connectors-back-btn"
              className="inline-flex items-center gap-2 text-sm mb-3 opacity-70 hover:opacity-100 transition-opacity"
            >
              <ArrowLeft size={14} /> Admin
            </button>
            <h1 className="font-display text-3xl sm:text-4xl" style={{ color: '#F7F2E9' }}>
              {i18n.t('adm.conn_title')}
            </h1>
            <p className="text-sm opacity-70 mt-2">{i18n.t('adm.conn_subtitle')}</p>
          </div>
          <button
            type="button"
            onClick={refresh}
            data-testid="connectors-refresh-btn"
            className="btn-ghost h-10 px-4 rounded-lg inline-flex items-center gap-2"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> {i18n.t('adm.conn_refresh')}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {connectors.map((c) => (
            <ConnectorCard
              key={c.name}
              connector={c}
              health={healths[c.name]}
              checking={checking === c.name}
              onCheck={checkHealth}
            />
          ))}
        </div>

        {/* Demandes de devis IA Bois */}
        <IaboisProjectsPanel />

        {/* Push manuel */}
        <div className="glass-panel rounded-2xl p-5 mb-8" data-testid="connectors-manual-push">
          <h2 className="font-display text-lg mb-3" style={{ color: '#F7F2E9' }}>
            {i18n.t('adm.conn_manual_push')}
          </h2>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              value={pushOrderId}
              onChange={(e) => setPushOrderId(e.target.value)}
              placeholder={i18n.t('adm.conn_order_placeholder')}
              data-testid="connectors-push-order-input"
              className="flex-1 h-10 px-4 rounded-lg bg-white/5 border border-white/10 text-sm"
            />
            <button
              type="button"
              onClick={pushOrder}
              disabled={pushing || !pushOrderId.trim()}
              data-testid="connectors-push-order-btn"
              className="btn-primary h-10 px-5 rounded-lg inline-flex items-center gap-2 text-sm"
            >
              <Send size={14} /> {i18n.t('adm.conn_push_order')}
            </button>
            <button
              type="button"
              onClick={broadcastSpots}
              disabled={broadcasting}
              data-testid="connectors-broadcast-spots-btn"
              className="btn-ghost h-10 px-5 rounded-lg inline-flex items-center gap-2 text-sm"
              style={{ border: '1px solid rgba(217,179,90,0.4)', color: '#B8860B' }}
            >
              <Clapperboard size={14} /> {broadcasting ? 'Diffusion…' : 'Diffuser les spots vidéo'}
            </button>
          </div>
        </div>

        {/* Filtres + compteurs */}
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <h2 className="font-display text-lg mr-auto" style={{ color: '#F7F2E9' }}>
            {i18n.t('adm.conn_sync_queue')}
          </h2>
          <span className="text-xs opacity-60" data-testid="connectors-counts">
            {i18n.t('adm.conn_counts', { success: counts.SUCCESS || 0, error: counts.ERROR || 0 })}
          </span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            data-testid="connectors-status-filter"
            className="h-9 px-3 rounded-lg bg-white/5 border border-white/10 text-sm"
          >
            <option value="">{i18n.t('adm.conn_all_status')}</option>
            <option value="SUCCESS">SUCCESS</option>
            <option value="ERROR">ERROR</option>
            <option value="PENDING">PENDING</option>
          </select>
        </div>

        <ConnectorSyncTable events={events} retryingId={retryingId} onRetry={retryEvent} />
      </div>
    </div>
  );
}
