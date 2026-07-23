import i18n from '@/i18n';
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import {
  Package, Plus, CheckCircle2, Building2, TrendingUp, ShoppingCart,
  Search, RefreshCw, AlertCircle, ArrowLeft, Filter, Coins, FileSignature, FileText, Ticket,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Card, CardContent } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { toast } from 'sonner';
import { BreadcrumbPill } from '../components/Breadcrumb';
import { VendorProductAssistant } from '../components/VendorProductAssistant';
import NavigationHistoryDropdown from '../components/NavigationHistoryDropdown';
import { getStatusBadge } from '../components/vendor/vendorConstants';
import { VendorProductFormModal as ProductFormModal } from '../components/vendor/VendorProductFormModal';
import { VendorProductViewModal } from '../components/vendor/VendorProductViewModal';
import { AIStudioModal } from '../components/vendor/AIStudioModal';
import { ProductActions } from '../components/vendor/ProductActions';
import { ProductContractBadge } from '../components/vendor/ProductContractBadge';
import { VendorDashboardTab } from '../components/vendor/VendorDashboardTab';
import { VendorInvoicesTab } from '../components/vendor/VendorInvoicesTab';
import { VendorCpcTab } from '../components/vendor/VendorCpcTab';
import { VendorConsultationsTab } from '../components/vendor/VendorConsultationsTab';
import { CreditPacksModal } from '../components/vendor/CreditPacksModal';
import { VendorContractsTab } from '../components/vendor/VendorContractsTab';
import { VendorConventionCard } from '../components/vendor/VendorConventionCard';
import { VendorSuspendedNotice } from '../components/vendor/VendorSuspendedNotice';
import { MemberSpaceBanners } from '../components/MemberSpaceBanners';
import { MessagesNavLink } from '../components/MessagesNavLink';
import { useCreditSessionPoll } from '../components/vendor/useCreditSessionPoll';
import { BrandLogos } from '../components/BrandLogos';
import { NotificationsBell } from '../components/NotificationsBell';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Demo vendor ID — points to the seeded "Distillerie Damoiseau" vendor pro.
// Login : vendor-pro@kdmarche.fr / Demo2026!
// In production, this should come from auth (user.vendor_id).
const DEMO_VENDOR_ID = 'vendor-demo-pro';

// ===== MAIN VENDOR SPACE PAGE =====
const VendorSpacePage = () => {
  const navigate = useNavigate();
  const [vendorId, setVendorId] = useState(null);
  const [suspension, setSuspension] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/vendor-onboarding/my-vendor`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : {}))
      .then((d) => setVendorId(d.vendor_id || DEMO_VENDOR_ID))
      .catch(() => setVendorId(DEMO_VENDOR_ID));
    fetch(`${API_URL}/api/vendor-onboarding/my-subscription`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then(setSuspension)
      .catch(() => {});
  }, []);
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [products, setProducts] = useState([]);
  const [countries, setCountries] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [viewProduct, setViewProduct] = useState(null);
  const [editProduct, setEditProduct] = useState(null);
  const [aiProduct, setAiProduct] = useState(null);
  const [credits, setCredits] = useState(null);
  const [creditsModalOpen, setCreditsModalOpen] = useState(false);
  const [contractsByProduct, setContractsByProduct] = useState({});
  const [rechargeParams] = useSearchParams();

  useEffect(() => {
    if (!vendorId) return;
    fetch(`${API_URL}/api/vendor/contracts/${vendorId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        const map = {};
        (d?.contracts || []).forEach((c) => { if (c.product_id) map[c.product_id] = c; });
        setContractsByProduct(map);
      }).catch(() => {});
  }, [vendorId]);

  useEffect(() => {
    if (rechargeParams.get('recharge') === '1') setCreditsModalOpen(true);
    const t = rechargeParams.get('tab');
    if (t) setActiveTab(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch dashboard data
  const fetchDashboard = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/vendor/dashboard/${vendorId}`);
      if (response.ok) {
        const data = await response.json();
        setDashboard(data);
      }
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    }
  }, [vendorId]);

  // Fetch products
  const fetchProducts = useCallback(async () => {
    try {
      const url = statusFilter === 'all'
        ? `${API_URL}/api/vendor/products/${vendorId}`
        : `${API_URL}/api/vendor/products/${vendorId}?status=${statusFilter}`;

      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        setProducts(data.products || []);
      }
    } catch (error) {
      console.error('Error fetching products:', error);
    }
  }, [vendorId, statusFilter]);

  // Fetch countries
  const fetchCountries = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/vendor/countries`);
      if (response.ok) {
        const data = await response.json();
        setCountries(data.countries || []);
      }
    } catch (error) {
      console.error('Error fetching countries:', error);
    }
  }, []);

  const fetchCredits = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}/api/vendor/credits/${vendorId}`);
      if (r.ok) setCredits((await r.json()).credits);
    } catch (_e) { /* silent */ }
  }, [vendorId]);

  useEffect(() => {
    if (!vendorId) return;
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchDashboard(), fetchProducts(), fetchCountries(), fetchCredits()]);
      setLoading(false);
    };
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vendorId, statusFilter]);

  useCreditSessionPoll(fetchCredits);

  const handleProductSuccess = () => {
    fetchDashboard();
    fetchProducts();
  };

  // Filter products by search
  const filteredProducts = products.filter(p => 
    p.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.sku?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat(i18n.language, { style: 'currency', currency: 'EUR' }).format(amount || 0);
  };

  if (suspension?.suspended) {
    return <VendorSuspendedNotice info={suspension} />;
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(160deg, #241040 0%, #3A1B5E 100%)' }}>
        <RefreshCw className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(160deg, #241040 0%, #3A1B5E 100%)' }} data-testid="vendor-space">
      <MemberSpaceBanners space="vendor" />
      <VendorProductAssistant />
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-white/10" style={{ background: 'rgba(31,10,51,0.92)', backdropFilter: 'blur(12px)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/" className="text-white/40 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <BrandLogos />
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-600 to-purple-700 flex items-center justify-center border border-[#D9B35A]/30">
                <Building2 className="w-6 h-6 text-[#E9CF8E]" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">{i18n.t('adm.espace_vendeur')}</h1>
                <p className="text-sm text-white/50">{dashboard?.company_name || 'Mon Entreprise'}</p>
              </div>
            </div>
            
            {/* Quick Navigation */}
            <nav className="hidden md:flex items-center gap-1 mr-4">
              <Link to="/" className="px-3 py-1.5 text-xs text-white/55 hover:text-white hover:bg-white/10 rounded-lg transition-colors">
                {i18n.t('nav.home')}
              </Link>
              <Link to="/espace-acheteur" className="px-3 py-1.5 text-xs text-white/55 hover:text-white hover:bg-white/10 rounded-lg transition-colors">
                {i18n.t('breadcrumb.espace_acheteur')}
              </Link>
              <Link to="/catalogue" className="px-3 py-1.5 text-xs text-white/55 hover:text-white hover:bg-white/10 rounded-lg transition-colors">
                {i18n.t('nav.catalog')}
              </Link>
              <Link to="/superadmin" className="px-3 py-1.5 text-xs text-[#E9CF8E] hover:bg-white/10 rounded-lg transition-colors">
                Admin
              </Link>
            </nav>
            
            <div className="flex items-center gap-3">
              {/* Messagerie interne */}
              <MessagesNavLink />

              {/* Navigation History */}
              <NavigationHistoryDropdown />

              {credits !== null && (
                <button
                  type="button"
                  onClick={() => setCreditsModalOpen(true)}
                  className="inline-flex items-center gap-1.5 h-9 px-3 rounded-full text-sm font-semibold hover:brightness-95 transition-all"
                  style={{ color: '#E9CF8E', background: '#D9B35A1c', border: '1px solid #D9B35A55' }}
                  data-testid="vendor-credits-balance"
                  title="Mon CREDI'SCOP — crédits IA : cliquez pour recharger et voir l'historique"
                >
                  <Coins className="w-4 h-4" /> {credits}
                  <span className="hidden lg:inline text-[10px] font-bold tracking-wide">CREDI&rsquo;SCOP</span>
                  <Plus className="w-3 h-3 opacity-60" />
                </button>
              )}
              <Link to="/mon-crediscop" data-testid="crediscop-nav-badge"
                title="Mon relevé CREDI'SCOP unifié (crédits IA + consultations)"
                className="inline-flex items-center gap-1 h-9 px-3 rounded-full text-[10px] font-bold tracking-wide hover:brightness-95 transition-all"
                style={{ color: '#E9CF8E', background: '#D9B35A1c', border: '1px solid #D9B35A55' }}>
                <FileText className="w-3.5 h-3.5" /> RELEVÉ
              </Link>
              <span className="[&_svg]:!text-white/70 [&_button:hover]:!bg-white/10"><NotificationsBell /></span>

              <Button 
                onClick={() => setIsFormOpen(true)}
                className="gap-2 bg-[#D9B35A] hover:bg-[#c9a34a] text-[#1F0A33] font-semibold"
                data-testid="add-product-btn"
              >
                <Plus className="w-4 h-4" />
                <span className="hidden sm:inline">{i18n.t('adm.nouveau_produit')}</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Breadcrumb */}
        <div className="mb-6">
          <BreadcrumbPill className="bg-white/10 border border-white/15" />
        </div>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-white/[0.06] border border-white/10">
            <TabsTrigger value="dashboard" className="gap-2">
              <TrendingUp className="w-4 h-4" /> {i18n.t('buyer.tableau_de_bord')}
            </TabsTrigger>
            <TabsTrigger value="products" className="gap-2">
              <Package className="w-4 h-4" /> {i18n.t('adm.mes_produits')}
            </TabsTrigger>
            <TabsTrigger value="orders" className="gap-2">
              <ShoppingCart className="w-4 h-4" /> {i18n.t('adm.commandes')}
            </TabsTrigger>
            <TabsTrigger value="contracts" className="gap-2" data-testid="vendor-tab-contracts">
              <FileSignature className="w-4 h-4" /> Contrats
            </TabsTrigger>
            <TabsTrigger value="invoices" className="gap-2" data-testid="vendor-tab-invoices">
              <FileText className="w-4 h-4" /> Mes factures
            </TabsTrigger>
            <TabsTrigger value="cpc" className="gap-2" data-testid="vendor-tab-cpc">
              <Ticket className="w-4 h-4" /> CREDI'SCOP
            </TabsTrigger>
            <TabsTrigger value="consultations" className="gap-2" data-testid="vendor-tab-consultations">
              <TrendingUp className="w-4 h-4" /> Consultations
            </TabsTrigger>
          </TabsList>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard">
            <VendorDashboardTab dashboard={dashboard} vendorId={vendorId} formatCurrency={formatCurrency} />
          </TabsContent>

          {/* Products Tab */}
          <TabsContent value="products" className="space-y-6">
            {/* Filters */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-wrap gap-4 items-center">
                  <div className="flex-1 min-w-[200px]">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-white/40" />
                      <Input
                        placeholder={i18n.t('adm.rechercher_un_produit')}
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-[180px]">
                      <Filter className="w-4 h-4 mr-2" />
                      <SelectValue placeholder="Statut" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">{i18n.t('adm.tous_les_statuts')}</SelectItem>
                      <SelectItem value="pending_approval">{i18n.t('adm.en_attente')}</SelectItem>
                      <SelectItem value="approved">{i18n.t('adm.approuves')}</SelectItem>
                      <SelectItem value="rejected">{i18n.t('adm.rejetes')}</SelectItem>
                      <SelectItem value="inactive">{i18n.t('adm.inactifs')}</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button variant="outline" onClick={fetchProducts}>
                    <RefreshCw className="w-4 h-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Products List */}
            {filteredProducts.length > 0 ? (
              <div className="grid gap-4">
                {filteredProducts.map((product) => (
                  <Card key={product.id} className="hover:shadow-md transition-shadow">
                    <CardContent className="p-4">
                      <div className="flex items-start gap-4">
                        {/* Image placeholder */}
                        <div className="w-20 h-20 bg-white/[0.06] rounded-lg flex items-center justify-center flex-shrink-0">
                          {product.images?.[0] ? (
                            <img src={product.images[0].url} alt={product.name} className="w-full h-full object-cover rounded-lg" />
                          ) : (
                            <Package className="w-8 h-8 text-white/25" />
                          )}
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <h3 className="font-semibold text-white truncate">{product.name}</h3>
                              <p className="text-sm text-white/45">SKU: {product.sku}</p>
                            </div>
                            {getStatusBadge(product.status)}
                          </div>
                          
                          <div className="flex flex-wrap gap-4 mt-2 text-sm">
                            <span className="text-white/70">
                              <strong>{formatCurrency(product.price_ht)}</strong> HT
                            </span>
                            <span className="text-white/50">
                              Stock: {product.stock_quantity}
                            </span>
                            <span className="text-white/50">
                              {product.country_flag} {product.country_name}
                            </span>
                            <span className="text-white/50">
                              TVA: {product.tva_rate}%
                            </span>
                          </div>
                          
                          {product.rejection_reason && (
                            <div className="mt-2 p-2 bg-red-500/15 border border-red-500/25 rounded text-sm text-red-300">
                              <AlertCircle className="w-4 h-4 inline mr-1" />
                              Motif de rejet: {product.rejection_reason}
                            </div>
                          )}
                          
                          <div className="flex flex-wrap gap-1 mt-2">
                            {product.available_zones?.map(zone => (
                              <Badge key={zone} variant="secondary" className="text-xs">
                                {zone}
                              </Badge>
                            ))}
                          </div>

                          <ProductContractBadge contract={contractsByProduct[product.id]} vendorId={vendorId} />
                        </div>
                        
                        <ProductActions
                          product={product} vendorId={vendorId}
                          onView={() => setViewProduct(product)}
                          onEdit={() => { setEditProduct(product); setIsFormOpen(true); }}
                          onAI={() => setAiProduct(product)}
                        />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <Card>
                <CardContent className="py-12 text-center">
                  <Package className="w-12 h-12 mx-auto text-white/20 mb-4" />
                  <h3 className="text-lg font-medium text-white mb-2">{i18n.t('adm.aucun_produit')}</h3>
                  <p className="text-white/50 mb-4">{i18n.t('adm.commencez_par_ajouter_votre_premier')}</p>
                  <Button onClick={() => setIsFormOpen(true)} className="bg-[#D9B35A] hover:bg-[#c9a34a] text-[#1F0A33] font-semibold">
                    <Plus className="w-4 h-4 mr-2" />
                    Ajouter un produit
                  </Button>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Orders Tab */}
          <TabsContent value="orders">
            <Card><CardContent className="py-12 text-center"><ShoppingCart className="w-12 h-12 mx-auto text-white/20 mb-4" /><h3 className="text-lg font-medium text-white mb-2">{i18n.t('adm.commandes')}</h3><p className="text-white/50">{i18n.t('adm.les_commandes_de_vos_produits')}</p></CardContent></Card>
          </TabsContent>

          {/* Contracts Tab */}
          <TabsContent value="contracts">
            <VendorConventionCard vendorId={vendorId} />
            <VendorContractsTab vendorId={vendorId} />
          </TabsContent>

          {/* Invoices Tab */}
          <TabsContent value="invoices">
            <VendorInvoicesTab />
          </TabsContent>

          {/* CPC Tab */}
          <TabsContent value="cpc">
            <VendorCpcTab />
          </TabsContent>

          {/* Consultations Tab */}
          <TabsContent value="consultations">
            <VendorConsultationsTab />
          </TabsContent>
        </Tabs>
      </main>
      {/* Product Form Modal (création + édition) */}
      <ProductFormModal
        isOpen={isFormOpen}
        onClose={() => { setIsFormOpen(false); setEditProduct(null); }}
        onSuccess={handleProductSuccess}
        vendorId={vendorId}
        countries={countries}
        editProduct={editProduct}
      />

      {viewProduct && (
        <VendorProductViewModal product={viewProduct} vendorId={vendorId} onClose={() => setViewProduct(null)} />
      )}

      {aiProduct && (
        <AIStudioModal
          product={aiProduct} vendorId={vendorId}
          onClose={() => { setAiProduct(null); fetchCredits(); }}
          onMediaAdded={() => { fetchProducts(); fetchCredits(); }}
        />
      )}

      {creditsModalOpen && (
        <CreditPacksModal vendorId={vendorId} onClose={() => { setCreditsModalOpen(false); fetchCredits(); }} />
      )}
    </div>
  );
};

export default VendorSpacePage;
