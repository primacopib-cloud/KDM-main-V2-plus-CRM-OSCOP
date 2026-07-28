import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { Camera, ImageOff, Loader2, Sparkles } from 'lucide-react';
import { lolodriveAPI } from '../../services/api';

// Super admin : produits du catalogue sans photo, avec upload direct pour compléter
export const MissingPhotosPanel = () => {
  const [data, setData] = useState(null);
  const [uploadingSku, setUploadingSku] = useState(null);
  const [aiSku, setAiSku] = useState(null);
  const fileRef = useRef(null);
  const targetSku = useRef(null);

  const load = () => lolodriveAPI.adminMissingPhotos().then(setData).catch(() => {});
  useEffect(() => { load(); }, []);
  if (!data || data.count === 0) return null;

  const pickPhoto = (sku) => { targetSku.current = sku; fileRef.current?.click(); };

  const generateAi = async (sku) => {
    setAiSku(sku);
    try {
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/admin/products/${sku}/generate-photo`,
        { method: 'POST', credentials: 'include' });
      const d = await r.json();
      if (!r.ok) { toast.error(d.detail || 'Génération IA échouée'); return; }
      toast.success('Photo IA générée et ajoutée au catalogue ✨');
      load();
    } catch { toast.error('Erreur de connexion'); } finally { setAiSku(null); }
  };

  const upload = async (file) => {
    const sku = targetSku.current;
    if (!sku || !file) return;
    setUploadingSku(sku);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/admin/products/${sku}/photo`,
        { method: 'POST', credentials: 'include', body: fd });
      const d = await r.json();
      if (!r.ok) { toast.error(d.detail || 'Upload échoué'); return; }
      toast.success('Photo ajoutée au catalogue ✓');
      load();
    } catch { toast.error('Erreur de connexion'); } finally { setUploadingSku(null); }
  };

  return (
    <div className="mt-6 rounded-2xl bg-amber-500/[0.04] border border-amber-500/25 p-5" data-testid="missing-photos-panel">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="font-semibold flex items-center gap-2">
          <ImageOff className="w-4 h-4 text-amber-400" /> Produits sans photo
          <span className="text-xs font-bold text-amber-300 bg-amber-400/10 border border-amber-400/30 rounded-full px-2 py-0.5"
            data-testid="missing-photos-count">{data.count}</span>
        </div>
        <span className="text-[11px] text-white/40">Ajoutez une photo pour améliorer la lisibilité du catalogue.</span>
      </div>
      <input ref={fileRef} type="file" accept="image/*" className="hidden" data-testid="missing-photo-file-input"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ''; }} />
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {data.products.map((p) => (
          <div key={p.sku} data-testid={`missing-photo-row-${p.sku}`}
            className="flex items-center justify-between gap-2 rounded-lg bg-white/[0.03] border border-white/[0.06] px-3 py-2 text-xs">
            <span className="min-w-0">
              <span className="block font-medium truncate">{p.name}</span>
              <span className="block text-[10px] text-white/40 truncate">
                {p.category || '—'}{p.subcategory ? ` · ${p.subcategory}` : ''}{p.point_code ? ` · Relais ${p.point_code}` : ''}
              </span>
            </span>
            <span className="flex items-center gap-1 shrink-0">
              <button type="button" onClick={() => generateAi(p.sku)} disabled={aiSku === p.sku}
                data-testid={`missing-photo-ai-${p.sku}`} title="Générer une photo d'illustration par IA"
                className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-bold text-[#c4b5fd] bg-[#7c3aed]/10 border border-[#7c3aed]/35 hover:bg-[#7c3aed]/20 disabled:opacity-60">
                {aiSku === p.sku ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                IA
              </button>
              <button type="button" onClick={() => pickPhoto(p.sku)} disabled={uploadingSku === p.sku}
                data-testid={`missing-photo-upload-${p.sku}`}
                className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-bold text-amber-300 bg-amber-400/10 border border-amber-400/35 hover:bg-amber-400/20">
                {uploadingSku === p.sku ? <Loader2 className="w-3 h-3 animate-spin" /> : <Camera className="w-3 h-3" />}
                Photo
              </button>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
