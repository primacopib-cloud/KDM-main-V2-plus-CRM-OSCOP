import { useState } from 'react';
import { Loader2, Package, Plus, Play, Lock, ChevronLeft, ChevronRight } from 'lucide-react';
import { tData } from '@/i18n/tData';
import i18n from '@/i18n';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { FavoriteButton } from '../FavoriteButton';
import { formatPrice } from './catalogUtils';
import { ProductVideoModal } from './ProductVideoModal';

const ProductImageCarousel = ({ product }) => {
  const [idx, setIdx] = useState(0);
  const imgs = (product.images && product.images.length > 0)
    ? product.images
    : (product.image_url ? [product.image_url] : []);
  if (imgs.length === 0) return <Package className="w-12 h-12 text-white/20" />;
  const go = (e, delta) => {
    e.stopPropagation();
    setIdx((i) => (i + delta + imgs.length) % imgs.length);
  };
  return (
    <>
      <img src={imgs[Math.min(idx, imgs.length - 1)]} alt={product.name}
        className="w-full h-full object-cover rounded-xl" loading="lazy" />
      {imgs.length > 1 && (
        <>
          <button type="button" onClick={(e) => go(e, -1)}
            data-testid={`carousel-prev-${product.sku}`}
            className="absolute left-1.5 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/50 hover:bg-black/70 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button type="button" onClick={(e) => go(e, 1)}
            data-testid={`carousel-next-${product.sku}`}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/50 hover:bg-black/70 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <ChevronRight className="w-4 h-4" />
          </button>
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1.5" data-testid={`carousel-dots-${product.sku}`}>
            {imgs.map((_, i) => (
              <button key={i} type="button"
                onClick={(e) => { e.stopPropagation(); setIdx(i); }}
                className={`w-1.5 h-1.5 rounded-full transition-colors ${i === idx ? 'bg-[#D9B35A]' : 'bg-white/40'}`} />
            ))}
          </div>
        </>
      )}
    </>
  );
};

export const ProductsGrid = ({ products, cart, cartLoading, handleAddToCart }) => {
  const [videoProduct, setVideoProduct] = useState(null);
  const lang = (i18n.language || 'fr').slice(0, 2);
  const tr = (p) => (lang !== 'fr' && p.translations?.[lang]) || {};
  return (
  <>
        {/* Products Grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {products.map(product => (
            <div 
              key={product.id}
              className="glass-panel-soft rounded-[18px] p-4 flex flex-col group"
              data-testid={`product-card-${product.sku}`}
            >
              {/* Product Image gallery (carousel jusqu'à 3 photos) */}
              <div className="aspect-square rounded-xl bg-white/[0.04] mb-4 flex items-center justify-center relative overflow-hidden">
                <ProductImageCarousel product={product} />
                {/* Favorite button - positioned top right */}
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <FavoriteButton 
                    productId={product.id} 
                    productName={product.name}
                    size="sm"
                  />
                </div>
                {/* Spot vidéo badge */}
                {product.video_url && (
                  <button type="button"
                    onClick={() => setVideoProduct(product)}
                    data-testid={`product-video-badge-${product.sku}`}
                    className="absolute bottom-2 left-2 inline-flex items-center gap-1.5 h-7 px-2.5 rounded-full text-[11px] font-semibold text-black bg-[#D9B35A] hover:bg-[#c9a34a] transition-colors shadow-lg">
                    <Play size={11} fill="currentColor" /> Spot vidéo
                  </button>
                )}
              </div>
              
              {/* Category badge */}
              <Badge variant="outline" className="w-fit mb-2 text-[10px] text-white/60 border-white/20">
                {tData(product.category_name) || tData('Produit')}
              </Badge>
              
              {/* Product info */}
              <h3 className="font-medium text-white/90 mb-1 line-clamp-2">{tr(product).name || product.name}</h3>
              {(tr(product).short_description || tr(product).description || product.description) && (
                <p className="text-xs text-white/55 mb-1 line-clamp-2" data-testid={`product-desc-${product.sku}`}>
                  {tr(product).short_description || tr(product).description || product.description}
                </p>
              )}
              <p className="text-xs text-white/50 mb-3">{product.sku} · {product.unit_quantity} {product.unit}</p>
              
              {/* Price & Add to cart */}
              <div className="mt-auto flex items-end justify-between">
                <div>
                  {product.price_visible ? (
                    <>
                      {product.savings_percent && (
                        <Badge className="mb-1 bg-[#D4AF37]/20 text-[#D4AF37] border-0 text-[10px]">
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
                    <div data-testid={`price-locked-${product.sku}`}>
                      <p className="text-lg font-bold text-[#D9B35A] blur-[6px] select-none" aria-hidden="true">
                        {(((product.sku || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0) % 3200) / 100 + 6).toFixed(2).replace('.', ',')} € <span className="text-xs font-normal text-white/50">HT</span>
                      </p>
                      <p className="flex items-center gap-1 text-[10px] text-[#D9B35A]/90 mt-0.5">
                        <Lock className="w-3 h-3" />
                        {i18n.t('catalog.tarif_adherent', 'Tarif réservé aux adhérents')}
                      </p>
                    </div>
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
        {videoProduct && <ProductVideoModal product={videoProduct} onClose={() => setVideoProduct(null)} />}
  </>
  );
};
