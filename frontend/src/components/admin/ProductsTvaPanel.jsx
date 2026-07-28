import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Percent, ChevronDown, ChevronUp } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

const RATES = ['0', '2.1', '5.5', '8.5', '20'];

// Super admin : réglage du taux de TVA de chaque produit du catalogue
export const ProductsTvaPanel = () => {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    lolodriveAPI.adminProductsTva().then(setData).catch(() => {});
  }, []);
  if (!data) return null;

  const setTva = async (sku, rate) => {
    try {
      await lolodriveAPI.adminSetProductTva(sku, parseFloat(rate));
      setData({ ...data, products: data.products.map((p) => (p.sku === sku ? { ...p, tva_rate: parseFloat(rate) } : p)) });
      toast.success(`TVA mise à jour : ${rate} % ✓`);
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="products-tva-panel">
      <button type="button" onClick={() => setOpen(!open)} data-testid="products-tva-toggle"
        className="w-full flex flex-wrap items-center justify-between gap-3 text-left">
        <div className="font-semibold flex items-center gap-2">
          <Percent className="w-4 h-4 text-[#D9B35A]" /> TVA des produits
          <span className="text-xs text-white/40 font-normal">({data.count} produits — appliquée sur les tickets HT / TVA / TTC)</span>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-white/40" /> : <ChevronDown className="w-4 h-4 text-white/40" />}
      </button>
      {open && (
        <div className="mt-3 grid sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-[380px] overflow-y-auto pr-1">
          {data.products.map((p) => (
            <div key={p.sku} data-testid={`tva-row-${p.sku}`}
              className="flex items-center justify-between gap-2 rounded-lg bg-white/[0.03] border border-white/[0.06] px-3 py-2 text-xs">
              <span className="min-w-0">
                <span className="block font-medium truncate">{p.name}</span>
                <span className="block text-[10px] text-white/40 truncate">
                  {p.category || '—'}{p.point_code ? ` · Relais ${p.point_code}` : ''} · {(p.price_public_cents / 100).toFixed(2)} € TTC
                </span>
              </span>
              <select value={String(p.tva_rate ?? 8.5)} data-testid={`tva-select-${p.sku}`}
                onChange={(e) => setTva(p.sku, e.target.value)}
                className="shrink-0 px-2 py-1 rounded-md bg-white/5 border border-white/10 text-xs text-white outline-none font-mono">
                {(RATES.includes(String(p.tva_rate ?? 8.5)) ? RATES : [...RATES, String(p.tva_rate)]).map((r) => (
                  <option key={r} value={r} className="bg-[#15151c]">{r} %</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
