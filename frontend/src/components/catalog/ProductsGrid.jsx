import { useState } from 'react';
import { Loader2, Package, Plus, Play, Lock, ChevronLeft, ChevronRight, X, Link2, MessageSquarePlus, Heart } from 'lucide-react';
import { tData } from '@/i18n/tData';
import i18n from '@/i18n';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { FavoriteButton } from '../FavoriteButton';
import { formatPrice } from './catalogUtils';
import { ProductVideoModal } from './ProductVideoModal';
import { ProductReviewsModal, Stars } from './ProductReviewsModal';

const ProductImageCarousel = ({ product, onZoom }) => {
  const [idx, setIdx] = useState(0);
  const imgs = (product.images && product.images.length > 0)
    ? product.images
    : (product.image_url ? [product.image_url] : []);
  if (imgs.length === 0) return <Package className="w-12 h-12 text-white/20" />;
  const go = (e, delta) => {
    e.stopPropagation();
    setIdx((i) => (i + delta + imgs.length) % imgs.length);
  };
  const current = Math.min(idx, imgs.length - 1);
  return (
    <>
      <img src={imgs[current]} alt={product.name}
        onClick={() => onZoom && onZoom(product, current)}
        data-testid={`product-image-${product.sku}`}
        className="w-full h-full object-cover rounded-xl cursor-zoom-in" loading="lazy" />
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

const ProductLightbox = ({ zoom, onClose }) => {
  const [idx, setIdx] = useState(zoom?.index || 0);
  if (!zoom) return null;
  const { product } = zoom;
  const imgs = (product.images && product.images.length > 0)
    ? product.images
    : (product.image_url ? [product.image_url] : []);
  const current = Math.min(idx, imgs.length - 1);
  return (
    <div className="fixed inset-0 z-[100] bg-black/85 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose} data-testid="product-lightbox">
      <button type="button" onClick={onClose} data-testid="lightbox-close"
        className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center">
        <X className="w-5 h-5" />
      </button>
      <div className="max-w-3xl w-full" onClick={(e) => e.stopPropagation()}>
        <div className="relative">
          <img src={imgs[current]} alt={product.name}
            className="w-full max-h-[75vh] object-contain rounded-2xl bg-white/[0.03]" />
          {imgs.length > 1 && (
            <>
              <button type="button" data-testid="lightbox-prev"
                onClick={() => setIdx((i) => (i - 1 + imgs.length) % imgs.length)}
                className="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center">
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button type="button" data-testid="lightbox-next"
                onClick={() => setIdx((i) => (i + 1) % imgs.length)}
                className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center">
                <ChevronRight className="w-5 h-5" />
              </button>
            </>
          )}
        </div>
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-white font-semibold text-sm">{product.name}</p>
          {imgs.length > 1 && (
            <div className="flex gap-2">
              {imgs.map((im, i) => (
                <button key={i} type="button" onClick={() => setIdx(i)}
                  className={`w-12 h-12 rounded-lg overflow-hidden border-2 ${i === current ? 'border-[#D9B35A]' : 'border-transparent opacity-60'}`}>
                  <img src={im} alt="" className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export const ProductsGrid = ({ products, cart, cartLoading, handleAddToCart }) => {
  const [videoProduct, setVideoProduct] = useState(null);
  const [zoom, setZoom] = useState(null);
  const [reviewsProduct, setReviewsProduct] = useState(null);
  const lang = (i18n.language || 'fr').slice(0, 2);
  const tr = (p) => (lang !== 'fr' && p.translations?.[lang]) || {};
  const copyLink = (product) => {
    const url = `${window.location.origin}/catalogue?produit=${product.id}`;
    const done = () => toast.success(i18n.t('catalog.lien_copie', 'Lien de la fiche produit copié !'));
    const fallback = () => {
      const ta = document.createElement('textarea');
      ta.value = url;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); done(); }
      catch { toast.error(i18n.t('catalog.lien_erreur', 'Impossible de copier le lien')); }
      document.body.removeChild(ta);
    };
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(url).then(done).catch(fallback);
    } else fallback();
  };
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
                <ProductImageCarousel product={product} onZoom={(p, index) => setZoom({ product: p, index })} />
                {/* Badge coup de cœur (note >= 4.5) */}
                {product.rating_avg >= 4.5 && (
                  <span
                    data-testid={`product-top-badge-${product.sku}`}
                    className="absolute top-2 left-2 inline-flex items-center gap-1.5 h-7 px-2.5 rounded-full text-[11px] font-semibold text-white shadow-lg"
                    style={{ background: 'linear-gradient(90deg, #C0392B, #E74C3C)' }}
                  >
                    <Heart size={11} fill="currentColor" />
                    {i18n.t('catalog.coup_de_coeur', 'Coup de cœur des adhérents')}
                  </span>
                )}
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
              <p className="text-xs text-white/50 mb-2">{product.sku} · {product.unit_quantity} {product.unit}</p>

              {/* Avis + partage */}
              <div className="flex items-center justify-between gap-2 mb-2">
                <button type="button" onClick={() => setReviewsProduct(product)}
                  data-testid={`product-reviews-btn-${product.sku}`}
                  className="inline-flex items-center gap-1.5 text-xs text-white/60 hover:text-[#D9B35A] transition-colors">
                  {product.rating_count > 0 ? (
                    <>
                      <Stars value={product.rating_avg} size={12} />
                      <span className="font-semibold text-[#D9B35A]">{product.rating_avg}</span>
                      <span>({product.rating_count})</span>
                    </>
                  ) : (
                    <>
                      <MessageSquarePlus className="w-3.5 h-3.5" />
                      {i18n.t('catalog.donner_avis', 'Donner un avis')}
                    </>
                  )}
                </button>
                <button type="button" onClick={() => copyLink(product)}
                  title={i18n.t('catalog.copier_lien', 'Copier le lien de la fiche')}
                  data-testid={`product-share-btn-${product.sku}`}
                  className="text-white/50 hover:text-[#D9B35A] transition-colors">
                  <Link2 className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Incoterms badges */}
              {product.incoterms && Object.keys(product.incoterms).length > 0 && (
                <div className="flex flex-wrap gap-1 mb-3" data-testid={`product-incoterms-${product.sku}`}>
                  {[...new Set(Object.values(product.incoterms).flat())].map((code) => (
                    <span
                      key={code}
                      title={`Incoterm ${code} — ${Object.entries(product.incoterms).filter(([, c]) => (c || []).includes(code)).map(([z]) => z).join(', ')}`}
                      className="px-1.5 py-0.5 rounded text-[9px] font-bold tracking-wide bg-[#D9B35A]/15 text-[#D9B35A] border border-[#D9B35A]/30"
                    >
                      {code}
                    </span>
                  ))}
                </div>
              )}
              
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
        {reviewsProduct && <ProductReviewsModal product={reviewsProduct} onClose={() => setReviewsProduct(null)} />}
        {zoom && <ProductLightbox key={`${zoom.product.id}-${zoom.index}`} zoom={zoom} onClose={() => setZoom(null)} />}
  </>
  );
};
