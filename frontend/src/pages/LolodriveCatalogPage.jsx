import i18n from '@/i18n';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BackLink } from '../components/BackLink';
import { ShoppingCart, Plus, Minus, Wallet, CreditCard, ArrowLeft, Star, ChevronRight, Timer } from 'lucide-react';
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
import { LolodriveSpotButton } from '../components/lolodrive/LolodriveSpot';
import { PassLolodriveBadge } from '../components/catalog/ProductPromoBadges';
import { distanceFeeRate, getReferencePointCode, kmBetween } from '../utils/relayDistance';

const PROMO_CAT = '__PROMOS__';

// Compte à rebours vers la fin de promo la plus proche (ex : « ⏱ 9 h 12 min » ou « ⏱ 2 j 5 h »)
const promoCountdown = (items) => {
  const ends = items
    .filter((p) => (p.tag === 'PROMO' || p.tag === 'SOLDE') && p.tag_until)
    .map((p) => new Date(p.tag_until).getTime())
    .filter((t) => t > Date.now());
  if (!ends.length) return null;
  const ms = Math.min(...ends) - Date.now();
  const d = Math.floor(ms / 86400000);
  const h = Math.floor((ms % 86400000) / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  if (d > 0) return `${d} j ${h} h`;
  if (h > 0) return `${h} h ${String(m).padStart(2, '0')} min`;
  return `${m} min`;
};

// Badge compte à rebours affiché sur les tuiles
const CountdownBadge = ({ items, testid }) => {
  const [, tick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tick((x) => x + 1), 30000);
    return () => clearInterval(id);
  }, []);
  const left = promoCountdown(items);
  if (!left) return null;
  return (
    <span data-testid={testid}
      className="absolute top-2 right-2 inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-red-500/90 text-white shadow-lg animate-pulse">
      <Timer className="w-3 h-3" /> {left}
    </span>
  );
};

// Tuile de navigation (catégorie ou sous-catégorie) avec image d'ambiance
const CatTile = ({ testid, name, count, image, accent, onClick, items = [] }) => (
  <button type="button" onClick={onClick} data-testid={testid}
    className={`relative rounded-2xl overflow-hidden border text-left h-28 flex flex-col justify-end p-3 transition-all hover:-translate-y-0.5 ${
      accent ? 'border-red-400/40 bg-red-500/10 hover:bg-red-500/15' : 'border-white/10 bg-white/[0.03] hover:border-[#D9B35A]/40'}`}>
    {image && <img src={image} alt="" loading="lazy" className="absolute inset-0 w-full h-full object-cover opacity-25" />}
    <CountdownBadge items={items} testid={`${testid}-countdown`} />
    <span className={`relative text-sm font-bold ${accent ? 'text-red-200' : 'text-[#D9B35A]'}`}>{name}</span>
    <span className="relative text-[11px] text-white/55">{count} produit{count > 1 ? 's' : ''}</span>
  </button>
);

// Fil d'Ariane : Catégories › Catégorie › Sous-catégorie
const Crumb = ({ parts }) => (
  <div className="flex flex-wrap items-center gap-1.5 text-sm mb-4" data-testid="catalog-breadcrumb">
    {parts.map((p, i) => (
      <span key={i} className="flex items-center gap-1.5">
        {i > 0 && <ChevronRight className="w-3.5 h-3.5 text-white/30" />}
        {p.onClick ? (
          <button type="button" onClick={p.onClick} data-testid={`crumb-${i}`}
            className="text-white/60 hover:text-[#D9B35A] font-medium transition-colors">{p.label}</button>
        ) : (
          <span className="text-white font-semibold" data-testid={`crumb-${i}`}>{p.label}</span>
        )}
      </span>
    ))}
  </div>
);

// Navigation catalogue par clics : catégories → sous-catégories → produits
const CatalogDrillDown = ({ pool, category, setCategory, subcategory, setSubcategory, renderGrid, renderLastChance }) => {
  const groups = groupByCategory(pool);
  const promos = pool.filter((p) => p.tag === 'PROMO' || p.tag === 'SOLDE');
  // Rayon « Dernière chance » : promos qui finissent dans moins de 24 h
  const lastChance = pool.filter((p) => {
    if (p.tag !== 'PROMO' && p.tag !== 'SOLDE') return false;
    const ms = p.tag_until ? new Date(p.tag_until).getTime() - Date.now() : null;
    return ms !== null && ms > 0 && ms < 86400000;
  });
  if (category === PROMO_CAT) {
    return (
      <>
        <Crumb parts={[
          { label: 'Catégories', onClick: () => setCategory('') },
          { label: 'Promos & Soldes' },
        ]} />
        {renderGrid(promos, 'catalog-promos-grid')}
      </>
    );
  }
  const catGroup = category ? groups.find((g) => g.category === category) : null;
  const effCategory = catGroup ? category : '';
  if (!effCategory) {
    return (
      <>
        {lastChance.length > 0 && renderLastChance && (
          <div className="mb-5 rounded-2xl border border-red-400/30 bg-red-500/[0.06] p-3" data-testid="last-chance-row">
            <h2 className="text-sm font-bold text-red-300 mb-2 flex items-center gap-1.5">
              <Timer className="w-4 h-4" /> Dernière chance — {lastChance.length} promo{lastChance.length > 1 ? 's' : ''} {lastChance.length > 1 ? 'finissent' : 'finit'} dans moins de 24 h
            </h2>
            {renderLastChance(lastChance)}
          </div>
        )}
        <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))' }} data-testid="catalog-categories">
        {promos.length > 0 && (
          <CatTile testid="catalog-cat-promos" name="Promos & Soldes" count={promos.length} accent items={promos}
            onClick={() => setCategory(PROMO_CAT)} />
        )}
        {groups.map((g) => {
          const count = g.subs.reduce((a, s) => a + s.items.length, 0);
          const allItems = g.subs.flatMap((s) => s.items);
          const img = allItems.find((p) => p.photo_url || p.image_url);
          return (
            <CatTile key={g.category} testid={`catalog-cat-${g.category}`} name={g.category} count={count}
              image={img?.photo_url || img?.image_url} items={allItems}
              onClick={() => { setCategory(g.category); setSubcategory(''); }} />
          );
        })}
        </div>
      </>
    );
  }
  const subGroup = subcategory ? catGroup.subs.find((s) => s.name === subcategory) : null;
  if (!subGroup) {
    return (
      <>
        <Crumb parts={[
          { label: 'Catégories', onClick: () => { setCategory(''); setSubcategory(''); } },
          { label: effCategory },
        ]} />
        <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))' }} data-testid="catalog-subcategories">
          {catGroup.subs.map((s) => {
            const img = s.items.find((p) => p.photo_url || p.image_url);
            return (
              <CatTile key={s.name} testid={`catalog-sub-tile-${s.name}`} name={s.name} count={s.items.length}
                image={img?.photo_url || img?.image_url} items={s.items} onClick={() => setSubcategory(s.name)} />
            );
          })}
        </div>
      </>
    );
  }
  return (
    <>
      <Crumb parts={[
        { label: 'Catégories', onClick: () => { setCategory(''); setSubcategory(''); } },
        { label: effCategory, onClick: () => setSubcategory('') },
        { label: subGroup.name },
      ]} />
      {renderGrid(subGroup.items, 'catalog-products-grid')}
    </>
  );
};

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
  const isVisitor = !authAPI.isAuthenticated() || new URLSearchParams(window.location.search).has('visitor');
  useEffect(() => {
    if (isVisitor) {
      fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/catalog/public`)
        .then((r) => r.json())
        .then((d) => setProducts(d.products || []))
        .catch(() => {})
        .finally(() => setLoading(false));
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

  // Concept LOLODRIVE : ajout au panier par lot de 3
  const add = (sku) => setCart({ ...cart, [sku]: (cart[sku] || 0) + 3 });

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
    const n = (cart[sku] || 0) - 3;
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
      subtitle={isVisitor
        ? 'Aperçu visiteur — prix réservés aux titulaires du PASS LOLODRIVE.'
        : passActive
          ? "PASS actif — prix PASS visibles sur les ESSENTIELS, paiement en UC autorisé."
          : "PASS inactif — activez votre PASS pour bénéficier des prix réduits."}
      actions={isVisitor ? (
        <>
        <LolodriveSpotButton />
        <Button onClick={() => navigate('/pass-lolodrive')} data-testid="visitor-pass-cta"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
          <Star className="w-4 h-4 mr-2" /> Acheter le PASS & créer mon espace
        </Button>
        </>
      ) : (
        <>
        <LolodriveSpotButton />
        <Button asChild variant="outline" data-testid="back-to-orders-btn">
          <BackLink fallback="/pass">
            <ArrowLeft className="w-4 h-4 mr-2" /> Retour
          </BackLink>
        </Button>
        <Sheet>
          <SheetTrigger asChild>
            <Button data-testid="open-cart-btn"
              style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
              <ShoppingCart className="w-4 h-4 mr-2" />
              Panier {qtyTotal > 0 && `(${Math.round(qtyTotal / 3)} lot${qtyTotal > 3 ? 's' : ''} ×3)`}
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
                  <div key={sku} className="flex items-center gap-2.5 p-2 rounded bg-white/[0.03]">
                    {/* Photo produit */}
                    <div className="w-12 h-12 rounded-lg overflow-hidden product-thumb-light border border-white/10 shrink-0 flex items-center justify-center">
                      {p.photo_url || p.image_url ? (
                        <img src={p.photo_url || p.image_url} alt={p.name} loading="lazy"
                          className="w-full h-full object-cover" data-testid={`cart-line-photo-${sku}`} />
                      ) : (
                        <ShoppingCart className="w-4 h-4 text-black/20" data-testid={`cart-line-photo-${sku}`} />
                      )}
                    </div>
                    <div className="flex-1 text-sm min-w-0">
                      <div className="font-medium truncate">{p.name}</div>
                      <div className="text-xs text-white/40" data-testid={`cart-line-lots-${sku}`}>{fmtEUR(discountedUnit(p) * 3)} le lot de 3 × {Math.round(qty / 3)}</div>
                    </div>
                    <Button size="icon" variant="ghost" onClick={() => sub(sku)} data-testid={`cart-sub-${sku}`}>
                      <Minus className="w-3 h-3" />
                    </Button>
                    <span className="w-14 text-center text-sm font-semibold">{Math.round(qty / 3)} lot{qty > 3 ? 's' : ''}</span>
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
      )}
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

      {!loading && isVisitor && (() => {
        const visitorCard = (p) => (
          <div key={p.sku} className="rounded-2xl overflow-hidden bg-white/[0.03] border border-white/[0.08]" data-testid={`visitor-product-${p.sku}`}>
            <div className="relative h-28 product-thumb-light">
              {p.photo_url || p.image_url ? (
                <img src={p.photo_url || p.image_url} alt={p.name} loading="lazy" className="w-full h-full object-contain p-1" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-black/15"><ShoppingCart className="w-8 h-8" /></div>
              )}
              <span className="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#8CC63E] text-[#1F2A12]">LOT ×3</span>
            </div>
            <div className="p-3">
              <div className="text-sm font-semibold text-white truncate">{p.name}</div>
              <div className="text-[10px] text-white/40">{p.category || ''}</div>
              <div className="mt-1.5 text-[11px] font-semibold text-[#E9CF8E]">🔒 Prix réservé aux titulaires PASS</div>
            </div>
          </div>
        );
        const visitorGrid = (items, testid) => (
          <div className="grid gap-2.5 mb-6" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))' }} data-testid={testid}>
            {items.map(visitorCard)}
          </div>
        );
        const visitorLastChance = (items) => (
          <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
            {items.map((p) => (
              <div key={p.sku} className="flex items-center gap-2.5 p-2 rounded-xl bg-white/[0.03] border border-red-400/20"
                data-testid={`last-chance-item-${p.sku}`}>
                <div className="w-10 h-10 rounded-lg overflow-hidden product-thumb-light shrink-0 flex items-center justify-center">
                  {p.photo_url || p.image_url ? (
                    <img src={p.photo_url || p.image_url} alt={p.name} loading="lazy" className="w-full h-full object-contain p-0.5" />
                  ) : (
                    <ShoppingCart className="w-4 h-4 text-black/20" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold text-white truncate">{p.name}</div>
                  <div className="text-[10px]"><span className="text-red-300 font-bold">⏱ {promoCountdown([p])}</span> <span className="text-[#E9CF8E]">· Prix réservé aux titulaires PASS</span></div>
                </div>
              </div>
            ))}
          </div>
        );
        return (
        <>
          {products.length === 0 && (
            <p className="text-white/40 text-sm py-8 text-center">Vitrine en cours de préparation — revenez bientôt !</p>
          )}
          {products.length > 0 && (search.trim() ? (
            visitorGrid(applyCatalogFilters(products, { search, category, subcategory }), 'visitor-catalog-grid')
          ) : (
            <CatalogDrillDown pool={products} category={category} setCategory={setCategory}
              subcategory={subcategory} setSubcategory={setSubcategory} renderGrid={visitorGrid} renderLastChance={visitorLastChance} />
          ))}
          <div className="rounded-2xl p-5 text-center border border-[#D9B35A]/40 bg-[#D9B35A]/[0.07]" data-testid="visitor-pass-invite">
            <p className="text-white font-semibold m-0 mb-1">Envie de commander par lots de 3 aux prix mutualisés ?</p>
            <p className="text-white/60 text-sm m-0 mb-3">Achetez votre PASS LOLODRIVE et créez votre espace pour accéder à tout le catalogue et aux prix.</p>
            <Button onClick={() => navigate('/pass-lolodrive')} data-testid="visitor-pass-invite-btn"
              style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
              <Star className="w-4 h-4 mr-2" /> Acheter le PASS & créer mon espace
            </Button>
          </div>
        </>
        );
      })()}

      {!loading && !isVisitor && (() => {
        const searching = search.trim().length > 0;
        const pool = products.filter((p) => filter !== 'FAVS' || favs.includes(p.sku));
        const grid = (items, testid) => (
          <div className="grid gap-2.5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))' }} data-testid={testid}>
            {[...items]
              .sort((a, b) => (favs.includes(b.sku) ? 1 : 0) - (favs.includes(a.sku) ? 1 : 0))
              .map((p) => (
                <LolodriveProductCard key={p.sku} p={p} qty={cart[p.sku] || 0} add={add} sub={sub}
                  isFav={favs.includes(p.sku)} toggleFav={toggleFav}
                  promo={promoOf(p)} favPromo={favPromo(p)} discounted={discountedUnit(p)} />
              ))}
          </div>
        );
        // Rayon « Dernière chance » : mini-cartes compactes avec compte à rebours et ajout direct
        const renderLastChance = (items) => (
          <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
            {items.map((p) => (
              <div key={p.sku} className="flex items-center gap-2.5 p-2 rounded-xl bg-white/[0.03] border border-red-400/20"
                data-testid={`last-chance-item-${p.sku}`}>
                <div className="w-10 h-10 rounded-lg overflow-hidden product-thumb-light shrink-0 flex items-center justify-center">
                  {p.photo_url || p.image_url ? (
                    <img src={p.photo_url || p.image_url} alt={p.name} loading="lazy" className="w-full h-full object-contain p-0.5" />
                  ) : (
                    <ShoppingCart className="w-4 h-4 text-black/20" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold text-white truncate">{p.name}</div>
                  <div className="text-[10px] text-red-300 font-bold">
                    ⏱ {promoCountdown([p])} · {fmtEUR(discountedUnit(p) * 3)} le lot
                  </div>
                </div>
                <button type="button" onClick={() => add(p.sku)} data-testid={`last-chance-add-${p.sku}`}
                  title="Ajouter au panier"
                  className="w-7 h-7 rounded-lg flex items-center justify-center text-black font-bold shrink-0"
                  style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                  <Plus className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        );
        // Navigation par clics : catégorie → sous-catégorie → produits
        if (!searching && filter !== 'FAVS') {
          if (pool.length === 0) {
            return <div className="text-center text-white/40 py-12" data-testid="catalog-no-result">Aucun produit disponible pour cette sélection.</div>;
          }
          return <CatalogDrillDown pool={pool} category={category} setCategory={setCategory}
            subcategory={subcategory} setSubcategory={setSubcategory} renderGrid={grid} renderLastChance={renderLastChance} />;
        }
        // Recherche ou favoris : affichage groupé direct
        const visible = applyCatalogFilters(products, { search, category, subcategory })
          .filter((p) => filter !== 'FAVS' || favs.includes(p.sku));
        if (visible.length === 0 && filter !== 'FAVS') {
          return <div className="text-center text-white/40 py-12" data-testid="catalog-no-result">Aucun produit ne correspond à ces filtres.</div>;
        }
        const promos = visible.filter((p) => p.tag === 'PROMO' || p.tag === 'SOLDE');
        return (
          <>
            {promos.length > 0 && (
              <div className="mb-8 rounded-2xl border border-red-400/25 bg-red-500/[0.05] p-3" data-testid="catalog-promos-section">
                <h2 className="text-lg font-bold text-red-300 mb-2 flex items-baseline gap-2">
                  🔥 Promos &amp; Soldes
                  <span className="text-xs font-normal text-white/35">{promos.length} produit(s)</span>
                </h2>
                {grid(promos, 'catalog-promos-inner-grid')}
              </div>
            )}
            {groupByCategory(visible).map((g) => (
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
                {grid(s.items, `catalog-grid-${s.name}`)}
              </div>
            ))}
          </div>
            ))}
          </>
        );
      })()}
    </LolodriveLayout>
  );
}
