import { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Layers, Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { lolodriveAPI } from '../../services/api';
import { PRODUCT_TAGS } from '../lolodrive/ProductTagBadge';

// Super admin : programmation EN MASSE des étiquettes et des lots — par catégorie, sous-catégorie ou produits
export const BulkProgramDialog = ({ products, onClose, onDone }) => {
  const bases = useMemo(() => products.filter((p) => !p.is_lot), [products]);
  const cats = useMemo(() => [...new Set(bases.map((p) => p.category).filter(Boolean))].sort(), [bases]);
  const [scope, setScope] = useState('category');
  const [category, setCategory] = useState('');
  const [subcategory, setSubcategory] = useState('');
  const [skus, setSkus] = useState([]);
  const [action, setAction] = useState('tag');
  const [tag, setTag] = useState('PROMO');
  const [until, setUntil] = useState('');
  const [paid, setPaid] = useState('3');
  const [free, setFree] = useState('1');
  const [busy, setBusy] = useState(false);

  const subs = useMemo(() => [...new Set(bases.filter((p) => p.category === category).map((p) => p.subcategory).filter(Boolean))].sort(), [bases, category]);

  const target = () => {
    if (scope === 'products') return skus.length ? { skus } : null;
    if (!category) return null;
    return scope === 'subcategory' && subcategory ? { category, subcategory } : { category };
  };

  const run = async () => {
    const t = target();
    if (!t) return toast.error('Choisissez une cible (catégorie, sous-catégorie ou produits)');
    setBusy(true);
    try {
      if (action === 'tag' || action === 'untag') {
        const r = await lolodriveAPI.adminBulkTag({ ...t, tag: action === 'tag' ? tag : null, tag_until: until || null });
        toast.success(action === 'tag'
          ? `Étiquette « ${PRODUCT_TAGS.find((x) => x.value === tag)?.label} » appliquée à ${r.matched} produit(s)${until ? ` jusqu'au ${new Date(until).toLocaleDateString('fr-FR')}` : ''} ✓`
          : `Étiquettes retirées sur ${r.matched} produit(s) ✓`);
      } else {
        const r = await lolodriveAPI.adminBulkCreateLot({ ...t, paid_qty: parseInt(paid, 10), free_qty: parseInt(free, 10) });
        toast.success(`${r.created_count} lot(s) créé(s)${r.skipped_existing ? ` — ${r.skipped_existing} déjà existant(s) ignoré(s)` : ''} ✓`);
      }
      onDone();
      onClose();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  const selCls = 'mt-1 w-full bg-white/5 border border-white/15 rounded-lg px-2 py-2 text-white text-xs';
  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-md" data-testid="bulk-program-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <Layers className="w-4 h-4 text-[#D9B35A]" /> Programmation en masse
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3 text-xs">
          <label className="block">
            <span className="text-white/50">Cible</span>
            <select value={scope} onChange={(e) => setScope(e.target.value)} data-testid="bulk-scope-select" className={selCls}>
              <option value="category" className="bg-[#15151c]">Toute une catégorie</option>
              <option value="subcategory" className="bg-[#15151c]">Une sous-catégorie</option>
              <option value="products" className="bg-[#15151c]">Produits choisis un par un</option>
            </select>
          </label>
          {scope !== 'products' && (
            <div className="flex gap-2">
              <select value={category} onChange={(e) => { setCategory(e.target.value); setSubcategory(''); }} data-testid="bulk-category-select" className={selCls}>
                <option value="" className="bg-[#15151c]">— catégorie —</option>
                {cats.map((c) => <option key={c} value={c} className="bg-[#15151c]">{c}</option>)}
              </select>
              {scope === 'subcategory' && (
                <select value={subcategory} onChange={(e) => setSubcategory(e.target.value)} data-testid="bulk-subcategory-select" className={selCls}>
                  <option value="" className="bg-[#15151c]">— sous-catégorie —</option>
                  {subs.map((s) => <option key={s} value={s} className="bg-[#15151c]">{s}</option>)}
                </select>
              )}
            </div>
          )}
          {scope === 'products' && (
            <div className="max-h-36 overflow-y-auto rounded-lg border border-white/10 p-2 space-y-1" data-testid="bulk-products-list">
              {bases.map((p) => (
                <label key={p.sku} className="flex items-center gap-2 text-[11px] text-white/70 cursor-pointer">
                  <input type="checkbox" checked={skus.includes(p.sku)} data-testid={`bulk-product-check-${p.sku}`}
                    onChange={(e) => setSkus((s) => e.target.checked ? [...s, p.sku] : s.filter((x) => x !== p.sku))} />
                  <span className="truncate">{p.name}</span>
                </label>
              ))}
            </div>
          )}
          <label className="block">
            <span className="text-white/50">Action</span>
            <select value={action} onChange={(e) => setAction(e.target.value)} data-testid="bulk-action-select" className={selCls}>
              <option value="tag" className="bg-[#15151c]">Appliquer une étiquette (Promo, Solde…)</option>
              <option value="untag" className="bg-[#15151c]">Retirer les étiquettes</option>
              <option value="lot" className="bg-[#15151c]">Créer des lots (×N, +offerts)</option>
            </select>
          </label>
          {action === 'tag' && (
            <div className="flex gap-2">
              <select value={tag} onChange={(e) => setTag(e.target.value)} data-testid="bulk-tag-select" className={selCls}>
                {PRODUCT_TAGS.map((t) => <option key={t.value} value={t.value} className="bg-[#15151c]">{t.label}</option>)}
              </select>
              <input type="date" value={until} onChange={(e) => setUntil(e.target.value)} data-testid="bulk-until-input"
                title="Fin (retrait automatique) — optionnel" className={selCls} />
            </div>
          )}
          {action === 'lot' && (
            <div className="flex gap-2">
              <select value={paid} onChange={(e) => setPaid(e.target.value)} data-testid="bulk-paid-select" className={selCls}>
                {[2, 3, 4, 5, 6, 8, 10, 12].map((n) => <option key={n} value={n} className="bg-[#15151c]">×{n} payés</option>)}
              </select>
              <select value={free} onChange={(e) => setFree(e.target.value)} data-testid="bulk-free-select" className={selCls}>
                {[0, 1, 2, 3].map((n) => <option key={n} value={n} className="bg-[#15151c]">{n ? `+${n} offert${n > 1 ? 's' : ''}` : 'aucun offert'}</option>)}
              </select>
            </div>
          )}
        </div>
        <Button onClick={run} disabled={busy} data-testid="bulk-run-btn"
          className="w-full bg-[#D9B35A] hover:bg-[#c9a34a] text-black font-bold">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Appliquer en masse'}
        </Button>
      </DialogContent>
    </Dialog>
  );
};
