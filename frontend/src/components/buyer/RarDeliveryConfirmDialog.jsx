import { useRef, useState, useEffect } from 'react';
import { Loader2, PenLine, Camera, X } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { rarAPI } from '../../services/api.rar';

// Preuve électronique de livraison LOGI'SCOP : OTP + signature + quantités + photos + réserves partielles
export const RarDeliveryConfirmDialog = ({ order, onClose, onDone }) => {
  const canvasRef = useRef(null);
  const [drawing, setDrawing] = useState(false);
  const [hasSigned, setHasSigned] = useState(false);
  const [otp, setOtp] = useState('');
  const [receiver, setReceiver] = useState('');
  const [busy, setBusy] = useState(false);
  const [photos, setPhotos] = useState([]);
  const [geo, setGeo] = useState(null);
  const [lines, setLines] = useState(
    (order.items || []).map((i) => ({ ...i, qty_received: i.quantity, reserve: false, reserve_qty: 0, reason: '' })));

  useEffect(() => {
    navigator.geolocation?.getCurrentPosition(
      (p) => setGeo({ lat: p.coords.latitude, lng: p.coords.longitude }), () => {});
  }, []);

  const pos = (e) => {
    const r = canvasRef.current.getBoundingClientRect();
    const t = e.touches?.[0] || e;
    return { x: t.clientX - r.left, y: t.clientY - r.top };
  };
  const start = (e) => { setDrawing(true); const c = canvasRef.current.getContext('2d'); const p = pos(e); c.beginPath(); c.moveTo(p.x, p.y); };
  const move = (e) => {
    if (!drawing) return;
    const c = canvasRef.current.getContext('2d');
    c.strokeStyle = '#1a1a2e'; c.lineWidth = 2; c.lineCap = 'round';
    const p = pos(e); c.lineTo(p.x, p.y); c.stroke(); setHasSigned(true);
  };
  const clearSig = () => { const c = canvasRef.current; c.getContext('2d').clearRect(0, 0, c.width, c.height); setHasSigned(false); };

  const addPhoto = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const rd = new FileReader();
    rd.onload = () => setPhotos((p) => [...p, rd.result].slice(0, 3));
    rd.readAsDataURL(f);
  };

  const submit = async () => {
    if (otp.length !== 6) return toast.error('Code OTP à 6 chiffres requis');
    if (!receiver.trim()) return toast.error('Identité du réceptionnaire requise');
    if (!hasSigned) return toast.error('Signature électronique requise');
    setBusy(true);
    try {
      const r = await rarAPI.confirmDelivery(order.id, {
        otp, receiver_name: receiver,
        signature: canvasRef.current.toDataURL('image/png'),
        photos, geolocation: geo,
        quantities: lines.map((l) => ({ product_id: l.product_id, qty_received: l.qty_received })),
        reserves: lines.filter((l) => l.reserve && l.reserve_qty > 0)
          .map((l) => ({ product_id: l.product_id, qty: l.reserve_qty, reason: l.reason })),
      });
      toast.success(`Réception confirmée — facture ${r.invoice_number || ''} · ${(r.payable_now_cents / 100).toFixed(2)} € exigibles${r.disputed_cents ? ` (${(r.disputed_cents / 100).toFixed(2)} € suspendus sous réserves)` : ''}`);
      onDone?.(); onClose();
    } catch (e) { toast.error(e.message || 'Erreur'); } finally { setBusy(false); }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto bg-[#2A1045] border-white/15 text-white" data-testid="rar-delivery-dialog">
        <DialogHeader>
          <DialogTitle className="text-base">Confirmer la réception — {order.order_number}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-white/60">Code OTP reçu par email</label>
              <input value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="w-full px-2 py-1.5 rounded bg-black/30 border border-white/15 text-white tracking-[6px] font-mono text-center"
                placeholder="••••••" data-testid="rar-otp-input" />
            </div>
            <div>
              <label className="text-xs text-white/60">Réceptionnaire (nom, prénom)</label>
              <input value={receiver} onChange={(e) => setReceiver(e.target.value)}
                className="w-full px-2 py-1.5 rounded bg-black/30 border border-white/15 text-white"
                data-testid="rar-receiver-input" />
            </div>
          </div>

          <div>
            <p className="text-xs text-white/60 mb-1">Quantités reçues & réserves (seule la valeur contestée est suspendue)</p>
            <div className="space-y-1.5">
              {lines.map((l, idx) => (
                <div key={l.product_id} className="p-2 rounded-lg bg-white/[0.04] border border-white/10" data-testid={`rar-line-${idx}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs truncate">{l.product_name}</span>
                    <span className="flex items-center gap-1 text-xs shrink-0">
                      <input type="number" min="0" max={l.quantity} value={l.qty_received}
                        onChange={(e) => setLines(lines.map((x, i) => i === idx ? { ...x, qty_received: parseInt(e.target.value || 0, 10) } : x))}
                        className="w-14 px-1 py-0.5 rounded bg-black/30 border border-white/15 text-center" />
                      / {l.quantity}
                    </span>
                  </div>
                  <label className="flex items-center gap-1.5 mt-1 text-[11px] text-amber-300 cursor-pointer">
                    <input type="checkbox" checked={l.reserve} data-testid={`rar-reserve-toggle-${idx}`}
                      onChange={(e) => setLines(lines.map((x, i) => i === idx ? { ...x, reserve: e.target.checked, reserve_qty: e.target.checked ? Math.max(1, l.quantity - l.qty_received) : 0 } : x))} />
                    Émettre une réserve
                  </label>
                  {l.reserve && (
                    <div className="flex gap-1.5 mt-1">
                      <input type="number" min="1" max={l.quantity} value={l.reserve_qty}
                        onChange={(e) => setLines(lines.map((x, i) => i === idx ? { ...x, reserve_qty: parseInt(e.target.value || 0, 10) } : x))}
                        className="w-14 px-1 py-0.5 rounded bg-black/30 border border-amber-400/30 text-center text-xs" />
                      <input value={l.reason} placeholder="Motif précis et circonstancié"
                        onChange={(e) => setLines(lines.map((x, i) => i === idx ? { ...x, reason: e.target.value } : x))}
                        className="flex-1 px-2 py-0.5 rounded bg-black/30 border border-amber-400/30 text-xs" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs text-white/60 mb-1 flex items-center gap-1"><PenLine className="w-3 h-3" /> Signature électronique</p>
            <canvas ref={canvasRef} width={440} height={110}
              className="w-full rounded-lg bg-white touch-none cursor-crosshair"
              onMouseDown={start} onMouseMove={move} onMouseUp={() => setDrawing(false)} onMouseLeave={() => setDrawing(false)}
              onTouchStart={start} onTouchMove={move} onTouchEnd={() => setDrawing(false)}
              data-testid="rar-signature-canvas" />
            <button type="button" onClick={clearSig} className="text-[10px] text-white/40 hover:text-white/70 mt-0.5">Effacer</button>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <label className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs border border-white/15 cursor-pointer hover:bg-white/5">
              <Camera className="w-3.5 h-3.5" /> Photo état apparent ({photos.length}/3)
              <input type="file" accept="image/*" className="hidden" onChange={addPhoto} data-testid="rar-photo-input" />
            </label>
            {photos.map((p, i) => (
              <span key={i} className="relative">
                <img src={p} alt="" className="w-10 h-10 rounded object-cover" />
                <button type="button" onClick={() => setPhotos(photos.filter((_, j) => j !== i))}
                  className="absolute -top-1 -right-1 bg-red-500 rounded-full p-0.5"><X className="w-2.5 h-2.5" /></button>
              </span>
            ))}
            {geo && <span className="text-[10px] text-emerald-300">📍 Géolocalisation capturée</span>}
          </div>

          <button type="button" onClick={submit} disabled={busy} data-testid="rar-confirm-delivery-btn"
            className="w-full py-2.5 rounded-xl font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] disabled:opacity-50 flex items-center justify-center gap-2">
            {busy && <Loader2 className="w-4 h-4 animate-spin" />}
            Signer et déclencher le règlement
          </button>
          <p className="text-[10px] text-white/35 text-center">
            La validation déclenche la facture KDMARCHÉ et l'envoi du lien de paiement. Le plafond est rétabli après encaissement définitif.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
};
