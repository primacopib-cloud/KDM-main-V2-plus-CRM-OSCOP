import { useState } from 'react';
import { toast } from 'sonner';
import { Loader2, MessageSquare } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../ui/dialog';
import { API, getAuthHeaders } from '../../services/http';

export const DIAL_CODES = [
  ['🇬🇵 Guadeloupe', '+590'], ['🇲🇶 Martinique', '+596'], ['🇬🇫 Guyane', '+594'],
  ['🇷🇪 La Réunion', '+262'], ['🇾🇹 Mayotte', '+262'], ['🇫🇷 France', '+33'],
  ['🇭🇹 Haïti', '+509'], ['🇩🇲 Dominique', '+1767'], ['🇱🇨 Sainte-Lucie', '+1758'],
  ['🇨🇦 Canada', '+1'], ['🇺🇸 États-Unis', '+1'], ['🇧🇪 Belgique', '+32'],
  ['🇨🇭 Suisse', '+41'], ['🇬🇧 Royaume-Uni', '+44'], ['🇩🇪 Allemagne', '+49'],
  ['🇪🇸 Espagne', '+34'], ['🇮🇹 Italie', '+39'], ['🇵🇹 Portugal', '+351'],
  ['🇲🇦 Maroc', '+212'], ['🇸🇳 Sénégal', '+221'], ['🇨🇮 Côte d\'Ivoire', '+225'],
];

const eur = (c) => (c / 100).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });

export const PaymentLinkSmsDialog = ({ link, onClose, onSent }) => {
  const [dial, setDial] = useState('+590');
  const [number, setNumber] = useState('');
  const [sending, setSending] = useState(false);

  if (!link) return null;
  const localDigits = number.replace(/\D/g, '').replace(/^0+/, '');
  const fullPhone = `${dial}${localDigits}`;

  const send = async () => {
    if (localDigits.length < 6) { toast.error('Numéro de mobile invalide'); return; }
    setSending(true);
    try {
      const r = await fetch(`${API}/admin/payment-links/${link.id}/send-sms`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ phone: fullPhone }),
      });
      const d = await r.json();
      if (!r.ok) { toast.error(typeof d.detail === 'string' ? d.detail : 'Envoi échoué'); return; }
      toast.success(`SMS envoyé au ${fullPhone}`);
      onSent();
      onClose();
    } finally { setSending(false); }
  };

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-sm bg-[#2A1045] border-white/15 text-white" data-testid="paylink-sms-dialog">
        <DialogHeader>
          <DialogTitle className="text-base flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-[#8CC63E]" /> Envoyer par SMS — {eur(link.amount_cents)}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label className="text-white/70 text-xs">Indicatif international</Label>
            <select value={dial} onChange={(e) => setDial(e.target.value)} data-testid="sms-dial-select"
              className="mt-1 w-full h-9 rounded-md bg-white/[0.04] border border-white/10 text-white text-sm px-2">
              {DIAL_CODES.map(([label, code], i) => (
                <option key={`${code}-${i}`} value={code} className="bg-[#2A1045]">{label} ({code})</option>
              ))}
            </select>
          </div>
          <div>
            <Label className="text-white/70 text-xs">Numéro de mobile (sans le 0 initial)</Label>
            <Input value={number} onChange={(e) => setNumber(e.target.value)} placeholder="690 12 34 56"
              data-testid="sms-number-input" className="mt-1 bg-white/[0.04] border-white/10 text-white text-sm h-9" />
            {localDigits.length >= 6 && (
              <p className="text-[10.5px] text-[#8CC63E] m-0 mt-0.5" data-testid="sms-phone-preview">
                SMS vers : {fullPhone}
              </p>
            )}
          </div>
          <p className="text-[10.5px] text-white/40 m-0">
            Message : « KDMARCHE x O&apos;SCOP - Lien de paiement … Payez en securite ici : buy.stripe.com/… »
          </p>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} className="text-white/60">Annuler</Button>
          <Button onClick={send} disabled={sending || localDigits.length < 6} data-testid="sms-send-btn"
            className="bg-[#8CC63E] text-black hover:bg-[#7ab332] font-semibold">
            {sending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />} Envoyer le SMS
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
