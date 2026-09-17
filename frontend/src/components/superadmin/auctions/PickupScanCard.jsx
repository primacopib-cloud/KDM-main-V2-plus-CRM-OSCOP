import { useState } from 'react';
import { QrCode, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../../services/http';

// Superadmin : vérifier le QR d'enlèvement d'un lot remporté et confirmer la remise
export const PickupScanCard = () => {
  const [code, setCode] = useState('');
  const [res, setRes] = useState(null);

  const scan = async (confirm) => {
    try {
      const r = await fetch(`${API}/admin/auctions/pickup-scan`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ code: code.trim(), confirm }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      setRes(d);
      if (d.confirmed) toast.success('Remise du lot confirmée ✓');
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 mb-4" data-testid="pickup-scan-card">
      <p className="text-[11px] font-bold text-white/60 uppercase mb-2 flex items-center gap-1">
        <QrCode className="w-3.5 h-3.5 text-[#D9B35A]" /> Vérification QR d'enlèvement (lots remportés)
      </p>
      <div className="flex gap-2 flex-wrap">
        <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="coopact:… ou token scanné"
          data-testid="pickup-scan-input"
          className="h-8 flex-1 min-w-[220px] px-2 rounded-lg bg-white/[0.05] border border-white/15 text-white text-xs" />
        <button onClick={() => scan(false)} disabled={!code.trim()} data-testid="pickup-scan-verify"
          className="px-3 h-8 rounded-full text-[11px] font-bold text-[#E9CF8E] border border-[#D9B35A]/40 hover:bg-[#D9B35A]/15 disabled:opacity-40">
          Vérifier
        </button>
      </div>
      {res && (
        <div className="mt-2 text-[11px] text-white/70 rounded-lg border border-white/10 p-2" data-testid="pickup-scan-result">
          <p><span className="font-bold text-[#E9CF8E]">{res.title}</span> · {res.reference} · {Number(res.price_eur).toFixed(2)} €</p>
          <p>Gagnant : <span className="font-semibold">{res.winner_name}</span> — {res.winner_email}{res.winner_phone ? ` — ${res.winner_phone}` : ''}</p>
          {res.already_picked_up || res.confirmed ? (
            <p className="text-emerald-300 font-bold mt-1">✓ Lot récupéré le {new Date(res.pickup_confirmed_at).toLocaleString('fr-FR')}</p>
          ) : (
            <button onClick={() => scan(true)} data-testid="pickup-scan-confirm"
              className="mt-1.5 inline-flex items-center gap-1 px-3 h-7 rounded-full text-[11px] font-bold text-emerald-300 border border-emerald-400/40 bg-emerald-500/10 hover:bg-emerald-500/20">
              <CheckCircle2 className="w-3.5 h-3.5" /> Confirmer la remise du lot
            </button>
          )}
        </div>
      )}
    </div>
  );
};
