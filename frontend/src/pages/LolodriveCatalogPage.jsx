import i18n from '@/i18n';
import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShoppingCart, Plus, Minus, Sparkles, Tag, Trash2, Wallet, CreditCard, ArrowLeft, Star } from 'lucide-react';
import LolodriveLayout, { SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '../components/ui/sheet';
import { lolodriveAPI, authAPI } from '../services/api';
import { toast } from 'sonner';
import TerritorySelector, { getInitialTerritory } from '../components/TerritorySelector';
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
          lolodriveAPI.catalogProducts(filter || undefined, territory || undefined),
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
    return next;
  });
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
    return acc + (p?.display_price_cents || 0) * qty;
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
                      <div className="text-xs text-white/40">{fmtEUR(p.display_price_cents)} × {qty}</div>
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

      <Tabs value={filter} onValueChange={setFilter} className="mb-6">
        <TabsList className="bg-white/[0.04] border border-white/10">
          <TabsTrigger value="" data-testid="tab-all">{i18n.t('lolodrive.tous')}</TabsTrigger>
          <TabsTrigger value="ESSENTIAL" data-testid="tab-essential">{i18n.t('lolodrive.essentiels_25')}</TabsTrigger>
          <TabsTrigger value="NORMAL" data-testid="tab-normal">{i18n.t('lolodrive.hors25')}</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading && <div className="text-center text-white/50 py-12">{i18n.t('lolodrive.chargement')}</div>}

      {!loading && (
        <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...products].sort((a, b) => (favs.includes(b.sku) ? 1 : 0) - (favs.includes(a.sku) ? 1 : 0)).map((p) => (
            <div key={p.sku} data-testid={`product-${p.sku}`}
              className={`relative rounded-2xl bg-white/[0.025] border overflow-hidden hover:border-white/[0.15] transition-all ${favs.includes(p.sku) ? 'border-[#D9B35A]/40' : 'border-white/[0.07]'}`}>
              <button type="button" onClick={() => toggleFav(p.sku)} data-testid={`fav-toggle-${p.sku}`}
                title={favs.includes(p.sku) ? 'Retirer des favoris' : 'Épingler en haut du catalogue'}
                className="absolute top-2 right-2 z-10 w-8 h-8 rounded-full flex items-center justify-center bg-black/50 backdrop-blur-sm border border-white/15 hover:border-[#D9B35A]/60 transition-colors">
                <Star className={`w-4 h-4 ${favs.includes(p.sku) ? 'fill-[#D9B35A] text-[#D9B35A]' : 'text-white/50'}`} />
              </button>
              {p.image_url && (
                <div className="aspect-square bg-white/[0.02] overflow-hidden">
                  <img src={p.image_url} alt={p.name} className="w-full h-full object-cover" />
                </div>
              )}
              <div className="p-3">
                <div className="flex flex-wrap gap-1 mb-2">
                  {p.catalog_type === 'ESSENTIAL'
                    ? <Badge color="#D9B35A"><Sparkles className="w-3 h-3 mr-1 inline" />ESSENTIEL</Badge>
                    : <Badge color="#7c3aed">{i18n.t('lolodrive.hors25')}</Badge>}
                  <PassLolodriveBadge sku={p.sku} />
                </div>
                <div className="font-medium text-sm leading-tight mb-1">{p.name}</div>
                <div className="text-xs text-white/40 mb-3">{p.brand} · {p.sku}</div>
                <div className="flex items-end justify-between mb-3">
                  <div>
                    <div className="text-lg font-bold">{fmtEUR(p.display_price_cents)}</div>
                    {p.display_uc != null && (
                      <div className="text-xs text-[#D9B35A]">{p.display_uc} UC</div>
                    )}
                  </div>
                  {p.catalog_type === 'ESSENTIAL' && p.price_pass_cents && p.price_public_cents > p.price_pass_cents && (
                    <Badge color="#10b981">
                      -{Math.round(((p.price_public_cents - p.price_pass_cents) / p.price_public_cents) * 100)}%
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" onClick={() => sub(p.sku)}
                    disabled={!cart[p.sku]} data-testid={`btn-sub-${p.sku}`}>
                    <Minus className="w-3 h-3" />
                  </Button>
                  <span className="flex-1 text-center text-sm">{cart[p.sku] || 0}</span>
                  <Button size="sm" onClick={() => add(p.sku)} data-testid={`btn-add-${p.sku}`}
                    style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
                    <Plus className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </LolodriveLayout>
  );
}
