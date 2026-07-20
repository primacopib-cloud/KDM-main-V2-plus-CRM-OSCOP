import i18n from '@/i18n';
import React, { useState, useEffect } from 'react';
import {
  Package, CheckCircle2, XCircle, Clock, Eye, Search, Filter,
  RefreshCw, Building2, AlertTriangle, Flag, ChevronDown,
  ThumbsUp, ThumbsDown, MessageSquare
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Status badge helper
import { getStatusBadge, ProductDetailModal } from '../components/admin/ProductDetailModal';

const AdminProductsPage = () => {
  const [loading, setLoading] = useState(true);
  const [products, setProducts] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [stats, setStats] = useState({});
  const [activeTab, setActiveTab] = useState('pending');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Fetch pending products
  const fetchProducts = async (status = 'pending_approval') => {
    try {
      const url = `${API_URL}/api/vendor/admin/products/pending?status=${status}`;
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        setProducts(data.products || []);
        setStats(prev => ({ ...prev, [status]: data.total || 0 }));
      }
    } catch (error) {
      console.error('Error fetching products:', error);
    }
  };

  // Fetch vendors
  const fetchVendors = async () => {
    try {
      const response = await fetch(`${API_URL}/api/vendor/admin/list`);
      if (response.ok) {
        const data = await response.json();
        setVendors(data.vendors || []);
      }
    } catch (error) {
      console.error('Error fetching vendors:', error);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchProducts('pending_approval'),
        fetchVendors()
      ]);
      setLoading(false);
    };
    loadData();
  }, []);

  useEffect(() => {
    const statusMap = {
      'pending': 'pending_approval',
      'approved': 'approved',
      'rejected': 'rejected'
    };
    fetchProducts(statusMap[activeTab] || 'pending_approval');
  }, [activeTab]);

  // Approve product
  const handleApprove = async (productId) => {
    try {
      const response = await fetch(`${API_URL}/api/vendor/admin/products/${productId}/approve`, {
        method: 'POST'
      });
      if (response.ok) {
        toast.success(i18n.t('adm.produit_approuve'));
        fetchProducts('pending_approval');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Erreur lors de l\'approbation');
      }
    } catch (error) {
      toast.error(i18n.t('adm.erreur_de_connexion'));
    }
  };

  // Reject product
  const handleReject = async (productId, reason) => {
    try {
      const response = await fetch(`${API_URL}/api/vendor/admin/products/${productId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      });
      if (response.ok) {
        toast.success(i18n.t('adm.produit_rejete'));
        fetchProducts('pending_approval');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Erreur lors du rejet');
      }
    } catch (error) {
      toast.error(i18n.t('adm.erreur_de_connexion'));
    }
  };

  // Filter products
  const filteredProducts = products.filter(p =>
    p.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.sku?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.vendor_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatCurrency = (amount) =>
    new Intl.NumberFormat(i18n.language, { style: 'currency', currency: 'EUR' }).format(amount || 0);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }}>
        <RefreshCw className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  const pendingCount = vendors.reduce((sum, v) => sum + (v.products?.pending || 0), 0) || products.filter(p => p.status === 'pending_approval').length;

  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }} data-testid="admin-products">
      {/* Header */}
      <header className="sticky top-0 z-50" style={{ background: '#1E0C34', borderBottom: '1px solid rgba(212,175,55,0.32)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
                <Package className="w-6 h-6 text-[#1A092D]" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">{i18n.t('adm.validation_des_produits')}</h1>
                <p className="text-sm text-white/55">{i18n.t('adm.administration_kdmarche')}</p>
              </div>
            </div>
            
            {pendingCount > 0 && (
              <Badge className="text-base px-4 py-2 border" style={{ background: 'rgba(217,179,90,0.14)', color: '#E9CF8E', borderColor: 'rgba(217,179,90,0.4)' }}>
                <AlertTriangle className="w-5 h-5 mr-2" />
                {i18n.t('adm.en_attente_count', { count: pendingCount })}
              </Badge>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: i18n.t('adm.en_attente'), value: stats.pending_approval || pendingCount || 0, color: '#E9CF8E', onClick: () => setActiveTab('pending') },
            { label: i18n.t('adm.approuves_total'), value: vendors.reduce((sum, v) => sum + (v.products?.approved || 0), 0), color: '#7BC94E' },
            { label: i18n.t('adm.vendeurs_actifs'), value: vendors.filter(v => v.status === 'approved').length, color: '#7AB7FF' },
            { label: i18n.t('adm.total_vendeurs'), value: vendors.length, color: '#D9B35A' },
          ].map((s) => (
            <div key={s.label} onClick={s.onClick}
              className={`rounded-2xl p-5 border border-white/10 ${s.onClick ? 'cursor-pointer hover:border-[#D9B35A]/40 transition-colors' : ''}`}
              style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03))' }}>
              <p className="text-sm text-white/60 mb-1">{s.label}</p>
              <p className="text-3xl font-black" style={{ color: s.color }}>{s.value}</p>
            </div>
          ))}
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <TabsList className="border border-white/12" style={{ background: 'rgba(255,255,255,0.05)' }}>
              <TabsTrigger value="pending" className="gap-2 text-white/65 data-[state=active]:bg-[#D9B35A] data-[state=active]:text-[#1A092D] data-[state=active]:font-semibold">
                <Clock className="w-4 h-4" /> {i18n.t('adm.en_attente')}
              </TabsTrigger>
              <TabsTrigger value="approved" className="gap-2 text-white/65 data-[state=active]:bg-[#D9B35A] data-[state=active]:text-[#1A092D] data-[state=active]:font-semibold">
                <CheckCircle2 className="w-4 h-4" /> {i18n.t('adm.approuves')}
              </TabsTrigger>
              <TabsTrigger value="rejected" className="gap-2 text-white/65 data-[state=active]:bg-[#D9B35A] data-[state=active]:text-[#1A092D] data-[state=active]:font-semibold">
                <XCircle className="w-4 h-4" /> {i18n.t('adm.rejetes')}
              </TabsTrigger>
            </TabsList>

            <div className="flex gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-white/40" />
                <Input
                  placeholder={i18n.t('adm.rechercher')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 w-64 bg-white/[0.05] border-white/15 text-white placeholder:text-white/35 focus-visible:ring-[#D9B35A]/30"
                />
              </div>
              <Button variant="outline" className="border-white/15 bg-white/[0.05] text-white/70 hover:bg-white/10 hover:text-white"
                onClick={() => fetchProducts(activeTab === 'pending' ? 'pending_approval' : activeTab)}>
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Products List */}
          <TabsContent value={activeTab} className="space-y-4">
            {filteredProducts.length > 0 ? (
              <div className="space-y-4">
                {filteredProducts.map((product) => (
                  <div key={product.id} className="rounded-2xl border border-white/10 hover:border-[#D9B35A]/35 transition-colors"
                    style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03))' }}>
                    <div className="p-4">
                      <div className="flex items-start gap-4">
                        <div className="w-16 h-16 rounded-lg flex items-center justify-center flex-shrink-0 bg-white/[0.06] border border-white/10">
                          {product.images?.[0] ? (
                            <img src={product.images[0].url} alt={product.name} className="w-full h-full object-cover rounded-lg" />
                          ) : (
                            <Package className="w-8 h-8 text-white/30" />
                          )}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <h3 className="font-semibold text-white">{product.name}</h3>
                              <p className="text-sm text-white/50">SKU: {product.sku}</p>
                            </div>
                            {getStatusBadge(product.status)}
                          </div>

                          <div className="flex flex-wrap gap-4 mt-2 text-sm">
                            <span className="font-bold text-[#E9CF8E]">
                              {formatCurrency(product.price_ht)} HT
                            </span>
                            <span className="text-white/55">
                              {i18n.t('adm.tva')}: {product.tva_rate}%
                            </span>
                            <span className="text-white/55">
                              Stock: {product.stock_quantity}
                            </span>
                            <span className="text-white/55 flex items-center gap-1">
                              {product.country_flag} {product.country_name}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 mt-2 text-sm">
                            <Building2 className="w-3 h-3 text-white/40" />
                            <span className="text-white/70">{product.vendor_name || 'N/A'}</span>
                          </div>

                          {product.rejection_reason && (
                            <div className="mt-2 p-2 rounded text-sm border" style={{ background: 'rgba(255,87,87,0.12)', color: '#FF9D9D', borderColor: 'rgba(255,87,87,0.3)' }}>
                              <strong>{i18n.t('adm.motif')}</strong> {product.rejection_reason}
                            </div>
                          )}
                        </div>

                        <div className="flex flex-col gap-2">
                          <Button 
                            variant="outline" 
                            size="sm"
                            className="border-white/15 bg-white/[0.05] text-white/80 hover:bg-white/10 hover:text-white"
                            onClick={() => {
                              setSelectedProduct(product);
                              setIsDetailOpen(true);
                            }}
                          >
                            <Eye className="w-4 h-4 mr-1" /> {i18n.t('adm.details')}
                          </Button>
                          
                          {product.status === 'pending_approval' && (
                            <>
                              <Button 
                                size="sm"
                                className="font-semibold hover:opacity-90"
                                style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)', color: '#1A092D' }}
                                onClick={() => handleApprove(product.id)}
                              >
                                <CheckCircle2 className="w-4 h-4 mr-1" /> {i18n.t('adm.approuver')}
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-white/10 py-12 text-center"
                style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))' }}>
                <Package className="w-12 h-12 mx-auto text-white/20 mb-4" />
                <h3 className="text-lg font-medium text-white mb-2">
                  {activeTab === 'pending' ? i18n.t('adm.aucun_produit_en_attente') :
                   activeTab === 'approved' ? i18n.t('adm.aucun_produit_approuve') :
                   i18n.t('adm.aucun_produit_rejete')}
                </h3>
                <p className="text-white/50">
                  {activeTab === 'pending' && i18n.t('adm.tous_les_produits_traites')}
                </p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* Product Detail Modal */}
      <ProductDetailModal
        product={selectedProduct}
        isOpen={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false);
          setSelectedProduct(null);
        }}
        onApprove={handleApprove}
        onReject={handleReject}
      />
    </div>
  );
};

export default AdminProductsPage;
