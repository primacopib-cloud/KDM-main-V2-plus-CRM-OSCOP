import { useEffect, useState } from 'react';
import { Truck, Star, Loader2, X } from 'lucide-react';
import { toast } from 'sonner';
import { rarAPI } from '../../services/api.rar';

// Choix du transporteur au lancement d'une livraison RàR — le mieux noté est proposé d'office
export const RarStartDeliveryDialog = ({ order, onClose, onDone }) => {
  const [carriers, setCarriers] = useState([]);
  const [name, setName] = useState("LOGI'SCOP");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    rarAPI.carrierScores().then((d) => {
      const list = d.carriers || [];
      setCarriers(list);
      if (list.length) setName(list[0].carrier);
    }).catch(() => {});
  }, []);

  const start = async () => {
    setBusy(true);
    try {
      await rarAPI.adminStartDelivery(order.id, (name || '').trim() || "LOGI'SCOP");
      toast.success('OTP envoyé au client');
      onDone();
      onClose();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl bg-[#1c0f33] border border-[#D9B35A]/30 p-5"
        onClick={(e) => e.stopPropagation()} data-testid="rar-start-delivery-dialog">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 m-0">
            <Truck className="w-4 h-4 text-[#D9B35A]" /> Livrer {order.order_number}
          </h3>
          <button type="button" onClick={onClose} className="text-white/50 hover:text-white" data-testid="rar-start-delivery-close">
            <X className="w-4 h-4" />
          </button>
        </div>
        {carriers.length > 0 && (
          <div className="mb-3 space-y-1" data-testid="rar-carrier-suggestions">
            <p className="text-[10px] text-white/45">Transporteurs connus — fiabilité (livraisons sans réserve) :</p>
            {carriers.map((c, i) => (
              <button key={c.carrier} type="button" onClick={() => setName(c.carrier)}
                data-testid={`rar-carrier-pick-${i}`}
                className={`w-full flex items-center justify-between gap-2 p-2 rounded-lg border text-xs transition-colors ${
                  name === c.carrier ? 'border-[#D9B35A] bg-[#D9B35A]/10 text-white' : 'border-white/10 bg-white/[0.03] text-white/70 hover:border-white/25'}`}>
                <span className="flex items-center gap-1.5">
                  {c.carrier}
                  {i === 0 && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded-full text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/30 flex items-center gap-0.5"
                      data-testid="rar-carrier-recommended">
                      <Star className="w-2.5 h-2.5" /> Recommandé
                    </span>
                  )}
                </span>
                <span className={`font-mono font-bold ${c.score >= 80 ? 'text-emerald-300' : c.score >= 50 ? 'text-amber-300' : 'text-red-300'}`}>
                  {c.score.toLocaleString('fr-FR')} % <span className="text-white/35 font-normal">· {c.deliveries} livr.</span>
                </span>
              </button>
            ))}
          </div>
        )}
        <p className="text-[10px] text-white/45 mb-1">Transporteur pour cette livraison :</p>
        <input value={name} onChange={(e) => setName(e.target.value)} data-testid="rar-carrier-name-input"
          className="w-full px-2.5 py-1.5 rounded-lg bg-black/30 border border-white/15 text-xs text-white mb-3" />
        <button type="button" onClick={start} disabled={busy} data-testid="rar-start-delivery-confirm"
          className="w-full px-3 py-2 rounded-lg text-xs font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] disabled:opacity-50 flex items-center justify-center gap-1.5">
          {busy && <Loader2 className="w-3 h-3 animate-spin" />} 🚚 Lancer la livraison (envoyer l'OTP)
        </button>
      </div>
    </div>
  );
};
