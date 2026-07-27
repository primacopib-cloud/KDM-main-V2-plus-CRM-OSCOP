import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { Package, Plus, Minus, Loader2, Camera, CreditCard, Pencil, Boxes, History, ClipboardList, ScanBarcode, Search } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { lolodriveAPI } from '../../services/api';
import { PosCounterJournal } from './PosCounterJournal';
import { CounterTicketDialog } from './CounterTicketDialog';
import { StockHistoryDialog } from './StockHistoryDialog';
import { RelayFeeBanner } from './RelayFeeBanner';
import { SalesGoalBar } from './SalesGoalBar';
import { InventoryDialog } from './InventoryDialog';
import { CounterPaymentDialog } from './CounterPaymentDialog';

const STATUS_STYLE = {
  PENDING: { label: 'En attente de validation', color: '#f59e0b' },
  APPROVED: { label: 'Approuvé — en ligne', color: '#10b981' },
  REJECTED: { label: 'Refusé', color: '#ef4444' },
};

export const PosCatalogPanel = () => {
  const [catalog, setCatalog] = useState(null);
  const [mine, setMine] = useState([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: '', category: '', brand: '', description: '', price: '', stock: '', barcode: '' });
  const [photo, setPhoto] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [editSku, setEditSku] = useState(null);
  const [sale, setSale] = useState({});
  const [selling, setSelling] = useState(false);
  const [payOpen, setPayOpen] = useState(false);
  const [ticket, setTicket] = useState(null);
  const [journalKey, setJournalKey] = useState(0);
  const [stockEdit, setStockEdit] = useState(null);
  const [historyOf, setHistoryOf] = useState(null);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [scanValue, setScanValue] = useState('');

  const handleScan = () => {
    const q = scanValue.trim().toLowerCase();
    if (!q) return;
    const products = catalog?.products || [];
    const found = products.find((p) => (p.barcode || '').toLowerCase() === q || p.sku.toLowerCase() === q)
      || products.find((p) => p.sku.toLowerCase().includes(q) || p.name.toLowerCase().includes(q));
    if (!found) { toast.error(`Référence "${scanValue}" introuvable au catalogue`); return; }
    if (found.stock_qty === 0) { toast.error(`"${found.name}" est en rupture de stock`); setScanValue(''); return; }
    addSale(found.sku);
    toast.success(`${found.name} ajouté à la vente ✓`);
    setScanValue('');
  };
  const [showInventory, setShowInventory] = useState(false);
  const fileRef = useRef(null);

  const saveStock = async () => {
    const qty = parseInt(stockEdit.value, 10);
    if (Number.isNaN(qty) || qty < 0) return toast.error('Quantité invalide');
    try {
      const r = await lolodriveAPI.posSetStock(stockEdit.sku, qty);
      toast.success(`Stock de "${r.name}" mis à jour : ${r.stock_qty} unités ✓`);
      setStockEdit(null);
      load();
      setJournalKey((k) => k + 1);
    } catch (e) { toast.error(e.message); }
  };

  const uploadPhoto = async (file) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/manager/products/photo`, {
        method: 'POST', credentials: 'include', body: fd,
      });
      const d = await r.json();
      if (!r.ok) { toast.error(d.detail || 'Upload échoué'); return; }
      setPhoto(d.image_url);
      toast.success('Photo ajoutée à la fiche ✓');
    } catch { toast.error('Erreur de connexion'); } finally { setUploading(false); }
  };

  const load = () => {
    lolodriveAPI.posCatalog().then(setCatalog).catch(() => {});
    lolodriveAPI.managerProducts().then((d) => setMine(d.products || [])).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const submit = async () => {
    const cents = Math.round(parseFloat(String(form.price).replace(',', '.')) * 100);
    if (!form.name || !form.category || !form.description || !cents || cents <= 0) {
      return toast.error('Fiche incomplète : nom, catégorie, description et prix requis');
    }
    setSaving(true);
    try {
      const stockQty = form.stock !== '' ? parseInt(form.stock, 10) : undefined;
      const payload = {
        name: form.name, category: form.category, brand: form.brand || undefined,
        description: form.description, price_public_cents: cents, image_url: photo || undefined,
        stock_qty: Number.isNaN(stockQty) ? undefined : stockQty,
        barcode: form.barcode || undefined,
      };
      if (editSku) await lolodriveAPI.managerUpdateProduct(editSku, payload);
      else await lolodriveAPI.managerSubmitProduct(payload);
      toast.success(editSku ? 'Fiche corrigée et re-soumise pour validation ✓' : 'Fiche soumise au super admin pour validation ✓');
      setOpen(false);
      setForm({ name: '', category: '', brand: '', description: '', price: '', stock: '', barcode: '' });
      setPhoto(null);
      setEditSku(null);
      load();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  const startEdit = (p) => {
    setForm({ name: p.name, category: p.category || '', brand: p.brand || '', description: p.description || '', price: (p.price_public_cents / 100).toFixed(2), stock: p.stock_qty != null ? String(p.stock_qty) : '', barcode: p.barcode || '' });
    setPhoto(p.image_url || null);
    setEditSku(p.sku);
    setOpen(true);
  };

  const saleItems = Object.entries(sale).filter(([, q]) => q > 0);
  const saleTotal = saleItems.reduce((acc, [sku, qty]) => {
    const p = catalog?.products.find((x) => x.sku === sku);
    return acc + (p?.price_public_cents || 0) * qty;
  }, 0);
  const addSale = (sku) => setSale((s) => ({ ...s, [sku]: (s[sku] || 0) + 1 }));
  const decSale = (sku) => setSale((s) => ({ ...s, [sku]: Math.max(0, (s[sku] || 0) - 1) }));

  const checkout = async (method, extra = {}) => {
    setSelling(true);
    try {
      const r = await lolodriveAPI.posCounterSale(saleItems.map(([sku, qty]) => ({ sku, qty })), method, extra);
      const payLabels = {
        CASH: 'espèces', CARD: 'CB',
        UC: `${r.uc_paid} UC — CREDI'SCOP client`,
        MIXED: `combiné ${r.uc_paid} UC + ${extra.rest_method === 'CARD' ? 'CB' : 'espèces'}`,
      };
      toast.success(`Vente ${r.order_number} encaissée — ${(r.total_cents / 100).toFixed(2)} € (${payLabels[r.payment_method] || r.payment_method})${r.promo_discount_cents > 0 ? ` · promo −${(r.promo_discount_cents / 100).toFixed(2)} €` : ''}${r.client_balance_uc != null ? ` · solde client : ${r.client_balance_uc} UC` : ''}${r.relay_fee_uc > 0 ? ` · ${r.relay_fee_uc} UC débités du CREDI'SCOP` : ''}`);
      setSale({});
      setPayOpen(false);
      setTicket(r.order);
      setJournalKey((k) => k + 1);
      load();
    } catch (e) { toast.error(e.message); } finally { setSelling(false); }
  };

  if (!catalog) return null;
  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="pos-catalog-panel">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="font-semibold flex items-center gap-2">
          <Package className="w-4 h-4 text-[#D9B35A]" />
          Catalogue du relais {catalog.point_code || ''} ({catalog.products.length} produits)
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => setShowInventory(true)} data-testid="inventory-btn"
            className="border-[#22d3ee]/40 text-[#22d3ee] hover:bg-[#22d3ee]/10">
            <ClipboardList className="w-3 h-3 mr-1" /> Inventaire
          </Button>
          <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setEditSku(null); }}>
          <DialogTrigger asChild>
            <Button size="sm" className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black" data-testid="pos-submit-product-btn">
              <Plus className="w-3 h-3 mr-1" /> Proposer un produit
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-md">
            <DialogHeader><DialogTitle>{editSku ? 'Corriger la fiche refusée — re-soumission' : 'Nouvelle fiche produit — soumise au super admin'}</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Input placeholder="Nom du produit *" value={form.name} data-testid="product-name-input"
                onChange={(e) => setForm({ ...form, name: e.target.value })} className="bg-white/5 border-white/10" />
              <div className="grid grid-cols-2 gap-3">
                <Input placeholder="Catégorie *" value={form.category} data-testid="product-category-input"
                  onChange={(e) => setForm({ ...form, category: e.target.value })} className="bg-white/5 border-white/10" />
                <Input placeholder="Marque / producteur" value={form.brand} data-testid="product-brand-input"
                  onChange={(e) => setForm({ ...form, brand: e.target.value })} className="bg-white/5 border-white/10" />
              </div>
              <Textarea placeholder="Description complète *" value={form.description} rows={3} data-testid="product-description-input"
                onChange={(e) => setForm({ ...form, description: e.target.value })} className="bg-white/5 border-white/10" />
              <div className="grid grid-cols-2 gap-3">
                <Input placeholder="Prix public en € * (ex: 4.50)" value={form.price} data-testid="product-price-input"
                  onChange={(e) => setForm({ ...form, price: e.target.value })} className="bg-white/5 border-white/10" />
                <Input type="number" min="0" placeholder="Stock initial (ex: 20)" value={form.stock} data-testid="product-stock-input"
                  onChange={(e) => setForm({ ...form, stock: e.target.value })} className="bg-white/5 border-white/10" />
              </div>
              <Input placeholder="Code-barres EAN (ex: 3760001234567)" value={form.barcode} data-testid="product-barcode-input"
                onChange={(e) => setForm({ ...form, barcode: e.target.value })} className="bg-white/5 border-white/10 font-mono" />
              <input ref={fileRef} type="file" accept="image/*" className="hidden" data-testid="product-photo-input"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadPhoto(f); e.target.value = ''; }} />
              <div className="flex items-center gap-3">
                <Button type="button" variant="outline" size="sm" disabled={uploading}
                  onClick={() => fileRef.current?.click()} data-testid="product-photo-btn"
                  className="border-white/15 text-white/80">
                  {uploading ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Camera className="w-3 h-3 mr-1 text-[#D9B35A]" />}
                  {photo ? 'Changer la photo' : 'Ajouter une photo'}
                </Button>
                {photo && <img src={photo} alt="Aperçu produit" data-testid="product-photo-preview"
                  className="w-12 h-12 rounded-lg object-cover border border-[#D9B35A]/40" />}
              </div>
              <Button onClick={submit} disabled={saving} className="w-full bg-[#D9B35A] hover:bg-[#c9a34a] text-black" data-testid="product-submit-btn">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Soumettre pour validation'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
        </div>
      </div>

      <SalesGoalBar refreshKey={journalKey} />
      <RelayFeeBanner refreshKey={journalKey} />
      <PosCounterJournal refreshKey={journalKey} />
      {ticket && <CounterTicketDialog sale={ticket} onClose={() => setTicket(null)} />}
      {historyOf && <StockHistoryDialog product={historyOf} onClose={() => setHistoryOf(null)} />}
      {showInventory && <InventoryDialog products={catalog.products} onClose={() => setShowInventory(false)}
        onSaved={() => { load(); setJournalKey((k) => k + 1); }} />}

      {mine.length > 0 && (
        <div className="mb-4 space-y-1.5" data-testid="pos-my-submissions">
          <p className="text-[11px] uppercase tracking-wider text-white/40">Mes fiches produits</p>
          {mine.map((p) => (
            <div key={p.sku} className="flex items-center justify-between text-xs p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <span className="truncate">{p.name} — {(p.price_public_cents / 100).toFixed(2)} €</span>
              <span className="flex items-center gap-2 shrink-0">
                <span className="px-2 py-0.5 rounded-full font-semibold"
                  style={{ color: STATUS_STYLE[p.status]?.color, background: `${STATUS_STYLE[p.status]?.color}1a` }}
                  data-testid={`submission-status-${p.sku}`}>
                  {STATUS_STYLE[p.status]?.label || p.status}{p.status === 'REJECTED' && p.reject_reason ? ` · ${p.reject_reason}` : ''}
                </span>
                {p.status === 'REJECTED' && (
                  <button type="button" onClick={() => startEdit(p)} data-testid={`edit-rejected-${p.sku}`}
                    className="flex items-center gap-1 px-2 py-0.5 rounded-full font-semibold text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/30 hover:bg-[#D9B35A]/20">
                    <Pencil className="w-3 h-3" /> Corriger
                  </button>
                )}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="mb-3 flex flex-wrap gap-2" data-testid="pos-catalog-toolbar">
        <div className="flex items-center gap-1.5 flex-1 min-w-[220px] px-3 rounded-lg bg-[#D9B35A]/[0.06] border border-[#D9B35A]/30">
          <ScanBarcode className="w-4 h-4 text-[#D9B35A] shrink-0" />
          <input value={scanValue} data-testid="product-scan-input"
            onChange={(e) => setScanValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleScan(); }}
            placeholder="Scanner code-barres EAN / référence + Entrée"
            className="w-full bg-transparent py-2 text-xs text-white outline-none placeholder:text-white/30" />
        </div>
        <div className="flex items-center gap-1.5 flex-1 min-w-[180px] px-3 rounded-lg bg-white/[0.04] border border-white/10">
          <Search className="w-3.5 h-3.5 text-white/40 shrink-0" />
          <input value={search} data-testid="catalog-search-input"
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher un produit…"
            className="w-full bg-transparent py-2 text-xs text-white outline-none placeholder:text-white/30" />
        </div>
        <select value={category} onChange={(e) => setCategory(e.target.value)} data-testid="catalog-category-select"
          className="px-3 py-2 rounded-lg bg-white/[0.04] border border-white/10 text-xs text-white outline-none">
          <option value="" className="bg-[#15151c]">Toutes catégories</option>
          {[...new Set(catalog.products.map((p) => p.category).filter(Boolean))].sort().map((c) => (
            <option key={c} value={c} className="bg-[#15151c]">{c}</option>
          ))}
        </select>
      </div>

      <div className="max-h-[520px] overflow-y-auto grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 pr-1" data-testid="pos-catalog-list">
        {catalog.products
          .filter((p) => !category || p.category === category)
          .filter((p) => {
            const q = search.trim().toLowerCase();
            if (!q) return true;
            return p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q)
              || (p.brand || '').toLowerCase().includes(q);
          })
          .map((p) => (
          <div key={p.sku} data-testid={`pos-product-${p.sku}`}
            className="relative rounded-2xl bg-white/[0.025] border border-white/[0.07] overflow-hidden hover:border-white/[0.15] transition-colors">
            {p.image_url ? (
              <div className="aspect-square bg-white/[0.02] overflow-hidden">
                <img src={p.image_url} alt={p.name} loading="lazy" className="w-full h-full object-cover"
                  onError={(e) => { e.currentTarget.style.display = 'none'; }} />
              </div>
            ) : (
              <div className="aspect-square bg-white/[0.03] flex items-center justify-center">
                <Package className="w-10 h-10 text-white/15" />
              </div>
            )}
            <div className="p-3">
              <div className="flex flex-wrap gap-1 mb-1.5 text-[9px] font-bold">
                {p.catalog_type === 'ESSENTIAL'
                  ? <span className="px-1.5 py-0.5 rounded text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/30">ESSENTIEL</span>
                  : <span className="px-1.5 py-0.5 rounded text-[#c4b5fd] bg-[#7c3aed]/10 border border-[#7c3aed]/30">HORS-25</span>}
                {p.point_code && <span className="px-1.5 py-0.5 rounded text-emerald-300 bg-emerald-400/10 border border-emerald-400/30">Relais {p.point_code}</span>}
              </div>
              <div className="font-medium text-xs leading-tight mb-0.5 line-clamp-2">{p.name}</div>
              <div className="text-[10px] text-white/35 mb-1.5 truncate">{p.brand ? `${p.brand} · ` : ''}{p.category || p.sku}{p.barcode ? ` · ${p.barcode}` : ''}</div>
              <div className="mb-2">
                <span className="text-sm font-bold font-mono">{(p.price_public_cents / 100).toFixed(2)} €</span>
                <span className="text-[10px] text-[#D9B35A] font-mono"> · {p.uc_public} UC</span>
                {p.price_pass_cents != null && (
                  <span className="block text-[10px] text-white/40 font-mono">PASS {(p.price_pass_cents / 100).toFixed(2)} € · {p.uc_pass} UC</span>
                )}
              </div>
              <div className="flex items-center gap-1.5 mb-2">
                {stockEdit?.sku === p.sku ? (
                  <span className="flex items-center gap-1">
                    <input type="number" min="0" autoFocus value={stockEdit.value} data-testid={`stock-input-${p.sku}`}
                      onChange={(e) => setStockEdit({ ...stockEdit, value: e.target.value })}
                      onKeyDown={(e) => { if (e.key === 'Enter') saveStock(); if (e.key === 'Escape') setStockEdit(null); }}
                      className="w-16 px-1.5 py-0.5 rounded bg-white/10 border border-[#D9B35A]/50 text-white text-xs font-mono" />
                    <button type="button" onClick={saveStock} data-testid={`stock-save-${p.sku}`}
                      className="px-1.5 py-0.5 rounded text-[10px] font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a]">OK</button>
                  </span>
                ) : (
                  <button type="button" title="Ajuster le stock (réassort)" data-testid={`stock-badge-${p.sku}`}
                    onClick={() => setStockEdit({ sku: p.sku, value: p.stock_qty ?? '' })}
                    className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold border ${
                      p.stock_qty == null ? 'text-white/40 bg-white/[0.04] border-white/10'
                        : p.stock_qty <= 5 ? 'text-red-300 bg-red-500/10 border-red-400/35'
                          : p.stock_qty <= 15 ? 'text-amber-300 bg-amber-400/10 border-amber-400/35'
                            : 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30'
                    } hover:brightness-125`}>
                    <Boxes className="w-3 h-3" /> {p.stock_qty == null ? 'Stock ?' : `Stock ${p.stock_qty}`}
                  </button>
                )}
                <button type="button" title="Historique du stock" data-testid={`stock-history-btn-${p.sku}`}
                  onClick={() => setHistoryOf({ sku: p.sku, name: p.name })}
                  className="w-6 h-6 rounded-full flex items-center justify-center bg-white/[0.05] border border-white/10 text-white/50 hover:text-[#D9B35A] hover:border-[#D9B35A]/40 shrink-0">
                  <History className="w-3 h-3" />
                </button>
              </div>
              <button type="button" onClick={() => addSale(p.sku)} data-testid={`sale-add-${p.sku}`}
                disabled={p.stock_qty === 0}
                title={p.stock_qty === 0 ? 'Rupture de stock — vente impossible' : 'Ajouter à la vente au comptoir'}
                className={`w-full flex items-center justify-center gap-1 py-1.5 rounded-lg text-xs font-bold border ${
                  p.stock_qty === 0
                    ? 'bg-white/[0.03] border-white/10 text-white/25 cursor-not-allowed'
                    : 'bg-[#D9B35A]/15 border-[#D9B35A]/40 text-[#D9B35A] hover:bg-[#D9B35A]/30'
                }`}>
                <Plus className="w-3 h-3" /> {p.stock_qty === 0 ? 'Rupture' : 'Vendre'}
                {sale[p.sku] ? <span className="ml-1 px-1.5 rounded-full bg-[#D9B35A] text-black">{sale[p.sku]}</span> : null}
              </button>
            </div>
          </div>
        ))}
      </div>

      {saleItems.length > 0 && (
        <div className="mt-4 rounded-xl border border-[#D9B35A]/35 bg-[#D9B35A]/[0.06] p-3" data-testid="counter-sale-cart">
          <p className="text-[11px] uppercase tracking-wider text-[#D9B35A] mb-2 font-bold">Vente au comptoir</p>
          <div className="space-y-1.5 mb-3">
            {saleItems.map(([sku, qty]) => {
              const p = catalog.products.find((x) => x.sku === sku);
              return (
                <div key={sku} className="flex items-center justify-between text-xs">
                  <span className="truncate">{p?.name || sku}</span>
                  <span className="flex items-center gap-2 shrink-0 ml-3">
                    <button type="button" onClick={() => decSale(sku)} className="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center"><Minus className="w-3 h-3" /></button>
                    <span className="font-mono w-5 text-center">{qty}</span>
                    <button type="button" onClick={() => addSale(sku)} className="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center"><Plus className="w-3 h-3" /></button>
                    <span className="font-mono w-16 text-right">{(((p?.price_public_cents || 0) * qty) / 100).toFixed(2)} €</span>
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="font-bold" data-testid="counter-sale-total">Total : {(saleTotal / 100).toFixed(2)} €<span className="text-[11px] text-white/40 font-normal"> (promos appliquées à l'encaissement)</span></span>
            <span className="flex gap-2">
              <Button size="sm" disabled={selling} onClick={() => setPayOpen(true)} data-testid="checkout-open-btn"
                className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black font-bold">
                <CreditCard className="w-3 h-3 mr-1" /> Encaisser (espèces · CB · UC)
              </Button>
            </span>
          </div>
          {payOpen && (
            <CounterPaymentDialog total={saleTotal} selling={selling}
              onClose={() => setPayOpen(false)} onCheckout={checkout} />
          )}
        </div>
      )}
    </div>
  );
};
