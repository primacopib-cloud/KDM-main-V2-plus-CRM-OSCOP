import { useRef, useState } from 'react';
import { Camera, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const RelayPhotoUpload = () => {
  const fileRef = useRef(null);
  const [busy, setBusy] = useState(false);

  const upload = async (file) => {
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${API_URL}/api/lolodrive/manager/my-point/photo`, {
        method: 'POST', credentials: 'include', body: fd,
      });
      const d = await r.json();
      if (!r.ok) { toast.error(d.detail || 'Upload échoué'); return; }
      toast.success('Photo de devanture mise à jour ✓ (visible dans l\'espace PASS des clients)');
    } catch { toast.error('Erreur de connexion'); } finally { setBusy(false); }
  };

  return (
    <>
      <input ref={fileRef} type="file" accept="image/*" className="hidden" data-testid="relay-photo-input"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ''; }} />
      <button type="button" onClick={() => fileRef.current?.click()} disabled={busy}
        data-testid="relay-photo-upload-btn" title="Photo de devanture affichée aux titulaires du PASS"
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.04] border border-white/10 text-xs text-white/80 hover:border-[#D9B35A]/50 disabled:opacity-50 transition-colors">
        {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Camera className="w-3 h-3 text-[#D9B35A]" />}
        Photo du relais
      </button>
    </>
  );
};
