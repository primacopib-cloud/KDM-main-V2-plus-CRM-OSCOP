import { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Boxes, Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { lolodriveAPI } from '../../services/api';

// Super admin : création d'un produit vendu en LOT (×2, ×3, ×3 +1 offert…) à partir d'un produit de base
export const CreateLotDialog = ({ products, onClose, onCreated }) => {
  const bases = useMemo(() => products.filter((p) => !p.is_lot), [products]);
  const [baseSku, setBaseSku] = useState('');
  const [paid, setPaid] = useState('3');
  const [free, setFree] = useState('0');
  const [price, setPrice] = useState('');
  const [busy, setBusy] = useState(false);

  const base = bases.find((p) => p.sku === baseSku);
  const paidN = parseInt(paid, 10) || 0;
  const freeN = parseInt(free, 10) || 0;
  const autoPrice = base ? (base.price_public_cents * paidN) / 100 : 0;

  const create = async () => {
    if (!base) return toast.error('Choisissez un produit de base');
    setBusy(true);
    try {
      const payload = { base_sku: base.sku, paid_qty: paidN, free_qty: freeN };
      if (price !== '') {
        const c = Math.round(parseFloat(price.replace(',', '.')) * 100);
        if (Number.isNaN(c) || c <= 0) { setBusy(false); return toast.error('Prix invalide'); }
        payload.price_public_cents = c;
      }
      const d = await lolodriveAPI.adminCreateLot(payload);
      toast.success(`Lot créé : ${d.name} — ${(d.price_public_cents / 100).toFixed(2)} € ✓`);
      onCreated();
      onClose();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-md" data-testid="create-lot-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <Boxes className="w-4 h-4 text-fuchsia-400" /> Créer un produit en lot
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3 text-xs">
          <label className="block">
            <span className="text-white/50">Produit de base</span>
            <select value={baseSku} onChange={(e) => { setBaseSku(e.target.value); setPrice(''); }} data-testid="lot-base-select"
              className="mt-1 w-full bg-white/5 border border-white/15 rounded-lg px-2 py-2 text-white text-xs">
              <option value="" className="bg-[#15151c]">— choisir un produit —</option>
              {bases.map((p) => (
                <option key={p.sku} value={p.sku} className="bg-[#15151c]">
                  {p.name} — {(p.price_public_cents / 100).toFixed(2)} €
                </option>
              ))}
            </select>
          </label>
          <div className="flex gap-3">
            <label className="flex-1">
              <span className="text-white/50">Quantité payée</span>
              <select value={paid} onChange={(e) => setPaid(e.target.value)} data-testid="lot-paid-select"
                className="mt-1 w-full bg-white/5 border border-white/15 rounded-lg px-2 py-2 text-white text-xs">
                {[2, 3, 4, 5, 6, 8, 10, 12, 24].map((n) => <option key={n} value={n} className="bg-[#15151c]">×{n}</option>)}
              </select>
            </label>
            <label className="flex-1">
              <span className="text-white/50">Unités offertes</span>
              <select value={free} onChange={(e) => setFree(e.target.value)} data-testid="lot-free-select"
                className="mt-1 w-full bg-white/5 border border-white/15 rounded-lg px-2 py-2 text-white text-xs">
                {[0, 1, 2, 3].map((n) => <option key={n} value={n} className="bg-[#15151c]">{n ? `+${n} gratuit${n > 1 ? 's' : ''}` : 'aucune'}</option>)}
              </select>
            </label>
          </div>
          <label className="block">
            <span className="text-white/50">Prix public du lot (€) — auto : {autoPrice.toFixed(2)} €</span>
            <input type="text" value={price} onChange={(e) => setPrice(e.target.value)} data-testid="lot-price-input"
              placeholder={autoPrice ? autoPrice.toFixed(2) : '—'}
              className="mt-1 w-full bg-white/5 border border-white/15 rounded-lg px-2 py-2 text-white text-xs font-mono" />
          </label>
          {base && (
            <p className="rounded-lg bg-fuchsia-500/10 border border-fuchsia-400/30 px-2.5 py-2 text-[11px] text-fuchsia-200" data-testid="lot-preview">
              📦 {base.name} — Lot ×{paidN + freeN}{freeN ? ` (${freeN} offert${freeN > 1 ? 's' : ''})` : ''} ·{' '}
              {(price !== '' ? price : autoPrice.toFixed(2))} € · stock géré en nombre de lots (indépendant du produit unitaire)
            </p>
          )}
        </div>
        <Button onClick={create} disabled={busy} data-testid="create-lot-btn"
          className="w-full bg-fuchsia-500 hover:bg-fuchsia-600 text-white font-bold">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Créer le lot au catalogue'}
        </Button>
      </DialogContent>
    </Dialog>
  );
};
