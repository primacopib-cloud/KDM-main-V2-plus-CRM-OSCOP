import { Link } from 'react-router-dom';
import {
  ArrowLeft, MapPin, Minus, Package, Plus, ShoppingCart, Trash2,
} from 'lucide-react';
import { Button } from '../ui/button';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger,
} from '../ui/sheet';
import { partners } from '../../data/mock';
import { CrediscopBadge } from '../CrediscopBadge';
import NavigationHistoryDropdown from '../NavigationHistoryDropdown';
import { formatPrice } from './catalogUtils';

export const CatalogHeader = ({
  zones, selectedZone, setSelectedZone, cart, cartOpen, setCartOpen,
  cartLoading, cartItemCount, cartTotal, handleUpdateQuantity,
  handleRemoveFromCart, navigate,
}) => (
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
              CREDI&rsquo;SCOP
            </Link>
            <Link to="/espace-vendeur" className="px-3 py-1.5 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              Vendeur
            </Link>
          </nav>
          
          <div className="flex items-center gap-3">
            <CrediscopBadge className="hidden sm:inline-flex" />
            {/* Navigation History */}
            <NavigationHistoryDropdown variant="dark" />
            
            {/* Zone selector */}
            <Select value={selectedZone} onValueChange={setSelectedZone}>
              <SelectTrigger className="w-[160px] h-10 bg-white/[0.04] border-white/10 text-white">
                <MapPin className="w-4 h-4 mr-2 text-[#D4AF37]" />
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
                  {cart.alerts?.length > 0 && (
                    <div className="mb-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-1" data-testid="cart-alerts-banner">
                      {cart.alerts.map((a) => (
                        <p key={`${a.type}-${a.item_id}`} className={`text-xs ${a.type === 'UNAVAILABLE' ? 'text-red-400' : 'text-amber-400'}`}>
                          {a.type === 'PRICE_CHANGED' && `⚠ Prix modifié : ${a.product_name} — ${formatPrice(a.old_price_ht_cents)} → ${formatPrice(a.new_price_ht_cents)} HT`}
                          {a.type === 'UNAVAILABLE' && `✕ Indisponible : ${a.product_name}`}
                          {a.type === 'AVAILABLE_AGAIN' && `✓ De nouveau disponible : ${a.product_name}`}
                        </p>
                      ))}
                    </div>
                  )}
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
                            className={`p-3 rounded-xl border ${item.unavailable ? 'bg-red-500/[0.06] border-red-500/25' : 'bg-white/[0.04] border-white/[0.08]'}`}
                          >
                            <div className="flex justify-between items-start mb-2">
                              <div className="flex-1">
                                <p className="font-medium text-white/90 text-sm">{item.product_name}</p>
                                <p className="text-xs text-white/50">{item.product_sku}</p>
                                {item.unavailable && (
                                  <span className="inline-block mt-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/20 text-red-400" data-testid={`cart-item-unavailable-${item.id}`}>
                                    INDISPONIBLE
                                  </span>
                                )}
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
                                {formatPrice(item.line_total_ht_cents || item.price_ht_cents * item.quantity)} HT
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
                          disabled={cart.items?.length === 0 || cart.items?.some(i => i.unavailable)}
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

);
