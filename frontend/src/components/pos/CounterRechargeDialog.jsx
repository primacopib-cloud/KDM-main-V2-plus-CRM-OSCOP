import { useState } from 'react';
import { toast } from 'sonner';
import { Coins, Loader2, Search, User, Banknote, CreditCard } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { lolodriveAPI } from '../../services/api';
import { QrPassScanner } from './QrPassScanner';

// Recharge du CREDI'SCOP client au comptoir (espèces / CB), avec reçu email automatique
export const CounterRechargeDialog = ({ onClose }) => {
  const [query, setQuery] = useState('');
  const [client, setClient] = useState(null);
  const [searching, setSearching] = useState(false);
  const [amount, setAmount] = useState('50');
  const [method, setMethod] = useState('CASH');
  const [saving, setSaving] = useState(false);

  const lookup = async (q = query) => {
    if ((q || '').trim().length < 2) return toast.error('Saisissez un code PASS, un email ou un nom');
    setSearching(true);
    try { setClient(await lolodriveAPI.posCustomerLookup(q.trim())); }
    catch (e) { setClient(null); toast.error(e.message); } finally { setSearching(false); }
  };

  const uc = Math.max(0, parseInt(amount, 10) || 0);
  const confirm = async () => {
    if (!client) return toast.error('Recherchez d’abord le client');
    if (uc < 1) return toast.error('Montant UC invalide');
    setSaving(true);
    try {
      const r = await lolodriveAPI.posCounterRecharge({
        customer_user_id: client.user_id, amount_uc: uc, payment_method: method });
      toast.success(`Recharge ${r.ref} : +${r.amount_uc} UC pour ${r.customer_name} — nouveau solde ${r.client_balance_uc} UC ✓ (reçu email envoyé)`);
      onClose();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-md" data-testid="counter-recharge-dialog">
        <DialogHeader><DialogTitle>🪙 Recharge CREDI'SCOP au comptoir</DialogTitle></DialogHeader>
        <div className="flex gap-2">
          <Input placeholder="Code PASS, email ou nom du client…" value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') lookup(); }}
            className="bg-white/5 border-white/10 text-xs" data-testid="recharge-lookup-input" />
          <QrPassScanner onScan={(code) => { setQuery(code); lookup(code); }} />
          <Button size="sm" onClick={() => lookup()} disabled={searching} data-testid="recharge-lookup-btn"
            className="bg-white/10 hover:bg-white/20 text-white shrink-0 h-9">
            {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          </Button>
        </div>
        {client && (
          <div className="rounded-lg border border-[#D9B35A]/30 bg-[#D9B35A]/[0.06] p-2.5 text-xs" data-testid="recharge-client-card">
            <span className="flex items-center gap-2"><User className="w-3.5 h-3.5 text-[#D9B35A]" /><b>{client.name || client.email}</b></span>
            <span className="font-mono block mt-1">Solde actuel : <b className="text-[#D9B35A]">{client.balance_uc} UC</b></span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <span className="text-xs text-white/60 shrink-0">Montant :</span>
          <Input type="number" min="1" value={amount} onChange={(e) => setAmount(e.target.value)}
            className="bg-white/5 border-white/10 h-9 w-28 font-mono" data-testid="recharge-amount-input" />
          <span className="text-xs text-white/40">UC (≈ {(uc / 10).toFixed(2)} € encaissés)</span>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => setMethod('CASH')} data-testid="recharge-method-cash"
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl border text-xs font-bold ${method === 'CASH' ? 'text-emerald-300 bg-emerald-400/15 border-emerald-400/40' : 'text-white/50 bg-white/[0.03] border-white/10'}`}>
            <Banknote className="w-4 h-4" /> Espèces
          </button>
          <button type="button" onClick={() => setMethod('CARD')} data-testid="recharge-method-card"
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl border text-xs font-bold ${method === 'CARD' ? 'text-[#c4b5fd] bg-[#7c3aed]/15 border-[#7c3aed]/40' : 'text-white/50 bg-white/[0.03] border-white/10'}`}>
            <CreditCard className="w-4 h-4" /> CB
          </button>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={onClose} className="border-white/15">Annuler</Button>
          <Button onClick={confirm} disabled={saving || !client || uc < 1} data-testid="recharge-confirm-btn"
            className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black font-bold">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Coins className="w-4 h-4 mr-1" /> Recharger +{uc} UC</>}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
