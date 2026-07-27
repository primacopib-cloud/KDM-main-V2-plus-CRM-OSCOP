import { useState } from 'react';
import { toast } from 'sonner';
import { ClipboardList, Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { lolodriveAPI } from '../../services/api';

export const InventoryDialog = ({ products, onClose, onSaved }) => {
  const [values, setValues] = useState(() =>
    Object.fromEntries(products.map((p) => [p.sku, p.stock_qty != null ? String(p.stock_qty) : ''])));
  const [saving, setSaving] = useState(false);

  const save = async () => {
    const items = Object.entries(values)
      .filter(([, v]) => v !== '' && !Number.isNaN(parseInt(v, 10)))
      .map(([sku, v]) => ({ sku, stock_qty: parseInt(v, 10) }));
    if (items.length === 0) return toast.error('Aucun stock renseigné');
    setSaving(true);
    try {
      const r = await lolodriveAPI.posInventory(items);
      toast.success(`Inventaire enregistré — ${r.updated_count} stock(s) corrigé(s) ✓`);
      onSaved();
      onClose();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-lg" data-testid="inventory-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <ClipboardList className="w-4 h-4 text-[#22d3ee]" /> Inventaire rapide — recomptez vos stocks
          </DialogTitle>
        </DialogHeader>
        <p className="text-[11px] text-white/40 -mt-1">Saisissez le stock réel compté pour chaque produit. Seuls les stocks modifiés seront corrigés (tracés dans l'historique).</p>
        <div className="max-h-80 overflow-y-auto space-y-1.5">
          {products.map((p) => (
            <div key={p.sku} className="flex items-center gap-3 text-xs p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <span className="flex-1 truncate">
                {p.name}
                {p.point_code && <span className="ml-1.5 px-1 py-0.5 rounded text-[9px] font-bold text-[#D9B35A] bg-[#D9B35A]/10">Relais</span>}
              </span>
              <span className="text-white/35 font-mono shrink-0">actuel : {p.stock_qty != null ? p.stock_qty : '—'}</span>
              <input type="number" min="0" value={values[p.sku]} data-testid={`inventory-input-${p.sku}`}
                onChange={(e) => setValues((v) => ({ ...v, [p.sku]: e.target.value }))}
                placeholder="?"
                className="w-20 px-2 py-1 rounded bg-white/10 border border-[#22d3ee]/40 text-white text-xs font-mono shrink-0" />
            </div>
          ))}
        </div>
        <Button onClick={save} disabled={saving} data-testid="inventory-save-btn"
          className="w-full bg-[#22d3ee] hover:bg-[#06b6d4] text-black font-bold">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Enregistrer l'inventaire"}
        </Button>
      </DialogContent>
    </Dialog>
  );
};
