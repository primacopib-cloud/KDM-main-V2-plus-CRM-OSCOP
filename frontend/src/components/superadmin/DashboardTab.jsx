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
        title="Chiffre d'affaires"
        value={formatCurrency(kpis?.sales?.total_revenue)}
        icon={TrendingUp}
        color="#10B981"
        trend="up"
        trendValue="+12%"
      />
      <StatCard
        title="Commandes"
        value={kpis?.sales?.total_orders || 0}
        subtitle={`Panier moyen: ${formatCurrency(kpis?.sales?.average_basket)}`}
        icon={ShoppingCart}
        color="#D9B35A"
      />
      <StatCard
        title="Utilisateurs"
        value={kpis?.users?.total || 0}
        subtitle={`${kpis?.users?.active || 0} actifs`}
        icon={Users}
        color="#3B82F6"
      />
      <StatCard
        title="Organisations"
        value={kpis?.users?.organizations?.total || 0}
        subtitle={`${kpis?.users?.organizations?.pending || 0} en attente`}
        icon={Building2}
        color="#8B5CF6"
      />
      <StatCard
        title="Produits"
        value={kpis?.products?.total || 0}
        subtitle={`${kpis?.products?.low_stock || 0} stock faible`}
        icon={Package}
        color="#F59E0B"
      />
      <StatCard
        title="Crédits Wallet"
        value={formatCurrency(kpis?.wallet?.current_total_balance)}
        subtitle={`${formatCurrency(kpis?.wallet?.total_credits_sold)} vendus`}
        icon={Wallet}
        color="#D4AF37"
      />
    </div>

    <div className="grid lg:grid-cols-3 gap-6">
      {/* Left Column - KPIs */}
      <div className="lg:col-span-2 space-y-6">
        {/* Sales KPIs */}
        <KPISection title="Ventes & Commandes" icon={ShoppingCart} color="#D9B35A">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 rounded-xl bg-white/[0.02]">
              <div className="text-xl font-bold text-[#D9B35A]">{formatCurrency(kpis?.sales?.total_revenue)}</div>
              <div className="text-xs text-white/50">CA Total</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-white/[0.02]">
              <div className="text-xl font-bold text-white">{kpis?.sales?.total_orders}</div>
              <div className="text-xs text-white/50">Commandes</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-white/[0.02]">
              <div className="text-xl font-bold text-white">{formatCurrency(kpis?.sales?.average_basket)}</div>
              <div className="text-xs text-white/50">Panier moyen</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-white/[0.02]">
              <div className="text-xl font-bold text-white">{kpis?.sales?.installment_orders || 0}</div>
              <div className="text-xs text-white/50">Paiements 4×</div>
            </div>
          </div>

          {kpis?.sales?.orders_by_status && Object.keys(kpis.sales.orders_by_status).length > 0 && (
            <div className="mt-4 pt-4 border-t border-white/5">
              <p className="text-xs text-white/50 mb-2">Par statut</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(kpis.sales.orders_by_status).map(([status, count]) => (
                  <span key={status} className="px-2 py-1 rounded-full bg-white/5 text-xs text-white/70">
                    {status}: <span className="font-semibold">{count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </KPISection>

        {/* Users & Organizations */}
        <KPISection title="Utilisateurs & Organisations" icon={Users} color="#3B82F6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 rounded-xl bg-white/[0.02]">
              <div className="text-xl font-bold text-[#3B82F6]">{kpis?.users?.total}</div>
              <div className="text-xs text-white/50">Total utilisateurs</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-white/[0.02]">
              <div className="text-xl font-bold text-green-400">{kpis?.users?.active}</div>
              <div className="text-xs text-white/50">Actifs</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-white/[0.02]">
              <div className="text-xl font-bold text-white">{kpis?.users?.new_period}</div>
              <div className="text-xs text-white/50">Nouveaux ({period})</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-white/[0.02]">
              <div className="text-xl font-bold text-[#8B5CF6]">{kpis?.users?.organizations?.approved}</div>
              <div className="text-xs text-white/50">Orgs. approuvées</div>
            </div>
          </div>

          {kpis?.users?.by_role && Object.keys(kpis.users.by_role).length > 0 && (
            <div className="mt-4 pt-4 border-t border-white/5">
              <p className="text-xs text-white/50 mb-2">Par rôle</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(kpis.users.by_role).map(([role, count]) => (
                  <span key={role} className="px-2 py-1 rounded-full bg-white/5 text-xs text-white/70">
                    {role}: <span className="font-semibold">{count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </KPISection>

        {/* Products */}
        <KPISection title="Catalogue Produits" icon={Package} color="#F59E0B">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 rounded-xl bg-white/[0.02]">
              <div className="text-xl font-bold text-[#F59E0B]">{kpis?.products?.total}</div>
              <div className="text-xs text-white/50">Total produits</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-white/[0.02]">
              <div className="text-xl font-bold text-green-400">{kpis?.products?.active}</div>
              <div className="text-xs text-white/50">Actifs</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-white/[0.02]">
              <div className="text-xl font-bold text-yellow-400">{kpis?.products?.low_stock}</div>
              <div className="text-xs text-white/50">Stock faible</div>
            </div>
            <div className="text-center p-3 rounded-xl bg-white/[0.02]">
              <div className="text-xl font-bold text-red-400">{kpis?.products?.out_of_stock}</div>
              <div className="text-xs text-white/50">Rupture</div>
            </div>
          </div>
        </KPISection>

        {/* Wallet & Signatures */}
        <div className="grid md:grid-cols-2 gap-6">
          <KPISection title="Wallet & Crédits" icon={Wallet} color="#D4AF37">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-white/60">Solde total</span>
                <span className="font-bold text-[#D4AF37]">{formatCurrency(kpis?.wallet?.current_total_balance)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-white/60">Crédits vendus</span>
                <span className="font-semibold text-white/90">{formatCurrency(kpis?.wallet?.total_credits_sold)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-white/60">Crédits consommés</span>
                <span className="font-semibold text-white/90">{formatCurrency(kpis?.wallet?.total_credits_consumed)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-white/60">Transactions</span>
                <span className="font-semibold text-white/90">{kpis?.wallet?.credits_transactions + kpis?.wallet?.consumption_transactions}</span>
              </div>
            </div>
          </KPISection>

          <KPISection title="Signatures eIDAS" icon={FileSignature} color="#8B5CF6">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-white/60">Total signatures</span>
                <span className="font-bold text-[#8B5CF6]">{kpis?.signatures?.total}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-white/60">Signées</span>
                <span className="font-semibold text-green-400">{kpis?.signatures?.signed}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-white/60">En attente</span>
                <span className="font-semibold text-yellow-400">{kpis?.signatures?.pending}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-white/60">Taux de succès</span>
                <span className="font-semibold text-white/90">{kpis?.signatures?.success_rate}%</span>
              </div>
            </div>
          </KPISection>
        </div>
      </div>

      {/* Right Column - Alerts & Activity */}
      <div className="space-y-6">
        {/* Alerts */}
        <div className="rounded-2xl bg-white/[0.02] border border-white/[0.08] overflow-hidden">
          <div className="px-5 py-3 flex items-center justify-between bg-red-500/5 border-b border-red-500/10">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <h3 className="font-semibold text-sm text-red-400">Alertes</h3>
            </div>
            <span className="text-xs text-red-400/60">{alerts.length} alerte(s)</span>
          </div>
          <div className="p-4 space-y-3 max-h-[300px] overflow-y-auto">
            {alerts.length > 0 ? (
              alerts.map((alert, idx) => <AlertCard key={alert.id || alert.code || `alert-${idx}`} alert={alert} />)
            ) : (
              <div className="text-center py-6 text-white/40">
                <CheckCircle2 className="w-8 h-8 mx-auto mb-2" />
                <p className="text-sm">Aucune alerte</p>
              </div>
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="rounded-2xl bg-white/[0.02] border border-white/[0.08] overflow-hidden">
          <div className="px-5 py-3 flex items-center justify-between bg-white/[0.02] border-b border-white/[0.05]">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-white/60" />
              <h3 className="font-semibold text-sm text-white/80">Activité récente</h3>
            </div>
          </div>
          <div className="p-4 max-h-[400px] overflow-y-auto">
            {activities.length > 0 ? (
              activities.map((activity, idx) => <ActivityItem key={activity.id || activity.timestamp || `act-${idx}`} activity={activity} />)
            ) : (
              <div className="text-center py-6 text-white/40">
                <Clock className="w-8 h-8 mx-auto mb-2" />
                <p className="text-sm">Aucune activité récente</p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="rounded-2xl bg-white/[0.02] border border-white/[0.08] p-5">
          <h3 className="font-semibold text-sm text-white/80 mb-4">Actions rapides</h3>
          <div className="space-y-2">
            <Link to="/admin-v2" className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] transition-colors">
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-[#8B5CF6]" />
                <span className="text-sm text-white/80">Gérer les organisations</span>
              </div>
              <ChevronRight className="w-4 h-4 text-white/40" />
            </Link>
            <Link to="/catalogue" className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] transition-colors">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-[#F59E0B]" />
                <span className="text-sm text-white/80">Catalogue produits</span>
              </div>
              <ChevronRight className="w-4 h-4 text-white/40" />
            </Link>
            <Link to="/legal/charte-ess" className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] transition-colors">
              <div className="flex items-center gap-2">
                <Leaf className="w-4 h-4 text-[#10B981]" />
                <span className="text-sm text-white/80">Charte ESS</span>
              </div>
              <ChevronRight className="w-4 h-4 text-white/40" />
            </Link>
            <button
              onClick={() => setActiveTab('catalog')}
              className="w-full flex items-center justify-between p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] transition-colors"
            >
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-[#D9B35A]" />
                <span className="text-sm text-white/80">Gérer le catalogue</span>
              </div>
              <ChevronRight className="w-4 h-4 text-white/40" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </>
);
