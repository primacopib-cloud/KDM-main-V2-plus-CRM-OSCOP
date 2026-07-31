import { Package, Plus, Boxes, History } from 'lucide-react';
import { TagBadge, LotBadge } from '../lolodrive/ProductTagBadge';

// Carte produit compacte du catalogue POS : densité élevée, hauteur uniforme, fallback image propre
export const PosProductCard = ({ p, count, stockEdit, setStockEdit, saveStock, onHistory, onSell }) => (
  <div data-testid={`pos-product-${p.sku}`}
    className="flex flex-col rounded-xl bg-white/[0.025] border border-white/[0.07] overflow-hidden hover:border-[#D9B35A]/35 transition-colors">
    <div className="relative h-20 bg-white/[0.03] shrink-0">
      {p.image_url && (
        <img src={p.image_url} alt={p.name} loading="lazy" className="w-full h-full object-cover"
          onError={(e) => { e.currentTarget.style.display = 'none'; e.currentTarget.nextElementSibling.style.display = 'flex'; }} />
      )}
      <div className="absolute inset-0 items-center justify-center" style={{ display: p.image_url ? 'none' : 'flex' }}>
        <Package className="w-7 h-7 text-white/15" />
      </div>
      <div className="absolute top-1 left-1 flex flex-wrap gap-1 text-[8px] font-bold">
        {p.catalog_type === 'ESSENTIAL'
          ? <span className="px-1 py-0.5 rounded text-[#D9B35A] bg-black/60 border border-[#D9B35A]/40 backdrop-blur-sm">ESSENTIEL</span>
          : <span className="px-1 py-0.5 rounded text-[#c4b5fd] bg-black/60 border border-[#7c3aed]/40 backdrop-blur-sm">HORS-25</span>}
        {p.point_code && <span className="px-1 py-0.5 rounded text-emerald-300 bg-black/60 border border-emerald-400/40 backdrop-blur-sm">Relais {p.point_code}</span>}
        <TagBadge tag={p.tag} sku={p.sku} />
        <LotBadge p={p} />
      </div>
    </div>
    <div className="p-2 flex flex-col flex-1">
      <div className="font-medium text-[11px] leading-tight line-clamp-2 min-h-[26px]">{p.name}</div>
      <div className="text-[9px] text-white/35 truncate mb-1">{p.brand ? `${p.brand} · ` : ''}{p.subcategory || p.category || p.sku}</div>
      <div className="mb-1.5">
        <span className="text-xs font-bold font-mono">{(p.price_public_cents / 100).toFixed(2)} €</span>
        <span className="text-[9px] text-[#D9B35A] font-mono"> · {p.uc_public} UC</span>
        {p.price_pass_cents != null && (
          <span className="block text-[9px] text-white/40 font-mono">PASS {(p.price_pass_cents / 100).toFixed(2)} € · {p.uc_pass} UC</span>
        )}
        {p.is_lot && p.lot_ref_price_cents > p.price_public_cents && (
          <span className="block text-[9px] text-emerald-300 font-mono" data-testid={`lot-savings-pos-${p.sku}`}>
            au lieu de <s className="text-white/35">{(p.lot_ref_price_cents / 100).toFixed(2)} €</s> · −{Math.round(((p.lot_ref_price_cents - p.price_public_cents) / p.lot_ref_price_cents) * 100)} %
          </span>
        )}
      </div>
      <div className="flex items-center gap-1 mb-1.5 mt-auto">
        {stockEdit?.sku === p.sku ? (
          <span className="flex items-center gap-1">
            <input type="number" min="0" autoFocus value={stockEdit.value} data-testid={`stock-input-${p.sku}`}
              onChange={(e) => setStockEdit({ ...stockEdit, value: e.target.value })}
              onKeyDown={(e) => { if (e.key === 'Enter') saveStock(); if (e.key === 'Escape') setStockEdit(null); }}
              className="w-14 px-1.5 py-0.5 rounded bg-white/10 border border-[#D9B35A]/50 text-white text-[10px] font-mono" />
            <button type="button" onClick={saveStock} data-testid={`stock-save-${p.sku}`}
              className="px-1.5 py-0.5 rounded text-[9px] font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a]">OK</button>
          </span>
        ) : (
          <button type="button" title="Ajuster le stock (réassort)" data-testid={`stock-badge-${p.sku}`}
            onClick={() => setStockEdit({ sku: p.sku, value: p.stock_qty ?? '' })}
            className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold border ${
              p.stock_qty == null ? 'text-white/40 bg-white/[0.04] border-white/10'
                : p.stock_qty <= 5 ? 'text-red-300 bg-red-500/10 border-red-400/35'
                  : p.stock_qty <= 15 ? 'text-amber-300 bg-amber-400/10 border-amber-400/35'
                    : 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30'
            } hover:brightness-125`}>
            <Boxes className="w-2.5 h-2.5" /> {p.stock_qty == null ? 'Stock ?' : p.stock_qty}
          </button>
        )}
        <button type="button" title="Historique du stock" data-testid={`stock-history-btn-${p.sku}`}
          onClick={onHistory}
          className="w-5 h-5 rounded-full flex items-center justify-center bg-white/[0.05] border border-white/10 text-white/50 hover:text-[#D9B35A] hover:border-[#D9B35A]/40 shrink-0">
          <History className="w-2.5 h-2.5" />
        </button>
      </div>
      <button type="button" onClick={onSell} data-testid={`sale-add-${p.sku}`}
        disabled={p.stock_qty === 0}
        title={p.stock_qty === 0 ? 'Rupture de stock — vente impossible' : 'Ajouter à la vente au comptoir'}
        className={`w-full flex items-center justify-center gap-1 py-1 rounded-lg text-[11px] font-bold border ${
          p.stock_qty === 0
            ? 'bg-white/[0.03] border-white/10 text-white/25 cursor-not-allowed'
            : 'bg-[#D9B35A]/15 border-[#D9B35A]/40 text-[#D9B35A] hover:bg-[#D9B35A]/30'
        }`}>
        <Plus className="w-3 h-3" /> {p.stock_qty === 0 ? 'Rupture' : 'Vendre'}
        {count ? <span className="ml-1 px-1.5 rounded-full bg-[#D9B35A] text-black">{count}</span> : null}
      </button>
    </div>
  </div>
);
