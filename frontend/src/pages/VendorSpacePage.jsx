import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Package, Plus, CheckCircle2, Building2, TrendingUp, ShoppingCart,
  Eye, Edit, Search, RefreshCw, AlertCircle, ArrowLeft, Filter,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { toast } from 'sonner';
import { BreadcrumbPill } from '../components/Breadcrumb';
import NavigationHistoryDropdown from '../components/NavigationHistoryDropdown';
import { getStatusBadge } from '../components/vendor/vendorConstants';
import { VendorProductFormModal as ProductFormModal } from '../components/vendor/VendorProductFormModal';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Demo vendor ID — points to the seeded "Distillerie Damoiseau" vendor pro.
// Login : vendor-pro@kdmarche.fr / Demo2026!
// In production, this should come from auth (user.vendor_id).
const DEMO_VENDOR_ID = 'vendor-demo-pro';

// ===== MAIN VENDOR SPACE PAGE =====
const VendorSpacePage = () => {
  const navigate = useNavigate();
  const [vendorId] = useState(DEMO_VENDOR_ID);
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [products, setProducts] = useState([]);
  const [countries, setCountries] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isFormOpen, setIsFormOpen] = useState(false);

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

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchDashboard(), fetchProducts(), fetchCountries()]);
      setLoading(false);
    };
    loadData();
  }, [fetchDashboard, fetchProducts, fetchCountries]);

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
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(amount || 0);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <RefreshCw className="w-8 h-8 animate-spin text-purple-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100" data-testid="vendor-space">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/" className="text-gray-400 hover:text-gray-600 transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-600 to-purple-700 flex items-center justify-center">
                <Building2 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Espace Vendeur</h1>
                <p className="text-sm text-gray-500">{dashboard?.company_name || 'Mon Entreprise'}</p>
              </div>
            </div>
            
            {/* Quick Navigation */}
            <nav className="hidden md:flex items-center gap-1 mr-4">
              <Link to="/" className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors">
                Accueil
              </Link>
              <Link to="/espace-acheteur" className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors">
                Espace Acheteur
              </Link>
              <Link to="/catalogue" className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors">
                Catalogue
              </Link>
              <Link to="/superadmin" className="px-3 py-1.5 text-xs text-purple-600 hover:bg-purple-50 rounded-lg transition-colors">
                Admin
              </Link>
            </nav>
            
            <div className="flex items-center gap-3">
              {/* Navigation History */}
              <NavigationHistoryDropdown variant="light" />
              
              <Button 
                onClick={() => setIsFormOpen(true)}
                className="gap-2 bg-purple-600 hover:bg-purple-700"
                data-testid="add-product-btn"
              >
                <Plus className="w-4 h-4" />
                <span className="hidden sm:inline">Nouveau produit</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Breadcrumb */}
        <div className="mb-6">
          <BreadcrumbPill className="bg-white border border-gray-200" />
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-white border">
            <TabsTrigger value="dashboard" className="gap-2">
              <TrendingUp className="w-4 h-4" /> Tableau de bord
            </TabsTrigger>
            <TabsTrigger value="products" className="gap-2">
              <Package className="w-4 h-4" /> Mes produits
            </TabsTrigger>
            <TabsTrigger value="orders" className="gap-2">
              <ShoppingCart className="w-4 h-4" /> Commandes
            </TabsTrigger>
          </TabsList>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard" className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Produits actifs</CardDescription>
                  <CardTitle className="text-3xl text-purple-600">
                    {dashboard?.products?.approved || 0}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-500">
                    sur {dashboard?.products?.total || 0} soumis
                  </p>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>En attente</CardDescription>
                  <CardTitle className="text-3xl text-amber-600">
                    {dashboard?.products?.pending || 0}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-500">produits à valider</p>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Chiffre d&apos;affaires</CardDescription>
                  <CardTitle className="text-3xl text-emerald-600">
                    {formatCurrency(dashboard?.sales?.total_revenue || 0)}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-500">total HT</p>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription>Commandes</CardDescription>
                  <CardTitle className="text-3xl text-blue-600">
                    {dashboard?.sales?.order_count || 0}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-500">total</p>
                </CardContent>
              </Card>
            </div>

            {/* Recent Orders */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Commandes récentes</CardTitle>
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
                  <p className="text-gray-500 text-center py-8">Aucune commande récente</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Products Tab */}
          <TabsContent value="products" className="space-y-6">
            {/* Filters */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-wrap gap-4 items-center">
                  <div className="flex-1 min-w-[200px]">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <Input
                        placeholder="Rechercher un produit..."
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
                      <SelectItem value="all">Tous les statuts</SelectItem>
                      <SelectItem value="pending_approval">En attente</SelectItem>
                      <SelectItem value="approved">Approuvés</SelectItem>
                      <SelectItem value="rejected">Rejetés</SelectItem>
                      <SelectItem value="inactive">Inactifs</SelectItem>
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
                        <div className="w-20 h-20 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                          {product.images?.[0] ? (
                            <img src={product.images[0].url} alt={product.name} className="w-full h-full object-cover rounded-lg" />
                          ) : (
                            <Package className="w-8 h-8 text-gray-400" />
                          )}
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <h3 className="font-semibold text-gray-900 truncate">{product.name}</h3>
                              <p className="text-sm text-gray-500">SKU: {product.sku}</p>
                            </div>
                            {getStatusBadge(product.status)}
                          </div>
                          
                          <div className="flex flex-wrap gap-4 mt-2 text-sm">
                            <span className="text-gray-600">
                              <strong>{formatCurrency(product.price_ht)}</strong> HT
                            </span>
                            <span className="text-gray-500">
                              Stock: {product.stock_quantity}
                            </span>
                            <span className="text-gray-500">
                              {product.country_flag} {product.country_name}
                            </span>
                            <span className="text-gray-500">
                              TVA: {product.tva_rate}%
                            </span>
                          </div>
                          
                          {product.rejection_reason && (
                            <div className="mt-2 p-2 bg-red-50 rounded text-sm text-red-700">
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
                        </div>
                        
                        <div className="flex flex-col gap-2">
                          <Button variant="outline" size="sm" className="gap-1">
                            <Eye className="w-3 h-3" /> Voir
                          </Button>
                          {product.status !== 'pending_approval' && (
                            <Button variant="outline" size="sm" className="gap-1">
                              <Edit className="w-3 h-3" /> Modifier
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <Card>
                <CardContent className="py-12 text-center">
                  <Package className="w-12 h-12 mx-auto text-gray-300 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Aucun produit</h3>
                  <p className="text-gray-500 mb-4">Commencez par ajouter votre premier produit</p>
                  <Button onClick={() => setIsFormOpen(true)} className="bg-purple-600 hover:bg-purple-700">
                    <Plus className="w-4 h-4 mr-2" />
                    Ajouter un produit
                  </Button>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Orders Tab */}
          <TabsContent value="orders">
            <Card>
              <CardContent className="py-12 text-center">
                <ShoppingCart className="w-12 h-12 mx-auto text-gray-300 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Commandes</h3>
                <p className="text-gray-500">Les commandes de vos produits apparaîtront ici</p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Product Form Modal */}
      <ProductFormModal
        isOpen={isFormOpen}
        onClose={() => setIsFormOpen(false)}
        onSuccess={handleProductSuccess}
        vendorId={vendorId}
        countries={countries}
      />
    </div>
  );
};

export default VendorSpacePage;
