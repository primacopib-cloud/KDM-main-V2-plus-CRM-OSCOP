import { useState, useEffect } from 'react';
import i18n from '@/i18n';
import { TrendingUp, TrendingDown, Minus, Star } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Stars } from '../catalog/ProductReviewsModal';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Carte « Avis clients » du dashboard vendeur : note moyenne, tendance 30j, détail par produit
export const VendorReviewsCard = ({ vendorId }) => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (!vendorId) return;
    fetch(`${API_URL}/api/v2/catalog/vendors/${vendorId}/reviews-stats`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then(setStats)
      .catch(() => {});
  }, [vendorId]);

  if (!stats) return null;
  const TrendIcon = stats.trend > 0 ? TrendingUp : stats.trend < 0 ? TrendingDown : Minus;
  const trendColor = stats.trend > 0 ? 'text-emerald-600' : stats.trend < 0 ? 'text-red-500' : 'text-gray-400';

  return (
    <Card data-testid="vendor-reviews-card">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Star className="w-5 h-5 text-[#D9B35A]" />
          {i18n.t('adm.avis_clients', 'Avis clients')}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {stats.total_reviews === 0 ? (
          <p className="text-gray-500 text-center py-6" data-testid="vendor-reviews-empty">
            {i18n.t('adm.aucun_avis_produits', 'Aucun avis sur vos produits pour le moment.')}
          </p>
        ) : (
          <div className="space-y-5">
            {/* Vue globale */}
            <div className="flex flex-wrap items-center gap-6">
              <div className="flex items-center gap-3" data-testid="vendor-reviews-overall">
                <span className="text-4xl font-bold text-[#b8923e]">{stats.overall_avg}</span>
                <div>
                  <Stars value={stats.overall_avg} size={16} />
                  <p className="text-xs text-gray-500 mt-0.5">
                    {stats.total_reviews} {i18n.t('adm.avis_recus', 'avis reçus')}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-sm" data-testid="vendor-reviews-trend">
                <TrendIcon className={`w-4 h-4 ${trendColor}`} />
                <span className={trendColor}>
                  {stats.trend !== null
                    ? `${stats.trend > 0 ? '+' : ''}${stats.trend} / 30 ${i18n.t('adm.jours', 'jours')}`
                    : `${stats.recent_count} ${i18n.t('adm.avis_30j', 'avis sur 30 jours')}`}
                </span>
              </div>
            </div>

            {/* Par produit */}
            <div className="space-y-1.5" data-testid="vendor-reviews-products">
              {stats.products.map((p) => (
                <div key={p.id} className="flex items-center justify-between gap-3 p-2 bg-gray-50 rounded-lg text-sm">
                  <span className="truncate font-medium">{p.name}</span>
                  <span className="flex items-center gap-2 shrink-0">
                    <Stars value={p.rating_avg} size={12} />
                    <span className="font-semibold text-[#b8923e]">{p.rating_avg}</span>
                    <span className="text-gray-400 text-xs">({p.rating_count})</span>
                  </span>
                </div>
              ))}
            </div>

            {/* Derniers avis */}
            {stats.latest_reviews.length > 0 && (
              <div className="space-y-2" data-testid="vendor-reviews-latest">
                <p className="text-xs font-semibold text-gray-500 uppercase">{i18n.t('adm.derniers_avis', 'Derniers avis')}</p>
                {stats.latest_reviews.slice(0, 3).map((r) => (
                  <div key={r.id} className="p-2 border border-gray-100 rounded-lg text-sm">
                    <div className="flex items-center gap-2">
                      <Stars value={r.rating} size={11} />
                      <span className="font-medium">{r.user_name}</span>
                      <span className="text-xs text-gray-400">· {r.product_name}</span>
                    </div>
                    {r.comment && <p className="text-gray-600 text-xs mt-1">{r.comment}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
