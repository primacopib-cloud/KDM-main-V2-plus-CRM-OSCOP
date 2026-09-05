import { useState, useEffect } from 'react';
import { Boxes, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const ZONES = ['GUADELOUPE', 'MARTINIQUE', 'GUYANE', 'REUNION'];

export const ZoneStockButton = ({ product }) => {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState(null);
  const [savingZone, setSavingZone] = useState(null);

  useEffect(() => {
    if (!open) return;
    fetch(`${API_URL}/api/catalog/admin/stock/${product.id}`, { headers: getAuthHeaders() })
      .then((r) => r.json())
      .then((d) => {
        const byZone = Object.fromEntries((d.stocks || []).map((s) => [s.zone_code, s]));
        setRows(ZONES.map((z) => ({
          zone_code: z,
          quantity_available: byZone[z]?.quantity_available ?? 0,
          quantity_reserved: byZone[z]?.quantity_reserved ?? 0,
        })));
      })
      .catch(() => toast.error('Erreur de chargement des stocks'));
  }, [open, product.id]);

  const save = async (row) => {
    setSavingZone(row.zone_code);
    try {
      const res = await fetch(`${API_URL}/api/catalog/admin/stock/${product.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ zone_code: row.zone_code, quantity_available: Number(row.quantity_available) || 0 }),
      });
      if (!res.ok) throw new Error();
      const d = await res.json();
      toast.success(`Stock ${row.zone_code} : ${d.quantity_available} unités${d.restock_alert_triggered ? ' (alerte réassort envoyée)' : ''}`);
    } catch {
      toast.error('Échec de la mise à jour du stock');
    } finally {
      setSavingZone(null);
    }
  };

  return (
    <>
      <Button size="sm" onClick={() => setOpen(true)} data-testid={`product-stock-${product.id}`}
        title="Stocks par territoire"
        className="bg-white/[0.06] border border-white/15 text-white/70 hover:bg-white/[0.12] h-8 px-2 text-xs">
        <Boxes className="w-3.5 h-3.5" />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-[#2B1548] border border-[#D9B35A]/30 text-white max-w-md" data-testid="zone-stock-dialog">
          <DialogHeader>
            <DialogTitle className="text-[#E9CF8E]">Stocks par territoire — {product.name}</DialogTitle>
          </DialogHeader>
          {!rows ? (
            <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-[#D9B35A]" /></div>
          ) : (
            <div className="space-y-3">
              {rows.map((row, i) => (
                <div key={row.zone_code} className="flex items-center gap-3">
                  <span className="w-32 text-sm text-white/80">{row.zone_code}</span>
                  <Input
                    type="number" min="0" value={row.quantity_available}
                    data-testid={`stock-input-${row.zone_code}`}
                    onChange={(e) => setRows((p) => p.map((r, j) => (j === i ? { ...r, quantity_available: e.target.value } : r)))}
                    className="h-9 w-28 bg-white/[0.06] border-white/15 text-white"
                  />
                  <span className="text-xs text-white/40">réservé : {row.quantity_reserved}</span>
                  <Button size="sm" onClick={() => save(row)} disabled={savingZone === row.zone_code}
                    data-testid={`stock-save-${row.zone_code}`}
                    className="ml-auto bg-[#D9B35A] hover:bg-[#c9a34a] text-black h-8 px-3 text-xs font-bold">
                    {savingZone === row.zone_code ? '…' : 'Enregistrer'}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};
