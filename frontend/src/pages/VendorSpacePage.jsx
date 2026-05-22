import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import {
  Package, Plus, FileText, Upload, CheckCircle2, Clock, XCircle,
  Building2, TrendingUp, ShoppingCart, Eye, Edit, Trash2, Search,
  Filter, RefreshCw, ChevronDown, ImagePlus, FileUp, Flag, AlertCircle, ArrowLeft
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { toast } from 'sonner';
import { BreadcrumbPill } from '../components/Breadcrumb';
import NavigationHistoryDropdown from '../components/NavigationHistoryDropdown';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Demo vendor ID (in production, get from auth)
const DEMO_VENDOR_ID = 'vendor_878ad7936d37';

// Product categories
const CATEGORIES = [
  { value: 'alimentaire', label: 'Alimentaire' },
  { value: 'boissons', label: 'Boissons' },
  { value: 'hygiene', label: 'Hygiène & Beauté' },
  { value: 'entretien', label: 'Entretien' },
  { value: 'fournitures', label: 'Fournitures' },
  { value: 'textile', label: 'Textile' },
  { value: 'equipement', label: 'Équipement' },
  { value: 'autre', label: 'Autre' },
];

// Unit types
const UNIT_TYPES = [
  { value: 'unit', label: 'Unité' },
  { value: 'kg', label: 'Kilogramme' },
  { value: 'liter', label: 'Litre' },
  { value: 'box', label: 'Carton' },
  { value: 'pallet', label: 'Palette' },
];

// Format types
const FORMAT_TYPES = [
  { value: 'standard', label: 'Standard (unité)' },
  { value: 'lot', label: 'Lot / Pack' },
  { value: 'palette', label: 'Palette complète' },
  { value: 'container', label: 'Container' },
];

// TVA rates
const TVA_RATES = [
  { value: 0, label: '0% (Exonéré)' },
  { value: 2.1, label: '2.1% (Super-réduit)' },
  { value: 5.5, label: '5.5% (Réduit)' },
  { value: 8.5, label: '8.5% (DOM)' },
  { value: 10, label: '10% (Intermédiaire)' },
  { value: 20, label: '20% (Normal)' },
];

// Zones
const ZONES = ['GUADELOUPE', 'MARTINIQUE', 'GUYANE', 'REUNION', 'MAYOTTE'];

// Status badge helper
const getStatusBadge = (status) => {
  switch (status) {
    case 'pending_approval':
      return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200"><Clock className="w-3 h-3 mr-1" /> En attente</Badge>;
    case 'approved':
      return <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200"><CheckCircle2 className="w-3 h-3 mr-1" /> Approuvé</Badge>;
    case 'rejected':
      return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200"><XCircle className="w-3 h-3 mr-1" /> Rejeté</Badge>;
    case 'draft':
      return <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200"><Edit className="w-3 h-3 mr-1" /> Brouillon</Badge>;
    case 'inactive':
      return <Badge variant="secondary"><XCircle className="w-3 h-3 mr-1" /> Inactif</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
};

// ===== PRODUCT FORM MODAL =====
const ProductFormModal = ({ isOpen, onClose, onSuccess, vendorId, countries }) => {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    sku: '',
    description: '',
    category: 'alimentaire',
    price_ht: '',
    tva_rate: 8.5,
    stock_quantity: '',
    min_order_quantity: 1,
    unit_type: 'unit',
    volume_per_unit: '',
    weight_per_unit: '',
    format_type: 'standard',
    units_per_lot: '',
    lots_per_palette: '',
    country_of_origin: 'FR',
    region_of_origin: '',
    dlc_days: '',
    ean13: '',
    storage_conditions: '',
    brand: '',
    certifications: [],
    available_zones: ['GUADELOUPE'],
  });

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleZoneToggle = (zone) => {
    setFormData(prev => ({
      ...prev,
      available_zones: prev.available_zones.includes(zone)
        ? prev.available_zones.filter(z => z !== zone)
        : [...prev.available_zones, zone]
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        ...formData,
        price_ht: parseFloat(formData.price_ht),
        tva_rate: parseFloat(formData.tva_rate),
        stock_quantity: parseInt(formData.stock_quantity),
        min_order_quantity: parseInt(formData.min_order_quantity) || 1,
        volume_per_unit: formData.volume_per_unit ? parseFloat(formData.volume_per_unit) : null,
        weight_per_unit: formData.weight_per_unit ? parseFloat(formData.weight_per_unit) : null,
        units_per_lot: formData.units_per_lot ? parseInt(formData.units_per_lot) : null,
        lots_per_palette: formData.lots_per_palette ? parseInt(formData.lots_per_palette) : null,
        dlc_days: formData.dlc_days ? parseInt(formData.dlc_days) : null,
      };

      const response = await fetch(`${API_URL}/api/vendor/products?vendor_id=${vendorId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Erreur lors de la soumission');
      }

      const result = await response.json();
      toast.success('Produit soumis !', {
        description: 'Votre produit est en attente de validation par l\'administrateur.'
      });
      onSuccess(result);
      onClose();
    } catch (error) {
      toast.error('Erreur', { description: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="w-5 h-5 text-purple-600" />
            Soumettre un nouveau produit
          </DialogTitle>
          <DialogDescription>
            Remplissez les informations du produit. Il sera soumis pour validation par l'administrateur.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Info */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <Package className="w-4 h-4" /> Informations de base
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label htmlFor="name">Nom du produit *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  placeholder="Ex: Riz long grain 5kg"
                  required
                  data-testid="product-name"
                />
              </div>
              <div>
                <Label htmlFor="sku">SKU / Référence *</Label>
                <Input
                  id="sku"
                  value={formData.sku}
                  onChange={(e) => handleChange('sku', e.target.value)}
                  placeholder="Ex: ALI-RIZ-001"
                  required
                  data-testid="product-sku"
                />
              </div>
              <div>
                <Label htmlFor="ean13">Code EAN-13</Label>
                <Input
                  id="ean13"
                  value={formData.ean13}
                  onChange={(e) => handleChange('ean13', e.target.value)}
                  placeholder="3700000000000"
                />
              </div>
              <div className="col-span-2">
                <Label htmlFor="description">Description *</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  placeholder="Décrivez votre produit en détail..."
                  rows={3}
                  required
                  data-testid="product-description"
                />
              </div>
              <div>
                <Label htmlFor="category">Catégorie *</Label>
                <Select value={formData.category} onValueChange={(v) => handleChange('category', v)}>
                  <SelectTrigger data-testid="product-category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map(c => (
                      <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="brand">Marque</Label>
                <Input
                  id="brand"
                  value={formData.brand}
                  onChange={(e) => handleChange('brand', e.target.value)}
                  placeholder="Ex: Ma Marque"
                />
              </div>
            </div>
          </div>

          {/* Pricing */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" /> Tarification
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label htmlFor="price_ht">Prix HT (€) *</Label>
                <Input
                  id="price_ht"
                  type="number"
                  step="0.01"
                  min="0"
                  value={formData.price_ht}
                  onChange={(e) => handleChange('price_ht', e.target.value)}
                  placeholder="0.00"
                  required
                  data-testid="product-price"
                />
              </div>
              <div>
                <Label htmlFor="tva_rate">Taux TVA *</Label>
                <Select value={String(formData.tva_rate)} onValueChange={(v) => handleChange('tva_rate', parseFloat(v))}>
                  <SelectTrigger data-testid="product-tva">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TVA_RATES.map(t => (
                      <SelectItem key={t.value} value={String(t.value)}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Prix TTC (calculé)</Label>
                <div className="h-10 px-3 py-2 border rounded-md bg-gray-50 text-gray-700 font-mono">
                  {formData.price_ht 
                    ? (parseFloat(formData.price_ht) * (1 + formData.tva_rate / 100)).toFixed(2) + ' €'
                    : '—'
                  }
                </div>
              </div>
            </div>
          </div>

          {/* Stock & Volume */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <ShoppingCart className="w-4 h-4" /> Stock & Format
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label htmlFor="stock_quantity">Quantité en stock *</Label>
                <Input
                  id="stock_quantity"
                  type="number"
                  min="0"
                  value={formData.stock_quantity}
                  onChange={(e) => handleChange('stock_quantity', e.target.value)}
                  placeholder="100"
                  required
                  data-testid="product-stock"
                />
              </div>
              <div>
                <Label htmlFor="min_order_quantity">Quantité min. commande</Label>
                <Input
                  id="min_order_quantity"
                  type="number"
                  min="1"
                  value={formData.min_order_quantity}
                  onChange={(e) => handleChange('min_order_quantity', e.target.value)}
                  placeholder="1"
                />
              </div>
              <div>
                <Label htmlFor="unit_type">Unité de vente</Label>
                <Select value={formData.unit_type} onValueChange={(v) => handleChange('unit_type', v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {UNIT_TYPES.map(u => (
                      <SelectItem key={u.value} value={u.value}>{u.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="format_type">Format / Conditionnement</Label>
                <Select value={formData.format_type} onValueChange={(v) => handleChange('format_type', v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {FORMAT_TYPES.map(f => (
                      <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="volume_per_unit">Volume (L)</Label>
                <Input
                  id="volume_per_unit"
                  type="number"
                  step="0.01"
                  value={formData.volume_per_unit}
                  onChange={(e) => handleChange('volume_per_unit', e.target.value)}
                  placeholder="Ex: 5"
                />
              </div>
              <div>
                <Label htmlFor="weight_per_unit">Poids (kg)</Label>
                <Input
                  id="weight_per_unit"
                  type="number"
                  step="0.01"
                  value={formData.weight_per_unit}
                  onChange={(e) => handleChange('weight_per_unit', e.target.value)}
                  placeholder="Ex: 5"
                />
              </div>
            </div>
          </div>

          {/* Origin */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <Flag className="w-4 h-4" /> Origine
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="country_of_origin">Pays d'origine *</Label>
                <Select value={formData.country_of_origin} onValueChange={(v) => handleChange('country_of_origin', v)}>
                  <SelectTrigger data-testid="product-origin">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {countries.map(c => (
                      <SelectItem key={c.code} value={c.code}>
                        {c.flag} {c.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="region_of_origin">Région (optionnel)</Label>
                <Input
                  id="region_of_origin"
                  value={formData.region_of_origin}
                  onChange={(e) => handleChange('region_of_origin', e.target.value)}
                  placeholder="Ex: Bretagne"
                />
              </div>
            </div>
          </div>

          {/* DLC & Storage */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <Clock className="w-4 h-4" /> Conservation
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="dlc_days">DLC (jours)</Label>
                <Input
                  id="dlc_days"
                  type="number"
                  min="0"
                  value={formData.dlc_days}
                  onChange={(e) => handleChange('dlc_days', e.target.value)}
                  placeholder="Ex: 365"
                />
              </div>
              <div>
                <Label htmlFor="storage_conditions">Conditions de stockage</Label>
                <Input
                  id="storage_conditions"
                  value={formData.storage_conditions}
                  onChange={(e) => handleChange('storage_conditions', e.target.value)}
                  placeholder="Ex: Conserver au frais"
                />
              </div>
            </div>
          </div>

          {/* Zones */}
          <div className="space-y-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              Zones de disponibilité *
            </h3>
            <div className="flex flex-wrap gap-2">
              {ZONES.map(zone => (
                <Button
                  key={zone}
                  type="button"
                  variant={formData.available_zones.includes(zone) ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleZoneToggle(zone)}
                  className={formData.available_zones.includes(zone) ? "bg-purple-600 hover:bg-purple-700" : ""}
                >
                  {zone}
                </Button>
              ))}
            </div>
            {formData.available_zones.length === 0 && (
              <p className="text-sm text-red-500">Sélectionnez au moins une zone</p>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Annuler
            </Button>
            <Button 
              type="submit" 
              disabled={loading || formData.available_zones.length === 0}
              className="bg-purple-600 hover:bg-purple-700"
              data-testid="submit-product"
            >
              {loading ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Plus className="w-4 h-4 mr-2" />
              )}
              Soumettre pour validation
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

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
  const fetchDashboard = async () => {
    try {
      const response = await fetch(`${API_URL}/api/vendor/dashboard/${vendorId}`);
      if (response.ok) {
        const data = await response.json();
        setDashboard(data);
      }
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    }
  };

  // Fetch products
  const fetchProducts = async () => {
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
  };

  // Fetch countries
  const fetchCountries = async () => {
    try {
      const response = await fetch(`${API_URL}/api/vendor/countries`);
      if (response.ok) {
        const data = await response.json();
        setCountries(data.countries || []);
      }
    } catch (error) {
      console.error('Error fetching countries:', error);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchDashboard(), fetchProducts(), fetchCountries()]);
      setLoading(false);
    };
    loadData();
    // Fetchers are stable closures over `statusFilter`; including them as deps would loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

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
                  <CardDescription>Chiffre d'affaires</CardDescription>
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
