import { useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { X, ScanLine } from 'lucide-react';
import jsQR from 'jsqr';

// Scanner caméra CONTINU pour l'inventaire : chaque QR décodé appelle onScan puis reprend après une courte pause
export const InventoryScanner = ({ onScan, onClose, status }) => {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const rafRef = useRef(null);
  const pausedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
        streamRef.current = stream;
        if (!videoRef.current) return;
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(() => {});
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        const tick = () => {
          const v = videoRef.current;
          if (v && v.readyState === v.HAVE_ENOUGH_DATA && !pausedRef.current) {
            canvas.width = v.videoWidth;
            canvas.height = v.videoHeight;
            ctx.drawImage(v, 0, 0, canvas.width, canvas.height);
            const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const code = jsQR(img.data, img.width, img.height);
            if (code?.data) {
              onScan(code.data.trim());
              pausedRef.current = true;
              setTimeout(() => { pausedRef.current = false; }, 1200);
            }
          }
          rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);
      } catch {
        toast.error("Caméra indisponible — autorisez l'accès ou saisissez les stocks manuellement");
        onClose();
      }
    })();
    return () => {
      cancelled = true;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []); // eslint-disable-line

  return (
    <div className="fixed inset-0 z-[100] bg-black/85 flex flex-col items-center justify-center p-4" data-testid="inventory-scan-overlay">
      <div className="relative w-full max-w-sm rounded-2xl overflow-hidden border-2 border-[#22d3ee]/60">
        <video ref={videoRef} className="w-full" muted playsInline />
        <div className="absolute inset-8 border-2 border-white/60 rounded-xl pointer-events-none" />
      </div>
      <p className="text-white/70 text-sm mt-3 flex items-center gap-2">
        <ScanLine className="w-4 h-4 text-[#22d3ee]" /> Scannez les QR produits de la feuille d'inventaire — chaque scan compte +1
      </p>
      {status && (
        <p className="mt-2 px-3 py-1.5 rounded-lg bg-[#22d3ee]/15 border border-[#22d3ee]/40 text-[#22d3ee] text-sm font-bold" data-testid="inventory-scan-status">
          {status}
        </p>
      )}
      <button type="button" onClick={onClose} data-testid="inventory-scan-close"
        className="mt-3 flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-bold text-white bg-white/10 border border-white/20 hover:bg-white/20">
        <X className="w-4 h-4" /> Terminer le scan
      </button>
    </div>
  );
};
