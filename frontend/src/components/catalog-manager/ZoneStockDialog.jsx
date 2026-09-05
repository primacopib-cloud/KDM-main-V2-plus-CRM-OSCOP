import { useState, useEffect } from 'react';
import { Boxes, Loader2, History } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const ZONES = ['GUADELOUPE', 'MARTINIQUE', 'GUYANE', 'REUNION'];

const StockHistory = ({ productId, refreshKey }) => {
  const [entries, setEntries] = useState([]);
  useEffect(() => {
    fetch(`${API_URL}/api/catalog/admin/stock-history?product_id=${productId}&limit=10`, { headers: getAuthHeaders() })
      .then((r) => r.json())
      .then((d) => setEntries(d.entries || []))
      .catch(() => {});
  }, [productId, refreshKey]);
  if (!entries.length) return null;
  return (
    <div className="mt-4 pt-3 border-t border-white/10" data-testid="stock-history">
      <p className="text-xs font-semibold text-[#E9CF8E] flex items-center gap-1.5 mb-2">
        <History className="w-3.5 h-3.5" /> Historique des ajustements
      </p>
      <div className="max-h-40 overflow-y-auto space-y-1">
        {entries.map((e) => (
          <div key={e.id} className="flex items-center gap-2 text-[11px] text-white/60" data-testid="stock-history-entry">
            <span className="w-24 shrink-0 font-mono text-white/40">{new Date(e.created_at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
            <span className="w-24 shrink-0">{e.zone_code}</span>
            <span className="font-mono">{e.old_quantity} → <strong className="text-white/85">{e.new_quantity}</strong></span>
            <span className="ml-auto truncate text-white/40">{e.author_email}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export const ZoneStockButton = ({ product }) => {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState(null);
  const [savingZone, setSavingZone] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

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
          reorder_point: byZone[z]?.reorder_point ?? 10,
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
        body: JSON.stringify({
          zone_code: row.zone_code,
          quantity_available: Number(row.quantity_available) || 0,
          reorder_point: Number(row.reorder_point) || 0,
        }),
      });
      if (!res.ok) throw new Error();
      const d = await res.json();
      setRefreshKey((k) => k + 1);
      let msg = `Stock ${row.zone_code} : ${d.quantity_available} unités`;
      if (d.restock_alert_triggered) msg += ' (alerte réassort envoyée)';
      if (d.low_stock_alert_triggered) msg += ' — ⚠ sous le seuil, admins alertés par email';
      toast.success(msg);
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
            <div className="space-y-3">              {rows.map((row, i) => (
                <div key={row.zone_code} className="flex items-center gap-2">
                  <span className="w-28 shrink-0 text-sm text-white/80">{row.zone_code}</span>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-white/40">Stock</span>
                    <Input
                      type="number" min="0" value={row.quantity_available}
                      data-testid={`stock-input-${row.zone_code}`}
                      onChange={(e) => setRows((p) => p.map((r, j) => (j === i ? { ...r, quantity_available: e.target.value } : r)))}
                      className="h-9 w-24 bg-white/[0.06] border-white/15 text-white"
                    />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-[#E9CF8E]/70">Seuil réassort</span>
                    <Input
                      type="number" min="0" value={row.reorder_point}
                      data-testid={`threshold-input-${row.zone_code}`}
                      onChange={(e) => setRows((p) => p.map((r, j) => (j === i ? { ...r, reorder_point: e.target.value } : r)))}
                      className="h-9 w-20 bg-[#D9B35A]/[0.08] border-[#D9B35A]/25 text-[#E9CF8E]"
                    />
                  </div>
                  <span className="text-[10px] text-white/40 self-end pb-2">rés. {row.quantity_reserved}</span>
                  <Button size="sm" onClick={() => save(row)} disabled={savingZone === row.zone_code}
                    data-testid={`stock-save-${row.zone_code}`}
                    className="ml-auto self-end bg-[#D9B35A] hover:bg-[#c9a34a] text-black h-8 px-3 text-xs font-bold">
                    {savingZone === row.zone_code ? '…' : 'Enregistrer'}
                  </Button>
                </div>
              ))}
              <StockHistory productId={product.id} refreshKey={refreshKey} />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};
