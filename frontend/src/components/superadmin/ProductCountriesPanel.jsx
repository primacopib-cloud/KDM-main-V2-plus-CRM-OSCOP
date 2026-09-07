import { useEffect, useState } from 'react';
import { Globe2 } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';

const API = process.env.REACT_APP_BACKEND_URL;

export const WORLD_COUNTRIES = [
  { code: 'CUBA', label: 'Cuba', flag: 'cu' },
  { code: 'HAITI', label: 'Haïti', flag: 'ht' },
  { code: 'BRESIL', label: 'Brésil', flag: 'br' },
  { code: 'MAROC', label: 'Maroc', flag: 'ma' },
  { code: 'FRANCE', label: 'France', flag: 'fr' },
  { code: 'SENEGAL', label: 'Sénégal', flag: 'sn' },
  { code: 'COTE-DIVOIRE', label: "Côte d'Ivoire", flag: 'ci' },
  { code: 'AFRIQUE-DU-SUD', label: 'Afrique du Sud', flag: 'za' },
  { code: 'MADAGASCAR', label: 'Madagascar', flag: 'mg' },
  { code: 'MAURICE', label: 'Maurice', flag: 'mu' },
];

// Superadmin : affecter des pays du monde aux produits pour peupler la carte
export const ProductCountriesPanel = () => {
  const [products, setProducts] = useState([]);
  const [q, setQ] = useState('');
  useEffect(() => {
    fetch(`${API}/api/catalog/admin/products/visitor-visibility`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { products: [] }))
      .then((d) => setProducts(d.products || []))
      .catch(() => {});
  }, []);

  const toggleCountry = async (p, code) => {
    const current = p.countries || [];
    const countries = current.includes(code) ? current.filter((c) => c !== code) : [...current, code];
    try {
      const r = await fetch(`${API}/api/catalog/admin/products/${p.id}/countries`, {
        method: 'PATCH', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ countries }),
      });
      if (!r.ok) throw new Error('Erreur');
      setProducts((prev) => prev.map((x) => (x.id === p.id ? { ...x, countries } : x)));
      toast.success(countries.includes(code)
        ? `${p.name} affecté à ${WORLD_COUNTRIES.find((c) => c.code === code)?.label}`
        : 'Pays retiré du produit');
    } catch (e) { toast.error(e.message); }
  };

  const ql = q.trim().toLowerCase();
  const list = ql ? products.filter((p) => `${p.name} ${p.sku}`.toLowerCase().includes(ql)) : products;
  const assigned = products.filter((p) => (p.countries || []).length > 0).length;

  return (
    <div className="rounded-2xl p-5 mt-6 bg-white/[0.03] border border-white/[0.08]" data-testid="product-countries-panel">
      <div className="flex items-center gap-2 mb-1">
        <Globe2 className="w-4 h-4 text-[#8CC63E]" />
        <h3 className="text-sm font-bold text-[#B6E27A] m-0">Produits par pays — carte du monde ({assigned} affecté{assigned > 1 ? 's' : ''})</h3>
      </div>
      <p className="text-[11px] text-white/45 m-0 mb-3">Affectez des pays du monde à un produit : il devient visible sur la carte et filtrable par ce pays dans le catalogue.</p>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher un produit…"
        data-testid="product-countries-search"
        className="h-9 w-full sm:w-72 mb-3 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-white text-sm placeholder:text-white/35" />
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {list.map((p) => (
          <div key={p.id} className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.06]" data-testid={`product-countries-row-${p.sku}`}>
            <div className="flex items-baseline gap-2 mb-1.5">
              <span className="text-sm text-white truncate">{p.name}</span>
              <span className="text-[10px] text-white/40">{p.sku}</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {WORLD_COUNTRIES.map((c) => {
                const on = (p.countries || []).includes(c.code);
                return (
                  <button key={c.code} type="button" onClick={() => toggleCountry(p, c.code)}
                    data-testid={`country-chip-${p.sku}-${c.code}`}
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border transition-colors ${
                      on ? 'bg-[#8CC63E]/20 border-[#8CC63E]/50 text-[#B6E27A]'
                        : 'bg-white/[0.03] border-white/10 text-white/45 hover:text-white/80'}`}>
                    <img src={`https://flagcdn.com/w20/${c.flag}.png`} alt="" width={14} height={10} className="rounded-[1px]" />
                    {c.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
