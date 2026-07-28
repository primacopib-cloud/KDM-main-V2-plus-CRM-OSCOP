import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Undo2, Loader2, Minus, Plus } from 'lucide-react';
import { QrPassScanner } from './QrPassScanner';

const API = process.env.REACT_APP_BACKEND_URL;
const REASONS = [
  { id: 'DEFECTIVE', label: 'Défectueux' },
  { id: 'ERROR', label: 'Erreur de caisse' },
  { id: 'EXPIRED', label: 'Péremption' },
  { id: 'OTHER', label: 'Autre' },
];

// Retour / remboursement d'articles : scan du QR du ticket ou ouverture depuis une vente du journal
export const CounterRefundDialog = ({ orderId: initialId, onClose, onDone }) => {
  const [order, setOrder] = useState(null);
  const [qty, setQty] = useState({});
  const [reason, setReason] = useState(null);
  const [busy, setBusy] = useState(false);

  const loadOrder = async (id) => {
    try {
      const r = await fetch(`${API}/api/lolodrive/pos/counter-sale/${id}`, { credentials: 'include' });
      const d = await r.json();
      if (!r.ok) { toast.error(d.detail || 'Vente introuvable'); return; }
      setOrder(d.order);
      setQty({});
    } catch { toast.error('Erreur de connexion'); }
  };

  useEffect(() => { if (initialId) loadOrder(initialId); }, [initialId]); // eslint-disable-line

  const onScan = (text) => {
    const m = text.match(/\/ticket\/([\w-]+)/);
    loadOrder(m ? m[1] : text);
  };

  const confirm = async () => {
    const items = Object.entries(qty).filter(([, q]) => q > 0).map(([sku, q]) => ({ sku, qty: q }));
    if (!items.length) { toast.error('Sélectionnez au moins un article'); return; }
    if (!reason) { toast.error('Choisissez le motif du retour'); return; }
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/lolodrive/pos/counter-sale/${order.id}/refund`,
        { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items, reason }) });
      const d = await r.json();
      if (!r.ok) { toast.error(d.detail || 'Retour impossible'); return; }
      toast.success(d.method === 'UC'
        ? `Retour effectué : ${d.uc_refunded} UC recrédités au client ✓`
        : `Retour effectué : ${(d.refunded_cents / 100).toFixed(2)} € à rembourser en espèces ✓`);
      onDone?.();
      onClose();
    } catch { toast.error('Erreur de connexion'); } finally { setBusy(false); }
  };

  const total = order ? Object.entries(qty).reduce((a, [sku, q]) => {
    const l = order.items.find((i) => i.sku === sku);
    return a + (l ? l.unit_cents * q : 0);
  }, 0) : 0;

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-md" data-testid="counter-refund-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Undo2 className="w-4 h-4 text-[#D9B35A]" /> Retour d'articles</DialogTitle></DialogHeader>
        {!order ? (
          <div className="space-y-3 text-sm">
            <p className="text-white/60 text-xs">Scannez le QR code du ticket du client, ou collez le lien / l'identifiant de la vente.</p>
            <div className="flex items-center gap-2">
              <QrPassScanner onScan={onScan} />
              <input placeholder="Lien du ticket ou ID de vente" data-testid="refund-order-input"
                onKeyDown={(e) => { if (e.key === 'Enter' && e.target.value.trim()) onScan(e.target.value.trim()); }}
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2.5 py-2 text-xs text-white" />
            </div>
          </div>
        ) : (
          <div className="space-y-2 text-xs">
            <p className="font-mono text-white/50">{order.order_number} · payé en {order.payment_method === 'UC' ? 'UC' : order.payment_method === 'CARD' ? 'CB' : 'espèces'}</p>
            {order.items.map((l) => {
              const available = l.qty - (l.returned_qty || 0);
              const q = qty[l.sku] || 0;
              return (
                <div key={l.sku} data-testid={`refund-line-${l.sku}`}
                  className="flex items-center gap-2 rounded-lg bg-white/[0.03] border border-white/[0.06] px-2.5 py-1.5">
                  <span className="min-w-0 flex-1">
                    <span className="block truncate">{l.name}</span>
                    <span className="text-white/40 text-[10px]">{(l.unit_cents / 100).toFixed(2)} € /u · acheté ×{l.qty}{l.returned_qty ? ` · déjà retourné ×${l.returned_qty}` : ''}</span>
                  </span>
                  {available > 0 ? (
                    <span className="flex items-center gap-1.5 shrink-0">
                      <button type="button" onClick={() => setQty({ ...qty, [l.sku]: Math.max(0, q - 1) })} disabled={!q}
                        data-testid={`refund-sub-${l.sku}`}
                        className="w-6 h-6 rounded flex items-center justify-center bg-white/[0.06] border border-white/15 disabled:opacity-30"><Minus className="w-3 h-3" /></button>
                      <span className="w-5 text-center font-mono">{q}</span>
                      <button type="button" onClick={() => setQty({ ...qty, [l.sku]: Math.min(available, q + 1) })}
                        data-testid={`refund-add-${l.sku}`}
                        className="w-6 h-6 rounded flex items-center justify-center bg-[#D9B35A]/15 border border-[#D9B35A]/40 text-[#D9B35A]"><Plus className="w-3 h-3" /></button>
                    </span>
                  ) : <span className="text-white/30 shrink-0">Tout retourné</span>}
                </div>
              );
            })}
            <div className="flex items-center justify-between border-t border-dashed border-white/15 pt-2">
              <span className="font-bold">À rembourser</span>
              <span className="font-mono font-bold" data-testid="refund-total">
                {(total / 100).toFixed(2)} € {order.payment_method === 'UC' && <span className="text-[#D9B35A]">· {+(total / 10).toFixed(1)} UC</span>}
              </span>
            </div>
            <div>
              <p className="text-white/50 text-[10px] mb-1">Motif du retour :</p>
              <div className="flex flex-wrap gap-1.5">
                {REASONS.map((r) => (
                  <button key={r.id} type="button" onClick={() => setReason(r.id)}
                    data-testid={`refund-reason-${r.id}`}
                    className={`px-2 py-1 rounded-lg text-[11px] font-bold border ${
                      reason === r.id
                        ? 'bg-[#D9B35A] text-black border-[#D9B35A]'
                        : 'bg-white/[0.04] text-white/60 border-white/15 hover:border-[#D9B35A]/50'}`}>
                    {r.label}
                  </button>
                ))}
              </div>
            </div>
            <button type="button" onClick={confirm} disabled={busy || total === 0 || !reason} data-testid="refund-confirm-btn"
              className="w-full py-2 rounded-lg text-sm font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] disabled:opacity-40 flex items-center justify-center gap-2">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Undo2 className="w-4 h-4" />}
              Valider le retour {order.payment_method === 'UC' ? '(recrédit UC)' : '(remboursement espèces)'}
            </button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
