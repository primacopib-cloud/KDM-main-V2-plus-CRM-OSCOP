import React, { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  ShoppingCart, Plus, Minus, Trash2, ArrowLeft, Package, Search,
  Play, Save, RefreshCw, Calendar, Edit2
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import { toast } from 'sonner';
import { frequencyLabels } from '../components/shopping-lists/shoppingListConstants';

const API_URL = process.env.REACT_APP_BACKEND_URL;

function formatPrice(cents) {
  if (!cents) return '—';
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR'
  }).format(cents / 100);
}

export default function ShoppingListDetailPage() {
  const { listId } = useParams();
  const navigate = useNavigate();
  const [list, setList] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddProducts, setShowAddProducts] = useState(false);
  const [availableProducts, setAvailableProducts] = useState([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productSearch, setProductSearch] = useState('');

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    };
  };

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/shopping-lists/${listId}`, {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' }
      });

      if (res.ok) {
        const data = await res.json();
        setList(data);
      } else if (res.status === 404) {
        toast.error('Liste non trouvée');
        navigate('/listes-achats');
      }
    } catch (error) {
      console.error('Error fetching list:', error);
    } finally {
      setLoading(false);
    }
  }, [listId, navigate]);

  const fetchAvailableProducts = useCallback(async () => {
    setProductsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({ page_size: '50', zone_code: 'GUADELOUPE' });
      if (productSearch.trim()) {
        params.append('search', productSearch.trim());
      }
      
      const res = await fetch(`${API_URL}/api/v2/catalog/products?${params}`, {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' }
      });

      if (res.ok) {
        const data = await res.json();
        setAvailableProducts(data || []);
      }
    } catch (error) {
      console.error('Error fetching products:', error);
    } finally {
      setProductsLoading(false);
    }
  }, [productSearch]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  useEffect(() => {
    if (showAddProducts) {
      fetchAvailableProducts();
    }
  }, [showAddProducts, fetchAvailableProducts]);

  const handleUpdateQuantity = async (productId, delta) => {
    const item = list.items.find(i => i.product_id === productId);
    if (!item) return;

    const newQty = Math.max(1, item.quantity + delta);

    try {
      const res = await fetch(`${API_URL}/api/shopping-lists/${listId}/items/${productId}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ quantity: newQty })
      });

      if (res.ok) {
        const updated = await res.json();
        setList(updated);
      }
    } catch (error) {
      console.error('Error updating quantity:', error);
    }
  };

  const handleRemoveItem = async (productId) => {
    try {
      const res = await fetch(`${API_URL}/api/shopping-lists/${listId}/items/${productId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (res.ok) {
        setList(prev => ({
          ...prev,
          items: prev.items.filter(i => i.product_id !== productId),
          items_count: prev.items_count - 1
        }));
        toast.info('Produit retiré de la liste');
      }
    } catch (error) {
      console.error('Error removing item:', error);
    }
  };

  const handleAddProduct = async (product) => {
    try {
      const res = await fetch(`${API_URL}/api/shopping-lists/${listId}/items`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          product_id: product.id,
          quantity: 1
        })
      });

      if (res.ok) {
        const updated = await res.json();
        setList(updated);
        toast.success(`${product.name} ajouté à la liste`, { icon: '✓' });
      }
    } catch (error) {
      console.error('Error adding product:', error);
    }
  };

  const handleUseList = async () => {
    try {
      const res = await fetch(`${API_URL}/api/shopping-lists/${listId}/use`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (res.ok) {
        const data = await res.json();
        setList(prev => ({
          ...prev,
          use_count: (prev.use_count || 0) + 1,
          last_used_at: new Date().toISOString()
        }));
        toast.success(`${data.items_count} produit(s) prêts à être ajoutés au panier`, {
          icon: '🛒'
        });
      }
    } catch (error) {
      console.error('Error using list:', error);
    }
  };

  // Filter items by search
  const filteredItems = list?.items?.filter(item => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      item.product_name?.toLowerCase().includes(query) ||
      item.product_sku?.toLowerCase().includes(query)
    );
  }) || [];

  // Filter available products (exclude already in list)
  const existingProductIds = new Set(list?.items?.map(i => i.product_id) || []);
  const filteredAvailableProducts = availableProducts.filter(
    p => !existingProductIds.has(p.id)
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-[#070A10] text-white">
        <NavBar />
        <main className="pt-24 pb-16">
          <div className="max-w-4xl mx-auto px-4 py-20 text-center">
            <div className="w-10 h-10 border-2 border-[#D9B35A] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-white/50">Chargement de la liste...</p>
          </div>
        </main>
      </div>
    );
  }

  if (!list) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#070A10] text-white">
      <NavBar />

      <main className="pt-24 pb-16">
        <div className="max-w-4xl mx-auto px-4 lg:px-6">
          {/* Header */}
          <div className="flex items-start gap-4 mb-8">
            <Link
              to="/listes-achats"
              className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] transition-colors mt-1"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <div 
                  className="w-3 h-8 rounded-full"
                  style={{ backgroundColor: list.color }}
                />
                <h1 className="text-2xl font-bold">{list.name}</h1>
              </div>
              {list.description && (
                <p className="text-white/60 mb-2">{list.description}</p>
              )}
              <div className="flex items-center gap-3 flex-wrap">
                <Badge variant="outline" className="border-white/20">
                  <Calendar className="w-3 h-3 mr-1" />
                  {frequencyLabels[list.frequency]}
                </Badge>
                <span className="text-sm text-white/50">
                  {list.items_count} produit{list.items_count !== 1 ? 's' : ''} • 
                  {list.use_count || 0} utilisation{(list.use_count || 0) !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={() => setShowAddProducts(true)}
                variant="outline"
                className="border-white/20"
              >
                <Plus className="w-4 h-4 mr-2" />
                Ajouter
              </Button>
              <Button
                onClick={handleUseList}
                className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
                disabled={list.items_count === 0}
              >
                <Play className="w-4 h-4 mr-2" />
                Utiliser
              </Button>
            </div>
          </div>

          {/* Search */}
          {list.items_count > 0 && (
            <div className="mb-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Rechercher dans la liste..."
                  className="pl-10 bg-white/[0.04] border-white/10"
                />
              </div>
            </div>
          )}

          {/* Items List */}
          <div
            className="rounded-2xl overflow-hidden"
            style={{
              background: 'linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            {filteredItems.length === 0 ? (
              <div className="py-16 text-center">
                <Package className="w-12 h-12 text-white/20 mx-auto mb-4" />
                <p className="text-white/50 mb-4">
                  {list.items_count === 0 
                    ? 'Cette liste est vide' 
                    : 'Aucun produit trouvé'
                  }
                </p>
                <Button
                  onClick={() => setShowAddProducts(true)}
                  className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Ajouter des produits
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-white/[0.04]">
                {filteredItems.map((item) => (
                  <div
                    key={item.product_id}
                    className="p-4 flex items-center gap-4 hover:bg-white/[0.02] transition-colors"
                    data-testid={`list-item-${item.product_id}`}
                  >
                    {/* Image */}
                    <div className="w-16 h-16 rounded-lg bg-white/[0.04] flex-shrink-0 overflow-hidden">
                      {item.product_image ? (
                        <img
                          src={item.product_image}
                          alt={item.product_name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Package className="w-6 h-6 text-white/20" />
                        </div>
                      )}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-white/40">{item.product_sku}</p>
                      <h4 className="font-medium truncate">
                        {item.product_name || 'Produit non disponible'}
                      </h4>
                      {item.notes && (
                        <p className="text-xs text-white/50 mt-1">{item.notes}</p>
                      )}
                    </div>

                    {/* Price */}
                    <div className="text-right">
                      <p className="font-bold text-[#D9B35A]">
                        {formatPrice(item.price_ht_cents)}
                      </p>
                      <p className="text-xs text-white/40">HT / unité</p>
                    </div>

                    {/* Quantity */}
                    <div className="flex items-center gap-1 bg-white/[0.04] rounded-lg">
                      <button
                        onClick={() => handleUpdateQuantity(item.product_id, -1)}
                        className="p-2 hover:bg-white/10 rounded-l-lg"
                        disabled={item.quantity <= 1}
                      >
                        <Minus className="w-4 h-4" />
                      </button>
                      <span className="w-10 text-center font-medium">
                        {item.quantity}
                      </span>
                      <button
                        onClick={() => handleUpdateQuantity(item.product_id, 1)}
                        className="p-2 hover:bg-white/10 rounded-r-lg"
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Subtotal */}
                    <div className="text-right w-24">
                      <p className="font-bold">
                        {formatPrice((item.price_ht_cents || 0) * item.quantity)}
                      </p>
                      <p className="text-xs text-white/40">Sous-total</p>
                    </div>

                    {/* Remove */}
                    <button
                      onClick={() => handleRemoveItem(item.product_id)}
                      className="p-2 rounded-lg hover:bg-red-500/20 text-red-400"
                      title="Retirer de la liste"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Total */}
            {list.items_count > 0 && (
              <div className="p-4 border-t border-white/[0.06] flex items-center justify-between">
                <span className="text-white/60">Total HT estimé</span>
                <span className="text-2xl font-bold text-[#D9B35A]">
                  {formatPrice(list.total_ht_cents)}
                </span>
              </div>
            )}
          </div>
        </div>
      </main>

      <Footer />

      {/* Add Products Dialog */}
      <Dialog open={showAddProducts} onOpenChange={setShowAddProducts}>
        <DialogContent className="bg-[#0A0E17] border-white/10 text-white max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Ajouter des produits</DialogTitle>
          </DialogHeader>
          
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
            <Input
              value={productSearch}
              onChange={(e) => setProductSearch(e.target.value)}
              placeholder="Rechercher un produit..."
              className="pl-10 bg-white/[0.04] border-white/10"
            />
          </div>

          {/* Products List */}
          <div className="flex-1 overflow-y-auto space-y-2 min-h-[300px]">
            {productsLoading ? (
              <div className="py-12 text-center">
                <div className="w-8 h-8 border-2 border-[#D9B35A] border-t-transparent rounded-full animate-spin mx-auto" />
              </div>
            ) : filteredAvailableProducts.length === 0 ? (
              <div className="py-12 text-center text-white/50">
                {productSearch ? 'Aucun produit trouvé' : 'Tous les produits sont déjà dans la liste'}
              </div>
            ) : (
              filteredAvailableProducts.map((product) => (
                <div
                  key={product.id}
                  className="p-3 rounded-lg bg-white/[0.04] flex items-center gap-3 hover:bg-white/[0.06] transition-colors"
                >
                  <div className="w-12 h-12 rounded-lg bg-white/[0.04] flex-shrink-0 overflow-hidden">
                    {product.image_url ? (
                      <img
                        src={product.image_url}
                        alt={product.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Package className="w-5 h-5 text-white/20" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-white/40">{product.sku}</p>
                    <p className="font-medium truncate">{product.name}</p>
                  </div>
                  <p className="font-bold text-[#D9B35A]">
                    {formatPrice(product.price_ht_cents)}
                  </p>
                  <Button
                    size="sm"
                    onClick={() => handleAddProduct(product)}
                    className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
                  >
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
              ))
            )}
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowAddProducts(false)}>
              Fermer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
