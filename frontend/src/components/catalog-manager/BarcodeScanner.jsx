import { useEffect, useRef, useState } from 'react';
import { X, ScanBarcode } from 'lucide-react';
import { toast } from 'sonner';

export const BarcodeScanner = ({ open, onClose, onDetect }) => {
  const videoRef = useRef(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    let stream, timer, stopped = false;
    const start = async () => {
      if (!('BarcodeDetector' in window)) {
        setError("Lecture directe non supportée par ce navigateur — utilisez la photo du produit (le code-barres y est lu automatiquement).");
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        if (stopped) { stream.getTracks().forEach((t) => t.stop()); return; }
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        const detector = new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'code_128', 'upc_a'] });
        timer = setInterval(async () => {
          try {
            const codes = await detector.detect(videoRef.current);
            if (codes.length) {
              clearInterval(timer);
              onDetect(codes[0].rawValue);
              toast.success(`Code-barres détecté : ${codes[0].rawValue}`);
              onClose();
            }
          } catch { /* frame not ready */ }
        }, 350);
      } catch {
        setError('Caméra inaccessible — autorisez l\'accès caméra ou utilisez la photo du produit.');
      }
    };
    start();
    return () => {
      stopped = true;
      if (timer) clearInterval(timer);
      if (stream) stream.getTracks().forEach((t) => t.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[80] bg-black/80 flex items-center justify-center p-4" data-testid="barcode-scanner">
      <div className="w-full max-w-sm rounded-2xl overflow-hidden bg-[#1A092D] border border-white/15">
        <div className="flex items-center justify-between px-4 py-3">
          <p className="text-sm font-semibold text-white flex items-center gap-2">
            <ScanBarcode className="w-4 h-4 text-[#D9B35A]" /> Scannez le code-barres
          </p>
          <button type="button" onClick={onClose} data-testid="barcode-scanner-close" className="p-1.5 rounded-lg text-white/60 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
        {error ? (
          <p className="px-4 pb-4 text-xs text-amber-300">{error}</p>
        ) : (
          <div className="relative">
            <video ref={videoRef} muted playsInline className="w-full h-64 object-cover bg-black" />
            <div className="absolute inset-x-8 top-1/2 -translate-y-1/2 h-20 border-2 border-[#D9B35A] rounded-lg pointer-events-none" />
            <p className="px-4 py-3 text-[11px] text-white/50">Placez le code-barres dans le cadre — la détection est automatique.</p>
          </div>
        )}
      </div>
    </div>
  );
};
