import { useState } from 'react';
import { TicketPercent } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const fmtPrice = (cents) => `${(cents / 100).toFixed(2).replace('.', ',')} €`;

// Saisie du bon de retour (relance panier abandonné)
export const ReturnCodeBox = ({ cart, zone }) => {
  const [code, setCode] = useState('');
  const [applied, setApplied] = useState(cart?.return_code ? { code: cart.return_code, discount: cart.return_discount_cents } : null);
  const [busy, setBusy] = useState(false);

  const apply = async () => {
    if (!code.trim()) return;
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/v2/catalog/cart/apply-return-code${zone ? `?zone_code=${zone}` : ''}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ code: code.trim() }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Code invalide');
      setApplied({ code: d.return_code, discount: d.return_discount_cents });
      toast.success(`Bon de retour appliqué : −${fmtPrice(d.return_discount_cents)} HT sur votre commande`);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (applied) {
    return (
      <p className="mb-2 text-[11px] text-[#8CC63E] flex items-center gap-1.5" data-testid="return-code-applied">
        <TicketPercent className="w-3.5 h-3.5" />
        Bon <strong className="font-mono">{applied.code}</strong> appliqué : <strong>−{fmtPrice(applied.discount)} HT</strong> à la commande
      </p>
    );
  }

  return (
    <div className="mb-2 flex items-center gap-1.5" data-testid="return-code-box">
      <TicketPercent className="w-3.5 h-3.5 text-[#D9B35A] shrink-0" />
      <input
        value={code}
        onChange={(e) => setCode(e.target.value.toUpperCase())}
        placeholder="Bon de retour (ex: RETOUR-A1B2C3)"
        data-testid="return-code-input"
        className="h-7 w-52 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-[11px] placeholder:text-white/30 font-mono"
      />
      <button type="button" onClick={apply} disabled={busy || !code.trim()} data-testid="return-code-apply"
        className="h-7 px-2.5 rounded-md text-[10px] font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] transition-colors disabled:opacity-40">
        {busy ? '…' : 'Appliquer'}
      </button>
    </div>
  );
};
