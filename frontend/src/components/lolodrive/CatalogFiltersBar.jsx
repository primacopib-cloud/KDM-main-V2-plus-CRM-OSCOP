import { useEffect, useState } from 'react';
import { Search } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { lolodriveAPI } from '../../services/api';

// Barre de filtres catalogue : recherche texte + catégorie + sous-catégorie (liste fixe super admin)
export const CatalogFiltersBar = ({ search, setSearch, category, setCategory, subcategory, setSubcategory }) => {
  const [cats, setCats] = useState([]);
  useEffect(() => {
    lolodriveAPI.lolodriveCategories().then((d) => setCats(d.categories || [])).catch(() => {});
  }, []);
  const current = cats.find((c) => c.name === category);

  return (
    <div className="flex flex-wrap gap-2 mb-4" data-testid="catalog-filters-bar">
      <div className="flex items-center gap-1.5 flex-1 min-w-[200px] px-3 rounded-lg bg-white/[0.04] border border-white/10">
        <Search className="w-3.5 h-3.5 text-white/40 shrink-0" />
        <input value={search} data-testid="catalog-search-text"
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Rechercher un produit…"
          className="w-full bg-transparent py-2 text-sm text-white outline-none placeholder:text-white/30" />
      </div>
      <Select value={category || 'ALL'} onValueChange={(v) => { setCategory(v === 'ALL' ? '' : v); setSubcategory(''); }}>
        <SelectTrigger className="w-44 bg-white/[0.04] border-white/10" data-testid="catalog-category-filter">
          <SelectValue placeholder="Catégorie" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="ALL">Toutes catégories</SelectItem>
          {cats.map((c) => <SelectItem key={c.id} value={c.name}>{c.name}</SelectItem>)}
        </SelectContent>
      </Select>
      {current && current.subcategories?.length > 0 && (
        <Select value={subcategory || 'ALL'} onValueChange={(v) => setSubcategory(v === 'ALL' ? '' : v)}>
          <SelectTrigger className="w-52 bg-white/[0.04] border-white/10" data-testid="catalog-subcategory-filter">
            <SelectValue placeholder="Sous-catégorie" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">Toutes sous-catégories</SelectItem>
            {current.subcategories.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
          </SelectContent>
        </Select>
      )}
    </div>
  );
};

// Filtre local d'une liste de produits selon les états de la barre
export const applyCatalogFilters = (products, { search, category, subcategory }) => products.filter((p) => {
  if (category && p.category !== category) return false;
  if (subcategory && p.subcategory !== subcategory) return false;
  const q = (search || '').trim().toLowerCase();
  if (!q) return true;
  return p.name.toLowerCase().includes(q) || (p.sku || '').toLowerCase().includes(q)
    || (p.brand || '').toLowerCase().includes(q) || (p.barcode || '').toLowerCase() === q;
});
