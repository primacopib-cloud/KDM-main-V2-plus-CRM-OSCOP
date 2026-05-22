import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  Package, 
  ShoppingCart, 
  Wallet, 
  FileSignature,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  Clock,
  RefreshCw,
  Building2,
  Store,
  Loader2,
  ArrowUpRight,
  ArrowDownRight,
  ChevronRight,
  Calendar,
  Shield,
  Leaf,
  BarChart3,
  Bell
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { partners } from '../data/mock';
import { toast } from 'sonner';
import ProductCatalogManager from '../components/ProductCatalogManager';
import AdvancedStatsCharts from '../components/AdvancedStatsCharts';
import { useNotificationWebSocket, ConnectionStatus } from '../components/NotificationToast';
import { BreadcrumbPill } from '../components/Breadcrumb';
import NavigationHistoryDropdown from '../components/NavigationHistoryDropdown';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Stat Card Component
const StatCard = ({ title, value, subtitle, icon: Icon, trend, trendValue, color = '#D9B35A', size = 'normal' }) => {
  const isPositive = trend === 'up';
  
  return (
    <div className={`rounded-2xl p-5 bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.04] transition-all ${size === 'large' ? 'col-span-2' : ''}`}>
      <div className="flex justify-between items-start mb-3">
        <div 
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: `${color}15` }}
        >
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full ${isPositive ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
            {isPositive ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {trendValue}
          </div>
        )}
      </div>
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      <div className="text-sm text-white/50">{title}</div>
      {subtitle && <div className="text-xs text-white/40 mt-1">{subtitle}</div>}
    </div>
  );
};

// Alert Card Component
const AlertCard = ({ alert }) => {
  const icons = {
    error: AlertTriangle,
    warning: AlertCircle,
    info: Info
  };
  const colors = {
    error: '#EF4444',
    warning: '#F59E0B',
    info: '#3B82F6'
  };
  const Icon = icons[alert.type] || Info;
  const color = colors[alert.type] || '#3B82F6';
  
  return (
    <div 
      className="flex items-start gap-3 p-3 rounded-xl"
      style={{ background: `${color}10`, border: `1px solid ${color}20` }}
    >
      <Icon className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color }} />
      <div>
        <p className="text-sm font-medium text-white/90">{alert.title}</p>
        <p className="text-xs text-white/60">{alert.message}</p>
      </div>
    </div>
  );
};

// Activity Item Component
const ActivityItem = ({ activity }) => {
  const icons = {
    order: ShoppingCart,
    signature: FileSignature,
    organization: Building2,
    product: Package
  };
  const colors = {
    order: '#D9B35A',
    signature: '#8B5CF6',
    organization: '#57D19A',
    product: '#3B82F6'
  };
  const Icon = icons[activity.type] || Clock;
  const color = colors[activity.type] || '#D9B35A';
  
  return (
    <div className="flex items-center gap-3 py-3 border-b border-white/5 last:border-0">
      <div 
        className="w-8 h-8 rounded-lg flex items-center justify-center"
        style={{ background: `${color}15` }}
      >
        <Icon className="w-4 h-4" style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white/90 truncate">{activity.action}</p>
        <p className="text-xs text-white/50">{activity.details}</p>
      </div>
      <div className="text-xs text-white/40">
        {activity.timestamp ? new Date(activity.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : ''}
      </div>
    </div>
  );
};

// KPI Section Component
const KPISection = ({ title, icon: Icon, color, children }) => (
  <div className="rounded-2xl bg-white/[0.02] border border-white/[0.08] overflow-hidden">
    <div 
      className="px-5 py-3 flex items-center gap-2"
      style={{ background: `${color}08`, borderBottom: `1px solid ${color}15` }}
    >
      <Icon className="w-4 h-4" style={{ color }} />
      <h3 className="font-semibold text-sm" style={{ color }}>{title}</h3>
    </div>
    <div className="p-5">
      {children}
    </div>
  </div>
);

export default function SuperAdminPage() {
  const [kpis, setKpis] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [period, setPeriod] = useState('month');
  
  // WebSocket notifications
  const { isConnected, notifications } = useNotificationWebSocket(
    localStorage.getItem('userId'),
    true // isAdmin
  );
  
  const fetchData = async () => {
    setLoading(true);
    try {
      const [kpisRes, alertsRes, activityRes] = await Promise.all([
        fetch(`${API_URL}/api/superadmin/kpis?period=${period}`).then(r => r.json()),
        fetch(`${API_URL}/api/superadmin/alerts`).then(r => r.json()),
        fetch(`${API_URL}/api/superadmin/recent-activity`).then(r => r.json())
      ]);
      
      setKpis(kpisRes);
      setAlerts(alertsRes.alerts || []);
      setActivities(activityRes.activities || []);
    } catch (err) {
      console.error('Failed to fetch data:', err);
      toast.error('Erreur de chargement des données');
    } finally {
      setLoading(false);
    }
  };

  const refreshData = () => {
    fetchData();
  };
  
  useEffect(() => {
    fetchData();
  }, [period]);
  
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(amount || 0);
  };
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  return (
    <div 
      className="min-h-screen text-white"
      style={{ background: 'linear-gradient(180deg, #05070C 0%, #070A10 45%, #060913 100%)' }}
    >
      {/* Header */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(7,10,16,0.95)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(255,255,255,0.08)'
        }}
      >
        <div className="max-w-[1400px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2">
              <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-8 w-auto object-contain" />
              <span className="text-white/30 text-xs">×</span>
              <img src={partners.oscop.logo} alt="O'SCOP" className="h-5 w-auto object-contain" />
            </Link>
            <div className="h-6 w-px bg-white/10" />
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-[#EF4444]" />
              <span className="text-sm font-semibold text-white/90">Super Admin</span>
            </div>
          </div>
          
          {/* Quick Navigation */}
          <nav className="hidden lg:flex items-center gap-1">
            <Link to="/" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Accueil
            </Link>
            <Link to="/espace-acheteur" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Espace Acheteur
            </Link>
            <Link to="/espace-vendeur" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Espace Vendeur
            </Link>
            <Link to="/catalogue" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Catalogue
            </Link>
            <Link to="/admin-v2" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Admin Orgs
            </Link>
            <Link to="/admin/produits" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Validation
            </Link>
          </nav>
          
          <div className="flex items-center gap-3">
            {/* Navigation History */}
            <NavigationHistoryDropdown variant="dark" />
            
            {/* WebSocket Status */}
            <ConnectionStatus isConnected={isConnected} />
            
            {/* Period Selector */}
            <select 
              value={period} 
              onChange={(e) => setPeriod(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white/80"
            >
              <option value="day">Aujourd'hui</option>
              <option value="week">Cette semaine</option>
              <option value="month">Ce mois</option>
              <option value="year">Cette année</option>
              <option value="all">Tout</option>
            </select>
            
            <Button 
              variant="outline" 
              size="sm" 
              onClick={fetchData}
              className="border-white/10 hover:bg-white/5"
            >
              <RefreshCw className="w-4 h-4 mr-1" />
              Actualiser
            </Button>
          </div>
        </div>
        
        {/* Tabs Navigation */}
        <div className="max-w-[1400px] mx-auto px-5 pb-3">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="bg-white/[0.04] border border-white/[0.08] p-1 rounded-xl">
              <TabsTrigger 
                value="dashboard" 
                className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
              >
                <LayoutDashboard className="w-4 h-4 mr-2" />
                Dashboard
              </TabsTrigger>
              <TabsTrigger 
                value="stats"
                className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
              >
                <BarChart3 className="w-4 h-4 mr-2" />
                Statistiques
              </TabsTrigger>
              <TabsTrigger 
                value="catalog"
                className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
              >
                <Package className="w-4 h-4 mr-2" />
                Catalogue
              </TabsTrigger>
              <TabsTrigger 
                value="users"
                className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
              >
                <Users className="w-4 h-4 mr-2" />
                Utilisateurs
              </TabsTrigger>
              <TabsTrigger 
                value="orders"
                className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
              >
                <ShoppingCart className="w-4 h-4 mr-2" />
                Commandes
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-5 py-8">
        {/* Breadcrumb */}
        <div className="mb-6">
          <BreadcrumbPill />
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          {/* DASHBOARD TAB */}
          <TabsContent value="dashboard">
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
            color="#57D19A"
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
              
              {/* Orders by Status */}
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
              
              {/* By Role */}
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
              <KPISection title="Wallet & Crédits" icon={Wallet} color="#57D19A">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-white/60">Solde total</span>
                    <span className="font-bold text-[#57D19A]">{formatCurrency(kpis?.wallet?.current_total_balance)}</span>
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
                  alerts.map((alert, idx) => <AlertCard key={idx} alert={alert} />)
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
                  activities.map((activity, idx) => <ActivityItem key={idx} activity={activity} />)
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
          </TabsContent>

          {/* CATALOG TAB */}
          <TabsContent value="catalog">
            <ProductCatalogManager onProductSaved={refreshData} />
          </TabsContent>

          {/* STATISTICS TAB */}
          <TabsContent value="stats">
            <div className="space-y-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-[#D9B35A]" />
                    Statistiques avancées
                  </h2>
                  <p className="text-white/60 text-sm mt-1">
                    Analyses et tendances détaillées de la plateforme
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-white/40">Période:</span>
                  <select 
                    value={period} 
                    onChange={(e) => setPeriod(e.target.value)}
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white/80"
                  >
                    <option value="week">7 derniers jours</option>
                    <option value="month">30 derniers jours</option>
                    <option value="quarter">Trimestre</option>
                    <option value="year">Année</option>
                  </select>
                </div>
              </div>
              
              <AdvancedStatsCharts period={period} />
            </div>
          </TabsContent>

          {/* USERS TAB */}
          <TabsContent value="users">
            <div className="rounded-2xl bg-white/[0.02] border border-white/[0.08] p-6">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Users className="w-5 h-5 text-[#3B82F6]" />
                Gestion des utilisateurs
              </h2>
              <p className="text-white/60 mb-6">Vue d'ensemble des utilisateurs et organisations.</p>
              
              <div className="grid sm:grid-cols-3 gap-4 mb-6">
                <div className="p-4 rounded-xl bg-[#3B82F6]/10 border border-[#3B82F6]/20 text-center">
                  <div className="text-3xl font-bold text-[#3B82F6]">{kpis?.users?.total || 0}</div>
                  <div className="text-sm text-white/60">Total utilisateurs</div>
                </div>
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center">
                  <div className="text-3xl font-bold text-emerald-400">{kpis?.users?.active || 0}</div>
                  <div className="text-sm text-white/60">Actifs</div>
                </div>
                <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/20 text-center">
                  <div className="text-3xl font-bold text-purple-400">{kpis?.users?.organizations?.approved || 0}</div>
                  <div className="text-sm text-white/60">Organisations</div>
                </div>
              </div>
              
              <div className="flex gap-3">
                <Link to="/admin-v2">
                  <Button className="bg-[#3B82F6] hover:bg-[#2563EB] text-white">
                    <Building2 className="w-4 h-4 mr-2" />
                    Gérer les organisations
                  </Button>
                </Link>
              </div>
            </div>
          </TabsContent>

          {/* ORDERS TAB */}
          <TabsContent value="orders">
            <div className="rounded-2xl bg-white/[0.02] border border-white/[0.08] p-6">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <ShoppingCart className="w-5 h-5 text-[#F59E0B]" />
                Gestion des commandes
              </h2>
              <p className="text-white/60 mb-6">Suivi des commandes et paiements.</p>
              
              <div className="grid sm:grid-cols-4 gap-4 mb-6">
                <div className="p-4 rounded-xl bg-[#D9B35A]/10 border border-[#D9B35A]/20 text-center">
                  <div className="text-3xl font-bold text-[#D9B35A]">{formatCurrency(kpis?.sales?.total_revenue)}</div>
                  <div className="text-sm text-white/60">CA Total</div>
                </div>
                <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-center">
                  <div className="text-3xl font-bold text-blue-400">{kpis?.sales?.total_orders || 0}</div>
                  <div className="text-sm text-white/60">Commandes</div>
                </div>
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-center">
                  <div className="text-3xl font-bold text-amber-400">{kpis?.sales?.pending_orders || 0}</div>
                  <div className="text-sm text-white/60">En attente</div>
                </div>
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center">
                  <div className="text-3xl font-bold text-emerald-400">{formatCurrency(kpis?.sales?.average_basket)}</div>
                  <div className="text-sm text-white/60">Panier moyen</div>
                </div>
              </div>
              
              {/* Orders by status */}
              {kpis?.sales?.orders_by_status && (
                <div className="mb-6">
                  <p className="text-sm text-white/50 mb-3">Répartition par statut</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(kpis.sales.orders_by_status).map(([status, count]) => (
                      <span key={status} className="px-3 py-1.5 rounded-full bg-white/[0.04] text-sm text-white/70 border border-white/[0.08]">
                        {status}: <span className="font-bold text-white">{count}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              <Link to="/commandes">
                <Button className="bg-[#F59E0B] hover:bg-[#D97706] text-black">
                  <ShoppingCart className="w-4 h-4 mr-2" />
                  Voir toutes les commandes
                </Button>
              </Link>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
