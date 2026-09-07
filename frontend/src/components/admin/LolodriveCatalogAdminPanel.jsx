import { useEffect, useState } from 'react';
import { Package, ExternalLink, Store, Ticket, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';

const API = process.env.REACT_APP_BACKEND_URL;
const inCls = 'h-9 px-2.5 rounded-lg bg-white/[0.06] border border-white/15 text-white text-xs w-full placeholder:text-white/35';
const fmtEUR = (c) => `${((c || 0) / 100).toFixed(2)} €`;

// Superadmin : voir + créer le catalogue LOLODRIVE, et accès rapide aux espaces
export const LolodriveCatalogAdminPanel = () => {
  const [products, setProducts] = useState([]);
  const [q, setQ] = useState('');
  const [nf, setNf] = useState({ sku: '', name: '', category: 'Épicerie', price_public: '', price_pass: '', image_url: '', stock_qty: '' });
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    fetch(`${API}/api/lolodrive/admin/products/list`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { products: [] }))
      .then((d) => setProducts(d.products || []))
      .catch(() => {});
  }, []);
  const create = async () => {
    if (!nf.name.trim() || !nf.price_public) return toast.error('Nom et prix public requis');
    setBusy(true);
    try {
      const sku = nf.sku.trim() || nf.name.trim().toUpperCase().replace(/[^A-Z0-9]+/g, '-').slice(0, 16);
      const r = await fetch(`${API}/api/lolodrive/admin/products`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          sku, name: nf.name.trim(), category: nf.category,
          price_public_cents: Math.round(parseFloat(nf.price_public) * 100),
          price_pass_cents: nf.price_pass ? Math.round(parseFloat(nf.price_pass) * 100) : null,
          image_url: nf.image_url || null,
          stock_qty: nf.stock_qty ? parseInt(nf.stock_qty, 10) : null,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Création impossible');
      setProducts((prev) => [{ sku, name: nf.name, category: nf.category, price_public_cents: Math.round(parseFloat(nf.price_public) * 100) }, ...prev]);
      setNf({ sku: '', name: '', category: 'Épicerie', price_public: '', price_pass: '', image_url: '', stock_qty: '' });
      toast.success(`Produit « ${nf.name} » ajouté au catalogue LOLODRIVE (${sku})`);
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };
  const ql = q.trim().toLowerCase();
  const list = ql ? products.filter((p) => `${p.name} ${p.sku} ${p.category || ''}`.toLowerCase().includes(ql)) : products;
  return (
    <div className="rounded-2xl p-5 mt-6 bg-white/[0.03] border border-white/[0.08]" data-testid="lolodrive-catalog-admin-panel">
      <div className="flex items-center gap-2 mb-1 flex-wrap">
        <Package className="w-4 h-4 text-[#D9B35A]" />
        <h3 className="text-sm font-bold text-[#E9CF8E] m-0">Catalogue LOLODRIVE ({products.length} produit{products.length > 1 ? 's' : ''})</h3>
        <span className="ml-auto flex items-center gap-1.5 flex-wrap">
          <a href="/lolo-point/dashboard" target="_blank" rel="noreferrer" data-testid="open-relay-space"
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold text-[#8CC63E] bg-[#8CC63E]/10 border border-[#8CC63E]/40 hover:bg-[#8CC63E]/20 transition-colors">
            <Store className="w-3 h-3" /> Espace relais <ExternalLink className="w-2.5 h-2.5" />
          </a>
          <a href="/espace-investisseur" target="_blank" rel="noreferrer" data-testid="open-investor-space"
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold text-[#E9CF8E] bg-[#D9B35A]/10 border border-[#D9B35A]/40 hover:bg-[#D9B35A]/20 transition-colors">
            <TrendingUp className="w-3 h-3" /> Espace investisseur <ExternalLink className="w-2.5 h-2.5" />
          </a>
          <a href="/pass" target="_blank" rel="noreferrer" data-testid="open-pass-space"
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold text-white/80 bg-white/[0.06] border border-white/20 hover:bg-white/[0.14] transition-colors">
            <Ticket className="w-3 h-3" /> Espace client PASS <ExternalLink className="w-2.5 h-2.5" />
          </a>
        </span>
      </div>
      <div className="rounded-xl p-3 my-3 bg-[#D9B35A]/[0.06] border border-[#D9B35A]/30" data-testid="create-lolo-product-form">
        <p className="text-[11px] font-bold text-[#E9CF8E] m-0 mb-2">➕ Ajouter un produit au catalogue (vendu par lot ×3)</p>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <input value={nf.name} onChange={(e) => setNf({ ...nf, name: e.target.value })} placeholder="Nom du produit *" className={inCls} data-testid="new-lolo-name" />
          <input value={nf.sku} onChange={(e) => setNf({ ...nf, sku: e.target.value })} placeholder="SKU (auto si vide)" className={inCls} data-testid="new-lolo-sku" />
          <input value={nf.category} onChange={(e) => setNf({ ...nf, category: e.target.value })} placeholder="Catégorie" className={inCls} data-testid="new-lolo-category" />
          <input type="number" step="0.01" min="0" value={nf.price_public} onChange={(e) => setNf({ ...nf, price_public: e.target.value })} placeholder="Prix public € *" className={inCls} data-testid="new-lolo-price" />
          <input type="number" step="0.01" min="0" value={nf.price_pass} onChange={(e) => setNf({ ...nf, price_pass: e.target.value })} placeholder="Prix PASS € (optionnel)" className={inCls} data-testid="new-lolo-price-pass" />
          <input value={nf.image_url} onChange={(e) => setNf({ ...nf, image_url: e.target.value })} placeholder="URL image" className={inCls} data-testid="new-lolo-image" />
          <input type="number" min="0" value={nf.stock_qty} onChange={(e) => setNf({ ...nf, stock_qty: e.target.value })} placeholder="Stock" className={inCls} data-testid="new-lolo-stock" />
          <button type="button" onClick={create} disabled={busy} data-testid="new-lolo-submit"
            className="h-9 rounded-lg text-xs font-bold text-[#1F2A12] bg-[#D9B35A] hover:brightness-110 disabled:opacity-60 transition-[filter]">
            {busy ? 'Ajout…' : 'Créer le produit'}
          </button>
        </div>
      </div>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher dans le catalogue…" data-testid="lolo-catalog-search"
        className={`${inCls} sm:w-72 mb-2`} />
      <div className="space-y-1 max-h-72 overflow-y-auto">
        {list.map((p) => (
          <div key={p.sku} className="flex items-center gap-3 p-2 rounded-lg bg-white/[0.02] border border-white/[0.06]" data-testid={`lolo-cat-row-${p.sku}`}>
            <div className="flex-1 min-w-0">
              <span className="text-sm text-white truncate block">{p.name}</span>
              <span className="text-[10px] text-white/40">{p.sku} · {p.category || '—'}</span>
            </div>
            <span className="text-xs font-semibold text-[#E9CF8E]">{fmtEUR(p.price_public_cents ?? p.display_price_cents)}</span>
          </div>
        ))}
        {!list.length && <p className="text-xs text-white/40">Aucun produit.</p>}
      </div>
    </div>
  );
};
