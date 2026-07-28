import { useState } from 'react';
import { toast } from 'sonner';
import { Printer, Mail, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { lolodriveAPI } from '../../services/api';

export const CounterTicketDialog = ({ sale, onClose }) => {
  const [email, setEmail] = useState('');
  const [sending, setSending] = useState(false);
  if (!sale) return null;
  const discount = sale.promo_discount_cents || 0;
  const payLabel = sale.payment_method === 'CARD' ? 'CB'
    : sale.payment_method === 'UC' ? "UC — CREDI'SCOP"
      : sale.payment_method === 'MIXED' ? `UC + ${sale.rest_method === 'CARD' ? 'CB' : 'espèces'}`
        : 'espèces';

  // Standard européen : lignes HT, cumul TVA par taux, puis montant TTC
  const euLines = (sale.items || []).map((l) => {
    const ttc = l.unit_cents * l.qty;
    const rate = l.tva_rate ?? 8.5;
    const ht = Math.round(ttc / (1 + rate / 100));
    return { ...l, ttc, ht, rate, tva: ttc - ht };
  });
  const totalHt = euLines.reduce((a, l) => a + l.ht, 0);
  const tvaByRate = Object.entries(euLines.reduce((m, l) => {
    m[l.rate] = (m[l.rate] || 0) + l.tva;
    return m;
  }, {})).sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]));

  const printTicket = () => {
    const rows = euLines.map((l) =>
      `<tr><td>${l.qty} × ${l.name}${l.promo_percent ? ` (-${l.promo_percent}%)` : ''} · TVA ${l.rate}%</td><td style="text-align:right">${(l.ht / 100).toFixed(2)} € HT</td></tr>`).join('');
    const tvaRows = tvaByRate.map(([rate, tva]) =>
      `<tr><td>TVA ${parseFloat(rate).toFixed(2).replace('.', ',')} %</td><td style="text-align:right">${(tva / 100).toFixed(2)} €</td></tr>`).join('');
    const w = window.open('', '_blank', 'width=380,height=620');
    w.document.write(`<html><head><title>Ticket ${sale.order_number}</title>
      <style>body{font-family:monospace;font-size:12px;padding:12px}table{width:100%;border-collapse:collapse}td{padding:2px 4px}.t{border-top:1px dashed #000;margin-top:8px;padding-top:8px}</style></head><body>
      <div style="text-align:center"><b>${sale.point_name || 'Relais LOLODRIVE'}</b><br/>Vente au comptoir<br/>${sale.order_number}</div>
      <div class="t"><table>${rows}</table></div>
      <div class="t"><table>
      <tr><td><b>Sous-total HT</b></td><td style="text-align:right"><b>${(totalHt / 100).toFixed(2)} €</b></td></tr>
      ${tvaRows}
      ${discount ? `<tr><td>Remise promo (deja deduite des lignes)</td><td style="text-align:right">-${(discount / 100).toFixed(2)} €</td></tr>` : ''}
      </table></div>
      <div class="t"><b>MONTANT TTC : ${(sale.total_cents / 100).toFixed(2)} €</b> (${payLabel})
      ${sale.uc_paid ? `<br/>Payé en UC : ${sale.uc_paid} UC (CREDI'SCOP mis à jour)` : ''}</div>
      ${sale.operator_name ? `<div style="margin-top:4px">Encaissé par : ${sale.operator_name}</div>` : ''}
      <div class="t" style="text-align:center">Merci de votre visite !<br/>LOLODRIVE by O'SCOP</div>
      </body></html>`);
    w.document.close();
    w.focus();
    w.print();
  };

  const sendEmail = async () => {
    if (!email.includes('@')) return toast.error('Email invalide');
    setSending(true);
    try {
      await lolodriveAPI.posEmailTicket(sale.id, email);
      toast.success(`Ticket envoyé à ${email} ✓`);
      onClose();
    } catch (e) { toast.error(e.message); } finally { setSending(false); }
  };

  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-sm" data-testid="counter-ticket-dialog">
        <DialogHeader><DialogTitle>🧾 Ticket — {sale.order_number}</DialogTitle></DialogHeader>
        <div className="font-mono text-xs bg-black/30 rounded-xl p-3 border border-white/10 space-y-1" data-testid="ticket-lines">
          {euLines.map((l) => (
            <div key={l.sku} className="flex justify-between">
              <span className="truncate">{l.qty} × {l.name}{l.promo_percent ? ` (-${l.promo_percent}%)` : ''} · TVA {l.rate}%</span>
              <span className="shrink-0 ml-2">{(l.ht / 100).toFixed(2)} € HT</span>
            </div>
          ))}
          <div className="flex justify-between font-bold border-t border-dashed border-white/20 pt-1 mt-1">
            <span>Sous-total HT</span>
            <span data-testid="ticket-total-ht">{(totalHt / 100).toFixed(2)} €</span>
          </div>
          <div data-testid="ticket-tva">
            {tvaByRate.map(([rate, tva]) => (
              <div key={rate} className="flex justify-between text-white/55" data-testid={`ticket-tva-${rate}`}>
                <span>TVA {parseFloat(rate).toFixed(2).replace('.', ',')} %</span>
                <span>{(tva / 100).toFixed(2)} €</span>
              </div>
            ))}
          </div>
          {discount > 0 && <div className="flex justify-between text-[#FF9E7A]"><span>⚡ Remise promo (déjà déduite des lignes)</span><span>−{(discount / 100).toFixed(2)} €</span></div>}
          <div className="flex justify-between font-bold border-t border-dashed border-white/20 pt-1 mt-1">
            <span>MONTANT TTC ({payLabel})</span>
            <span data-testid="ticket-total">{(sale.total_cents / 100).toFixed(2)} €</span>
          </div>
          {sale.uc_paid > 0 && (
            <div className="flex justify-between text-[#D9B35A]" data-testid="ticket-uc-paid">
              <span>🪙 Payé en UC{sale.customer_name ? ` (${sale.customer_name})` : ''}</span>
              <span>{sale.uc_paid} UC</span>
            </div>
          )}
          {sale.operator_name && (
            <div className="text-white/45 pt-1" data-testid="ticket-operator">Encaissé par : {sale.operator_name}</div>
          )}
        </div>
        <Button onClick={printTicket} variant="outline" className="w-full border-white/15" data-testid="print-ticket-btn">
          <Printer className="w-4 h-4 mr-2" /> Imprimer le ticket
        </Button>
        <div className="flex gap-2">
          <Input placeholder="email@client.fr" value={email} onChange={(e) => setEmail(e.target.value)}
            className="bg-white/5 border-white/10" data-testid="ticket-email-input" />
          <Button onClick={sendEmail} disabled={sending} className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black shrink-0" data-testid="ticket-email-btn">
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Mail className="w-4 h-4 mr-1" /> Envoyer</>}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
