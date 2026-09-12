import { Timer, Package } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Badge } from '../ui/badge';
import { tData } from '@/i18n/tData';

const eur = (cents) => `${((cents || 0) / 100).toFixed(2).replace('.', ',')} €`;

export const ProductSheetModal = ({ product, onClose }) => {
  if (!product) return null;
  const imgs = (product.images || []).map((i) => i.url || i).filter(Boolean);
  const incoterms = [...new Set([
    ...(product.incoterms ? Object.values(product.incoterms).flat() : []),
    ...(product.incoterm ? [product.incoterm] : []),
  ])];
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl bg-[#2c1247] border-white/15 text-white max-h-[85vh] overflow-y-auto" data-testid="product-sheet-modal">
        <DialogHeader>
          <DialogTitle className="text-xl text-white pr-8" data-testid="product-sheet-title">
            {tData(product.name) || product.name}
          </DialogTitle>
        </DialogHeader>
        <div className="grid sm:grid-cols-2 gap-5">
          <div className="rounded-xl overflow-hidden bg-white/5 aspect-square flex items-center justify-center">
            {imgs.length > 0 ? (
              <img src={imgs[0]} alt={product.name} className="w-full h-full object-cover" />
            ) : (
              <Package className="w-16 h-16 text-white/20" />
            )}
          </div>
          <div className="space-y-3">
            {product.promo_days_left != null && (
              <div className="w-fit px-3 py-1.5 rounded-md text-xs font-bold flex items-center gap-1.5 text-black bg-[#D9B35A] shadow-lg animate-pulse"
                data-testid="product-sheet-promo-countdown">
                <Timer size={13} />
                Promo — se termine dans {product.promo_days_left} jour{product.promo_days_left > 1 ? 's' : ''}
              </div>
            )}
            {product.price_visible && product.price_ht_cents ? (
              <div data-testid="product-sheet-price">
                {product.savings_percent ? (
                  <Badge className="bg-[#D4AF37]/20 text-[#D4AF37] border-0 text-xs mb-1">-{product.savings_percent}%</Badge>
                ) : null}
                <p className="text-3xl font-bold text-[#D9B35A]">
                  {eur(product.price_ht_cents)} <span className="text-sm font-normal text-white/50">HT</span>
                </p>
                {product.original_price_ht_cents && product.original_price_ht_cents > product.price_ht_cents && (
                  <p className="text-base text-white/40 line-through" data-testid="product-sheet-old-price">
                    {eur(product.original_price_ht_cents)}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-[#D9B35A]/90">Tarif réservé aux adhérents</p>
            )}
            <p className="text-xs text-white/50">Réf. {product.sku}{product.unit ? ` · ${product.unit}` : ''}</p>
            {product.description && (
              <p className="text-sm text-white/75 leading-relaxed" data-testid="product-sheet-description">
                {tData(product.description) || product.description}
              </p>
            )}
            {(product.available_zones || []).length > 0 && (
              <div className="flex flex-wrap items-center gap-1">
                <span className="text-[10px] uppercase tracking-wide text-white/40">Zones :</span>
                {product.available_zones.map((z) => (
                  <span key={z} className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">{z}</span>
                ))}
              </div>
            )}
            {incoterms.length > 0 && (
              <div className="flex flex-wrap items-center gap-1">
                <span className="text-[10px] uppercase tracking-wide text-white/40">Incoterms :</span>
                {incoterms.map((c) => (
                  <span key={c} className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#D9B35A]/15 text-[#D9B35A] border border-[#D9B35A]/30">{c}</span>
                ))}
              </div>
            )}
            {!product.in_stock && (
              <p className="text-xs text-red-400">Rupture de stock sur ce territoire</p>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
