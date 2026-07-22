import { useRef, useState } from 'react';
import { Eraser, PenLine } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

export const CodSignatureDialog = ({ open, onClose, order, onConfirm, loading }) => {
  const canvasRef = useRef(null);
  const drawing = useRef(false);
  const [hasInk, setHasInk] = useState(false);
  const [signerName, setSignerName] = useState('');

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

  const confirm = () => {
    if (!hasInk) return;
    onConfirm({ signature: canvasRef.current.toDataURL('image/png'), signer_name: signerName.trim() });
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
          placeholder="Nom du signataire (client)" data-testid="cod-signer-name"
          className="bg-white/[0.06] border-white/15 text-white placeholder:text-white/35" />
        <div className="rounded-xl overflow-hidden border border-white/20 bg-white touch-none">
          <canvas ref={canvasRef} width={420} height={160} className="w-full cursor-crosshair touch-none"
            data-testid="cod-signature-canvas"
            onPointerDown={start} onPointerMove={move} onPointerUp={end} onPointerLeave={end} />
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={clear} className="border-white/20 text-white/70">
            <Eraser size={13} className="mr-1" /> Effacer
          </Button>
          <Button size="sm" onClick={confirm} disabled={!hasInk || loading} data-testid="cod-signature-confirm-btn"
            className="ml-auto text-[#1A092D] font-semibold"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #F2D07A)' }}>
            {loading ? 'Encaissement…' : 'Confirmer l\'encaissement signé'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
