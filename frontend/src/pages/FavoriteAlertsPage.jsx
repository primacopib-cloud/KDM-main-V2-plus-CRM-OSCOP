import i18n from '@/i18n';
import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { BellRing, RefreshCw, Package, Tag, ArrowUpRight, Heart } from 'lucide-react';
import NavBar from '../components/NavBar';
import { Switch } from '../components/ui/switch';

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
};

export default function FavoriteAlertsPage() {
  const [products, setProducts] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [togglingId, setTogglingId] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/user-prefs/favorites/alerts-center`, { credentials: 'include' });
      if (r.ok) {
        const data = await r.json();
        setProducts(data.products || []);
        setAlerts(data.alerts || []);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

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
            <h1 className="font-display text-3xl sm:text-4xl flex items-center gap-3" style={{ color: 'var(--kdm-bleu-logistique)' }}>
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

        {/* Préférences par produit */}
        <h2 className="font-display text-lg mb-3" style={{ color: 'var(--kdm-bleu-logistique)' }}>
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
        <h2 className="font-display text-lg mb-3" style={{ color: 'var(--kdm-bleu-logistique)' }}>
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
