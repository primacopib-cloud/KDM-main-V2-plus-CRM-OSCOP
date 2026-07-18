import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Coins, X, ShoppingCart, Loader2, History, Gift } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const fmtDate = (iso) => { try { return new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch (_e) { return iso; } };

/** Modal crédits vendeur : achat de packs Stripe + historique des transactions. */
export const CreditPacksModal = ({ vendorId, onClose }) => {
  const [packs, setPacks] = useState([]);
  const [bonus, setBonus] = useState(0);
  const [data, setData] = useState(null);
  const [buying, setBuying] = useState(null);

  const refresh = useCallback(async () => {
    const [pR, cR] = await Promise.all([
      fetch(`${API_URL}/api/credit-packs`),
      fetch(`${API_URL}/api/vendor/credits/${vendorId}`),
    ]);
    if (pR.ok) { const d = await pR.json(); setPacks(d.packs || []); setBonus(d.bonus_percent || 0); }
    if (cR.ok) setData(await cR.json());
  }, [vendorId]);

  useEffect(() => { refresh(); }, [refresh]);

  const buy = async (pack) => {
    setBuying(pack.id);
    try {
      const r = await fetch(`${API_URL}/api/credit-packs/purchase`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pack_id: pack.id, vendor_id: vendorId, origin_url: window.location.origin }),
      });
      const d = await r.json();
      if (!r.ok) { toast.error(typeof d.detail === 'string' ? d.detail : 'Connexion requise pour acheter'); return; }
      window.location.href = d.url;
    } finally { setBuying(null); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose} data-testid="credit-packs-modal">
      <div className="rounded-[20px] p-6 max-w-lg w-full max-h-[88vh] overflow-y-auto bg-white" onClick={(e) => e.stopPropagation()}
        style={{ boxShadow: '0 24px 64px rgba(76,42,110,0.3)' }}>
        <div className="flex items-start justify-between mb-1">
          <h3 className="font-display text-xl text-[#1F2A3A] flex items-center gap-2">
            <Coins size={18} className="text-amber-500" /> Mes crédits
            <span className="text-base font-bold text-[#B8860B]" data-testid="credit-modal-balance">{data?.credits ?? '…'}</span>
          </h3>
          <button type="button" onClick={onClose} data-testid="credit-packs-close" className="opacity-50 hover:opacity-100 p-1"><X size={18} /></button>
        </div>

        <p className="text-xs opacity-60 mb-4">Rechargez votre solde pour créer des fiches, téléverser des photos et utiliser le Studio IA.</p>
        {bonus > 0 && (
          <p className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg p-2.5 mb-3 flex items-center gap-1.5" data-testid="credit-bonus-banner">
            <Gift size={13} /> Promotion en cours : +{bonus}% de crédits offerts sur tout achat de pack !
          </p>
        )}

        <div className="grid grid-cols-3 gap-2 mb-5">
          {packs.map((p) => (
            <button key={p.id} type="button" onClick={() => buy(p)} disabled={buying === p.id}
              data-testid={`buy-pack-${p.id}`}
              className="rounded-xl border border-gray-200 hover:border-amber-400 p-3 text-center transition-all disabled:opacity-50">
              {buying === p.id ? <Loader2 size={16} className="animate-spin mx-auto mb-1" /> : <ShoppingCart size={16} className="mx-auto mb-1 text-amber-500" />}
              <p className="text-lg font-bold text-[#1F2A3A]">{p.credits}<span className="text-[10px] font-normal opacity-60"> cr.</span></p>
              {bonus > 0 && <p className="text-[10px] text-emerald-600 font-semibold">+{Math.round(p.credits * bonus / 100)} offerts</p>}
              <p className="text-xs opacity-70 mt-0.5">{p.price_eur.toFixed(2)} €</p>
            </button>
          ))}
        </div>

        <h4 className="text-sm font-semibold text-[#1F2A3A] mb-2 flex items-center gap-1.5">
          <History size={13} /> Historique
        </h4>
        <div className="divide-y divide-gray-100 max-h-56 overflow-y-auto" data-testid="credit-history-list">
          {(data?.transactions || []).map((t) => (
            <div key={t.id} className="flex items-center justify-between gap-2 py-2 text-sm">
              <div className="min-w-0">
                <p className="text-[#1F2A3A] truncate text-xs font-medium">{t.detail || t.action}</p>
                <p className="text-[10px] opacity-50">{fmtDate(t.at)}{t.discount_percent ? ` · remise ${t.discount_percent}%` : ''}</p>
              </div>
              <span className={`font-bold text-sm shrink-0 ${t.cost > 0 ? 'text-red-500' : 'text-emerald-600'}`}>
                {t.cost > 0 ? `−${t.cost}` : `+${-t.cost}`}
              </span>
            </div>
          ))}
          {(data?.transactions || []).length === 0 && <p className="text-xs opacity-50 py-3">Aucune transaction.</p>}
        </div>
      </div>
    </div>
  );
};
