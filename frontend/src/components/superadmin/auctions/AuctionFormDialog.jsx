import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../../services/http';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../ui/dialog';
import { Input } from '../../ui/input';
import { Button } from '../../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Switch } from '../../ui/switch';

const SOURCES = [
  ['LOLODRIVE', 'LOLODRIVE'], ['VENDOR', 'Vendeur'], ['PARTNER', 'Partenaire'],
  ['KDMARCHE', 'KDMARCHÉ'], ['OSCOP', "O'SCOP"],
];
const toLocal = (iso) => (iso ? new Date(iso).toISOString().slice(0, 16) : '');

export const AuctionFormDialog = ({ auction, onClose, onSaved }) => {
  const [form, setForm] = useState(() => auction ? {
    ...auction, starts_at: toLocal(auction.starts_at), ends_at: toLocal(auction.ends_at),
  } : {
    title: '', image_url: '', description: '', source: 'LOLODRIVE', source_visible: true,
    product_id: '', category_id: '', type_id: '', value_eur: '', floor_eur: 0,
    bid_cost_credits: 10, price_drop_eur: 1, starts_at: '', ends_at: '', recurrence: 'NONE',
  });
  const [pickerSource, setPickerSource] = useState('lolodrive');
  const [pickerQ, setPickerQ] = useState('');
  const [products, setProducts] = useState([]);
  const [cats, setCats] = useState([]);
  const [types, setTypes] = useState([]);
  const [busy, setBusy] = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    const h = { headers: getAuthHeaders(), credentials: 'include' };
    fetch(`${API}/admin/auctions/taxonomy/categories`, h).then((r) => r.json()).then((d) => setCats(d.items || []));
    fetch(`${API}/admin/auctions/taxonomy/types`, h).then((r) => r.json()).then((d) => setTypes(d.items || []));
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      fetch(`${API}/admin/auctions/products?source=${pickerSource}&q=${encodeURIComponent(pickerQ)}`,
        { headers: getAuthHeaders(), credentials: 'include' })
        .then((r) => r.json()).then((d) => setProducts(d.items || [])).catch(() => {});
    }, 300);
    return () => clearTimeout(t);
  }, [pickerSource, pickerQ]);

  const pick = (p) => {
    setForm((f) => ({
      ...f, title: p.name, image_url: p.image_url || '', product_id: p.product_id,
      value_eur: p.value_eur || f.value_eur,
      source: pickerSource === 'lolodrive' ? 'LOLODRIVE' : 'VENDOR',
    }));
  };

  const applyType = (typeId) => {
    const t = types.find((x) => x.id === typeId);
    setForm((f) => ({
      ...f, type_id: typeId,
      bid_cost_credits: t?.bid_cost_credits ?? f.bid_cost_credits,
      price_drop_eur: t?.price_drop_eur ?? f.price_drop_eur,
    }));
  };

  const save = async () => {
    setBusy(true);
    try {
      const body = {
        ...form,
        value_eur: parseFloat(form.value_eur), floor_eur: parseFloat(form.floor_eur || 0),
        bid_cost_credits: parseInt(form.bid_cost_credits, 10), price_drop_eur: parseFloat(form.price_drop_eur),
        starts_at: new Date(form.starts_at).toISOString(), ends_at: new Date(form.ends_at).toISOString(),
        category_id: form.category_id || null, type_id: form.type_id || null,
      };
      const url = auction ? `${API}/admin/auctions/${auction.id}` : `${API}/admin/auctions`;
      const res = await fetch(url, {
        method: auction ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        credentials: 'include', body: JSON.stringify(body),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(auction ? 'Enchère mise à jour' : `Enchère ${d.reference} programmée`);
      onSaved();
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  const inputCls = 'bg-white/[0.05] border-white/15 text-white text-xs h-9';
  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#2A1045] border-[#D9B35A]/30 text-white max-w-2xl max-h-[85vh] overflow-y-auto"
        data-testid="auction-form-dialog">
        <DialogHeader>
          <DialogTitle className="text-[#E9CF8E]">{auction ? `Modifier ${auction.reference}` : 'Nouvelle enchère produit'}</DialogTitle>
        </DialogHeader>

        {!auction && (
          <div className="rounded-xl bg-white/[0.04] border border-white/10 p-3 space-y-2">
            <div className="flex gap-2 items-center">
              <span className="text-[10px] text-white/50 uppercase">Choisir dans</span>
              {[['lolodrive', 'Catalogue LOLODRIVE'], ['vendor', 'Catalogue vendeurs']].map(([v, l]) => (
                <button key={v} type="button" onClick={() => setPickerSource(v)}
                  data-testid={`picker-source-${v}`}
                  className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                    pickerSource === v ? 'bg-[#D9B35A] text-[#2A1045] border-[#D9B35A]' : 'bg-white/[0.05] text-white/60 border-white/15'}`}>
                  {l}
                </button>
              ))}
              <Input value={pickerQ} onChange={(e) => setPickerQ(e.target.value)} placeholder="Rechercher…"
                className={`${inputCls} flex-1`} data-testid="picker-search" />
            </div>
            <div className="flex gap-1.5 flex-wrap max-h-28 overflow-y-auto">
              {products.map((p) => (
                <button key={p.product_id} type="button" onClick={() => pick(p)}
                  data-testid={`picker-item-${p.sku || p.product_id}`}
                  className={`px-2 py-1 rounded-lg text-[10px] border transition-colors ${
                    form.product_id === p.product_id ? 'bg-[#D9B35A]/25 border-[#D9B35A]/50 text-[#E9CF8E]' : 'bg-white/[0.04] border-white/10 text-white/65 hover:bg-white/10'}`}>
                  {p.name} · {Number(p.value_eur).toFixed(2)} €
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs text-white/60 col-span-2">Titre du lot
            <Input value={form.title} onChange={(e) => set('title', e.target.value)} className={inputCls} data-testid="auction-title-input" /></label>
          <label className="text-xs text-white/60">Provenance
            <Select value={form.source} onValueChange={(v) => set('source', v)}>
              <SelectTrigger className={inputCls} data-testid="auction-source-select"><SelectValue /></SelectTrigger>
              <SelectContent>{SOURCES.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
            </Select></label>
          <label className="text-xs text-white/60 flex items-center gap-2 pt-5">
            <Switch checked={form.source_visible} onCheckedChange={(v) => set('source_visible', v)}
              data-testid="auction-source-visible-switch" />
            Afficher la provenance aux membres
          </label>
          <label className="text-xs text-white/60">Catégorie
            <Select value={form.category_id || 'none'} onValueChange={(v) => set('category_id', v === 'none' ? '' : v)}>
              <SelectTrigger className={inputCls} data-testid="auction-category-select"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="none">—</SelectItem>
                {cats.map((c) => <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>)}</SelectContent>
            </Select></label>
          <label className="text-xs text-white/60">Type d'enchère (conditions de mise)
            <Select value={form.type_id || 'none'} onValueChange={(v) => v !== 'none' && applyType(v)}>
              <SelectTrigger className={inputCls} data-testid="auction-type-select"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="none">—</SelectItem>
                {types.map((t) => <SelectItem key={t.id} value={t.id}>{t.label}</SelectItem>)}</SelectContent>
            </Select></label>
          <label className="text-xs text-white/60">Valeur du produit (€)
            <Input type="number" step="0.01" value={form.value_eur} onChange={(e) => set('value_eur', e.target.value)}
              className={inputCls} data-testid="auction-value-input" /></label>
          <label className="text-xs text-white/60">Prix plancher € (jamais affiché)
            <Input type="number" step="0.01" value={form.floor_eur} onChange={(e) => set('floor_eur', e.target.value)}
              className={inputCls} data-testid="auction-floor-input" /></label>
          <label className="text-xs text-white/60">Coût d'une mise (crédits)
            <Input type="number" value={form.bid_cost_credits} onChange={(e) => set('bid_cost_credits', e.target.value)}
              className={inputCls} data-testid="auction-bidcost-input" /></label>
          <label className="text-xs text-white/60">Baisse de prix par mise (€)
            <Input type="number" step="0.01" value={form.price_drop_eur} onChange={(e) => set('price_drop_eur', e.target.value)}
              className={inputCls} data-testid="auction-drop-input" /></label>
          <label className="text-xs text-white/60">Début
            <Input type="datetime-local" value={form.starts_at} onChange={(e) => set('starts_at', e.target.value)}
              className={inputCls} data-testid="auction-starts-input" /></label>
          <label className="text-xs text-white/60">Fin
            <Input type="datetime-local" value={form.ends_at} onChange={(e) => set('ends_at', e.target.value)}
              className={inputCls} data-testid="auction-ends-input" /></label>
          <label className="text-xs text-white/60 col-span-2">Récurrence (relance automatique)
            <Select value={form.recurrence} onValueChange={(v) => set('recurrence', v)}>
              <SelectTrigger className={inputCls} data-testid="auction-recurrence-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="NONE">Aucune — planification simple</SelectItem>
                <SelectItem value="DAILY">Quotidienne</SelectItem>
                <SelectItem value="MONTHLY">Mensuelle</SelectItem>
                <SelectItem value="YEARLY">Annuelle</SelectItem>
              </SelectContent>
            </Select></label>
        </div>

        <Button onClick={save} disabled={busy || !form.title || !form.value_eur || !form.starts_at || !form.ends_at}
          data-testid="auction-save-btn"
          className="bg-[#D9B35A] text-[#2A1045] hover:bg-[#F2D07A] font-semibold">
          {auction ? 'Enregistrer' : "Programmer l'enchère"}
        </Button>
      </DialogContent>
    </Dialog>
  );
};
