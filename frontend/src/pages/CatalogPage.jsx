import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ShoppingCart, Search, Filter, Package, ArrowLeft, Plus, Minus, Trash2,
  MapPin, ChevronDown, Loader2, Check, X, Tag, Building2, AlertCircle,
  Calendar, CreditCard, Clock, Heart
} from 'lucide-react';

import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger, SheetFooter,
} from '../components/ui/sheet';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';

import { partners } from '../data/mock';
import { authAPI, catalogAPI, zonesAPIV2, ordersAPIV2, installmentAPI } from '../services/api';
import { BreadcrumbPill } from '../components/Breadcrumb';
import NavigationHistoryDropdown from '../components/NavigationHistoryDropdown';
import { FavoriteButton, useFavorites } from '../components/FavoriteButton';

// Format price in cents to euros
const formatPrice = (cents) => {
  if (!cents) return '---';
  return (cents / 100).toFixed(2).replace('.', ',') + ' €';
};

export default function CatalogPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Catalog data
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [pickupLocations, setPickupLocations] = useState([]);
  const [zones, setZones] = useState([]);
  
  // Filters
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedZone, setSelectedZone] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  
  // Cart state
  const [cart, setCart] = useState({ items: [], total_ht_cents: 0 });
  const [cartOpen, setCartOpen] = useState(false);
  const [cartLoading, setCartLoading] = useState(false);
  
  // Checkout
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [selectedPickup, setSelectedPickup] = useState('');
  const [orderNotes, setOrderNotes] = useState('');
  const [submittingOrder, setSubmittingOrder] = useState(false);
  
  // Installment payment
  const [useInstallment, setUseInstallment] = useState(false);
  const [installmentPlan, setInstallmentPlan] = useState(null);
  const [installmentLoading, setInstallmentLoading] = useState(false);
  
  // Min amount for installment (5500€ HT = 550000 cents)
  const MIN_INSTALLMENT_CENTS = 550000;

  // Load initial data
  useEffect(() => {
    const init = async () => {
      if (!authAPI.isAuthenticated()) {
        toast.error('Veuillez vous connecter');
        navigate('/connexion?redirect=/catalogue');
        return;
      }

      try {
        const userData = await authAPI.getMe();
        setUser(userData);

        // Load zones and categories in parallel
        const [zonesData, categoriesData] = await Promise.all([
          zonesAPIV2.list(),
          catalogAPI.getCategories(),
        ]);

        setZones(zonesData);
        setCategories(categoriesData);

        // Set default zone if available
        if (zonesData.length > 0) {
          const defaultZone = zonesData[0].code;
          setSelectedZone(defaultZone);
          
          // Load products and pickup locations for this zone
          const [productsData, locationsData] = await Promise.all([
            catalogAPI.getProducts({ zoneCode: defaultZone }),
            catalogAPI.getPickupLocations(defaultZone),
          ]);
          setProducts(productsData);
          setPickupLocations(locationsData);
        }

        // Load cart
        try {
          const cartData = await catalogAPI.getCart();
          setCart(cartData);
        } catch (e) {
          // Cart may not exist yet
          console.log('No cart found');
        }

      } catch (error) {
        console.error('Init error:', error);
        toast.error('Erreur de chargement');
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [navigate]);

  // Load products when zone or category changes
  const loadProducts = useCallback(async () => {
    if (!selectedZone) return;
    
    try {
      const params = { zoneCode: selectedZone };
      if (selectedCategory && selectedCategory !== 'all') {
        params.categoryId = selectedCategory;
      }
      if (searchTerm) {
        params.search = searchTerm;
      }
      
      const data = await catalogAPI.getProducts(params);
      setProducts(data);
    } catch (error) {
      console.error('Error loading products:', error);
    }
  }, [selectedZone, selectedCategory, searchTerm]);

  useEffect(() => {
    if (selectedZone) {
      loadProducts();
      // Load pickup locations for zone
      catalogAPI.getPickupLocations(selectedZone).then(setPickupLocations).catch(console.error);
    }
  }, [selectedZone, loadProducts]);

  // Add to cart
  const handleAddToCart = async (product) => {
    if (!product.price_visible) {
      toast.error('Prix non disponible pour votre organisation');
      return;
    }

    setCartLoading(true);
    try {
      const updatedCart = await catalogAPI.addToCart(product.id, product.min_order_qty || 1);
      setCart(updatedCart);
      toast.success(`${product.name} ajouté au panier`);
    } catch (error) {
      toast.error(error.message || 'Erreur lors de l\'ajout');
    } finally {
      setCartLoading(false);
    }
  };

  // Update cart item quantity
  const handleUpdateQuantity = async (itemId, newQuantity) => {
    if (newQuantity < 1) {
      handleRemoveFromCart(itemId);
      return;
    }

    setCartLoading(true);
    try {
      // Remove and re-add with new quantity
      await catalogAPI.removeFromCart(itemId);
      const item = cart.items.find(i => i.id === itemId);
      if (item) {
        const updatedCart = await catalogAPI.addToCart(item.product_id, newQuantity);
        setCart(updatedCart);
      }
    } catch (error) {
      toast.error('Erreur lors de la mise à jour');
    } finally {
      setCartLoading(false);
    }
  };

  // Remove from cart
  const handleRemoveFromCart = async (itemId) => {
    setCartLoading(true);
    try {
      await catalogAPI.removeFromCart(itemId);
      setCart(prev => ({
        ...prev,
        items: prev.items.filter(i => i.id !== itemId),
        total_ht_cents: prev.items
          .filter(i => i.id !== itemId)
          .reduce((sum, i) => sum + (i.unit_price_ht_cents * i.quantity), 0),
      }));
      toast.success('Article retiré du panier');
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    } finally {
      setCartLoading(false);
    }
  };

  // Calculate installment plan when cart changes or installment is selected
  useEffect(() => {
    const calculateInstallment = async () => {
      if (!cart.total_ht_cents || cart.total_ht_cents < MIN_INSTALLMENT_CENTS) {
        setInstallmentPlan(null);
        setUseInstallment(false);
        return;
      }
      
      setInstallmentLoading(true);
      try {
        const plan = await installmentAPI.calculate(cart.total_ht_cents);
        setInstallmentPlan(plan);
      } catch (error) {
        console.error('Installment calculation error:', error);
        setInstallmentPlan(null);
      } finally {
        setInstallmentLoading(false);
      }
    };
    
    if (checkoutOpen && cart.total_ht_cents >= MIN_INSTALLMENT_CENTS) {
      calculateInstallment();
    }
  }, [checkoutOpen, cart.total_ht_cents]);

  // Submit order
  const handleSubmitOrder = async () => {
    if (!selectedPickup) {
      toast.error('Veuillez sélectionner un point d\'enlèvement');
      return;
    }

    if (!cart.id || cart.items.length === 0) {
      toast.error('Votre panier est vide');
      return;
    }

    setSubmittingOrder(true);
    try {
      const order = await ordersAPIV2.create(cart.id, selectedPickup, orderNotes || null, useInstallment);
      
      if (useInstallment && order.is_installment) {
        toast.success(`Commande ${order.order_number} créée en 4× !`);
      } else {
        toast.success(`Commande ${order.order_number} créée avec succès !`);
      }
      
      setCart({ items: [], total_ht_cents: 0 });
      setCheckoutOpen(false);
      setCartOpen(false);
      setUseInstallment(false);
      setInstallmentPlan(null);
      navigate('/commandes');
    } catch (error) {
      toast.error(error.message || 'Erreur lors de la commande');
    } finally {
      setSubmittingOrder(false);
    }
  };

  // Calculate cart totals
  const cartItemCount = cart.items?.reduce((sum, item) => sum + item.quantity, 0) || 0;
  const cartTotal = cart.total_ht_cents || cart.items?.reduce((sum, item) => sum + (item.unit_price_ht_cents * item.quantity), 0) || 0;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }} data-testid="catalog-page">
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
            <Link to="/espace-acheteur" className="flex items-center gap-2 text-white/60 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm hidden sm:inline">Mon Espace</span>
            </Link>
            <div className="flex items-center gap-3">
              <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-10 w-auto object-contain" />
              <span className="text-white/40 text-xs">×</span>
              <img src={partners.oscop.logo} alt="O'SCOP" className="h-6 w-auto object-contain" />
            </div>
          </div>
          
          {/* Quick Navigation */}
          <nav className="hidden lg:flex items-center gap-1">
            <Link to="/" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Accueil
            </Link>
            <Link to="/espace-acheteur" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Mon Espace
            </Link>
            <Link to="/commandes" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Commandes
            </Link>
            <Link to="/wallet" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Wallet
            </Link>
            <Link to="/espace-vendeur" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Vendeur
            </Link>
          </nav>
          
          <div className="flex items-center gap-3">
            {/* Navigation History */}
            <NavigationHistoryDropdown variant="dark" />
            
            {/* Zone selector */}
            <Select value={selectedZone} onValueChange={setSelectedZone}>
              <SelectTrigger className="w-[160px] h-10 bg-white/[0.04] border-white/10 text-white">
                <MapPin className="w-4 h-4 mr-2 text-[#57D19A]" />
                <SelectValue placeholder="Zone" />
              </SelectTrigger>
              <SelectContent>
                {zones.map(zone => (
                  <SelectItem key={zone.code} value={zone.code}>
                    {zone.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Cart button */}
            <Sheet open={cartOpen} onOpenChange={setCartOpen}>
              <SheetTrigger asChild>
                <Button 
                  variant="outline" 
                  className="relative bg-[#D9B35A]/20 border-[#D9B35A]/30 text-[#D9B35A] hover:bg-[#D9B35A]/30"
                  data-testid="cart-button"
                >
                  <ShoppingCart className="w-5 h-5" />
                  {cartItemCount > 0 && (
                    <span className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-[#D9B35A] text-black text-xs font-bold flex items-center justify-center">
                      {cartItemCount}
                    </span>
                  )}
                </Button>
              </SheetTrigger>
              <SheetContent className="w-full sm:max-w-lg bg-[#0a0d14] border-white/10">
                <SheetHeader>
                  <SheetTitle className="text-white flex items-center gap-2">
                    <ShoppingCart className="w-5 h-5 text-[#D9B35A]" />
                    Panier ({cartItemCount} article{cartItemCount > 1 ? 's' : ''})
                  </SheetTitle>
                  <SheetDescription className="text-white/60">
                    Zone: {zones.find(z => z.code === selectedZone)?.name || selectedZone}
                  </SheetDescription>
                </SheetHeader>

                <div className="mt-6 flex flex-col h-[calc(100vh-200px)]">
                  {cart.items?.length === 0 ? (
                    <div className="flex-1 flex items-center justify-center text-white/50">
                      <div className="text-center">
                        <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>Votre panier est vide</p>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex-1 overflow-auto space-y-3">
                        {cart.items?.map(item => (
                          <div 
                            key={item.id} 
                            className="p-3 rounded-xl bg-white/[0.04] border border-white/[0.08]"
                          >
                            <div className="flex justify-between items-start mb-2">
                              <div className="flex-1">
                                <p className="font-medium text-white/90 text-sm">{item.product_name}</p>
                                <p className="text-xs text-white/50">{item.sku}</p>
                              </div>
                              <button 
                                onClick={() => handleRemoveFromCart(item.id)}
                                className="p-1.5 rounded-lg hover:bg-red-500/20 text-red-400"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <button 
                                  onClick={() => handleUpdateQuantity(item.id, item.quantity - 1)}
                                  className="w-7 h-7 rounded-lg bg-white/[0.06] flex items-center justify-center hover:bg-white/[0.12]"
                                  disabled={cartLoading}
                                >
                                  <Minus className="w-3 h-3" />
                                </button>
                                <span className="w-8 text-center font-medium">{item.quantity}</span>
                                <button 
                                  onClick={() => handleUpdateQuantity(item.id, item.quantity + 1)}
                                  className="w-7 h-7 rounded-lg bg-white/[0.06] flex items-center justify-center hover:bg-white/[0.12]"
                                  disabled={cartLoading}
                                >
                                  <Plus className="w-3 h-3" />
                                </button>
                              </div>
                              <p className="font-semibold text-[#D9B35A]">
                                {formatPrice(item.unit_price_ht_cents * item.quantity)} HT
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="pt-4 border-t border-white/[0.08] space-y-4">
                        <div className="flex justify-between items-center">
                          <span className="text-white/70">Total HT</span>
                          <span className="text-xl font-bold text-[#D9B35A]">{formatPrice(cartTotal)}</span>
                        </div>
                        <Button 
                          className="w-full bg-[#D9B35A] hover:bg-[#c9a34a] text-black font-semibold"
                          onClick={() => navigate('/checkout')}
                          disabled={cart.items?.length === 0}
                          data-testid="checkout-button"
                        >
                          Passer commande (EXW)
                        </Button>
                        <p className="text-xs text-white/40 text-center">
                          Bon de commande dynamique + Signature électronique
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-[1280px] mx-auto px-5 py-6">
        {/* Breadcrumb */}
        <div className="mb-4">
          <BreadcrumbPill />
        </div>

        {/* Title & Search */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold mb-1">Catalogue KDMARCHE</h1>
            <p className="text-white/60 text-sm">
              {products.length} produit{products.length > 1 ? 's' : ''} disponible{products.length > 1 ? 's' : ''}
            </p>
          </div>
          
          <div className="flex gap-3">
            <div className="relative flex-1 md:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
              <Input
                placeholder="Rechercher..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadProducts()}
                className="pl-9 h-10 bg-white/[0.04] border-white/10 text-white placeholder:text-white/40"
              />
            </div>
            <Button variant="outline" onClick={loadProducts} className="border-white/10">
              <Search className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Categories */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          <button
            onClick={() => setSelectedCategory('all')}
            className={`px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all ${
              selectedCategory === 'all'
                ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30'
                : 'bg-white/[0.04] text-white/60 hover:text-white border border-white/[0.08]'
            }`}
          >
            Tous
          </button>
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all ${
                selectedCategory === cat.id
                  ? 'bg-[#D9B35A]/20 text-[#D9B35A] border border-[#D9B35A]/30'
                  : 'bg-white/[0.04] text-white/60 hover:text-white border border-white/[0.08]'
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>

        {/* Access Warning */}
        {products.length > 0 && !products[0].price_visible && (
          <div className="mb-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-amber-400">Accès limité</p>
                <p className="text-sm text-amber-400/80">
                  Les prix ne sont pas visibles. Votre organisation doit être approuvée et avoir un abonnement actif.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Products Grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {products.map(product => (
            <div 
              key={product.id}
              className="glass-panel-soft rounded-[18px] p-4 flex flex-col group"
              data-testid={`product-card-${product.sku}`}
            >
              {/* Product Image placeholder */}
              <div className="aspect-square rounded-xl bg-white/[0.04] mb-4 flex items-center justify-center relative overflow-hidden">
                {product.image_url ? (
                  <img src={product.image_url} alt={product.name} className="w-full h-full object-cover rounded-xl" />
                ) : (
                  <Package className="w-12 h-12 text-white/20" />
                )}
                {/* Favorite button - positioned top right */}
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <FavoriteButton 
                    productId={product.id} 
                    productName={product.name}
                    size="sm"
                  />
                </div>
              </div>
              
              {/* Category badge */}
              <Badge variant="outline" className="w-fit mb-2 text-[10px] text-white/60 border-white/20">
                {product.category_name || 'Produit'}
              </Badge>
              
              {/* Product info */}
              <h3 className="font-medium text-white/90 mb-1 line-clamp-2">{product.name}</h3>
              <p className="text-xs text-white/50 mb-3">{product.sku} · {product.unit_quantity} {product.unit}</p>
              
              {/* Price & Add to cart */}
              <div className="mt-auto flex items-end justify-between">
                <div>
                  {product.price_visible ? (
                    <>
                      {product.savings_percent && (
                        <Badge className="mb-1 bg-[#57D19A]/20 text-[#57D19A] border-0 text-[10px]">
                          -{product.savings_percent}%
                        </Badge>
                      )}
                      <p className="text-lg font-bold text-[#D9B35A]">
                        {formatPrice(product.price_ht_cents)} <span className="text-xs font-normal text-white/50">HT</span>
                      </p>
                      {product.original_price_ht_cents && (
                        <p className="text-xs text-white/40 line-through">
                          {formatPrice(product.original_price_ht_cents)}
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-white/40 italic">Prix sur demande</p>
                  )}
                </div>
                
                <Button
                  size="sm"
                  onClick={() => handleAddToCart(product)}
                  disabled={!product.price_visible || !product.in_stock || cartLoading}
                  className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
                  data-testid={`add-to-cart-${product.sku}`}
                >
                  {cartLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                </Button>
              </div>
              
              {/* Stock indicator */}
              {!product.in_stock && (
                <p className="text-xs text-red-400 mt-2">Rupture de stock</p>
              )}
            </div>
          ))}
        </div>

        {products.length === 0 && (
          <div className="text-center py-20 text-white/50">
            <Package className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p className="text-lg">Aucun produit trouvé</p>
            <p className="text-sm">Essayez de modifier vos filtres</p>
          </div>
        )}
      </div>

      {/* Checkout Dialog */}
      <Dialog open={checkoutOpen} onOpenChange={setCheckoutOpen}>
        <DialogContent className="bg-[#0a0d14] border-white/10 text-white sm:max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Finaliser la commande</DialogTitle>
            <DialogDescription className="text-white/60">
              Commande EXW - Enlèvement à votre charge
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Order summary */}
            <div className="p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]">
              <p className="text-sm text-white/60 mb-2">Récapitulatif</p>
              <div className="flex justify-between items-center">
                <span>{cartItemCount} article{cartItemCount > 1 ? 's' : ''}</span>
                <span className="font-bold text-[#D9B35A]">{formatPrice(cartTotal)} HT</span>
              </div>
            </div>
            
            {/* Installment Payment Option */}
            {cartTotal >= MIN_INSTALLMENT_CENTS && (
              <div className={`p-4 rounded-xl border transition-all ${
                useInstallment 
                  ? 'bg-purple-500/10 border-purple-500/30' 
                  : 'bg-white/[0.02] border-white/[0.08]'
              }`}>
                <div className="flex items-start gap-3">
                  <Checkbox 
                    id="installment"
                    checked={useInstallment}
                    onCheckedChange={setUseInstallment}
                    className="mt-1 border-white/30 data-[state=checked]:bg-purple-500 data-[state=checked]:border-purple-500"
                  />
                  <div className="flex-1">
                    <Label htmlFor="installment" className="font-medium cursor-pointer flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-purple-400" />
                      Paiement en 4× sans frais cachés
                    </Label>
                    <p className="text-xs text-white/50 mt-1">
                      À partir de 5 500€ HT. Frais: 20% HT + TVA 8,50%
                    </p>
                    
                    {installmentLoading && (
                      <div className="flex items-center gap-2 mt-3">
                        <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                        <span className="text-xs text-white/50">Calcul en cours...</span>
                      </div>
                    )}
                    
                    {useInstallment && installmentPlan && !installmentLoading && (
                      <div className="mt-3 pt-3 border-t border-white/[0.08] space-y-2">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <span className="text-white/50">Montant HT</span>
                            <p className="font-medium">{installmentPlan.subtotal_ht_eur?.toFixed(2)}€</p>
                          </div>
                          <div>
                            <span className="text-white/50">TVA produits (8,50%)</span>
                            <p className="font-medium">{installmentPlan.product_tva_eur?.toFixed(2)}€</p>
                          </div>
                          <div>
                            <span className="text-white/50">Frais échelonnement (20%)</span>
                            <p className="font-medium">{installmentPlan.fees_ht_eur?.toFixed(2)}€</p>
                          </div>
                          <div>
                            <span className="text-white/50">TVA frais (8,50%)</span>
                            <p className="font-medium">{installmentPlan.fees_tva_eur?.toFixed(2)}€</p>
                          </div>
                        </div>
                        
                        <div className="pt-2 border-t border-white/[0.08]">
                          <div className="flex justify-between items-center mb-2">
                            <span className="text-sm font-medium text-purple-400">Total à payer en 4×</span>
                            <span className="text-lg font-bold text-purple-400">
                              {installmentPlan.total_with_fees_eur?.toFixed(2)}€
                            </span>
                          </div>
                          
                          <div className="space-y-1">
                            {installmentPlan.installments?.map((inst, idx) => (
                              <div key={idx} className="flex justify-between items-center text-xs bg-white/[0.02] p-2 rounded">
                                <span className="text-white/60">
                                  <Clock className="w-3 h-3 inline mr-1" />
                                  {inst.label}
                                </span>
                                <span className="font-medium">{inst.amount_eur?.toFixed(2)}€</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
            
            {/* Under minimum amount notice */}
            {cartTotal > 0 && cartTotal < MIN_INSTALLMENT_CENTS && (
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.08]">
                <p className="text-xs text-white/50">
                  <Calendar className="w-3 h-3 inline mr-1" />
                  Paiement en 4× disponible à partir de 5 500€ HT 
                  <span className="text-white/30 ml-1">
                    (il vous manque {formatPrice(MIN_INSTALLMENT_CENTS - cartTotal)})
                  </span>
                </p>
              </div>
            )}
            
            {/* Pickup location selector */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Point d'enlèvement (EXW) *</label>
              <Select value={selectedPickup} onValueChange={setSelectedPickup}>
                <SelectTrigger className="w-full bg-white/[0.04] border-white/10">
                  <SelectValue placeholder="Sélectionner un point" />
                </SelectTrigger>
                <SelectContent>
                  {pickupLocations.map(loc => (
                    <SelectItem key={loc.id} value={loc.id}>
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-[#57D19A]" />
                        <span>{loc.name} - {loc.city}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {pickupLocations.find(l => l.id === selectedPickup) && (
                <p className="text-xs text-white/50">
                  {pickupLocations.find(l => l.id === selectedPickup)?.address}
                </p>
              )}
            </div>
            
            {/* Notes */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Notes (optionnel)</label>
              <Input
                placeholder="Instructions particulières..."
                value={orderNotes}
                onChange={(e) => setOrderNotes(e.target.value)}
                className="bg-white/[0.04] border-white/10"
              />
            </div>
            
            {/* EXW Warning */}
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <p className="text-xs text-amber-400">
                <strong>Incoterm EXW :</strong> L'enlèvement, le transport et les formalités sont à votre charge.
              </p>
            </div>
          </div>
          
          <DialogFooter className="flex gap-3">
            <Button variant="outline" onClick={() => setCheckoutOpen(false)} className="border-white/10">
              Annuler
            </Button>
            <Button 
              onClick={handleSubmitOrder}
              disabled={!selectedPickup || submittingOrder}
              className={useInstallment ? "bg-purple-600 hover:bg-purple-700 text-white" : "bg-[#D9B35A] hover:bg-[#c9a34a] text-black"}
              data-testid="confirm-order-button"
            >
              {submittingOrder ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : useInstallment ? (
                <Calendar className="w-4 h-4 mr-2" />
              ) : (
                <Check className="w-4 h-4 mr-2" />
              )}
              {useInstallment ? 'Commander en 4×' : 'Confirmer la commande'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
