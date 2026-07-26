import { useEffect, useState } from 'react';
import { Zap, Coins } from 'lucide-react';
import { Badge } from '../ui/badge';
import { formatPrice } from './catalogUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
let promoCache = null;

export const useCatalogPromos = () => {
  const [promos, setPromos] = useState(promoCache || []);
  useEffect(() => {
    if (promoCache) return;
    fetch(`${API}/public/catalog-promos`)
      .then((r) => (r.ok ? r.json() : { promotions: [] }))
      .then((d) => { promoCache = d.promotions || []; setPromos(promoCache); })
      .catch(() => {});
  }, []);
  return promos;
};

const matchesProduct = (promo, product) => {
  const cat = (promo.scope_category || 'all').toLowerCase();
  if (cat !== 'all') {
    const names = [product.category_id, product.category_name, product.category]
      .filter(Boolean).map((s) => String(s).toLowerCase());
    if (!names.includes(cat)) return false;
  }
  const pt = (promo.scope_product_type || 'all').toLowerCase();
  if (pt !== 'all' && pt !== (product.product_type || '').toLowerCase()) return false;
  if (promo.scope_brand && promo.scope_brand.toLowerCase() !== (product.brand || '').toLowerCase()) return false;
  return true;
};

export const bestPromos = (promos, product) => {
  let discount = null;
  let bonus = null;
  promos.forEach((p) => {
    if (!matchesProduct(p, product)) return;
    if (p.promo_type === 'discount_action' && (!discount || p.value_percent > discount.value_percent)) discount = p;
    if (p.promo_type === 'bonus_purchase' && (!bonus || p.value_percent > bonus.value_percent)) bonus = p;
  });
  return { discount, bonus };
};

export const PassLolodriveBadge = ({ sku }) => (
  <span
    data-testid={`pass-lolodrive-badge-${sku}`}
    className="inline-flex items-center gap-1 h-5 px-1.5 rounded-full text-[9px] font-bold uppercase tracking-wide text-[#E9CF8E] border border-[#D9B35A]/40 bg-[#D9B35A]/10"
  >
    <img src="/lolodrive-logo.jpg" alt="" className="w-3.5 h-3.5 rounded-full bg-white object-contain" />
    PASS LOLODRIVE
  </span>
);

export const PromoPriceBlock = ({ product, discount, bonus }) => {
  const price = product.price_ht_cents;
  const promoPrice = discount ? Math.round(price * (1 - discount.value_percent / 100)) : price;
  const bonusUc = bonus ? Math.round((promoPrice / 100) * bonus.value_percent / 100 * 10) : 0;
  return (
    <div data-testid={`promo-price-block-${product.sku}`}>
      {(discount || bonus || product.savings_percent) && (
        <div className="flex flex-wrap items-center gap-1 mb-1">
          {discount && (
            <Badge data-testid={`promo-flash-badge-${product.sku}`}
              className="border-0 text-[10px] font-black text-black px-1.5"
              style={{ background: 'linear-gradient(90deg, #FF4D4D, #D9B35A)' }}
              title={discount.name}>
              <Zap className="w-3 h-3 mr-0.5" fill="currentColor" /> -{discount.value_percent}%
            </Badge>
          )}
          {!discount && product.savings_percent && (
            <Badge className="bg-[#D4AF37]/20 text-[#D4AF37] border-0 text-[10px]">
              -{product.savings_percent}%
            </Badge>
          )}
          {bonus && (
            <Badge data-testid={`promo-bonus-uc-badge-${product.sku}`}
              className="bg-[#7BC94E]/20 text-[#7BC94E] border border-[#7BC94E]/40 text-[10px] font-bold px-1.5"
              title={bonus.name}>
              <Coins className="w-3 h-3 mr-0.5" /> +{bonus.value_percent}% UC
            </Badge>
          )}
        </div>
      )}
      <p className="text-lg font-bold text-[#D9B35A]">
        {formatPrice(promoPrice)} <span className="text-xs font-normal text-white/50">HT</span>
      </p>
      {discount && (
        <p className="text-xs text-white/40 line-through" data-testid={`promo-old-price-${product.sku}`}>
          {formatPrice(price)}
        </p>
      )}
      {!discount && product.original_price_ht_cents && (
        <p className="text-xs text-white/40 line-through">
          {formatPrice(product.original_price_ht_cents)}
        </p>
      )}
      {bonus && bonusUc > 0 && (
        <p className="text-[10px] font-semibold text-[#7BC94E]" data-testid={`promo-bonus-uc-hint-${product.sku}`}>
          ≈ +{bonusUc} UC crédités
        </p>
      )}
    </div>
  );
};
