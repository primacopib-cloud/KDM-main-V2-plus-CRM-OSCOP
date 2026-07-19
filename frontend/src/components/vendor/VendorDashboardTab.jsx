import i18n from '@/i18n';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { MySpotsWidget } from './MySpotsWidget';
import { getStatusBadge } from './vendorConstants';

export const VendorDashboardTab = ({ dashboard, vendorId, formatCurrency }) => (
  <div className="space-y-6" data-testid="vendor-dashboard-tab">
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{i18n.t('adm.produits_actifs')}</CardDescription>
          <CardTitle className="text-3xl text-purple-600">{dashboard?.products?.approved || 0}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">{i18n.t('adm.sur_soumis', { count: dashboard?.products?.total || 0 })}</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{i18n.t('adm.en_attente')}</CardDescription>
          <CardTitle className="text-3xl text-amber-600">{dashboard?.products?.pending || 0}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">{i18n.t('adm.produits_a_valider')}</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{i18n.t('adm.chiffre_d_affaires')}</CardDescription>
          <CardTitle className="text-3xl text-emerald-600">{formatCurrency(dashboard?.sales?.total_revenue || 0)}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">{i18n.t('adm.total_ht')}</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{i18n.t('adm.commandes')}</CardDescription>
          <CardTitle className="text-3xl text-blue-600">{dashboard?.sales?.order_count || 0}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">{i18n.t('adm.total')}</p>
        </CardContent>
      </Card>
    </div>

    <MySpotsWidget vendorId={vendorId} />

    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{i18n.t('adm.commandes_recentes')}</CardTitle>
      </CardHeader>
      <CardContent>
        {dashboard?.recent_orders?.length > 0 ? (
          <div className="space-y-2">
            {dashboard.recent_orders.map((order, idx) => (
              <div key={order.id || order.order_id || `vendor-order-${idx}`} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium">{order.id}</p>
                  <p className="text-sm text-gray-500">{order.created_at?.split('T')[0]}</p>
                </div>
                <div className="text-right">
                  <p className="font-bold">{formatCurrency(order.total_ht)}</p>
                  {getStatusBadge(order.status)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">{i18n.t('adm.aucune_commande_recente')}</p>
        )}
      </CardContent>
    </Card>
  </div>
);
