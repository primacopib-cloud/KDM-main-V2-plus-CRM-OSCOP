import i18n from '@/i18n';
import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { BellRing, RefreshCw, Package, Tag, ArrowUpRight, Heart, Ship } from 'lucide-react';
import NavBar from '../components/NavBar';
import { Switch } from '../components/ui/switch';
import { INCOTERMS } from '../components/vendor/vendorConstants';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(i18n.language, {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch (_e) {
    return iso;
  }
};

const ALERT_ICON = {
  favorite_restock: { icon: Package, color: '#6FA82E' },
  favorite_promo: { icon: Tag, color: '#D9B35A' },
  product_incoterm_match: { icon: Ship, color: '#3498DB' },
};

export default function FavoriteAlertsPage() {
  const [products, setProducts] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [incotermCodes, setIncotermCodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [togglingId, setTogglingId] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [r, ri] = await Promise.all([
        fetch(`${API}/user-prefs/favorites/alerts-center`, { credentials: 'include' }),
        fetch(`${API}/v2/catalog/incoterm-alerts`, { credentials: 'include' }),
      ]);
      if (r.ok) {
        const data = await r.json();
        setProducts(data.products || []);
        setAlerts(data.alerts || []);
      }
      if (ri.ok) {
        setIncotermCodes((await ri.json()).codes || []);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const toggleIncoterm = async (code) => {
    const next = incotermCodes.includes(code)
      ? incotermCodes.filter((c) => c !== code)
      : [...incotermCodes, code];
    try {
      const r = await fetch(`${API}/v2/catalog/incoterm-alerts`, {
        method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ codes: next }),
      });
      if (!r.ok) throw new Error();
      setIncotermCodes(next);
      toast.success(next.includes(code)
        ? i18n.t('fav_alerts.incoterm_on', `Alerte ${code} activée`)
        : i18n.t('fav_alerts.incoterm_off', `Alerte ${code} désactivée`));
    } catch {
      toast.error(i18n.t('fav_alerts.incoterm_error', "Impossible de mettre à jour l'alerte"));
    }
  };

  const toggleAlerts = async (productId, enabled) => {
    setTogglingId(productId);
    try {
      const r = await fetch(`${API}/user-prefs/favorites/${productId}/alerts`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      if (r.ok) {
        setProducts((prev) => prev.map((p) => (p.product_id === productId ? { ...p, alerts_enabled: enabled } : p)));
        toast.success(enabled ? i18n.t('fav_alerts.toast_on') : i18n.t('fav_alerts.toast_off'));
      }
    } finally {
      setTogglingId(null);
    }
  };

  return (
    <div className="min-h-screen" data-testid="favorite-alerts-page">
      <NavBar />
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="font-display text-3xl sm:text-4xl flex items-center gap-3" style={{ color: '#F7F2E9' }}>
              <BellRing size={30} style={{ color: 'var(--kdm-or-metallise)' }} />
              {i18n.t('fav_alerts.title')}
            </h1>
            <p className="text-sm opacity-70 mt-2">{i18n.t('fav_alerts.subtitle')}</p>
          </div>
          <button
            type="button"
            onClick={fetchData}
            data-testid="fav-alerts-refresh-btn"
            className="btn-ghost h-10 px-4 rounded-lg inline-flex items-center gap-2"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> {i18n.t('fav_alerts.refresh')}
          </button>
        </div>

        {/* Incoterms suivis */}
        <h2 className="font-display text-lg mb-3" style={{ color: '#F7F2E9' }}>
          <Ship size={16} className="inline mr-2" style={{ color: '#3498DB' }} />
          {i18n.t('fav_alerts.incoterms_title', 'Incoterms suivis')}
        </h2>
        <div className="glass-panel rounded-2xl p-5 mb-8" data-testid="incoterm-prefs-section">
          <p className="text-sm opacity-70 mb-4">
            {i18n.t('fav_alerts.incoterms_desc', "Soyez prévenu (notification + email) dès qu'un nouveau produit livrable avec ces incoterms arrive au catalogue.")}
          </p>
          <div className="flex flex-wrap gap-2">
            {INCOTERMS.map((inc) => {
              const active = incotermCodes.includes(inc.code);
              return (
                <button
                  key={inc.code}
                  type="button"
                  onClick={() => toggleIncoterm(inc.code)}
                  title={inc.label}
                  data-testid={`incoterm-pref-${inc.code}`}
                  className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-sm font-semibold border transition-all ${
                    active
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                      : 'bg-white/[0.04] text-white/60 hover:text-white border-white/[0.08]'
                  }`}
                >
                  <BellRing size={13} className={active ? '' : 'opacity-40'} />
                  {inc.code}
                </button>
              );
            })}
          </div>
        </div>

        {/* Préférences par produit */}
        <h2 className="font-display text-lg mb-3" style={{ color: '#F7F2E9' }}>
          {i18n.t('fav_alerts.prefs_title')}
        </h2>
        {products.length === 0 && !loading ? (
          <div className="glass-panel rounded-2xl p-8 text-center opacity-70 mb-8" data-testid="fav-alerts-empty">
            <Heart className="mx-auto mb-3 opacity-50" size={28} />
            <p>{i18n.t('fav_alerts.no_favorites')}</p>
            <Link to="/catalogue" className="inline-flex items-center gap-1.5 mt-3 text-sm font-medium" style={{ color: 'var(--kdm-or-metallise)' }}>
              {i18n.t('fav_alerts.browse_catalog')} <ArrowUpRight size={14} />
            </Link>
          </div>
        ) : (
          <div className="glass-panel rounded-2xl divide-y divide-white/5 mb-8" data-testid="fav-alerts-products">
            {products.map((p) => (
              <div key={p.product_id} className="flex items-center justify-between gap-4 p-4" data-testid={`fav-alert-row-${p.product_id}`}>
                <div className="min-w-0">
                  <p className="font-medium truncate">{p.product_name || p.product_id}</p>
                  <p className="text-xs opacity-50">{p.product_sku || '—'}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-xs opacity-60 hidden sm:block">
                    {p.alerts_enabled ? i18n.t('fav_alerts.alerts_on') : i18n.t('fav_alerts.alerts_off')}
                  </span>
                  <Switch
                    checked={p.alerts_enabled}
                    disabled={togglingId === p.product_id}
                    onCheckedChange={(checked) => toggleAlerts(p.product_id, checked)}
                    data-testid={`fav-alert-switch-${p.product_id}`}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Historique des alertes */}
        <h2 className="font-display text-lg mb-3" style={{ color: '#F7F2E9' }}>
          {i18n.t('fav_alerts.history_title')}
        </h2>
        {alerts.length === 0 ? (
          <div className="glass-panel rounded-2xl p-8 text-center opacity-60" data-testid="fav-alerts-history-empty">
            {i18n.t('fav_alerts.no_alerts')}
          </div>
        ) : (
          <div className="glass-panel rounded-2xl divide-y divide-white/5" data-testid="fav-alerts-history">
            {alerts.map((a) => {
              const meta = ALERT_ICON[a.type] || ALERT_ICON.favorite_restock;
              const Icon = meta.icon;
              return (
                <div key={a.id} className="flex items-start gap-3 p-4" data-testid={`fav-alert-item-${a.id}`}>
                  <span className="mt-0.5 p-2 rounded-full shrink-0" style={{ background: `${meta.color}18`, color: meta.color }}>
                    <Icon size={16} />
                  </span>
                  <div className="min-w-0">
                    <p className="font-medium text-sm">{a.title}</p>
                    <p className="text-sm opacity-75">{a.message}</p>
                    <p className="text-xs opacity-45 mt-1">{fmtDate(a.created_at)}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
