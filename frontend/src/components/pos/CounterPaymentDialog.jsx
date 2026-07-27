import { useState } from 'react';
import { toast } from 'sonner';
import { Banknote, CreditCard, Coins, Loader2, Search, User, BadgeCheck, BadgeX } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { lolodriveAPI } from '../../services/api';

const MODES = [
  { id: 'CASH', label: 'Espèces', icon: Banknote, color: '#10b981' },
  { id: 'CARD', label: 'CB', icon: CreditCard, color: '#7c3aed' },
  { id: 'UC', label: 'UC', icon: Coins, color: '#D9B35A' },
  { id: 'MIXED', label: 'Combiné', icon: Coins, color: '#22d3ee' },
];

export const CounterPaymentDialog = ({ total, onClose, onCheckout, selling }) => {
  const [mode, setMode] = useState('CASH');
  const [query, setQuery] = useState('');
  const [client, setClient] = useState(null);
  const [searching, setSearching] = useState(false);
  const [ucAmount, setUcAmount] = useState('');
  const [restMethod, setRestMethod] = useState('CASH');

  const ucTotal = Math.round(total / 10);
  const needsClient = mode === 'UC' || mode === 'MIXED';
  const balance = client?.balance_uc ?? 0;
  const ucPart = mode === 'UC' ? ucTotal : Math.max(0, parseInt(ucAmount, 10) || 0);
  const restCents = Math.max(0, total - Math.min(ucPart, ucTotal) * 10);
  const insufficient = needsClient && client && balance < ucPart;
  const canConfirm = !selling && (!needsClient || (client && !insufficient && ucPart > 0));

  const lookup = async () => {
    const q = query.trim();
    if (q.length < 2) return toast.error('Saisissez un code PASS, un email ou un nom');
    setSearching(true);
    try {
      const r = await lolodriveAPI.posCustomerLookup(q);
      setClient(r);
      if (mode === 'MIXED') setUcAmount(String(Math.max(0, Math.min(Math.floor(r.balance_uc), ucTotal))));
    } catch (e) { setClient(null); toast.error(e.message); } finally { setSearching(false); }
  };

  const confirm = () => {
    const extra = {};
    if (client) extra.customer_user_id = client.user_id;
    if (mode === 'MIXED') { extra.uc_amount = ucPart; extra.rest_method = restMethod; }
    onCheckout(mode, extra);
  };

  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-md" data-testid="counter-payment-dialog">
        <DialogHeader><DialogTitle>Encaissement — {(total / 100).toFixed(2)} €</DialogTitle></DialogHeader>

        {/* Client PASS LOLODRIVE */}
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 space-y-2">
          <p className="text-[11px] uppercase tracking-wider text-white/40 font-bold">
            Client PASS LOLODRIVE {needsClient ? <span className="text-[#D9B35A]">(requis pour payer en UC)</span> : '(optionnel)'}
          </p>
          <div className="flex gap-2">
            <Input placeholder="Code PASS, email ou nom du client…" value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') lookup(); }}
              className="bg-white/5 border-white/10 text-xs" data-testid="customer-lookup-input" />
            <Button size="sm" onClick={lookup} disabled={searching} data-testid="customer-lookup-btn"
              className="bg-white/10 hover:bg-white/20 text-white shrink-0 h-9">
              {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            </Button>
          </div>
          {client && (
            <div className="rounded-lg border border-[#D9B35A]/30 bg-[#D9B35A]/[0.06] p-2.5 text-xs space-y-1" data-testid="customer-card">
              <div className="flex items-center gap-2 flex-wrap">
                <User className="w-3.5 h-3.5 text-[#D9B35A]" />
                <b>{client.name || client.email}</b>
                {client.pass_active ? (
                  <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold text-emerald-300 bg-emerald-400/10 border border-emerald-400/30" data-testid="customer-pass-badge">
                    <BadgeCheck className="w-3 h-3" /> PASS actif {client.pass_id ? `· ${client.pass_id}` : ''}
                  </span>
                ) : (
                  <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold text-amber-300 bg-amber-400/10 border border-amber-400/30" data-testid="customer-pass-badge">
                    <BadgeX className="w-3 h-3" /> {client.pass_id ? 'PASS expiré' : 'Sans PASS'}
                  </span>
                )}
              </div>
              <div className="font-mono" data-testid="customer-balance">
                CREDI'SCOP : <b className={balance > 0 ? 'text-[#D9B35A]' : 'text-red-300'}>{balance} UC</b>
                <span className="text-white/40"> (≈ {(balance / 10).toFixed(2)} €)</span>
              </div>
            </div>
          )}
        </div>

        {/* Mode de paiement */}
        <div className="grid grid-cols-4 gap-2">
          {MODES.map((m) => {
            const Icon = m.icon;
            const active = mode === m.id;
            return (
              <button key={m.id} type="button" data-testid={`pay-mode-${m.id}`}
                onClick={() => { setMode(m.id); if (m.id === 'MIXED' && client) setUcAmount(String(Math.max(0, Math.min(Math.floor(balance), ucTotal)))); }}
                className="flex flex-col items-center gap-1 py-2.5 rounded-xl border text-xs font-bold transition-colors"
                style={active
                  ? { color: m.color, background: `${m.color}1f`, borderColor: `${m.color}66` }
                  : { color: 'rgba(255,255,255,0.5)', background: 'rgba(255,255,255,0.03)', borderColor: 'rgba(255,255,255,0.1)' }}>
                <Icon className="w-4 h-4" /> {m.label}
              </button>
            );
          })}
        </div>

        {/* Détail UC */}
        {mode === 'UC' && (
          <div className="rounded-xl border border-[#D9B35A]/30 bg-[#D9B35A]/[0.05] p-3 text-xs space-y-1" data-testid="uc-summary">
            <p><b className="text-[#D9B35A]">{ucTotal} UC</b> seront débités du CREDI'SCOP du client (mise à jour automatique).</p>
            {!client && <p className="text-amber-300">⚠️ Recherchez d'abord le client (code PASS ou email).</p>}
            {insufficient && <p className="text-red-300" data-testid="uc-insufficient">❌ Solde insuffisant : {balance} UC disponibles, {ucTotal} UC requis.</p>}
          </div>
        )}
        {mode === 'MIXED' && (
          <div className="rounded-xl border border-[#22d3ee]/30 bg-[#22d3ee]/[0.05] p-3 text-xs space-y-2" data-testid="mixed-summary">
            <div className="flex items-center gap-2">
              <span className="shrink-0">Part en UC :</span>
              <Input type="number" min="1" max={ucTotal} value={ucAmount}
                onChange={(e) => setUcAmount(e.target.value)}
                className="bg-white/5 border-white/10 h-8 w-24 font-mono text-xs" data-testid="pay-uc-amount-input" />
              <span className="text-white/40">/ {ucTotal} UC max</span>
            </div>
            <p>Reste à encaisser : <b className="text-[#22d3ee]">{(restCents / 100).toFixed(2)} €</b> en</p>
            <div className="flex gap-2">
              <button type="button" onClick={() => setRestMethod('CASH')} data-testid="pay-rest-cash"
                className={`px-2.5 py-1 rounded-lg border text-[11px] font-bold ${restMethod === 'CASH' ? 'text-emerald-300 bg-emerald-400/15 border-emerald-400/40' : 'text-white/50 bg-white/[0.03] border-white/10'}`}>
                💵 Espèces
              </button>
              <button type="button" onClick={() => setRestMethod('CARD')} data-testid="pay-rest-card"
                className={`px-2.5 py-1 rounded-lg border text-[11px] font-bold ${restMethod === 'CARD' ? 'text-[#c4b5fd] bg-[#7c3aed]/15 border-[#7c3aed]/40' : 'text-white/50 bg-white/[0.03] border-white/10'}`}>
                💳 CB
              </button>
            </div>
            {!client && <p className="text-amber-300">⚠️ Recherchez d'abord le client (code PASS ou email).</p>}
            {insufficient && <p className="text-red-300" data-testid="uc-insufficient">❌ Solde insuffisant : {balance} UC disponibles, {ucPart} UC demandés.</p>}
          </div>
        )}

        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={onClose} className="border-white/15">Annuler</Button>
          <Button onClick={confirm} disabled={!canConfirm} data-testid="pay-confirm-btn"
            className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black font-bold">
            {selling ? <Loader2 className="w-4 h-4 animate-spin" /> : `Encaisser ${(total / 100).toFixed(2)} €`}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
