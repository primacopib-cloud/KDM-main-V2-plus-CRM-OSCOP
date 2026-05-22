import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShoppingCart, Plus, Minus, Sparkles, Tag, Trash2, Wallet, CreditCard } from 'lucide-react';
import LolodriveLayout, { SectionCard, Badge, fmtEUR } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '../components/ui/sheet';
import { lolodriveAPI, authAPI } from '../services/api';
import { toast } from 'sonner';

export default function LolodriveCatalogPage() {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [filter, setFilter] = useState('');
  const [passActive, setPassActive] = useState(false);
  const [cart, setCart] = useState({});
  const [fulfillment, setFulfillment] = useState('DRIVE');
  const [loloPoints, setLoloPoints] = useState([]);
  const [selectedPoint, setSelectedPoint] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authAPI.isAuthenticated()) {
      navigate('/connexion');
      return;
    }
    (async () => {
      try {
        const [c, lp] = await Promise.all([
          lolodriveAPI.catalogProducts(filter || undefined),
          lolodriveAPI.listLoloPoints(),
        ]);
        setProducts(c.products || []);
        setPassActive(c.pass_active);
        setLoloPoints(lp.points || []);
      } catch (e) {
        toast.error(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [navigate, filter]);

  const add = (sku) => setCart({ ...cart, [sku]: (cart[sku] || 0) + 1 });
  const sub = (sku) => {
    const n = (cart[sku] || 0) - 1;
    const c = { ...cart };
    if (n <= 0) delete c[sku]; else c[sku] = n;
    setCart(c);
  };

  const cartItems = Object.entries(cart).map(([sku, qty]) => ({ sku, qty }));
  const cartTotal = cartItems.reduce((acc, { sku, qty }) => {
    const p = products.find((x) => x.sku === sku);
    return acc + (p?.display_price_cents || 0) * qty;
  }, 0);

  const checkout = async (payInUC) => {
    if (cartItems.length === 0) return toast.error('Panier vide');
    if (fulfillment === 'LOLO_POINT' && !selectedPoint) return toast.error('Choisir un Lolo Point');
    try {
      const order = await lolodriveAPI.createOrder({
        fulfillment_type: fulfillment,
        items: cartItems,
        lolo_point_code: fulfillment === 'LOLO_POINT' ? selectedPoint : undefined,
      });
      toast.success(`Commande ${order.order_number} créée`);
      if (payInUC) {
        await lolodriveAPI.payOrderUC(order.id);
        toast.success('Payée en UC ✅');
        setCart({});
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
      title="Catalogue LOLODRIVE"
      subtitle={passActive
        ? "PASS actif — prix PASS visibles sur les ESSENTIELS, paiement en UC autorisé."
        : "PASS inactif — activez votre PASS pour bénéficier des prix réduits."}
      actions={
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
              <SheetTitle className="text-white">Mon panier</SheetTitle>
            </SheetHeader>
            <div className="mt-4 space-y-2 max-h-[40vh] overflow-y-auto">
              {cartItems.length === 0 && (
                <div className="text-sm text-white/40 text-center py-8">Panier vide</div>
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
                  <span>Sous-total</span>
                  <span>{fmtEUR(cartTotal)}</span>
                </div>
                <div>
                  <label className="text-xs text-white/60">Mode de retrait</label>
                  <Select value={fulfillment} onValueChange={setFulfillment}>
                    <SelectTrigger className="bg-white/[0.04] border-white/10 mt-1" data-testid="fulfillment-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DRIVE">Drive</SelectItem>
                      <SelectItem value="DELIVERY">Livraison</SelectItem>
                      <SelectItem value="LOLO_POINT">Lolo Point</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {fulfillment === 'LOLO_POINT' && (
                  <Select value={selectedPoint} onValueChange={setSelectedPoint}>
                    <SelectTrigger className="bg-white/[0.04] border-white/10" data-testid="lolo-point-select">
                      <SelectValue placeholder="Choisir un Lolo Point" />
                    </SelectTrigger>
                    <SelectContent>
                      {loloPoints.map((p) => (
                        <SelectItem key={p.code} value={p.code}>{p.name} — {p.city}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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
      }
    >
      <Tabs value={filter} onValueChange={setFilter} className="mb-6">
        <TabsList className="bg-white/[0.04] border border-white/10">
          <TabsTrigger value="" data-testid="tab-all">Tous</TabsTrigger>
          <TabsTrigger value="ESSENTIAL" data-testid="tab-essential">Essentiels (25)</TabsTrigger>
          <TabsTrigger value="NORMAL" data-testid="tab-normal">Hors25</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}

      {!loading && (
        <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {products.map((p) => (
            <div key={p.sku} data-testid={`product-${p.sku}`}
              className="rounded-2xl bg-white/[0.025] border border-white/[0.07] overflow-hidden hover:border-white/[0.15] transition-all">
              {p.image_url && (
                <div className="aspect-square bg-white/[0.02] overflow-hidden">
                  <img src={p.image_url} alt={p.name} className="w-full h-full object-cover" />
                </div>
              )}
              <div className="p-3">
                <div className="flex gap-1 mb-2">
                  {p.catalog_type === 'ESSENTIAL'
                    ? <Badge color="#D9B35A"><Sparkles className="w-3 h-3 mr-1 inline" />ESSENTIEL</Badge>
                    : <Badge color="#7c3aed">Hors25</Badge>}
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
