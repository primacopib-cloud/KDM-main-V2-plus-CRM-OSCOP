import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { Camera, X } from 'lucide-react';
import jsQR from 'jsqr';

// Scan caméra du QR-code PASS client (jsQR) — onScan(text) appelé au premier décodage
export const QrPassScanner = ({ onScan }) => {
  const [open, setOpen] = useState(false);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const rafRef = useRef(null);

  const stop = () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (streamRef.current) { streamRef.current.getTracks().forEach((t) => t.stop()); streamRef.current = null; }
    setOpen(false);
  };

  useEffect(() => () => stop(), []); // eslint-disable-line

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      streamRef.current = stream;
      setOpen(true);
      setTimeout(() => {
        if (!videoRef.current) return;
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(() => {});
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        const tick = () => {
          const v = videoRef.current;
          if (v && v.readyState === v.HAVE_ENOUGH_DATA) {
            canvas.width = v.videoWidth;
            canvas.height = v.videoHeight;
            ctx.drawImage(v, 0, 0, canvas.width, canvas.height);
            const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const code = jsQR(img.data, img.width, img.height);
            if (code?.data) {
              toast.success('QR-code PASS scanné ✓');
              stop();
              onScan(code.data.trim());
              return;
            }
          }
          rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);
      }, 150);
    } catch {
      toast.error("Caméra indisponible — autorisez l'accès ou saisissez le code manuellement");
    }
  };

  return (
    <>
      <button type="button" onClick={start} title="Scanner le QR-code PASS du client" data-testid="qr-scan-btn"
        className="h-9 px-2.5 rounded-lg flex items-center gap-1 text-xs font-bold text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/40 hover:bg-[#D9B35A]/25 shrink-0">
        <Camera className="w-4 h-4" /> Scan
      </button>
      {open && (
        <div className="fixed inset-0 z-[100] bg-black/85 flex flex-col items-center justify-center p-4" data-testid="qr-scan-overlay">
          <div className="relative w-full max-w-sm rounded-2xl overflow-hidden border-2 border-[#D9B35A]/60">
            <video ref={videoRef} className="w-full" muted playsInline />
            <div className="absolute inset-8 border-2 border-white/60 rounded-xl pointer-events-none" />
          </div>
          <p className="text-white/70 text-sm mt-3">Présentez le QR-code PASS du client devant la caméra…</p>
          <button type="button" onClick={stop} data-testid="qr-scan-close"
            className="mt-3 flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-bold text-white bg-white/10 border border-white/20 hover:bg-white/20">
            <X className="w-4 h-4" /> Fermer
          </button>
        </div>
      )}
    </>
  );
};
