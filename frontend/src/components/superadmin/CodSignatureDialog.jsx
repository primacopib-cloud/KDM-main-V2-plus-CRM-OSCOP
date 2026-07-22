import { useRef, useState } from 'react';
import { Eraser, PenLine, Camera, X } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

const downscale = (file, maxSize = 900) => new Promise((resolve) => {
  const img = new Image();
  img.onload = () => {
    const ratio = Math.min(1, maxSize / Math.max(img.width, img.height));
    const c = document.createElement('canvas');
    c.width = Math.round(img.width * ratio);
    c.height = Math.round(img.height * ratio);
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
    resolve(c.toDataURL('image/jpeg', 0.8));
  };
  img.src = URL.createObjectURL(file);
});

export const CodSignatureDialog = ({ open, onClose, order, onConfirm, loading }) => {
  const canvasRef = useRef(null);
  const fileRef = useRef(null);
  const drawing = useRef(false);
  const [hasInk, setHasInk] = useState(false);
  const [signerName, setSignerName] = useState('');
  const [photo, setPhoto] = useState(null);

  const pos = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };
  const start = (e) => {
    drawing.current = true;
    const ctx = canvasRef.current.getContext('2d');
    const { x, y } = pos(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
  };
  const move = (e) => {
    if (!drawing.current) return;
    const ctx = canvasRef.current.getContext('2d');
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#1A092D';
    const { x, y } = pos(e);
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasInk(true);
  };
  const end = () => { drawing.current = false; };
  const clear = () => {
    const c = canvasRef.current;
    c.getContext('2d').clearRect(0, 0, c.width, c.height);
    setHasInk(false);
  };

  const onPhotoPick = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhoto(await downscale(file));
    e.target.value = '';
  };

  const confirm = () => {
    if (!hasInk || !signerName.trim()) return;
    onConfirm({ signature: canvasRef.current.toDataURL('image/png'), signer_name: signerName.trim(), photo });
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-md bg-[#2A1045] border-white/15 text-white" data-testid="cod-signature-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <PenLine size={16} className="text-[#D9B35A]" /> Preuve de livraison — {order?.order_number}
          </DialogTitle>
        </DialogHeader>
        <p className="text-xs text-white/60">
          Faites signer le client sur l'écran pour attester la réception des marchandises et le règlement.
        </p>
        <Input value={signerName} onChange={(e) => setSignerName(e.target.value)}
          placeholder="Nom du signataire (client) *" data-testid="cod-signer-name"
          className="bg-white/[0.06] border-white/15 text-white placeholder:text-white/35" />
        <div className="rounded-xl overflow-hidden border border-white/20 bg-white touch-none">
          <canvas ref={canvasRef} width={420} height={160} className="w-full cursor-crosshair touch-none"
            data-testid="cod-signature-canvas"
            onPointerDown={start} onPointerMove={move} onPointerUp={end} onPointerLeave={end} />
        </div>
        <div className="flex items-center gap-2">
          <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={onPhotoPick} data-testid="cod-photo-input" />
          <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()}
            className="border-white/20 text-white/70" data-testid="cod-photo-btn">
            <Camera size={13} className="mr-1" /> {photo ? 'Reprendre la photo' : 'Photo du colis (optionnel)'}
          </Button>
          {photo && (
            <div className="relative">
              <img src={photo} alt="Colis" className="h-10 w-14 object-cover rounded-lg border border-white/20" data-testid="cod-photo-preview" />
              <button onClick={() => setPhoto(null)} className="absolute -top-1.5 -right-1.5 bg-red-500 rounded-full p-0.5">
                <X size={9} />
              </button>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={clear} className="border-white/20 text-white/70">
            <Eraser size={13} className="mr-1" /> Effacer
          </Button>
          <Button size="sm" onClick={confirm} disabled={!hasInk || !signerName.trim() || loading} data-testid="cod-signature-confirm-btn"
            className="ml-auto text-[#1A092D] font-semibold"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
            {loading ? 'Encaissement…' : 'Confirmer l\'encaissement signé'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
