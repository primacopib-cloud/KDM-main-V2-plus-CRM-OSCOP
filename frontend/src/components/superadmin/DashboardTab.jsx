import i18n from '@/i18n';
import { Link } from 'react-router-dom';
import {
  Users, Package, ShoppingCart, Wallet, FileSignature, TrendingUp,
  AlertTriangle, CheckCircle2, Clock, Building2, ChevronRight, Leaf,
} from 'lucide-react';
import { StatCard, AlertCard, ActivityItem, KPISection, formatCurrency } from './widgets';

export const DashboardTab = ({ kpis, alerts, activities, period, setActiveTab }) => (
  <>
    {/* Top Stats Row */}
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
      <StatCard
        title={i18n.t('adm.chiffre_d_affaires')}
        value={formatCurrency(kpis?.sales?.total_revenue)}
        icon={TrendingUp}
        color="#10B981"
        trend="up"
        trendValue="+12%"
      />
      <StatCard
        title={i18n.t('adm.commandes')}
        value={kpis?.sales?.total_orders || 0}
        subtitle={i18n.t('adm.panier_moyen_sub', { value: formatCurrency(kpis?.sales?.average_basket) })}
        icon={ShoppingCart}
        color="#D9B35A"
      />
      <StatCard
        title={i18n.t('adm.utilisateurs')}
        value={kpis?.users?.total || 0}
        subtitle={i18n.t('adm.actifs_count', { count: kpis?.users?.active || 0 })}
        icon={Users}
        color="#3B82F6"
      />
      <StatCard
        title={i18n.t('adm.organisations')}
        value={kpis?.users?.organizations?.total || 0}
        subtitle={i18n.t('adm.en_attente_count', { count: kpis?.users?.organizations?.pending || 0 })}
        icon={Building2}
        color="#8B5CF6"
      />
      <StatCard
        title={i18n.t('adm.total_produits')}
        value={kpis?.products?.total || 0}
        subtitle={i18n.t('adm.stock_faible_count', { count: kpis?.products?.low_stock || 0 })}
        icon={Package}
        color="#F59E0B"
      />
      <StatCard
        title={i18n.t('adm.credits_wallet')}
        value={formatCurrency(kpis?.wallet?.current_total_balance)}
        subtitle={i18n.t('adm.vendus_sub', { value: formatCurrency(kpis?.wallet?.total_credits_sold) })}
        icon={Wallet}
        color="#D4AF37"
      />
    </div>

    <div className="grid lg:grid-cols-3 gap-6">
      {/* Left Column - KPIs */}
      <div className="lg:col-span-2 space-y-6">
        {/* Sales KPIs */}
        <KPISection title={i18n.t('adm.ventes_commandes')} icon={ShoppingCart} color="#D9B35A">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 rounded-xl bg-[#F8F1E1]">
              <div className="text-xl font-bold text-[#D9B35A]">{formatCurrency(kpis?.sales?.total_revenue)}</div>
              <div className="text-xs text-[#8A785F]">{i18n.t('adm.ca_total')}</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-[#F8F1E1]">
              <div className="text-xl font-bold text-[#4C2A6E]">{kpis?.sales?.total_orders}</div>
              <div className="text-xs text-[#8A785F]">{i18n.t('adm.commandes')}</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-[#F8F1E1]">
              <div className="text-xl font-bold text-[#4C2A6E]">{formatCurrency(kpis?.sales?.average_basket)}</div>
              <div className="text-xs text-[#8A785F]">{i18n.t('adm.panier_moyen')}</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-[#F8F1E1]">
              <div className="text-xl font-bold text-[#4C2A6E]">{kpis?.sales?.installment_orders || 0}</div>
              <div className="text-xs text-[#8A785F]">{i18n.t('adm.paiements_4')}</div>
            </div>
          </div>

          {kpis?.sales?.orders_by_status && Object.keys(kpis.sales.orders_by_status).length > 0 && (
            <div className="mt-4 pt-4 border-t border-[#EDE1C6]">
              <p className="text-xs text-[#8A785F] mb-2">{i18n.t('adm.par_statut')}</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(kpis.sales.orders_by_status).map(([status, count]) => (
                  <span key={status} className="px-2 py-1 rounded-full bg-[#F3E9D2] text-xs text-[#5C4B36]">
                    {status}: <span className="font-semibold">{count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </KPISection>

        {/* Users & Organizations */}
        <KPISection title={i18n.t('adm.utilisateurs_organisations')} icon={Users} color="#3B82F6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 rounded-xl bg-[#F8F1E1]">
              <div className="text-xl font-bold text-[#3B82F6]">{kpis?.users?.total}</div>
              <div className="text-xs text-[#8A785F]">{i18n.t('adm.total_utilisateurs')}</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-[#F8F1E1]">
              <div className="text-xl font-bold text-green-700">{kpis?.users?.active}</div>
              <div className="text-xs text-[#8A785F]">{i18n.t('adm.actifs')}</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-[#F8F1E1]">
              <div className="text-xl font-bold text-[#4C2A6E]">{kpis?.users?.new_period}</div>
              <div className="text-xs text-[#8A785F]">{i18n.t('adm.nouveaux_period', { period })}</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-[#F8F1E1]">
              <div className="text-xl font-bold text-[#8B5CF6]">{kpis?.users?.organizations?.approved}</div>
              <div className="text-xs text-[#8A785F]">{i18n.t('adm.orgs_approuvees')}</div>
            </div>
          </div>

          {kpis?.users?.by_role && Object.keys(kpis.users.by_role).length > 0 && (
            <div className="mt-4 pt-4 border-t border-[#EDE1C6]">
              <p className="text-xs text-[#8A785F] mb-2">{i18n.t('adm.par_role')}</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(kpis.users.by_role).map(([role, count]) => (
                  <span key={role} className="px-2 py-1 rounded-full bg-[#F3E9D2] text-xs text-[#5C4B36]">
                    {role}: <span className="font-semibold">{count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </KPISection>

        {/* Products */}
        <KPISection title={i18n.t('adm.catalogue_produits_2')} icon={Package} color="#F59E0B">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 rounded-xl bg-[#F8F1E1]">
              <div className="text-xl font-bold text-[#F59E0B]">{kpis?.products?.total}</div>
              <div className="text-xs text-[#8A785F]">{i18n.t('adm.total_produits')}</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-[#F8F1E1]">
              <div className="text-xl font-bold text-green-700">{kpis?.products?.active}</div>
              <div className="text-xs text-[#8A785F]">{i18n.t('adm.actifs')}</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-[#F8F1E1]">
              <div className="text-xl font-bold text-amber-600">{kpis?.products?.low_stock}</div>
              <div className="text-xs text-[#8A785F]">{i18n.t('adm.stock_faible')}</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-[#F8F1E1]">
              <div className="text-xl font-bold text-red-600">{kpis?.products?.out_of_stock}</div>
              <div className="text-xs text-[#8A785F]">{i18n.t('adm.rupture')}</div>
            </div>
          </div>
        </KPISection>

        {/* Wallet & Signatures */}
        <div className="grid md:grid-cols-2 gap-6">
          <KPISection title={i18n.t('adm.wallet_credits')} icon={Wallet} color="#D4AF37">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-[#7A6850]">{i18n.t('adm.solde_total')}</span>
                <span className="font-bold text-[#D4AF37]">{formatCurrency(kpis?.wallet?.current_total_balance)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-[#7A6850]">{i18n.t('adm.credits_vendus')}</span>
                <span className="font-semibold text-[#3D2E1E]">{formatCurrency(kpis?.wallet?.total_credits_sold)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-[#7A6850]">{i18n.t('adm.credits_consommes')}</span>
                <span className="font-semibold text-[#3D2E1E]">{formatCurrency(kpis?.wallet?.total_credits_consumed)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-[#7A6850]">{i18n.t('adm.transactions')}</span>
                <span className="font-semibold text-[#3D2E1E]">{kpis?.wallet?.credits_transactions + kpis?.wallet?.consumption_transactions}</span>
              </div>
            </div>
          </KPISection>

          <KPISection title={i18n.t('adm.signatures_eidas')} icon={FileSignature} color="#8B5CF6">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-[#7A6850]">{i18n.t('adm.total_signatures')}</span>
                <span className="font-bold text-[#8B5CF6]">{kpis?.signatures?.total}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-[#7A6850]">{i18n.t('adm.signees')}</span>
                <span className="font-semibold text-green-700">{kpis?.signatures?.signed}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-[#7A6850]">{i18n.t('adm.en_attente')}</span>
                <span className="font-semibold text-amber-600">{kpis?.signatures?.pending}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-[#7A6850]">{i18n.t('adm.taux_de_succes')}</span>
                <span className="font-semibold text-[#3D2E1E]">{kpis?.signatures?.success_rate}%</span>
              </div>
            </div>
          </KPISection>
        </div>
      </div>

      {/* Right Column - Alerts & Activity */}
      <div className="space-y-6">
        {/* Alerts */}
        <div className="rounded-2xl bg-white border border-[#E9DCC0] shadow-[0_4px_16px_rgba(76,42,110,0.06)] overflow-hidden">
          <div className="px-5 py-3 flex items-center justify-between bg-red-500/5 border-b border-red-500/10">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600" />
              <h3 className="font-semibold text-sm text-red-600">{i18n.t('adm.alertes')}</h3>
            </div>
            <span className="text-xs text-red-600/60">{i18n.t('adm.alertes_count', { count: alerts.length })}</span>
          </div>
          <div className="p-4 space-y-3 max-h-[300px] overflow-y-auto">
            {alerts.length > 0 ? (
              alerts.map((alert, idx) => <AlertCard key={alert.id || alert.code || `alert-${idx}`} alert={alert} />)
            ) : (
              <div className="text-center py-6 text-[#A8977C]">
                <CheckCircle2 className="w-8 h-8 mx-auto mb-2" />
                <p className="text-sm">{i18n.t('adm.aucune_alerte')}</p>
              </div>
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="rounded-2xl bg-white border border-[#E9DCC0] shadow-[0_4px_16px_rgba(76,42,110,0.06)] overflow-hidden">
          <div className="px-5 py-3 flex items-center justify-between bg-[#F8F1E1] border-b border-[#EDE1C6]">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-[#7A6850]" />
              <h3 className="font-semibold text-sm text-[#3D2E1E]">{i18n.t('adm.activite_recente')}</h3>
            </div>
          </div>
          <div className="p-4 max-h-[400px] overflow-y-auto">
            {activities.length > 0 ? (
              activities.map((activity, idx) => <ActivityItem key={activity.id || activity.timestamp || `act-${idx}`} activity={activity} />)
            ) : (
              <div className="text-center py-6 text-[#A8977C]">
                <Clock className="w-8 h-8 mx-auto mb-2" />
                <p className="text-sm">{i18n.t('adm.aucune_activite_recente')}</p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="rounded-2xl bg-white border border-[#E9DCC0] shadow-[0_4px_16px_rgba(76,42,110,0.06)] p-5">
          <h3 className="font-semibold text-sm text-[#3D2E1E] mb-4">{i18n.t('adm.actions_rapides')}</h3>
          <div className="space-y-2">
            <Link to="/admin-v2" className="flex items-center justify-between p-3 rounded-xl bg-[#F8F1E1] hover:bg-[#F3E9D2] transition-colors">
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-[#8B5CF6]" />
                <span className="text-sm text-[#3D2E1E]">{i18n.t('adm.gerer_les_organisations')}</span>
              </div>
              <ChevronRight className="w-4 h-4 text-[#A8977C]" />
            </Link>
            <Link to="/catalogue" className="flex items-center justify-between p-3 rounded-xl bg-[#F8F1E1] hover:bg-[#F3E9D2] transition-colors">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-[#F59E0B]" />
                <span className="text-sm text-[#3D2E1E]">{i18n.t('adm.catalogue_produits')}</span>
              </div>
              <ChevronRight className="w-4 h-4 text-[#A8977C]" />
            </Link>
            <Link to="/legal/charte-ess" className="flex items-center justify-between p-3 rounded-xl bg-[#F8F1E1] hover:bg-[#F3E9D2] transition-colors">
              <div className="flex items-center gap-2">
                <Leaf className="w-4 h-4 text-[#10B981]" />
                <span className="text-sm text-[#3D2E1E]">{i18n.t('adm.charte_ess')}</span>
              </div>
              <ChevronRight className="w-4 h-4 text-[#A8977C]" />
            </Link>
            <button
              onClick={() => setActiveTab('catalog')}
              className="w-full flex items-center justify-between p-3 rounded-xl bg-[#F8F1E1] hover:bg-[#F3E9D2] transition-colors"
            >
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-[#D9B35A]" />
                <span className="text-sm text-[#3D2E1E]">{i18n.t('adm.gerer_le_catalogue')}</span>
              </div>
              <ChevronRight className="w-4 h-4 text-[#A8977C]" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </>
);
