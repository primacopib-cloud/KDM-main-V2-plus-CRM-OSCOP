import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  ShoppingBag, Package, FileText, Wallet, Bell, TrendingUp,
  Clock, CheckCircle2, XCircle, ChevronRight, ArrowLeft,
  Calendar, CreditCard, RefreshCw, Download, Filter, Eye,
  AlertTriangle, ArrowUpRight, ArrowDownRight, Building2,
  MapPin, Truck, Search, AlertCircle, Receipt, Euro, X
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from '../components/ui/dialog';
import { toast } from 'sonner';
import { BreadcrumbPill } from '../components/Breadcrumb';
import NavigationHistoryDropdown from '../components/NavigationHistoryDropdown';

import { authAPI, ordersAPIV2, walletAPIV2, invoicesAPI } from '../services/api';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Format currency
const formatCurrency = (cents) => {
  if (!cents && cents !== 0) return '---';
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR'
  }).format(cents / 100);
};

// Format date
const formatDate = (dateStr) => {
  if (!dateStr) return '---';
  return new Date(dateStr).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Format short date
const formatShortDate = (dateStr) => {
  if (!dateStr) return '---';
  return new Date(dateStr).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short'
  });
};

// Order status config
const ORDER_STATUS = {
  PENDING: { label: 'En attente', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: Clock },
  CONFIRMED: { label: 'Confirmée', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: CheckCircle2 },
  PROCESSING: { label: 'En préparation', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30', icon: Package },
  READY_FOR_PICKUP: { label: 'Prête', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', icon: Truck },
  COMPLETED: { label: 'Terminée', color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: CheckCircle2 },
  CANCELED: { label: 'Annulée', color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: XCircle },
};

// Transaction type config
const TRANSACTION_TYPE = {
  CREDIT_PURCHASE: { label: 'Achat crédits', icon: ArrowUpRight, color: 'text-emerald-400' },
  CREDIT_USED: { label: 'Utilisation', icon: ArrowDownRight, color: 'text-orange-400' },
  REFUND: { label: 'Remboursement', icon: ArrowUpRight, color: 'text-blue-400' },
  ADMIN_ADJUSTMENT: { label: 'Ajustement', icon: RefreshCw, color: 'text-purple-400' },
};

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
            title: `${readyOrders.length} commande(s) prête(s) à enlever`,
            message: 'Vos commandes sont disponibles au point de retrait EXW.',
            action: () => setActiveTab('orders')
          });
        }
        
        // Low balance alert
        if (walletBalance < 5000) {
          newAlerts.push({
            id: 'low-balance',
            type: 'warning',
            title: 'Solde crédits faible',
            message: 'Pensez à recharger vos crédits pour vos prochaines commandes.',
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
            message: 'Consultez vos factures pour régulariser votre situation.',
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
      toast.success('Données actualisées');
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
      toast.error('Erreur lors du chargement des détails');
    }
  };

  // View invoice details
  const viewInvoiceDetails = (invoice) => {
    setSelectedInvoice(invoice);
    setInvoiceModalOpen(true);
  };

  // Download invoice PDF (placeholder)
  const downloadInvoicePDF = async (invoice) => {
    toast.info('Génération du PDF en cours...');
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v2/pdf/invoice/${invoice.id}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (!response.ok) throw new Error('Erreur de génération');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `facture_${invoice.invoice_number}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success(`Facture ${invoice.invoice_number} téléchargée`);
    } catch (error) {
      console.error('PDF download error:', error);
      toast.error('Erreur lors du téléchargement du PDF');
    }
  };

  // Download order PDF
  const downloadOrderPDF = async (order) => {
    toast.info('Génération du bon de commande...');
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/v2/pdf/order/${order.id}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (!response.ok) throw new Error('Erreur de génération');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `bon_commande_${order.order_number}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success(`Bon de commande ${order.order_number} téléchargé`);
    } catch (error) {
      console.error('PDF download error:', error);
      toast.error('Erreur lors du téléchargement du PDF');
    }
  };

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
              <span className="text-sm hidden sm:inline">Accueil</span>
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#D9B35A]/20 flex items-center justify-center">
                <ShoppingBag className="w-5 h-5 text-[#D9B35A]" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">Espace Acheteur Pro</h1>
                <p className="text-xs text-white/50">{user?.company_name || 'Mon compte B2B'}</p>
              </div>
            </div>
          </div>
          
          {/* Quick Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            <Link to="/catalogue" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Catalogue
            </Link>
            <Link to="/commandes" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Commandes
            </Link>
            <Link to="/wallet" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Wallet
            </Link>
            <Link to="/documents" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Documents
            </Link>
            <Link to="/espace-vendeur" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Vendeur
            </Link>
            {(user?.role === 'admin' || user?.email?.includes('admin')) && (
              <Link to="/superadmin" className="px-3 py-1.5 text-xs text-[#D9B35A] hover:bg-[#D9B35A]/10 rounded-lg transition-colors">
                Admin
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
                <span className="hidden sm:inline">Catalogue</span>
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
              Tableau de bord
            </TabsTrigger>
            <TabsTrigger 
              value="orders"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
            >
              <Package className="w-4 h-4 mr-2" />
              Commandes
              {stats.pendingOrders > 0 && (
                <Badge className="ml-2 bg-amber-500/20 text-amber-400 border-0">{stats.pendingOrders}</Badge>
              )}
            </TabsTrigger>
            <TabsTrigger 
              value="invoices"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
            >
              <FileText className="w-4 h-4 mr-2" />
              Factures
            </TabsTrigger>
            <TabsTrigger 
              value="wallet"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg"
            >
              <Wallet className="w-4 h-4 mr-2" />
              Wallet
            </TabsTrigger>
          </TabsList>

          {/* ===== DASHBOARD TAB ===== */}
          <TabsContent value="dashboard" className="space-y-6">
            {/* KPIs */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <Card className="bg-white/[0.04] border-white/[0.08]">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-white/50">Commandes totales</p>
                    <Package className="w-4 h-4 text-[#D9B35A]" />
                  </div>
                  <p className="text-2xl font-bold text-white">{stats.totalOrders}</p>
                </CardContent>
              </Card>

              <Card className="bg-white/[0.04] border-white/[0.08]">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-white/50">En cours</p>
                    <Clock className="w-4 h-4 text-amber-400" />
                  </div>
                  <p className="text-2xl font-bold text-amber-400">{stats.pendingOrders}</p>
                </CardContent>
              </Card>

              <Card className="bg-white/[0.04] border-white/[0.08]">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-white/50">Total dépensé</p>
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                  </div>
                  <p className="text-2xl font-bold text-emerald-400">{formatCurrency(stats.totalSpent)}</p>
                </CardContent>
              </Card>

              <Card className="bg-white/[0.04] border-white/[0.08]">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-white/50">Crédits O'SCOP</p>
                    <Wallet className="w-4 h-4 text-purple-400" />
                  </div>
                  <p className="text-2xl font-bold text-purple-400">{formatCurrency(stats.creditsBalance)}</p>
                </CardContent>
              </Card>
            </div>

            {/* Recent Orders */}
            <Card className="bg-white/[0.04] border-white/[0.08]">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white flex items-center gap-2">
                    <Package className="w-5 h-5 text-[#D9B35A]" />
                    Commandes récentes
                  </CardTitle>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setActiveTab('orders')}
                    className="text-white/60 hover:text-white"
                  >
                    Voir tout <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {orders.length === 0 ? (
                  <div className="text-center py-8 text-white/50">
                    <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Aucune commande</p>
                    <Link to="/catalogue">
                      <Button className="mt-4 bg-[#D9B35A] hover:bg-[#c9a34a] text-black">
                        Commander
                      </Button>
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {orders.slice(0, 5).map(order => {
                      const status = ORDER_STATUS[order.status] || ORDER_STATUS.PENDING;
                      const StatusIcon = status.icon;
                      return (
                        <div 
                          key={order.id}
                          className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between hover:bg-white/[0.04] transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${status.color.split(' ')[0]}`}>
                              <StatusIcon className={`w-4 h-4 ${status.color.split(' ')[1]}`} />
                            </div>
                            <div>
                              <p className="font-medium text-white/90 text-sm">{order.order_number}</p>
                              <p className="text-xs text-white/50">{formatShortDate(order.created_at)} · {order.items_count} article(s)</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <Badge variant="outline" className={status.color}>{status.label}</Badge>
                            <p className="text-sm font-semibold text-[#D9B35A] mt-1">{formatCurrency(order.total_ttc_cents)} TTC</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <div className="grid sm:grid-cols-3 gap-4">
              <Link to="/catalogue">
                <Card className="bg-gradient-to-br from-[#D9B35A]/10 to-[#D9B35A]/5 border-[#D9B35A]/20 hover:border-[#D9B35A]/40 transition-colors cursor-pointer">
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-[#D9B35A]/20 flex items-center justify-center">
                      <Package className="w-6 h-6 text-[#D9B35A]" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">Nouvelle commande</p>
                      <p className="text-xs text-white/60">Accéder au catalogue</p>
                    </div>
                  </CardContent>
                </Card>
              </Link>

              <Link to="/wallet">
                <Card className="bg-gradient-to-br from-purple-500/10 to-purple-500/5 border-purple-500/20 hover:border-purple-500/40 transition-colors cursor-pointer">
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center">
                      <Wallet className="w-6 h-6 text-purple-400" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">Recharger crédits</p>
                      <p className="text-xs text-white/60">Gérer mon wallet</p>
                    </div>
                  </CardContent>
                </Card>
              </Link>

              <Link to="/legal">
                <Card className="bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border-emerald-500/20 hover:border-emerald-500/40 transition-colors cursor-pointer">
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                      <FileText className="w-6 h-6 text-emerald-400" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">Documents légaux</p>
                      <p className="text-xs text-white/60">CGV, Contrats</p>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </div>
          </TabsContent>

          {/* ===== ORDERS TAB ===== */}
          <TabsContent value="orders" className="space-y-6">
            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <Input
                  placeholder="Rechercher par numéro..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 bg-white/[0.04] border-white/10 text-white"
                />
              </div>
              <Select value={orderStatusFilter} onValueChange={setOrderStatusFilter}>
                <SelectTrigger className="w-[180px] bg-white/[0.04] border-white/10">
                  <Filter className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les statuts</SelectItem>
                  <SelectItem value="PENDING">En attente</SelectItem>
                  <SelectItem value="CONFIRMED">Confirmée</SelectItem>
                  <SelectItem value="PROCESSING">En préparation</SelectItem>
                  <SelectItem value="READY_FOR_PICKUP">Prête à enlever</SelectItem>
                  <SelectItem value="COMPLETED">Terminée</SelectItem>
                  <SelectItem value="CANCELED">Annulée</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Orders List */}
            {filteredOrders.length === 0 ? (
              <div className="text-center py-16 text-white/50">
                <Package className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg">Aucune commande trouvée</p>
                <p className="text-sm mb-4">Modifiez vos filtres ou passez une commande</p>
                <Link to="/catalogue">
                  <Button className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black">
                    Voir le catalogue
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredOrders.map(order => {
                  const status = ORDER_STATUS[order.status] || ORDER_STATUS.PENDING;
                  const StatusIcon = status.icon;
                  
                  return (
                    <Card key={order.id} className="bg-white/[0.04] border-white/[0.08] overflow-hidden">
                      <CardContent className="p-0">
                        <div className="p-4">
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${status.color.split(' ')[0]}`}>
                                <StatusIcon className={`w-5 h-5 ${status.color.split(' ')[1]}`} />
                              </div>
                              <div>
                                <p className="font-semibold text-white">{order.order_number}</p>
                                <p className="text-xs text-white/50">
                                  {formatDate(order.created_at)}
                                  {order.is_installment && (
                                    <span className="ml-2 text-purple-400">· Paiement 4×</span>
                                  )}
                                </p>
                              </div>
                            </div>
                            <Badge variant="outline" className={status.color}>{status.label}</Badge>
                          </div>

                          {/* Order Items Preview */}
                          <div className="space-y-2 mb-4">
                            {order.items?.slice(0, 3).map((item, idx) => (
                              <div key={idx} className="flex justify-between items-center text-sm p-2 rounded-lg bg-white/[0.02]">
                                <span className="text-white/80">{item.product_name}</span>
                                <span className="text-white/50">{item.quantity} × {formatCurrency(item.unit_price_ht_cents)}</span>
                              </div>
                            ))}
                            {(order.items?.length || 0) > 3 && (
                              <p className="text-xs text-white/40 text-center">+ {order.items.length - 3} autres articles</p>
                            )}
                          </div>

                          {/* Pickup Location */}
                          {order.pickup_location && (
                            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 mb-4">
                              <div className="flex items-center gap-2 text-emerald-400">
                                <MapPin className="w-4 h-4" />
                                <span className="text-sm font-medium">Point de retrait EXW</span>
                              </div>
                              <p className="text-sm text-white/70 mt-1">{order.pickup_location.name} - {order.pickup_location.city}</p>
                            </div>
                          )}

                          {/* Totals */}
                          <div className="flex items-center justify-between pt-3 border-t border-white/[0.06]">
                            <div className="text-sm">
                              <span className="text-white/50">Total HT : </span>
                              <span className="text-white/80">{formatCurrency(order.subtotal_ht_cents)}</span>
                            </div>
                            <div>
                              <span className="text-white/50 text-sm">Total TTC : </span>
                              <span className="text-xl font-bold text-[#D9B35A]">{formatCurrency(order.total_ttc_cents)}</span>
                            </div>
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="px-4 py-3 bg-white/[0.02] border-t border-white/[0.06] flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Button variant="ghost" size="sm" className="text-white/60 hover:text-white">
                              <Eye className="w-4 h-4 mr-2" />
                              Détails
                            </Button>
                            <Link to={`/bon-de-commande?order=${order.id}`}>
                              <Button variant="ghost" size="sm" className="text-white/60 hover:text-white">
                                <FileText className="w-4 h-4 mr-2" />
                                Bon de commande
                              </Button>
                            </Link>
                          </div>
                          {order.status === 'COMPLETED' && (
                            <Button variant="ghost" size="sm" className="text-emerald-400 hover:text-emerald-300">
                              <Download className="w-4 h-4 mr-2" />
                              Facture
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>

          {/* ===== INVOICES TAB ===== */}
          <TabsContent value="invoices" className="space-y-6">
            {/* Invoice Stats */}
            {invoiceStats && (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="bg-white/[0.04] border-white/[0.08]">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-white/50">Total factures</p>
                      <FileText className="w-4 h-4 text-[#D9B35A]" />
                    </div>
                    <p className="text-2xl font-bold text-white">{invoiceStats.total_invoices}</p>
                  </CardContent>
                </Card>

                <Card className="bg-white/[0.04] border-white/[0.08]">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-white/50">Payées</p>
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    </div>
                    <p className="text-2xl font-bold text-emerald-400">{invoiceStats.total_paid}</p>
                  </CardContent>
                </Card>

                <Card className="bg-white/[0.04] border-white/[0.08]">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-white/50">En attente</p>
                      <Clock className="w-4 h-4 text-amber-400" />
                    </div>
                    <p className="text-2xl font-bold text-amber-400">{invoiceStats.total_pending}</p>
                  </CardContent>
                </Card>

                <Card className="bg-white/[0.04] border-white/[0.08]">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-white/50">Montant total</p>
                      <Euro className="w-4 h-4 text-purple-400" />
                    </div>
                    <p className="text-2xl font-bold text-purple-400">{formatCurrency(invoiceStats.total_amount_cents)}</p>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <Input
                  placeholder="Rechercher par numéro de facture..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 bg-white/[0.04] border-white/10 text-white"
                  data-testid="invoice-search-input"
                />
              </div>
              <Select value={invoiceStatusFilter} onValueChange={setInvoiceStatusFilter}>
                <SelectTrigger className="w-[180px] bg-white/[0.04] border-white/10" data-testid="invoice-status-filter">
                  <Filter className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les statuts</SelectItem>
                  <SelectItem value="PENDING">En attente</SelectItem>
                  <SelectItem value="PAID">Payée</SelectItem>
                  <SelectItem value="PARTIAL">Partiel</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Invoices List */}
            <Card className="bg-white/[0.04] border-white/[0.08]">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Receipt className="w-5 h-5 text-[#D9B35A]" />
                  Factures
                </CardTitle>
                <CardDescription className="text-white/60">
                  Historique de vos factures et documents comptables
                </CardDescription>
              </CardHeader>
              <CardContent>
                {filteredInvoices.length === 0 ? (
                  <div className="text-center py-12 text-white/50" data-testid="no-invoices">
                    <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">Aucune facture disponible</p>
                    <p className="text-sm">Les factures sont générées après validation des commandes</p>
                  </div>
                ) : (
                  <div className="space-y-3" data-testid="invoices-list">
                    {filteredInvoices.map(invoice => {
                      const isPaid = invoice.payment_status === 'PAID';
                      const isPending = invoice.payment_status === 'PENDING';
                      
                      return (
                        <div 
                          key={invoice.id}
                          className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.04] transition-colors"
                          data-testid={`invoice-item-${invoice.id}`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                                isPaid ? 'bg-emerald-500/20' : 'bg-amber-500/20'
                              }`}>
                                {isPaid ? (
                                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                                ) : (
                                  <Clock className="w-5 h-5 text-amber-400" />
                                )}
                              </div>
                              <div>
                                <p className="font-semibold text-white">{invoice.invoice_number}</p>
                                <p className="text-xs text-white/50">
                                  Commande {invoice.order_number} · {formatDate(invoice.issue_date)}
                                </p>
                              </div>
                            </div>
                            <Badge 
                              variant="outline" 
                              className={isPaid 
                                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' 
                                : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                              }
                            >
                              {isPaid ? 'Payée' : 'En attente'}
                            </Badge>
                          </div>
                          
                          {/* Invoice Details */}
                          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                            <div>
                              <p className="text-white/50">Montant HT</p>
                              <p className="text-white/90">{formatCurrency(invoice.subtotal_ht_cents)}</p>
                            </div>
                            <div>
                              <p className="text-white/50">TVA ({(invoice.tax_rate * 100).toFixed(1)}%)</p>
                              <p className="text-white/90">{formatCurrency(invoice.tax_cents)}</p>
                            </div>
                            {invoice.total_fees_cents > 0 && (
                              <div>
                                <p className="text-white/50">Frais</p>
                                <p className="text-white/90">{formatCurrency(invoice.total_fees_cents)}</p>
                              </div>
                            )}
                            <div>
                              <p className="text-white/50">Total TTC</p>
                              <p className="font-bold text-[#D9B35A]">{formatCurrency(invoice.total_ttc_cents)}</p>
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between">
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="text-white/60 hover:text-white"
                              onClick={() => viewInvoiceDetails(invoice)}
                              data-testid={`view-invoice-${invoice.id}`}
                            >
                              <Eye className="w-4 h-4 mr-2" />
                              Détails
                            </Button>
                            <Button 
                              variant="outline" 
                              size="sm" 
                              className="border-white/10"
                              onClick={() => downloadInvoicePDF(invoice)}
                              data-testid={`download-invoice-${invoice.id}`}
                            >
                              <Download className="w-4 h-4 mr-2" />
                              Télécharger PDF
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* ===== WALLET TAB ===== */}
          <TabsContent value="wallet" className="space-y-6">
            {/* Balance Card */}
            <Card className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 border-purple-500/30">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white/60 mb-1">Solde disponible</p>
                    <p className="text-4xl font-bold text-white" data-testid="wallet-balance">
                      {formatCurrency(wallet?.balance_cents || wallet?.balance_credits * 100 || 0)}
                    </p>
                    <p className="text-sm text-white/50 mt-2">
                      Crédits O'SCOP pour vos commandes
                    </p>
                  </div>
                  <div className="w-16 h-16 rounded-2xl bg-white/10 flex items-center justify-center">
                    <Wallet className="w-8 h-8 text-purple-400" />
                  </div>
                </div>
                <div className="mt-6 flex gap-3">
                  <Link to="/wallet" className="flex-1">
                    <Button className="w-full bg-purple-600 hover:bg-purple-700 text-white" data-testid="topup-wallet-btn">
                      <CreditCard className="w-4 h-4 mr-2" />
                      Recharger
                    </Button>
                  </Link>
                  <Button variant="outline" className="border-white/20 text-white/80" data-testid="wallet-history-btn">
                    <Calendar className="w-4 h-4 mr-2" />
                    Historique
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Recent Transactions */}
            <Card className="bg-white/[0.04] border-white/[0.08]">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-purple-400" />
                  Transactions récentes
                </CardTitle>
              </CardHeader>
              <CardContent>
                {transactions.length === 0 ? (
                  <div className="text-center py-8 text-white/50" data-testid="no-transactions">
                    <Wallet className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Aucune transaction</p>
                    <p className="text-sm mt-2">Vos transactions apparaîtront ici</p>
                  </div>
                ) : (
                  <div className="space-y-3" data-testid="transactions-list">
                    {transactions.slice(0, 10).map((tx, idx) => {
                      // Determine transaction type based on direction or type
                      const isCredit = tx.direction === 'CREDIT' || tx.type === 'CREDIT_PURCHASE' || tx.type === 'REFUND';
                      const txLabel = tx.reason_code || tx.type || 'Transaction';
                      const txDescription = tx.description || tx.correlation_id || formatShortDate(tx.created_at);
                      const txAmount = tx.amount_credits * 100 || tx.amount_cents || tx.amount || 0;
                      
                      return (
                        <div 
                          key={tx.id || idx}
                          className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between"
                          data-testid={`transaction-${tx.id || idx}`}
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                              isCredit ? 'bg-emerald-500/20' : 'bg-orange-500/20'
                            }`}>
                              {isCredit ? (
                                <ArrowUpRight className="w-4 h-4 text-emerald-400" />
                              ) : (
                                <ArrowDownRight className="w-4 h-4 text-orange-400" />
                              )}
                            </div>
                            <div>
                              <p className="font-medium text-white/90 text-sm">
                                {txLabel.replace(/_/g, ' ')}
                              </p>
                              <p className="text-xs text-white/50">{txDescription}</p>
                            </div>
                          </div>
                          <p className={`font-semibold ${isCredit ? 'text-emerald-400' : 'text-orange-400'}`}>
                            {isCredit ? '+' : '-'}{formatCurrency(Math.abs(txAmount))}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Order Details Modal */}
      <Dialog open={orderModalOpen} onOpenChange={setOrderModalOpen}>
        <DialogContent className="bg-[#0c0f15] border-white/10 text-white max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="w-5 h-5 text-[#D9B35A]" />
              Détails de la commande
            </DialogTitle>
          </DialogHeader>
          
          {selectedOrder && (
            <div className="space-y-4">
              {/* Order Header */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-bold text-lg">{selectedOrder.order_number}</p>
                    <p className="text-sm text-white/50">{formatDate(selectedOrder.created_at)}</p>
                  </div>
                  <Badge variant="outline" className={ORDER_STATUS[selectedOrder.status]?.color || ''}>
                    {ORDER_STATUS[selectedOrder.status]?.label || selectedOrder.status}
                  </Badge>
                </div>
              </div>

              {/* Items */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <ShoppingBag className="w-4 h-4 text-[#D9B35A]" />
                  Articles ({selectedOrder.items?.length || 0})
                </h4>
                <div className="space-y-2">
                  {selectedOrder.items?.map((item, idx) => (
                    <div key={idx} className="flex justify-between items-center py-2 border-b border-white/[0.06] last:border-0">
                      <div>
                        <p className="text-sm font-medium text-white/90">{item.product_name}</p>
                        <p className="text-xs text-white/50">SKU: {item.product_sku}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm">{item.quantity} × {formatCurrency(item.price_ht_cents || item.unit_price_ht_cents)}</p>
                        <p className="text-xs text-white/50">{formatCurrency(item.line_total_ht_cents)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Pickup Location */}
              {selectedOrder.pickup_location && (
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                  <h4 className="font-semibold mb-2 flex items-center gap-2 text-emerald-400">
                    <MapPin className="w-4 h-4" />
                    Point de retrait EXW
                  </h4>
                  <p className="text-sm">{selectedOrder.pickup_location.name}</p>
                  <p className="text-xs text-white/60">{selectedOrder.pickup_location.address}, {selectedOrder.pickup_location.city}</p>
                </div>
              )}

              {/* Totals */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">Sous-total HT</span>
                    <span>{formatCurrency(selectedOrder.subtotal_ht_cents)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">TVA (8,5%)</span>
                    <span>{formatCurrency(selectedOrder.tax_cents)}</span>
                  </div>
                  {selectedOrder.is_installment && selectedOrder.installment_plan && (
                    <div className="flex justify-between text-sm text-purple-400">
                      <span>Frais paiement 4×</span>
                      <span>+{formatCurrency(selectedOrder.installment_plan.total_fees_cents)}</span>
                    </div>
                  )}
                  <div className="flex justify-between font-bold text-lg pt-2 border-t border-white/[0.06]">
                    <span>Total TTC</span>
                    <span className="text-[#D9B35A]">{formatCurrency(selectedOrder.total_ttc_cents)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setOrderModalOpen(false)} className="border-white/10">
              Fermer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Invoice Details Modal */}
      <Dialog open={invoiceModalOpen} onOpenChange={setInvoiceModalOpen}>
        <DialogContent className="bg-[#0c0f15] border-white/10 text-white max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Receipt className="w-5 h-5 text-[#D9B35A]" />
              Détails de la facture
            </DialogTitle>
          </DialogHeader>
          
          {selectedInvoice && (
            <div className="space-y-4">
              {/* Invoice Header */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-bold text-lg">{selectedInvoice.invoice_number}</p>
                    <p className="text-sm text-white/50">Commande: {selectedInvoice.order_number}</p>
                    <p className="text-xs text-white/40">Émise le {formatDate(selectedInvoice.issue_date)}</p>
                  </div>
                  <Badge 
                    variant="outline" 
                    className={selectedInvoice.payment_status === 'PAID'
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' 
                      : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                    }
                  >
                    {selectedInvoice.payment_status === 'PAID' ? 'Payée' : 'En attente'}
                  </Badge>
                </div>
              </div>

              {/* Invoice Items */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[#D9B35A]" />
                  Lignes de facturation ({selectedInvoice.items_count})
                </h4>
                <div className="space-y-2">
                  {selectedInvoice.items?.map((item, idx) => (
                    <div key={idx} className="flex justify-between items-center py-2 border-b border-white/[0.06] last:border-0">
                      <div>
                        <p className="text-sm font-medium text-white/90">{item.product_name}</p>
                        <p className="text-xs text-white/50">{item.quantity} {item.unit}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm">{formatCurrency(item.unit_price_ht_cents)} × {item.quantity}</p>
                        <p className="text-xs text-white/50">{formatCurrency(item.line_total_ht_cents)} HT</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Totals */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">Sous-total HT</span>
                    <span>{formatCurrency(selectedInvoice.subtotal_ht_cents)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/60">TVA ({(selectedInvoice.tax_rate * 100).toFixed(1)}%)</span>
                    <span>{formatCurrency(selectedInvoice.tax_cents)}</span>
                  </div>
                  {selectedInvoice.total_fees_cents > 0 && (
                    <>
                      <div className="flex justify-between text-sm text-purple-400">
                        <span>Frais HT</span>
                        <span>{formatCurrency(selectedInvoice.fees_ht_cents)}</span>
                      </div>
                      <div className="flex justify-between text-sm text-purple-400">
                        <span>TVA sur frais</span>
                        <span>{formatCurrency(selectedInvoice.fees_tax_cents)}</span>
                      </div>
                    </>
                  )}
                  <div className="flex justify-between font-bold text-lg pt-2 border-t border-white/[0.06]">
                    <span>Total TTC</span>
                    <span className="text-[#D9B35A]">{formatCurrency(selectedInvoice.total_ttc_cents)}</span>
                  </div>
                  {selectedInvoice.payment_status === 'PENDING' && (
                    <div className="flex justify-between text-sm text-amber-400 pt-2">
                      <span>Reste à payer</span>
                      <span>{formatCurrency(selectedInvoice.balance_due_cents)}</span>
                    </div>
                  )}
                  {selectedInvoice.paid_at && (
                    <div className="flex justify-between text-sm text-emerald-400 pt-2">
                      <span>Payée le</span>
                      <span>{formatDate(selectedInvoice.paid_at)}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Metadata */}
              <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-white/50">Zone</p>
                    <p className="text-white/90">{selectedInvoice.zone_code}</p>
                  </div>
                  <div>
                    <p className="text-white/50">Incoterm</p>
                    <p className="text-white/90">{selectedInvoice.incoterm}</p>
                  </div>
                  {selectedInvoice.payment_method && (
                    <div>
                      <p className="text-white/50">Mode de paiement</p>
                      <p className="text-white/90">{selectedInvoice.payment_method}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          
          <DialogFooter className="gap-2">
            <Button 
              variant="outline" 
              onClick={() => downloadInvoicePDF(selectedInvoice)} 
              className="border-white/10"
            >
              <Download className="w-4 h-4 mr-2" />
              Télécharger PDF
            </Button>
            <Button variant="outline" onClick={() => setInvoiceModalOpen(false)} className="border-white/10">
              Fermer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
