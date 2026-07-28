import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { PackagePlus, Loader2, Send, Mail, MailX } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { lolodriveAPI } from '../../services/api';

// Bon de commande fournisseur depuis les suggestions de réassort (gérant)
export const RestockOrderDialog = ({ alerts, onClose }) => {
  const [qtys, setQtys] = useState({});
  const [sending, setSending] = useState(false);

  useEffect(() => {
    setQtys(Object.fromEntries(alerts.map((a) => [a.sku, String(a.suggested_qty || '')])));
  }, [alerts]);

  const groups = {};
  alerts.forEach((a) => { groups[a.supplier || 'Fournisseur non renseigné'] = [...(groups[a.supplier || 'Fournisseur non renseigné'] || []), a]; });

  const send = async () => {
    const items = Object.entries(qtys)
      .map(([sku, v]) => ({ sku, qty: parseInt(v, 10) }))
      .filter((it) => !Number.isNaN(it.qty) && it.qty > 0);
    if (items.length === 0) return toast.error('Aucune quantité à commander');
    setSending(true);
    try {
      const r = await lolodriveAPI.posRestockOrder(items);
      toast.success(`Bon ${r.order_number} envoyé — ${r.suppliers_emailed.length} fournisseur(s) + récap sur ${r.recap_sent_to} ✓`);
      onClose();
    } catch (e) { toast.error(e.message); } finally { setSending(false); }
  };

  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-lg" data-testid="restock-order-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <PackagePlus className="w-4 h-4 text-emerald-400" /> Bon de commande fournisseur
          </DialogTitle>
        </DialogHeader>
        <p className="text-[11px] text-white/40 -mt-1">
          Quantités pré-remplies avec le réassort conseillé (30 j) — ajustez puis envoyez.
          Les fournisseurs avec email le reçoivent directement, vous recevez toujours le récapitulatif.
        </p>
        <div className="max-h-72 overflow-y-auto space-y-3">
          {Object.entries(groups).map(([supplier, ls]) => (
            <div key={supplier} data-testid={`restock-group-${supplier}`}>
              <p className="text-xs font-bold flex items-center gap-1.5 mb-1">
                {ls[0].supplier_email
                  ? <><Mail className="w-3 h-3 text-emerald-400" /> {supplier} <span className="text-[9px] font-normal text-emerald-300">✉ envoi direct : {ls[0].supplier_email}</span></>
                  : <><MailX className="w-3 h-3 text-amber-400" /> {supplier} <span className="text-[9px] font-normal text-amber-300">pas d'email — via votre récap</span></>}
              </p>
              <div className="space-y-1">
                {ls.map((a) => (
                  <div key={a.sku} className="flex items-center gap-3 text-xs p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                    <span className="flex-1 truncate">{a.name}</span>
                    <span className="text-white/35 font-mono shrink-0">stock : {a.stock_qty}</span>
                    <input type="number" min="0" value={qtys[a.sku] ?? ''} data-testid={`restock-qty-${a.sku}`}
                      onChange={(e) => setQtys((q) => ({ ...q, [a.sku]: e.target.value }))}
                      className="w-20 px-2 py-1 rounded bg-white/10 border border-emerald-500/40 text-white text-xs font-mono shrink-0" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <Button onClick={send} disabled={sending} data-testid="restock-order-send-btn"
          className="w-full bg-emerald-500 hover:bg-emerald-600 text-black font-bold">
          {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Send className="w-4 h-4 mr-1.5" /> Envoyer le bon de commande</>}
        </Button>
        {(() => {
          const t = alerts.reduce((s, a) => s + ((a.purchase_price_cents || 0) * (parseInt(qtys[a.sku], 10) || 0)), 0);
          return t > 0 ? (
            <p className="text-xs text-white/60 text-right -mt-1" data-testid="restock-order-total">
              Total achat estimé : <b className="text-emerald-300">{(t / 100).toFixed(2)} €</b>
            </p>
          ) : null;
        })()}
      </DialogContent>
    </Dialog>
  );
};
