import { Plus, Minus, Sparkles, Star } from 'lucide-react';
import { Badge, fmtEUR } from '../LolodriveLayout';
import { PassLolodriveBadge } from '../catalog/ProductPromoBadges';
import { Button } from '../ui/button';
import i18n from '@/i18n';

// Carte produit du catalogue client LOLODRIVE (extrait de LolodriveCatalogPage)
export const LolodriveProductCard = ({ p, qty, add, sub, isFav, toggleFav, promo, favPromo, discounted }) => (
  <div data-testid={`product-${p.sku}`}
    className={`relative rounded-2xl bg-white/[0.025] border overflow-hidden hover:border-white/[0.15] transition-all ${isFav ? 'border-[#D9B35A]/40' : 'border-white/[0.07]'}`}>
    <button type="button" onClick={() => toggleFav(p.sku)} data-testid={`fav-toggle-${p.sku}`}
      title={isFav ? 'Retirer des favoris' : 'Épingler en haut du catalogue'}
      className="absolute top-2 right-2 z-10 w-8 h-8 rounded-full flex items-center justify-center bg-black/50 backdrop-blur-sm border border-white/15 hover:border-[#D9B35A]/60 transition-colors">
      <Star className={`w-4 h-4 ${isFav ? 'fill-[#D9B35A] text-[#D9B35A]' : 'text-white/50'}`} />
    </button>
    {favPromo && (
      <span data-testid={`fav-promo-band-${p.sku}`} title={favPromo.name}
        className="absolute top-2 left-2 z-10 px-2 py-1 rounded-lg text-[11px] font-black text-black shadow-lg"
        style={{ background: 'linear-gradient(90deg, #FF4D4D, #D9B35A)' }}>
        ⚡ -{favPromo.value_percent}%
      </span>
    )}
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
        {p.point_code && <Badge color="#10b981">Relais {p.point_code}</Badge>}
        <PassLolodriveBadge sku={p.sku} />
      </div>
      <div className="font-medium text-sm leading-tight mb-1">{p.name}</div>
      <div className="text-xs text-white/40 mb-3">{p.brand} · {p.subcategory || p.sku}</div>
      <div className="flex items-end justify-between mb-3">
        <div>
          {promo ? (
            <>
              <div className="text-lg font-bold text-[#FF9E7A]" data-testid={`promo-price-${p.sku}`}>
                {fmtEUR(discounted)}
              </div>
              <div className="text-xs text-white/40 line-through" data-testid={`promo-old-price-${p.sku}`}>
                {fmtEUR(p.display_price_cents)}
              </div>
            </>
          ) : (
            <div className="text-lg font-bold">{fmtEUR(p.display_price_cents)}</div>
          )}
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
          disabled={!qty} data-testid={`btn-sub-${p.sku}`}>
          <Minus className="w-3 h-3" />
        </Button>
        <span className="flex-1 text-center text-sm">{qty || 0}</span>
        <Button size="sm" onClick={() => add(p.sku)} data-testid={`btn-add-${p.sku}`}
          style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
          <Plus className="w-3 h-3" />
        </Button>
      </div>
    </div>
  </div>
);
