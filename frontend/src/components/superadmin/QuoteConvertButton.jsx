import { useState } from 'react';
import { UserPlus, Loader2, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

export const QuoteConvertButton = ({ quote, onDone }) => {
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState('buyer');
  const [busy, setBusy] = useState(false);

  if (quote.converted_user_id) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-bold"
        style={{ color: '#7BC94E', background: '#7BC94E1a', border: '1px solid #7BC94E55' }}
        data-testid={`quote-member-badge-${quote.id}`}>
        <CheckCircle2 size={10} /> Compte {quote.converted_role === 'vendor' ? 'vendeur' : 'acheteur'} créé
      </span>
    );
  }

  const convert = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/admin/quotes/${quote.id}/convert-to-member`, {
        method: 'POST', credentials: 'include',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, send_email: true }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Conversion impossible');
      toast.success(`Compte ${role === 'vendor' ? 'Vendeur' : 'Acheteur'} créé pour ${d.email}`, {
        description: d.email_sent
          ? `Identifiants envoyés par email. Mot de passe temporaire : ${d.temp_password}`
          : `⚠️ Email non envoyé — mot de passe temporaire : ${d.temp_password}`,
        duration: 15000,
      });
      setOpen(false);
      onDone?.();
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)} data-testid={`quote-convert-btn-${quote.id}`}
        className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-bold transition-colors"
        style={{ background: 'rgba(123,201,78,0.14)', color: '#A5E27E', border: '1px solid rgba(123,201,78,0.45)' }}>
        <UserPlus size={10} /> Convertir en Membre
      </button>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5" data-testid={`quote-convert-panel-${quote.id}`}>
      <select value={role} onChange={(e) => setRole(e.target.value)} data-testid={`quote-convert-role-${quote.id}`}
        className="px-1.5 py-1 rounded-md text-[10px] font-bold bg-white/[0.08] text-white border border-white/25 cursor-pointer">
        <option value="buyer" style={{ color: '#111' }}>Acheteur Pro</option>
        <option value="vendor" style={{ color: '#111' }}>Vendeur Pro</option>
      </select>
      <button type="button" onClick={convert} disabled={busy} data-testid={`quote-convert-confirm-${quote.id}`}
        className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-bold disabled:opacity-50"
        style={{ background: '#D4AF37', color: '#1F0A33' }}>
        {busy ? <Loader2 size={10} className="animate-spin" /> : <UserPlus size={10} />} Créer le compte
      </button>
      <button type="button" onClick={() => setOpen(false)} disabled={busy}
        className="px-1.5 py-1 rounded-md text-[10px] text-white/50 border border-white/15">✕</button>
    </span>
  );
};
