import { useEffect, useRef, useState } from 'react';
import { BookOpen, ImagePlus, Plus, X } from 'lucide-react';
import { toast } from 'sonner';
import { detaillantAPI } from '../../../services/api.detaillant';
import { API, getAuthHeaders } from '../../../services/http';

const logoSrc = (u) => (u?.startsWith('/api/') ? `${API}${u.slice(4)}` : u);

const inputCls = 'h-8 px-2 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs';

export const CatalogManagerCard = () => {
  const [products, setProducts] = useState([]);
  const [f, setF] = useState({ name: '', category: '', brand: '', brand_logo: null, perishable: false });
  const [busy, setBusy] = useState(false);
  const logoRef = useRef(null);
  const uploadLogo = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(`${API}/admin/detaillant/catalog/logo`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(), body: fd,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Échec du téléversement');
      setF((p) => ({ ...p, brand_logo: data.url }));
      toast.success('✓ Logo de marque ajouté');
    } catch (err) { toast.error(err.message); }
  };
  const load = () => detaillantAPI.adminCatalog().then((r) => setProducts(r.products || [])).catch(() => {});
  useEffect(() => { load(); }, []);
  const add = async () => {
    setBusy(true);
    try {
      await detaillantAPI.adminUpsertProduct(f);
      toast.success('✓ Produit ajouté au catalogue en vigueur');
      setF({ name: '', category: '', brand: '', brand_logo: null, perishable: false });
      load();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const toggle = async (sku, params) => {
    try { await detaillantAPI.adminToggleProduct(sku, params); load(); } catch (e) { toast.error(e.message); }
  };
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" data-testid="admin-catalog-manager">
      <h3 className="text-sm font-bold text-[#E9CF8E] mb-1 flex items-center gap-2">
        <BookOpen className="w-4 h-4" /> Catalogue POP'S en vigueur
      </h3>
      <p className="text-[10px] text-white/45 mb-3">
        Produits proposables par les détaillants. « Périssable » impose une DLC d'au moins 3 mois au dépôt.
      </p>
      <div className="flex gap-2 flex-wrap items-center mb-3">
        <input value={f.name} onChange={(e) => setF((p) => ({ ...p, name: e.target.value }))}
          placeholder="Nom du produit" className={inputCls + ' w-48'} data-testid="catalog-new-name" />
          <input value={f.brand} onChange={(e) => setF((p) => ({ ...p, brand: e.target.value }))}
            placeholder="Marque (optionnel)" className={inputCls + ' w-36'} data-testid="catalog-new-brand" />
        {f.brand_logo ? (
          <span className="inline-flex items-center gap-1">
            <img src={logoSrc(f.brand_logo)} alt="logo" className="h-6 w-auto max-w-[56px] object-contain rounded bg-white/90 px-0.5" data-testid="catalog-new-logo-preview" />
            <button onClick={() => setF((p) => ({ ...p, brand_logo: null }))} data-testid="catalog-new-logo-remove"
              className="w-4 h-4 rounded-full bg-black/50 flex items-center justify-center"><X className="w-2.5 h-2.5 text-white" /></button>
          </span>
        ) : (
          <button onClick={() => logoRef.current?.click()} data-testid="catalog-new-logo-btn"
            className="inline-flex items-center gap-1 px-2 h-8 rounded-lg border border-dashed border-white/25 text-[10px] text-white/50 hover:text-[#E9CF8E] hover:border-[#D9B35A]/50">
            <ImagePlus className="w-3 h-3" /> Logo marque
          </button>
        )}
        <input ref={logoRef} type="file" accept="image/png,image/jpeg,image/webp,image/svg+xml" className="hidden"
          onChange={uploadLogo} data-testid="catalog-new-logo-input" />
        <input value={f.category} onChange={(e) => setF((p) => ({ ...p, category: e.target.value }))}
          placeholder="Catégorie" className={inputCls + ' w-36'} data-testid="catalog-new-category" />
        <label className="flex items-center gap-1.5 text-[10px] text-white/60">
          <input type="checkbox" checked={f.perishable} data-testid="catalog-new-perishable"
            onChange={(e) => setF((p) => ({ ...p, perishable: e.target.checked }))} />
          Périssable (DLC min. 3 mois)
        </label>
        <button onClick={add} disabled={busy || f.name.trim().length < 2} data-testid="catalog-new-submit"
          className="inline-flex items-center gap-1 px-3 h-8 rounded-full bg-[#D9B35A] text-black text-[10px] font-bold hover:bg-[#E9CF8E] disabled:opacity-40">
          <Plus className="w-3 h-3" /> Ajouter
        </button>
      </div>
      <div className="max-h-64 overflow-y-auto space-y-1">
        {products.map((p) => (
          <div key={p.sku} className="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-lg bg-white/[0.03] border border-white/10"
            data-testid={`catalog-row-${p.sku}`}>
            <p className="text-[11px] truncate">
              <span className={p.detaillant_active === false ? 'line-through text-white/35' : ''}>
                {p.brand_logo && <img src={logoSrc(p.brand_logo)} alt={p.brand} className="inline h-4 w-auto max-w-[40px] object-contain rounded bg-white/90 px-0.5 mr-1 align-[-3px]" />}
                {p.name}{p.brand ? ` · ${p.brand}` : ''}
              </span>
              <span className="text-white/40"> · {p.category || '—'}</span>
            </p>
            <div className="flex items-center gap-2 shrink-0">
              <label className="flex items-center gap-1 text-[9px] text-white/50">
                <input type="checkbox" checked={!!p.perishable} data-testid={`catalog-perishable-${p.sku}`}
                  onChange={(e) => toggle(p.sku, { perishable: e.target.checked })} />
                DLC
              </label>
              <button onClick={() => toggle(p.sku, { detaillant_active: p.detaillant_active === false })}
                data-testid={`catalog-active-${p.sku}`}
                className={`px-2 h-5 rounded-full text-[9px] font-bold border ${
                  p.detaillant_active === false
                    ? 'text-white/40 border-white/20 hover:bg-white/5'
                    : 'text-emerald-300 border-emerald-400/40 hover:bg-emerald-400/10'}`}>
                {p.detaillant_active === false ? 'inactif' : 'actif'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
