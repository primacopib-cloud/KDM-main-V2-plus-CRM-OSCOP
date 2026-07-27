import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Package, User, Clock, Phone, Mail, Loader2, MapPin, Printer } from 'lucide-react';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { fmtEUR } from '../LolodriveLayout';
import { lolodriveAPI } from '../../services/api';

// Fenêtre de préparation : détail complet de la commande (articles, client, créneau)
export const PrepareOrderDialog = ({ orderId, onClose, onStart, acting }) => {
  const [data, setData] = useState(null);
  useEffect(() => {
    lolodriveAPI.posOrderDetail(orderId).then(setData).catch((e) => { toast.error(e.message); onClose(); });
    // eslint-disable-next-line
  }, [orderId]);

  const o = data?.order;

  const printSlip = () => {
    const dateFr = o.pickup_date ? new Date(o.pickup_date).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' }) : '';
    const w = window.open('', '_blank', 'width=420,height=640');
    w.document.write(`<html><head><title>Bon de préparation ${o.order_number}</title>
      <style>body{font-family:monospace;font-size:13px;padding:14px;color:#111}
      h2{font-size:15px;margin:0 0 4px}.m{color:#555;font-size:11px;margin:2px 0}
      .line{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px dashed #ccc}
      .qty{font-size:16px;font-weight:bold;margin-right:8px}.t{margin-top:10px;font-weight:bold}</style></head><body>
      <h2>BON DE PRÉPARATION</h2>
      <div class="m">Commande ${o.order_number} · ${data.point || ''}</div>
      <div class="m">Client : ${data.customer?.name || 'Client'}${data.customer?.phone ? ` · ${data.customer.phone}` : ''}</div>
      <div class="m">🕐 Retrait : ${dateFr ? `${dateFr} — ` : ''}${o.pickup_slot_label || 'créneau non précisé'} (${o.fulfillment_type})</div>
      <hr/>
      ${(o.items || []).map((it) => `<div class="line"><span><span class="qty">${it.qty}×</span>${it.name}</span></div>`).join('')}
      <div class="t">${o.items?.length || 0} article(s) — Total : ${((o.total_cents || 0) / 100).toFixed(2)} €${o.pay_with_uc ? ` · ${o.total_uc} UC (payé UC)` : ''}</div>
      ${o.slot_fee_uc > 0 ? `<div class="m">dont frais de créneau : ${o.slot_fee_uc} UC</div>` : ''}
      </body></html>`);
    w.document.close();
    w.print();
  };

  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-lg" data-testid="prepare-order-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="w-4 h-4 text-[#D9B35A]" /> Préparation — {o?.order_number || '…'}
          </DialogTitle>
        </DialogHeader>
        {!data && <div className="py-8 text-center"><Loader2 className="w-5 h-5 animate-spin mx-auto text-[#D9B35A]" /></div>}
        {o && (
          <div className="space-y-3">
            <div className="grid sm:grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg bg-white/[0.03] border border-white/[0.06] p-2.5 space-y-1" data-testid="prepare-customer">
                <p className="text-[10px] uppercase tracking-wider text-white/40 font-bold flex items-center gap-1"><User className="w-3 h-3" /> Client</p>
                <p className="font-semibold">{data.customer?.name || 'Client'}</p>
                {data.customer?.phone && <p className="text-white/60 flex items-center gap-1"><Phone className="w-3 h-3" /> {data.customer.phone}</p>}
                {data.customer?.email && <p className="text-white/60 flex items-center gap-1 truncate"><Mail className="w-3 h-3" /> {data.customer.email}</p>}
              </div>
              <div className="rounded-lg bg-white/[0.03] border border-white/[0.06] p-2.5 space-y-1" data-testid="prepare-slot">
                <p className="text-[10px] uppercase tracking-wider text-white/40 font-bold flex items-center gap-1"><Clock className="w-3 h-3" /> Retrait</p>
                <p className="font-semibold">{o.pickup_date ? `${new Date(o.pickup_date).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })} — ` : ''}{o.pickup_slot_label || 'Créneau non précisé'}</p>
                {o.no_pickup_penalty_uc > 0 && (
                  <p className="text-red-300 font-bold" data-testid="prepare-penalty">
                    ⚠️ Pénalité non-retrait : {o.no_pickup_penalty_uc} UC ({(o.no_pickup_penalty_uc / 10).toFixed(2)} €)
                  </p>
                )}
                <p className="text-white/60">{o.fulfillment_type}{data.point ? <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {data.point}</span> : ''}</p>
              </div>
            </div>
            <div className="rounded-xl border border-[#D9B35A]/25 bg-[#D9B35A]/[0.04] p-3" data-testid="prepare-items">
              <p className="text-[10px] uppercase tracking-wider text-[#D9B35A] font-bold mb-2">
                {o.items?.length || 0} article(s) à préparer
              </p>
              <div className="max-h-64 overflow-y-auto space-y-1.5">
                {(o.items || []).map((it, i) => (
                  <div key={`${it.sku}-${i}`} className="flex items-center justify-between text-sm p-2 rounded-lg bg-black/20">
                    <span className="flex items-center gap-2 min-w-0">
                      <span className="w-8 h-8 rounded-lg bg-[#D9B35A]/15 border border-[#D9B35A]/40 flex items-center justify-center font-black text-[#D9B35A] shrink-0">
                        {it.qty}
                      </span>
                      <span className="truncate">{it.name}</span>
                    </span>
                    <span className="text-xs text-white/40 shrink-0 ml-2 font-mono">{fmtEUR((it.unit_cents || 0) * it.qty)}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="text-white/60">
                Total : <b className="text-white">{fmtEUR(o.total_cents)}</b>
                {o.pay_with_uc && <span className="text-[#D9B35A]"> · {o.total_uc} UC</span>}
                {o.slot_fee_uc > 0 && <span className="text-white/40 text-xs"> (dont frais créneau {o.slot_fee_uc} UC)</span>}
              </span>
              <span className="flex gap-2">
                <Button variant="outline" size="sm" onClick={onClose} className="border-white/15">Fermer</Button>
                <Button variant="outline" size="sm" onClick={printSlip} data-testid="prepare-print-btn"
                  className="border-[#D9B35A]/40 text-[#D9B35A] hover:bg-[#D9B35A]/10">
                  <Printer className="w-3 h-3 mr-1" /> Imprimer le bon
                </Button>
                {o.status === 'PAID' && (
                  <Button size="sm" disabled={acting} onClick={() => { printSlip(); onStart(o.id); }} data-testid="prepare-start-btn"
                    className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black font-bold">
                    <Package className="w-3 h-3 mr-1" /> Commencer la préparation
                  </Button>
                )}
              </span>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
