import i18n from '@/i18n';
import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShoppingCart, Plus, Minus, Wallet, CreditCard, ArrowLeft, Star } from 'lucide-react';
import LolodriveLayout, { fmtEUR } from '../components/LolodriveLayout';
import { useCatalogPromos, bestPromos } from '../components/catalog/ProductPromoBadges';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '../components/ui/sheet';
import { lolodriveAPI, authAPI } from '../services/api';
import { toast } from 'sonner';
import TerritorySelector, { getInitialTerritory } from '../components/TerritorySelector';
import { PromoCountdownStrip } from '../components/lolodrive/PromoCountdownStrip';
import { CatalogFiltersBar, applyCatalogFilters } from '../components/lolodrive/CatalogFiltersBar';
import { groupByCategory } from '../components/lolodrive/groupByCategory';
import { CartSlotPicker } from '../components/lolodrive/CartSlotPicker';
import { LolodriveProductCard } from '../components/lolodrive/LolodriveProductCard';
import { PassLolodriveBadge } from '../components/catalog/ProductPromoBadges';
import { distanceFeeRate, getReferencePointCode, kmBetween } from '../utils/relayDistance';

export default function LolodriveCatalogPage() {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [filter, setFilter] = useState('');
  const [passActive, setPassActive] = useState(false);
  const [cart, setCart] = useState(() => {
    try { return JSON.parse(localStorage.getItem('kdm_lolodrive_cart') || '{}') || {}; } catch { return {}; }
  });
  const [fulfillment, setFulfillment] = useState('DRIVE');
  const [pickupSlot, setPickupSlot] = useState('');
  const [pickupDate, setPickupDate] = useState('');
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [subcategory, setSubcategory] = useState('');
  const [loloPoints, setLoloPoints] = useState([]);
  const [relayRatings, setRelayRatings] = useState({});

  useEffect(() => {
    lolodriveAPI.relayReviewStats()
      .then((d) => setRelayRatings(d.stats || {}))
      .catch(() => {});
  }, []);
  const [selectedPoint, setSelectedPoint] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('kdm_preselected_point') || 'null');
      return saved?.code || '';
    } catch (_) { return ''; }
  });
  const [territories, setTerritories] = useState([]);
  const [territory, setTerritory] = useState(getInitialTerritory());
  const [loading, setLoading] = useState(true);

  // Load territories once on mount
  useEffect(() => {
    lolodriveAPI.listTerritories()
      .then((tr) => { if (tr.territories) setTerritories(tr.territories); })
      .catch(() => {});
  }, []);

  // Load catalog products + lolo points whenever filter/territory change (also gates on auth)
  useEffect(() => {
    if (!authAPI.isAuthenticated()) {
      navigate('/connexion');
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [c, lp] = await Promise.all([
          lolodriveAPI.catalogProducts(filter && filter !== 'FAVS' ? filter : undefined, territory || undefined, getReferencePointCode() || undefined),
          lolodriveAPI.listLoloPoints({ territory: territory || undefined }),
        ]);
        if (cancelled) return;
        setProducts(c.products || []);
        setPassActive(c.pass_active);
        setLoloPoints(lp.points || []);
        // Reset selected point if no longer in filtered list
        setSelectedPoint((prev) => (prev && !(lp.points || []).some((p) => p.code === prev) ? '' : prev));
      } catch (e) {
        if (!cancelled) toast.error(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [navigate, filter, territory]);

  // Promos actives (bandeau favoris + prix barrés + remise panier)
  const promos = useCatalogPromos();
  const promoOf = (p) => bestPromos(promos, p).discount;
  const favPromo = (p) => (favs.includes(p.sku) ? promoOf(p) : null);
  const discountedUnit = (p) => {
    const d = promoOf(p);
    return d ? Math.round((p.display_price_cents || 0) * (1 - d.value_percent / 100)) : (p.display_price_cents || 0);
  };

  const add = (sku) => setCart({ ...cart, [sku]: (cart[sku] || 0) + 1 });

  // Panier sauvegardé : persiste entre les sessions
  useEffect(() => {
    try { localStorage.setItem('kdm_lolodrive_cart', JSON.stringify(cart)); } catch { /* quota */ }
  }, [cart]);

  // Produits favoris épinglés en haut du catalogue
  const [favs, setFavs] = useState(() => {
    try { return JSON.parse(localStorage.getItem('kdm_lolodrive_favs') || '[]') || []; } catch { return []; }
  });
  const toggleFav = (sku) => setFavs((prev) => {
    const next = prev.includes(sku) ? prev.filter((s) => s !== sku) : [...prev, sku];
    try { localStorage.setItem('kdm_lolodrive_favs', JSON.stringify(next)); } catch { /* quota */ }
    lolodriveAPI.favoritesSave(next).catch(() => {});
    return next;
  });

  // Sync favoris avec le backend (alertes promo email + multi-appareils)
  useEffect(() => {
    lolodriveAPI.favoritesGet().then((d) => {
      const remote = d.skus || [];
      setFavs((prev) => {
        const merged = [...new Set([...prev, ...remote])];
        try { localStorage.setItem('kdm_lolodrive_favs', JSON.stringify(merged)); } catch { /* quota */ }
        if (merged.length !== remote.length) lolodriveAPI.favoritesSave(merged).catch(() => {});
        return merged;
      });
    }).catch(() => {});
  }, []);
  const sub = (sku) => {
    const n = (cart[sku] || 0) - 1;
    const c = { ...cart };
    if (n <= 0) delete c[sku]; else c[sku] = n;
    setCart(c);
  };

  const cartItems = Object.entries(cart).map(([sku, qty]) => ({ sku, qty }));
  const refCode = getReferencePointCode();
  const refPoint = loloPoints.find((p) => p.code === refCode) || null;
  const pickedPoint = loloPoints.find((p) => p.code === selectedPoint) || null;
  const sortedPoints = [...loloPoints].sort((a, b) => {
    if (refPoint) {
      if (a.code === refPoint.code) return -1;
      if (b.code === refPoint.code) return 1;
    }
    const ra = relayRatings[a.code]?.avg ?? -1;
    const rb = relayRatings[b.code]?.avg ?? -1;
    if (rb !== ra) return rb - ra;
    return (a.name || '').localeCompare(b.name || '');
  });
  const qtyTotal = cartItems.reduce((acc, { qty }) => acc + qty, 0);
  const distanceRate = fulfillment === 'LOLO_POINT' ? distanceFeeRate(refPoint, pickedPoint) : 0;
  const distanceFeeUc = Math.round(distanceRate * qtyTotal * 100) / 100;
  const cartTotal = cartItems.reduce((acc, { sku, qty }) => {
    const p = products.find((x) => x.sku === sku);
    return acc + (p ? discountedUnit(p) : 0) * qty;
  }, 0);
  const cartPromoDiscount = cartItems.reduce((acc, { sku, qty }) => {
    const p = products.find((x) => x.sku === sku);
    return acc + (p ? (p.display_price_cents || 0) - discountedUnit(p) : 0) * qty;
  }, 0);

  const checkout = async (payInUC) => {
    if (cartItems.length === 0) return toast.error('Panier vide');
    if (fulfillment === 'LOLO_POINT' && !selectedPoint) return toast.error('Choisir un relais LOLODRIVE');
    try {
      const order = await lolodriveAPI.createOrder({
        fulfillment_type: fulfillment,
        items: cartItems,
        lolo_point_code: fulfillment === 'LOLO_POINT' ? selectedPoint : undefined,
        reference_point_code: refCode || undefined,
        pickup_slot_id: fulfillment !== 'DELIVERY' ? pickupSlot || undefined : undefined,
        delivery_slot_id: fulfillment === 'DELIVERY' ? pickupSlot || undefined : undefined,
        pickup_date: pickupSlot ? pickupDate || undefined : undefined,
      });
      toast.success(`Commande ${order.order_number} créée`);
      setCart({});
      if (payInUC) {
        await lolodriveAPI.payOrderUC(order.id);
        toast.success('Payée en UC ✅');
        navigate('/pass');
      } else {
        // Stripe Checkout hosted (real test flow)
        const session = await lolodriveAPI.checkoutOrder(window.location.origin, order.id);
        if (session?.url) {
          window.location.href = session.url;
        } else {
          toast.error('Erreur Stripe Checkout');
        }
      }
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <LolodriveLayout
      title={i18n.t('lolodrive.catalogue_lolodrive')}
      subtitle={passActive
        ? "PASS actif — prix PASS visibles sur les ESSENTIELS, paiement en UC autorisé."
        : "PASS inactif — activez votre PASS pour bénéficier des prix réduits."}
      actions={
        <>
        <Button asChild variant="outline" data-testid="back-to-orders-btn">
          <Link to="/pass">
            <ArrowLeft className="w-4 h-4 mr-2" /> Retour à mes commandes
          </Link>
        </Button>
        <Sheet>
          <SheetTrigger asChild>
            <Button data-testid="open-cart-btn"
              style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
              <ShoppingCart className="w-4 h-4 mr-2" />
              Panier {cartItems.length > 0 && `(${cartItems.length})`}
            </Button>
          </SheetTrigger>
          <SheetContent className="bg-[#0a0a0f] border-white/10 text-white w-full sm:max-w-md">
            <SheetHeader>
              <SheetTitle className="text-white">{i18n.t('lolodrive.mon_panier')}</SheetTitle>
            </SheetHeader>
            <div className="mt-4 space-y-2 max-h-[40vh] overflow-y-auto">
              {cartItems.length === 0 && (
                <div className="text-sm text-white/40 text-center py-8">{i18n.t('lolodrive.panier_vide')}</div>
              )}
              {cartItems.map(({ sku, qty }) => {
                const p = products.find((x) => x.sku === sku);
                if (!p) return null;
                return (
                  <div key={sku} className="flex items-center gap-2 p-2 rounded bg-white/[0.03]">
                    <div className="flex-1 text-sm">
                      <div className="font-medium">{p.name}</div>
                      <div className="text-xs text-white/40">{fmtEUR(discountedUnit(p))} × {qty}</div>
                    </div>
                    <Button size="icon" variant="ghost" onClick={() => sub(sku)} data-testid={`cart-sub-${sku}`}>
                      <Minus className="w-3 h-3" />
                    </Button>
                    <span className="w-6 text-center text-sm">{qty}</span>
                    <Button size="icon" variant="ghost" onClick={() => add(sku)} data-testid={`cart-add-${sku}`}>
                      <Plus className="w-3 h-3" />
                    </Button>
                  </div>
                );
              })}
            </div>
            {cartItems.length > 0 && (
              <div className="mt-4 space-y-3">
                {cartPromoDiscount > 0 && (
                  <div className="flex justify-between text-xs font-semibold text-[#FF9E7A]" data-testid="cart-promo-discount-line">
                    <span>⚡ Remise promo appliquée</span>
                    <span>−{fmtEUR(cartPromoDiscount)}</span>
                  </div>
                )}
                <div className="flex justify-between font-bold">
                  <span>{i18n.t('lolodrive.sous_total')}</span>
                  <span>{fmtEUR(cartTotal)}</span>
                </div>
                <div>
                  <label className="text-xs text-white/60">{i18n.t('lolodrive.mode_de_retrait')}</label>
                  <Select value={fulfillment} onValueChange={setFulfillment}>
                    <SelectTrigger className="bg-white/[0.04] border-white/10 mt-1" data-testid="fulfillment-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DRIVE">{i18n.t('lolodrive.drive')}</SelectItem>
                      <SelectItem value="DELIVERY">{i18n.t('lolodrive.livraison')}</SelectItem>
                      <SelectItem value="LOLO_POINT">{i18n.t('lolodrive.relais_lolodrive')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <CartSlotPicker fulfillment={fulfillment} cartItems={cartItems} products={products}
                  slotId={pickupSlot} setSlotId={setPickupSlot}
                  pickupDate={pickupDate} setPickupDate={setPickupDate} />
                {fulfillment === 'LOLO_POINT' && (
                  <Select value={selectedPoint} onValueChange={setSelectedPoint}>
                    <SelectTrigger className="bg-white/[0.04] border-white/10" data-testid="lolo-point-select">
                      <SelectValue placeholder={i18n.t('lolodrive.choisir_un_relais_lolodrive')} />
                    </SelectTrigger>
                    <SelectContent>
                      {sortedPoints.map((p) => {
                        const r = distanceFeeRate(refPoint, p);
                        const km = kmBetween(refPoint, p);
                        const note = relayRatings[p.code];
                        const gold = note && note.avg >= 4.5 ? " · 🏆 Relais d'Or" : '';
                        const noteTag = note ? ` · ★ ${note.avg}` : '';
                        const tag = !refPoint ? `${noteTag}${gold}` : r === 0 ? ` · ★ Mon relais${noteTag}${gold}`
                          : `${noteTag}${gold} ·${km != null ? ` ${km} km ·` : ''} +${r.toFixed(2)} UC/produit`;
                        return <SelectItem key={p.code} value={p.code}>{p.name} — {p.city}{tag}</SelectItem>;
                      })}
                    </SelectContent>
                  </Select>
                )}
                {distanceRate > 0 && qtyTotal > 0 && (
                  <div className="flex justify-between text-xs text-amber-300 px-0.5" data-testid="distance-fee-line">
                    <span>Frais hors relais de référence ({distanceRate.toFixed(2)} UC × {qtyTotal} produit{qtyTotal > 1 ? 's' : ''})</span>
                    <span className="font-bold">+{distanceFeeUc.toFixed(2)} UC</span>
                  </div>
                )}
                <Button onClick={() => checkout(false)} className="w-full" data-testid="checkout-card-btn">
                  <CreditCard className="w-4 h-4 mr-2" /> Payer par CB (Stripe)
                </Button>
                {passActive && (
                  <Button onClick={() => checkout(true)} variant="outline" className="w-full" data-testid="checkout-uc-btn">
                    <Wallet className="w-4 h-4 mr-2" /> Payer en UC
                  </Button>
                )}
              </div>
            )}
          </SheetContent>
        </Sheet>
        </>
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <TerritorySelector
          territories={territories}
          value={territory}
          onChange={setTerritory}
          testId="catalog-territory-selector"
        />
      </div>

      <PromoCountdownStrip promos={promos} />
      <Tabs value={filter} onValueChange={setFilter} className="mb-6">
        <TabsList className="bg-white/[0.04] border border-white/10">
          <TabsTrigger value="" data-testid="tab-all">{i18n.t('lolodrive.tous')}</TabsTrigger>
          <TabsTrigger value="ESSENTIAL" data-testid="tab-essential">{i18n.t('lolodrive.essentiels_25')}</TabsTrigger>
          <TabsTrigger value="NORMAL" data-testid="tab-normal">{i18n.t('lolodrive.hors25')}</TabsTrigger>
          <TabsTrigger value="FAVS" data-testid="tab-favs">
            <Star className="w-3.5 h-3.5 mr-1 fill-[#D9B35A] text-[#D9B35A]" /> Mes favoris{favs.length > 0 ? ` (${favs.length})` : ''}
          </TabsTrigger>
        </TabsList>
      </Tabs>

      <CatalogFiltersBar search={search} setSearch={setSearch}
        category={category} setCategory={setCategory}
        subcategory={subcategory} setSubcategory={setSubcategory} />

      {loading && <div className="text-center text-white/50 py-12">{i18n.t('lolodrive.chargement')}</div>}

      {!loading && filter === 'FAVS' && favs.length === 0 && (
        <div className="text-center text-white/40 py-12" data-testid="favs-empty">
          <Star className="w-8 h-8 mx-auto mb-2 opacity-40" />
          Aucun favori pour le moment — cliquez sur l'étoile d'un produit pour l'épingler ici.
        </div>
      )}

      {!loading && (() => {
        const visible = applyCatalogFilters(products, { search, category, subcategory })
          .filter((p) => filter !== 'FAVS' || favs.includes(p.sku));
        if (visible.length === 0 && filter !== 'FAVS') {
          return <div className="text-center text-white/40 py-12" data-testid="catalog-no-result">Aucun produit ne correspond à ces filtres.</div>;
        }
        return groupByCategory(visible).map((g) => (
          <div key={g.category} className="mb-8" data-testid={`catalog-group-${g.category}`}>
            <h2 className="text-lg font-bold text-[#D9B35A] mb-2 flex items-baseline gap-2">
              {g.category}
              <span className="text-xs font-normal text-white/35">
                {g.subs.reduce((a, s) => a + s.items.length, 0)} produit(s)
              </span>
            </h2>
            {g.subs.map((s) => (
              <div key={s.name} className="mb-5">
                <h3 className="text-sm font-semibold text-white/60 mb-2 border-l-2 border-[#D9B35A]/50 pl-2" data-testid={`catalog-sub-${s.name}`}>{s.name}</h3>
                <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {[...s.items]
                    .sort((a, b) => (favs.includes(b.sku) ? 1 : 0) - (favs.includes(a.sku) ? 1 : 0))
                    .map((p) => (
                      <LolodriveProductCard key={p.sku} p={p} qty={cart[p.sku] || 0} add={add} sub={sub}
                        isFav={favs.includes(p.sku)} toggleFav={toggleFav}
                        promo={promoOf(p)} favPromo={favPromo(p)} discounted={discountedUnit(p)} />
                    ))}
                </div>
              </div>
            ))}
          </div>
        ));
      })()}
    </LolodriveLayout>
  );
}
