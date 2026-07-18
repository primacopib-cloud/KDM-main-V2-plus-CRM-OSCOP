import i18n from '@/i18n';
import { useState, useEffect, useCallback } from 'react';
import { BarChart3, Loader2 } from 'lucide-react';
import { Tabs, TabsContent } from '../components/ui/tabs';
import { toast } from 'sonner';
import ProductCatalogManager from '../components/ProductCatalogManager';
import AdvancedStatsCharts from '../components/AdvancedStatsCharts';
import { useNotificationWebSocket } from '../components/NotificationToast';
import { BreadcrumbPill } from '../components/Breadcrumb';
import { SuperAdminHeader } from '../components/superadmin/SuperAdminHeader';
import { DashboardTab } from '../components/superadmin/DashboardTab';
import { UsersTab, OrdersTab } from '../components/superadmin/UsersOrdersTabs';
import { TeamRolesTab } from '../components/superadmin/TeamRolesTab';
import { BuyersTab } from '../components/superadmin/BuyersTab';
import { TaxonomyTab } from '../components/superadmin/TaxonomyTab';
import { VendorCreditsTab } from '../components/superadmin/VendorCreditsTab';
import { SupportTicketsTab } from '../components/superadmin/SupportTicketsTab';
import { MemberRegistryTab } from '../components/superadmin/MemberRegistryTab';
import { CoopersConventionsTab } from '../components/superadmin/CoopersConventionsTab';
import { AdminContractsTab } from '../components/superadmin/AdminContractsTab';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function SuperAdminPage() {
  const [kpis, setKpis] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [period, setPeriod] = useState('month');

  // WebSocket notifications
  const { isConnected } = useNotificationWebSocket(
    JSON.parse(localStorage.getItem('user') || 'null')?.id,
    true // isAdmin
  );

  const fetchData = useCallback(async () => {
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
      toast.error(i18n.t('adm.erreur_de_chargement_des_donnees'));
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  return (
    <div
      className="min-h-screen text-white"
      style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }}
    >
      <SuperAdminHeader
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        period={period}
        setPeriod={setPeriod}
        onRefresh={fetchData}
        isConnected={isConnected}
      />

      <main className="max-w-[1400px] mx-auto px-5 py-8">
        <div className="mb-6">
          <BreadcrumbPill />
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsContent value="dashboard">
            <DashboardTab
              kpis={kpis}
              alerts={alerts}
              activities={activities}
              period={period}
              setActiveTab={setActiveTab}
            />
          </TabsContent>

          <TabsContent value="catalog">
            <ProductCatalogManager onProductSaved={fetchData} />
          </TabsContent>

          <TabsContent value="stats">
            <div className="space-y-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-[#D9B35A]" />
                    {i18n.t('adm.statistiques_avancees')}
                  </h2>
                  <p className="text-white/60 text-sm mt-1">
                    {i18n.t('adm.analyses_tendances')}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-white/40">{i18n.t('adm.periode')}</span>
                  <select
                    value={period}
                    onChange={(e) => setPeriod(e.target.value)}
                    className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white/80"
                  >
                    <option value="week">{i18n.t('adm.7_derniers_jours')}</option>
                    <option value="month">{i18n.t('adm.30_derniers_jours')}</option>
                    <option value="quarter">{i18n.t('adm.trimestre')}</option>
                    <option value="year">{i18n.t('adm.annee')}</option>
                  </select>
                </div>
              </div>

              <AdvancedStatsCharts period={period} />
            </div>
          </TabsContent>

          <TabsContent value="users">
            <UsersTab kpis={kpis} />
          </TabsContent>

          <TabsContent value="roles">
            <TeamRolesTab />
          </TabsContent>

          <TabsContent value="buyers">
            <BuyersTab />
          </TabsContent>

          <TabsContent value="taxonomy">
            <TaxonomyTab />
          </TabsContent>

          <TabsContent value="credits">
            <VendorCreditsTab />
          </TabsContent>

          <TabsContent value="support">
            <SupportTicketsTab />
          </TabsContent>

          <TabsContent value="registry">
            <MemberRegistryTab />
          </TabsContent>

          <TabsContent value="conventions">
            <CoopersConventionsTab />
          </TabsContent>

          <TabsContent value="contracts">
            <AdminContractsTab />
          </TabsContent>

          <TabsContent value="orders">
            <OrdersTab kpis={kpis} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
