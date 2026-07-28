import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Percent, ChevronDown, ChevronUp, Package, Sparkles, Loader2, Ban, RotateCcw, Download, Upload } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';
import { ProductToggleHistory } from './ProductToggleHistory';

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

  const saveSupplier = async (p) => {
    const supplier = document.querySelector(`[data-testid="supplier-input-${p.sku}"]`)?.value.trim() || '';
    const email = document.querySelector(`[data-testid="supplier-email-input-${p.sku}"]`)?.value.trim() || '';
    const rawPrice = document.querySelector(`[data-testid="purchase-input-${p.sku}"]`)?.value.trim() || '';
    let purchase = null;
    if (rawPrice !== '') {
      purchase = Math.round(parseFloat(rawPrice.replace(',', '.')) * 100);
      if (Number.isNaN(purchase) || purchase < 0) return toast.error("Prix d'achat invalide");
    }
    if (supplier === (p.supplier || '') && email === (p.supplier_email || '') && purchase === (p.purchase_price_cents ?? null)) return;
    try {
      await lolodriveAPI.adminSetProductSupplier(p.sku, { supplier, supplier_email: email, purchase_price_cents: purchase });
      setData((prev) => ({ ...prev, products: prev.products.map((x) => (x.sku === p.sku ? { ...x, supplier: supplier || null, supplier_email: email || null, purchase_price_cents: purchase } : x)) }));
      toast.success('Fournisseur enregistré ✓');
    } catch (e) { toast.error(e.message); }
  };

  const importCsv = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    try {
      const text = await f.text();
      const r = await lolodriveAPI.adminImportProductsCsv(text);
      toast.success(`Import CSV : ${r.updated} fiche(s) mise(s) à jour${r.error_count ? ` — ${r.error_count} erreur(s)` : ''} ✓`);
      if (r.errors?.length) toast.warning(r.errors.slice(0, 5).join(' · '));
      lolodriveAPI.adminProductsTva().then(setData).catch(() => {});
    } catch (err) { toast.error(err.message); }
  };

  const exportCsv = async () => {
    try {
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/admin/products/export.csv`, { credentials: 'include' });
      if (!r.ok) return toast.error('Export indisponible');
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement('a');
      a.href = url; a.download = 'produits-kdmarche.csv'; a.click();
      URL.revokeObjectURL(url);
      toast.success('Export CSV téléchargé ✓');
    } catch { toast.error('Erreur de connexion'); }
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
        <>
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <button type="button" onClick={exportCsv} data-testid="export-products-csv-btn"
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold text-[#22d3ee] bg-[#22d3ee]/10 border border-[#22d3ee]/35 hover:bg-[#22d3ee]/20">
            <Download className="w-3 h-3" /> Exporter CSV
          </button>
          <label data-testid="import-products-csv-btn"
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold text-emerald-300 bg-emerald-500/10 border border-emerald-500/35 hover:bg-emerald-500/20 cursor-pointer">
            <Upload className="w-3 h-3" /> Importer CSV
            <input type="file" accept=".csv,text/csv" className="hidden" onChange={importCsv} data-testid="import-products-csv-input" />
          </label>
          <span className="text-[10px] text-white/30">exportez, modifiez puis réimportez — colonnes : sku · prix_public_eur · tva · fournisseur · email_fournisseur · prix_achat_eur · actif</span>
        </div>
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
                    {p.purchase_price_cents != null && p.price_public_cents > 0 && (
                      <span className="text-emerald-300/80" data-testid={`margin-${p.sku}`}> · marge {Math.round(100 * (p.price_public_cents - p.purchase_price_cents) / p.price_public_cents)} %</span>
                    )}
                  </span>
                  <span className="mt-0.5 flex gap-1">
                    <input type="text" key={`s-${p.supplier || ''}`} defaultValue={p.supplier || ''} placeholder="Fournisseur…"
                      data-testid={`supplier-input-${p.sku}`}
                      onBlur={() => saveSupplier(p)}
                      onKeyDown={(ev) => ev.key === 'Enter' && ev.target.blur()}
                      className="w-full max-w-[105px] bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-[10px] text-white/70 placeholder:text-white/25" />
                    <input type="text" key={`e-${p.supplier_email || ''}`} defaultValue={p.supplier_email || ''} placeholder="email fournisseur…"
                      data-testid={`supplier-email-input-${p.sku}`}
                      onBlur={() => saveSupplier(p)}
                      onKeyDown={(ev) => ev.key === 'Enter' && ev.target.blur()}
                      className="w-full max-w-[105px] bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-[10px] text-white/70 placeholder:text-white/25" />
                    <input type="text" key={`p-${p.purchase_price_cents ?? ''}`} defaultValue={p.purchase_price_cents != null ? (p.purchase_price_cents / 100).toFixed(2) : ''} placeholder="achat €"
                      data-testid={`purchase-input-${p.sku}`}
                      onBlur={() => saveSupplier(p)}
                      onKeyDown={(ev) => ev.key === 'Enter' && ev.target.blur()}
                      className="w-full max-w-[52px] bg-white/5 border border-emerald-500/25 rounded px-1.5 py-0.5 text-[10px] text-emerald-200/80 placeholder:text-white/25 font-mono" />
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
        <ProductToggleHistory />
        </>
      )}
    </div>
  );
};
