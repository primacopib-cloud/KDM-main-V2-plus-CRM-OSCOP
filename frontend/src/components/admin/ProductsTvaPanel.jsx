import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Percent, ChevronDown, ChevronUp, Package, Sparkles, Loader2, Ban, RotateCcw } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

const RATES = ['0', '2.1', '5.5', '8.5', '20'];

// Super admin : fiches produits du catalogue — taux de TVA + photo (régénération IA)
export const ProductsTvaPanel = () => {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const [aiSku, setAiSku] = useState(null);

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

  const regenPhoto = async (sku) => {
    setAiSku(sku);
    try {
      const d = await lolodriveAPI.adminGenerateProductPhoto(sku);
      setData((prev) => ({ ...prev, products: prev.products.map((p) => (p.sku === sku ? { ...p, image_url: `${d.image_url}?t=${Date.now()}`, image_ai_generated: true } : p)) }));
      toast.success('Photo IA générée et remplacée ✨');
    } catch (e) { toast.error(e.message); } finally { setAiSku(null); }
  };

  const toggleActive = async (p) => {
    const next = p.is_active === false;
    try {
      await lolodriveAPI.adminToggleProduct(p.sku, next);
      setData((prev) => ({ ...prev, products: prev.products.map((x) => (x.sku === p.sku ? { ...x, is_active: next } : x)) }));
      toast.success(next ? `${p.name} remis au catalogue ✓` : `${p.name} retiré du catalogue`);
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="products-tva-panel">
      <button type="button" onClick={() => setOpen(!open)} data-testid="products-tva-toggle"
        className="w-full flex flex-wrap items-center justify-between gap-3 text-left">
        <div className="font-semibold flex items-center gap-2">
          <Percent className="w-4 h-4 text-[#D9B35A]" /> Fiches produits — TVA & photos
          <span className="text-xs text-white/40 font-normal">({data.count} produits — TVA appliquée sur les tickets HT / TVA / TTC)</span>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-white/40" /> : <ChevronDown className="w-4 h-4 text-white/40" />}
      </button>
      {open && (
        <div className="mt-3 grid sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-[380px] overflow-y-auto pr-1">
          {data.products.map((p) => (
            <div key={p.sku} data-testid={`tva-row-${p.sku}`}
              className={`flex items-center justify-between gap-2 rounded-lg border px-2 py-2 text-xs ${p.is_active === false ? 'bg-red-500/[0.06] border-red-500/25 opacity-70' : 'bg-white/[0.03] border-white/[0.06]'}`}>
              <span className="flex items-center gap-2 min-w-0">
                <span className="relative w-9 h-9 rounded-md overflow-hidden bg-white/[0.05] shrink-0 flex items-center justify-center">
                  {p.image_url
                    ? <img src={p.image_url} alt="" className="w-full h-full object-cover" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                    : <Package className="w-4 h-4 text-white/20" />}
                  {p.image_ai_generated && <span className="absolute bottom-0 right-0 text-[7px] bg-[#7c3aed] text-white px-0.5 rounded-tl">IA</span>}
                </span>
                <span className="min-w-0">
                  <span className="block font-medium truncate">
                    {p.name}
                    {p.is_active === false && <span className="ml-1 text-[9px] font-bold text-red-400 uppercase" data-testid={`inactive-badge-${p.sku}`}>Retiré</span>}
                  </span>
                  <span className="block text-[10px] text-white/40 truncate">
                    {p.category || '—'}{p.point_code ? ` · Relais ${p.point_code}` : ''} · {(p.price_public_cents / 100).toFixed(2)} € TTC
                  </span>
                </span>
              </span>
              <span className="flex items-center gap-1 shrink-0">
                <button type="button" onClick={() => toggleActive(p)} data-testid={`product-toggle-${p.sku}`}
                  title={p.is_active === false ? 'Remettre au catalogue' : 'Retirer du catalogue (produit suspect)'}
                  className={`w-7 h-7 rounded-md flex items-center justify-center border ${p.is_active === false
                    ? 'text-emerald-300 bg-emerald-500/10 border-emerald-500/35 hover:bg-emerald-500/25'
                    : 'text-red-300 bg-red-500/10 border-red-500/35 hover:bg-red-500/25'}`}>
                  {p.is_active === false ? <RotateCcw className="w-3 h-3" /> : <Ban className="w-3 h-3" />}
                </button>
                <button type="button" onClick={() => regenPhoto(p.sku)} disabled={aiSku === p.sku}
                  data-testid={`regen-photo-${p.sku}`}
                  title={p.image_url ? 'Remplacer par une photo IA' : 'Générer une photo IA'}
                  className="w-7 h-7 rounded-md flex items-center justify-center text-[#c4b5fd] bg-[#7c3aed]/10 border border-[#7c3aed]/35 hover:bg-[#7c3aed]/25 disabled:opacity-60">
                  {aiSku === p.sku ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                </button>
                <select value={String(p.tva_rate ?? 8.5)} data-testid={`tva-select-${p.sku}`}
                  onChange={(e) => setTva(p.sku, e.target.value)}
                  className="px-2 py-1 rounded-md bg-white/5 border border-white/10 text-xs text-white outline-none font-mono">
                  {(RATES.includes(String(p.tva_rate ?? 8.5)) ? RATES : [...RATES, String(p.tva_rate)]).map((r) => (
                    <option key={r} value={r} className="bg-[#15151c]">{r} %</option>
                  ))}
                </select>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
