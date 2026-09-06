import { useEffect, useState } from 'react';
import { Eye, EyeOff, Store } from 'lucide-react';
import { Switch } from '../ui/switch';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';

const API = process.env.REACT_APP_BACKEND_URL;

// Superadmin : choix des produits LOLODRIVE visibles par les visiteurs (vitrine, prix masqués)
export const VisitorShowcasePanel = () => {
  const [products, setProducts] = useState([]);
  const [q, setQ] = useState('');
  const [spotViews, setSpotViews] = useState(null);
  useEffect(() => {
    fetch(`${API}/api/lolodrive/admin/products/visitor-visibility`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { products: [] }))
      .then((d) => setProducts(d.products || []))
      .catch(() => {});
    fetch(`${API}/api/lolodrive/admin/spot-views`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setSpotViews).catch(() => {});
  }, []);
  const toggle = async (sku, visible) => {
    try {
      const r = await fetch(`${API}/api/lolodrive/admin/products/${sku}/visitor-visible`, {
        method: 'PATCH', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ visible }),
      });
      if (!r.ok) throw new Error('Erreur');
      setProducts((prev) => prev.map((p) => (p.sku === sku ? { ...p, visitor_visible: visible } : p)));
      toast.success(visible ? 'Produit visible en vitrine visiteurs' : 'Produit retiré de la vitrine');
    } catch (e) { toast.error(e.message); }
  };
  const visibleCount = products.filter((p) => p.visitor_visible).length;
  const ql = q.trim().toLowerCase();
  const list = ql ? products.filter((p) => `${p.name} ${p.sku}`.toLowerCase().includes(ql)) : products;
  return (
    <div className="rounded-2xl p-5 mt-6 bg-white/[0.03] border border-white/[0.08]" data-testid="visitor-showcase-panel">
      <div className="flex items-center gap-2 mb-1">
        <Store className="w-4 h-4 text-[#D9B35A]" />
        <h3 className="text-sm font-bold text-[#E9CF8E] m-0">Vitrine visiteurs — catalogue LOLODRIVE ({visibleCount} visible{visibleCount > 1 ? 's' : ''})</h3>
        <button type="button" data-testid="showcase-preview-btn"
          onClick={() => window.open('/catalogue-lolodrive?visitor=1', '_blank')}
          className="ml-auto px-3 py-1 rounded-full text-[11px] font-bold text-[#1F2A12] bg-[#8CC63E] hover:brightness-110 transition-[filter]">
          👁 Voir comme un visiteur
        </button>
      </div>
      <p className="text-[11px] text-white/45 m-0 mb-3">Les visiteurs non connectés ne voient que ces produits, prix masqués, avec invitation à acheter le PASS.</p>
      {spotViews && (
        <div className="mb-3 rounded-xl px-3 py-2 bg-white/[0.04] border border-white/[0.08] flex items-center gap-2 flex-wrap" data-testid="spot-views-stats">
          <span className="text-[11px] font-bold text-[#E9CF8E]">🎬 Spot LOLODRIVE — {spotViews.total} lecture{spotViews.total > 1 ? 's' : ''}</span>
          <span className="text-[11px] font-bold text-[#8CC63E]" data-testid="spot-conversion-rate">
            → {spotViews.total_cta || 0} clic{(spotViews.total_cta || 0) > 1 ? 's' : ''} « Découvrir le PASS » ({spotViews.conversion_pct || 0} % de conversion)
          </span>
          {(spotViews.months || []).map((m) => (
            <span key={m.month} className="px-2 py-0.5 rounded-full text-[10px] text-white/70 bg-white/[0.05] border border-white/15">
              {m.month} · {m.views} vue{m.views > 1 ? 's' : ''} · {m.cta_clicks || 0} clic{(m.cta_clicks || 0) > 1 ? 's' : ''} · {m.conversion_pct || 0} %
            </span>
          ))}
        </div>
      )}
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher un produit…"
        data-testid="visitor-showcase-search"
        className="h-9 w-full sm:w-72 mb-3 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-white text-sm placeholder:text-white/35" />
      <div className="space-y-1.5 max-h-80 overflow-y-auto">
        {list.map((p) => (
          <div key={p.sku} className="flex items-center gap-3 p-2 rounded-lg bg-white/[0.02] border border-white/[0.06]" data-testid={`showcase-row-${p.sku}`}>
            {p.visitor_visible ? <Eye className="w-3.5 h-3.5 text-[#8CC63E]" /> : <EyeOff className="w-3.5 h-3.5 text-white/30" />}
            <div className="flex-1 min-w-0">
              <span className="text-sm text-white truncate block">{p.name}</span>
              <span className="text-[10px] text-white/40">{p.sku} · {p.category || '—'}</span>
            </div>
            <Switch checked={!!p.visitor_visible} onCheckedChange={(v) => toggle(p.sku, v)} data-testid={`showcase-toggle-${p.sku}`} />
          </div>
        ))}
      </div>
    </div>
  );
};
