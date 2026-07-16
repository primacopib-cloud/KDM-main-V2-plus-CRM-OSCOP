import i18n from '@/i18n';
import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Heart, ShoppingCart, Trash2, ArrowLeft, RefreshCw, 
  Package, Search, Grid, List, Plus, Minus
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';
import { useFavorites } from '../components/FavoriteButton';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

function formatPrice(cents) {
  if (!cents) return '—';
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR'
  }).format(cents / 100);
}

export default function FavoritesPage() {
  const navigate = useNavigate();
  const { clearAllFavorites, refreshFavorites } = useFavorites();
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState('grid'); // grid or list
  const [quantities, setQuantities] = useState({});

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    };
  };

  const fetchFavorites = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/user-prefs/favorites?include_details=true`, {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' }
      });

      if (res.ok) {
        const data = await res.json();
        setFavorites(data.favorites || []);
        // Initialize quantities
        const initQty = {};
        data.favorites?.forEach(f => {
          initQty[f.product_id] = 1;
        });
        setQuantities(initQty);
      }
    } catch (error) {
      console.error('Error fetching favorites:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchFavorites();
  }, [fetchFavorites]);

  const handleRemoveFavorite = async (productId, productName) => {
    try {
      const res = await fetch(`${API_URL}/api/user-prefs/favorites/${productId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (res.ok) {
        setFavorites(prev => prev.filter(f => f.product_id !== productId));
        refreshFavorites();
        toast.info(i18n.t('favorites.toast_retire', { name: productName || i18n.t('favorites.produit') }));
      }
    } catch (error) {
      console.error('Error removing favorite:', error);
      toast.error('Erreur lors de la suppression');
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm(i18n.t('favorites.confirm_vider'))) return;
    await clearAllFavorites();
    setFavorites([]);
  };

  const handleAddToCart = (product) => {
    const qty = quantities[product.product_id] || 1;
    // This would integrate with your cart system
    toast.success(i18n.t('favorites.toast_ajoute', { qty, name: product.product_name }), {
      icon: '🛒'
    });
  };

  const handleAddAllToCart = () => {
    const itemsToAdd = favorites.filter(f => f.product_name);
    if (itemsToAdd.length === 0) return;
    
    toast.success(i18n.t('favorites.toast_ajoutes', { count: itemsToAdd.length }), {
      icon: '🛒'
    });
  };

  const updateQuantity = (productId, delta) => {
    setQuantities(prev => ({
      ...prev,
      [productId]: Math.max(1, (prev[productId] || 1) + delta)
    }));
  };

  // Filter favorites by search
  const filteredFavorites = favorites.filter(f => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      f.product_name?.toLowerCase().includes(query) ||
      f.product_sku?.toLowerCase().includes(query)
    );
  });

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString(i18n.language, {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  return (
    <div className="min-h-screen bg-[#070A10] text-white">
      <NavBar />

      <main className="pt-24 pb-16">
        <div className="max-w-6xl mx-auto px-4 lg:px-6">
          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
            <Link
              to="/catalogue"
              className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex-1">
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <Heart className="w-7 h-7 text-red-500 fill-red-500" />
                {i18n.t('favorites.mes_favoris')}
              </h1>
              <p className="text-white/60">
                {i18n.t('favorites.count', { count: favorites.length })}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => fetchFavorites(true)}
              disabled={refreshing}
              className="text-white/60"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              {i18n.t('favorites.actualiser')}
            </Button>
          </div>

          {/* Actions Bar */}
          {favorites.length > 0 && (
            <div
              className="p-4 rounded-2xl mb-6"
              style={{
                background: 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))',
                border: '1px solid rgba(255,255,255,0.08)'
              }}
            >
              <div className="flex flex-col lg:flex-row gap-4 items-center">
                {/* Search */}
                <div className="relative flex-1 w-full">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={i18n.t('favorites.rechercher_dans_mes_favoris')}
                    className="pl-10 bg-white/[0.04] border-white/10"
                    data-testid="favorites-search"
                  />
                </div>

                {/* View Mode Toggle */}
                <div className="flex items-center gap-1 p-1 bg-white/[0.04] rounded-lg">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-2 rounded ${viewMode === 'grid' ? 'bg-white/10' : ''}`}
                  >
                    <Grid className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`p-2 rounded ${viewMode === 'list' ? 'bg-white/10' : ''}`}
                  >
                    <List className="w-4 h-4" />
                  </button>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <Button
                    onClick={handleAddAllToCart}
                    className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
                  >
                    <ShoppingCart className="w-4 h-4 mr-2" />
                    {i18n.t('favorites.tout_ajouter_au_panier')}
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={handleClearAll}
                    className="text-red-400 hover:text-red-300"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    {i18n.t('favorites.vider')}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Content */}
          {loading ? (
            <div className="py-20 text-center">
              <div className="w-10 h-10 border-2 border-[#D9B35A] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-white/50">{i18n.t('favorites.chargement_de_vos_favoris')}</p>
            </div>
          ) : favorites.length === 0 ? (
            <div
              className="py-20 text-center rounded-2xl"
              style={{
                background: 'linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))',
                border: '1px solid rgba(255,255,255,0.08)'
              }}
            >
              <Heart className="w-16 h-16 text-white/20 mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">{i18n.t('favorites.aucun_favori')}</h2>
              <p className="text-white/50 mb-6">
                {i18n.t('favorites.vous_n_avez_pas')}
              </p>
              <Button
                onClick={() => navigate('/catalogue')}
                className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
              >
                <Package className="w-4 h-4 mr-2" />
                {i18n.t('favorites.parcourir_le_catalogue')}
              </Button>
            </div>
          ) : filteredFavorites.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-white/50">{i18n.t('favorites.aucun_resultat', { query: searchQuery })}</p>
              <Button
                variant="ghost"
                onClick={() => setSearchQuery('')}
                className="mt-4"
              >
                {i18n.t('favorites.effacer_la_recherche')}
              </Button>
            </div>
          ) : viewMode === 'grid' ? (
            /* Grid View */
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredFavorites.map((fav) => (
                <div
                  key={fav.product_id}
                  className="group rounded-xl overflow-hidden transition-all hover:ring-1 hover:ring-white/20"
                  style={{
                    background: 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))',
                    border: '1px solid rgba(255,255,255,0.08)'
                  }}
                  data-testid={`favorite-card-${fav.product_id}`}
                >
                  {/* Image */}
                  <div className="relative aspect-square bg-white/[0.02]">
                    {fav.product_image ? (
                      <img
                        src={fav.product_image}
                        alt={fav.product_name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Package className="w-12 h-12 text-white/20" />
                      </div>
                    )}
                    {/* Remove button */}
                    <button
                      onClick={() => handleRemoveFavorite(fav.product_id, fav.product_name)}
                      className="absolute top-2 right-2 p-2 rounded-full bg-black/50 hover:bg-red-500/80 transition-colors opacity-0 group-hover:opacity-100"
                      title={i18n.t('favorites.retirer_des_favoris')}
                    >
                      <Heart className="w-4 h-4 fill-red-500 text-red-500" />
                    </button>
                  </div>

                  {/* Info */}
                  <div className="p-4">
                    <p className="text-xs text-white/40 mb-1">{fav.product_sku}</p>
                    <h3 className="font-medium line-clamp-2 mb-2">
                      {fav.product_name || 'Produit non disponible'}
                    </h3>
                    
                    {fav.product_price_ht && (
                      <p className="text-lg font-bold text-[#D9B35A] mb-3">
                        {formatPrice(fav.product_price_ht)} HT
                      </p>
                    )}

                    {/* Quantity & Add to Cart */}
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1 bg-white/[0.04] rounded-lg">
                        <button
                          onClick={() => updateQuantity(fav.product_id, -1)}
                          className="p-1.5 hover:bg-white/10 rounded-l-lg"
                        >
                          <Minus className="w-3 h-3" />
                        </button>
                        <span className="w-8 text-center text-sm">
                          {quantities[fav.product_id] || 1}
                        </span>
                        <button
                          onClick={() => updateQuantity(fav.product_id, 1)}
                          className="p-1.5 hover:bg-white/10 rounded-r-lg"
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => handleAddToCart(fav)}
                        className="flex-1 bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
                        disabled={!fav.product_name}
                      >
                        <ShoppingCart className="w-3 h-3 mr-1" />
                        {i18n.t('favorites.ajouter')}
                      </Button>
                    </div>

                    <p className="text-xs text-white/30 mt-3">
                      {i18n.t('favorites.ajoute_le')} {formatDate(fav.added_at)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* List View */
            <div
              className="rounded-2xl overflow-hidden"
              style={{
                background: 'linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))',
                border: '1px solid rgba(255,255,255,0.08)'
              }}
            >
              <div className="divide-y divide-white/[0.04]">
                {filteredFavorites.map((fav) => (
                  <div
                    key={fav.product_id}
                    className="p-4 flex items-center gap-4 hover:bg-white/[0.02] transition-colors"
                    data-testid={`favorite-row-${fav.product_id}`}
                  >
                    {/* Image */}
                    <div className="w-16 h-16 rounded-lg bg-white/[0.04] flex-shrink-0 overflow-hidden">
                      {fav.product_image ? (
                        <img
                          src={fav.product_image}
                          alt={fav.product_name}
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
                      <p className="text-xs text-white/40">{fav.product_sku}</p>
                      <h3 className="font-medium truncate">
                        {fav.product_name || 'Produit non disponible'}
                      </h3>
                      <p className="text-xs text-white/30">
                        {i18n.t('favorites.ajoute_le')} {formatDate(fav.added_at)}
                      </p>
                    </div>

                    {/* Price */}
                    <div className="text-right">
                      {fav.product_price_ht ? (
                        <p className="font-bold text-[#D9B35A]">
                          {formatPrice(fav.product_price_ht)} HT
                        </p>
                      ) : (
                        <p className="text-white/40">—</p>
                      )}
                    </div>

                    {/* Quantity */}
                    <div className="flex items-center gap-1 bg-white/[0.04] rounded-lg">
                      <button
                        onClick={() => updateQuantity(fav.product_id, -1)}
                        className="p-1.5 hover:bg-white/10 rounded-l-lg"
                      >
                        <Minus className="w-3 h-3" />
                      </button>
                      <span className="w-8 text-center text-sm">
                        {quantities[fav.product_id] || 1}
                      </span>
                      <button
                        onClick={() => updateQuantity(fav.product_id, 1)}
                        className="p-1.5 hover:bg-white/10 rounded-r-lg"
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleAddToCart(fav)}
                        className="bg-[#D9B35A] hover:bg-[#C9A34A] text-black"
                        disabled={!fav.product_name}
                      >
                        <ShoppingCart className="w-4 h-4" />
                      </Button>
                      <button
                        onClick={() => handleRemoveFavorite(fav.product_id, fav.product_name)}
                        className="p-2 rounded-lg hover:bg-red-500/20 text-red-400"
                        title={i18n.t('favorites.retirer_des_favoris')}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
