import { Loader2, Package, Plus } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { FavoriteButton } from '../FavoriteButton';
import { formatPrice } from './catalogUtils';

export const ProductsGrid = ({ products, cart, cartLoading, handleAddToCart }) => (
  <>
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
                {tData(product.category_name) || tData('Produit')}
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
  </>
);
