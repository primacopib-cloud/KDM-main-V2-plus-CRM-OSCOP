import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { Home, Search, Trash2, Save, Plus, GripVertical } from 'lucide-react';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Super admin : produits et nombre affichés dans le carrousel de l'accueil particuliers LOLODRIVE
export const LolodriveCarouselPanel = () => {
  const [selected, setSelected] = useState([]);
  const [maxCount, setMaxCount] = useState(12);
  const [promoPercent, setPromoPercent] = useState(0);
  const [promoEndsAt, setPromoEndsAt] = useState('');
  const [clicks, setClicks] = useState(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const dragIndex = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const cfg = await fetch(`${API_URL}/api/public/lolodrive-carousel`).then((r) => r.json());
        setMaxCount(cfg.max_count || 12);
        setPromoPercent(cfg.promo_percent || 0);
        if (cfg.promo_ends_at) setPromoEndsAt(cfg.promo_ends_at.slice(0, 16));
        fetch(`${API_URL}/api/admin/lolodrive-carousel/pass-clicks`, { headers: getAuthHeaders(), credentials: 'include' })
          .then((r) => (r.ok ? r.json() : null)).then(setClicks).catch(() => {});
        if (cfg.product_ids?.length) {
          const all = await fetch(`${API_URL}/api/v2/catalog/products?limit=100`, { headers: getAuthHeaders(), credentials: 'include' }).then((r) => r.json());
          setSelected(cfg.product_ids.map((id) => (Array.isArray(all) ? all.find((p) => p.id === id) : null) || { id, name: id, sku: '' }));
        }
      } catch { /* vide */ }
    })();
  }, []);

  const search = async () => {
    try {
      const d = await fetch(`${API_URL}/api/v2/catalog/products?limit=12&search=${encodeURIComponent(query)}`, { headers: getAuthHeaders(), credentials: 'include' }).then((r) => r.json());
      setResults(Array.isArray(d) ? d : []);
    } catch { toast.error('Recherche impossible'); }
  };

  const save = async (list = selected, count = maxCount) => {
    try {
      const res = await fetch(`${API_URL}/api/admin/lolodrive-carousel`, {
        method: 'PUT', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ product_ids: list.map((p) => p.id), max_count: Number(count) || 12, promo_percent: Number(promoPercent) || 0, promo_ends_at: promoEndsAt || null }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Erreur');
      toast.success('Carrousel de l\'accueil particuliers enregistré');
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="rounded-2xl p-5 mt-6 bg-white/[0.03] border border-white/[0.08]" data-testid="lolodrive-carousel-panel">
      <div className="flex items-center gap-2 flex-wrap mb-1">
        <Home className="w-4 h-4 text-[#D9B35A]" />
        <h3 className="text-sm font-bold text-[#E9CF8E] m-0">Carrousel accueil particuliers ({selected.length} produit(s) choisi(s))</h3>
        <label className="ml-auto text-[10px] text-white/50 flex items-center gap-1">
          Nombre max affiché
          <input type="number" min={1} max={24} value={maxCount} onChange={(e) => setMaxCount(e.target.value)}
            data-testid="carousel-max-input"
            className="h-7 w-16 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs" />
        </label>
        <label className="text-[10px] text-white/50 flex items-center gap-1">
          Promo PASS
          <input type="number" min={0} max={90} value={promoPercent} onChange={(e) => setPromoPercent(e.target.value)}
            data-testid="carousel-promo-input"
            className="h-7 w-14 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs" /> %
        </label>
        <label className="text-[10px] text-white/50 flex items-center gap-1">
          Fin de promo
          <input type="datetime-local" value={promoEndsAt} onChange={(e) => setPromoEndsAt(e.target.value)}
            data-testid="carousel-promo-ends-input"
            className="h-7 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs" />
        </label>
        <button type="button" onClick={() => save()} data-testid="carousel-save-btn"
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] transition-colors">
          <Save className="w-3.5 h-3.5" /> Enregistrer
        </button>
      </div>
      <p className="text-[11px] text-white/40 m-0 mb-3">Sans sélection, l'accueil affiche automatiquement les produits les mieux notés.</p>
      {clicks && (
        <p className="text-[11px] m-0 mb-3 text-[#8CC63E]" data-testid="pass-clicks-counter">
          Clics sur PASS LOLODRIVE depuis le carrousel : <b>{clicks.total}</b> au total · {clicks.last_30d} sur 30 j · {clicks.last_7d} sur 7 j
        </p>
      )}
      <div className="flex gap-2 mb-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-white/40" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()}
            placeholder="Rechercher un produit (nom ou SKU)…" data-testid="carousel-search-input"
            className="h-9 w-full pl-8 pr-3 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs" />
        </div>
        <button type="button" onClick={search} data-testid="carousel-search-btn"
          className="px-3 py-1.5 rounded-lg text-xs font-semibold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30 hover:bg-white/[0.1] transition-colors">
          Rechercher
        </button>
      </div>
      {results.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {results.map((p) => (
            <button key={p.id} type="button" data-testid={`carousel-add-${p.sku}`}
              disabled={selected.some((s) => s.id === p.id)}
              onClick={() => setSelected((prev) => [...prev, p])}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-white/80 bg-white/[0.05] border border-white/15 hover:border-[#8CC63E]/50 disabled:opacity-30 transition-colors">
              <Plus className="w-3 h-3 text-[#8CC63E]" /> {p.name} <span className="text-white/35">{p.sku}</span>
            </button>
          ))}
        </div>
      )}
      {selected.length > 0 && (
        <div className="space-y-1">
          {selected.map((p, i) => (
            <div key={p.id} draggable
              onDragStart={() => { dragIndex.current = i; }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => {
                const from = dragIndex.current;
                if (from === null || from === i) return;
                setSelected((prev) => {
                  const next = [...prev];
                  const [moved] = next.splice(from, 1);
                  next.splice(i, 0, moved);
                  return next;
                });
                dragIndex.current = null;
              }}
              className="flex items-center gap-2 text-xs text-white/75 rounded-lg px-3 py-1.5 bg-white/[0.02] border border-white/[0.06] cursor-grab active:cursor-grabbing"
              data-testid={`carousel-selected-${p.sku || p.id}`}>
              <GripVertical className="w-3.5 h-3.5 text-white/30" />
              <span className="text-white/35 font-mono w-5">{i + 1}.</span>
              <span className="flex-1 truncate">{p.name} <span className="text-white/35">{p.sku}</span></span>
              <button type="button" onClick={() => setSelected((prev) => prev.filter((x) => x.id !== p.id))}
                data-testid={`carousel-remove-${p.sku || p.id}`}
                className="p-1 rounded text-red-300/70 hover:text-red-300 hover:bg-red-500/10 transition-colors">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
