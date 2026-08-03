import { Package, Edit, Trash2, Rocket, Sparkles } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { CATEGORIES, formatPrice } from './constants';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const ProductRow = ({
  product, checked, onToggle, pricingId, suggestPrice, publishProduct, openEditProduct, handleDelete,
}) => (
  <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] flex items-center gap-4 hover:bg-white/[0.04] transition-colors">
    <input type="checkbox" checked={checked} onChange={onToggle}
      data-testid={`product-select-${product.id}`}
      className="w-4 h-4 accent-[#D9B35A] flex-shrink-0 cursor-pointer" />
    <div className="w-16 h-16 rounded-xl bg-white/[0.04] flex items-center justify-center flex-shrink-0 overflow-hidden">
      {product.image_url
        ? <img src={`${API_URL}${product.image_url}`} alt={product.name} className="w-full h-full object-cover" />
        : <Package className="w-6 h-6 text-white/20" />}
    </div>

    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs">{CATEGORIES.find((c) => c.value === product.category)?.icon}</span>
        <p className="font-semibold text-white truncate">{product.name}</p>
        {product.is_new && <Badge className="bg-blue-500/20 text-blue-400 border-0 text-xs">Nouveau</Badge>}
        {product.is_active === false && <Badge className="bg-slate-500/25 text-slate-300 border-0 text-xs" data-testid={`product-pro-off-${product.id}`}>Hors cat. pro</Badge>}
      </div>
      <div className="flex items-center gap-3 text-xs text-white/50">
        <span className="font-mono">{product.sku}</span>
        {product.ean && <span>EAN: {product.ean}</span>}
        <span>{product.brand}</span>
      </div>
    </div>

    <div className="text-right">
      <p className="font-bold text-[#D9B35A]">{formatPrice(product.pricing?.price_ht_cents)}</p>
      <p className="text-xs text-white/50">HT · TVA {product.pricing?.tva_rate}%</p>
    </div>

    <Badge
      variant="outline"
      className={
        product.status === 'approved' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
        product.status === 'draft' ? 'bg-gray-500/20 text-gray-400 border-gray-500/30' :
        'bg-amber-500/20 text-amber-400 border-amber-500/30'
      }
    >
      {product.status === 'approved' ? 'Approuvé' : product.status === 'draft' ? 'Brouillon' : 'En attente'}
    </Badge>

    <div className="flex gap-2">
      {product.status === 'draft' && (
        <>
          <Button size="sm" onClick={() => suggestPrice(product)} disabled={pricingId === product.id}
            data-testid={`product-ai-price-${product.id}`} title="Prix suggéré par l'IA (marché Outre-mer)"
            className="bg-white/[0.06] border border-[#D9B35A]/30 text-[#E9CF8E] hover:bg-[#D9B35A]/15 h-8 px-2 text-xs">
            <Sparkles className={`w-3.5 h-3.5 mr-1 ${pricingId === product.id ? 'animate-spin' : ''}`} /> Prix IA
          </Button>
          <Button size="sm" onClick={() => publishProduct(product)}
            data-testid={`product-publish-${product.id}`} title="Publier cette fiche au catalogue"
            className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black h-8 px-2 text-xs font-bold">
            <Rocket className="w-3.5 h-3.5 mr-1" /> Publier
          </Button>
        </>
      )}
      <Button size="sm" variant="ghost" onClick={() => openEditProduct(product)} className="text-white/60 hover:text-white">
        <Edit className="w-4 h-4" />
      </Button>
      <Button size="sm" variant="ghost" onClick={() => handleDelete(product.id)} className="text-white/60 hover:text-red-400">
        <Trash2 className="w-4 h-4" />
      </Button>
    </div>
  </div>
);
