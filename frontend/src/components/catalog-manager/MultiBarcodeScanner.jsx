import { useEffect, useRef, useState } from 'react';
import { X, ScanBarcode, Check, Keyboard } from 'lucide-react';
import { toast } from 'sonner';

export const MultiBarcodeScanner = ({ open, onClose, onDone, max = 10 }) => {
  const videoRef = useRef(null);
  const codesRef = useRef([]);
  const [codes, setCodes] = useState([]);
  const [manual, setManual] = useState('');
  const [error, setError] = useState('');

  const addCode = (raw) => {
    const code = String(raw || '').trim();
    if (!code) return;
    if (codesRef.current.includes(code)) return;
    if (codesRef.current.length >= max) {
      toast.warning(`Maximum ${max} codes atteint`);
      return;
    }
    codesRef.current = [...codesRef.current, code];
    setCodes(codesRef.current);
    toast.success(`Code ajouté : ${code} (${codesRef.current.length}/${max})`);
  };

  const removeCode = (code) => {
    codesRef.current = codesRef.current.filter((c) => c !== code);
    setCodes(codesRef.current);
  };

  useEffect(() => {
    if (!open) return undefined;
    codesRef.current = [];
    setCodes([]);
    setError('');
    setManual('');
    let stream, timer, stopped = false;
    const start = async () => {
      if (!('BarcodeDetector' in window)) {
        setError('Caméra non supportée par ce navigateur — utilisez le champ lecteur code-barres ci-dessous.');
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
            const found = await detector.detect(videoRef.current);
            found.forEach((c) => addCode(c.rawValue));
          } catch { /* frame not ready */ }
        }, 400);
      } catch {
        setError('Caméra inaccessible — autorisez l\'accès caméra ou utilisez le champ lecteur code-barres ci-dessous.');
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
    <div className="fixed inset-0 z-[80] bg-black/80 flex items-center justify-center p-4" data-testid="multi-barcode-scanner">
      <div className="w-full max-w-md rounded-2xl overflow-hidden bg-[#1A092D] border border-white/15">
        <div className="flex items-center justify-between px-4 py-3">
          <p className="text-sm font-semibold text-white flex items-center gap-2">
            <ScanBarcode className="w-4 h-4 text-[#D9B35A]" /> Scan en série
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-[#D9B35A]/15 text-[#E9CF8E] border border-[#D9B35A]/40"
              data-testid="multi-scan-counter">{codes.length}/{max}</span>
          </p>
          <button type="button" onClick={onClose} data-testid="multi-scan-close" className="p-1.5 rounded-lg text-white/60 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
        {error ? (
          <p className="px-4 pb-2 text-xs text-amber-300">{error}</p>
        ) : (
          <div className="relative">
            <video ref={videoRef} muted playsInline className="w-full h-52 object-cover bg-black" />
            <div className="absolute inset-x-8 top-1/2 -translate-y-1/2 h-16 border-2 border-[#D9B35A] rounded-lg pointer-events-none" />
          </div>
        )}
        <div className="px-4 py-3 space-y-2">
          <div className="flex items-center gap-2">
            <Keyboard className="w-4 h-4 text-white/40 shrink-0" />
            <input
              value={manual}
              autoFocus
              onChange={(e) => setManual(e.target.value.replace(/\D/g, ''))}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addCode(manual);
                  setManual('');
                }
              }}
              placeholder="Lecteur code-barres ou saisie EAN + Entrée"
              data-testid="multi-scan-manual-input"
              className="flex-1 h-9 px-2.5 rounded-lg text-xs font-mono text-white bg-white/[0.05] border border-white/15"
            />
          </div>
          {codes.length > 0 && (
            <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto" data-testid="multi-scan-codes">
              {codes.map((c) => (
                <span key={c} className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
                  {c}
                  <button type="button" onClick={() => removeCode(c)} data-testid={`multi-scan-remove-${c}`} className="hover:text-white">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
          <p className="text-[10px] text-white/40">
            Scannez les codes-barres à la caméra ou au lecteur — les doublons sont ignorés automatiquement.
          </p>
          <button type="button" onClick={() => { onDone(codesRef.current); onClose(); }}
            disabled={!codes.length} data-testid="multi-scan-done-btn"
            className="w-full h-9 rounded-lg text-xs font-bold inline-flex items-center justify-center gap-1.5 disabled:opacity-40"
            style={{ background: '#D9B35A', color: '#1F0A33' }}>
            <Check className="w-3.5 h-3.5" /> Terminer — ajouter {codes.length} code(s)
          </button>
        </div>
      </div>
    </div>
  );
};
