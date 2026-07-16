import i18n from '@/i18n';
import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  ShoppingBag, Package, FileText, Wallet, TrendingUp,
  CheckCircle2, ChevronRight, ArrowLeft, RefreshCw,
  AlertTriangle, AlertCircle,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { BreadcrumbPill } from '../components/Breadcrumb';
import NavigationHistoryDropdown from '../components/NavigationHistoryDropdown';

import { authAPI, ordersAPIV2, walletAPIV2, invoicesAPI } from '../services/api';
import { BuyerDashboardTab } from '../components/buyer/BuyerDashboardTab';
import { BuyerOrdersTab } from '../components/buyer/BuyerOrdersTab';
import { BuyerInvoicesTab } from '../components/buyer/BuyerInvoicesTab';
import { BuyerWalletTab } from '../components/buyer/BuyerWalletTab';
import { BuyerModals } from '../components/buyer/BuyerModals';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ===== MAIN COMPONENT =====
export default function BuyerSpacePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Data states
  const [orders, setOrders] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [invoiceStats, setInvoiceStats] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({
    totalOrders: 0,
    pendingOrders: 0,
    totalSpent: 0,
    creditsBalance: 0
  });
  
  // Modal states
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [orderModalOpen, setOrderModalOpen] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [invoiceModalOpen, setInvoiceModalOpen] = useState(false);
  
  // Filters
  const [orderStatusFilter, setOrderStatusFilter] = useState('all');
  const [invoiceStatusFilter, setInvoiceStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Load initial data
  useEffect(() => {
    const init = async () => {
      if (!authAPI.isAuthenticated()) {
        toast.error('Veuillez vous connecter');
        navigate('/connexion?redirect=/espace-acheteur');
        return;
      }

      try {
        // Get user profile with org info from v2 API
        const token = localStorage.getItem('token');
        const API_BASE = process.env.REACT_APP_BACKEND_URL;
        
        // Try to get extended user profile
        let userProfile = null;
        try {
          const profileRes = await fetch(`${API_BASE}/api/v2/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (profileRes.ok) {
            userProfile = await profileRes.json();
          }
        } catch (e) {
          console.log('v2 profile not available');
        }
        
        // Fallback to legacy auth
        const userData = userProfile || await authAPI.getMe();
        setUser(userData);
        
        const orgId = userData?.organization_id;

        // Load all data in parallel
        const [ordersData, invoicesData, invoiceStatsData] = await Promise.all([
          ordersAPIV2.list(null, 0, 100).catch(() => []),
          invoicesAPI.list(null, null, 0, 100).catch(() => ({ invoices: [] })),
          invoicesAPI.getStats().catch(() => null),
        ]);

        setOrders(ordersData || []);
        setInvoices(invoicesData?.invoices || []);
        setInvoiceStats(invoiceStatsData);

        // Set wallet from user profile or load separately
        if (userData?.wallet) {
          setWallet(userData.wallet);
        } else if (orgId) {
          const walletData = await walletAPIV2.get(orgId).catch(() => null);
          setWallet(walletData);
        }

        // Load transactions
        if (orgId) {
          const ledgerData = await walletAPIV2.getLedger(orgId, 50).catch(() => []);
          setTransactions(ledgerData || []);
        }

        // Calculate stats
        const totalOrders = ordersData?.length || 0;
        const pendingOrders = ordersData?.filter(o => 
          ['PENDING', 'CONFIRMED', 'PROCESSING', 'READY_FOR_PICKUP'].includes(o.status)
        ).length || 0;
        const totalSpent = ordersData?.reduce((sum, o) => sum + (o.total_ttc_cents || 0), 0) || 0;
        const walletBalance = userData?.wallet?.balance_cents || 0;
        
        setStats({
          totalOrders,
          pendingOrders,
          totalSpent,
          creditsBalance: walletBalance
        });

        // Generate alerts
        const newAlerts = [];
        const readyOrders = ordersData?.filter(o => o.status === 'READY_FOR_PICKUP') || [];
        if (readyOrders.length > 0) {
          newAlerts.push({
            id: 'ready-orders',
            type: 'success',
            title: i18n.t('buyer.toast_pretes', { count: readyOrders.length }),
            message: 'Vos commandes sont disponibles au point de retrait EXW.',
            action: () => setActiveTab('orders')
          });
        }
        
        // Low balance alert
        if (walletBalance < 5000) {
          newAlerts.push({
            id: 'low-balance',
            type: 'warning',
            title: i18n.t('buyer.solde_faible'),
            message: i18n.t('buyer.solde_faible_msg'),
            action: () => setActiveTab('wallet')
          });
        }
        
        // Unpaid invoices alert
        const unpaidInvoices = invoicesData?.invoices?.filter(i => i.payment_status === 'PENDING') || [];
        if (unpaidInvoices.length > 0) {
          newAlerts.push({
            id: 'unpaid-invoices',
            type: 'warning',
            title: `${unpaidInvoices.length} facture(s) en attente de paiement`,
            message: i18n.t('buyer.factures_msg'),
            action: () => setActiveTab('invoices')
          });
        }

        setAlerts(newAlerts);

      } catch (error) {
        console.error('Error loading buyer space:', error);
        toast.error('Erreur lors du chargement');
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate]);

  // Filter orders
  const filteredOrders = orders.filter(order => {
    const matchesStatus = orderStatusFilter === 'all' || order.status === orderStatusFilter;
    const matchesSearch = !searchTerm || 
      order.order_number?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  // Filter invoices
  const filteredInvoices = invoices.filter(invoice => {
    const matchesStatus = invoiceStatusFilter === 'all' || 
      invoice.payment_status === invoiceStatusFilter ||
      invoice.status === invoiceStatusFilter;
    const matchesSearch = !searchTerm || 
      invoice.invoice_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      invoice.order_number?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  // Refresh data
  const refreshData = async () => {
    setLoading(true);
    try {
      const orgId = user?.organization_id;
      const [ordersData, walletData, invoicesData, invoiceStatsData] = await Promise.all([
        ordersAPIV2.list(null, 0, 100).catch(() => []),
        orgId ? walletAPIV2.get(orgId).catch(() => null) : Promise.resolve(null),
        invoicesAPI.list(null, null, 0, 100).catch(() => ({ invoices: [] })),
        invoicesAPI.getStats().catch(() => null),
      ]);
      setOrders(ordersData || []);
      setWallet(walletData);
      setInvoices(invoicesData?.invoices || []);
      setInvoiceStats(invoiceStatsData);
      toast.success(i18n.t('buyer.toast_actualise'));
    } catch (error) {
      toast.error('Erreur lors de l\'actualisation');
    } finally {
      setLoading(false);
    }
  };

  // View order details
  const viewOrderDetails = async (order) => {
    try {
      const fullOrder = await ordersAPIV2.get(order.id);
      setSelectedOrder(fullOrder);
      setOrderModalOpen(true);
    } catch (error) {
      toast.error(i18n.t('buyer.toast_erreur_details'));
    }
  };

  // View invoice details
  const viewInvoiceDetails = (invoice) => {
    setSelectedInvoice(invoice);
    setInvoiceModalOpen(true);
  };

  // Download invoice PDF (placeholder)
  const downloadInvoicePDF = async (invoice) => {
    toast.info(i18n.t('buyer.toast_pdf'));
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v2/pdf/invoice/${invoice.id}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (!response.ok) throw new Error(i18n.t('buyer.toast_erreur_generation'));
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `facture_${invoice.invoice_number}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success(i18n.t('buyer.toast_facture', { number: invoice.invoice_number }));
    } catch (error) {
      console.error('PDF download error:', error);
      toast.error(i18n.t('buyer.toast_erreur_pdf'));
    }
  };

  // Download order PDF: handled via /bon-de-commande page (link in orders tab)

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}>
        <RefreshCw className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }} data-testid="buyer-space-page">
      {/* Header */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(255,253,247,0.86)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(212,175,55,0.32)'
        }}
      >
        <div className="max-w-[1280px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2 text-white/60 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm hidden sm:inline">{i18n.t('buyer.accueil')}</span>
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#D9B35A]/20 flex items-center justify-center">
                <ShoppingBag className="w-5 h-5 text-[#D9B35A]" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">{i18n.t('buyer.espace_acheteur_pro')}</h1>
                <p className="text-xs text-white/50">{user?.company_name || 'Mon compte B2B'}</p>
              </div>
            </div>
          </div>
          
          {/* Quick Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            <Link to="/catalogue" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              {i18n.t('buyer.catalogue')}
            </Link>
            <Link to="/commandes" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              {i18n.t('buyer.commandes')}
            </Link>
            <Link to="/wallet" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              {i18n.t('buyer.wallet')}
            </Link>
            <Link to="/documents" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              {i18n.t('onboarding.documents')}
            </Link>
            <Link to="/espace-vendeur" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              {i18n.t('buyer.vendeur')}
            </Link>
            {(user?.role === 'admin' || user?.email?.includes('admin')) && (
              <Link to="/superadmin" className="px-3 py-1.5 text-xs text-[#D9B35A] hover:bg-[#D9B35A]/10 rounded-lg transition-colors">
                {i18n.t('buyer.admin')}
              </Link>
            )}
          </nav>
          
          <div className="flex items-center gap-3">
            {/* Navigation History */}
            <NavigationHistoryDropdown variant="dark" />
            
            <Button 
              variant="outline" 
              size="sm"
              onClick={refreshData}
              className="border-white/10 text-white/70"
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            <Link to="/catalogue">
              <Button className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black text-sm">
                <Package className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">{i18n.t('buyer.catalogue')}</span>
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-[1280px] mx-auto px-5 py-6">
        {/* Breadcrumb */}
        <div className="mb-4">
          <BreadcrumbPill />
        </div>

        {/* Alerts Banner */}
        {alerts.length > 0 && (
          <div className="space-y-3 mb-6">
            {alerts.map(alert => (
              <div
                key={alert.id}
                className={`p-4 rounded-xl border flex items-start justify-between gap-4 ${
                  alert.type === 'success' 
                    ? 'bg-emerald-500/10 border-emerald-500/20' 
                    : alert.type === 'warning'
                    ? 'bg-amber-500/10 border-amber-500/20'
                    : 'bg-red-500/10 border-red-500/20'
                }`}
              >
                <div className="flex items-start gap-3">
                  {alert.type === 'success' ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  ) : alert.type === 'warning' ? (
                    <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  )}
                  <div>
                    <p className={`font-medium ${
                      alert.type === 'success' ? 'text-emerald-400' : 
                      alert.type === 'warning' ? 'text-amber-400' : 'text-red-400'
                    }`}>{alert.title}</p>
                    <p className="text-sm text-white/60">{alert.message}</p>
                  </div>
                </div>
                {alert.action && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={alert.action}
                    className="text-white/60 hover:text-white"
                  >
                    Voir <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-white/[0.04] border border-white/[0.08] p-1 rounded-xl">
            <TabsTrigger 
              value="dashboard" 
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
            >
              <TrendingUp className="w-4 h-4 mr-2" />
              {i18n.t('buyer.tableau_de_bord')}
            </TabsTrigger>
            <TabsTrigger 
              value="orders"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
            >
              <Package className="w-4 h-4 mr-2" />
              {i18n.t('buyer.commandes')}
              {stats.pendingOrders > 0 && (
                <Badge className="ml-2 bg-amber-500/20 text-amber-400 border-0">{stats.pendingOrders}</Badge>
              )}
            </TabsTrigger>
            <TabsTrigger 
              value="invoices"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
            >
              <FileText className="w-4 h-4 mr-2" />
              {i18n.t('buyer.factures')}
            </TabsTrigger>
            <TabsTrigger 
              value="wallet"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
            >
              <Wallet className="w-4 h-4 mr-2" />
              {i18n.t('buyer.wallet')}
            </TabsTrigger>
          </TabsList>

          <BuyerDashboardTab stats={stats} orders={orders} setActiveTab={setActiveTab} />

          <BuyerOrdersTab
            orders={orders}
            filteredOrders={filteredOrders}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            orderStatusFilter={orderStatusFilter}
            setOrderStatusFilter={setOrderStatusFilter}
            viewOrderDetails={viewOrderDetails}
          />

          <BuyerInvoicesTab
            invoices={invoices}
            filteredInvoices={filteredInvoices}
            invoiceStats={invoiceStats}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            invoiceStatusFilter={invoiceStatusFilter}
            setInvoiceStatusFilter={setInvoiceStatusFilter}
            viewInvoiceDetails={viewInvoiceDetails}
            downloadInvoicePDF={downloadInvoicePDF}
          />

          <BuyerWalletTab wallet={wallet} transactions={transactions} />
        </Tabs>
      </div>

      <BuyerModals
        orderModalOpen={orderModalOpen}
        setOrderModalOpen={setOrderModalOpen}
        selectedOrder={selectedOrder}
        invoiceModalOpen={invoiceModalOpen}
        setInvoiceModalOpen={setInvoiceModalOpen}
        selectedInvoice={selectedInvoice}
        downloadInvoicePDF={downloadInvoicePDF}
      />
    </div>
  );
}
