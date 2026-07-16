import i18n from '@/i18n';
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

import { formatPrice, MIN_INSTALLMENT_CENTS } from '../components/catalog/catalogUtils';
import { CatalogHeader } from '../components/catalog/CatalogHeader';
import { ProductsGrid } from '../components/catalog/ProductsGrid';
import { CheckoutDialog } from '../components/catalog/CheckoutDialog';

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
      toast.error(i18n.t('catalog.toast_prix_indispo'));
      return;
    }

    setCartLoading(true);
    try {
      const updatedCart = await catalogAPI.addToCart(product.id, product.min_order_qty || 1);
      setCart(updatedCart);
      toast.success(i18n.t('catalog.toast_ajoute_panier', { name: product.name }));
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
      toast.error(i18n.t('catalog.toast_maj_erreur'));
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
      toast.success(i18n.t('catalog.toast_retire_panier'));
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
      toast.error(i18n.t('checkout.toast_select_enlevement'));
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
        toast.success(i18n.t('catalog.toast_commande_4x', { number: order.order_number }));
      } else {
        toast.success(i18n.t('checkout.toast_commande_creee', { number: order.order_number }));
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
      <CatalogHeader
        zones={zones}
        selectedZone={selectedZone}
        setSelectedZone={setSelectedZone}
        cart={cart}
        cartOpen={cartOpen}
        setCartOpen={setCartOpen}
        cartLoading={cartLoading}
        cartItemCount={cartItemCount}
        cartTotal={cartTotal}
        handleUpdateQuantity={handleUpdateQuantity}
        handleRemoveFromCart={handleRemoveFromCart}
        navigate={navigate}
      />
      {/* Main Content */}
      <div className="max-w-[1280px] mx-auto px-5 py-6">
        {/* Breadcrumb */}
        <div className="mb-4">
          <BreadcrumbPill />
        </div>

        {/* Title & Search */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold mb-1">{i18n.t('catalog.catalogue_kdmarche')}</h1>
            <p className="text-white/60 text-sm">
              {i18n.t('catalog.disponibles', { count: products.length })}
            </p>
          </div>
          
          <div className="flex gap-3">
            <div className="relative flex-1 md:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
              <Input
                placeholder={i18n.t('catalog.rechercher')}
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
            {i18n.t('lolodrive.tous')}
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
                <p className="font-medium text-amber-400">{i18n.t('catalog.acces_limite')}</p>
                <p className="text-sm text-amber-400/80">
                  {i18n.t('catalog.les_prix_ne_sont')}
                </p>
              </div>
            </div>
          </div>
        )}

        <ProductsGrid
          products={products}
          cart={cart}
          cartLoading={cartLoading}
          handleAddToCart={handleAddToCart}
        />
      </div>

      <CheckoutDialog
        cart={cart}
        cartItemCount={cartItemCount}
        cartTotal={cartTotal}
        checkoutOpen={checkoutOpen}
        setCheckoutOpen={setCheckoutOpen}
        pickupLocations={pickupLocations}
        selectedPickup={selectedPickup}
        setSelectedPickup={setSelectedPickup}
        orderNotes={orderNotes}
        setOrderNotes={setOrderNotes}
        submittingOrder={submittingOrder}
        handleSubmitOrder={handleSubmitOrder}
        useInstallment={useInstallment}
        setUseInstallment={setUseInstallment}
        installmentPlan={installmentPlan}
        installmentLoading={installmentLoading}
      />
    </div>
  );
}
