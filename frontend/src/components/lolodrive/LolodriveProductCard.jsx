import { Plus, Minus, Star, Package } from 'lucide-react';
import { fmtEUR } from '../LolodriveLayout';
import { PassLolodriveBadge } from '../catalog/ProductPromoBadges';
import { TagBadge, LotBadge } from './ProductTagBadge';

// Carte produit compacte du catalogue client LOLODRIVE : densité élevée, hauteur uniforme, fallback image propre
export const LolodriveProductCard = ({ p, qty, add, sub, isFav, toggleFav, promo, favPromo, discounted }) => (
  <div data-testid={`product-${p.sku}`}
    className={`flex flex-col rounded-xl bg-white/[0.025] border overflow-hidden hover:border-[#D9B35A]/35 transition-colors ${isFav ? 'border-[#D9B35A]/40' : 'border-white/[0.07]'}`}>
    <div className="relative h-24 bg-white/[0.03] shrink-0">
      {p.image_url && (
        <img src={p.image_url} alt={p.name} loading="lazy" className="w-full h-full object-cover"
          onError={(e) => { e.currentTarget.style.display = 'none'; e.currentTarget.nextElementSibling.style.display = 'flex'; }} />
      )}
      <div className="absolute inset-0 items-center justify-center" style={{ display: p.image_url ? 'none' : 'flex' }}>
        <Package className="w-8 h-8 text-white/15" />
      </div>
      <button type="button" onClick={() => toggleFav(p.sku)} data-testid={`fav-toggle-${p.sku}`}
        title={isFav ? 'Retirer des favoris' : 'Épingler en haut du catalogue'}
        className="absolute top-1 right-1 z-10 w-6 h-6 rounded-full flex items-center justify-center bg-black/55 backdrop-blur-sm border border-white/15 hover:border-[#D9B35A]/60 transition-colors">
        <Star className={`w-3 h-3 ${isFav ? 'fill-[#D9B35A] text-[#D9B35A]' : 'text-white/50'}`} />
      </button>
      <div className="absolute top-1 left-1 flex flex-wrap gap-1 text-[8px] font-bold pr-7">
        {p.catalog_type === 'ESSENTIAL'
          ? <span className="px-1 py-0.5 rounded text-[#D9B35A] bg-black/60 border border-[#D9B35A]/40 backdrop-blur-sm">ESSENTIEL</span>
          : <span className="px-1 py-0.5 rounded text-[#c4b5fd] bg-black/60 border border-[#7c3aed]/40 backdrop-blur-sm">HORS-25</span>}
        {p.point_code && <span className="px-1 py-0.5 rounded text-emerald-300 bg-black/60 border border-emerald-400/40 backdrop-blur-sm">Relais {p.point_code}</span>}
        <TagBadge tag={p.tag} sku={p.sku} />
        <LotBadge p={p} />
      </div>
      {favPromo && (
        <span data-testid={`fav-promo-band-${p.sku}`} title={favPromo.name}
          className="absolute bottom-1 left-1 z-10 px-1.5 py-0.5 rounded text-[10px] font-black text-black shadow-lg"
          style={{ background: 'linear-gradient(90deg, #FF4D4D, #D9B35A)' }}>
          ⚡ -{favPromo.value_percent}%
        </span>
      )}
    </div>
    <div className="p-2 flex flex-col flex-1">
      <div className="font-medium text-[11px] leading-tight line-clamp-2 min-h-[26px]">{p.name}</div>
      <div className="text-[9px] text-white/40 truncate mb-1">{p.brand ? `${p.brand} · ` : ''}{p.subcategory || p.sku}</div>
      <div className="mb-1"><PassLolodriveBadge sku={p.sku} /></div>
      <div className="flex items-end justify-between gap-1 mb-1.5">
        <div>
          {promo ? (
            <>
              <span className="text-sm font-bold text-[#FF9E7A]" data-testid={`promo-price-${p.sku}`}>{fmtEUR(discounted)}</span>
              <span className="text-[10px] text-white/40 line-through ml-1" data-testid={`promo-old-price-${p.sku}`}>{fmtEUR(p.display_price_cents)}</span>
            </>
          ) : (
            <span className="text-sm font-bold">{fmtEUR(p.display_price_cents)}</span>
          )}
          {p.display_uc != null && <span className="block text-[10px] text-[#D9B35A]">{p.display_uc} UC</span>}
        </div>
        {p.catalog_type === 'ESSENTIAL' && p.price_pass_cents && p.price_public_cents > p.price_pass_cents && (
          <span className="text-[9px] font-bold text-emerald-300 bg-emerald-400/10 border border-emerald-400/30 rounded px-1 py-0.5 shrink-0">
            -{Math.round(((p.price_public_cents - p.price_pass_cents) / p.price_public_cents) * 100)}%
          </span>
        )}
      </div>
      <div className="flex items-center gap-1.5 mt-auto">
        <button type="button" onClick={() => sub(p.sku)} disabled={!qty} data-testid={`btn-sub-${p.sku}`}
          className="w-7 h-7 rounded-lg flex items-center justify-center bg-white/[0.05] border border-white/15 text-white/70 disabled:opacity-30 hover:border-white/30">
          <Minus className="w-3 h-3" />
        </button>
        <span className="flex-1 text-center text-xs font-mono">{qty || 0}</span>
        <button type="button" onClick={() => add(p.sku)} data-testid={`btn-add-${p.sku}`}
          className="w-7 h-7 rounded-lg flex items-center justify-center text-black font-bold"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
          <Plus className="w-3 h-3" />
        </button>
      </div>
    </div>
  </div>
);
